#!/usr/bin/env python3
"""Device probe: which services are actually publishing, and is the device onroad.
Run on device: PYTHONPATH=/data/openpilot:/data python3 _verify_state.py"""
import sys
import time

sys.path.insert(0, "/data")
import cereal.messaging as messaging

SERVICES = ["deviceState", "pandaStates", "roadCameraState", "modelV2",
            "liveLocationKalman", "carState", "cameraOdometry"]

sm = messaging.SubMaster(SERVICES)
counts = {s: 0 for s in SERVICES}
started = None
panda = None

t0 = time.time()
while time.time() - t0 < 10:
  sm.update(100)
  for s in SERVICES:
    if sm.updated[s]:
      counts[s] += 1
  if sm.updated["deviceState"]:
    started = sm["deviceState"].started
  if sm.updated["pandaStates"] and len(sm["pandaStates"]):
    panda = sm["pandaStates"][0]

print(f"deviceState.started = {started}")
if panda is not None:
  print(f"pandaStates: ignitionLine={panda.ignitionLine} harness={panda.harnessStatus}")
print("\nmessages received in 10s:")
for s in SERVICES:
  flag = "" if counts[s] else "   <-- NOTHING"
  print(f"  {s:22s} {counts[s]:5d}{flag}")
