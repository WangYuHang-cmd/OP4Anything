#!/usr/bin/env python3
"""experiment.py — day-of control + readiness for the Civic longitudinal experiment.

Runs on the LAPTOP (which can ssh comma@<ip> with its key and reach the device stream).

  python3 experiment.py --ip 192.168.1.231 check     # is everything ready? (run onroad)
  python3 experiment.py --ip 192.168.1.231 stop       # decel-to-stop  (needs OP long + engaged)
  python3 experiment.py --ip 192.168.1.231 go         # resume
  python3 experiment.py --ip 192.168.1.231 status     # config + flag state

'check' samples the reg_export stream and tells you, for BOTH deliverables:
  - longitudinal: OP long engaged? longActive? accel commanded?
  - JSON export:  GPS fix? modelV2 trajectory present? (cp_export needs these)
"""
import argparse
import json
import socket
import subprocess
import sys
import time

FLAG = "/tmp/op_stop_requested"


def ssh(ip, user, cmd, timeout=10):
  try:
    r = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", "-o", f"ConnectTimeout=6",
                        f"{user}@{ip}", cmd], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()
  except Exception as e:
    return 1, "", str(e)


def sample_stream(ip, port, secs=6.0):
  """Collect records for a few seconds; return merged view of key fields."""
  got = {"n": 0, "loc": None, "gps": False, "modelV2_pos": False,
         "enabled": None, "longActive": None, "accel": None, "vEgo": None, "state": None}
  try:
    s = socket.create_connection((ip, port), timeout=secs)
    s.settimeout(secs)
    f = s.makefile("r")
    t0 = time.time()
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        r = json.loads(line)
      except json.JSONDecodeError:
        continue
      got["n"] += 1
      loc = r.get("loc") or {}
      if loc.get("lat") is not None:
        got["loc"] = (loc.get("lat"), loc.get("lon"), loc.get("yaw"))
        if (abs(loc.get("lat") or 0) > 1e-6 or abs(loc.get("lon") or 0) > 1e-6):
          got["gps"] = True
      mv = r.get("modelV2") or {}
      if mv.get("pos_x"):
        got["modelV2_pos"] = True
      cc = r.get("carControl") or {}
      if cc:
        got["enabled"] = cc.get("enabled", got["enabled"])
        got["longActive"] = cc.get("longActive", got["longActive"])
        got["accel"] = cc.get("accel", got["accel"])
      cs = r.get("carState") or {}
      if cs.get("vEgo") is not None:
        got["vEgo"] = cs.get("vEgo")
      cst = r.get("controlsState") or {}
      if cst.get("state"):
        got["state"] = cst.get("state")
      if time.time() - t0 > secs:
        break
    s.close()
  except Exception as e:
    got["error"] = str(e)
  return got


def yn(b):
  return "\033[32m✓\033[0m" if b else "\033[31m✗\033[0m"


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--ip", required=True)
  ap.add_argument("--user", default="comma")
  ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("action", choices=["check", "stop", "go", "release", "status"])
  a = ap.parse_args()

  if a.action == "stop":
    rc, _, err = ssh(a.ip, a.user, f"touch {FLAG}")
    print("■ STOP requested" if rc == 0 else f"failed: {err}")
    return
  if a.action == "go":
    rc, _, err = ssh(a.ip, a.user, f"rm -f {FLAG}")
    print("▶ GO (stop cleared)" if rc == 0 else f"failed: {err}")
    return
  if a.action == "release":
    # one-shot operator release for the VISION stop daemon (static-pedestrian case):
    # objstopd consumes /tmp/op_stop_release and forces RESUMING
    rc, _, err = ssh(a.ip, a.user, "touch /tmp/op_stop_release")
    print("⏩ RELEASE sent (objstopd will resume)" if rc == 0 else f"failed: {err}")
    return
  if a.action == "status":
    rc, out, err = ssh(a.ip, a.user,
                       f"echo -n 'ExpLong='; cat /data/params/d/ExperimentalLongitudinalEnabled 2>/dev/null; echo; "
                       f"echo -n 'onroad='; cat /data/params/d/IsOnroad 2>/dev/null; echo; "
                       f"ls {FLAG} >/dev/null 2>&1 && echo 'stop_flag=ARMED' || echo 'stop_flag=clear'")
    print(out or f"failed: {err}")
    return

  # check
  print(f"[check] config via ssh …")
  rc, out, err = ssh(a.ip, a.user,
                     "cat /data/params/d/ExperimentalLongitudinalEnabled 2>/dev/null; echo '|'; "
                     "cat /data/params/d/IsOnroad 2>/dev/null; echo '|'; "
                     "grep -q op_stop_requested /data/openpilot/selfdrive/controls/lib/longitudinal_planner.py && echo patched || echo NOTPATCHED")
  explong = onroad = patched = "?"
  if rc == 0:
    parts = out.split("|")
    explong = "1" in parts[0]
    onroad = len(parts) > 1 and "1" in parts[1]
    patched = len(parts) > 2 and "NOTPATCHED" not in parts[2]
  print(f"  OP-long param set      {yn(explong)}")
  print(f"  planner stop patch     {yn(patched)}")
  print(f"  device onroad          {yn(onroad)}   (camera/stream/braking only work onroad)")

  print(f"[check] sampling stream {a.ip}:{a.port} …")
  g = sample_stream(a.ip, a.port)
  if g["n"] == 0:
    print(f"  \033[31mno stream data\033[0m ({g.get('error','')}). If offroad, turn the car on & engage.")
  else:
    print(f"  stream records         {yn(True)} ({g['n']})")
    print(f"  --- longitudinal ---")
    print(f"  openpilot enabled      {yn(g['enabled'])}  state={g['state']}")
    print(f"  longActive (OP long)   {yn(g['longActive'])}  accel={g['accel']}  vEgo={g['vEgo']}")
    print(f"  --- JSON export (cp_export needs these) ---")
    print(f"  GPS fix (loc)          {yn(g['gps'])}  loc={g['loc']}")
    print(f"  modelV2 trajectory     {yn(g['modelV2_pos'])}")
    ready_long = bool(g["longActive"])
    ready_json = bool(g["gps"] and g["modelV2_pos"])
    print(f"\n  LONGITUDINAL ready: {yn(ready_long)}    JSON export ready: {yn(ready_json)}")
    if not ready_long:
      print("   → engage openpilot; confirm OP long (longActive ✓). If ✗ onroad, reboot after ExpLong=1.")
    if not ready_json:
      print("   → need a GPS fix + onroad model. Or run cp_export with --ref-lat/--ref-lon / --local-frame.")


if __name__ == "__main__":
  main()
