#!/usr/bin/env python3
"""objstopd v2 — distance-aware vision stop daemon (runs ON the comma device).

v2 upgrades over v1 (field problems: imprecise stop position, difficult resume):
  * PRECISE STOPS — pinhole distance from bbox height (narrow road cam, f=2648 px),
    tracked by a tiny per-target Kalman filter (predict with vEgo odometry, correct with
    latency-compensated detections). The stop flag now carries a TARGET DISTANCE and the
    patched planner glides the car onto it with a sqrt speed ramp (a=0.8 m/s^2):
        /tmp/op_stop_requested  content:  "d=<m> t=<monotonic> src=v"
    d=0 (or an empty/foreign file) = legacy stop-now. Stale t (>1 s) = ignored by the
    planner (daemon-crash fail-safe).
  * RELIABLE RESUME —
      - red light: while stopped, detection alternates narrow full-frame and a WIDE-cam
        center-top ROI (the fisheye sees overhead lights the narrow cam loses inside
        ~17 m). Resume only on CONFIRMED GREEN (>=0.5 s); the dangerous "red absent
        timeout" rule is gone. Escape hatches: driver gas press, or a >120 s no-light
        alert (holds, human decides).
      - stop sign: momentary stop (wait_sec, default 3 s from standstill), then resume
        even though the sign is still (or no longer) in view. Re-trigger is suppressed
        by PASS-TRACKING (odometry: the served sign cannot re-latch during pull-away;
        a genuinely new sign farther ahead can) instead of the old fixed cooldown.
  * DILEMMA-ZONE GUARD — if stopping would need > 1.1 m/s^2, do not latch (alert only);
    never brake into the middle of an intersection.
  * ARCHITECTURE — inference thread (adaptive 320/640 input by speed, YUV subsampled
    before RGB conversion) + 20 Hz control loop (KF predict, state machine, flag write).

  python3 objstopd.py                     # shadow (no braking)
  python3 objstopd.py --arm               # drives the planner stop flag

Status: /tmp/objstop_status.json (+ /tmp/objstop_last.jpg with --save-every).
"""
import argparse
import collections
import json
import math
import os
import queue
import signal
import threading
import time

import numpy as np

STOP_FLAG = "/tmp/op_stop_requested"      # ACTUATION: the planner brakes on this (--arm only)
INTENT_FLAG = "/tmp/op_stop_intent"       # INTENT: written always (shadow too) -> exporter
                                          # "stop":0/1 reflects the vision decision even
                                          # when nothing is braking (dashcam / shadow)
RELEASE_FLAG = "/tmp/op_stop_release"     # touch -> one-shot operator release (go)
STATUS = "/tmp/objstop_status.json"

# narrow road camera (comma 3X, OX03C10): 1928x1208, focal 2648 px
F_NARROW = 2648.0
NATIVE_W, NATIVE_H = 1928, 1208
SUBSAMPLE = 2                      # YUV subsample factor before RGB conversion

SIGN_H = 0.75                      # US 30" stop sign face [m]
LIGHT_H = 1.07                     # 3-lamp traffic light housing [m]
A_STOP = 0.8                       # must match the planner ramp
A_MAX_LATCH = 1.1                  # dilemma-zone guard [m/s^2]
H_PX_NOISE = 6.0                   # bbox height 1-sigma in native px

PERSON, TRAFFIC_LIGHT, STOP_SIGN = 0, 9, 11


# ---------- camera frame (NV12 -> RGB with subsampling) ----------
def yuv_to_rgb(y, u, v):
  ul = np.repeat(np.repeat(u, 2).reshape(u.shape[0], y.shape[1]), 2, axis=0).reshape(y.shape)
  vl = np.repeat(np.repeat(v, 2).reshape(v.shape[0], y.shape[1]), 2, axis=0).reshape(y.shape)
  yuv = np.dstack((y, ul, vl)).astype(np.int16)
  yuv[:, :, 1:] -= 128
  m = np.array([[1.0, 1.0, 1.0], [0.0, -0.39465, 2.03211], [1.13983, -0.5806, 0.0]])
  return np.dot(yuv, m).clip(0, 255).astype(np.uint8)


