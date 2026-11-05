# Arman — openpilot → STÄHLE TrackDriver curvepoints (real-time)

Convert openpilot's planning / GPS trajectory into the curvepoint formats the client
(STÄHLE TrackDriver ecosystem) consumes, **in real time**, from the reg_export TCP
stream — no openpilot install needed on the laptop (pure stdlib; matplotlib only for
the viewer).

## Target frame & sign convention (from the CP Definition PDF + the client's engineer)
STÄHLE / client **ENU** frame — the origin `(0,0)` is a lat/lon fixed **once** at mission
start (WGS84) and never changed:

| quantity | convention |
|---|---|
| PositionX | **East** [m], relative to ref |
| PositionY | **North** [m], relative to ref |
| Theta | tangent heading [rad], **East = 0, counter-clockwise positive** (North = +π/2), range ±π |
| Kappa | curvature = 1/R [1/m], **left turn positive** |
| Velocity | **> 0** always (else the vehicle stands still) |

openpilot is different (Calibrated/Car frame = **Forward, Right, Down**; NED yaw; car-frame
κ is *right*-positive), so we transform:

```
theta = pi/2 - yaw_ned                       # North(yaw0)->pi/2, East(yaw pi/2)->0
E = E0 + fx*cos(theta_veh) + fy*sin(theta_veh)   # fx=Forward, fy=Right
N = N0 + fx*sin(theta_veh) - fy*cos(theta_veh)
kappa  : recomputed in ENU (kappa = (xE'*yN'' - xE''*yN')/(...)^1.5) so LEFT/CCW is +.
```
All of this is verified by unit tests (`frame.py --test`, `curvepoints.py --test`).

## Distance rule (point spacing, from the PDF)
```
d = v[kph]/3.6 * dsdv,  dsdv = 0.3,  min 0.6 m, max 5 m   ->  d = clip(v_mps*0.3, 0.6, 5)
```

## Two output formats (both produced)
1. **STÄHLE native curvepoints** — `*.csv`, one row per point, columns:
   `Deltatime_s, velocity_kph, gear(99), index, PositionX_East_m, PositionY_North_m,
   theta_rad, kappa_1pm, long_accel_mss(=0)`. This is the "10000" layout the robot
   consumes directly.
2. **Client internal segment JSON** — `*.json`:
   ```json
   { "ref": {"latitude": .., "longitude": ..},
     "segments": [ {"start": {"x": E, "y": N}, "end": {"x": E, "y": N},
                    "velocity": <m/s>, "radius": <m, 0=straight>, "direction": "left|right"} ] }
   ```
   The client has a wrapper that turns this into the STÄHLE format. The line/arc split
   here is a straightforward, sign-correct approximation — their wrapper is authoritative.

> **Units note:** STÄHLE curvepoints use **kph**; the segment JSON keeps openpilot's
> native **m/s** (the client example's `velocity: 2.0` reads as m/s). Flagged here so the
> client can adjust if their wrapper expects otherwise.

## Files
| file | what |
|---|---|
| `frame.py` | WGS84 geodetic→ENU, `yaw_ned_to_theta`, `car_point_to_enu` (pure math) |
| `curvepoints.py` | distance-rule resample, ENU θ/κ, STÄHLE rows, line/arc segments |
| `cp_export.py` | **main**: stream → both formats, `live` / `record` modes |
| `cp_view.py` | **live viewer** (North-up ENU map + tiles + delay), run while driving |
| `stream_lib.py` | vendored reg_export TCP client (JSON-lines, auto-reconnect) |
| `cp_slides.html` | slide deck explaining the whole approach |

## Data source
The comma device runs the `reg_export` exporter (sunnypilot 0.9.7.1) serving JSON-lines
on **TCP :7700**. Fields used: `loc.{lat,lon,alt,yaw}` (yaw = `calibratedOrientationNED[2]`),
`modelV2.{pos_x,pos_y,vel_x}`. Data only flows when the car is **onroad** with a GPS fix.

## Usage
```bash
# self-tests (no device needed)
python3 frame.py --test
python3 curvepoints.py --test
python3 cp_export.py --selftest
python3 cp_view.py --selftest          # writes cp_view_selftest.png

# LIVE: turn openpilot's planned path ahead into curvepoints, rolling
python3 cp_export.py --ip <comma_ip> --mode live --out-dir ./cp_out
#   -> ./cp_out/track_live.csv  and  track_live.json  (rewritten ~20 Hz)

# RECORD: drive a route, accumulate it, write the whole track on Ctrl-C
python3 cp_export.py --ip <comma_ip> --mode record --out-dir ./cp_out
#   -> ./cp_out/route_track.csv  and  route_track.json

# fix the reference origin explicitly (else first GPS fix is locked as origin)
python3 cp_export.py --ip <comma_ip> --ref-lat 37.7749295 --ref-lon -122.4194155

# WATCH while driving (run alongside the exporter)
python3 cp_view.py --ip <comma_ip>
```

### Options
- `--mode live|record`
- `--ref-lat/--ref-lon[/--ref-alt]` — fixed origin; omit to lock the first valid GPS fix.
- `--out-dir` — output directory (default `./cp_out`).
- `--smooth N` — moving-average window on E,N (default 5 in record, 0 in live) — GPS filtering per the PDF.
- `--stdout` — also emit each frame's segment JSON to stdout for a live downstream.
- `--local-frame` — fallback when no GPS: body-fixed North-up frame (NOT true North).

## Validating the sign convention live
On `cp_view`: steer **left** → the track bends **counter-clockwise**, the CURVATURE tile
shows **κ > 0 / DIR LEFT** (green); steer **right** → clockwise, **κ < 0 / DIR RIGHT**
(orange). Heading θ is East=0 and increases CCW (North shows ~90°). If any of these read
inverted on the real car, the yaw or y-sign assumption is wrong — fix in `frame.py`.
