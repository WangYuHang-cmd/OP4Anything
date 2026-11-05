# Vision stop — stop sign / red light / pedestrian (comma device, on-board)

## v2.1 (2026-08-06): field-test fixes
rlog forensics on the 8/4 drives proved: stop-sign 3s auto-resume WORKS (standstill →
`starting`, accel 0.6); the "stuck" cases were pedestrian holds on the static test dummy
(by design) + `DisengageOnAccelerator=1` turning the driver's gas tap into a disengage.
- **Pedestrian**: person-class conf now 0.30 (`--ped-conf`; was the main field miss cause —
  device-pipeline eval on 38 dummy frames: 92% @v8n/320/0.30 vs ~misses at 0.4);
  **N-of-M confirm** (2 sightings in 1 s to stop, clear_sec sticky release) kills
  single-frame false stops. `yolov8s_320.onnx` on device as option (97% but 2 Hz —
  default stays v8n@5 Hz whose temporal redundancy wins).
- **Operator release**: `experiment.py release` (touches `/tmp/op_stop_release`) forces
  RESUMING — for the static-dummy case; >20 s ped-hold shows an escalation alert.
- **Client JSON**: exporter adds `stopFlag`; cp_export/UDP carry top-level `"stop": 0/1`.
- **Networking**: `find_comma.sh` (auto-discover on hotspot OR ethernet) + `ETHERNET_SETUP.md`.
- Pending user decision: `DisengageOnAccelerator=0` so a gas tap resumes instead of
  disengaging (Settings → Toggles → "Disengage on Accelerator" off).

## v2 (2026-07-25): distance-aware stops + reliable resume
Field problems fixed: imprecise stop position, difficult resume (green / sign-out-of-view /
wait), weak launch.

**Precise stops** — pinhole distance from bbox height (narrow cam f=2648, sign 0.75 m,
light housing 1.07 m), per-target 1-state Kalman filter (predict with vEgo odometry,
latency-compensated updates, outlier gate). The flag file now carries a target distance:
`/tmp/op_stop_requested` = `d=<m> t=<monotonic> src=v`; the patched planner glides onto it
with `v_cruise = sqrt(2*0.8*d_eff)` and latches a full stop near zero (no creep-through).
`d=0`/empty/garbled = stop-now (fail-safe); stale `t` (>1 s) = released (daemon-crash safe).
Stop targets: sign = d−3 m (`--sign-setback`), light = d−10 m (`--tl-setback`).
**Dilemma-zone guard**: if stopping needs >1.1 m/s², don't latch — alert and continue
(never brake into the middle of an intersection).

**Reliable resume** —
- *Red light*: while stopped, detection alternates narrow full-frame and a **wide-cam
  center-top ROI** (fisheye sees overhead lights the narrow cam loses inside ~17 m).
  Resume **only on confirmed green** (≥0.5 s); the "red absent timeout" rule is REMOVED
  (it ran red lights when the light left the frame). Escape hatches: driver gas press →
  resume; >120 s with no light visible → alert, keeps holding, human decides.
- *Stop sign*: stop, hold `--wait-sec` (default **3 s**) from standstill, resume — even if
  the sign is still visible (or no longer visible). Re-trigger suppressed by
  **pass-tracking** (odometry: the served sign can't re-latch during pull-away; a new sign
  ≥12 m ahead can — closely spaced intersections work). Fixed cooldown removed.
- *Launch*: device Honda interface now sets `startingState=True, startAccel=0.6`
  (backup `interface.py.bak_arman2`) — firm, bounded open-loop push off the line.

**Architecture** — inference thread (YUV subsampled 2× before RGB, adaptive input:
640 when vEgo>8 m/s for ~66 m range, else 320 at ~5 Hz) + 20 Hz control loop
(SubMaster carState → KF predict → state machine → atomic flag/status writes).
States: DRIVING / BRAKING / STOPPED_SIGN / STOPPED_RED / STOPPED_PED / RESUMING.
Manual stops still work: an empty `touch`ed flag file is treated as stop-now and objstopd
never deletes a file it didn't write (`src=v` tag).

Run: `objstopd.py [--arm] [--wait-sec 3] [--tl-setback 10] [--sign-setback 3]`
Tests: `test_stopsm.py` (KF accuracy/dropout/outliers, closed-loop ramp precision,
all resume scenarios, dilemma zone, flag protocol) — all green locally + on device.
Planner backup: `longitudinal_planner.py.bak_arman2`.

---
# v1 reference below

Camera-based auto-stop: when the road camera sees a **stop sign**, a **red light**, or a
**pedestrian in the forward path**, the car does a controlled decel-to-stop (via the planner
flag `/tmp/op_stop_requested`), waits, then resumes. Runs entirely **on the device**.

> ⚠️ openpilot's own model does NOT detect these — this is an added YOLOv8 detector. It is
> experimental, has NO stock AEB backup (OP long is on), and must be validated in SHADOW
> mode and tested only in a closed area with a driver ready to take over.

