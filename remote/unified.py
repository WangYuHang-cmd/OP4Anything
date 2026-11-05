#!/usr/bin/env python3
"""unified.py — one big-font screen: trajectory + control + bus-feasibility.

Left  : bird's-eye trajectory (path, lanes, road edges, lead, ego).
Right : four large stat tiles — SPEED, THROTTLE/BRAKE, STEER, CURVATURE
        (the curvature tile turns red when the planned lateral accel exceeds the bus limit).
Top   : engage status.

Run (on the laptop, one line):
    python3 ~/Desktop/Drive/remote/unified.py --ip 192.168.1.231
Preview:  python3 unified.py --selftest
Bus limit:  --bus-max-lat-acc 2.0
"""
import argparse
import collections
import math
import threading
import time

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec

from stream_lib import stream

BG = "#0e1116"; PANEL = "#161b22"; GRID = "#243040"; FG = "#e6edf3"; MUTED = "#8b949e"
ACCENT = "#58a6ff"; PATH = "#f5c542"; LANE = "#7ee787"; EDGE = "#ff7b72"
GOOD = "#3fb950"; BAD = "#f85149"
matplotlib.rcParams.update({
  "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
  "text.color": FG, "axes.edgecolor": PANEL,
})

latest = {"rec": None, "traj": None}
stats = {"last_recv": 0.0, "t_wall": None, "recv": collections.deque(maxlen=120)}
lock = threading.Lock()


def reader(ip, port):
  for rec in stream(ip, port):
    now = time.monotonic()
    with lock:
      latest["rec"] = rec
      mv = rec.get("modelV2", {})
      if mv.get("_upd") and mv.get("pos_x"):
        latest["traj"] = mv
      stats["last_recv"] = now
      stats["t_wall"] = rec.get("t_wall")
      stats["recv"].append(now)


def synthetic():
  n = 33
  xs = [i * 2.5 for i in range(n)]
  ys = [2.0 * math.sin(x / 26.0) for x in xs]
  latest["traj"] = {"pos_x": xs, "pos_y": [y + 0.3 for y in ys], "_upd": True,
                    "laneLineProbs": [0.3, 0.95, 0.92, 0.35],
                    "laneLines": [[xs, [y - 1.85 + w for y in ys]] for w in (-3.6, 0, 3.7, 7.3)],
                    "roadEdges": [[xs, [y - 7.4 for y in ys]], [xs, [y + 7.4 for y in ys]]]}
  latest["rec"] = {"carState": {"vEgo": 13.4, "steeringAngleDeg": 5.6, "gas": 0.2, "brake": 0.0},
                   "carControl": {"accel": 1.15, "curvature": 0.02, "steer": 0.28, "enabled": True,
                                  "latActive": True, "longActive": False},
                   "controlsState": {"desiredCurvature": 0.021, "desSteerAngleDeg": 6.1, "state": "enabled"}}
  t = time.monotonic()
  stats["last_recv"] = t; stats["t_wall"] = time.time()
  stats["recv"].extend([t - 0.02, t - 0.01, t])


