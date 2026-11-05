#!/usr/bin/env python3
"""objstop_view v2 — laptop status board for the vision stop daemon.

Answers two questions at a glance, per the user's spec:
  1. WHAT IS DETECTED right now — three fixed tiles (STOP SIGN / TRAFFIC LIGHT /
     PEDESTRIAN), each always visible: NOT DETECTED / TRACKING d / LATCHED / WAIVED,
     light colour shown as a dot + word (never colour alone).
  2. WHAT HAPPENS NEXT — a hero ACTION banner (the daemon's current action) plus a
     NEXT line (the exact condition for the next transition).

Pulls /tmp/objstop_status.json (+ /tmp/objstop_last.jpg) from the device over SSH.
Run objstopd with --save-every 0.3 for the camera panel.

    python3 objstop_view.py --ip 192.168.1.231
    python3 objstop_view.py --selftest          # renders objstop_view_selftest.png
"""
import argparse
import json
import os
import subprocess
import tempfile
import time

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec

# dark board (single committed mode — in-car use), reference palette roles
PAGE = "#0d0d0d"; TILE = "#1a1a19"; HAIR = "#2c2c2a"; RING = (1, 1, 1, 0.10)
INK = "#ffffff"; INK2 = "#c3c2b7"; MUTED = "#898781"
GOOD = "#0ca30c"; WARN = "#fab219"; SERIOUS = "#ec835a"; CRIT = "#d03b3b"
matplotlib.rcParams.update({
  "figure.facecolor": PAGE, "axes.facecolor": TILE, "savefig.facecolor": PAGE,
  "text.color": INK, "axes.edgecolor": TILE,
  "font.family": ["DejaVu Sans", "sans-serif"],
})

LEVEL = {"ok": GOOD, "info": INK2, "prompt": SERIOUS, "danger": CRIT}
LEVEL_ICON = {"ok": "▶", "info": "●", "prompt": "■", "danger": "■"}  # ▶ ● ■ ■


def pull(ip, user, remote, local):
  try:
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=4",
                    f"{user}@{ip}", f"cat {remote}"],
                   stdout=open(local, "wb"), stderr=subprocess.DEVNULL, timeout=8, check=True)
    return os.path.getsize(local) > 0
  except Exception:
    return False


def tile_panel(ax, name, dot_color, state_word, value, sub, stripe):
  """One detection tile: status stripe + name + colored dot + state word + value + sub."""
  ax.clear(); ax.axis("off")
  ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=TILE,
                             edgecolor=RING, lw=1))
  ax.add_patch(plt.Rectangle((0, 0), 0.012, 1, transform=ax.transAxes,
                             facecolor=stripe, edgecolor="none"))
  ax.text(0.06, 0.84, name, transform=ax.transAxes, fontsize=13, color=MUTED, va="center")
  ax.text(0.06, 0.60, "●", transform=ax.transAxes, fontsize=15, color=dot_color, va="center")
  ax.text(0.115, 0.60, state_word, transform=ax.transAxes, fontsize=14, fontweight="bold",
          color=INK2, va="center")
  ax.text(0.06, 0.33, value, transform=ax.transAxes, fontsize=25, fontweight="bold",
          color=INK, va="center")
  if sub:
    ax.text(0.06, 0.10, sub, transform=ax.transAxes, fontsize=11.5, color=MUTED, va="center")


