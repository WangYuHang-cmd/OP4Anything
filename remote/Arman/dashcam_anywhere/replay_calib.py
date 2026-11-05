#!/usr/bin/env python3
"""
replay_calib.py: read-only replay of the dashcam-anywhere calibration logic on recorded drives.

Runs on the comma device (needs the patched openpilot in PYTHONPATH):
  cd /data/openpilot && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/data/openpilot \
    /usr/local/venv/bin/python3 -B /data/dashcam_anywhere/replay_calib.py [--root DIR] [SEGMENT ...]

Each logged cameraOdometry sample is fed to calibrationd's Calibrator. The residual is composed with
the liveCalibration.rpyCalib that modeld actually used when it was recorded, which reproduces the
calibration feedback loop. MOCK has no wheel speed, so the speed is GPS (fresh, good fix) or visual
odometry, exactly like calibrationd in dashcam mode. Nothing is written to disk or Params.

Acceptance (dashcam config, on the CAN < 6.7 m/s and CAN < 3.1 m/s subsets):
  0 false recalibrations, max yaw spread < 1.5 deg, |d pitch|, |d yaw| < 0.2 deg vs the stock replay.
"""
import argparse
import bisect
import os
import sys

import numpy as np
import zstandard

from cereal import log
import openpilot.selfdrive.locationd.calibrationd as cd

LOW_SPEED = [
  "00000052--fa571d31f0--7", "00000052--fa571d31f0--8", "00000059--66f2256e8f--5", "00000062--b32fa6b44a--2",
  "0000005d--e221fa3711--0", "00000055--f935f3b49e--12", "00000051--873d9460bd--0", "00000051--873d9460bd--1",
  "00000050--4a22209229--3", "00000050--4a22209229--12", "00000053--f6ab57865f--2", "00000053--f6ab57865f--4",
  "0000005a--630ba402a4--5", "0000005c--03399c43cd--17", "0000004b--9bff7e7880--3", "0000004d--ebec04b408--2",
]
HIGHWAY = ["0000005c--03399c43cd--11", "00000057--ef39d20a22--2", "00000059--66f2256e8f--12"]

Status = log.LiveCalibrationData.Status
STATUS_NAMES = {Status.uncalibrated: "uncalibrated", Status.calibrated: "calibrated",
                Status.invalid: "invalid", Status.recalibrating: "recalibrating"}
DEG = 180 / np.pi


def load_segment(path):
  data = zstandard.ZstdDecompressor().stream_reader(open(path, 'rb')).read()
  car, gps, calib, odo = [], [], [], []
  for ev in log.Event.read_multiple_bytes(data):
    w = ev.which()
    t = ev.logMonoTime
    if w == 'carState':
      car.append((t, ev.carState.vEgo))
    elif w == 'gpsLocation':
      g = ev.gpsLocation
      gps.append((t, g.speed, g.speedAccuracy, g.hasFix))
    elif w == 'liveCalibration':
      calib.append((t, list(ev.liveCalibration.rpyCalib)))
    elif w == 'cameraOdometry':
      o = ev.cameraOdometry
      odo.append((t, list(o.trans), list(o.rot), list(o.wideFromDeviceEuler), list(o.transStd),
                  list(o.roadTransformTrans), list(o.roadTransformTransStd)))
  for lst in (car, gps, calib, odo):
    lst.sort(key=lambda x: x[0])

  car_t = [x[0] for x in car]
  gps_t = [x[0] for x in gps]
  cal_t = [x[0] for x in calib]
  samples = []
  for t, trans, rot, wide, trans_std, rtt, rtt_std in odo:
    i = bisect.bisect_right(cal_t, t) - 1
    if i < 0 or len(calib[i][1]) != 3:
      continue
    j = bisect.bisect_right(car_t, t) - 1
    v_can = car[j][1] if j >= 0 else 0.0
    k = bisect.bisect_right(gps_t, t) - 1
    gps_ok = k >= 0 and (t - gps[k][0]) < cd.GPS_MAX_AGE * 1e9 and gps[k][3] and gps[k][2] < cd.GPS_MAX_SPEED_STD
    v_gps = gps[k][1] if gps_ok else None
    samples.append((v_can, v_gps, np.array(calib[i][1]), trans, rot, wide, trans_std, rtt, rtt_std))
  return samples


def new_calibrator():
  c = cd.Calibrator.__new__(cd.Calibrator)  # no Params(), nothing is written
  c.param_put = False
  c.not_car = False
  c.cal_status = Status.uncalibrated
  c.reset()
  c.update_status()
  return c


CONFIGS = {
  # name: (dashcam logic, min speed, max angle std, speed source)
  "stock": (False, 15 * 0.44704, np.radians(0.25), "can"),
  "lowspeed_only": (False, 9 / 3.6, np.radians(1.0), "gps_vision"),
  "dashcam": (True, 9 / 3.6, np.radians(1.0), "gps_vision"),
  "dashcam_vision": (True, 9 / 3.6, np.radians(1.0), "vision"),
}


