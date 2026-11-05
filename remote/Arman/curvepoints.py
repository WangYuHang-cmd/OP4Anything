#!/usr/bin/env python3
"""curvepoints.py — turn an ENU polyline into STÄHLE curvepoints / segments.

All geometry is in the STÄHLE / client ENU frame (x = East, y = North, theta CCW
from East, kappa LEFT-turn-positive). See frame.py for how openpilot data is brought
into this frame.

Pipeline (per the CP Definition of Curvepoints PDF):
  1. resample_by_distance_rule : lay points at spacing d = clip(v*0.3, 0.6, 5) m.
  2. theta_kappa               : theta = atan2(dN, dE) in +-pi; kappa via the PDF
                                 formula, recomputed in ENU so left turns are positive.
  3a. to_stahle_rows           : the native STÄHLE per-point columns.
  3b. to_segments              : the client's internal line/arc segment JSON.

Pure stdlib.
"""
import math

DSDV = 0.3          # spacing = v[kph]/3.6 * dsdv = v_mps * dsdv
D_MIN = 0.6         # m
D_MAX = 5.0         # m
V_FLOOR = 0.3       # m/s floor so velocity is strictly > 0 (spec: else vehicle stands still)


def _cumlen(E, N):
  s = [0.0]
  for i in range(1, len(E)):
    s.append(s[-1] + math.hypot(E[i] - E[i - 1], N[i] - N[i - 1]))
  return s


def spacing_for(v_mps):
  """Distance rule: d = clip(v_mps * 0.3, 0.6, 5.0) metres."""
  return min(D_MAX, max(D_MIN, v_mps * DSDV))


def _interp(E, N, V, s_cum, s_target):
  """Linear-interpolate (E,N,v) at arc-length s_target along the polyline."""
  if s_target <= 0:
    return E[0], N[0], V[0]
  if s_target >= s_cum[-1]:
    return E[-1], N[-1], V[-1]
  # find segment containing s_target
  lo, hi = 0, len(s_cum) - 1
  while lo + 1 < hi:
    mid = (lo + hi) // 2
    if s_cum[mid] <= s_target:
      lo = mid
    else:
      hi = mid
  seg = s_cum[hi] - s_cum[lo]
  t = 0.0 if seg < 1e-9 else (s_target - s_cum[lo]) / seg
  return (E[lo] + t * (E[hi] - E[lo]),
          N[lo] + t * (N[hi] - N[lo]),
          V[lo] + t * (V[hi] - V[lo]))


def resample_by_distance_rule(E, N, V):
  """Resample an ENU polyline at variable spacing set by the local speed.

  Returns [(E, N, v), ...] with arc-length gaps = clip(v*0.3, 0.6, 5) m.
  """
  n = len(E)
  if n == 0:
    return []
  if n == 1:
    return [(E[0], N[0], max(V[0], V_FLOOR))]
  s_cum = _cumlen(E, N)
  total = s_cum[-1]
  out = []
  s = 0.0
  guard = 0
  while s <= total + 1e-6 and guard < 100000:
    guard += 1
    e, nn, v = _interp(E, N, V, s_cum, s)
    v = max(v, V_FLOOR)
    out.append((e, nn, v))
    step = spacing_for(v)
    s += step
  # always include the final point so the track reaches its end
  el, nl, vl = E[-1], N[-1], max(V[-1], V_FLOOR)
  if not out or math.hypot(out[-1][0] - el, out[-1][1] - nl) > 1e-3:
    out.append((el, nl, vl))
  return out


def _signed_kappa(p0, p1, p2):
  """Signed curvature through 3 ENU points; >0 = CCW = LEFT turn (STÄHLE convention)."""
  ax, ay = p1[0] - p0[0], p1[1] - p0[1]
  bx, by = p2[0] - p1[0], p2[1] - p1[1]
  a = math.hypot(ax, ay)
  b = math.hypot(bx, by)
  c = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
  if a < 1e-6 or b < 1e-6 or c < 1e-6:
    return 0.0
  cross = ax * by - ay * bx        # >0 = left/CCW in (East, North)
  return 2.0 * cross / (a * b * c)


def _movavg(x, w):
  if w <= 1 or len(x) < 3:
    return list(x)
  half = w // 2
  out = []
  for i in range(len(x)):
    lo = max(0, i - half)
    hi = min(len(x), i + half + 1)
    out.append(sum(x[lo:hi]) / (hi - lo))
  return out


