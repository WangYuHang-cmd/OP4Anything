#!/usr/bin/env python3
"""cp_export.py — real-time openpilot -> STÄHLE TrackDriver curvepoints exporter.

Consumes the reg_export TCP stream from a comma device and writes the client's two
target formats in the STÄHLE / client ENU frame (x=East, y=North, theta CCW from East,
kappa left-positive; origin = a lat/lon fixed once at mission start):

  <out>/track_live.csv   or  route_track.csv   -- STÄHLE per-point curvepoints
  <out>/track_live.json  or  route_track.json  -- client internal line/arc segments

Two data sources (both supported):
  --mode live    : each modelV2 frame -> the planned path ahead, transformed to ENU
                   using the live GPS position + heading (rolling; also keeps a short
                   ego-history tail so there are points "behind" the vehicle).
  --mode record  : accumulate the driven GPS route, then emit the whole track on exit
                   (Ctrl-C) or periodically.

Reference origin (set ONCE, never changed, per spec):
  --ref-lat/--ref-lon  : use these; else the first valid GPS fix is locked as origin.

  python3 cp_export.py --ip <comma_ip> --mode live
  python3 cp_export.py --ip <comma_ip> --mode record --ref-lat 37.7749295 --ref-lon -122.4194155
  python3 cp_export.py --selftest
"""
import argparse
import json
import math
import os
import signal
import sys
import time

import frame
import curvepoints as cp

try:
  from stream_lib import stream
except Exception:                       # pragma: no cover
  stream = None

HIST_TAIL = 5            # ego points kept "behind" the vehicle in live mode
RECORD_MIN_MOVE = 0.5    # m: dedup/dequantize accumulated GPS route


# ---------- track building ----------
def build_track(E, N, V, smooth=0):
  """ENU polyline -> dict(pts, thetas, kappas, rows, segments)."""
  pts = cp.resample_by_distance_rule(E, N, V)
  te = [p[0] for p in pts]
  tn = [p[1] for p in pts]
  thetas, kappas = cp.theta_kappa(te, tn, smooth=smooth)
  rows = cp.to_stahle_rows(pts, thetas, kappas)
  segs = cp.to_segments(pts, kappas)
  return {"pts": pts, "thetas": thetas, "kappas": kappas, "rows": rows, "segments": segs}


def model_to_enu(model, ego_enu, theta_veh, hist=None):
  """Transform a modelV2 planned path (car frame) into ENU (E,N,V) lists.

  hist = optional list of recent ego ENU (E,N,v) points to prepend as the "behind" tail.
  """
  px = model.get("pos_x") or []
  py = model.get("pos_y") or []
  vx = model.get("vel_x") or []
  E, N, V = [], [], []
  if hist:
    for he, hn, hv in hist[-HIST_TAIL:]:
      E.append(he); N.append(hn); V.append(hv)
  e0, n0 = ego_enu
  for i in range(len(px)):
    e, n = frame.car_point_to_enu(px[i], py[i], e0, n0, theta_veh)
    v = vx[i] if i < len(vx) else (vx[-1] if vx else 0.0)
    E.append(e); N.append(n); V.append(v)
  return E, N, V


# ---------- output ----------
def _atomic_write(path, text):
  tmp = path + ".tmp"
  with open(tmp, "w") as f:
    f.write(text)
  os.replace(tmp, path)


def write_stahle_csv(path, rows, origin):
  lines = [f"# STAHLE TrackDriver curvepoints  ref_lat={origin.lat} ref_lon={origin.lon} ref_alt={origin.alt}",
           "# frame: x=East y=North theta=CCW-from-East(rad) kappa=left-positive(1/m) velocity=kph",
           ",".join(cp.STAHLE_HEADER)]
  for r in rows:
    lines.append(",".join(str(c) for c in r))
  _atomic_write(path, "\n".join(lines) + "\n")


def write_segments_json(path, segs, origin, stop=0):
  doc = {"ref": {"latitude": origin.lat, "longitude": origin.lon},
         "stop": int(stop),
         "segments": segs}
  _atomic_write(path, json.dumps(doc, indent=2))


