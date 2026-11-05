#!/usr/bin/env python3
"""UDP transmission of the track-segment JSON — snippet for review.

This is exactly what our exporter (cp_export.py) does on the wire. Full pipeline:

  openpilot (comma device) --TCP 7700--> laptop --[this UDP sender]--> your receiver

Wire format
-----------
* One UDP datagram per update, plain UTF-8 JSON (no header, no framing, no
  compression), sent at <= 10 Hz (configurable) to HOST:PORT.
* Datagram payload = the agreed internal format, plus an explicit stop flag:

    {"ref":{"latitude":37.7749295,"longitude":-122.4194155},
     "stop":0,
     "segments":[
       {"start":{"x":0.0,"y":0.0},"end":{"x":28.19,"y":15.90},
        "velocity":4.19,"radius":35.21,"direction":"left"},
       ...]}

* "stop": 1 = the vehicle is being commanded to stop (hold / decel-to-stop active),
  0 = drive / resume. It reflects the live stop command on the car in real time.

* Coordinates: x = East [m], y = North [m], relative to `ref` (WGS-84, fixed once
  at mission start). radius = 0 -> straight, > 0 -> arc [m]; direction left/right;
  velocity in m/s; the final segment's velocity is 0.0 when the track ends in a stop.
* Typical payload is a few hundred bytes; we skip (never fragment) anything > 60 kB.

Open questions for you
----------------------
1. Destination: which IP:port should we send to on your machine?
2. Is one-JSON-per-datagram OK, or does your receiver expect a different framing /
   the native STÄHLE curvepoint packets instead? (We also produce the per-point
   STÄHLE table: Deltatime, velocity_kph, gear, index, East, North, theta, kappa.)
3. Is 10 Hz a good rate, and m/s the right unit for `velocity`?
"""
import json
import socket
import time

UDP_HOST, UDP_PORT = "192.168.1.50", 5005      # <- your receiver
SEND_HZ = 10.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
last_send = 0.0


def send_track(ref_lat, ref_lon, segments):
    """segments: list of {start:{x,y}, end:{x,y}, velocity, radius, direction}."""
    global last_send
    now = time.monotonic()
    if now - last_send < 1.0 / SEND_HZ:        # rate limit
        return
    last_send = now
    payload = json.dumps(
        {"ref": {"latitude": ref_lat, "longitude": ref_lon}, "segments": segments},
        separators=(",", ":")).encode("utf-8")
    if len(payload) > 60000:                   # keep one datagram; never fragment
        return
    sock.sendto(payload, (UDP_HOST, UDP_PORT))


if __name__ == "__main__":
    # demo: send one example track once per second
    demo = [
        {"start": {"x": 0.0, "y": 0.0}, "end": {"x": 28.19, "y": 15.90},
         "velocity": 4.19, "radius": 35.21, "direction": "left"},
        {"start": {"x": 28.19, "y": 15.90}, "end": {"x": 38.0, "y": 28.88},
         "velocity": 0.0, "radius": 0.0, "direction": "left"},
    ]
    while True:
        send_track(37.7749295, -122.4194155, demo)
        time.sleep(1.0)