def theta_kappa(E, N, smooth=0, kappa_straight=1.0 / 200.0):
  """Heading and signed curvature along the ENU points.

  theta = atan2(dN, dE) in (-pi, pi]; kappa left-positive.
  smooth>0 applies a moving average to E,N first (use for raw GPS; the PDF asks for
  filtering). Near-straight points (|kappa| < kappa_straight) are snapped to 0 so a
  straight->arc threshold point uses the straight's curvature (PDF tip).
  """
  if smooth and smooth > 1:
    E = _movavg(E, smooth)
    N = _movavg(N, smooth)
  n = len(E)
  thetas, kappas = [], []
  for i in range(n):
    if n == 1:
      thetas.append(0.0)
    elif i == 0:
      thetas.append(math.atan2(N[1] - N[0], E[1] - E[0]))
    elif i == n - 1:
      thetas.append(math.atan2(N[i] - N[i - 1], E[i] - E[i - 1]))
    else:
      thetas.append(math.atan2(N[i + 1] - N[i - 1], E[i + 1] - E[i - 1]))
    if 0 < i < n - 1:
      k = _signed_kappa((E[i - 1], N[i - 1]), (E[i], N[i]), (E[i + 1], N[i + 1]))
    else:
      k = 0.0
    kappas.append(0.0 if abs(k) < kappa_straight else k)
  return thetas, kappas


def to_stahle_rows(pts, thetas, kappas):
  """STÄHLE "10000" columns per point:
  [Deltatime_s, velocity_kph, gear, index, PositionX_East, PositionY_North,
   theta_rad, kappa_1pm, long_accel]  (long_accel fixed 0 -> recalculated by TrackDriver).
  """
  rows = []
  prev = None
  for i, (e, n, v) in enumerate(pts):
    v = max(v, V_FLOOR)
    if prev is None:
      dt = 0.0
    else:
      ds = math.hypot(e - prev[0], n - prev[1])
      dt = ds / v if v > 1e-6 else 0.0
    rows.append([round(dt, 4), round(v * 3.6, 3), 99, i,
                 round(e, 4), round(n, 4), round(thetas[i], 6),
                 round(kappas[i], 6), 0.0])
    prev = (e, n)
  return rows


STAHLE_HEADER = ["Deltatime_s", "velocity_kph", "gear", "index",
                 "PositionX_East_m", "PositionY_North_m", "theta_rad",
                 "kappa_1pm", "long_accel_mss"]


def to_segments(pts, kappas, kappa_straight=1.0 / 200.0, min_run=3):
  """Decompose the resampled ENU points into line/arc segments (client internal format).

  Each segment: {start:{x,y}, end:{x,y}, velocity(m/s), radius(m, 0=straight),
  direction("left"/"right")}. Runs shorter than min_run points are merged into their
  neighbour so noisy kappa near the straight threshold doesn't fragment the track.
  The final segment's velocity is 0.0 when the plan ends at (floored) standstill,
  matching the client convention "velocity 0 at the end = stop there".
  This is an approximation of a proper spline fit — the client's own wrapper is
  authoritative; kept simple and sign-correct here.
  """
  if len(pts) < 2:
    return []

  def cls(k):
    if abs(k) < kappa_straight:
      return "straight"
    return "left" if k > 0 else "right"

  labels = [cls(k) for k in kappas]

  # merge runs shorter than min_run into the previous run's label (next run's at start)
  if min_run > 1 and len(labels) > min_run:
    runs = []                    # [start_idx, label]
    for i, lb in enumerate(labels):
      if not runs or runs[-1][1] != lb:
        runs.append([i, lb])
    changed = True
    while changed and len(runs) > 1:
      changed = False
      for j, (st, lb) in enumerate(runs):
        end = runs[j + 1][0] if j + 1 < len(runs) else len(labels)
        if end - st < min_run:
          new_lb = runs[j - 1][1] if j > 0 else runs[j + 1][1]
          for i in range(st, end):
            labels[i] = new_lb
          runs = []
          for i, lb2 in enumerate(labels):
            if not runs or runs[-1][1] != lb2:
              runs.append([i, lb2])
          changed = True
          break
  segs = []
  i = 0
  n = len(pts)
  while i < n - 1:
    # segments share their boundary point, so the run's label comes from the point
    # AFTER the boundary (else a 1-gap sliver of the previous label is emitted)
    label = labels[i + 1] if i + 1 < n else labels[i]
    j = i
    while j + 1 < n and labels[j + 1] == label:
      j += 1
    # segment spans points i..j (at least i..i+1)
    end = min(max(j, i + 1), n - 1)
    run_k = [abs(k) for k in kappas[i:end + 1] if abs(k) >= kappa_straight]
    if label == "straight" or not run_k:
      radius = 0.0
      direction = "left" if sum(kappas[i:end + 1]) >= 0 else "right"
    else:
      mean_k = sum(run_k) / len(run_k)
      radius = 1.0 / mean_k if mean_k > 1e-9 else 0.0
      direction = label
    vs = [p[2] for p in pts[i:end + 1]]
    segs.append({
      "start": {"x": round(pts[i][0], 4), "y": round(pts[i][1], 4)},
      "end": {"x": round(pts[end][0], 4), "y": round(pts[end][1], 4)},
      "velocity": round(sum(vs) / len(vs), 3),
      "radius": round(radius, 3),
      "direction": direction,
    })
    i = end
  # client convention: velocity 0.0 on the final segment = stop at the end
  if segs and segs[-1]["velocity"] <= V_FLOOR + 0.05:
    segs[-1]["velocity"] = 0.0
  return segs


