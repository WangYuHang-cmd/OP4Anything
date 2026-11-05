#!/usr/bin/env python3
"""Why is modeld silent? Checks the camera streams it depends on, then dumps its logs.
Run on device: PYTHONPATH=/data/openpilot:/data python3 _modeld_diag.py"""
import glob
import json
import os
import sys
import time

sys.path.insert(0, "/data")
import cereal.messaging as messaging

CAMS = ["roadCameraState", "wideRoadCameraState", "driverCameraState"]
sm = messaging.SubMaster(CAMS)
counts = {s: 0 for s in CAMS}
t0 = time.time()
while time.time() - t0 < 6:
  sm.update(100)
  for s in CAMS:
    if sm.updated[s]:
      counts[s] += 1

print("camera streams in 6s (modeld needs road + wideRoad):")
for s in CAMS:
  flag = "" if counts[s] else "   <-- NOTHING"
  print(f"  {s:22s} {counts[s]:5d}{flag}")

print("\nlast modeld / locationd log lines:")
seen = 0
for f in sorted(glob.glob("/data/log/swaglog*"), key=os.path.getmtime)[-6:]:
  for line in open(f, errors="ignore"):
    if '"modeld' not in line and '"locationd' not in line and 'modeld.py' not in line:
      continue
    try:
      d = json.loads(line)
    except Exception:
      continue
    msg = d.get("msg")
    text = msg if isinstance(msg, str) else json.dumps(msg, ensure_ascii=False)
    print(f"  [{d.get('level')}] {d.get('filename')}:{d.get('lineno')} {text[:220]}")
    seen += 1
if not seen:
  print("  (nothing found)")