def detection_tiles(st):
  """status json -> the three fixed tiles' contents."""
  tracks = st.get("tracks") or {}
  dets = st.get("dets") or []

  def track_tile(key):
    tr = tracks.get(key)
    if not tr:
      return MUTED, "NOT DETECTED", "—", "", HAIR
    if tr.get("waived"):
      return WARN, "WAIVED", f"{tr['d']:.0f} m", "dilemma zone — passing", WARN
    if tr.get("latched"):
      return SERIOUS, "LATCHED", f"{tr['d']:.0f} m", "stop target armed", SERIOUS
    return INK2, "TRACKING", f"{tr['d']:.0f} m", f"{tr.get('hits', 0)} hits · confirming", HAIR

  sign = track_tile("stop_sign")

  tr = tracks.get("red_light")
  light_colors = [d.get("color") for d in dets if d.get("name") == "traffic light" and d.get("color")]
  if tr:
    col = {"red": CRIT, "green": GOOD, "yellow": WARN}.get(
      (light_colors or ["red"])[0], CRIT)
    word = (light_colors or ["RED"])[0].upper()
    light = (col, word, f"{tr['d']:.0f} m",
             "stop target armed" if tr.get("latched") else f"{tr.get('hits', 0)} hits · confirming",
             SERIOUS if tr.get("latched") else HAIR)
  elif light_colors:
    c = light_colors[0]
    col = {"red": CRIT, "green": GOOD, "yellow": WARN}.get(c, INK2)
    light = (col, c.upper(), "seen", "colour only (wide cam)", HAIR)
  else:
    light = (MUTED, "NOT DETECTED", "—", "", HAIR)

  persons = [d for d in dets if d.get("name") == "person"]
  if st.get("ped_hold"):
    ped = (CRIT, "IN PATH", "STOP", "holding until clear", CRIT)
  elif persons:
    ped = (INK2, "SEEN", f"{len(persons)}", "outside the stop zone", HAIR)
  else:
    ped = (MUTED, "NOT DETECTED", "—", "", HAIR)
  return sign, light, ped


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip")
  ap.add_argument("--user", default="comma")
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()
  if not args.selftest and not args.ip:
    ap.error("--ip required (or --selftest)")

  d = tempfile.mkdtemp()
  jpg = os.path.join(d, "f.jpg"); js = os.path.join(d, "s.json")

  fig = plt.figure(figsize=(15, 8.2))
  fig.canvas.manager.set_window_title("vision stop — detections & next action")
  gs = gridspec.GridSpec(4, 2, width_ratios=[1.45, 1.0], height_ratios=[1, 1, 1, 0.34],
                         hspace=0.14, wspace=0.10, left=0.025, right=0.978, top=0.80, bottom=0.03)
  ax_img = fig.add_subplot(gs[0:3, 0]); ax_img.axis("off")
  ax_sign = fig.add_subplot(gs[0, 1])
  ax_light = fig.add_subplot(gs[1, 1])
  ax_ped = fig.add_subplot(gs[2, 1])
  ax_foot = fig.add_subplot(gs[3, 0:2])

  hero = fig.text(0.03, 0.935, "", fontsize=30, fontweight="bold", va="center")
  nxt = fig.text(0.03, 0.858, "", fontsize=15, color=INK2, va="center")
  mode_chip = fig.text(0.975, 0.935, "", fontsize=14, fontweight="bold", ha="right", va="center")

  def update(_):
    st = {}
    if args.selftest:
      st = {"t": time.time(), "state": "BRAKING", "reason": "red_light", "armed": False,
            "action": "BRAKING — RED LIGHT, stop in 14 m",
            "next": "resume when green confirmed", "level": "prompt",
            "v_ego": 5.2, "infer_ms": 187.0, "alert": "",
            "ped_hold": False,
            "tracks": {"stop_sign": None,
                       "red_light": {"d": 24.0, "hits": 12, "latched": True, "waived": False}},
            "dets": [{"name": "traffic light", "color": "red", "conf": 0.78},
                     {"name": "person", "color": None, "conf": 0.6}]}
    else:
      if pull(args.ip, args.user, "/tmp/objstop_status.json", js):
        try:
          st = json.load(open(js))
        except Exception:
          st = {}
      pull(args.ip, args.user, "/tmp/objstop_last.jpg", jpg)

    # hero ACTION + NEXT
    level = st.get("level", "info")
    col = LEVEL.get(level, INK2)
    action = st.get("action") or ("waiting for daemon…" if not st else st.get("state", ""))
    hero.set_text(f"{LEVEL_ICON.get(level, '●')}  {action}")
    hero.set_color(col if level != "info" else INK)
    nxt.set_text(f"NEXT:  {st.get('next', '')}" if st.get("next") else "")
    armed = st.get("armed")
    mode_chip.set_text("■ ARMED — will brake" if armed else "○ SHADOW — not braking")
    mode_chip.set_color(CRIT if armed else MUTED)

    # camera
    if os.path.exists(jpg) and os.path.getsize(jpg) > 0:
      try:
        import matplotlib.image as mpimg
        img = mpimg.imread(jpg)
        ax_img.clear(); ax_img.axis("off"); ax_img.imshow(img)
        ax_img.set_title("road camera (detection boxes)", fontsize=11, color=MUTED, loc="left")
      except Exception:
        pass
    else:
      ax_img.clear(); ax_img.axis("off")
      ax_img.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax_img.transAxes,
                                     facecolor=TILE, edgecolor=RING))
      ax_img.text(0.5, 0.5, "no camera frame\n(run objstopd with --save-every 0.3)",
                  transform=ax_img.transAxes, ha="center", va="center", color=MUTED, fontsize=13)

    # three fixed detection tiles
    sign, light, ped = detection_tiles(st)
    tile_panel(ax_sign, "STOP SIGN", *sign)
    tile_panel(ax_light, "TRAFFIC LIGHT", *light)
    tile_panel(ax_ped, "PEDESTRIAN", *ped)

    # footer: freshness + telemetry + alert
    ax_foot.clear(); ax_foot.axis("off")
    ax_foot.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax_foot.transAxes,
                                    facecolor=TILE, edgecolor=RING))
    age = (time.time() - st["t"]) if st.get("t") else None
    live = age is not None and age < 1.5
    ax_foot.text(0.015, 0.5, ("● LIVE" if live else "○ STALE") +
                 (f"  {age*1000:.0f} ms" if age is not None else ""),
                 transform=ax_foot.transAxes, fontsize=13, fontweight="bold",
                 color=GOOD if live else CRIT, va="center")
    ax_foot.text(0.18, 0.5, f"v {st.get('v_ego', '—')} m/s    infer {st.get('infer_ms', '—')} ms    "
                 f"state {st.get('state', '—')}",
                 transform=ax_foot.transAxes, fontsize=12.5, color=INK2, va="center")
    if st.get("alert"):
      ax_foot.text(0.985, 0.5, f"⚠ {st['alert']}", transform=ax_foot.transAxes,
                   fontsize=12.5, fontweight="bold", color=WARN, ha="right", va="center")
    return []

  if args.selftest:
    update(0)
    fig.savefig("objstop_view_selftest.png", dpi=110, facecolor=PAGE)
    print("selftest OK -> objstop_view_selftest.png")
    return

  from matplotlib.animation import FuncAnimation
  _an = FuncAnimation(fig, update, interval=400, cache_frame_data=False)
  plt.show()


if __name__ == "__main__":
  main()
