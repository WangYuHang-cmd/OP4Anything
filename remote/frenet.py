#!/usr/bin/env python3
"""frenet.py — convert openpilot trajectories to vehicle-agnostic Frenet outputs.

Input: one modelV2 block from the reg_export stream (a frame where `_upd` is true),
containing the planned path (`pos_x`, `pos_y`), speed profile (`vel_x`) and lane
geometry (`laneLines`, `laneLineProbs`). All geometry is in the openpilot CAR frame:
x forward, y RIGHT, z down (so curvature kappa > 0 = turning right).

Two vehicle-agnostic representations are produced:

1) frenet_sd(mv)      -> [(s, d), ...]
   Trajectory expressed against a REFERENCE LINE (probability-weighted centerline of
   the inner lane lines; falls back to the path itself when lanes are missing).
   s = arc length along the reference line [m], d = signed lateral offset
   (**d > 0 = RIGHT of the reference**, matching the y-right car frame).

2) path_profile(mv)   -> [(s, x, y, theta, kappa, v, a), ...]
   The planned path itself parameterized by arc length:
   theta = heading vs x-axis [rad], kappa = curvature [1/m] (3-point Menger,
   >0 = right turn), v = planned speed [m/s], a = v * dv/ds [m/s^2].

Any downstream planner (e.g. a bus) can consume these directly — no Honda-specific
units are involved. Export with to_csv(). Run `python frenet.py --test` for the
built-in geometry unit tests.
"""
import math

MIN_LANE_PROB = 0.3


# ---------- geometry helpers ----------
def _arclength(xs, ys):
  s = [0.0]
  for i in range(1, len(xs)):
    s.append(s[-1] + math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]))
  return s


def _menger_curvature(p0, p1, p2):
  """Signed curvature through 3 points; >0 = turning toward +y (right)."""
  ax, ay = p1[0] - p0[0], p1[1] - p0[1]
  bx, by = p2[0] - p1[0], p2[1] - p1[1]
  a = math.hypot(ax, ay)
  b = math.hypot(bx, by)
  c = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
  if a < 1e-6 or b < 1e-6 or c < 1e-6:
    return 0.0
  cross = ax * by - ay * bx          # >0 = bending toward +y (right in car frame)
  return 2.0 * cross / (a * b * c)


def _project_point(px, py, ax, ay, bx, by):
  """Project P onto segment AB. Returns (t in [0,1], dist_signed, seg_len)."""
  vx, vy = bx - ax, by - ay
  L2 = vx * vx + vy * vy
  if L2 < 1e-12:
    return 0.0, math.hypot(px - ax, py - ay), 0.0
  t = ((px - ax) * vx + (py - ay) * vy) / L2
  t = max(0.0, min(1.0, t))
  cx, cy = ax + t * vx, ay + t * vy
  # signed lateral: cross(tangent, offset); >0 = P on +y (right) side of AB
  cross = vx * (py - cy) - vy * (px - cx)
  d = math.hypot(px - cx, py - cy)
  return t, math.copysign(d, cross) if d > 1e-12 else 0.0, math.sqrt(L2)


# ---------- reference line ----------
def reference_line(mv):
  """Probability-weighted centerline of the inner lane lines; fallback = path itself.

  Returns (xs, ys, source) with source in {"lane_center", "path"}.
  """
  lls = mv.get("laneLines") or []
  probs = mv.get("laneLineProbs") or []
  if len(lls) >= 3 and len(probs) >= 3:
    lx, ly = lls[1][0], lls[1][1]   # inner-left line
    rx, ry = lls[2][0], lls[2][1]   # inner-right line
    lp = probs[1] if len(probs) > 1 else 0.0
    rp = probs[2] if len(probs) > 2 else 0.0
    if lp > MIN_LANE_PROB and rp > MIN_LANE_PROB and len(lx) == len(rx) and len(lx) >= 2:
      xs = [(a + b) / 2.0 for a, b in zip(lx, rx)]
      ys = [(lp * a + rp * b) / (lp + rp) for a, b in zip(ly, ry)]
      return xs, ys, "lane_center"
  px, py = mv.get("pos_x") or [], mv.get("pos_y") or []
  return list(px), list(py), "path"


# ---------- representation 1: (s, d) vs reference ----------
def frenet_sd(mv, ref=None):
  """Trajectory as (s, d) against the reference line. Returns (list[(s,d)], source)."""
  px, py = mv.get("pos_x") or [], mv.get("pos_y") or []
  if len(px) < 2:
    return [], "none"
  if ref is None:
    rx, ry, source = reference_line(mv)
  else:
    rx, ry, source = ref[0], ref[1], "custom"
  if len(rx) < 2:
    return [], "none"
  ref_s = _arclength(rx, ry)
  out = []
  for x, y in zip(px, py):
    best = (1e18, 0.0, 0.0)   # (abs_d, s, d)
    for i in range(len(rx) - 1):
      t, d_signed, seg = _project_point(x, y, rx[i], ry[i], rx[i + 1], ry[i + 1])
      if abs(d_signed) < best[0]:
        best = (abs(d_signed), ref_s[i] + t * seg, d_signed)
    out.append((round(best[1], 3), round(best[2], 3)))
  return out, source