## Pipeline (all on-device, CPU)
```
camerad ──VisionIPC road frame(NV12)──► objstopd.py
   extract_image (NV12→RGB, numpy)
   YOLOv8n ONNX (onnxruntime CPU)  → person / stop sign / traffic light
   traffic-light crop → HSV → red/yellow/green
   relevance heuristics → active triggers
   StopSM state machine → stop / wait / resume
   SHADOW: log + /tmp/objstop_status.json   |   ARM: touch/rm /tmp/op_stop_requested
```

## Validated on the device (offroad, static images)
- person ✓ (bus.jpg → 4 people, 0.90/0.88/0.87)
- stop sign ✓ (0.67, correct box — even a symbol-only sign)
- traffic light ✓ + **colour = red** ✓ (0.73)
- colour classifier ✓ (synthetic red/green/yellow all correct)

**Inference speed (SDA845, CPU-only, onnxruntime):**
| input | infer | rate (fwd only) | use |
|---|---|---|---|
| 640 | ~616 ms | ~1.6 Hz | best range, small/distant lights |
| 480 | ~360 ms | ~2.8 Hz | balance |
| **320** | **~185 ms** | **~5.4 Hz** | **default — low-speed, closest range** |

Add ~50–100 ms/frame for NV12→RGB. At 320 the end-to-end rate is ~4 Hz. **Smaller input =
faster but shorter detection range** (distant traffic lights are the first to be missed).

## Files (on device `/data/objstop/`)
| file | role |
|---|---|
| `yolo_infer.py` | YOLOv8 ONNX + numpy post-proc + traffic-light colour |
| `objstopd.py` | camera → detect → state machine → shadow/arm |
| `objstop_view.py` | laptop viewer (pulls status+frame over SSH) |
| `yolov8n_320.onnx` / `_480` / `yolov8n.onnx` | models (match `--imgsz`) |

## Run — SHADOW FIRST (no braking)
```bash
# on the device (needs openpilot on PYTHONPATH, camera running = onroad)
cd /data/objstop
PYTHONPATH=/data/openpilot /usr/local/pyenv/versions/3.11.4/bin/python3 \
  objstopd.py --onnx yolov8n_320.onnx --imgsz 320 --save-every 0.3
# it prints [go]/[STOP] + writes /tmp/objstop_status.json and /tmp/objstop_last.jpg
```
Watch from the laptop:
```bash
python3 objstop_view.py --ip 192.168.1.231     # camera + boxes + STATE panel
```
Drive (or walk in front) past a stop sign / red light / person and confirm STATE flips to
STOP for the right reason — **while nothing touches the brakes**. Tune thresholds until
false-positives are rare and true events are caught.

## Arm (actually stop the car) — only after shadow looks good
```bash
... objstopd.py --onnx yolov8n_320.onnx --imgsz 320 --arm
```
Now a trigger creates `/tmp/op_stop_requested` → planner decels to a stop; on resume the
flag is removed. Requires OP longitudinal enabled + openpilot engaged. The daemon always
clears the flag on exit (no stale stop); a reboot also clears it (tmpfs).

## Behaviour / resume rules
- **stop sign**: stop, hold `--wait-sec` (default 2 s, timed from real standstill if carState
  is available), then resume; a `--cooldown` (6 s) suppresses re-stopping at the same sign.
- **red light**: hold until red has been absent for `--clear-sec` (i.e., green/gone).
- **pedestrian**: hold until no pedestrian in the forward zone for `--clear-sec`.
- A new hazard appearing while stopped extends the hold (safety).

## Tuning knobs (relevance)
`--conf` detection threshold · `--stop-min-h` / `--tl-min-h` / `--ped-min-h` how close (bbox
pixel height) before it counts · `--tl-max-cy` lights only in the upper part of the frame ·
`--ped-band-lo/hi` + `--ped-min-bottom` the "in front of me on the road" zone for people.

## Honest limitations
- **Reaction ~4 Hz** at 320 — fine for low speed, weak for fast-moving hazards.
- **Traffic-light relevance is crude**: any red light in the upper-central frame region &
  large enough triggers — it does NOT know which light governs your lane (cross-street reds
  can false-trigger). This is the least reliable target.
- **Pedestrian = "person in the forward zone"**, not true crossing-intent prediction; it
  will also stop for people standing near the path.
- **No stock AEB** while OP long is engaged — driver is the only safety net.
- Distant/small objects missed at 320; raise `--imgsz` (slower) for more range.

## Safety checklist
- [ ] Closed/empty area, low speed, driver hands ready, foot over brake.
- [ ] SHADOW-mode validated first: right STOPs, few false-positives.
- [ ] Confirm OP long engaged (LONG ● in controls_monitor / cp_view) before `--arm`.
- [ ] Verify resume works and no stale flag remains (`ls /tmp/op_stop_requested`).
- [ ] Reboot clears everything.

## Not yet done
- On-road validation of stop-sign / red-light / pedestrian on the live camera (needs the car
  onroad — offroad the camera daemon isn't running).
- Optional: autostart under manager; INT8 quantization for more speed; restrict lights to the
  ego lane using the model's lane lines.
