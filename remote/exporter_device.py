#!/usr/bin/env python3
"""reg_export/exporter.py — stream openpilot planning/control signals to a laptop.

Runs ON the comma device (sunnypilot 0.9.7.1). Subscribes read-only to the local
msgq (native, no bridge / no ZMQ), and every carState frame (~100 Hz) emits ONE
compact JSON line with the latest planning/control/feedback signals. Serves the
JSON-lines over TCP so a laptop on the same LAN (phone hotspot) can consume it for
logging, real-time downstream use, or visualization.

Design notes:
- READ-ONLY: msgq is a lock-free broadcast ring buffer; a subscriber cannot back-
  pressure openpilot, so this can NEVER affect the driving stack.
- Per-client bounded queue + sender thread: a slow laptop just drops old frames,
  it never stalls the sampling loop (no partial-write corruption either).
- Heavy arrays (modelV2 trajectory, longitudinalPlan speeds/accels) are only
  included on the frames where that 20 Hz service actually updated.

Run on device:
  cd /data/openpilot && PYTHONPATH=/data/openpilot \
    /usr/local/pyenv/versions/3.11.4/bin/python3 tools/reg_export/exporter.py
Options: --port 7700  --bind 0.0.0.0
"""
import argparse
import collections
import json
import math
import os
import socket
import threading
import time

# native msgq: make sure we do NOT force ZMQ and do NOT set a prefix (must match
# the running openpilot's default namespace to see its messages)
os.environ.pop("ZMQ", None)
os.environ.pop("OPENPILOT_PREFIX", None)

import cereal.messaging as messaging  # noqa: E402

SERVICES = ['carState', 'carControl', 'carOutput', 'controlsState',
            'longitudinalPlan', 'modelV2', 'liveLocationKalman', 'radarState',
            'liveParameters']

WHEELBASE = 2.70          # m, Honda Civic; used for desired-steering-angle derivation
DEFAULT_STEER_RATIO = 16.7

# fields we consider "heavy" (arrays) — only serialized when their service updated
HEAVY = {'modelV2', 'longitudinalPlan'}


def g(obj, attr, default=None):
  try:
    return getattr(obj, attr)
  except Exception:
    return default


def r(x, nd=3):
  try:
    return round(float(x), nd)
  except Exception:
    return None


def rl(seq, nd=3):
  try:
    return [round(float(v), nd) for v in seq]
  except Exception:
    return []


# ----- per-message extractors (0.9.7.1 field paths) -----
def ext_carState(cs):
  return {
    "vEgo": r(cs.vEgo, 4), "vEgoRaw": r(cs.vEgoRaw, 4), "aEgo": r(cs.aEgo, 4),
    "vCruise": r(g(cs, "vCruise"), 3), "yawRate": r(cs.yawRate, 5),
    "steeringAngleDeg": r(cs.steeringAngleDeg, 3), "steeringRateDeg": r(cs.steeringRateDeg, 3),
    "steeringTorque": r(cs.steeringTorque, 3), "steeringTorqueEps": r(cs.steeringTorqueEps, 3),
    "steeringPressed": bool(cs.steeringPressed),
    "gas": r(cs.gas, 3), "gasPressed": bool(cs.gasPressed),
    "brake": r(cs.brake, 3), "brakePressed": bool(cs.brakePressed),
    "standstill": bool(cs.standstill), "gear": str(g(cs, "gearShifter", "")),
    "leftBlinker": bool(cs.leftBlinker), "rightBlinker": bool(cs.rightBlinker),
    "cruiseEnabled": bool(cs.cruiseState.enabled), "cruiseSpeed": r(cs.cruiseState.speed, 3),
    "cruiseAvail": bool(cs.cruiseState.available),
  }


def ext_carControl(cc):
  a = cc.actuators
  return {
    "enabled": bool(cc.enabled), "latActive": bool(cc.latActive), "longActive": bool(cc.longActive),
    "steer": r(a.steer, 4), "steeringAngleDeg": r(a.steeringAngleDeg, 3),
    "curvature": r(a.curvature, 6), "accel": r(a.accel, 4),
    "longControlState": str(g(a, "longControlState", "")), "steerOutputCan": r(g(a, "steerOutputCan"), 4),
    "cancel": bool(cc.cruiseControl.cancel), "resume": bool(cc.cruiseControl.resume),
    "override": bool(cc.cruiseControl.override),
  }


def ext_carOutput(co):
  a = co.actuatorsOutput
  return {"steer": r(a.steer, 4), "steeringAngleDeg": r(a.steeringAngleDeg, 3),
          "curvature": r(g(a, "curvature"), 6), "accel": r(a.accel, 4),
          # final values as sent on the CAN bus (steerOutputCan: raw EPS torque units, ±4096 on Honda Bosch)
          "steerOutputCan": r(g(a, "steerOutputCan"), 1),
          "gas": r(g(a, "gas"), 4), "brake": r(g(a, "brake"), 4)}