# ---------- representation 2: arc-length path profile ----------
def path_profile(mv):
  """Planned path as [(s, x, y, theta, kappa, v, a), ...] (vehicle-agnostic)."""
  px, py = mv.get("pos_x") or [], mv.get("pos_y") or []
  vx = mv.get("vel_x") or []
  n = len(px)
  if n < 3:
    return []
  s = _arclength(px, py)
  out = []
  for i in range(n):
    if i == 0:
      theta = math.atan2(py[1] - py[0], px[1] - px[0])
    else:
      theta = math.atan2(py[i] - py[i - 1], px[i] - px[i - 1])
    if 0 < i < n - 1:
      kappa = _menger_curvature((px[i - 1], py[i - 1]), (px[i], py[i]), (px[i + 1], py[i + 1]))
    else:
      kappa = 0.0
    v = vx[i] if i < len(vx) else (vx[-1] if vx else 0.0)
    # a = v * dv/ds (central difference on the s grid)
    if 0 < i < n - 1 and i < len(vx) - 1 and (s[i + 1] - s[i - 1]) > 1e-6:
      a = v * (vx[i + 1] - vx[i - 1]) / (s[i + 1] - s[i - 1])
    else:
      a = 0.0
    out.append((round(s[i], 3), round(px[i], 3), round(py[i], 3),
                round(theta, 5), round(kappa, 6), round(v, 3), round(a, 3)))
  return out


def to_csv(profile, path, sd=None):
  """Write the arc-length profile (and optionally (s,d)) to a CSV any planner can read."""
  with open(path, "w") as f:
    if sd:
      f.write("s,x,y,theta,kappa,v,a,s_ref,d_ref\n")
      for row, (sr, dr) in zip(profile, sd):
        f.write(",".join(str(v) for v in row) + f",{sr},{dr}\n")
    else:
      f.write("s,x,y,theta,kappa,v,a\n")
      for row in profile:
        f.write(",".join(str(v) for v in row) + "\n")


# ---------- unit tests ----------
def _tests():
  ok = True

  def chk(name, cond):
    nonlocal ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond

  # straight path, straight centered lanes -> d≈0, kappa≈0
  xs = [float(i) for i in range(0, 40, 2)]
  mv = {"pos_x": xs, "pos_y": [0.0] * len(xs), "vel_x": [10.0] * len(xs),
        "laneLines": [[xs, [-5.0] * len(xs)], [xs, [-1.8] * len(xs)],
                      [xs, [1.8] * len(xs)], [xs, [5.0] * len(xs)]],
        "laneLineProbs": [0.2, 0.9, 0.9, 0.2]}
  sd, src = frenet_sd(mv)
  prof = path_profile(mv)
  chk("straight: ref=lane_center", src == "lane_center")
  chk("straight: |d|<=0.01", all(abs(d) <= 0.01 for _, d in sd))
  chk("straight: |kappa|<=1e-6", all(abs(r[4]) <= 1e-6 for r in prof))
  chk("straight: s monotonic", all(b[0] > a[0] for a, b in zip(prof, prof[1:])))

  # path shifted 0.5 m to the RIGHT (+y) of lane center -> d ≈ +0.5
  mv2 = dict(mv); mv2["pos_y"] = [0.5] * len(xs)
  sd2, _ = frenet_sd(mv2)
  chk("offset right: d≈+0.5", all(abs(d - 0.5) < 0.05 for s, d in sd2 if 1 < s < 35))

  # circular arc R=20 turning right (+y): kappa ≈ +1/20
  R = 20.0
  ang = [i * 0.05 for i in range(30)]
  mv3 = {"pos_x": [R * math.sin(t) for t in ang],
         "pos_y": [R * (1 - math.cos(t)) for t in ang],
         "vel_x": [8.0] * 30, "laneLines": [], "laneLineProbs": []}
  prof3 = path_profile(mv3)
  mid = [r[4] for r in prof3[3:-3]]
  chk("arc R=20 right: kappa≈+0.05", all(abs(k - 1.0 / R) < 0.002 for k in mid))

  # decel profile: v from 10->4 over path, a should be negative mid-path
  mv4 = dict(mv); mv4["vel_x"] = [10.0 - 0.3 * i for i in range(len(xs))]
  prof4 = path_profile(mv4)
  chk("decel: a<0 mid-path", all(r[6] < 0 for r in prof4[2:-2]))

  print("ALL FRENET TESTS OK" if ok else "FRENET TESTS FAILED")
  return ok


if __name__ == "__main__":
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--test", action="store_true")
  a = ap.parse_args()
  if a.test:
    raise SystemExit(0 if _tests() else 1)
  print(__doc__)