def extract_image(buf, sub=SUBSAMPLE):
  """NV12 VisionBuf -> RGB, subsampled by `sub` (bbox px scale = native/sub)."""
  y = np.array(buf.data[:buf.uv_offset], dtype=np.uint8).reshape((-1, buf.stride))[:buf.height, :buf.width]
  u = np.array(buf.data[buf.uv_offset::2], dtype=np.uint8).reshape((-1, buf.stride // 2))[:buf.height // 2, :buf.width // 2]
  v = np.array(buf.data[buf.uv_offset + 1::2], dtype=np.uint8).reshape((-1, buf.stride // 2))[:buf.height // 2, :buf.width // 2]
  if sub > 1:
    y = y[::sub, ::sub]
    u = u[::sub, ::sub]
    v = v[::sub, ::sub]
    # keep U/V exactly half of Y (repeat-based upsampling requires it)
    y = y[: (u.shape[0] * 2), : (u.shape[1] * 2)]
    u = u[: y.shape[0] // 2, : y.shape[1] // 2]
    v = v[: y.shape[0] // 2, : y.shape[1] // 2]
  return yuv_to_rgb(y, u, v)


# ---------- geometry ----------
def pinhole_d(h_native_px, H_m, f_px=F_NARROW):
  """Distance from bbox height in NATIVE pixels (narrow cam only)."""
  if h_native_px <= 1:
    return None
  return f_px * H_m / h_native_px


def meas_R(d, H_m, f_px=F_NARROW):
  """Measurement variance: sigma_d ~ d^2 * sigma_h / (f*H)."""
  s = (d * d * H_PX_NOISE) / (f_px * H_m)
  return max(s * s, 0.04)


def ramp_v(d_eff, a=A_STOP):
  """Planner-side allowed speed for remaining distance (mirrors the device patch)."""
  return math.sqrt(2.0 * a * max(d_eff, 0.0))


# ---------- per-class distance track (1-state KF) ----------
class Track:
  def __init__(self, H_m):
    self.H = H_m
    self.d = None
    self.P = 0.0
    self.hits = 0
    self.last_t = 0.0
    self.latched = False
    self.waived = False        # dilemma-zone: too close/fast to stop -> never latch
    self.rejects = 0

  def predict(self, v, dt):
    if self.d is None:
      return
    self.d -= v * dt
    self.P += (0.02 * v * dt + 0.005) ** 2

  def update(self, d_meas, now):
    R = meas_R(d_meas, self.H)
    if self.d is None:
      self.d, self.P = d_meas, R
      self.hits, self.last_t, self.rejects = 1, now, 0
      return True
    innov = d_meas - self.d
    gate = max(3.0, 3.0 * math.sqrt(self.P + R))
    if abs(innov) > gate:
      self.rejects += 1
      if self.rejects >= 4 and not self.latched:   # persistent mismatch -> new object
        self.d, self.P, self.hits, self.rejects = d_meas, R, 1, 0
        self.latched = self.waived = False
        self.last_t = now
      return False
    K = self.P / (self.P + R)
    self.d += K * innov
    self.P *= (1.0 - K)
    self.hits += 1
    self.last_t = now
    self.rejects = 0
    return True

  def reset(self):
    self.__init__(self.H)


# ---------- state machine ----------
DRIVING, BRAKING, STOPPED_SIGN, STOPPED_RED, STOPPED_PED, RESUMING = \
  "DRIVING", "BRAKING", "STOPPED_SIGN", "STOPPED_RED", "STOPPED_PED", "RESUMING"


class VisionStopSM:
  """Distance-aware stop/wait/resume. Inputs each 20 Hz tick:
    meas: list of dicts {t, cls ('stop_sign'|'red_light'), d (m or None), color}
          (d only from the narrow cam; wide-cam entries carry color with d=None)
    ped_active: pedestrian currently in the forward zone (bool)
    gas_pressed: driver override (bool)
  Output dict: {state, flag (None|('now',)|('dist', d_target)), alert}
  """

  def __init__(self, args):
    self.a = args
    self.state = DRIVING
    self.reason = None
    self.tracks = {"stop_sign": Track(SIGN_H), "red_light": Track(LIGHT_H)}
    self.ped_hold = False
    self.ped_last_seen = None
    self.ped_sightings = collections.deque(maxlen=12)
    self.t_standstill = None
    self.odo = 0.0
    self.resume_odo = 0.0
    self.resume_t = 0.0
    self.green_events = collections.deque(maxlen=8)
    self.red_last_seen = None
    self.alert = ""

  # -- helpers --
  def _setback(self, cls):
    return self.a.sign_setback if cls == "stop_sign" else self.a.tl_setback

  def _green_confirmed(self, now):
    ev = [t for t in self.green_events if now - t < 1.5]
    return len(ev) >= 2 and (now - ev[0]) >= 0.5 and (now - ev[-1]) < 0.8

  def _ped_update(self, ped_active, now):
    # N-of-M confirmation: >=2 sightings within 1.0 s to SET the hold (kills
    # single-frame false stops); clear_sec of absence to RELEASE (sticky).
    if ped_active:
      self.ped_sightings.append(now)
      self.ped_last_seen = now
      recent = [t for t in self.ped_sightings if now - t <= 1.0]
      if len(recent) >= 2:
        self.ped_hold = True
    elif self.ped_hold and self.ped_last_seen is not None and \
            (now - self.ped_last_seen) >= self.a.clear_sec:
      self.ped_hold = False

  def _feed(self, meas, now, v):
    """Route measurements into tracks / color memories."""
    min_new = {"stop_sign": 0.0, "red_light": 0.0}
    if self.state == RESUMING:
      min_new = {"stop_sign": 12.0, "red_light": 10.0}
    for m in meas:
      cls = m["cls"]
      if cls == "red_light":
        if m.get("color") == "green":
          # rate-limit so a dense green stream still spans the 0.5 s confirm window
          if not self.green_events or m["t"] - self.green_events[-1] >= 0.15:
            self.green_events.append(m["t"])
          continue
        if m.get("color") != "red":
          continue
        self.red_last_seen = now
        if m.get("d") is None:
          continue
      if cls not in self.tracks or m.get("d") is None:
        continue
      if m["d"] < min_new[cls] and self.tracks[cls].d is None:
        continue                       # suppress re-latching the just-served object
      self.tracks[cls].update(m["d"], now)

  def _try_latch(self, cls, v):
    tr = self.tracks[cls]
    if tr.d is None or tr.latched or tr.waived or tr.hits < 3:
      return False
    d_line = tr.d - self._setback(cls)
    if d_line <= 0.5:
      tr.waived = True
      self.alert = f"{cls} too close to stop"
      return False
    a_req = v * v / (2.0 * max(d_line, 0.1))
    if a_req > A_MAX_LATCH:
      tr.waived = True
      self.alert = f"{cls} dilemma zone (need {a_req:.1f} m/s^2) - continuing"
      return False
    tr.latched = True
    return True

  def _enter_resuming(self, now):
    self.state = RESUMING
    self.resume_odo = self.odo
    self.resume_t = now
    for tr in self.tracks.values():
      tr.reset()
    self.green_events.clear()
    self.reason = None

  # -- main tick --
  def update(self, now, dt, v, meas, ped_active, gas_pressed=False, release=False):
    self.alert = ""
    self.odo += v * dt
    for tr in self.tracks.values():
      tr.predict(v, dt)
      if tr.d is not None and not tr.latched and (now - tr.last_t) > 3.0:
        tr.reset()                       # unlatched track went stale
    self._ped_update(ped_active, now)
    self._feed(meas, now, v)

    if (gas_pressed or release) and self.state in (BRAKING, STOPPED_SIGN, STOPPED_RED, STOPPED_PED):
      # driver gas tap or an explicit operator release always wins
      self._enter_resuming(now)
      self.ped_hold = False              # operator takes responsibility (static dummy case)
      self.ped_sightings.clear()

    if self.state == DRIVING:
      if self.ped_hold:
        self.state, self.reason = BRAKING, "pedestrian"
      else:
        for cls in ("red_light", "stop_sign"):
          if self._try_latch(cls, v):
            self.state, self.reason = BRAKING, cls
            break

    elif self.state == BRAKING:
      if self.reason == "pedestrian":
        if v < 0.3:
          self.state = STOPPED_PED
          self.t_standstill = now
        elif not self.ped_hold:
          self._enter_resuming(now)
      else:
        tr = self.tracks[self.reason]
        if self.reason == "red_light" and self._green_confirmed(now) and v > 1.0:
          self._enter_resuming(now)      # light turned green on approach
        elif v < 0.3:
          self.state = STOPPED_SIGN if self.reason == "stop_sign" else STOPPED_RED
          self.t_standstill = now
        elif tr.d is not None and (tr.d - self._setback(self.reason)) < -5.0:
          self._enter_resuming(now)      # somehow passed the target (override etc.)

    elif self.state == STOPPED_SIGN:
      if not self.ped_hold and (now - self.t_standstill) >= self.a.wait_sec:
        self._enter_resuming(now)

    elif self.state == STOPPED_RED:
      if not self.ped_hold and self._green_confirmed(now):
        self._enter_resuming(now)
      elif (now - self.t_standstill) > 120.0 and \
              (self.red_last_seen is None or now - self.red_last_seen > 10.0) and \
              not self.green_events:
        self.alert = "no light visible >120s - holding, driver decides"

    elif self.state == STOPPED_PED:
      if not self.ped_hold:
        self._enter_resuming(now)
      elif self.t_standstill is not None and (now - self.t_standstill) > 20.0:
        self.alert = "PEDESTRIAN HOLD >20s - tap gas or send release to go"

    elif self.state == RESUMING:
      if self.ped_hold:
        self.state, self.reason = BRAKING, "pedestrian"
      elif (self.odo - self.resume_odo) > 8.0 or (now - self.resume_t) > 15.0:
        self.state = DRIVING

    # ---- output flag ----
    flag = None
    if self.ped_hold and self.state in (BRAKING, STOPPED_SIGN, STOPPED_RED, STOPPED_PED):
      flag = ("now",)
    elif self.state == BRAKING and self.reason in self.tracks:
      tr = self.tracks[self.reason]
      d_line = max((tr.d or 0.0) - self._setback(self.reason), 0.0)
      flag = ("dist", d_line)
    elif self.state in (STOPPED_SIGN, STOPPED_RED, STOPPED_PED):
      flag = ("now",)
    elif self.state == BRAKING:          # pedestrian braking
      flag = ("now",)
    wait_left = None
    if self.state == STOPPED_SIGN and self.t_standstill is not None:
      wait_left = max(0.0, self.a.wait_sec - (now - self.t_standstill))
    return {"state": self.state, "reason": self.reason, "flag": flag,
            "ped_hold": self.ped_hold, "alert": self.alert, "wait_left": wait_left,
            "resume_gone": (self.odo - self.resume_odo) if self.state == RESUMING else None}


REASON_TXT = {"stop_sign": "STOP SIGN", "red_light": "RED LIGHT", "pedestrian": "PEDESTRIAN"}


def display_info(out, sm, v_ego):
  """One source of truth for what every UI shows: current ACTION + the NEXT step.

  Returns {action, next, level, screen1, screen2}; level in
  {"ok","info","prompt","danger"} (maps to status colors / device alert status).
  """
  st, reason = out["state"], out["reason"]
  flag = out["flag"]
  d_flag = None if (flag is None or flag[0] == "now") else flag[1]
  if out["ped_hold"] and st in (BRAKING, STOPPED_SIGN, STOPPED_RED, STOPPED_PED):
    reason = "pedestrian"
  r_txt = REASON_TXT.get(reason, "")

  if st == DRIVING:
    tracked = [(k, tr) for k, tr in sm.tracks.items() if tr.d is not None]
    if tracked:
      k, tr = min(tracked, key=lambda x: x[1].d)
      act = f"CONTINUE — {REASON_TXT[k]} seen {tr.d:.0f} m"
      nxt = ("will latch a stop once confirmed" if not tr.waived
             else "too close/fast to stop safely — passing (dilemma zone)")
      return {"action": act, "next": nxt, "level": "info",
              "screen1": f"VISION: {REASON_TXT[k]} {tr.d:.0f}m", "screen2": nxt}
    return {"action": "CONTINUE", "next": "watching for stop sign / red light / pedestrian",
            "level": "ok", "screen1": "", "screen2": ""}
  if st == BRAKING:
    if reason == "pedestrian":
      return {"action": "STOPPING NOW — PEDESTRIAN", "next": "hold until path is clear",
              "level": "danger", "screen1": "VISION: PEDESTRIAN", "screen2": "stopping now"}
    d_s = f"{d_flag:.0f} m" if d_flag is not None else "now"
    return {"action": f"BRAKING — {r_txt}, stop in {d_s}",
            "next": ("resume when green confirmed" if reason == "red_light"
                     else f"stop, wait {sm.a.wait_sec:.0f}s, then resume"),
            "level": "prompt", "screen1": f"VISION: {r_txt}", "screen2": f"braking — stop in {d_s}"}
  if st == STOPPED_SIGN:
    wl = out.get("wait_left") or 0.0
    return {"action": f"HOLDING — STOP SIGN ({wl:.1f}s left)",
            "next": "auto-resume when timer ends (pedestrian blocks it)",
            "level": "prompt", "screen1": "VISION: STOP SIGN",
            "screen2": f"resuming in {wl:.0f}s"}
  if st == STOPPED_RED:
    return {"action": "HOLDING — RED LIGHT", "next": "resume on confirmed GREEN (gas tap overrides)",
            "level": "prompt", "screen1": "VISION: RED LIGHT", "screen2": "waiting for green"}
  if st == STOPPED_PED:
    return {"action": "HOLDING — PEDESTRIAN", "next": "resume when clear for 1.5s",
            "level": "danger", "screen1": "VISION: PEDESTRIAN", "screen2": "waiting until clear"}
  if st == RESUMING:
    gone = out.get("resume_gone") or 0.0
    return {"action": f"RESUMING ({gone:.0f} m / 8 m)", "next": "back to normal driving",
            "level": "ok", "screen1": "VISION: RESUMING", "screen2": ""}
  return {"action": st, "next": "", "level": "info", "screen1": "", "screen2": ""}


# ---------- relevance: raw detections -> SM measurements ----------
def to_measurements(dets, W, H, t_frame, args, cam, sub=SUBSAMPLE):
  """dets are in the (subsampled) frame the detector saw. Returns (meas, ped_active)."""
  meas = []
  ped = False
  for d in dets:
    if d.cls == STOP_SIGN and cam == "narrow":
      dist = pinhole_d(d.h * sub, SIGN_H)
      if dist is not None and 3.0 < dist < 90.0:
        meas.append({"t": t_frame, "cls": "stop_sign", "d": dist, "color": None})
    elif d.cls == TRAFFIC_LIGHT:
      if cam == "narrow":
        if d.cy > args.tl_max_cy * H:
          continue
        dist = pinhole_d(d.h * sub, LIGHT_H)
        meas.append({"t": t_frame, "cls": "red_light", "d": dist, "color": d.color})
      else:                              # wide: presence/color only (fisheye)
        meas.append({"t": t_frame, "cls": "red_light", "d": None, "color": d.color})
    elif d.cls == PERSON and cam == "narrow":
      in_band = args.ped_band_lo * W <= d.cx <= args.ped_band_hi * W
      close = d.h * sub >= args.ped_min_h
      ahead = d.y2 >= args.ped_min_bottom * H
      if in_band and close and ahead:
        ped = True
  return meas, ped


# ---------- flag file ----------
def write_flag(flag, now, path=STOP_FLAG):
  """Atomic write with our tag; never delete a file we didn't write (manual stops)."""
  try:
    if flag is None:
      if os.path.exists(path):
        with open(path) as f:
          if "src=v" not in f.read():
            return                       # foreign (manual) stop - leave it alone
        os.remove(path)
      return
    d = 0.0 if flag[0] == "now" else max(float(flag[1]), 0.0)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
      f.write(f"d={d:.2f} t={now:.3f} src=v")
    os.replace(tmp, path)
  except OSError:
    pass


# ---------- inference thread ----------
class InferThread(threading.Thread):
  def __init__(self, args, shared):
    super().__init__(daemon=True)
    self.a = args
    self.sh = shared
    self.q = queue.Queue(maxsize=8)

  def run(self):
    from yolo_infer import Detector
    from msgq.visionipc import VisionIpcClient, VisionStreamType
    cc = {PERSON: self.a.ped_conf}       # lower bar for person only (recall)
    det320 = Detector(self.a.onnx_320, conf=self.a.conf, imgsz=320, class_conf=cc)
    det640 = Detector(self.a.onnx_640, conf=self.a.conf, imgsz=640, class_conf=cc) if self.a.onnx_640 else None
    narrow = VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_ROAD, True)
    wide = VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_WIDE_ROAD, True)
    while not narrow.connect(False):
      time.sleep(0.5)
    wide_ok = wide.connect(False)
    print(f"[objstopd] narrow {narrow.width}x{narrow.height} connected; wide={'ok' if wide_ok else 'NO'}", flush=True)
    use_wide_next = False
    last_save = 0.0
    while not self.sh["quit"]:
      stopped_red = self.sh["state"] == STOPPED_RED
      cam = "wide" if (stopped_red and wide_ok and use_wide_next) else "narrow"
      use_wide_next = not use_wide_next
      client = wide if cam == "wide" else narrow
      buf = client.recv()
      if buf is None:
        if cam == "wide":
          wide_ok = wide.connect(False)
        time.sleep(0.05)
        continue
      t_frame = time.monotonic()
      rgb = extract_image(buf)
      if cam == "wide":
        h, w = rgb.shape[:2]
        rgb = rgb[0:int(h * 0.55), int(w * 0.2):int(w * 0.8)]   # center-top ROI (overhead lights)
      det = det640 if (det640 is not None and self.sh["v_ego"] > 8.0 and cam == "narrow") else det320
      dets = det.detect(rgb)
      H, W = rgb.shape[:2]
      meas, ped = to_measurements(dets, W, H, t_frame, self.a, cam)
      try:
        self.q.put_nowait({"t": t_frame, "cam": cam, "meas": meas, "ped": ped,
                           "infer_ms": det.last_ms, "imgsz": det.imgsz,
                           "dets": [d.as_dict() for d in dets]})
      except queue.Full:
        pass
      if self.a.save_every and t_frame - last_save >= self.a.save_every:
        last_save = t_frame
        try:
          from PIL import Image, ImageDraw
          im = Image.fromarray(rgb); dr = ImageDraw.Draw(im)
          for d in dets:
            c = {"red": (255, 0, 0), "green": (0, 255, 0), "yellow": (255, 200, 0)}.get(d.color, (0, 200, 255))
            dr.rectangle([d.x1, d.y1, d.x2, d.y2], outline=c, width=3)
          im.save("/tmp/objstop_last.jpg", "JPEG")
        except Exception:
          pass


# ---------- main ----------
def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--onnx-320", default="/data/objstop/yolov8n_320.onnx")
  ap.add_argument("--onnx-640", default="/data/objstop/yolov8n.onnx", help="'' to disable the high-speed model")
  ap.add_argument("--arm", action="store_true", help="write the planner stop flag (default: shadow)")
  ap.add_argument("--conf", type=float, default=0.4)
  ap.add_argument("--ped-conf", type=float, default=0.30, help="person-class threshold (recall)")
  ap.add_argument("--wait-sec", type=float, default=3.0, help="stop-sign hold from standstill")
  ap.add_argument("--clear-sec", type=float, default=1.5, help="pedestrian-clear hysteresis")
  ap.add_argument("--sign-setback", type=float, default=3.0)
  ap.add_argument("--tl-setback", type=float, default=10.0)
  ap.add_argument("--tl-max-cy", type=float, default=0.6)
  ap.add_argument("--ped-min-h", type=float, default=90.0, help="native px")
  ap.add_argument("--ped-band-lo", type=float, default=0.2)
  ap.add_argument("--ped-band-hi", type=float, default=0.8)
  ap.add_argument("--ped-min-bottom", type=float, default=0.45)
  ap.add_argument("--save-every", type=float, default=0.3)
  args = ap.parse_args()

  sm = VisionStopSM(args)
  shared = {"quit": False, "state": DRIVING, "v_ego": 0.0}
  inf = InferThread(args, shared)
  inf.start()

  try:
    import cereal.messaging as messaging
    sub = messaging.SubMaster(['carState'])
  except Exception:
    sub = None
  print(f"[objstopd] v2 {'ARMED' if args.arm else 'SHADOW'}  wait={args.wait_sec}s "
        f"setbacks sign={args.sign_setback} tl={args.tl_setback}", flush=True)

  def _stop(*_):
    shared["quit"] = True
  signal.signal(signal.SIGINT, _stop)
  signal.signal(signal.SIGTERM, _stop)

  last = time.monotonic()
  v_ego = 0.0
  gas = False
  last_dets = []
  infer_ms = 0.0
  try:
    while not shared["quit"]:
      now = time.monotonic()
      dt = min(now - last, 0.2)
      last = now
      if sub is not None:
        sub.update(0)
        if sub.updated.get('carState'):
          cs = sub['carState']
          v_ego = float(cs.vEgo)
          gas = bool(cs.gasPressed)
      shared["v_ego"] = v_ego

      meas, ped = [], False
      while True:
        try:
          item = inf.q.get_nowait()
        except queue.Empty:
          break
        lat = now - item["t"]                       # detection latency
        for m in item["meas"]:
          if m.get("d") is not None:
            m["d"] = m["d"] - v_ego * lat           # latency compensation
        meas.extend(item["meas"])
        ped = ped or item["ped"]
        last_dets = item["dets"]
        infer_ms = item["infer_ms"]

      release = False
      if os.path.exists(RELEASE_FLAG):
        release = True
        try:
          os.remove(RELEASE_FLAG)
        except OSError:
          pass
        print("[objstopd] operator RELEASE received", flush=True)

      out = sm.update(now, dt, v_ego, meas, ped, gas, release=release)
      shared["state"] = out["state"]
      if args.arm:
        write_flag(out["flag"], now)               # actuation (planner brakes)
      write_flag(out["flag"], now, path=INTENT_FLAG)  # intent: always, for "stop":0/1
      disp = display_info(out, sm, v_ego)

      status = {"t": time.time(), "state": out["state"], "reason": out["reason"],
                "ped_hold": out["ped_hold"], "alert": out["alert"],
                "action": disp["action"], "next": disp["next"], "level": disp["level"],
                "screen1": disp["screen1"], "screen2": disp["screen2"],
                "wait_left": out.get("wait_left"),
                "flag": (None if out["flag"] is None else
                         ("now" if out["flag"][0] == "now" else round(out["flag"][1], 2))),
                "armed": args.arm, "v_ego": round(v_ego, 2), "infer_ms": round(infer_ms, 1),
                "tracks": {k: ({"d": round(tr.d, 1), "hits": tr.hits, "latched": tr.latched,
                                "waived": tr.waived} if tr.d is not None else None)
                           for k, tr in sm.tracks.items()},
                "dets": last_dets}
      try:
        tmp = STATUS + ".tmp"
        json.dump(status, open(tmp, "w"))
        os.replace(tmp, STATUS)
      except OSError:
        pass

      if out["flag"] is not None or out["alert"]:
        print(f"[{out['state']}] flag={status['flag']} reason={out['reason']} "
              f"v={v_ego:.1f} {out['alert']}", flush=True)
      time.sleep(max(0.0, 0.05 - (time.monotonic() - now)))
  finally:
    shared["quit"] = True
    if args.arm:
      write_flag(None, time.monotonic())
    write_flag(None, time.monotonic(), path=INTENT_FLAG)
    print("[objstopd] exit; flags cleared", flush=True)


if __name__ == "__main__":
  main()
