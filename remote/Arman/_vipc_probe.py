#!/usr/bin/env python3
"""Which VisionIPC streams is camerad actually serving, and do frames arrive?

Run on device: PYTHONPATH=/data/openpilot:/data python3 _vipc_probe.py

cameraState (cereal) and the VisionIPC frame buffers are separate paths — camerad can be
publishing 20 Hz of cameraState metadata while the VisionIPC stream delivers nothing, which
is exactly what makes modeld sit in its recv loop at ~0.6% CPU producing no modelV2.
"""
import sys
import time

sys.path.insert(0, "/data")

try:
  from msgq.visionipc import VisionIpcClient, VisionStreamType
except ImportError:
  from cereal.visionipc import VisionIpcClient, VisionStreamType

print("streams camerad advertises:")
try:
  avail = VisionIpcClient.available_streams("camerad", False)
  for s in sorted(avail, key=str):
    print(f"  {s}")
  if not avail:
    print("  (none)")
except Exception as e:
  print(f"  available_streams failed: {e}")

WANT = [
  ("VISION_STREAM_ROAD", VisionStreamType.VISION_STREAM_ROAD),
  ("VISION_STREAM_WIDE_ROAD", VisionStreamType.VISION_STREAM_WIDE_ROAD),
  ("VISION_STREAM_DRIVER", VisionStreamType.VISION_STREAM_DRIVER),
]

for name, st in WANT:
  print(f"\n--- {name} ---")
  c = VisionIpcClient("camerad", st, True)
  t0 = time.time()
  while not c.connect(False) and time.time() - t0 < 5:
    time.sleep(0.1)
  if not c.is_connected():
    print("  NOT CONNECTED (camerad is not serving this stream)")
    continue
  print(f"  connected: {c.width}x{c.height} buffer_len={c.buffer_len}")

  got = 0
  first = last = None
  t0 = time.time()
  while time.time() - t0 < 4:
    buf = c.recv()
    if buf is not None:
      got += 1
      if first is None:
        first = c.frame_id
      last = c.frame_id
  if got:
    print(f"  frames in 4s: {got}  (frame_id {first} -> {last})   OK")
  else:
    print("  frames in 4s: 0   <-- NO FRAMES; this is what stalls modeld")