def run(samples, config, max_can_speed=None):
  dashcam, min_speed, max_std, source = CONFIGS[config]
  cd.DASHCAM, cd.MIN_SPEED_FILTER, cd.MAX_VEL_ANGLE_STD = dashcam, min_speed, max_std
  c = new_calibrator()
  recals, max_spread, t_cal, fed, prev_status = 0, np.zeros(3), None, 0, c.cal_status
  closed_blocks = []
  for v_can, v_gps, logged, trans, rot, wide, trans_std, rtt, rtt_std in samples:
    if max_can_speed is not None and v_can >= max_can_speed:
      continue
    fed += 1
    if source == "can":
      v = v_can
    elif source == "vision" or v_gps is None:
      v = trans[0]
    else:
      v = v_gps
    c.handle_v_ego(v)
    c.old_rpy = logged
    c.old_rpy_weight = 1.0 + 1 / cd.SMOOTH_CYCLES  # smooth rpy == logged rpy after the internal decrement
    block_before = c.block_idx
    c.handle_cam_odom(trans, rot, wide, trans_std, rtt, rtt_std)
    if c.block_idx != block_before and c.valid_blocks > 0:
      closed_blocks.append(c.rpys[(c.block_idx - 1) % cd.INPUTS_WANTED].copy())
    if c.cal_status == Status.recalibrating and prev_status != Status.recalibrating:
      recals += 1
    if c.cal_status == Status.calibrated:
      max_spread = np.maximum(max_spread, c.calib_spread)
      if t_cal is None:
        t_cal = fed / 20.0
    prev_status = c.cal_status
  blocks = np.array(closed_blocks) if closed_blocks else np.zeros((0, 3))
  return {
    "rpy_deg": c.rpy * DEG, "height": float(c.height[0]), "valid_blocks": c.valid_blocks,
    "status": STATUS_NAMES.get(c.cal_status, str(c.cal_status)), "recals": recals, "max_spread_deg": max_spread * DEG,
    "t_to_calibrated_s": t_cal, "fed_s": fed / 20.0,
    "block_std_deg": blocks.std(axis=0) * DEG if len(blocks) > 1 else np.zeros(3),
  }


def fmt(r):
  t = "-" if r["t_to_calibrated_s"] is None else f"{r['t_to_calibrated_s']:.0f}s"
  return (f"pitch {r['rpy_deg'][1]:+.2f} yaw {r['rpy_deg'][2]:+.2f} h {r['height']:.3f} vb {r['valid_blocks']:2d} "
          f"{r['status']:<13} recal {r['recals']} spread(p,y) {r['max_spread_deg'][1]:.2f},{r['max_spread_deg'][2]:.2f} "
          f"blockstd(p,y) {r['block_std_deg'][1]:.2f},{r['block_std_deg'][2]:.2f} t_cal {t} fed {r['fed_s']:.0f}s")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default="/data/media/0/realdata", help="dir holding <segment>/rlog.zst")
  ap.add_argument("segments", nargs="*", default=LOW_SPEED + HIGHWAY)
  args = ap.parse_args()

  samples = []
  for seg in args.segments:
    p = os.path.join(args.root, seg, "rlog.zst")
    if not os.path.isfile(p):
      print(f"missing {p}", file=sys.stderr)
      continue
    samples += load_segment(p)
  n_gps = sum(1 for s in samples if s[1] is not None)
  print(f"{len(samples)} cameraOdometry samples ({len(samples) / 20 / 60:.1f} min), GPS usable {100 * n_gps / max(len(samples), 1):.0f}%")

  ref = run(samples, "stock")
  print(f"\nreference stock (CAN speed, all data): {fmt(ref)}")
  ok = True
  for subset, vmax in (("all", None), ("CAN<6.7", 6.7), ("CAN<3.1", 3.1)):
    print(f"\n== subset {subset}")
    for config in ("lowspeed_only", "dashcam", "dashcam_vision"):
      r = run(samples, config, vmax)
      line = f"  {config:<15} {fmt(r)}"
      if config == "dashcam" and vmax is not None:
        d = np.abs(r["rpy_deg"] - ref["rpy_deg"])
        passed = (r["recals"] == 0 and r["max_spread_deg"][2] < 1.5 and d[1] < 0.2 and d[2] < 0.2 and
                  r["status"] == "calibrated")
        ok &= passed
        line += f"  -> {'PASS' if passed else 'FAIL'} (d pitch {d[1]:.2f}, d yaw {d[2]:.2f})"
      print(line)
  print(f"\nACCEPTANCE: {'PASS' if ok else 'FAIL'}")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
