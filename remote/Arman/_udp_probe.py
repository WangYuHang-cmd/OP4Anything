#!/usr/bin/env python3
"""Probe a UDP destination the way cp_export --udp actually sends.

    python3 _udp_probe.py 172.20.10.2 5005

UDP is fire-and-forget, so "no error" is not proof of delivery. What this can tell apart:
  ICMP port unreachable  -> host reached us back: routing is fine, nothing is listening yet
  nothing at all         -> either a listener is there and silently consuming, or a
                            firewall is dropping; check on the receiving machine
  network unreachable    -> routing problem on this laptop
"""
import socket
import sys
import time

host = sys.argv[1] if len(sys.argv) > 1 else "172.20.10.2"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5005

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.0)
s.connect((host, port))          # connect() so the kernel reports ICMP errors back to us
print(f"local {s.getsockname()[0]}:{s.getsockname()[1]} -> {host}:{port}")

for i in range(5):
  try:
    s.send(b'{"probe":%d}' % i)
    print(f"  sent #{i}: no error")
  except ConnectionRefusedError:
    print(f"  sent #{i}: ICMP port unreachable -> HOST REACHED, no listener on {port}")
  except OSError as e:
    print(f"  sent #{i}: {e}")
  time.sleep(0.4)

print("\nOn the receiving machine, confirm with:  nc -u -l 5005")
