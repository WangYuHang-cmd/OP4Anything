#!/usr/bin/env python3
"""fake_ignition.py — synthetic pandaStates so the UI leaves the offroad screen.
Bench / no-CAN experiment rig.

    scp fake_ignition.py comma@<ip>:/data/objstop/
    ssh comma@<ip>
    cd /data/objstop && PYTHONPATH=/data/openpilot:/data \\
      /usr/local/pyenv/versions/3.11.4/bin/python3 fake_ignition.py

Revert: sudo reboot   (nothing on disk is modified; the real pandad comes back)

Why this exists: /data/force_onroad patches hardwared, which brings the whole backend
onroad with no car (camerad, modeld, controlsd, loggerd, reg_export, objstopd all verified
running with real_ign=False). It cannot move the *screen*, because
selfdrive/ui/ui.cc:210 computes

    scene.started = deviceState.getStarted() && scene.ignition

and scene.ignition (ui.cc:191-193) comes ONLY from pandaStates ignitionLine / ignitionCan.
ui.cc:361 gates the backlight on the same flag. This release branch ships a prebuilt `ui`
binary with the .cc sources stripped, so the gate can't be patched out — but the message
it reads can be published by us.

The real pandad has to be stopped first (one publisher per msgq topic), so while this runs
there is no CAN, no safety model and no actuation.
"""
import subprocess
import sys
import time

sys.path.insert(0, "/data")
import cereal.messaging as messaging
from cereal import car, log

RATE = 10  # pandaStates is a 10 Hz service; hardwared paces its loop off this


def stop_real_pandad():
  for pat in (["sudo", "pkill", "-f", "[s]elfdrive.pandad.pandad"], ["sudo", "pkill", "-x", "pandad"]):
    subprocess.run(pat, check=False)
  time.sleep(2)


def main():
  stop_real_pandad()
  print("real pandad stopped; publishing synthetic pandaStates (Ctrl-C or reboot to stop)")

  pm = messaging.PubMaster(["pandaStates", "peripheralState"])
  while True:
    msg = messaging.new_message("pandaStates", 1)
    msg.valid = True
    ps = msg.pandaStates[0]
    ps.pandaType = log.PandaState.PandaType.tres
    ps.ignitionLine = True
    ps.ignitionCan = False
    ps.controlsAllowed = False
    ps.safetyModel = car.CarParams.SafetyModel.noOutput
    ps.harnessStatus = log.PandaState.HarnessStatus.normal
    pm.send("pandaStates", msg)

    pmsg = messaging.new_message("peripheralState")
    pmsg.valid = True
    pmsg.peripheralState.pandaType = log.PandaState.PandaType.tres
    pmsg.peripheralState.voltage = 12000
    pmsg.peripheralState.current = 0
    pm.send("peripheralState", pmsg)

    time.sleep(1.0 / RATE)


if __name__ == "__main__":
  sys.exit(main())
