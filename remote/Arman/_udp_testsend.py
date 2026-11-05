#!/usr/bin/env python3
"""Send test datagrams shaped exactly like cp_export --udp output, so the receiving side
can confirm the path before the real stream runs.

    python3 _udp_testsend.py 172.20.10.2 5005 [seconds]

On the receiving machine, any of these will show the packets:
    nc -u -l 5005                                  (Linux/macOS)
    python3 -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('0.0.0.0',5005));print('listening');
                [print(s.recvfrom(65535)[0][:200]) for _ in iter(int,1)]"
    Wireshark filter: udp.port == 5005

If nothing arrives here but the sender reports no error, the packets are being dropped on
the receiving host — on Windows that is almost always Windows Defender Firewall blocking
inbound UDP for the listening program (same reason that machine ignores ping).
"""
import json
import socket
import sys
import time

host = sys.argv[1] if len(sys.argv) > 1 else "172.20.10.2"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5005
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 15.0

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((host, port))
print(f"sending from {s.getsockname()[0]}:{s.getsockname()[1]} -> {host}:{port} for {secs:.0f}s")

n = 0
errs = 0
t0 = time.time()
while time.time() - t0 < secs:
  n += 1
  # same envelope cp_export emits: ref + stop flag + segments
  payload = {
    "test": True,
    "seq": n,
    "ts": round(time.time(), 3),
    "ref": {"latitude": 37.7749295, "longitude": -122.4194155},
    "stop": n % 20 < 10,          # toggles so the receiver can see it change
    "segments": [
      {"start": {"x": 0.0, "y": 0.0}, "end": {"x": 5.0, "y": 0.0},
       "velocity": 2.0, "radius": 0.0, "direction": "left"},
      {"start": {"x": 5.0, "y": 0.0}, "end": {"x": 9.0, "y": 3.0},
       "velocity": 2.0, "radius": 12.5, "direction": "left"},
    ],
  }
  payload["stop"] = int(payload["stop"])
  try:
    s.send(json.dumps(payload).encode())
  except ConnectionRefusedError:
    errs += 1
    print(f"  #{n}: ICMP port unreachable -> host reachable, nothing listening on {port}")
  except OSError as e:
    errs += 1
    print(f"  #{n}: {e}")
  if n % 20 == 0:
    print(f"  sent {n} datagrams, {errs} errors")
  time.sleep(0.1)              # 10 Hz, same as cp_export default --udp-hz

print(f"\ndone: {n} datagrams sent, {errs} errors")
print("no errors here only means the packets left this machine — confirm on the receiver.")
