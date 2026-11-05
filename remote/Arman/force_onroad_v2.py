#!/usr/bin/env python3
"""force_onroad_v2.py — make the forced-onroad hook explicit + add a persistent diagnostic.
RUN ON DEVICE after review.

    scp force_onroad_v2.py comma@<ip>:/data/objstop/
    ssh comma@<ip> 'python3 /data/objstop/force_onroad_v2.py && sudo reboot'

Why v2: the v1 hook (enable_dashcam_mode.py) works on the bench, but the bench always has
a real ignition line, so it never actually exercised the forced path. And hardwared only
logs "Startup blocked" when ignition is already True (hardwared.py:381), so a boot that
stays offroad because ignition is False leaves NO evidence at all. That made the field
failure ("12V connected, never went onroad") undiagnosable.

What it changes: system/hardware/hardwared.py (backup .bak_arman_v2)
1. Rewrites the ignition hook into the explicit form:
       onroad_conditions["ignition"] = real_ignition or force_onroad
   Same behavior as v1, but it keeps `real_ignition` around so we can tell the two apart.
2. Appends a state-change line to /data/onroad_debug.log every time should_start or the
   ignition source changes. /data survives reboot and needs no network, so the next field
   test is diagnosable even with no hotspot in the truck.

The log answers, for the failing boot: did hardwared even see the file? was ignition
forced True? if so, which of onroad_conditions/startup_conditions was False?

Revert: cp system/hardware/hardwared.py.bak_arman_v2 system/hardware/hardwared.py
"""
import py_compile
import shutil
import sys

PATH = "/data/openpilot/system/hardware/hardwared.py"
MARKER = "bak_arman_v2"

OLD_HOOK = (
  "    # Arman bench/dashcam mode: `touch /data/force_onroad` forces ignition so the\n"
  "    # camera/model/GPS stack runs without a car CAN connection. Remove to revert.\n"
  "    if os.path.exists('/data/force_onroad'):\n"
  "      onroad_conditions[\"ignition\"] = True\n"
)

NEW_HOOK = (
  "    # Arman bench/dashcam mode (v2, see " + MARKER + "): `touch /data/force_onroad`\n"
  "    # forces ignition so the camera/model/GPS stack runs without a car CAN connection.\n"
  "    # Kept explicit so the diagnostic below can tell a real ignition from a forced one.\n"
  "    arman_real_ignition = onroad_conditions[\"ignition\"]\n"
  "    arman_forced = os.path.exists('/data/force_onroad')\n"
  "    onroad_conditions[\"ignition\"] = arman_real_ignition or arman_forced\n"
)

INIT_ANCHOR = "  should_start_prev = False\n"
INIT_ADD = ("  arman_real_ignition = False\n"
            "  arman_forced = False\n"
            "  arman_last_state: tuple | None = None\n")

LOG_ANCHOR = ("    # Handle offroad/onroad transition\n"
              "    should_start = all(onroad_conditions.values())\n"
              "    if started_ts is None:\n"
              "      should_start = should_start and all(startup_conditions.values())\n")

LOG_ADD = (
  "\n"
  "    # Arman: persistent forced-onroad diagnostic. /data survives reboot and needs no\n"
  "    # network, so a field boot that never goes onroad still leaves evidence here.\n"
  "    arman_state = (should_start, onroad_conditions[\"ignition\"], arman_real_ignition, arman_forced)\n"
  "    if arman_state != arman_last_state:\n"
  "      arman_last_state = arman_state\n"
  "      try:\n"
  "        with open('/data/onroad_debug.log', 'a') as arman_f:\n"
  "          arman_f.write(f\"{time.time():.0f} mono={time.monotonic():.1f} \"\n"
  "                        f\"should_start={should_start} ignition={onroad_conditions['ignition']} \"\n"
  "                        f\"real_ign={arman_real_ignition} forced_file={arman_forced} \"\n"
  "                        f\"onroad={onroad_conditions} startup={startup_conditions}\\n\")\n"
  "      except Exception:\n"
  "        pass\n"
)


def main():
  src = open(PATH).read()
  if MARKER in src:
    print("hardwared: already v2")
    return 0
  if OLD_HOOK not in src:
    print("ERROR: v1 hook not found verbatim — aborting, nothing changed")
    return 1
  if INIT_ANCHOR not in src or LOG_ANCHOR not in src:
    print("ERROR: init/log anchor not found — aborting, nothing changed")
    return 1

  out = src.replace(OLD_HOOK, NEW_HOOK, 1)
  out = out.replace(INIT_ANCHOR, INIT_ANCHOR + INIT_ADD, 1)
  out = out.replace(LOG_ANCHOR, LOG_ANCHOR + LOG_ADD, 1)

  shutil.copy(PATH, PATH + "." + MARKER)
  open(PATH, "w").write(out)
  try:
    py_compile.compile(PATH, doraise=True)
  except py_compile.PyCompileError as e:
    shutil.copy(PATH + "." + MARKER, PATH)
    print(f"ERROR: patched file does not compile, rolled back: {e}")
    return 1

  print(f"hardwared: PATCHED v2 + compiled (backup .{MARKER})")
  print("diagnostic -> /data/onroad_debug.log   (tail it after any boot)")
  print("Restart to apply:  sudo reboot")
  return 0


if __name__ == "__main__":
  sys.exit(main())