def write_outputs(out_dir, base, track, origin, stop=0):
  write_stahle_csv(os.path.join(out_dir, base + ".csv"), track["rows"], origin)
  write_segments_json(os.path.join(out_dir, base + ".json"), track["segments"], origin, stop=stop)


# ---------- runtime ----------
def _valid_fix(loc):
  if not loc:
    return False
  lat, lon = loc.get("lat"), loc.get("lon")
  return (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
          and (abs(lat) > 1e-6 or abs(lon) > 1e-6))


def run(args):
  if stream is None:
    print("stream_lib unavailable", file=sys.stderr)
    return 2
  os.makedirs(args.out_dir, exist_ok=True)
  origin = None
  if args.ref_lat is not None and args.ref_lon is not None:
    origin = frame.ENUOrigin(args.ref_lat, args.ref_lon, args.ref_alt or 0.0)
    print(f"[cp_export] ref fixed at {origin.lat},{origin.lon}")

  last_loc = None
  ego_hist = []            # accumulated ego ENU (E,N,v)
  route = []               # record mode: driven ENU polyline
  last_write = 0.0
  last_hb = 0.0            # heartbeat timer
  last_segs = 0           # last written segment count (for the heartbeat)
  base = "track_live" if args.mode == "live" else "route_track"

  # optional UDP output of the client-format JSON (one datagram per update)
  udp_sock, udp_addr, last_udp = None, None, 0.0
  if args.udp:
    import socket as _socket
    # HOST[:PORT] — a bare host falls back to --udp-port so the common case is just --udp <ip>
    host, sep, port_s = args.udp.rpartition(":")
    udp_addr = (host, int(port_s)) if sep else (args.udp, args.udp_port)
    udp_sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    print(f"[cp_export] UDP -> {udp_addr[0]}:{udp_addr[1]} at <= {args.udp_hz} Hz")

  def udp_send(track, stop=0):
    nonlocal last_udp
    if udp_sock is None or origin is None:
      return
    nowu = time.monotonic()
    if nowu - last_udp < 1.0 / max(args.udp_hz, 0.1):
      return
    last_udp = nowu
    payload = json.dumps({"ref": {"latitude": origin.lat, "longitude": origin.lon},
                          "stop": int(stop),
                          "segments": track["segments"]},
                         separators=(",", ":")).encode("utf-8")
    if len(payload) > 60000:          # keep it one datagram; oversized tracks are skipped
      print(f"[cp_export] UDP payload {len(payload)}B too large, skipped", file=sys.stderr)
      return
    try:
      udp_sock.sendto(payload, udp_addr)
    except OSError as e:
      print(f"[cp_export] UDP send failed: {e}", file=sys.stderr)

  def emit_record():
    if len(route) < 3:
      return
    E = [p[0] for p in route]; N = [p[1] for p in route]; V = [p[2] for p in route]
    track = build_track(E, N, V, smooth=args.smooth)
    write_outputs(args.out_dir, base, track, origin)
    udp_send(track)
    print(f"[cp_export] wrote {base}.{{csv,json}}  points={len(track['rows'])} "
          f"segments={len(track['segments'])}")

  if args.mode == "record":
    def _sig(*_):
      print("\n[cp_export] finalizing route ...")
      emit_record()
      sys.exit(0)
    signal.signal(signal.SIGINT, _sig)

  print(f"[cp_export] mode={args.mode}  streaming from {args.ip}:{args.port} ... (Ctrl-C to stop)")
  last_stop = 0            # client flag: 1 = a stop is being commanded on the car
  for rec in stream(args.ip, args.port):
    sf = rec.get("stopFlag")
    if isinstance(sf, dict):
      last_stop = int(sf.get("stop") or 0)
    loc = rec.get("loc")
    if loc:
      last_loc = loc
    # lock origin on first valid fix if not preset
    if origin is None and _valid_fix(last_loc):
      origin = frame.ENUOrigin(last_loc["lat"], last_loc["lon"], last_loc.get("alt", 0.0) or 0.0)
      print(f"[cp_export] ref locked at first fix {origin.lat},{origin.lon}")

    if origin is None and args.local_frame:
      origin = frame.ENUOrigin(0.0, 0.0, 0.0)
      print("[cp_export] --local-frame: dummy origin (0,0); NOT true North/ENU", flush=True)

    have_pose = origin is not None and _valid_fix(last_loc) and isinstance(last_loc.get("yaw"), (int, float))

    # heartbeat (~1 Hz) so during the experiment you can see if it is producing output
    now_hb = time.monotonic()
    if now_hb - last_hb >= 1.0:
      last_hb = now_hb
      mv0 = rec.get("modelV2") or {}
      if origin is None:
        msg = "waiting for GPS fix (or pass --ref-lat/--ref-lon, or --local-frame)"
      elif not have_pose:
        msg = "have origin, waiting for valid GPS pose (lat/lon/yaw)"
      elif args.mode == "live" and not mv0.get("pos_x"):
        msg = "GPS ok, waiting for modelV2 trajectory (is the car onroad?)"
      else:
        msg = f"OK -> {base}.{{csv,json}}  segs={last_segs}"
      print(f"[cp_export] {msg}", flush=True)

    if not have_pose and not args.local_frame:
      continue

    if have_pose:
      ego_e, ego_n, _ = origin.enu(last_loc["lat"], last_loc["lon"], last_loc.get("alt"))
      theta_veh = frame.yaw_ned_to_theta(last_loc["yaw"])
      ego_v = (last_loc.get("vel") or [0.0])[0] if isinstance(last_loc.get("vel"), list) else 0.0
    else:                                    # --local-frame fallback: body-fixed, North-up
      ego_e, ego_n, theta_veh, ego_v = 0.0, 0.0, math.pi / 2, 0.0

    if args.mode == "record":
      if not route or math.hypot(ego_e - route[-1][0], ego_n - route[-1][1]) >= RECORD_MIN_MOVE:
        route.append((ego_e, ego_n, max(ego_v, cp.V_FLOOR)))
      now = time.monotonic()
      if now - last_write > 2.0:            # periodic snapshot while recording
        last_write = now
        emit_record()
      continue

    # live mode
    mv = rec.get("modelV2") or {}
    if not (mv.get("_upd") and mv.get("pos_x")):
      # still track ego history for the "behind" tail
      if have_pose:
        if not ego_hist or math.hypot(ego_e - ego_hist[-1][0], ego_n - ego_hist[-1][1]) >= 1.0:
          ego_hist.append((ego_e, ego_n, max(ego_v, cp.V_FLOOR)))
          ego_hist[:] = ego_hist[-HIST_TAIL:]
      continue
    E, N, V = model_to_enu(mv, (ego_e, ego_n), theta_veh, hist=ego_hist)
    if len(E) < 3:
      continue
    track = build_track(E, N, V, smooth=args.smooth)
    last_segs = len(track["segments"])
    now = time.monotonic()
    if now - last_write > 0.05:             # cap file writes ~20 Hz
      last_write = now
      write_outputs(args.out_dir, base, track, origin, stop=last_stop)
    udp_send(track, stop=last_stop)
    if args.stdout:
      print(json.dumps({"ref": {"latitude": origin.lat, "longitude": origin.lon},
                        "stop": last_stop,
                        "segments": track["segments"]}), flush=True)
  return 0


