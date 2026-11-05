#!/usr/bin/env python3
"""recv_log.py — log the comma reg_export stream to CSV (and optional parquet).

Flattens nested JSON records to columns like `carControl.curvature`,
`longitudinalPlan.aTarget`, `modelV2.desiredCurvature`. Heavy arrays (trajectory,
speeds) are stored as JSON strings in their own columns so each row stays flat.

A short warm-up collects the full column set first (heavy-array columns only appear
on the 20 Hz frames), so the CSV header is complete.

Usage:
    python recv_log.py --ip 192.168.x.x --out drive.csv
    python recv_log.py --ip 192.168.x.x --out drive.parquet   # needs pandas+pyarrow
"""
import argparse
import csv
import json
import time

from stream_lib import stream

ARRAY_KEYS = {"pos_x", "pos_y", "pos_z", "vel_x", "orient_z", "laneLineProbs",
              "speeds", "accels", "jerks", "vel", "lat"}


def flatten(rec: dict) -> dict:
  out = {}
  for k, v in rec.items():
    if isinstance(v, dict):
      for kk, vv in v.items():
        col = f"{k}.{kk}"
        out[col] = json.dumps(vv, separators=(",", ":")) if isinstance(vv, (list, dict)) else vv
    else:
      out[k] = v
  return out


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ip", required=True)
  ap.add_argument("--port", type=int, default=7700)
  ap.add_argument("--out", default="reg_log.csv", help=".csv or .parquet")
  ap.add_argument("--warmup", type=int, default=80, help="records buffered to build the header")
  args = ap.parse_args()

  parquet = args.out.lower().endswith(".parquet")
  n = 0
  t0 = time.time()
  print(f"[recv_log] connecting to {args.ip}:{args.port} -> {args.out}", flush=True)

  if parquet:
    rows = []
    try:
      for rec in stream(args.ip, args.port):
        rows.append(flatten(rec))
        n += 1
        if n % 200 == 0:
          print(f"[recv_log] {n} rows ~{n/(time.time()-t0):.0f}Hz", flush=True)
    except KeyboardInterrupt:
      pass
    finally:
      import pandas as pd
      pd.DataFrame(rows).to_parquet(args.out)
      print(f"[recv_log] wrote {len(rows)} rows -> {args.out}", flush=True)
    return

  # CSV: warm up to collect the full header, then stream
  buf = []
  header = set()
  writer = None
  fout = None
  try:
    for rec in stream(args.ip, args.port):
      row = flatten(rec)
      n += 1
      if writer is None:
        buf.append(row)
        header |= row.keys()
        if len(buf) >= args.warmup:
          cols = sorted(header)
          fout = open(args.out, "w", newline="")
          writer = csv.DictWriter(fout, fieldnames=cols, extrasaction="ignore")
          writer.writeheader()
          for b in buf:
            writer.writerow(b)
          buf = []
          print(f"[recv_log] header ready ({len(cols)} cols), logging...", flush=True)
      else:
        writer.writerow(row)
      if writer and n % 200 == 0:
        fout.flush()
        print(f"[recv_log] {n} rows ~{n/(time.time()-t0):.0f}Hz", flush=True)
  except KeyboardInterrupt:
    pass
  finally:
    if writer is None and buf:  # never reached warmup
      cols = sorted(header)
      with open(args.out, "w", newline="") as f2:
        w = csv.DictWriter(f2, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(buf)
    if fout:
      fout.close()
    print(f"[recv_log] closed {args.out} ({n} rows)", flush=True)


if __name__ == "__main__":
  main()