def ext_liveParameters(lp):
  return {"steerRatio": r(g(lp, "steerRatio"), 3), "angleOffsetDeg": r(g(lp, "angleOffsetDeg"), 3),
          "stiffnessFactor": r(g(lp, "stiffnessFactor"), 3), "roll": r(g(lp, "roll"), 4),
          "valid": bool(g(lp, "valid", False))}


def ext_controlsState(cs):
  d = {
    "state": str(g(cs, "state", "")), "desiredCurvature": r(cs.desiredCurvature, 6),
    "curvature": r(cs.curvature, 6), "longControlState": str(g(cs, "longControlState", "")),
    "vCruise": r(g(cs, "vCruise"), 3),
    "upAccelCmd": r(g(cs, "upAccelCmd"), 4), "uiAccelCmd": r(g(cs, "uiAccelCmd"), 4),
    "ufAccelCmd": r(g(cs, "ufAccelCmd"), 4),
  }
  try:
    which = cs.lateralControlState.which()
    st = getattr(cs.lateralControlState, which)
    lat = {}
    for f in ("output", "saturated", "error", "p", "i", "d", "f", "steeringAngleDeg",
              "steeringAngleDesiredDeg", "actualLateralAccel", "desiredLateralAccel", "angleError"):
      if hasattr(st, f):
        v = getattr(st, f)
        lat[f] = bool(v) if isinstance(v, bool) else r(v, 4)
    d["latType"] = which
    d["lat"] = lat
  except Exception:
    pass
  return d


def ext_longitudinalPlan(lp, heavy):
  # 0.9.7.1: LongitudinalPlan carries the MPC solution (speeds/accels/jerks); there is
  # NO aTarget/shouldStop field (deprecated). Near-term planned accel = accels[0];
  # the actual commanded accel is carControl.accel.
  accels = list(lp.accels)
  speeds = list(lp.speeds)
  d = {"hasLead": bool(lp.hasLead), "source": str(g(lp, "longitudinalPlanSource", "")),
       "fcw": bool(lp.fcw),
       "aTarget0": r(accels[0], 4) if accels else None,
       "vTarget0": r(speeds[0], 3) if speeds else None}
  if heavy:
    d["speeds"] = rl(speeds, 3)
    d["accels"] = rl(accels, 3)
    d["jerks"] = rl(g(lp, "jerks", []), 3)
  return d


def ext_modelV2(m, heavy):
  d = {"desiredCurvature": r(m.action.desiredCurvature, 6),
       "laneChangeState": str(g(m.meta, "laneChangeState", "")),
       "laneChangeDirection": str(g(m.meta, "laneChangeDirection", "")),
       "hardBrakePredicted": bool(g(m.meta, "hardBrakePredicted", False)),
       "confidence": str(g(m, "confidence", "")),
       "frameId": int(g(m, "frameId", 0)), "timestampEof": int(g(m, "timestampEof", 0))}
  if heavy:
    d["pos_x"] = rl(m.position.x, 3); d["pos_y"] = rl(m.position.y, 3); d["pos_z"] = rl(m.position.z, 3)
    d["vel_x"] = rl(m.velocity.x, 3)
    d["orient_z"] = rl(m.orientation.z, 4)
    d["laneLineProbs"] = rl(g(m, "laneLineProbs", []), 3)
    # lane lines & road edges geometry (vehicle frame): list of [x[], y[]]
    try:
      d["laneLines"] = [[rl(ll.x, 2), rl(ll.y, 2)] for ll in m.laneLines]
    except Exception:
      d["laneLines"] = []
    try:
      d["roadEdges"] = [[rl(re.x, 2), rl(re.y, 2)] for re in m.roadEdges]
    except Exception:
      d["roadEdges"] = []
  return d


def ext_loc(llk):
  pg = g(llk, "positionGeodetic")
  ned = g(llk, "calibratedOrientationNED")
  vc = g(llk, "velocityCalibrated")
  out = {"status": str(g(llk, "status", "")), "gpsOK": bool(g(llk, "gpsOK", False))}
  try:
    if pg is not None and len(pg.value) == 3:
      out["lat"], out["lon"], out["alt"] = r(pg.value[0], 7), r(pg.value[1], 7), r(pg.value[2], 2)
  except Exception:
    pass
  try:
    if ned is not None and len(ned.value) == 3:
      out["yaw"] = r(ned.value[2], 5)
  except Exception:
    pass
  try:
    if vc is not None and len(vc.value) == 3:
      out["vel"] = rl(vc.value, 3)
  except Exception:
    pass
  return out


def ext_radar(rs):
  lo = g(rs, "leadOne")
  if lo is None:
    return {}
  return {"status": bool(g(lo, "status", False)), "dRel": r(g(lo, "dRel"), 2),
          "yRel": r(g(lo, "yRel"), 2), "vRel": r(g(lo, "vRel"), 3),
          "vLead": r(g(lo, "vLead"), 3), "aLeadK": r(g(lo, "aLeadK"), 3)}