def tile(ax, label, value, sub="", color=FG, vsize=46):
  ax.clear(); ax.axis("off")
  ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=PANEL,
                             edgecolor=GRID, lw=1.2))
  ax.text(0.06, 0.80, label, transform=ax.transAxes, fontsize=15, color=MUTED, va="center")
  ax.text(0.06, 0.40, value, transform=ax.transAxes, fontsize=vsize, fontweight="bold",
          color=color, va="center")
  if sub:
    ax.text(0.06, 0.13, sub, transform=ax.transAxes, fontsize=14, color=MUTED, va="center")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip"); ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--bus-max-lat-acc", type=float, default=2.0)
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()
  if not args.selftest and not args.ip:
    ap.error("--ip required (or --selftest)")

  if args.selftest:
    synthetic()
  else:
    threading.Thread(target=reader, args=(args.ip, args.port), daemon=True).start()

  fig = plt.figure(figsize=(15, 8.5))
  fig.canvas.manager.set_window_title("openpilot — live")
  gs = gridspec.GridSpec(4, 3, width_ratios=[1.5, 0.55, 0.55], hspace=0.14, wspace=0.14,
                         left=0.03, right=0.98, top=0.90, bottom=0.03)
  ax_bev = fig.add_subplot(gs[0:4, 0])
  ax_t = [fig.add_subplot(gs[r, c]) for r, c in [(0, 1), (0, 2), (1, 1), (1, 2),
                                                 (2, 1), (2, 2), (3, 1), (3, 2)]]
  head = fig.text(0.5, 0.955, "", ha="center", fontsize=20, fontweight="bold", color=FG)
  delay_txt = fig.text(0.008, 0.988, "", ha="left", va="top", fontsize=13,
                       family="monospace", color=MUTED)

  ax_bev.set_xlim(-11, 11); ax_bev.set_ylim(-4, 80)
  ax_bev.set_aspect("equal", adjustable="box")
  ax_bev.set_facecolor("#0a1020"); ax_bev.tick_params(colors=MUTED, labelsize=11)
  ax_bev.axvline(0, color=GRID, lw=0.8)
  path_ln, = ax_bev.plot([], [], color=PATH, lw=5, zorder=5)
  lane_lns = [ax_bev.plot([], [], color=LANE, lw=2)[0] for _ in range(4)]
  edge_lns = [ax_bev.plot([], [], color=EDGE, lw=1.6, ls="--")[0] for _ in range(2)]
  lead_pt, = ax_bev.plot([], [], "o", color="#ffa657", ms=15, zorder=6)
  ax_bev.plot([0], [0], marker="^", color=ACCENT, ms=22, zorder=7)

  def fnum(v, s="{:.1f}"):
    return s.format(v) if isinstance(v, (int, float)) else "—"

  def update(_):
    with lock:
      rec = latest["rec"]; tr = latest["traj"]
      lr = stats["last_recv"]; tw = stats["t_wall"]; rt = list(stats["recv"])

    # top-left delay / freshness indicator
    now_m = time.monotonic()
    if lr:
      age = (now_m - lr) * 1000.0                          # data freshness (laptop clock)
      hz = (len(rt) - 1) / (rt[-1] - rt[0]) if len(rt) > 1 and rt[-1] > rt[0] else 0.0
      e2e = (time.time() - tw) * 1000.0 if isinstance(tw, (int, float)) else None
      live = age < 300
      e2e_s = (f"  e2e {e2e:.0f}ms" if e2e is not None and -500 < e2e < 3000 else "  e2e n/a(clk)")
      delay_txt.set_text(f"{'● LIVE' if live else '○ STALE'}  age {age:.0f}ms  {hz:.0f}Hz{e2e_s}")
      delay_txt.set_color(GOOD if live else BAD)
    else:
      delay_txt.set_text("○ waiting for data…"); delay_txt.set_color(MUTED)

    if rec is None:
      return []
    cs = rec.get("carState", {}); cc = rec.get("carControl", {}); cst = rec.get("controlsState", {})
    if tr:
      px, py = tr.get("pos_x", []), tr.get("pos_y", [])
      if px:
        path_ln.set_data(py, px)
      pr = tr.get("laneLineProbs", [1, 1, 1, 1]); ll = tr.get("laneLines", [])
      for i, ln in enumerate(lane_lns):
        if i < len(ll) and ll[i][0]:
          ln.set_data(ll[i][1], ll[i][0]); ln.set_alpha(0.2 + 0.8 * (pr[i] if i < len(pr) else 1))
        else:
          ln.set_data([], [])
      re = tr.get("roadEdges", [])
      for i, ln in enumerate(edge_lns):
        ln.set_data(re[i][1], re[i][0]) if i < len(re) and re[i][0] else ln.set_data([], [])
    d = rec.get("radar", {})
    lead_pt.set_data([d.get("yRel") or 0], [d.get("dRel")]) if d.get("status") and d.get("dRel") else lead_pt.set_data([], [])

    # header
    def oo(b, n):
      return f"{n} " + ("●" if b else "○")
    head.set_text(f"{oo(cc.get('enabled'), 'ENGAGED')}    {oo(cc.get('latActive'), 'LAT')}    "
                  f"{oo(cc.get('longActive'), 'LONG')}    {cst.get('state', '')}")

    # tiles
    vego = cs.get("vEgo")
    tile(ax_t[0], "SPEED  m/s", fnum(vego), sub=f"{fnum(vego*3.6,'{:.0f}')} km/h" if isinstance(vego, (int, float)) else "")
    accel = cc.get("accel")
    if isinstance(accel, (int, float)):
      tile(ax_t[1], "THROTTLE" if accel >= 0 else "BRAKE", f"{accel:+.2f}", sub="m/s² (planned)",
           color=GOOD if accel >= 0 else BAD)
    else:
      tile(ax_t[1], "ACCEL", "—")
    tile(ax_t[2], "STEER  deg", fnum(cs.get("steeringAngleDeg")),
         sub=f"cmd {fnum(cst.get('desSteerAngleDeg'))}")
    curv = cst.get("desiredCurvature")
    lat = (vego or 0) ** 2 * abs(curv) if isinstance(curv, (int, float)) else None
    over = isinstance(lat, (int, float)) and lat > args.bus_max_lat_acc
    tile(ax_t[3], "CURVATURE 1/m", fnum(curv, "{:+.3f}"),
         sub=(f"bus latacc {fnum(lat,'{:.1f}')}/{args.bus_max_lat_acc}" if lat is not None else ""),
         color=BAD if over else GOOD)
    g, b = cs.get("gas"), cs.get("brake")
    tile(ax_t[4], "GAS", fnum(g, "{:.2f}"), sub="pedal (meas)")
    tile(ax_t[5], "BRAKE", fnum(b, "{:.2f}"), sub="pedal (meas)")
    tile(ax_t[6], "TORQUE cmd", fnum(cc.get("steer"), "{:+.2f}"), sub="norm [-1,1]", vsize=40)
    tile(ax_t[7], "R turn radius m", fnum(1.0/abs(curv) if isinstance(curv, (int, float)) and abs(curv) > 1e-4 else float('inf'), "{:.0f}"), sub="1/|kappa|", vsize=40)
    return [path_ln, *lane_lns, *edge_lns, lead_pt]

  if args.selftest:
    update(0)
    fig.savefig("unified_selftest.png", dpi=110, facecolor=BG)
    print("selftest OK -> unified_selftest.png")
    return

  from matplotlib.animation import FuncAnimation
  _an = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
  plt.show()


if __name__ == "__main__":
  main()