# ---------- unit tests ----------
def _tests():
  ok = True

  def chk(name, cond):
    nonlocal ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond

  # straight line heading East
  E = [float(i) for i in range(0, 40, 2)]
  N = [0.0] * len(E)
  V = [10.0] * len(E)
  th, ka = theta_kappa(E, N)
  chk("straight: theta~0", all(abs(t) < 1e-6 for t in th))
  chk("straight: kappa~0", all(abs(k) < 1e-9 for k in ka))
  segs = to_segments(list(zip(E, N, V)), ka)
  chk("straight: one straight seg r=0", len(segs) == 1 and segs[0]["radius"] == 0.0)

  # LEFT / CCW arc, radius R, starting heading East
  R = 20.0
  ang = [i * 0.05 for i in range(40)]
  El = [R * math.sin(t) for t in ang]
  Nl = [R * (1 - math.cos(t)) for t in ang]
  Vl = [8.0] * len(El)
  thl, kal = theta_kappa(El, Nl)
  mid = kal[3:-3]
  chk("left arc: kappa>0 ~ +1/R", all(abs(k - 1.0 / R) < 0.003 for k in mid))
  segl = to_segments(list(zip(El, Nl, Vl)), kal)
  chk("left arc: direction=left", any(s["direction"] == "left" for s in segl))
  chk("left arc: radius~R", any(abs(s["radius"] - R) < 1.5 for s in segl if s["radius"] > 0))

  # RIGHT / CW arc (mirror in North)
  Nr = [-x for x in Nl]
  thr, kar = theta_kappa(El, Nr)
  midr = kar[3:-3]
  chk("right arc: kappa<0 ~ -1/R", all(abs(k + 1.0 / R) < 0.003 for k in midr))
  segr = to_segments(list(zip(El, Nr, Vl)), kar)
  chk("right arc: direction=right", any(s["direction"] == "right" for s in segr))

  # distance rule spacing
  chk("spacing v=1 -> 0.6 (floor)", abs(spacing_for(1.0) - 0.6) < 1e-9)
  chk("spacing v=10 -> 3.0", abs(spacing_for(10.0) - 3.0) < 1e-9)
  chk("spacing v=30 -> 5.0 (cap)", abs(spacing_for(30.0) - 5.0) < 1e-9)

  # resample a 100 m straight at v=10 -> gaps ~3.0 m
  Es = [float(i) for i in range(0, 101)]
  Ns = [0.0] * len(Es)
  Vs = [10.0] * len(Es)
  pts = resample_by_distance_rule(Es, Ns, Vs)
  gaps = [math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts) - 1)]
  chk("resample gaps ~3.0", all(abs(g - 3.0) < 1e-6 for g in gaps))

  # stahle rows shape + velocity>0 + kph
  rows = to_stahle_rows(pts, *theta_kappa([p[0] for p in pts], [p[1] for p in pts]))
  chk("stahle: 9 cols", all(len(r) == 9 for r in rows))
  chk("stahle: velocity_kph>0", all(r[1] > 0 for r in rows))
  chk("stahle: gear=99, index ok", rows[5][2] == 99 and rows[5][3] == 5)

  print("ALL CURVEPOINTS TESTS OK" if ok else "CURVEPOINTS TESTS FAILED")
  return ok


if __name__ == "__main__":
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--test", action="store_true")
  a = ap.parse_args()
  if a.test:
    raise SystemExit(0 if _tests() else 1)
  print(__doc__)
