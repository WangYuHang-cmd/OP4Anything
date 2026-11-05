#!/usr/bin/env python3
"""enable_fake_ignition_autostart.py — boot straight into the camera view on the bench rig.
RUN ON DEVICE after review.

    scp fake_ignition.py enable_fake_ignition_autostart.py comma@<ip>:/data/objstop/
    ssh comma@<ip> 'python3 /data/objstop/enable_fake_ignition_autostart.py && sudo reboot'

Problem this closes: /data/force_onroad already brings the whole backend onroad with no
car, but the screen stays on the sunnypilot home UI because selfdrive/ui/ui.cc:210 gates
on scene.ignition, which comes only from pandaStates (ui.cc:191-193). fake_ignition.py
supplies that message — but run by hand it dies on every reboot, which is exactly what was
observed: the camera view appeared, the device reset, and the UI went back to the home
screen.

What it changes: system/manager/process_config.py (backup .bak_arman_fakeign)
Rather than having fake_ignition race the real pandad and kill it, manager simply doesn't
start pandad while /data/force_onroad exists, and starts the synthetic publisher instead.
Deterministic, no kill loop, and one file is the whole switch:

    touch /data/force_onroad   ->  dashcam rig: synthetic ignition, camera view on boot
    rm    /data/force_onroad   ->  completely stock: real pandad, real ignition

Also writes tools/fake_ignition_launcher.py (same shim pattern as tools/objstop_launcher.py).

Revert: cp system/manager/process_config.py.bak_arman_fakeign system/manager/process_config.py
"""
import os
import py_compile
import shutil
import sys

PC = "/data/openpilot/system/manager/process_config.py"
LAUNCHER = "/data/openpilot/tools/fake_ignition_launcher.py"
MARKER = "bak_arman_fakeign"

LAUNCHER_SRC = '''import sys
import threading
import time


def keep_car_params():
  """modeld.py:242 blocks on params.get("CarParams", block=True). card only writes that
  after fingerprinting, which needs CAN — with no bus modeld stalls forever and nothing
  downstream produces a trajectory (no modelV2 -> no cameraOdometry -> locationd silent
  -> reg_export streams zero records).

  Writing it once is not enough: CarParams is CLEAR_ON_MANAGER_START *and*
  CLEAR_ON_ONROAD_TRANSITION, and manager clears the latter on every transition
  (manager.py:236-238) — which happens ~26 s after boot, wiping an early write. So keep
  it present. MOCK is the same value card falls back to when no fingerprint matches.
  """
  from openpilot.common.params import Params
  from openpilot.selfdrive.car.car_helpers import write_car_param
  params = Params()
  while True:
    try:
      if not params.get("CarParams"):
        write_car_param()
    except Exception:
      pass
    time.sleep(1.0)


def main():
  sys.path.insert(0, '/data/objstop')
  sys.argv = [sys.argv[0]]      # manager argv must not leak into the script

  threading.Thread(target=keep_car_params, daemon=True).start()

  import fake_ignition
  fake_ignition.main()


if __name__ == '__main__':
  main()
'''

FUNCS = '''def dashcam_rig(started, params, CP) -> bool:
  # Bench / no-CAN rig (see ''' + MARKER + '''): while /data/force_onroad exists the real
  # panda daemon is replaced by tools/fake_ignition_launcher, which publishes a synthetic
  # pandaStates with ignitionLine=True so selfdrive/ui/ui.cc:210 leaves the offroad screen.
  return os.path.exists('/data/force_onroad')


def pandad_run(started, params, CP) -> bool:
  # one publisher per msgq topic: the real pandad steps aside for the synthetic one
  return always_run(started, params, CP) and not dashcam_rig(started, params, CP)


'''

DRIVERVIEW_ANCHOR = "def driverview(started: bool, params: Params, CP: car.CarParams) -> bool:\n"
PANDAD_OLD = '  PythonProcess("pandad", "selfdrive.pandad.pandad", always_run),\n'
PANDAD_NEW = '  PythonProcess("pandad", "selfdrive.pandad.pandad", pandad_run),\n'
OBJSTOP_ANCHOR = '  PythonProcess("objstopd", "tools.objstop_launcher", objstop_auto),\n'
FAKEIGN_ADD = '  PythonProcess("fake_ignition", "tools.fake_ignition_launcher", dashcam_rig),\n'


def main():
  if not os.path.exists("/data/objstop/fake_ignition.py"):
    print("ERROR: /data/objstop/fake_ignition.py not staged — scp it first, nothing changed")
    return 1

  src = open(PC).read()
  if MARKER in src:
    print("process_config: already patched")
  else:
    for anchor in (DRIVERVIEW_ANCHOR, PANDAD_OLD, OBJSTOP_ANCHOR):
      if src.count(anchor) != 1:
        print(f"ERROR: anchor not unique/found ({src.count(anchor)}x) — aborting:\n{anchor!r}")
        return 1

    out = src.replace(DRIVERVIEW_ANCHOR, FUNCS + DRIVERVIEW_ANCHOR, 1)
    out = out.replace(PANDAD_OLD, PANDAD_NEW, 1)
    out = out.replace(OBJSTOP_ANCHOR, OBJSTOP_ANCHOR + FAKEIGN_ADD, 1)

    shutil.copy(PC, PC + "." + MARKER)
    open(PC, "w").write(out)
    try:
      py_compile.compile(PC, doraise=True)
    except py_compile.PyCompileError as e:
      shutil.copy(PC + "." + MARKER, PC)
      print(f"ERROR: patched file does not compile, rolled back: {e}")
      return 1
    print(f"process_config: PATCHED + compiled (backup .{MARKER})")

  # always rewrite: this file is ours, and it is the piece that gets iterated on
  open(LAUNCHER, "w").write(LAUNCHER_SRC)
  py_compile.compile(LAUNCHER, doraise=True)
  print("launcher: tools/fake_ignition_launcher.py written")

  if not os.path.exists("/data/force_onroad"):
    open("/data/force_onroad", "w").close()
    print("/data/force_onroad CREATED")

  print("\nReboot to apply:  sudo reboot")
  print("Expected after boot: camera view on screen, no real pandad, IsOnroad=1")
  return 0


if __name__ == "__main__":
  sys.exit(main())
