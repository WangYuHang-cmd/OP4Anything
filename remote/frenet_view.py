#!/usr/bin/env python3
"""frenet_view.py — live Frenet trajectory view + bus-transferability panel.

Four panels (dark theme, matches dashboard.py):
  1) d(s)      — lateral offset of the planned trajectory vs the lane-center reference
  2) kappa(s)  — path curvature (>0 = right turn, car frame y-right)
  3) v(s), a(s)— planned speed & tangential accel profiles
  4) transferability — required lateral accel v^2*kappa(s) vs a BUS capability
     envelope (max lateral accel + max curvature from wheelbase & steer limit);
     violating segments are shaded red.

Usage:
    python frenet_view.py --ip <comma_ip>
    python frenet_view.py --selftest                 # render synthetic PNG
    python frenet_view.py --ip <ip> --dump-csv out/  # also save one CSV per second
Bus envelope options: --bus-wheelbase 12 --bus-max-steer-deg 40 --bus-max-lat-acc 2.0
"""
import argparse
import math
import os
import threading
import time

import matplotlib
import matplotlib.pyplot as plt

import frenet
from stream_lib import stream

BG = "#0e1116"; PANEL = "#161b22"; GRID = "#243040"; FG = "#c9d1d9"; MUTED = "#8b949e"
ACCENT = "#58a6ff"; PATH = "#f5c542"; GOOD = "#3fb950"; BAD = "#f85149"; PURPLE = "#d2a8ff"
matplotlib.rcParams.update({
  "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
  "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED, "ytick.color": MUTED,
  "axes.edgecolor": GRID, "grid.color": GRID, "font.size": 9,
})

latest = {"mv": None, "t": 0.0}
lock = threading.Lock()


def reader(ip, port):
  for rec in stream(ip, port):
    mv = rec.get("modelV2", {})
    if mv.get("_upd") and mv.get("pos_x"):
      with lock:
        latest["mv"] = mv
        latest["t"] = rec.get("t_mono", time.monotonic())


