#!/usr/bin/env python3
"""suppress_car_prompt.py — hide the "select your car" prompt. RUN ON DEVICE after review.

    scp suppress_car_prompt.py comma@<ip>:/data/objstop/
    ssh comma@<ip> 'python3 /data/objstop/suppress_car_prompt.py && sudo reboot'

Why: with no CAN (truck / bench dashcam mode) fingerprinting falls back to MOCK, so
controlsd raises EventName.carUnrecognized and the screen permanently shows
`Dashcam Mode / ⚙️ -> "Vehicle" to select your car`. Nothing to select — the truck
isn't a supported car and we don't want to control it anyway.

What it changes: selfdrive/controls/lib/events.py (backup .bak_arman_carprompt)
Comments out the ET.PERMANENT alert inside EventName.carUnrecognized, leaving an empty
dict — the same shape EventName.cruiseMismatch already has in this file, so it is a
supported form. Behavior is unchanged: the car stays MOCK/dashcamOnly, openpilot stays
read-only, camera/model/GPS/objstopd/exporter all keep running. Display only.

Revert: cp selfdrive/controls/lib/events.py.bak_arman_carprompt selfdrive/controls/lib/events.py
"""
import py_compile
import shutil
import sys

PATH = "/data/openpilot/selfdrive/controls/lib/events.py"
ANCHOR = "  EventName.carUnrecognized: {\n"
END = "  },\n"
MARKER = "bak_arman_carprompt"
NOTE = ("    # Arman: no-CAN dashcam/truck mode — nothing to select, so this permanent\n"
        "    # prompt is just noise. Revert: cp events.py." + MARKER + " events.py\n")


def main():
  lines = open(PATH).readlines()
  src = "".join(lines)
  if MARKER in src:
    print("events.py: already patched")
    return 0
  if ANCHOR not in lines:
    print("ERROR: carUnrecognized anchor not found — aborting, nothing changed")
    return 1

  start = lines.index(ANCHOR)
  try:
    end = lines.index(END, start + 1)
  except ValueError:
    print("ERROR: end of carUnrecognized block not found — aborting, nothing changed")
    return 1

  body = ["    #" + ln.lstrip(" ") for ln in lines[start + 1:end]]
  out = lines[:start + 1] + [NOTE] + body + lines[end:]

  shutil.copy(PATH, PATH + "." + MARKER)
  open(PATH, "w").write("".join(out))
  try:
    py_compile.compile(PATH, doraise=True)
  except py_compile.PyCompileError as e:
    shutil.copy(PATH + "." + MARKER, PATH)
    print(f"ERROR: patched file does not compile, rolled back: {e}")
    return 1

  print(f"events.py: PATCHED + compiled (backup .{MARKER})")
  print("".join(out[start:start + len(body) + 3]), end="")
  print("\nRestart to apply:  sudo reboot   (or: pkill -f '[s]elfdrive.controls.controlsd')")
  return 0


if __name__ == "__main__":
  sys.exit(main())
