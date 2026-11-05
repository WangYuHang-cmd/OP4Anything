#!/usr/bin/env python3
"""stop_udp.py — RUNS ON THE COMMA. Send ONLY "0" or "1" over UDP, nothing else.

1 = the vision/stop system wants the vehicle stopped, 0 = drive/resume.
Reads the same flags objstopd writes:
  /tmp/op_stop_requested  (actuation) or /tmp/op_stop_intent (vision decision, shadow too)
Each datagram payload is a single ASCII byte: b"0" or b"1".

    python3 stop_udp.py 192.168.1.50 5005            # host port
    python3 stop_udp.py 192.168.1.50 5005 --hz 20    # send rate (default 10)
"""
import argparse
import os
import socket
import time

STOP_FILES = ("/tmp/op_stop_requested", "/tmp/op_stop_intent")


def stop_now():
  return b"1" if any(os.path.exists(p) for p in STOP_FILES) else b"0"


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("host")
  ap.add_argument("port", type=int)
  ap.add_argument("--hz", type=float, default=10.0)
  a = ap.parse_args()
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  dst = (a.host, a.port)
  period = 1.0 / max(a.hz, 0.1)
  print(f"[stop_udp] -> {a.host}:{a.port}  {a.hz:g} Hz  (payload: '0' / '1' only)", flush=True)
  while True:
    try:
      sock.sendto(stop_now(), dst)
    except OSError:
      pass
    time.sleep(period)


if __name__ == "__main__":
  main()
