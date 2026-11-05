#!/usr/bin/env python3
"""stream_lib.py — thin client for the comma reg_export JSON stream.

No openpilot install needed — just stdlib. Connect to the exporter running on the
comma (TCP JSON-lines) and iterate decoded records, or register a callback.

Usage (real-time downstream):
    from stream_lib import stream
    for rec in stream("192.168.x.x"):          # comma IP on the phone hotspot
        curv = rec["carControl"]["curvature"]  # final lateral command (1/m)
        acc  = rec["longitudinalPlan"]["aTarget0"]  # near-term planned accel (accels[0])
        ...

Each `rec` is a dict, roughly:
    {
      "t_wall": <unix s>, "t_mono": <s>, "seq": <int>,
      "carState":   {vEgo, aEgo, steeringAngleDeg, ..., _upd, _valid, _mono},
      "carControl": {enabled, latActive, longActive, steer, curvature, accel, ...},
      "carOutput":  {steer, curvature, accel, ...},            # actually sent
      "controlsState": {state, desiredCurvature, curvature, lat{...}, ...},
      "longitudinalPlan": {aTarget, shouldStop, speeds[], accels[], ...},  # arrays only when _upd
      "modelV2":    {desiredCurvature, pos_x[], pos_y[], ..., ...},        # arrays only when _upd
      "loc":        {lat, lon, yaw, ...},
      "radar":      {status, dRel, vRel, ...},
    }
Heavy arrays (trajectory / speeds) are present only on frames where that 20 Hz
service updated (check `block["_upd"]` or `"pos_x" in rec["modelV2"]`).
"""
import json
import socket
import time
from collections.abc import Iterator


def stream(ip: str, port: int = 7700, reconnect: bool = True,
           timeout: float = 5.0) -> Iterator[dict]:
  """Yield decoded records from the exporter. Reconnects on drop by default."""
  while True:
    try:
      with socket.create_connection((ip, port), timeout=timeout) as s:
        s.settimeout(timeout)
        f = s.makefile("r", encoding="utf-8", newline="\n")
        for line in f:
          line = line.strip()
          if not line:
            continue
          try:
            yield json.loads(line)
          except json.JSONDecodeError:
            continue
    except (OSError, socket.timeout) as e:
      if not reconnect:
        raise
      print(f"[stream] disconnected ({e}); retrying in 1s...", flush=True)
      time.sleep(1.0)


def stream_callback(ip: str, on_record, port: int = 7700, **kw):
  """Call on_record(rec) for every record (blocking)."""
  for rec in stream(ip, port=port, **kw):
    on_record(rec)


if __name__ == "__main__":
  import argparse
  ap = argparse.ArgumentParser(description="print reg_export records")
  ap.add_argument("--ip", required=True)
  ap.add_argument("--port", type=int, default=7700)
  args = ap.parse_args()
  n = 0
  t0 = time.time()
  for rec in stream(args.ip, args.port):
    n += 1
    if n % 100 == 0:
      hz = n / (time.time() - t0)
      cs = rec.get("carState", {})
      cc = rec.get("carControl", {})
      print(f"[{n}] {hz:.0f}Hz vEgo={cs.get('vEgo')} "
            f"steer={cc.get('steer')} curv={cc.get('curvature')} "
            f"accel={cc.get('accel')} enabled={cc.get('enabled')}", flush=True)
