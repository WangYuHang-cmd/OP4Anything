#!/usr/bin/env python3
"""live_plot.py — real-time plot of the comma reg_export stream (matplotlib).

Shows a rolling window of key planning/control signals:
  - speed (vEgo) & set speed
  - curvature: model desiredCurvature vs final carControl.curvature
  - accel: longitudinalPlan.aTarget vs carControl.accel
  - steering angle (deg)

Usage:
    python live_plot.py --ip 192.168.x.x
    python live_plot.py --ip 192.168.x.x --seconds 20

Needs matplotlib. The network read runs in a background thread; the main thread
animates so a slow plot never blocks the socket.
"""
import argparse
import collections
import threading
import time

import matplotlib.pyplot as plt
import matplotlib.animation as animation

from stream_lib import stream

WINDOW = 2000  # samples kept (~20 s at 100 Hz)
buf = collections.deque(maxlen=WINDOW)
lock = threading.Lock()


def reader(ip, port):
  for rec in stream(ip, port):
    cc = rec.get("carControl", {})
    cs = rec.get("carState", {})
    cst = rec.get("controlsState", {})
    lp = rec.get("longitudinalPlan", {})
    mv = rec.get("modelV2", {})
    with lock:
      buf.append({
        "t": rec.get("t_mono", time.monotonic()),
        "vEgo": cs.get("vEgo"),
        "vCruise": cs.get("vCruise"),
        "mCurv": mv.get("desiredCurvature"),
        "ccCurv": cc.get("curvature"),
        "desCurv": cst.get("desiredCurvature"),
        "aTarget": lp.get("aTarget0"),
        "ccAccel": cc.get("accel"),
        "steer": cs.get("steeringAngleDeg"),
        "enabled": cc.get("enabled"),
      })


def series(key):
  with lock:
    d = list(buf)
  if not d:
    return [], []
  t0 = d[0]["t"]
  xs = [r["t"] - t0 for r in d]
  ys = [r[key] if r[key] is not None else float("nan") for r in d]
  return xs, ys


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip", required=True)
  ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--seconds", type=float, default=20.0, help="x-axis window")
  args = ap.parse_args()

  threading.Thread(target=reader, args=(args.ip, args.port), daemon=True).start()

  fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
  fig.suptitle(f"comma reg_export live — {args.ip}")
  ax_v, ax_c, ax_a, ax_s = axes

  lines = {
    "vEgo": ax_v.plot([], [], label="vEgo (m/s)")[0],
    "vCruise": ax_v.plot([], [], label="vCruise")[0],
    "mCurv": ax_c.plot([], [], label="model desiredCurv")[0],
    "ccCurv": ax_c.plot([], [], label="carControl.curvature")[0],
    "desCurv": ax_c.plot([], [], label="controlsState.desiredCurv")[0],
    "aTarget": ax_a.plot([], [], label="planned accel[0] (m/s²)")[0],
    "ccAccel": ax_a.plot([], [], label="carControl.accel")[0],
    "steer": ax_s.plot([], [], label="steeringAngle (deg)")[0],
  }
  ax_v.set_ylabel("speed"); ax_c.set_ylabel("curvature 1/m")
  ax_a.set_ylabel("accel"); ax_s.set_ylabel("steer deg"); ax_s.set_xlabel("t (s)")
  for a in axes:
    a.legend(loc="upper left", fontsize=8); a.grid(True, alpha=0.3)

  def update(_):
    for key, ln in lines.items():
      xs, ys = series(key)
      ln.set_data(xs, ys)
    for a in axes:
      a.relim(); a.autoscale_view(scaley=True)
      if buf:
        xmax = series("vEgo")[0][-1] if series("vEgo")[0] else 0
        a.set_xlim(max(0, xmax - args.seconds), max(args.seconds, xmax))
    return list(lines.values())

  _anim = animation.FuncAnimation(fig, update, interval=100, cache_frame_data=False)
  plt.tight_layout()
  plt.show()


if __name__ == "__main__":
  main()
