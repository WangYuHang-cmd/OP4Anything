# Experiment runbook — Civic longitudinal + STÄHLE JSON

Device (experimental comma): **192.168.1.231**. Run everything below **on the laptop**
(`~/Desktop/Drive/remote/Arman`), which can `ssh comma@192.168.1.231` and reach the stream.

## 0. Power on & get onroad
Turn the car on so openpilot goes **onroad** (camera + model + stream only run onroad).

## 1. Readiness check (run after engaging openpilot)
```bash
cd ~/Desktop/Drive/remote/Arman
python3 experiment.py --ip 192.168.1.231 check
```
Want to see:
- `OP-long param set ✓`, `planner stop patch ✓`, `device onroad ✓`
- `longActive (OP long) ✓`  → **openpilot is controlling longitudinal**
- `GPS fix ✓`, `modelV2 trajectory ✓`  → JSON export will be populated
- Bottom line: `LONGITUDINAL ready ✓   JSON export ready ✓`

If `longActive ✗` after engaging: the OP-long config needs a fresh boot →
`ssh comma@192.168.1.231 'sudo reboot'`, wait ~45 s, re-engage, re-check.

## 2. Longitudinal stop / go  ⚠️ closed area, driver ready, foot over brake
```bash
python3 experiment.py --ip 192.168.1.231 stop    # ■ controlled decel-to-stop
python3 experiment.py --ip 192.168.1.231 go      # ▶ resume
python3 experiment.py --ip 192.168.1.231 status  # config + flag state
```
The stop is openpilot's own jerk/accel-limited decel (smooth, not a hard brake). It only
acts when engaged + OP long. **No stock AEB while OP long is on — you are the safety net.**
First test from a slow crawl; verify smooth stop, then `go`.

## 3. STÄHLE / client JSON export (real-time)
```bash
cd ~/Desktop/Drive/remote/Arman
python3 cp_export.py --ip 192.168.1.231 --mode live --out-dir ./cp_out
# heartbeat should print:  [cp_export] OK -> track_live.{csv,json}  segs=N
```
Outputs (rewritten ~20 Hz):
- `./cp_out/track_live.json`  → client segment format
  `{ref:{latitude,longitude}, segments:[{start,end,velocity,radius,direction}]}`
- `./cp_out/track_live.csv`   → STÄHLE per-point curvepoints (East/North/theta/kappa/kph)

Record a whole driven route instead: `--mode record` → `route_track.{csv,json}` on Ctrl-C.
Fix the origin: `--ref-lat 37.7749295 --ref-lon -122.4194155`. No GPS at all: `--local-frame`
(body frame, not true North). If heartbeat says "waiting for GPS/modelV2", you're not onroad
with a fix yet.

Watch it: `python3 cp_view.py --ip 192.168.1.231` (North-up ENU map + θ/κ/direction tiles).

## 4. (Optional) vision auto-stop — SHADOW first
```bash
# on device: cd /data/objstop && PYTHONPATH=/data/openpilot \
#   /usr/local/pyenv/versions/3.11.4/bin/python3 objstopd.py --onnx yolov8n_320.onnx --imgsz 320 --save-every 0.3
# laptop:   python3 vision/objstop_view.py --ip 192.168.1.231
```
Shadow shows STOP/GO without braking. Add `--arm` only after it looks reliable.

## Revert longitudinal to stock (after experiments)
```bash
ssh comma@192.168.1.231 'cp /data/openpilot/selfdrive/controls/lib/longitudinal_planner.py.bak_arman \
  /data/openpilot/selfdrive/controls/lib/longitudinal_planner.py; \
  python3 -c "from openpilot.common.params import Params; Params().remove(\"ExperimentalLongitudinalEnabled\")"; sudo reboot'
```

## Verified offroad (2h before): config ✓, planner patch ✓, stop flag ✓, cp_export JSON ✓
## To confirm ONROAD (step 1): longActive ✓ + first smooth stop + JSON segs>0.
