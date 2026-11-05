#!/usr/bin/env python3
"""controls_monitor.py — live text table of openpilot control commands vs feedback.

Terminal dashboard (no GUI) that redraws in place ~10 Hz. Each row is one signal,
with columns COMMAND (what openpilot wants) | SENT/CAN (final value on the bus) |
MEASURED (sensor feedback) | UNIT. Header shows engage/lat/long/state.

For this vehicle (2020 Civic Bosch, stock PCM + torque lateral):
  - steering command is a normalized torque + CAN torque (±4096); angle command is
    derived from desired curvature (torque mode has no native angle command).
  - accel is planned but NOT sent to CAN (stock PCM) — flagged accordingly.
  - gas/brake shown are the MEASURED pedals (self-calibrated %); Bosch sends no
    pedal command.

    python controls_monitor.py --ip <comma_ip>
    python controls_monitor.py --ip <comma_ip> --csv controls.csv
    python controls_monitor.py --selftest
"""
import argparse
import json
import time

from stream_lib import stream

C = {"reset": "\033[0m", "dim": "\033[2m", "b": "\033[1m", "cyan": "\033[36m",
     "grn": "\033[32m", "red": "\033[31m", "yel": "\033[33m", "gry": "\033[90m",
     "clr": "\033[2J\033[H"}


def f(v, spec="{:>8.3f}"):
  return spec.format(v) if isinstance(v, (int, float)) else "{:>8}".format("—")


def onoff(b):
  return f"{C['grn']}ON {C['reset']}" if b else f"{C['gry']}off{C['reset']}"


def render(rec, cal):
  cs = rec.get("carState", {}); cc = rec.get("carControl", {})
  co = rec.get("carOutput", {}); cst = rec.get("controlsState", {})
  lp = rec.get("longitudinalPlan", {})
  g, b = cs.get("gas"), cs.get("brake")
  if isinstance(g, (int, float)):
    cal["g"] = max(cal["g"], g)
  if isinstance(b, (int, float)):
    cal["b"] = max(cal["b"], b)
  gp = 100 * g / cal["g"] if isinstance(g, (int, float)) and cal["g"] > 0 else None
  bp = 100 * b / cal["b"] if isinstance(b, (int, float)) and cal["b"] > 0 else None

  rows = [
    # signal,               command,                 sent/CAN,                measured,               unit
    ("steering angle",       cst.get("desSteerAngleDeg"), None,               cs.get("steeringAngleDeg"), "deg"),
    ("steering rate",        None,                    None,                    cs.get("steeringRateDeg"), "deg/s"),
    ("steering torque",      cc.get("steer"),         co.get("steerOutputCan"), cs.get("steeringTorqueEps"), "norm/CAN/EPS"),
    ("driver steer torque",  None,                    None,                    cs.get("steeringTorque"), "raw"),
    ("desired curvature",    cst.get("desiredCurvature"), None,               cst.get("curvature"),   "1/m"),
    ("speed",                cst.get("vCruise"),      None,                    cs.get("vEgo"),         "kph|m/s"),
    ("acceleration",         cc.get("accel"),         None,                    cs.get("aEgo"),         "m/s²"),
    ("gas pedal",            None,                    None,                    gp,                     "%"),
    ("brake pedal",          None,                    None,                    bp,                     "%"),
  ]
  out = [C["clr"]]
  out.append(f"{C['b']}{C['cyan']} openpilot control monitor {C['reset']}"
             f"  seq={rec.get('seq')}   t={rec.get('t_wall')}")
  out.append(f" engaged {onoff(cc.get('enabled'))}   lat {onoff(cc.get('latActive'))}   "
             f"long {onoff(cc.get('longActive'))}   state={C['yel']}{cst.get('state')}{C['reset']}")
  out.append(f"{C['dim']} accel command is computed but NOT sent to CAN (stock PCM ACC drives long.){C['reset']}")
  out.append("")
  out.append(f" {C['b']}{'SIGNAL':<20}{'COMMAND':>12}{'SENT/CAN':>12}{'MEASURED':>12}  {'UNIT':<12}{C['reset']}")
  out.append(f" {C['gry']}{'-'*68}{C['reset']}")
  for name, cmd, sent, meas, unit in rows:
    out.append(f" {name:<20}{f(cmd):>12}{f(sent):>12}{f(meas):>12}  {C['gry']}{unit:<12}{C['reset']}")
  print("\n".join(out), flush=True)


def synthetic():
  import math
  i = 0
  while True:
    t = i * 0.01
    yield {"seq": i, "t_wall": round(time.time(), 2),
           "carState": {"steeringAngleDeg": 6 * math.sin(t), "steeringRateDeg": 6 * math.cos(t),
                        "steeringTorqueEps": 300 * math.sin(t), "steeringTorque": 20 * math.sin(t),
                        "vEgo": 12 + 2 * math.sin(t), "aEgo": 1.1 * math.sin(t), "gas": 0.15, "brake": 0.0,
                        "curvature": 0.02 * math.sin(t)},
           "carControl": {"enabled": True, "latActive": True, "longActive": False,
                          "steer": 0.3 * math.sin(t), "accel": 1.2 * math.sin(t)},
           "carOutput": {"steerOutputCan": -1228 * math.sin(t)},
           "controlsState": {"state": "enabled", "desSteerAngleDeg": 6.2 * math.sin(t),
                             "desiredCurvature": 0.021 * math.sin(t), "curvature": 0.02 * math.sin(t),
                             "vCruise": 45.0},
           "longitudinalPlan": {}}
    i += 1
    time.sleep(0.05)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip"); ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--csv", default=None)
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()
  if not args.selftest and not args.ip:
    ap.error("--ip required (or --selftest)")

  cal = {"g": 0.5, "b": 0.5}
  csvf = None
  if args.csv:
    import csv as _csv
    csvf = open(args.csv, "w", newline="")
    csvw = None

  src = synthetic() if args.selftest else stream(args.ip, args.port)
  last = 0.0
  n = 0
  try:
    for rec in src:
      n += 1
      now = time.monotonic()
      if now - last >= 0.1:                 # redraw at ~10 Hz
        last = now
        render(rec, cal)
      if csvf is not None:
        flat = {"t_wall": rec.get("t_wall"), "seq": rec.get("seq")}
        for blk in ("carState", "carControl", "carOutput", "controlsState"):
          for k, v in (rec.get(blk) or {}).items():
            if not isinstance(v, (list, dict)):
              flat[f"{blk}.{k}"] = v
        if csvw is None:
          csvw = _csv.DictWriter(csvf, fieldnames=list(flat.keys()), extrasaction="ignore")
          csvw.writeheader()
        csvw.writerow(flat)
      if args.selftest and n >= 3:
        print("\nselftest OK (rendered synthetic frames)")
        break
  except KeyboardInterrupt:
    pass
  finally:
    if csvf:
      csvf.close()


if __name__ == "__main__":
  main()
