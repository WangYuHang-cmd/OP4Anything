#!/usr/bin/env python3
"""write_carparams_mock.py — unblock modeld when there is no CAN. RUN ON DEVICE.

    scp write_carparams_mock.py comma@<ip>:/data/objstop/
    ssh comma@<ip> 'cd /data/openpilot && PYTHONPATH=/data/openpilot:/data \\
      /usr/local/pyenv/versions/3.11.4/bin/python3 /data/objstop/write_carparams_mock.py'

Why: modeld.py:242 does

    car.CarParams.from_bytes(params.get("CarParams", block=True))

so it sits in a polling sleep until the CarParams param exists. That param is written by
card once fingerprinting finishes — which needs CAN traffic. On the no-CAN rig (and
especially once the real pandad has been replaced, so there is no `can` socket at all)
card never finishes, CarParams is never written, and the whole chain stalls:

    no CarParams -> modeld blocked -> no modelV2 / cameraOdometry
                 -> locationd silent -> reg_export has nothing -> TCP 7700 connects but
                    streams zero records

Writing the MOCK CarParams releases modeld immediately; no process restart is needed
because the blocking get polls. MOCK is what card itself falls back to when fingerprinting
finds no match, so this is the same value, just without waiting for a bus that isn't there.
"""
import sys

sys.path.insert(0, "/data")

from openpilot.common.params import Params
from openpilot.selfdrive.car.car_helpers import write_car_param
from cereal import car


def main():
  p = Params()
  before = p.get("CarParams")
  print(f"CarParams before: {'present' if before else 'MISSING'}")

  write_car_param()          # defaults to MOCK.MOCK

  after = p.get("CarParams")
  if not after:
    print("ERROR: CarParams still missing after write")
    return 1
  with car.CarParams.from_bytes(after) as CP:
    print(f"CarParams written: carName={CP.carName} carFingerprint={CP.carFingerprint} "
          f"dashcamOnly={CP.dashcamOnly}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
