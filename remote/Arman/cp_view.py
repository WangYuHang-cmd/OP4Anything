#!/usr/bin/env python3
"""cp_view.py — live view of the STÄHLE curvepoints while driving (laptop).

Left  : North-up ENU map (x=East right, y=North up, theta CCW) — exactly the client
        frame. Shows the ref origin, the ego + heading arrow, and the curvepoints laid
        by the distance rule, coloured by turn direction (left=green, right=orange,
        straight=grey). So you can eyeball the sign convention: turn the wheel left and
        the track bends counter-clockwise, DIR shows LEFT, kappa > 0.
Right : big tiles — HEADING theta, CURVATURE kappa + DIRECTION, RADIUS, VELOCITY,
        POS(E,N), #points + measured spacing. Header shows the ref lat/lon.
Top-left: freshness / delay indicator (LIVE age .. ms .. Hz).

Run alongside cp_export.py (they share frame.py / curvepoints.py):
    python3 cp_view.py --ip <comma_ip>
    python3 cp_view.py --ip <comma_ip> --mode record
Preview without a device:
    python3 cp_view.py --selftest        # writes cp_view_selftest.png
"""
import argparse
import collections
import math
import threading
import time

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec

import frame
import curvepoints as cp
from cp_export import model_to_enu, build_track, _valid_fix, HIST_TAIL, RECORD_MIN_MOVE

BG = "#0e1116"; PANEL = "#161b22"; GRID = "#243040"; FG = "#e6edf3"; MUTED = "#8b949e"
ACCENT = "#58a6ff"; LEFT = "#3fb950"; RIGHT = "#ffa657"; STRAIGHT = "#8b949e"
GOOD = "#3fb950"; BAD = "#f85149"; REFC = "#d2a8ff"
matplotlib.rcParams.update({
  "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
  "text.color": FG, "axes.edgecolor": PANEL,
})

state = {"rec": None, "loc": None, "origin": None, "hist": [], "route": [], "track": None,
         "ego": None, "theta": None}
stats = {"last_recv": 0.0, "t_wall": None, "recv": collections.deque(maxlen=120)}
lock = threading.Lock()


def dir_color(k):
  if abs(k) < 1.0 / 200.0:
    return STRAIGHT
  return LEFT if k > 0 else RIGHT


def _update_from_rec(rec, args):
  """Reader-side: keep origin/ego/track current (called under lock)."""
  loc = rec.get("loc")
  if loc:
    state["loc"] = loc
  last_loc = state["loc"]
  if state["origin"] is None:
    if args.ref_lat is not None and args.ref_lon is not None:
      state["origin"] = frame.ENUOrigin(args.ref_lat, args.ref_lon, args.ref_alt or 0.0)
    elif _valid_fix(last_loc):
      state["origin"] = frame.ENUOrigin(last_loc["lat"], last_loc["lon"], last_loc.get("alt", 0.0) or 0.0)
  origin = state["origin"]
  have_pose = origin is not None and _valid_fix(last_loc) and isinstance(last_loc.get("yaw"), (int, float))
  if not have_pose:
    return
  ego_e, ego_n, _ = origin.enu(last_loc["lat"], last_loc["lon"], last_loc.get("alt"))
  theta_veh = frame.yaw_ned_to_theta(last_loc["yaw"])
  ego_v = (last_loc.get("vel") or [0.0])[0] if isinstance(last_loc.get("vel"), list) else 0.0
  state["ego"] = (ego_e, ego_n)
  state["theta"] = theta_veh

  if args.mode == "record":
    route = state["route"]
    if not route or math.hypot(ego_e - route[-1][0], ego_n - route[-1][1]) >= RECORD_MIN_MOVE:
      route.append((ego_e, ego_n, max(ego_v, cp.V_FLOOR)))
    if len(route) >= 3:
      E = [p[0] for p in route]; N = [p[1] for p in route]; V = [p[2] for p in route]
      state["track"] = build_track(E, N, V, smooth=5)
    return

  # live
  hist = state["hist"]
  mv = rec.get("modelV2") or {}
  if mv.get("_upd") and mv.get("pos_x"):
    E, N, V = model_to_enu(mv, (ego_e, ego_n), theta_veh, hist=hist)
    if len(E) >= 3:
      state["track"] = build_track(E, N, V, smooth=0)
  else:
    if not hist or math.hypot(ego_e - hist[-1][0], ego_n - hist[-1][1]) >= 1.0:
      hist.append((ego_e, ego_n, max(ego_v, cp.V_FLOOR)))
      state["hist"][:] = hist[-HIST_TAIL:]


