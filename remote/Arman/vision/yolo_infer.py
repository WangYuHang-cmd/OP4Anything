#!/usr/bin/env python3
"""yolo_infer.py — YOLOv8 (COCO) ONNX inference, pure numpy post-processing.

No cv2, no torch — just onnxruntime + numpy + PIL (all present on the comma device).
Detects the three classes we care about (COCO): person=0, traffic light=9, stop sign=11,
and classifies a traffic-light crop's colour (red/yellow/green) from HSV.

    from yolo_infer import Detector
    det = Detector("yolov8n.onnx", conf=0.35)
    dets = det.detect(rgb)          # rgb: HxWx3 uint8 -> list[Det]
"""
import time
import numpy as np

COCO = [
  'person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light',
  'fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow',
  'elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee',
  'skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard',
  'tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl','banana','apple',
  'sandwich','orange','broccoli','carrot','hot dog','pizza','donut','cake','chair','couch',
  'potted plant','bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone',
  'microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear',
  'hair drier','toothbrush']

PERSON, TRAFFIC_LIGHT, STOP_SIGN = 0, 9, 11
KEEP = {PERSON, TRAFFIC_LIGHT, STOP_SIGN}


class Det:
  __slots__ = ("cls", "name", "conf", "x1", "y1", "x2", "y2", "color")

  def __init__(self, cls, conf, box):
    self.cls = int(cls)
    self.name = COCO[int(cls)] if 0 <= int(cls) < len(COCO) else str(cls)
    self.conf = float(conf)
    self.x1, self.y1, self.x2, self.y2 = [float(v) for v in box]
    self.color = None            # traffic-light colour: red/yellow/green/None

  @property
  def w(self): return self.x2 - self.x1

  @property
  def h(self): return self.y2 - self.y1

  @property
  def cx(self): return 0.5 * (self.x1 + self.x2)

  @property
  def cy(self): return 0.5 * (self.y1 + self.y2)

  def as_dict(self):
    return {"cls": self.cls, "name": self.name, "conf": round(self.conf, 3),
            "box": [round(self.x1), round(self.y1), round(self.x2), round(self.y2)],
            "color": self.color}


def letterbox(img, new=640):
  """Resize (keep aspect) + pad to new x new. Returns padded uint8, (r, dw, dh)."""
  from PIL import Image
  h, w = img.shape[:2]
  r = min(new / h, new / w)
  nh, nw = int(round(h * r)), int(round(w * r))
  im = Image.fromarray(img).resize((nw, nh), Image.BILINEAR)
  canvas = np.full((new, new, 3), 114, dtype=np.uint8)
  dw, dh = (new - nw) // 2, (new - nh) // 2
  canvas[dh:dh + nh, dw:dw + nw] = np.asarray(im)
  return canvas, r, dw, dh


def nms(boxes, scores, iou_thr=0.45):
  """Pure-numpy NMS. boxes: Nx4 xyxy. Returns kept indices."""
  if len(boxes) == 0:
    return []
  x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
  areas = (x2 - x1).clip(0) * (y2 - y1).clip(0)
  order = scores.argsort()[::-1]
  keep = []
  while order.size > 0:
    i = order[0]
    keep.append(i)
    if order.size == 1:
      break
    xx1 = np.maximum(x1[i], x1[order[1:]])
    yy1 = np.maximum(y1[i], y1[order[1:]])
    xx2 = np.minimum(x2[i], x2[order[1:]])
    yy2 = np.minimum(y2[i], y2[order[1:]])
    w = (xx2 - xx1).clip(0)
    h = (yy2 - yy1).clip(0)
    inter = w * h
    iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
    order = order[1:][iou <= iou_thr]
  return keep


def classify_light_color(crop):
  """Classify a traffic-light crop (RGB uint8) as red/yellow/green/None via HSV votes."""
  if crop.size == 0 or crop.shape[0] < 3 or crop.shape[1] < 3:
    return None
  from PIL import Image
  hsv = np.asarray(Image.fromarray(crop).convert("HSV")).astype(np.int32)
  h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
  bright = (s > 60) & (v > 90)                 # lit lamp pixels
  if bright.sum() < max(4, 0.01 * crop.shape[0] * crop.shape[1]):
    return None
  hh = h[bright]
  # PIL HSV hue is 0..255 (maps 0..360). red ~0/255, yellow ~30-45, green ~60-100
  red = ((hh < 12) | (hh > 244)).sum()
  yellow = ((hh >= 12) & (hh < 50)).sum()
  green = ((hh >= 50) & (hh < 110)).sum()
  votes = {"red": red, "yellow": yellow, "green": green}
  best = max(votes, key=votes.get)
  return best if votes[best] > 0 else None


