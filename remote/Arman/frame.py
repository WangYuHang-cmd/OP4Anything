#!/usr/bin/env python3
"""frame.py — coordinate & sign transforms: openpilot → STÄHLE TrackDriver frame.

Pure stdlib (math only) — no numpy, no openpilot C extensions — so it runs on any
laptop that only has the reg_export TCP stream.

Frames
------
openpilot Calibrated/Car frame (what modelV2.position is in, per
common/transformations/README):   x = Forward, y = Right, z = Down.
openpilot localizer heading:       loc.yaw = calibratedOrientationNED[2], NED yaw
                                   (0 = North, +toward East, i.e. clockwise-from-above).

STÄHLE / client ENU frame (target, from the CP Definition PDF + the client's engineer):
  x = East (theta = 0), y = North (theta = +pi/2), theta CCW-positive, kappa left-positive.
  origin (0,0) = a reference lat/lon fixed once at mission start (WGS84).

Derived transforms (verified against the PDF sign convention):
  theta_stahle = pi/2 - yaw_ned          # North(yaw0)->pi/2, East(yaw pi/2)->0
  E = E0 + fx*cos(th) + fy*sin(th)        # fx = forward, fy = right, th = vehicle theta
  N = N0 + fx*sin(th) - fy*cos(th)
Curvature is NOT taken from the car frame; it is recomputed in ENU (see curvepoints.py)
so that a left (CCW) turn is naturally positive, matching STÄHLE "left turn is positive".
"""
import math

# WGS84 ellipsoid
_A = 6378137.0                      # semi-major axis [m]
_F = 1.0 / 298.257223563           # flattening
_E2 = _F * (2.0 - _F)              # first eccentricity squared


def geodetic2ecef(lat_deg, lon_deg, alt=0.0):
  """WGS84 geodetic (deg, deg, m) -> ECEF (m,m,m)."""
  lat = math.radians(lat_deg)
  lon = math.radians(lon_deg)
  sin_lat, cos_lat = math.sin(lat), math.cos(lat)
  n = _A / math.sqrt(1.0 - _E2 * sin_lat * sin_lat)
  x = (n + alt) * cos_lat * math.cos(lon)
  y = (n + alt) * cos_lat * math.sin(lon)
  z = (n * (1.0 - _E2) + alt) * sin_lat
  return x, y, z


def ecef2enu(ecef, ref_lat_deg, ref_lon_deg, ref_ecef):
  """ECEF point -> local ENU (East, North, Up) about a reference geodetic point."""
  lat = math.radians(ref_lat_deg)
  lon = math.radians(ref_lon_deg)
  sin_lat, cos_lat = math.sin(lat), math.cos(lat)
  sin_lon, cos_lon = math.sin(lon), math.cos(lon)
  dx = ecef[0] - ref_ecef[0]
  dy = ecef[1] - ref_ecef[1]
  dz = ecef[2] - ref_ecef[2]
  e = -sin_lon * dx + cos_lon * dy
  n = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
  u = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
  return e, n, u


class ENUOrigin:
  """A fixed WGS84 reference point; converts geodetic -> (East, North, Up) [m].

  The origin is set ONCE (mission start) and never changed, per the STÄHLE spec.
  """
  def __init__(self, ref_lat, ref_lon, ref_alt=0.0):
    self.lat = ref_lat
    self.lon = ref_lon
    self.alt = ref_alt
    self._ecef = geodetic2ecef(ref_lat, ref_lon, ref_alt)

  def enu(self, lat, lon, alt=None):
    if alt is None:
      alt = self.alt
    return ecef2enu(geodetic2ecef(lat, lon, alt), self.lat, self.lon, self._ecef)


def wrap_pi(a):
  """Wrap an angle to (-pi, pi]."""
  a = math.fmod(a + math.pi, 2.0 * math.pi)
  if a <= 0.0:
    a += 2.0 * math.pi
  return a - math.pi


def yaw_ned_to_theta(yaw_ned):
  """openpilot NED yaw (0=North, +toward East) -> STÄHLE theta (0=East, CCW+)."""
  return wrap_pi(math.pi / 2.0 - yaw_ned)


def car_point_to_enu(fx, fy, e0, n0, theta_veh):
  """Car-frame point (fx=Forward, fy=Right) at vehicle pose (e0,n0,theta_veh) -> ENU (E,N).

  Right is 90deg clockwise from Forward, hence the (sin, -cos) column.
  """
  c, s = math.cos(theta_veh), math.sin(theta_veh)
  e = e0 + fx * c + fy * s
  n = n0 + fx * s - fy * c
  return e, n


# ---------- unit tests ----------
def _tests():
  ok = True

  def chk(name, cond):
    nonlocal ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond

  # geodetic2enu at the reference itself -> (0,0,0)
  o = ENUOrigin(37.7749295, -122.4194155, 0.0)
  e, n, u = o.enu(37.7749295, -122.4194155, 0.0)
  chk("enu(ref)=0", abs(e) < 1e-6 and abs(n) < 1e-6 and abs(u) < 1e-6)

  # 1 arc-second of latitude north ~ 30.9 m north, ~0 east
  e2, n2, _ = o.enu(37.7749295 + 1.0 / 3600.0, -122.4194155)
  chk("+1'' lat -> ~+30.8m North", abs(e2) < 0.5 and 30.0 < n2 < 31.5)
  # a bit of longitude east -> positive East, ~0 north
  e3, n3, _ = o.enu(37.7749295, -122.4194155 + 1.0 / 3600.0)
  chk("+1'' lon -> +East, ~0 North", e3 > 20.0 and abs(n3) < 0.5)

  # yaw -> theta
  chk("yaw 0 (N) -> theta pi/2", abs(yaw_ned_to_theta(0.0) - math.pi / 2) < 1e-9)
  chk("yaw pi/2 (E) -> theta 0", abs(yaw_ned_to_theta(math.pi / 2)) < 1e-9)
  chk("yaw -pi/2 (W) -> theta pi", abs(abs(yaw_ned_to_theta(-math.pi / 2)) - math.pi) < 1e-9)
  chk("yaw pi (S) -> theta -pi/2", abs(yaw_ned_to_theta(math.pi) + math.pi / 2) < 1e-9)

  # car -> ENU: facing North (theta=pi/2), forward adds North, right adds East
  th = math.pi / 2
  e, n = car_point_to_enu(10.0, 0.0, 0.0, 0.0, th)
  chk("N-facing forward -> +N", abs(e) < 1e-9 and abs(n - 10.0) < 1e-9)
  e, n = car_point_to_enu(0.0, 3.0, 0.0, 0.0, th)
  chk("N-facing right -> +E", abs(e - 3.0) < 1e-9 and abs(n) < 1e-9)
  # facing East (theta=0), forward adds East, right adds South (-North)
  e, n = car_point_to_enu(10.0, 2.0, 0.0, 0.0, 0.0)
  chk("E-facing fwd->+E, right->-N", abs(e - 10.0) < 1e-9 and abs(n + 2.0) < 1e-9)

  print("ALL FRAME TESTS OK" if ok else "FRAME TESTS FAILED")
  return ok


if __name__ == "__main__":
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--test", action="store_true")
  a = ap.parse_args()
  if a.test:
    raise SystemExit(0 if _tests() else 1)
  print(__doc__)