def synthetic_mv():
  """S-curve with decel — for --selftest."""
  n = 33
  xs = [i * 2.5 for i in range(n)]
  ys = [2.2 * math.sin(x / 25.0) for x in xs]
  lls = [[xs, [y - 1.85 + 0.3 for y in ys]], [xs, [y - 1.85 for y in ys]],
         [xs, [y + 1.85 for y in ys]], [xs, [y + 1.85 + 3.6 for y in ys]]]
  return {"_upd": True, "pos_x": xs, "pos_y": [y + 0.35 for y in ys],
          "vel_x": [14.0 - 0.25 * i for i in range(n)],
          "laneLines": [lls[0], lls[1], lls[2], lls[3]],
          "laneLineProbs": [0.3, 0.95, 0.92, 0.35]}


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip"); ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--bus-wheelbase", type=float, default=12.0)
  ap.add_argument("--bus-max-steer-deg", type=float, default=40.0)
  ap.add_argument("--bus-max-lat-acc", type=float, default=2.0)
  ap.add_argument("--dump-csv", default=None, help="dir: save frenet CSV once per second")
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()
  if not args.selftest and not args.ip:
    ap.error("--ip required (or --selftest)")

  kappa_max_bus = math.tan(math.radians(args.bus_max_steer_deg)) / args.bus_wheelbase

  if not args.selftest:
    threading.Thread(target=reader, args=(args.ip, args.port), daemon=True).start()
  else:
    latest["mv"] = synthetic_mv()

  fig, axes = plt.subplots(2, 2, figsize=(13, 8))
  fig.canvas.manager.set_window_title("Frenet trajectory — vehicle-agnostic view")
  (ax_d, ax_k), (ax_v, ax_tr) = axes
  fig.suptitle("openpilot trajectory in Frenet / path coordinates  (transferable output)",
               color=FG, fontsize=12, fontweight="bold")
  fig.subplots_adjust(hspace=0.34, wspace=0.22, left=0.07, right=0.97, top=0.9, bottom=0.08)
  for a in axes.flat:
    a.grid(True, alpha=0.25)

  d_ln, = ax_d.plot([], [], color=PATH, lw=2)
  ax_d.axhline(0, color=GRID, lw=0.8)
  ax_d.set_ylabel("d (m)  + = right of ref"); ax_d.set_xlabel("s along reference (m)")
  ttl_d = ax_d.set_title("lateral offset d(s) — ref: lane center", color=MUTED)

  k_ln, = ax_k.plot([], [], color=PURPLE, lw=2)
  kb_ln = ax_k.axhline(kappa_max_bus, color=BAD, lw=1.2, ls="--")
  ax_k.axhline(-kappa_max_bus, color=BAD, lw=1.2, ls="--")
  ax_k.axhline(0, color=GRID, lw=0.8)
  ax_k.set_ylabel("kappa (1/m)  + = right"); ax_k.set_xlabel("s along path (m)")
  ax_k.set_title(f"curvature kappa(s)   [--] bus steer limit ±{kappa_max_bus:.3f}", color=MUTED)

  v_ln, = ax_v.plot([], [], color=ACCENT, lw=2, label="v(s) m/s")
  a_ln, = ax_v.plot([], [], color=FG, lw=1.4, label="a(s) m/s²")
  ax_v.axhline(0, color=GRID, lw=0.8)
  ax_v.set_xlabel("s along path (m)"); ax_v.set_title("planned speed / accel profile", color=MUTED)
  ax_v.legend(loc="upper right", fontsize=8, labelcolor=FG, facecolor=PANEL, edgecolor=GRID)

  la_ln, = ax_tr.plot([], [], color=PATH, lw=2, label="required |v²·kappa|")
  ax_tr.axhline(args.bus_max_lat_acc, color=BAD, lw=1.4, ls="--",
                label=f"bus lat-acc limit {args.bus_max_lat_acc} m/s²")
  ax_tr.set_xlabel("s along path (m)"); ax_tr.set_ylabel("lateral accel (m/s²)")
  ax_tr.set_title(f"BUS transferability  (L={args.bus_wheelbase} m, "
                  f"max steer {args.bus_max_steer_deg}°)", color=MUTED)
  ax_tr.legend(loc="upper right", fontsize=8, labelcolor=FG, facecolor=PANEL, edgecolor=GRID)
  shade = {"tr": None, "k": None}
  last_csv = [0.0]

  def update(_):
    with lock:
      mv = latest["mv"]
    if mv is None:
      return []
    sd, src = frenet.frenet_sd(mv)
    prof = frenet.path_profile(mv)
    if not prof:
      return []
    s = [r[0] for r in prof]; k = [r[4] for r in prof]
    v = [r[5] for r in prof]; a = [r[6] for r in prof]
    lat = [abs(vv * vv * kk) for vv, kk in zip(v, k)]

    if sd:
      d_ln.set_data([p[0] for p in sd], [p[1] for p in sd])
      ttl_d.set_text(f"lateral offset d(s) — ref: {src}")
    k_ln.set_data(s, k); v_ln.set_data(s, v); a_ln.set_data(s, a); la_ln.set_data(s, lat)

    # red shading where the BUS cannot follow
    for key, ax in (("tr", ax_tr), ("k", ax_k)):
      if shade[key] is not None:
        shade[key].remove(); shade[key] = None
    bad_tr = [(x, y) for x, y in zip(s, lat) if y > args.bus_max_lat_acc]
    if bad_tr:
      shade["tr"] = ax_tr.fill_between(s, 0, lat, where=[y > args.bus_max_lat_acc for y in lat],
                                       color=BAD, alpha=0.25)
    bad_k = [abs(x) > kappa_max_bus for x in k]
    if any(bad_k):
      shade["k"] = ax_k.fill_between(s, min(k), max(k), where=bad_k, color=BAD, alpha=0.2)

    for ax in axes.flat:
      ax.relim(); ax.autoscale_view()

    if args.dump_csv and time.monotonic() - last_csv[0] > 1.0:
      last_csv[0] = time.monotonic()
      os.makedirs(args.dump_csv, exist_ok=True)
      frenet.to_csv(prof, os.path.join(args.dump_csv, f"traj_{int(time.time())}.csv"), sd=sd)
    return [d_ln, k_ln, v_ln, a_ln, la_ln]

  if args.selftest:
    update(0)
    out = "frenet_selftest.png"
    fig.savefig(out, dpi=110, facecolor=BG)
    print("selftest OK ->", out)
    return

  from matplotlib.animation import FuncAnimation
  _an = FuncAnimation(fig, update, interval=150, cache_frame_data=False)
  plt.show()


if __name__ == "__main__":
  main()
