#!/usr/bin/env python3
"""dashboard.py — pretty real-time dashboard for the comma reg_export stream.

Left  : bird's-eye view in the VEHICLE frame — predicted trajectory, lane lines,
        road edges, lead vehicle, ego at origin (forward = up).
Right : planned throttle/brake (accel), steering (curvature + angle) and speed as
        rolling time-series, plus a status strip (engaged / lat / long / state).

Pure client — needs only matplotlib. The network read runs in a background thread
so a slow render never blocks the socket.

    pip install matplotlib
    python dashboard.py --ip 192.168.x.x
"""
import argparse
import collections
import threading
import time

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec

from stream_lib import stream

# ---------- theme ----------
BG = "#0e1116"; PANEL = "#161b22"; GRID = "#243040"; FG = "#c9d1d9"; MUTED = "#8b949e"
ACCENT = "#58a6ff"; PATH = "#f5c542"; LANE = "#7ee787"; EDGE = "#ff7b72"
GOOD = "#3fb950"; BAD = "#f85149"; THROT = "#3fb950"; BRAKE = "#f85149"
matplotlib.rcParams.update({
  "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
  "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED, "ytick.color": MUTED,
  "axes.edgecolor": GRID, "grid.color": GRID, "font.size": 9,
})

HIST = 1500  # ~15 s at 100 Hz
hist = collections.deque(maxlen=HIST)
latest = {"traj": None}          # last modelV2 block that carried arrays
lock = threading.Lock()


def reader(ip, port):
  for rec in stream(ip, port):
    cc = rec.get("carControl", {}); cs = rec.get("carState", {})
    cst = rec.get("controlsState", {}); mv = rec.get("modelV2", {}); rd = rec.get("radar", {})
    with lock:
      hist.append({
        "t": rec.get("t_mono", time.monotonic()),
        "vEgo": cs.get("vEgo"), "vCruise": cs.get("vCruise"),
        "accel": cc.get("accel"), "gas": cs.get("gas"), "brake": cs.get("brake"),
        "steer": cc.get("steer"), "angle": cs.get("steeringAngleDeg"),
        "desAngle": cc.get("steeringAngleDeg"),
        "ccCurv": cc.get("curvature"), "desCurv": cst.get("desiredCurvature"),
        "enabled": cc.get("enabled"), "latActive": cc.get("latActive"),
        "longActive": cc.get("longActive"), "state": cst.get("state"),
        "dRel": rd.get("dRel"), "yRel": rd.get("yRel"), "leadStatus": rd.get("status"),
      })
      if mv.get("_upd") and mv.get("pos_x") is not None:
        latest["traj"] = mv