# ---------- selftest ----------
def _selftest():
  ok = True

  def chk(name, cond):
    nonlocal ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond

  origin = frame.ENUOrigin(37.7749295, -122.4194155, 0.0)
  # vehicle facing East (yaw=pi/2 -> theta 0), model path curving LEFT (toward -y=left)
  # car frame: y = Right, so a left curve has y decreasing (negative).
  px = [float(i) for i in range(0, 40, 2)]
  py = [-0.02 * (x ** 2) for x in px]          # bending left (negative y = left)
  vx = [8.0] * len(px)
  model = {"pos_x": px, "pos_y": py, "vel_x": vx, "_upd": True}
  theta_veh = frame.yaw_ned_to_theta(math.pi / 2)   # facing East
  E, N, V = model_to_enu(model, (0.0, 0.0), theta_veh)
  track = build_track(E, N, V)
  midk = track["kappas"][3:-3]
  chk("left-curving model -> kappa>0 (left positive)", all(k > 0 for k in midk))
  chk("segments contain a left arc", any(s["direction"] == "left" and s["radius"] > 0
                                         for s in track["segments"]))
  chk("stahle rows velocity_kph>0", all(r[1] > 0 for r in track["rows"]))
  chk("stahle rows 9 cols", all(len(r) == 9 for r in track["rows"]))

  # facing East, straight ahead -> theta ~ 0, points go +East
  py0 = [0.0] * len(px)
  E0, N0, V0 = model_to_enu({"pos_x": px, "pos_y": py0, "vel_x": vx}, (0.0, 0.0), theta_veh)
  chk("E-facing straight -> +East", E0[-1] > 30 and abs(N0[-1]) < 1e-6)
  t0 = build_track(E0, N0, V0)
  chk("E-facing straight -> theta~0", all(abs(t) < 1e-3 for t in t0["thetas"]))

  # file writers round-trip
  d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_out")
  os.makedirs(d, exist_ok=True)
  write_outputs(d, "selftest", track, origin)
  with open(os.path.join(d, "selftest.json")) as f:
    doc = json.load(f)
  chk("json has ref lat/lon", doc["ref"]["latitude"] == origin.lat)
  chk("json has stop flag 0/1", doc.get("stop") in (0, 1))
  chk("json has segments", len(doc["segments"]) >= 1)
  with open(os.path.join(d, "selftest.csv")) as f:
    head = f.readline()
  chk("csv has ref header", "ref_lat" in head)

  print("ALL CP_EXPORT SELFTESTS OK" if ok else "CP_EXPORT SELFTESTS FAILED")
  return ok


