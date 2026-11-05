#!/usr/bin/env python3
"""
status.py: read-only status of the dashcam-anywhere mode. Runs on the comma device:
  cd /data/openpilot && PYTHONPATH=/data/openpilot /usr/local/venv/bin/python3 -B /data/dashcam_anywhere/status.py
Listens to the live services for a few seconds, prints one screen and writes nothing.
"""
import math
import os
import sys
import time

import cereal.messaging as messaging
from cereal import car
from openpilot.common.params import Params

FLAG = "/data/force_onroad"
MARKER = "/data/calib_from_dashcam"
RESET_FLAG = "/data/reset_calib"
REALDATA = "/data/media/0/realdata"
GPS_MAX_AGE, GPS_MAX_SPEED_STD = 2.0, 1.0  # same as calibrationd
DEG = 180 / math.pi


def main(listen_s: float = 3.0) -> int:
  services = ['pandaStates', 'liveCalibration', 'gpsLocation', 'cameraOdometry', 'deviceState', 'managerState', 'sendcan']
  sm = messaging.SubMaster(services)
  sendcan_msgs = 0
  t_end = time.monotonic() + listen_s
  while time.monotonic() < t_end:
    sm.update(100)
    sendcan_msgs += int(sm.updated['sendcan'])
  now = time.monotonic()
  params = Params()

  print("== dashcam-anywhere")
  print(f"flag {FLAG}: {'present' if os.path.isfile(FLAG) else 'absent'}   "
        f"calib marker: {'present' if os.path.isfile(MARKER) else 'absent'}   "
        f"pending reset: {'yes' if os.path.isfile(RESET_FLAG) else 'no'}   "
        f"DisableUpdates: {params.get_bool('DisableUpdates')}")
  cp_bytes = params.get("CarParams")
  if cp_bytes:
    with car.CarParams.from_bytes(cp_bytes) as cp:
      safety = [str(sc.safetyModel) for sc in cp.safetyConfigs]
      print(f"this boot: CarParams brand={cp.brand} passive={cp.passive} safetyConfigs={safety}")
  else:
    print("this boot: no CarParams yet (offroad, or card not started)")
  print(f"IsOnroad: {params.get_bool('IsOnroad')}")

  print("\n== panda (expect ignitionLine=True, safety noOutput, no TX)")
  if sm.seen['pandaStates'] and len(sm['pandaStates']):
    ps = sm['pandaStates'][0]
    tx = [getattr(ps, f"canState{i}").totalTxCnt for i in range(3)]
    fwd = [getattr(ps, f"canState{i}").totalFwdCnt for i in range(3)]
    print(f"ignitionLine={ps.ignitionLine} safetyModel={ps.safetyModel} controlsAllowed={ps.controlsAllowed} "
          f"safetyTxBlocked={ps.safetyTxBlocked} txCnt={tx} fwdCnt={fwd} harness={ps.harnessStatus}")
  else:
    print("no pandaStates received")
  print(f"sendcan messages in {listen_s:.0f} s: {sendcan_msgs}")

  print("\n== calibration")
  if sm.seen['liveCalibration']:
    lc = sm['liveCalibration']
    rpy = [x * DEG for x in lc.rpyCalib] if len(lc.rpyCalib) == 3 else [float('nan')] * 3
    spread = [x * DEG for x in lc.rpyCalibSpread] if len(lc.rpyCalibSpread) == 3 else [float('nan')] * 3
    height = lc.height[0] if len(lc.height) else float('nan')
    print(f"status={lc.calStatus} calPerc={lc.calPerc}% validBlocks={lc.validBlocks} valid={sm.valid['liveCalibration']}")
    print(f"pitch {rpy[1]:+.2f} deg (+ = pointing down)  yaw {rpy[2]:+.2f} deg (+ = pointing left)  "
          f"height {height:.3f} m  spread pitch {spread[1]:.2f} yaw {spread[2]:.2f} deg")
  else:
    print("no liveCalibration (calibrationd runs onroad only)")

  print("\n== speed used for calibration (needs > 9 km/h, straight)")
  v_vision = sm['cameraOdometry'].trans[0] if sm.seen['cameraOdometry'] and len(sm['cameraOdometry'].trans) else None
  g = sm['gpsLocation']
  gps_age = now - sm.recv_time['gpsLocation'] if sm.seen['gpsLocation'] else None
  gps_ok = gps_age is not None and gps_age < GPS_MAX_AGE and g.hasFix and g.speedAccuracy < GPS_MAX_SPEED_STD
  if sm.seen['gpsLocation']:
    print(f"GPS: hasFix={g.hasFix} speed={g.speed * 3.6:.1f} km/h acc={g.speedAccuracy:.2f} m/s age={gps_age:.1f} s "
          f"lat={g.latitude:.6f} lon={g.longitude:.6f}")
  else:
    print("GPS: no gpsLocation yet (no fix, or offroad)")
  if v_vision is not None:
    print(f"vision: {v_vision * 3.6:.1f} km/h")
  if gps_ok and v_vision is not None and g.speed > 1.0:
    print(f"vision/GPS speed ratio: {v_vision / g.speed:.2f}")
  print(f"source: {'GPS' if gps_ok else 'vision (no usable GPS)'}")

  print("\n== device")
  if sm.seen['deviceState']:
    ds = sm['deviceState']
    print(f"thermalStatus={ds.thermalStatus} maxTempC={ds.maxTempC:.0f} fan={ds.fanSpeedPercentDesired}% "
          f"freeSpace={ds.freeSpacePercent:.0f}% started={ds.started}")
  if sm.seen['managerState']:
    # updated exits right away by design when DisableUpdates is set
    down = [p.name for p in sm['managerState'].processes if p.shouldBeRunning and not p.running and p.name != 'updated']
    print(f"processes that should run but are down: {down if down else 'none'}")
  try:
    def seg_key(d):
      route, _, seg = d.rpartition('--')
      return route, int(seg) if seg.isdigit() else -1
    routes = sorted((d for d in os.listdir(REALDATA) if '--' in d), key=seg_key)
    print(f"latest segment: {routes[-1] if routes else '-'}  ({len(routes)} segments on disk)")
  except OSError:
    pass
  return 0


if __name__ == "__main__":
  sys.exit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 3.0))