def col(key):
  with lock:
    d = list(hist)
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
  ap.add_argument("--window", type=float, default=12.0, help="time-series window (s)")
  ap.add_argument("--selftest", action="store_true", help="render one synthetic frame to PNG and exit")
  args = ap.parse_args()

  if not args.selftest:
    threading.Thread(target=reader, args=(args.ip, args.port), daemon=True).start()

  fig = plt.figure(figsize=(14, 8))
  fig.canvas.manager.set_window_title(f"comma reg_export — {args.ip}")
  gs = gridspec.GridSpec(4, 2, width_ratios=[1.25, 1], height_ratios=[1, 1, 1, 0.5],
                         hspace=0.45, wspace=0.2, left=0.05, right=0.97, top=0.93, bottom=0.07)

  ax_bev = fig.add_subplot(gs[0:3, 0])
  ax_spd = fig.add_subplot(gs[0, 1])
  ax_acc = fig.add_subplot(gs[1, 1])
  ax_str = fig.add_subplot(gs[2, 1])
  ax_txt = fig.add_subplot(gs[3, :]); ax_txt.axis("off")
  fig.suptitle("openpilot planning / control — live", color=FG, fontsize=13, fontweight="bold")

  # bird's-eye setup (vehicle frame: x forward=up, y right=+x on screen)
  ax_bev.set_title("bird's-eye (vehicle frame)", color=MUTED)
  ax_bev.set_xlim(-12, 12); ax_bev.set_ylim(-5, 85)
  ax_bev.set_xlabel("lateral (m)  ← left | right →"); ax_bev.set_ylabel("forward (m)")
  ax_bev.set_aspect("equal", adjustable="box"); ax_bev.grid(True, alpha=0.25)
  ax_bev.axvline(0, color=GRID, lw=0.8)
  path_ln, = ax_bev.plot([], [], color=PATH, lw=3, label="planned path", zorder=5)
  lane_lns = [ax_bev.plot([], [], color=LANE, lw=1.6)[0] for _ in range(4)]
  edge_lns = [ax_bev.plot([], [], color=EDGE, lw=1.4, ls="--")[0] for _ in range(2)]
  lead_pt, = ax_bev.plot([], [], "o", color="#ffa657", ms=11, label="lead", zorder=6)
  # ego marker (triangle)
  ax_bev.plot([0], [0], marker=(3, 0, 0), color=ACCENT, ms=16, zorder=7)
  ax_bev.legend(loc="upper right", fontsize=8, facecolor=PANEL, edgecolor=GRID, labelcolor=FG)

  # time-series
  for a in (ax_spd, ax_acc, ax_str):
    a.grid(True, alpha=0.25)
  ax_spd.set_ylabel("speed m/s")
  spd_ln, = ax_spd.plot([], [], color=ACCENT, lw=1.8, label="vEgo")
  set_ln, = ax_spd.plot([], [], color=MUTED, lw=1.2, ls="--", label="set")
  ax_spd.legend(loc="upper left", fontsize=7, labelcolor=FG, facecolor=PANEL, edgecolor=GRID)

  ax_acc.set_ylabel("accel m/s²"); ax_acc.axhline(0, color=GRID, lw=0.8)
  acc_ln, = ax_acc.plot([], [], color=FG, lw=1.8, label="planned accel (throttle+/brake−)")
  ax_acc.legend(loc="upper left", fontsize=7, labelcolor=FG, facecolor=PANEL, edgecolor=GRID)
  ax_acc._fills = []
  gmax = [0.5]; bmax = [0.5]  # self-calibrated pedal maxima for %

  ax_str.set_ylabel("curvature 1/m"); ax_str.axhline(0, color=GRID, lw=0.8)
  ax_str.set_xlabel("t (s)")
  cur_ln, = ax_str.plot([], [], color="#d2a8ff", lw=1.8, label="desiredCurv")
  cca_ln, = ax_str.plot([], [], color=ACCENT, lw=1.2, label="carControl.curv")
  ax_str.legend(loc="upper left", fontsize=7, labelcolor=FG, facecolor=PANEL, edgecolor=GRID)

  txt = ax_txt.text(0.01, 0.5, "", color=FG, fontsize=12, family="monospace", va="center")

  def fmt(v, spec="{:.2f}"):
    return spec.format(v) if isinstance(v, (int, float)) else "—"

  def update(_):
    with lock:
      tr = latest["traj"]
      d = list(hist)
    # bird's-eye
    if tr is not None:
      px, py = tr.get("pos_x", []), tr.get("pos_y", [])
      if px and py:
        path_ln.set_data(py, px)                      # screen x = lateral(y), screen y = forward(x)
      probs = tr.get("laneLineProbs", [1, 1, 1, 1])
      for i, ln in enumerate(lane_lns):
        ll = tr.get("laneLines", [])
        if i < len(ll) and ll[i][0]:
          ln.set_data(ll[i][1], ll[i][0])
          ln.set_alpha(0.25 + 0.75 * (probs[i] if i < len(probs) else 1))
        else:
          ln.set_data([], [])
      for i, ln in enumerate(edge_lns):
        re = tr.get("roadEdges", [])
        ln.set_data(re[i][1], re[i][0]) if i < len(re) and re[i][0] else ln.set_data([], [])
    if d and d[-1]["leadStatus"] and d[-1]["dRel"] is not None:
      lead_pt.set_data([d[-1]["yRel"] or 0], [d[-1]["dRel"]])
    else:
      lead_pt.set_data([], [])

    # time series
    def setwin(ax, ln, key, ln2=None, key2=None):
      xs, ys = col(key); ln.set_data(xs, ys)
      if ln2 is not None:
        _, y2 = col(key2); ln2.set_data(xs, y2)
      if xs:
        ax.set_xlim(max(0, xs[-1] - args.window), max(args.window, xs[-1]))
      ax.relim(); ax.autoscale_view(scaley=True)
    setwin(ax_spd, spd_ln, "vEgo", set_ln, "vCruise")
    setwin(ax_acc, acc_ln, "accel")
    setwin(ax_str, cur_ln, "desCurv", cca_ln, "ccCurv")

    # throttle(green)/brake(red) fill under the planned-accel line
    xs, ys = col("accel")
    for c in ax_acc._fills:
      c.remove()
    ax_acc._fills = []
    if xs:
      ax_acc._fills = [
        ax_acc.fill_between(xs, 0, ys, where=[(y or 0) >= 0 for y in ys], color=THROT, alpha=0.22),
        ax_acc.fill_between(xs, 0, ys, where=[(y or 0) < 0 for y in ys], color=BRAKE, alpha=0.22),
      ]

    if d:
      r = d[-1]
      def onoff(b): return "ON " if b else "off"
      accel = r["accel"]
      if isinstance(accel, (int, float)):
        tb = f"THROTTLE {accel:+.2f}" if accel >= 0 else f"BRAKE    {accel:+.2f}"
      else:
        tb = "—"
      # self-calibrated pedal % (actual, from carState)
      g, b = r.get("gas"), r.get("brake")
      if isinstance(g, (int, float)):
        gmax[0] = max(gmax[0], g)
      if isinstance(b, (int, float)):
        bmax[0] = max(bmax[0], b)
      gp = f"{100*g/gmax[0]:.0f}%" if isinstance(g, (int, float)) else "—"
      bp = f"{100*b/bmax[0]:.0f}%" if isinstance(b, (int, float)) else "—"
      txt.set_text(
        f"engaged {onoff(r['enabled'])}   lat {onoff(r['latActive'])}   long {onoff(r['longActive'])}   "
        f"state={r['state']}\n"
        f"vEgo {fmt(r['vEgo'], '{:.1f}')} m/s    plan {tb} m/s²    "
        f"gas {gp}  brake {bp} (actual)    steerCmd {fmt(r['steer'])}    "
        f"angle {fmt(r['angle'], '{:.1f}')}°    desCurv {fmt(r['desCurv'], '{:.4f}')}")
    return [path_ln, *lane_lns, *edge_lns, lead_pt, spd_ln, set_ln, acc_ln, cur_ln, cca_ln, txt]

  if args.selftest:
    import math
    with lock:
      for i in range(120):
        t = i * 0.01
        hist.append({
          "t": t, "vEgo": 12 + 2 * math.sin(t), "vCruise": 15.0,
          "accel": 1.2 * math.sin(t * 1.5), "gas": 0.2, "brake": 0.0,
          "steer": 0.3 * math.sin(t), "angle": 6 * math.sin(t), "desAngle": 6 * math.sin(t),
          "ccCurv": 0.02 * math.sin(t), "desCurv": 0.022 * math.sin(t),
          "enabled": True, "latActive": True, "longActive": True, "state": "enabled",
          "dRel": 38.0, "yRel": -0.5, "leadStatus": True,
        })
      xs = [float(v) for v in range(0, 80, 2)]
      latest["traj"] = {
        "_upd": True, "pos_x": xs, "pos_y": [0.02 * v for v in xs],
        "laneLineProbs": [0.3, 0.99, 0.98, 0.4],
        "laneLines": [[xs, [w] * len(xs)] for w in (-5.4, -1.85, 1.85, 5.4)],
        "roadEdges": [[xs, [w] * len(xs)] for w in (-7.5, 7.5)],
      }
    update(0)
    out = "dashboard_selftest.png"
    fig.savefig(out, dpi=110, facecolor=BG)
    print("selftest OK ->", out)
    return

  from matplotlib.animation import FuncAnimation
  _a = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
  plt.show()


if __name__ == "__main__":
  main()