def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--ip")
  ap.add_argument("--port", type=int, default=7700,
                  help="source port: the comma's reg_export TCP stream (default 7700). "
                       "The client's UDP destination port is --udp-port, not this.")
  ap.add_argument("--mode", choices=["live", "record"], default="live")
  ap.add_argument("--ref-lat", type=float, dest="ref_lat")
  ap.add_argument("--ref-lon", type=float, dest="ref_lon")
  ap.add_argument("--ref-alt", type=float, dest="ref_alt", default=0.0)
  ap.add_argument("--out-dir", dest="out_dir", default="./cp_out")
  ap.add_argument("--smooth", type=int, default=None,
                  help="moving-average window on E,N (default 5 in record, 0 in live)")
  ap.add_argument("--stdout", action="store_true", help="also emit each frame's segment JSON to stdout")
  ap.add_argument("--udp", default=None, metavar="HOST[:PORT]",
                  help="also send the client-format JSON as UDP datagrams (one JSON per datagram); "
                       "a bare host uses --udp-port")
  ap.add_argument("--udp-port", dest="udp_port", type=int, default=5005,
                  help="destination port when --udp gives a bare host (default 5005)")
  ap.add_argument("--udp-hz", dest="udp_hz", type=float, default=10.0,
                  help="max UDP send rate (default 10 Hz)")
  ap.add_argument("--local-frame", dest="local_frame", action="store_true",
                  help="fallback when no GPS: body-fixed North-up frame (NOT true North)")
  ap.add_argument("--selftest", action="store_true")
  args = ap.parse_args()

  if args.selftest:
    raise SystemExit(0 if _selftest() else 1)
  if not args.ip:
    ap.error("--ip required (or --selftest)")
  if args.smooth is None:
    args.smooth = 5 if args.mode == "record" else 0
  raise SystemExit(run(args))


if __name__ == "__main__":
  main()
