#!/usr/bin/env python3
"""ped_analysis.py — offline pedestrian-detection study on the 8/4 test videos (LAPTOP, GPU).

Compares yolov8n vs yolov8s at 320/640 input on the dummy-pedestrian route, focusing on
the known standstill windows (from rlog forensics) where the cardboard pedestrian was in
front of the car. Metrics per (model, imgsz): person recall inside the windows, max
consecutive miss gap (flicker), and out-of-window person rate (false-positive proxy).

    ~/yolo_export/bin/python3 ped_analysis.py --dir ~/ped84 --fps 5
"""
import argparse
import glob
import json
import os
import subprocess
import tempfile

# dummy-present standstill windows from rlog forensics (route 13, t0: seg N starts 29.67+60N)
# (segment, start_s_in_seg, end_s_in_seg)
WINDOWS = [
  ("00000013--c1f80e15d6--4", 34.0, 58.4),     # ep1 24.4s hold
  ("00000013--c1f80e15d6--6", 4.3, 11.6),      # ep3 7.3s
  ("00000013--c1f80e15d6--8", 39.3, 43.4),     # ep5 (worked)
  ("00000013--c1f80e15d6--8", 49.2, 56.6),     # ep6 7.4s
  ("00000013--c1f80e15d6--10", 38.2, 45.1),    # ep8 6.9s
  ("00000013--c1f80e15d6--10", 58.2, 60.0),    # ep9 head
  ("00000013--c1f80e15d6--11", 0.0, 24.6),     # ep9 tail (26.4s hold spans segs)
  ("00000013--c1f80e15d6--11", 36.3, 47.3),    # ep10 11.0s
]
SEGS = sorted({w[0] for w in WINDOWS})


def extract_frames(seg_dir, out_dir, fps):
  os.makedirs(out_dir, exist_ok=True)
  if glob.glob(os.path.join(out_dir, "*.jpg")):
    return
  subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i",
                  os.path.join(seg_dir, "qcamera.ts"),
                  "-vf", f"fps={fps}", os.path.join(out_dir, "f%04d.jpg")], check=True)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--dir", required=True, help="dir containing the route--seg folders")
  ap.add_argument("--fps", type=float, default=5.0)
  ap.add_argument("--conf", type=float, default=0.30)
  ap.add_argument("--out", default="ped_report.json")
  args = ap.parse_args()

  from ultralytics import YOLO
  configs = [("yolov8n", 320), ("yolov8n", 640), ("yolov8s", 320), ("yolov8s", 640)]
  models = {}
  for name, _ in configs:
    if name not in models:
      models[name] = YOLO(name + ".pt")

  frame_root = tempfile.mkdtemp(prefix="ped84_")
  report = {}
  for name, imgsz in configs:
    key = f"{name}@{imgsz}"
    tot_in, hit_in, tot_out, hit_out = 0, 0, 0, 0
    max_gap = 0.0
    per_win = []
    for seg in SEGS:
      seg_dir = os.path.join(args.dir, seg)
      fdir = os.path.join(frame_root, seg)
      extract_frames(seg_dir, fdir, args.fps)
      frames = sorted(glob.glob(os.path.join(fdir, "*.jpg")))
      wins = [(a, b) for s, a, b in WINDOWS if s == seg]
      # batch predict
      results = models[name].predict(frames, imgsz=imgsz, conf=args.conf,
                                     classes=[0], verbose=False)
      det = []
      for i, r in enumerate(results):
        t = i / args.fps
        n = len(r.boxes)
        det.append((t, n > 0))
      for a, b in wins:
        inwin = [(t, hit) for t, hit in det if a <= t <= b]
        hits = sum(1 for _, h in inwin if h)
        tot_in += len(inwin)
        hit_in += hits
        gap = cur = 0
        for _, h in inwin:
          cur = 0 if h else cur + 1
          gap = max(gap, cur)
        max_gap = max(max_gap, gap / args.fps)
        per_win.append({"seg": seg, "win": [a, b], "recall": round(hits / max(len(inwin), 1), 3),
                        "max_gap_s": round(gap / args.fps, 2)})
      outwin = [(t, hit) for t, hit in det if not any(a <= t <= b for a, b in wins)]
      tot_out += len(outwin)
      hit_out += sum(1 for _, h in outwin if h)
    report[key] = {
      "recall_in_windows": round(hit_in / max(tot_in, 1), 3),
      "max_miss_gap_s": round(max_gap, 2),
      "person_rate_outside": round(hit_out / max(tot_out, 1), 3),
      "windows": per_win,
    }
    print(f"{key}: recall={report[key]['recall_in_windows']}  "
          f"max_gap={report[key]['max_miss_gap_s']}s  outside_rate={report[key]['person_rate_outside']}")
  json.dump(report, open(args.out, "w"), indent=1)
  print("->", args.out)


if __name__ == "__main__":
  main()