EXTRACTORS = {
  'carState': lambda m, h: ext_carState(m),
  'carControl': lambda m, h: ext_carControl(m),
  'carOutput': lambda m, h: ext_carOutput(m),
  'controlsState': lambda m, h: ext_controlsState(m),
  'longitudinalPlan': ext_longitudinalPlan,
  'modelV2': ext_modelV2,
  'liveLocationKalman': lambda m, h: ext_loc(m),
  'radarState': lambda m, h: ext_radar(m),
  'liveParameters': lambda m, h: ext_liveParameters(m),
}
OUT_KEY = {'liveLocationKalman': 'loc', 'radarState': 'radar', 'liveParameters': 'liveParams'}


def build_record(sm, seq):
  rec = {"t_wall": round(time.time(), 4), "t_mono": round(time.monotonic(), 4), "seq": seq}
  for s in SERVICES:
    try:
      upd = bool(sm.updated[s])
      heavy = upd and (s in HEAVY)
      block = EXTRACTORS[s](sm[s], heavy)
      block["_upd"] = upd
      block["_valid"] = bool(sm.valid[s])
      block["_mono"] = int(sm.logMonoTime[s])
      rec[OUT_KEY.get(s, s)] = block
    except Exception as e:
      rec[OUT_KEY.get(s, s)] = {"_err": str(e)}

  # derived: equivalent desired steering-wheel angle from desired curvature (bicycle model).
  # torque-mode cars have no angle command, so this is the readable "steering angle command".
  try:
    curv = rec["controlsState"].get("desiredCurvature")
    lp = rec.get("liveParams", {})
    sr = lp.get("steerRatio") or DEFAULT_STEER_RATIO
    off = lp.get("angleOffsetDeg") or 0.0
    if curv is not None:
      rec["controlsState"]["desSteerAngleDeg"] = round(
        math.degrees(math.atan(WHEELBASE * curv)) * sr + off, 3)
  except Exception:
    pass
  return rec


# ----- TCP fan-out -----
class Client:
  def __init__(self, conn, addr):
    self.conn = conn
    self.addr = addr
    self.q = collections.deque(maxlen=300)  # drop oldest when the laptop is slow
    self.ev = threading.Event()
    self.alive = True
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    threading.Thread(target=self._run, daemon=True).start()

  def put(self, data):
    self.q.append(data)
    self.ev.set()

  def _run(self):
    try:
      while self.alive:
        if not self.q:
          self.ev.wait(1.0)
          self.ev.clear()
          continue
        try:
          data = self.q.popleft()
        except IndexError:
          continue
        self.conn.sendall(data)
    except Exception:
      pass
    finally:
      self.alive = False
      try:
        self.conn.close()
      except Exception:
        pass


class Fanout:
  def __init__(self, bind, port):
    self.clients = []
    self.lock = threading.Lock()
    self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # retry bind: when manager restarts us, the old instance may still hold the port briefly
    for i in range(30):
      try:
        self.srv.bind((bind, port))
        break
      except OSError:
        if i == 29:
          raise
        time.sleep(1.0)
    self.srv.listen(8)
    threading.Thread(target=self._accept, daemon=True).start()
    print(f"reg_export: serving JSON lines on {bind}:{port}", flush=True)

  def _accept(self):
    while True:
      try:
        conn, addr = self.srv.accept()
      except Exception:
        break
      c = Client(conn, addr)
      with self.lock:
        self.clients = [x for x in self.clients if x.alive]
        self.clients.append(c)
      print(f"reg_export: client connected {addr} (total {len(self.clients)})", flush=True)

  def broadcast(self, data):
    with self.lock:
      dead = False
      for c in self.clients:
        if c.alive:
          c.put(data)
        else:
          dead = True
      if dead:
        self.clients = [x for x in self.clients if x.alive]

  def nclients(self):
    with self.lock:
      return sum(1 for x in self.clients if x.alive)


def main(port=None, bind=None):
  # manager launches this via `mod.main()` (no args), so read config from env/defaults
  # here; the CLI (__main__ below) still supports --port/--bind for standalone runs.
  port = int(os.environ.get("REG_EXPORT_PORT", 7700 if port is None else port))
  bind = os.environ.get("REG_EXPORT_BIND", "0.0.0.0" if bind is None else bind)

  fan = Fanout(bind, port)
  sm = messaging.SubMaster(SERVICES, poll='carState')

  seq = 0
  last_log = 0.0
  while True:
    sm.update(1000)
    if not sm.updated['carState']:
      continue
    rec = build_record(sm, seq)
    seq += 1
    line = (json.dumps(rec, separators=(",", ":")) + "\n").encode()
    fan.broadcast(line)

    now = time.monotonic()
    if now - last_log > 5.0:
      last_log = now
      print(f"reg_export: seq={seq} clients={fan.nclients()} "
            f"vEgo={rec.get('carState', {}).get('vEgo')} "
            f"curv={rec.get('carControl', {}).get('curvature')}", flush=True)


if __name__ == "__main__":
  ap = argparse.ArgumentParser()
  ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--bind", default="0.0.0.0")
  a = ap.parse_args()
  main(a.port, a.bind)