class Detector:
  def __init__(self, onnx_path, conf=0.35, iou=0.45, imgsz=640, threads=4, class_conf=None):
    """conf: default threshold; class_conf: optional {class_id: threshold} overrides
    (e.g. {0: 0.30} lowers the bar for person only)."""
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    self.sess = ort.InferenceSession(onnx_path, so, providers=["CPUExecutionProvider"])
    self.inp = self.sess.get_inputs()[0].name
    self.conf = conf
    self.class_conf = class_conf or {}
    self.iou = iou
    self.imgsz = imgsz
    self.last_ms = 0.0

  def detect(self, rgb, classify_lights=True):
    padded, r, dw, dh = letterbox(rgb, self.imgsz)
    x = padded.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
    t0 = time.time()
    out = self.sess.run(None, {self.inp: x})[0]      # (1, 84, 8400)
    self.last_ms = (time.time() - t0) * 1000.0
    p = out[0].T                                     # (8400, 84)
    boxes_xywh = p[:, :4]
    scores_all = p[:, 4:]
    cls = scores_all.argmax(1)
    conf = scores_all.max(1)
    thr = np.full(cls.shape, self.conf, dtype=np.float32)
    for cid, t in self.class_conf.items():
      thr[cls == cid] = t
    m = (conf > thr) & np.isin(cls, list(KEEP))
    if not m.any():
      return []
    b = boxes_xywh[m]; c = conf[m]; k = cls[m]
    # xywh(center) -> xyxy in padded space, then undo letterbox
    xy = np.empty_like(b)
    xy[:, 0] = b[:, 0] - b[:, 2] / 2
    xy[:, 1] = b[:, 1] - b[:, 3] / 2
    xy[:, 2] = b[:, 0] + b[:, 2] / 2
    xy[:, 3] = b[:, 1] + b[:, 3] / 2
    xy[:, [0, 2]] = (xy[:, [0, 2]] - dw) / r
    xy[:, [1, 3]] = (xy[:, [1, 3]] - dh) / r
    H, W = rgb.shape[:2]
    xy[:, [0, 2]] = xy[:, [0, 2]].clip(0, W - 1)
    xy[:, [1, 3]] = xy[:, [1, 3]].clip(0, H - 1)
    dets = []
    for cid in np.unique(k):
      idx = np.where(k == cid)[0]
      keep = nms(xy[idx], c[idx], self.iou)
      for j in keep:
        dets.append(Det(cid, c[idx][j], xy[idx][j]))
    if classify_lights:
      for d in dets:
        if d.cls == TRAFFIC_LIGHT:
          crop = rgb[int(d.y1):int(d.y2), int(d.x1):int(d.x2)]
          d.color = classify_light_color(crop)
    return dets


if __name__ == "__main__":
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--onnx", required=True)
  ap.add_argument("--image")
  ap.add_argument("--imgsz", type=int, default=640)
  ap.add_argument("--conf", type=float, default=0.35)
  ap.add_argument("--bench", type=int, default=0, help="run N timing iterations on random input")
  ap.add_argument("--out", default="annotated.jpg")
  a = ap.parse_args()
  det = Detector(a.onnx, conf=a.conf, imgsz=a.imgsz)
  if a.bench:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (1208, 1928, 3), dtype=np.uint8)
    ts = []
    for i in range(a.bench):
      det.detect(img, classify_lights=False)
      ts.append(det.last_ms)
    ts = np.array(ts[1:] or ts)
    print(f"infer-only: mean {ts.mean():.0f}ms  p50 {np.percentile(ts,50):.0f}  "
          f"p90 {np.percentile(ts,90):.0f}  -> ~{1000/ts.mean():.1f} Hz (model fwd only)")
  if a.image:
    from PIL import Image, ImageDraw
    rgb = np.asarray(Image.open(a.image).convert("RGB"))
    t0 = time.time()
    dets = det.detect(rgb)
    dt = (time.time() - t0) * 1000
    print(f"{len(dets)} dets in {dt:.0f}ms (infer {det.last_ms:.0f}ms):")
    im = Image.fromarray(rgb); dr = ImageDraw.Draw(im)
    for d in dets:
      lbl = f"{d.name}{('/'+d.color) if d.color else ''} {d.conf:.2f}"
      print("  ", lbl, [round(d.x1), round(d.y1), round(d.x2), round(d.y2)])
      col = {"red": (255, 0, 0), "green": (0, 255, 0), "yellow": (255, 200, 0)}.get(d.color, (0, 200, 255))
      dr.rectangle([d.x1, d.y1, d.x2, d.y2], outline=col, width=3)
      dr.text((d.x1, max(0, d.y1 - 12)), lbl, fill=col)
    im.save(a.out)
    print("saved", a.out)