def reader(args):
  from stream_lib import stream
  for rec in stream(args.ip, args.port):
    now = time.monotonic()
    with lock:
      state["rec"] = rec
      _update_from_rec(rec, args)
      stats["last_recv"] = now
      stats["t_wall"] = rec.get("t_wall")
      stats["recv"].append(now)


def synthetic(args):
  origin = frame.ENUOrigin(37.7749295, -122.4194155, 0.0)
  state["origin"] = origin
  px = [float(i) for i in range(0, 60, 2)]
  py = [-0.015 * (x ** 2) for x in px]                 # bending left
  vx = [10.0] * len(px)
  theta_veh = frame.yaw_ned_to_theta(math.radians(30))  # arbitrary heading
  state["ego"] = (0.0, 0.0); state["theta"] = theta_veh
  E, N, V = model_to_enu({"pos_x": px, "pos_y": py, "vel_x": vx}, (0.0, 0.0), theta_veh)
  state["track"] = build_track(E, N, V)
  t = time.monotonic()
  stats["last_recv"] = t; stats["t_wall"] = time.time()
  stats["recv"].extend([t - 0.02, t - 0.01, t])


def tile(ax, label, value, sub="", color=FG, vsize=40):
  ax.clear(); ax.axis("off")
  ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=PANEL,
                             edgecolor=GRID, lw=1.2))
  ax.text(0.06, 0.80, label, transform=ax.transAxes, fontsize=14, color=MUTED, va="center")
  ax.text(0.06, 0.42, value, transform=ax.transAxes, fontsize=vsize, fontweight="bold",
          color=color, va="center")
  if sub:
    ax.text(0.06, 0.14, sub, transform=ax.transAxes, fontsize=13, color=MUTED, va="center")


def fnum(v, s="{:.1f}"):
  return s.format(v) if isinstance(v, (int, float)) else "—"


def nearest_idx(pts, ego):
  if not pts or ego is None:
    return 0
  return min(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - ego[0], pts[i][1] - ego[1]))


