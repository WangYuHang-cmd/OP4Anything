#!/usr/bin/env python3
"""enable_dashcam_mode.py — no-CAN (truck / bench) mode. RUN ON DEVICE after review.

    ssh comma@<ip>
    cd /data/openpilot && python3 /data/objstop/enable_dashcam_mode.py
    touch /data/force_onroad        # <- enter dashcam mode (camera/model/GPS run, no car)
    rm /data/force_onroad           # <- back to normal (car-ignition controlled)

What it changes (both backed up, both reviewed below):
1. system/hardware/hardwared.py  (backup .bak_arman)
   Adds: if /data/force_onroad exists -> ignition considered ON, so the device goes
   onroad and camerad/modeld/locationd/GPS all run WITHOUT a car CAN connection.
   Without the file, behavior is completely stock. controlsd/card simply wait for a
   car and do nothing — no control is possible without CAN (display/output only).
2. tools/reg_export/exporter.py  (staged at /data/objstop/exporter_nocan.py)
   The stream used to emit records only on carState (100 Hz) — with no CAN it emitted
   NOTHING. Now: with a car, unchanged (carState-paced); without CAN, it emits on any
   service update (modelV2/loc @20 Hz, throttled 50 Hz max) so cp_export still gets
   loc + modelV2 + stopFlag and can produce the client JSON ("stop":0/1 + segments).

With GPS fix outdoors: full ENU output (--ref-lat/lon or first fix). Indoors/no fix:
run cp_export with --local-frame (body frame). objstopd vision works either way.
"""
import os
import py_compile
import shutil
import sys

HOOK = ("    # Arman bench/dashcam mode: `touch /data/force_onroad` forces ignition so the\n"
        "    # camera/model/GPS stack runs without a car CAN connection. Remove to revert.\n"
        "    if os.path.exists('/data/force_onroad'):\n"
        "      onroad_conditions[\"ignition\"] = True\n\n")
ANCHOR = "    # Run at 2Hz, plus rising edge of ignition\n"


def main():
  os.chdir("/data/openpilot")
  # 1) hardwared hook
  p = "system/hardware/hardwared.py"
  s = open(p).read()
  if "force_onroad" in s:
    print("hardwared: already patched")
  else:
    if ANCHOR not in s:
      print("ERROR: hardwared anchor not found — aborting, nothing changed")
      return 1
    shutil.copy(p, p + ".bak_arman")
    open(p, "w").write(s.replace(ANCHOR, HOOK + ANCHOR, 1))
    py_compile.compile(p, doraise=True)
    print("hardwared: PATCHED + compiled (backup .bak_arman)")

  # 2) exporter no-CAN emit fallback (staged copy -> live location)
  staged = "/data/objstop/exporter_nocan.py"
  live = "tools/reg_export/exporter.py"
  if os.path.exists(staged):
    src = open(staged).read()
    if "dashcam / no-CAN mode" in open(live).read():
      print("exporter: already updated")
    else:
      shutil.copy(live, live + ".bak_arman_nocan")
      shutil.copy(staged, live)
      py_compile.compile(live, doraise=True)
      print("exporter: UPDATED + compiled (backup .bak_arman_nocan); restart it:")
      print("  pkill -f '[t]ools.reg_export'   # manager restarts it with the new code")
  else:
    print(f"NOTE: {staged} not staged; exporter unchanged")

  # 3) objstopd auto-start under manager (shadow; disabled by /data/objstop/manual_mode)
  lau = "tools/objstop_launcher.py"
  if not os.path.exists(lau):
    with open(lau, "w") as f:
      f.write(
        "import os\nimport sys\n\n\n"
        "def main():\n"
        "  sys.path.insert(0, '/data/objstop')\n"
        "  os.chdir('/data/objstop')\n"
        "  sys.argv = [sys.argv[0]]      # manager argv must not leak into argparse\n"
        "  import objstopd\n"
        "  objstopd.main()\n\n\n"
        "if __name__ == '__main__':\n  main()\n")
    print("launcher: tools/objstop_launcher.py written")
  pc = "system/manager/process_config.py"
  s = open(pc).read()
  if "objstop_launcher" in s:
    print("process_config: already has objstopd")
  else:
    anchor = '  PythonProcess("reg_export", "tools.reg_export.exporter", always_run),\n'
    if anchor not in s:
      print("ERROR: process_config anchor not found — objstopd auto-start NOT added")
    else:
      shutil.copy(pc, pc + ".bak_arman_auto")
      if "\nimport os\n" not in s:
        s = s.replace("\nfrom cereal import car\n", "\nimport os\nfrom cereal import car\n", 1)
      cond = ("def objstop_auto(started, params, CP) -> bool:\n"
              "  # vision stop daemon: onroad (incl. forced dashcam mode), shadow by default;\n"
              "  # `touch /data/objstop/manual_mode` disables auto-start for manual --arm runs\n"
              "  return started and not os.path.exists('/data/objstop/manual_mode')\n\n\n")
      s = s.replace("def driverview(", cond + "def driverview(", 1)
      s = s.replace(anchor, anchor +
                    '  PythonProcess("objstopd", "tools.objstop_launcher", objstop_auto),\n', 1)
      open(pc, "w").write(s)
      py_compile.compile(pc, doraise=True)
      print("process_config: PATCHED (objstopd auto-start, backup .bak_arman_auto)")

  # 4) power-on = dashcam: persistent flag (survives reboot). Remove when back in the Civic
  #    for normal ignition-controlled behavior.
  open("/data/force_onroad", "w").close()
  print("/data/force_onroad CREATED -> power-on enters dashcam mode until you rm it")

  print("\nDashcam on boot: ACTIVE.  Revert: rm /data/force_onroad (+ restore backups)")
  print("Reboot now so hardwared/manager pick everything up:  sudo reboot")
  return 0


if __name__ == "__main__":
  sys.exit(main())
