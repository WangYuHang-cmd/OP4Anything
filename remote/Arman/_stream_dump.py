#!/usr/bin/env python3
"""Dump what the device is actually putting on TCP 7700, so we can see whether modelV2
carries a trajectory. Run on the laptop:

    python3 _stream_dump.py 172.20.10.3
"""
import sys

from stream_lib import stream

ip = sys.argv[1] if len(sys.argv) > 1 else "172.20.10.3"

n = 0
seen_model = 0
for rec in stream(ip, 7700):
  n += 1
  m = rec.get("modelV2", {})
  loc = rec.get("loc", {})
  if m.get("_upd"):
    seen_model += 1
  if n <= 3 or (m.get("_upd") and seen_model <= 2):
    print(f"--- record {n} ---")
    print(f"  top-level keys: {sorted(rec.keys())}")
    print(f"  modelV2._upd={m.get('_upd')} _valid={m.get('_valid')} keys={sorted(m.keys())}")
    for k in ("pos_x", "pos_y", "vel_x"):
      v = m.get(k)
      if isinstance(v, list):
        print(f"    {k}: len={len(v)} head={[round(x, 2) for x in v[:5]]}")
      else:
        print(f"    {k}: {v}")
    print(f"  loc: lat={loc.get('lat')} lon={loc.get('lon')} yaw={loc.get('yaw')} "
          f"_valid={loc.get('_valid')}")
  if n >= 120:
    break

print(f"\n{n} records, {seen_model} with modelV2 updated")
