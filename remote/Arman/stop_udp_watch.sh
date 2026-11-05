#!/usr/bin/env bash
# stop_udp_watch.sh — sanity check: print the 0/1 datagrams arriving here (LAPTOP).
# Use only if THIS laptop is the UDP destination.
#   ./stop_udp_watch.sh 5005
PORT="${1:?usage: stop_udp_watch.sh <PORT>}"
python3 - "$PORT" <<'PY'
import socket, sys, time
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", port)); s.settimeout(5)
print(f"listening on udp/{port} (Ctrl-C to stop)")
last = None
try:
    while True:
        try:
            d, a = s.recvfrom(16)
        except socket.timeout:
            print("… no datagrams in 5s (sender running? right IP/port?)"); continue
        v = d.decode(errors="replace")
        if v != last:
            print(f"{time.strftime('%H:%M:%S')}  from {a[0]}  ->  {v}")
            last = v
except KeyboardInterrupt:
    pass
PY