def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--ip"); ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--mode", choices=["live", "record"], default="live")
  ap.add_argument("--ref-lat", type=float, dest="ref_lat")
  ap.add_argument("--ref-lon", type=float, dest="ref_lon")
  ap.add_argument("--ref-alt", type=float, dest="ref_alt", default=0.0)
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()
  if not args.selftest and not args.ip:
    ap.error("--ip required (or --selftest)")

  if args.selftest:
    synthetic(args)
  else:
    threading.Thread(target=reader, args=(args,), daemon=True).start()

  fig = plt.figure(figsize=(15, 8.5))
  fig.canvas.manager.set_window_title("openpilot -> STAHLE curvepoints (live)")
  gs = gridspec.GridSpec(3, 3, width_ratios=[1.7, 0.6, 0.6], hspace=0.16, wspace=0.16,
                         left=0.06, right=0.98, top=0.90, bottom=0.08)
  ax_map = fig.add_subplot(gs[0:3, 0])
  ax_t = [fig.add_subplot(gs[r, c]) for r, c in [(0, 1), (0, 2), (1, 1), (1, 2), (2, 1), (2, 2)]]
  head = fig.text(0.5, 0.955, "", ha="center", fontsize=18, fontweight="bold", color=FG)
  delay_txt = fig.text(0.008, 0.988, "", ha="left", va="top", fontsize=13,
                       family="monospace", color=MUTED)

  ax_map.set_aspect("equal", adjustable="box")
  ax_map.set_facecolor("#0a1020"); ax_map.tick_params(colors=MUTED, labelsize=10)
  ax_map.set_xlabel("East  x [m]", color=MUTED); ax_map.set_ylabel("North  y [m]", color=MUTED)
  track_ln, = ax_map.plot([], [], color=GRID, lw=1.5, zorder=2)
  scat = ax_map.scatter([], [], s=26, zorder=3)
  ref_pt, = ax_map.plot([0], [0], marker="o", mfc="none", mec=REFC, ms=16, mew=2, zorder=4)
  ref_txt = ax_map.text(0, 0, " ref", color=REFC, fontsize=10, va="center")
  ego_arrow = [None]

  def update(_):
    with lock:
      track = state["track"]; ego = state["ego"]; theta = state["theta"]
      origin = state["origin"]
      lr = stats["last_recv"]; tw = stats["t_wall"]; rt = list(stats["recv"])

    now_m = time.monotonic()
    if lr:
      age = (now_m - lr) * 1000.0
      hz = (len(rt) - 1) / (rt[-1] - rt[0]) if len(rt) > 1 and rt[-1] > rt[0] else 0.0
      e2e = (time.time() - tw) * 1000.0 if isinstance(tw, (int, float)) else None
      live = age < 400
      e2e_s = (f"  e2e {e2e:.0f}ms" if e2e is not None and -500 < e2e < 3000 else "")
      delay_txt.set_text(f"{'● LIVE' if live else '○ STALE'}  age {age:.0f}ms  {hz:.0f}Hz{e2e_s}")
      delay_txt.set_color(GOOD if live else BAD)
    else:
      delay_txt.set_text("○ waiting for data…"); delay_txt.set_color(MUTED)

    reflatlon = (f"REF  {origin.lat:.6f}, {origin.lon:.6f}" if origin else "REF  (waiting for GPS fix)")
    head.set_text(f"openpilot → STÄHLE curvepoints (ENU, North-up)      {reflatlon}")

    if track and track["pts"]:
      pts = track["pts"]; ka = track["kappas"]; th = track["thetas"]
      xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
      track_ln.set_data(xs, ys)
      scat.set_offsets(list(zip(xs, ys)))
      scat.set_color([dir_color(k) for k in ka])

      # view window around ego (fallback: around track)
      cx = ego[0] if ego else sum(xs) / len(xs)
      cy = ego[1] if ego else sum(ys) / len(ys)
      span = max(30.0, max(xs) - min(xs), max(ys) - min(ys)) * 0.6 + 8.0
      ax_map.set_xlim(cx - span, cx + span); ax_map.set_ylim(cy - span, cy + span)
      ref_txt.set_position((1.0, 1.0))

      if ego is not None and theta is not None:
        if ego_arrow[0] is not None:
          ego_arrow[0].remove()
        al = span * 0.14
        ego_arrow[0] = ax_map.annotate("", xy=(ego[0] + al * math.cos(theta), ego[1] + al * math.sin(theta)),
                                       xytext=(ego[0], ego[1]),
                                       arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=2.4), zorder=6)

      # read curvature a bit AHEAD of ego (endpoints have kappa=0 by construction),
      # so the tile reflects the upcoming bend shown on the map
      ne = nearest_idx(pts, ego)
      fwd = len(pts) - ne
      i = min(len(pts) - 2, max(1, ne + max(2, fwd // 4)))
      k = ka[i]; v = pts[i][2]
      direction = "STRAIGHT" if abs(k) < 1.0 / 200.0 else ("LEFT" if k > 0 else "RIGHT")
      dcol = dir_color(k)
      radius = 1.0 / abs(k) if abs(k) > 1e-4 else float("inf")
      gaps = [math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]) for j in range(1, len(pts))]
      spac = sum(gaps) / len(gaps) if gaps else 0.0

      tile(ax_t[0], "HEADING θ  deg", fnum(math.degrees(theta) if theta is not None else None),
           sub="East=0, CCW+")
      tile(ax_t[1], "CURVATURE κ  1/m", fnum(k, "{:+.4f}"), sub=f"DIR: {direction}", color=dcol)
      tile(ax_t[2], "RADIUS  m", ("∞" if radius == float("inf") else fnum(radius, "{:.1f}")),
           sub="1/|κ|", color=dcol)
      tile(ax_t[3], "VELOCITY", fnum(v * 3.6, "{:.1f}"), sub=f"kph  ({fnum(v)} m/s)")
      tile(ax_t[4], "POS  E,N  m", f"{fnum(ego[0]) if ego else '—'}, {fnum(ego[1]) if ego else '—'}",
           sub="from ref origin")
      tile(ax_t[5], "#POINTS", str(len(pts)), sub=f"spacing {fnum(spac)} m")
    else:
      for j, lbl in enumerate(["HEADING θ", "CURVATURE κ", "RADIUS", "VELOCITY", "POS E,N", "#POINTS"]):
        tile(ax_t[j], lbl, "—")

    return []

  if args.selftest:
    update(0)
    fig.savefig("cp_view_selftest.png", dpi=110, facecolor=BG)
    print("selftest OK -> cp_view_selftest.png")
    return

  from matplotlib.animation import FuncAnimation
  _an = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
  plt.show()


if __name__ == "__main__":
  main()
