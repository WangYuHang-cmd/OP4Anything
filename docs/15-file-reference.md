# File reference

This page lists every file in the repository: what it does, where it runs, how to call it, what it needs, which era it belongs to and which document explains it. The tables follow the directory layout (`find remote docs -type f`, plus the root files) and were checked against each file's docstring and argument parser. The appendix collects the constants, defaults, paths and flag files that the code defines, each traced to a file and a symbol.

## At a glance

| | |
|---|---|
| Audience | Developers and maintainers |
| Runs on | Laptop and device; see the "Runs on" column of each table |
| Era | Both: Era 1 — sunnypilot 0.9.7.1, and Era 2 — openpilot v0.11.1 `release-tizi` + dashcam-anywhere |
| Status | Reference for the redacted snapshot published with these docs |
| Key files | [`remote/`](../remote/), [`remote/Arman/`](../remote/Arman/), [`remote/Arman/vision/`](../remote/Arman/vision/), [`remote/Arman/dashcam_anywhere/`](../remote/Arman/dashcam_anywhere/), [documentation index](README.md) |

## Legend

| Column | Values |
|---|---|
| Runs on | **laptop** (the operator's computer with Python 3; the shell scripts assume Linux), **device** (on the comma 3X, over SSH), **both**, or **—** for documents and data files |
| Era | **1** = Era 1 — sunnypilot 0.9.7.1 (2026‑07 → 2026‑08; Honda Civic + truck/bench no‑CAN). **2** = Era 2 — openpilot v0.11.1 `release-tizi` + dashcam‑anywhere (from 2026‑10‑03; robots/small vehicles). **1+2** = used in both. **—** = needs no device |
| Dependencies | **stdlib** = Python standard library only. **matplotlib**, **numpy**, **pandas** and so on = pip packages. **device openpilot** = the `cereal`, `msgq` and `openpilot.*` modules of the openpilot or sunnypilot install on the device (they cannot be installed on a laptop). **ssh** = an OpenSSH client with key access as the lowercase user `comma` |
| Docs | The primary document first, then other documents that also cover the file. "Erratum N" points to the [errata table](16-errata-and-crosswalk.md#errata), "A-item An" to the [additional findings](16-errata-and-crosswalk.md#additional-inconsistencies-found-in-this-review) |
| Dates | "Last modified" is the file's original modification date from before redaction; the file times in this snapshot or a clone may differ. Dates that a note states itself (for example the STOP_SIGN_VISION version headers) are quoted from the note |

| Status | Meaning |
|---|---|
| current | Works with the device as it is now (era 2), or needs no device at all |
| historical | Written for the era‑1 device. That device state was erased by the re-flash, so live use needs the era‑1 setup again. Offline `--test` and `--selftest` modes still run |
| superseded | Replaced by another file in this repository |
| diagnostic | A one-off probe kept for troubleshooting |
| sample | Generated output kept as an example |
| legacy-duplicate | An older copy kept for one specific reason |
| reference | Notes, slides and snippets to read, or tools whose inputs are not included |

> [!WARNING]
> **Historical (sunnypilot era).** Every era‑1 change on the device (the patched openpilot files, `/data/objstop/`, the reg_export exporter, the launchers and the flag files) was erased when the device was re-flashed for era 2, at an unrecorded date between 2026‑08‑13 and 2026‑10‑03. Files marked "historical" describe or need that state.

> [!IMPORTANT]
> **Inferred; verify with `nc -z $COMMA_IP 7700`.** Nothing in `remote/Arman/dashcam_anywhere/` reinstalls reg_export or objstopd, so the era‑2 device most likely serves no telemetry on TCP 7700 and runs no vision stop daemon. For objstopd, `ssh comma@$COMMA_IP 'ls -d /data/objstop'` should report that the folder does not exist. Set `COMMA_IP` as shown under [Command conventions](#command-conventions).

### Command conventions

Command blocks start with a comment that says where they run; laptop commands start from the root of your clone. Set `$COMMA_IP` once per shell, either by discovery or by hand, and check that you reached your own device:

```bash
# laptop
cd remote/Arman && export COMMA_IP=$(./find_comma.sh)   # or by hand, e.g. export COMMA_IP=192.168.43.1
ssh comma@$COMMA_IP 'cat /data/params/d/DongleId'       # must print your device's dongle id
```

On the device, use the era-correct interpreter listed in [Device interpreters](#device-interpreters).

## Directory overview

| Directory | Files | What lives there |
|---|---|---|
| repository root | 4 | Landing page, license, third-party notices, `.gitignore` |
| [`remote/`](../remote/) | 16 | The era‑1 telemetry exporter and its laptop clients, control-chain notes, Frenet tools, slides |
| [`remote/Arman/`](../remote/Arman/) | 35 | Curvepoints pipeline, client link, 0/1 stop signal, Civic experiment control, vision stop daemon, era‑1 no‑CAN patchers, diagnostics, operator notes |
| [`remote/Arman/vision/`](../remote/Arman/vision/) | 6 | YOLO inference, status viewer, state-machine tests, pedestrian study, design note, legacy daemon copy |
| [`remote/Arman/dashcam_anywhere/`](../remote/Arman/dashcam_anywhere/) | 6 | The era‑2 patch, its control and status scripts, the calibration replay, two notes |
| [`remote/Arman/_selftest_out/`](../remote/Arman/_selftest_out/) | 2 | Sample outputs of `cp_export.py --selftest` |
| [`docs/`](README.md) | 17 + 1 image | These documents and `img/objstop_view_selftest.png` |

`remote/` is a redacted snapshot of the laptop work folder. If you want the original paths from the notes (`~/Desktop/Drive/remote/...`), link your clone there: `mkdir -p ~/Desktop/Drive && ln -s <clone>/remote ~/Desktop/Drive/remote`, where `<clone>` is the clone's absolute path ([02](02-setup-ssh-networking.md#original-paths-optional-symlink)).

## Repository root

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`README.md`](../README.md) | Repository landing page with links into these docs | — | — | — | — · current | [index](README.md) |
| [`LICENSE`](../LICENSE) | MIT License for the original work in this repository; portions derived from third-party projects keep their own licenses | — | — | — | — · current | this page; [landing page](../README.md) |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | Notices for openpilot and sunnypilot (MIT; where their code or excerpts appear), Ultralytics YOLOv8 (AGPL‑3.0; no code and no weights included) and the Python packages; non-affiliation statement; research-only caution | — | — | — | — · current | this page; [01](01-overview.md) |
| [`.gitignore`](../.gitignore) | Keeps tool output (`cp_out/`, `reg_log.csv`, `*.parquet`, `*.tmp`), device data (`data/`, `replay_rlogs/`, `robot_data/`, `*.hevc`, `*.zst`, `*.ts`, `*.mp4`, `*.wav`, `*.raw`), model weights (`*.onnx`, `*.pt`), Python caches, virtual environments and editor folders out of git | — | — | — | — · current | this page |

## The remote folder

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`controls_monitor.py`](../remote/controls_monitor.py) | Terminal table of COMMAND / SENT‑CAN / MEASURED for steering angle, steering rate, steering torque, driver torque, curvature, speed, acceleration, gas and brake (self-calibrated %); redraws about 10 times per second | laptop | `--ip IP` (required unless `--selftest`), `--port 7700`, `--csv FILE` (scalar fields of carState, carControl, carOutput, controlsState; header from the first record), `--selftest` (3 synthetic frames) | stdlib | 1 · historical; the "NOT sent to CAN" banner is hard-coded (erratum 16) | [03](03-telemetry-stream.md); also [04](04-control-principles-and-frenet.md), [16](16-errata-and-crosswalk.md) |
| [`controls_principles.md`](../remote/controls_principles.md) | Chinese quick reference of the sunnypilot 0.9.7.1 control chain on the 2020 Civic Bosch: lateral (curvature → torque → CAN), longitudinal, pedal sensors, command vs measured, frames and signs, porting to a bus. Its `file:line` references point into the device's sunnypilot source, not into this repository. Last modified 2026‑07‑14 | — | — | — | 1 · reference; describes the stock-PCM configuration only (erratum 16) | [04](04-control-principles-and-frenet.md); also [16](16-errata-and-crosswalk.md) |
| [`dashboard.py`](../remote/dashboard.py) | Live dashboard: vehicle-frame bird's-eye view (planned path, 4 lane lines, 2 road edges, lead), time series of speed, planned accel (throttle green / brake red) and curvature, status strip with measured pedal % | laptop | `--ip IP` (required, even with `--selftest`), `--port 7700`, `--window 12` (s), `--selftest` (writes `dashboard_selftest.png` to the current directory) | matplotlib | 1 · historical; set-speed line in km/h on an m/s axis (erratum 26); the docstring's steering-angle time series is not drawn (A-item A17) | [03](03-telemetry-stream.md); also [16](16-errata-and-crosswalk.md) |
| [`dashboard_selftest.png`](../remote/dashboard_selftest.png) | Render of `dashboard.py --ip x --selftest` (1540 × 880) | — | — | — | — · sample | [03](03-telemetry-stream.md) |
| [`exporter_device.py`](../remote/exporter_device.py) | The reg_export exporter, baseline of 2026‑07‑14: subscribes read-only (native msgq) to 9 services and serves one compact JSON line per `carState` update over TCP, with a per-client queue of 300 records (oldest dropped); derives `controlsState.desSteerAngleDeg`. Installed on the device as `/data/openpilot/tools/reg_export/exporter.py`. Has no `stopFlag` | device | `--port 7700`, `--bind 0.0.0.0`; the environment variables `REG_EXPORT_PORT` and `REG_EXPORT_BIND` take precedence | device openpilot (`cereal.messaging`) | 1 · historical (errata 8, 9) | [03](03-telemetry-stream.md); also [06](06-client-interface-spec.md), [14](14-device-changes-and-revert.md), [16](16-errata-and-crosswalk.md) |
| [`frenet.py`](../remote/frenet.py) | Vehicle-agnostic outputs from one `modelV2` block (car frame, κ > 0 = right): `reference_line()`, `frenet_sd()` (s, d against the lane-centre reference), `path_profile()` (s, x, y, θ, κ, v, a), `to_csv()` | laptop | `--test` (7 checks); without it, prints the docstring | stdlib | — · current | [04](04-control-principles-and-frenet.md) |
| [`frenet_selftest.png`](../remote/frenet_selftest.png) | Render of `frenet_view.py --selftest` (1430 × 880) | — | — | — | — · sample | [04](04-control-principles-and-frenet.md) |
| [`frenet_view.py`](../remote/frenet_view.py) | Four live panels: d(s); κ(s) with the bus steering limit ±tan(δmax)/L; v(s) and a(s); bus transferability (required \|v²κ\| against the bus lateral-acceleration limit, shaded red where exceeded) | laptop | `--ip IP` (required unless `--selftest`), `--port 7700`, `--bus-wheelbase 12`, `--bus-max-steer-deg 40`, `--bus-max-lat-acc 2.0`, `--dump-csv DIR` (one `traj_<unix s>.csv` per second), `--selftest` (writes `frenet_selftest.png`) | matplotlib | 1 · historical | [04](04-control-principles-and-frenet.md) |
| [`live_plot.py`](../remote/live_plot.py) | Simple rolling plot in four rows: speed (vEgo, vCruise), curvature (model, carControl, controlsState desired), accel (`aTarget0` vs `carControl.accel`), steering angle; keeps 2000 samples | laptop | `--ip IP` (required), `--port 7700`, `--seconds 20` | matplotlib | 1 · historical (errata 10, 26) | [03](03-telemetry-stream.md) |
| [`openpilot_controls_slides.html`](../remote/openpilot_controls_slides.html) | Six-slide English deck "openpilot Control Module — planning to actuation, and porting to a bus" (arrow keys navigate; print to PDF). GitHub shows the source, so open it locally | — | — | a browser | 1 · reference; slide 3 shows the pre‑2026‑07‑17 configuration (erratum 16) | [04](04-control-principles-and-frenet.md); also [16](16-errata-and-crosswalk.md) |
| [`openpilot_controls_slides.pdf`](../remote/openpilot_controls_slides.pdf) | Six-page PDF print of the same deck (created 2026‑07‑14 by headless Chrome, according to its metadata); renders on GitHub | — | — | — | 1 · reference; slide 3 as in the HTML deck (erratum 16) | [04](04-control-principles-and-frenet.md) |
| [`README.md`](../remote/README.md) | Original laptop-client note (English, with a Chinese section): hotspot setup, manual exporter start in `tmux`, tool usage, the "Control-command & trajectory tools (added)" list and the record schema. Last modified 2026‑07‑14 | — | — | — | 1 · historical (errata 8, 10, 16) | [03](03-telemetry-stream.md); also [01](01-overview.md), [16](16-errata-and-crosswalk.md) |
| [`recv_log.py`](../remote/recv_log.py) | Logs the stream to CSV (columns `block.field`, arrays stored as JSON strings, header built from the first `--warmup` records) or to parquet | laptop | `--ip IP` (required), `--port 7700`, `--out reg_log.csv` (a name ending in `.parquet` switches format), `--warmup 80` | stdlib; pandas + pyarrow for parquet | 1 · historical (erratum 10) | [03](03-telemetry-stream.md) |
| [`stream_lib.py`](../remote/stream_lib.py) | Client of the TCP JSON-lines stream: `stream(ip, port=7700, reconnect=True, timeout=5.0)` yields one dict per record and reconnects after 1 s; `stream_callback(ip, on_record, port=7700, **kw)` | laptop | `--ip IP` (required), `--port 7700`; prints the rate and a few fields every 100 records | stdlib | 1 · historical (erratum 10) | [03](03-telemetry-stream.md) |
| [`unified.py`](../remote/unified.py) | One big-font screen: bird's-eye view, 8 tiles (speed, throttle/brake, steering angle with its command, curvature with the bus lateral-acceleration check, gas, brake, torque command, turn radius) and a LIVE/STALE/e2e indicator | laptop | `--ip IP` (required unless `--selftest`), `--port 7700`, `--bus-max-lat-acc 2.0`, `--selftest` (writes `unified_selftest.png`) | matplotlib | 1 · historical (erratum 24) | [03](03-telemetry-stream.md) |
| [`unified_selftest.png`](../remote/unified_selftest.png) | Render of `unified.py --selftest` (1650 × 935). According to the original file dates it predates the last edit of `unified.py` by 3 minutes, so one tile may differ slightly | — | — | — | — · sample | [03](03-telemetry-stream.md) |

## The remote/Arman folder

The 35 files of this folder are grouped by topic below.

### Operator notes

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`README.md`](../remote/Arman/README.md) | English overview of the curvepoints work: the client ENU frame and sign convention, the distance rule, both output formats, file list, data source, usage, options and the live sign-validation drill. Last modified 2026‑07‑17 | — | — | — | 1 · reference (errata 13, 23) | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md), [16](16-errata-and-crosswalk.md) |
| [`OPERATIONS.md`](../remote/Arman/OPERATIONS.md) | Chinese operations manual for era 1: §0 system overview, §1 network, §2 Civic with CAN, §3 truck without CAN, §4–§5 device and laptop quick reference, §6 client integration, §7 troubleshooting, §8 after each experiment, §9 revert table. Last modified 2026‑08‑06 | — | — | — | 1 · historical (errata 3, 12, 13, 15, 17, 18, 19) | [13](13-operations-runbook.md); also [07](07-longitudinal-stop.md), [08](08-vision-stop-objstopd.md), [10](10-no-can-mode-sunnypilot.md), [14](14-device-changes-and-revert.md), [16](16-errata-and-crosswalk.md) |
| [`EXPERIMENT_RUNBOOK.md`](../remote/Arman/EXPERIMENT_RUNBOOK.md) | English day-of runbook for the Civic OP-long stop and the JSON export: readiness check, stop/go, export, vision shadow run, revert. Last modified 2026‑07‑17 | — | — | — | 1 · historical (errata 4, 13, 23) | [07](07-longitudinal-stop.md); also [13](13-operations-runbook.md), [16](16-errata-and-crosswalk.md) |
| [`STOP_COMMAND.md`](../remote/Arman/STOP_COMMAND.md) | English: the deployed v1 file-flag stop on sunnypilot 0.9.7.1 (`/tmp/op_stop_requested`), the OP-long prerequisite, a safety checklist, and a param-based reference design for an openpilot 0.9.8 checkout that was never deployed. Last modified 2026‑07‑17 | — | — | — | 1 · historical (errata 2, 27) | [07](07-longitudinal-stop.md); also [14](14-device-changes-and-revert.md), [16](16-errata-and-crosswalk.md) |
| [`ETHERNET_SETUP.md`](../remote/Arman/ETHERNET_SETUP.md) | English: USB‑C Ethernet adapter; Plan A (the laptop shares the link and the device gets 10.42.0.x), Plan B (static 192.168.5.1 / 192.168.5.2); a field checklist with no recorded result. Last modified 2026‑08‑06 | — | — | — | 1+2 · reference; never confirmed in the field (errata 5, 27) | [02](02-setup-ssh-networking.md); also [12](12-dashcam-anywhere-field-guide.md) |

### Curvepoints pipeline

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`frame.py`](../remote/Arman/frame.py) | WGS84 → ECEF → ENU (`geodetic2ecef()`, `ecef2enu()`, `ENUOrigin`), `wrap_pi()` to (−π, π], `yaw_ned_to_theta()` (θ = π/2 − yaw), `car_point_to_enu()` | laptop | `--test` (10 checks); without it, prints the docstring | stdlib | — · current | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md) |
| [`curvepoints.py`](../remote/Arman/curvepoints.py) | `spacing_for()` and `resample_by_distance_rule()` (d = clip(0.3·v, 0.6, 5) m), `theta_kappa()` (ENU θ and left-positive κ; \|κ\| < 1/200 snaps to 0; optional moving average), `to_stahle_rows()` with `STAHLE_HEADER`, `to_segments()` (line/arc segments, runs shorter than 3 points merged, final-velocity‑0 rule) | laptop | `--test` (15 checks); without it, prints the docstring | stdlib | — · current | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md) |
| [`cp_export.py`](../remote/Arman/cp_export.py) | Main exporter: stream → ENU → STÄHLE CSV and segment JSON, optionally UDP and stdout. `--mode live` converts the planned path ahead (plus up to 5 ego-history points); `--mode record` accumulates the driven route | laptop | `--ip IP` (required unless `--selftest`), `--port 7700`, `--mode live` (or `record`), `--ref-lat`/`--ref-lon` (default: first valid fix), `--ref-alt 0`, `--out-dir ./cp_out`, `--smooth` (5 in record, 0 in live), `--stdout`, `--udp HOST[:PORT]`, `--udp-port 5005`, `--udp-hz 10`, `--local-frame`, `--selftest` (10 checks; rewrites `_selftest_out/`) | stdlib (+ `stream_lib`) | 1 · historical: needs a reg_export stream; `--selftest` runs anywhere (errata 12, 13, 14) | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md) |
| [`cp_view.py`](../remote/Arman/cp_view.py) | Live North-up ENU map of the curvepoints, coloured by direction (left green, right orange, straight grey), with the ego arrow and the reference origin; tiles for θ, κ with DIR, radius, velocity (kph), position, point count and spacing; LIVE/STALE indicator | laptop | `--ip IP` (required unless `--selftest`), `--port 7700`, `--mode live` (or `record`, smoothed with a window of 5), `--ref-lat`/`--ref-lon`, `--ref-alt 0`, `--selftest` (writes `cp_view_selftest.png`); there is no `--local-frame` | matplotlib (+ `cp_export`, `frame`, `curvepoints`, `stream_lib`) | 1 · historical (errata 13, 14, 24) | [05](05-curvepoints-pipeline.md) |
| [`cp_view_selftest.png`](../remote/Arman/cp_view_selftest.png) | Render of `cp_view.py --selftest` (1650 × 935), re-rendered for this snapshot with the neutral example origin | — | — | — | — · sample | [05](05-curvepoints-pipeline.md) |
| [`cp_slides.html`](../remote/Arman/cp_slides.html) | Eight-slide English deck "openpilot → STÄHLE curvepoints" with an embedded copy of `cp_view_selftest.png`; open it locally | — | — | a browser | 1 · reference (errata 23, 28) | [05](05-curvepoints-pipeline.md) |
| [`stream_lib.py`](../remote/Arman/stream_lib.py) | Byte-identical copy of `remote/stream_lib.py`, so that `cp_export.py`, `cp_view.py` and `_stream_dump.py` can import it from their own folder | laptop | as `remote/stream_lib.py` | stdlib | 1 · historical (vendored duplicate) | [03](03-telemetry-stream.md) |

### Networking and client link

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`find_comma.sh`](../remote/Arman/find_comma.sh) | Finds the device: for each IPv4 subnet of the laptop it lists hosts with TCP 22 open (nmap when installed, otherwise a parallel sweep of the laptop's /24), then prints the first host that has TCP 7700 open or accepts `ssh comma@<ip> 'test -d /data/openpilot'` with `BatchMode=yes` | laptop | `./find_comma.sh [-v]` (any argument turns on verbose output); IP on stdout, log on stderr, exit 1 when nothing is found | bash, iproute2 `ip`, `timeout`, ssh; nmap optional | 1+2 · current; the first match wins, so check the DongleId | [02](02-setup-ssh-networking.md); also [12](12-dashcam-anywhere-field-guide.md) |
| [`udp_snippet.py`](../remote/Arman/udp_snippet.py) | English snippet for the client: the UDP wire format, open questions, and `send_track(ref_lat, ref_lon, segments)` (at most 10 Hz, skips payloads over 60,000 B); the demo sends a two-segment example to 192.168.1.50:5005 once per second | laptop | no options; edit `UDP_HOST`, `UDP_PORT` and `SEND_HZ` | stdlib | — · reference; the payload lacks `"stop"` (erratum 11) | [06](06-client-interface-spec.md); also [16](16-errata-and-crosswalk.md) |
| [`_udp_probe.py`](../remote/Arman/_udp_probe.py) | Probes the destination that `cp_export --udp` would send to, over a connected socket (cp_export itself uses an unconnected one) so that an ICMP "port unreachable" reply surfaces; 5 probes 0.4 s apart | laptop | `python3 _udp_probe.py [HOST] [PORT]` (172.20.10.2, 5005) | stdlib | — · diagnostic | [06](06-client-interface-spec.md); also [09](09-stop-signal-udp.md) |
| [`_udp_testsend.py`](../remote/Arman/_udp_testsend.py) | Sends datagrams shaped like `cp_export --udp` output plus the keys `test`, `seq` and `ts`; `"stop"` flips about once a second; 10 Hz | laptop | `python3 _udp_testsend.py [HOST] [PORT] [SECONDS]` (172.20.10.2, 5005, 15) | stdlib | — · diagnostic | [06](06-client-interface-spec.md) |

### Stop signal over UDP

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`stop_udp.py`](../remote/Arman/stop_udp.py) | Sends one ASCII byte per datagram: `"1"` while `/tmp/op_stop_requested` or `/tmp/op_stop_intent` exists, otherwise `"0"`. Installed as `/data/objstop/stop_udp.py` | device | `HOST PORT [--hz 10]` | stdlib | 1 · historical; checks file existence only (erratum 25) | [09](09-stop-signal-udp.md); also [06](06-client-interface-spec.md) |
| [`stop_udp_start.sh`](../remote/Arman/stop_udp_start.sh) | One-step start from the laptop: copies `stop_udp.py` to the device if it is missing, kills an old sender in a separate SSH call, starts a detached sender with the era‑1 interpreter, and shows the start of `/tmp/stop_udp.log` | laptop | `./stop_udp_start.sh DEST_IP DEST_PORT [HZ]` (HZ 10); the device address is hard-coded to 172.20.10.3 | bash, ssh, scp | 1 · historical (erratum 5) | [09](09-stop-signal-udp.md); also [16](16-errata-and-crosswalk.md) |
| [`stop_udp_stop.sh`](../remote/Arman/stop_udp_stop.sh) | Stops the device sender with `pkill -f '[s]top_udp.py'` | laptop | no arguments; the device address is hard-coded to 172.20.10.3 | bash, ssh | 1 · historical (erratum 5) | [09](09-stop-signal-udp.md); also [16](16-errata-and-crosswalk.md) |
| [`stop_udp_watch.sh`](../remote/Arman/stop_udp_watch.sh) | Listens on a UDP port of this laptop and prints every change of the received payload; reports 5 s of silence | laptop | `./stop_udp_watch.sh PORT` | bash, python3 | — · current | [09](09-stop-signal-udp.md); also [06](06-client-interface-spec.md) |
| [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) | Laptop fallback that sends the same `"0"`/`"1"` byte without the device; in a terminal the keys `1`, `0`, space (toggle) and `q` work. Chinese docstring | laptop | `[HOST] [PORT] [--hz 10] [--value 1] [--duration 0] [--pulse 0]`; defaults 172.20.10.2:5005; `--duration 0` runs until stopped; `--pulse N` switches to "0" after N s and sends `--value` until then (the help text says "1") | stdlib (POSIX terminal: `termios`, `tty`) | — · current; the docstring names the wrong default host (erratum 6) | [09](09-stop-signal-udp.md); also [06](06-client-interface-spec.md), [16](16-errata-and-crosswalk.md) |

### Civic experiment control and vision stop

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`experiment.py`](../remote/Arman/experiment.py) | Day-of control for the Civic experiment over SSH: `check` (params, planner patch and onroad over SSH, then 6 s of stream for engagement, `longActive`, GPS fix and `modelV2`), `stop` (`touch /tmp/op_stop_requested`), `go` (`rm -f` that file), `release` (`touch /tmp/op_stop_release`), `status` | laptop | `--ip IP` (required), `--user comma`, `--port 7700`, action `check` \| `stop` \| `go` \| `release` \| `status` | stdlib, ssh | 1 · historical | [07](07-longitudinal-stop.md); also [08](08-vision-stop-objstopd.md), [13](13-operations-runbook.md) |
| [`objstopd.py`](../remote/Arman/objstopd.py) | Canonical vision stop daemon v2.1: narrow road camera (a wide-camera ROI only in STOPPED_RED) → YOLOv8 ONNX → pinhole distance → per-target 1-state Kalman filter → `VisionStopSM` → actuation flag (only with `--arm`), intent flag (always), status JSON and JPEG. Shadow by default. Runs from `/data/objstop/` next to `yolo_infer.py`; `yuv_to_rgb()` and `extract_image()` are adapted from openpilot | device | `[--arm]` plus 14 tuning options; model defaults `/data/objstop/yolov8n_320.onnx` and `/data/objstop/yolov8n.onnx`; `--save-every 0.3` (full list in [CLI defaults](#cli-defaults)) | numpy, Pillow, onnxruntime (through `yolo_infer`), device openpilot (`cereal`, `msgq` VisionIPC); ONNX models not included | 1 · historical (errata 1, 18, 25) | [08](08-vision-stop-objstopd.md); also [06](06-client-interface-spec.md), [14](14-device-changes-and-revert.md) |
| [`watch_detect.py`](../remote/Arman/watch_detect.py) | Console viewer with a Chinese docstring: streams `/tmp/objstop_status.json` over one SSH session and prints the state, the tracks and every raw detection, re-computing the three pedestrian gates (centred band, close enough, low enough) for each person | laptop | `--ip 172.20.10.3`, `--user comma`, `--hz 4`, `--all` (print every frame, not only changes), `--ped-min-h 90`, `--ped-band-lo 0.2`, `--ped-band-hi 0.8`, `--ped-min-bottom 0.45` | stdlib, ssh | 1 · historical (erratum 5) | [08](08-vision-stop-objstopd.md) |

> [!CAUTION]
> `objstopd.py --arm`, `experiment.py stop` and the planner stop patch actuate the brakes through openpilot longitudinal control, which disables the Civic's stock radar and AEB. Use them only on a closed course with a driver ready to brake. To undo: the brake disengages openpilot at once; `experiment.py --ip $COMMA_IP go` ends a manual stop; a light gas tap or `release` ends a vision hold; Ctrl‑C stops objstopd and clears its flags ([08](08-vision-stop-objstopd.md#arming)). The OP-long revert is in [07](07-longitudinal-stop.md#revert).

### No-CAN rig patchers

> [!WARNING]
> **Historical (sunnypilot era).** These scripts patched the era‑1 device's sunnypilot 0.9.7.1 checkout in place. None of their changes survive the re-flash, and their text anchors are not expected to match openpilot v0.11.1: for example, `enable_dashcam_mode.py` anchors on the hardwared comment "Run at 2Hz, plus rising edge of ignition", while the v0.11.1 context in `dashcam_anywhere.patch` reads "Run at 2Hz, plus either edge of ignition". The scripts check each anchor before writing and abort, or skip that step, when it is missing. The ordered era‑1 revert, earliest backup first, is in [14](14-device-changes-and-revert.md#era-1-ordered-full-revert).

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`enable_dashcam_mode.py`](../remote/Arman/enable_dashcam_mode.py) | Patches `system/hardware/hardwared.py` to force ignition while `/data/force_onroad` exists (backup `.bak_arman`), swaps in the staged `/data/objstop/exporter_nocan.py` (`.bak_arman_nocan`), adds the objstopd autostart (`tools/objstop_launcher.py` and `objstop_auto()` in `process_config.py`; `.bak_arman_auto`) and creates `/data/force_onroad` | device | no options; works in `/data/openpilot`; reboot afterwards | stdlib | 1 · historical; enabled 2026‑08‑06 (reported in OPERATIONS §3.1) | [10](10-no-can-mode-sunnypilot.md); also [08](08-vision-stop-objstopd.md), [14](14-device-changes-and-revert.md) |
| [`force_onroad_v2.py`](../remote/Arman/force_onroad_v2.py) | Rewrites the hardwared hook as `real_ignition or forced` and appends a line to `/data/onroad_debug.log` whenever `should_start` or the ignition source changes (backup `.bak_arman_v2`); rolls back if the result does not compile | device | no options; reboot afterwards | stdlib | 1 · historical | [10](10-no-can-mode-sunnypilot.md); also [14](14-device-changes-and-revert.md) |
| [`fake_ignition.py`](../remote/Arman/fake_ignition.py) | Stops the real pandad and publishes synthetic `pandaStates` (ignition line on, `noOutput`, harness normal) and `peripheralState` (12000 mV) at 10 Hz so that the UI leaves the offroad screen | device | no options; a reboot undoes a manual run | device openpilot (`cereal`) | 1 · historical | [10](10-no-can-mode-sunnypilot.md) |
| [`enable_fake_ignition_autostart.py`](../remote/Arman/enable_fake_ignition_autostart.py) | Makes manager run `fake_ignition` instead of pandad while `/data/force_onroad` exists (`dashcam_rig()` and `pandad_run()` in `process_config.py`; backup `.bak_arman_fakeign`), writes `tools/fake_ignition_launcher.py` (its `keep_car_params()` re-writes the MOCK CarParams every second when missing) and creates `/data/force_onroad` | device | no options; needs `/data/objstop/fake_ignition.py` and the objstopd autostart entry; reboot afterwards | stdlib | 1 · historical; whether it was applied is not recorded | [10](10-no-can-mode-sunnypilot.md); also [14](14-device-changes-and-revert.md) |
| [`write_carparams_mock.py`](../remote/Arman/write_carparams_mock.py) | Writes the MOCK CarParams once (`write_car_param()`) so that modeld stops blocking on `CarParams` | device | no options | device openpilot | 1 · superseded by `keep_car_params()` in the fake-ignition launcher | [10](10-no-can-mode-sunnypilot.md) |
| [`suppress_car_prompt.py`](../remote/Arman/suppress_car_prompt.py) | Comments out the permanent alert of `EventName.carUnrecognized` in `selfdrive/controls/lib/events.py`, display only (backup `.bak_arman_carprompt`) | device | no options; reboot, or restart controlsd | stdlib | 1 · historical; applied (reported in an operator note of 2026‑08‑06) | [10](10-no-can-mode-sunnypilot.md); also [14](14-device-changes-and-revert.md) |
| [`enable_cabin_audio.py`](../remote/Arman/enable_cabin_audio.py) | Patches `system/micd.py` so that raw microphone samples are appended to `cabin_audio_44100_mono_s16le.raw` (about 5 MB/min) in the segment loggerd is filling, while `/data/record_audio` exists (backup `.bak_arman_audio`); creates `/data/record_audio` | device | no options; then `pkill -f "[s]ystem.micd"` | stdlib | 1 · historical; applying it is not recorded | [10](10-no-can-mode-sunnypilot.md); also [14](14-device-changes-and-revert.md) |

> [!CAUTION]
> Recording cabin audio can require the consent of everyone in the vehicle; some jurisdictions have all-party consent laws. Check the law before you enable it. To stop recording, `rm /data/record_audio`; the revert restores `system/micd.py` from `.bak_arman_audio` ([14](14-device-changes-and-revert.md#era-1-ordered-full-revert)).

### Device and stream diagnostics

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`_verify_state.py`](../remote/Arman/_verify_state.py) | Counts messages for 10 s on `deviceState`, `pandaStates`, `roadCameraState`, `modelV2`, `liveLocationKalman`, `carState` and `cameraOdometry`; prints `deviceState.started`, the ignition line and the harness status | device | no options | device openpilot | 1 · diagnostic | [10](10-no-can-mode-sunnypilot.md); also [02](02-setup-ssh-networking.md) |
| [`_vipc_probe.py`](../remote/Arman/_vipc_probe.py) | Lists the VisionIPC streams camerad advertises and counts frames for 4 s on ROAD, WIDE_ROAD and DRIVER | device | no options | device openpilot (VisionIPC) | 1 · diagnostic | [10](10-no-can-mode-sunnypilot.md) |
| [`_modeld_diag.py`](../remote/Arman/_modeld_diag.py) | Counts road, wide-road and driver camera states for 6 s, then prints the modeld and locationd lines of the newest 6 `/data/log/swaglog*` files | device | no options | device openpilot | 1 · diagnostic | [10](10-no-can-mode-sunnypilot.md) |
| [`_stream_dump.py`](../remote/Arman/_stream_dump.py) | Prints the keys and array heads of the first 3 records and of the first 2 `modelV2` updates on TCP 7700; stops after 120 records | laptop | `python3 _stream_dump.py [IP]` (172.20.10.3; the port is fixed at 7700) | stdlib (+ `stream_lib`) | 1 · diagnostic (erratum 5) | [10](10-no-can-mode-sunnypilot.md); also [03](03-telemetry-stream.md) |

The three device probes import from `/data` as well as `/data/openpilot`. Their docstrings use a bare `python3`; on the era‑1 device the explicit form was:

```bash
# device  (ssh comma@$COMMA_IP)   era 1 only; run it in the folder you copied the probe to
PYTHONPATH=/data/openpilot:/data /usr/local/pyenv/versions/3.11.4/bin/python3 _verify_state.py
```

## The remote/Arman/vision folder

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`STOP_SIGN_VISION.md`](../remote/Arman/vision/STOP_SIGN_VISION.md) | English design and history note: v2.1 field-test fixes (2026‑08‑06), v2 distance-aware stops (2026‑07‑25), and the v1 reference (pipeline, offroad validation, inference speeds on the device CPU, the v1 CLI) | — | — | — | 1 · historical (errata 4, 19, 25, 27) | [08](08-vision-stop-objstopd.md); also [07](07-longitudinal-stop.md), [14](14-device-changes-and-revert.md), [16](16-errata-and-crosswalk.md) |
| [`objstopd.py`](../remote/Arman/vision/objstopd.py) | Earlier v2.1 copy of the daemon without the intent flag (relative model names, `--save-every 0.0`). It stays because `test_stopsm.py` imports `objstopd` from this folder. Same state machine as the canonical copy | both: imported by the tests on the laptop; a daemon on the device | as the canonical copy, with the defaults named here | as the canonical copy | 1 · legacy-duplicate (erratum 1) | [08](08-vision-stop-objstopd.md); also [16](16-errata-and-crosswalk.md) |
| [`objstop_view.py`](../remote/Arman/vision/objstop_view.py) | Laptop status board: action banner and NEXT line, ARMED/SHADOW chip, three fixed tiles (stop sign, traffic light, pedestrian), camera panel, footer with LIVE/STALE, speed, inference time and alert; pulls the status JSON and the JPEG over SSH every 400 ms | laptop | `--ip IP` (required unless `--selftest`), `--user comma`, `--selftest` (writes `objstop_view_selftest.png`) | matplotlib, ssh | 1 · historical (erratum 24) | [08](08-vision-stop-objstopd.md) |
| [`ped_analysis.py`](../remote/Arman/vision/ped_analysis.py) | Offline pedestrian study of the 2026‑08‑04 test-dummy drive: yolov8n and yolov8s at 320 and 640 on 8 standstill windows; recall, longest miss gap and person rate outside the windows, written as JSON | laptop (GPU) | `--dir DIR` (required; folders `<route>--<seg>` that hold `qcamera.ts`), `--fps 5`, `--conf 0.30`, `--out ped_report.json` | ultralytics (with `yolov8n.pt`, `yolov8s.pt`), ffmpeg | 1 · reference; the videos are not included | [08](08-vision-stop-objstopd.md) |
| [`test_stopsm.py`](../remote/Arman/vision/test_stopsm.py) | 38 simulation checks: the Kalman filter, the planner-ramp mirror `planner_ramp()`, stop-sign, red-light, green-on-approach and pedestrian scenarios, the operator release, the dilemma zone and the flag protocol `parse_flag()` | laptop | no options: `python3 remote/Arman/vision/test_stopsm.py` | numpy (through `objstopd`) | — · current | [08](08-vision-stop-objstopd.md); also [07](07-longitudinal-stop.md) |
| [`yolo_infer.py`](../remote/Arman/vision/yolo_infer.py) | YOLOv8 (COCO) ONNX inference with a numpy letterbox and NMS for person (0), traffic light (9) and stop sign (11), plus an HSV colour vote for lights; `Detector(onnx_path, conf=0.35, iou=0.45, imgsz=640, threads=4, class_conf=None)` | device (or a laptop with onnxruntime) | `--onnx PATH` (required), `--image IMG`, `--imgsz 640`, `--conf 0.35`, `--bench N` (0), `--out annotated.jpg` | onnxruntime, numpy, Pillow; ONNX models not included | 1 · historical | [08](08-vision-stop-objstopd.md) |

## The remote/Arman/dashcam_anywhere folder

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`README.md`](../remote/Arman/dashcam_anywhere/README.md) | Chinese design note: behaviour while `/data/force_onroad` exists, daily use, calibration steps, validation record of 2026‑10‑03, known limitations, rollback | — | — | — | 2 · current (errata 7, 20, 21) | [11](11-dashcam-anywhere-design.md); also [12](12-dashcam-anywhere-field-guide.md), [14](14-device-changes-and-revert.md) |
| [`LAPTOP_GUIDE.md`](../remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md) | Chinese field guide §0–§11: cheat sheet, one-time preparation, mounting and power, connecting, standard procedure, `status` fields, calibration, downloads, shutdown, troubleshooting, back to the Civic, file list | — | — | — | 2 · current (errata 7, 20, 21) | [12](12-dashcam-anywhere-field-guide.md); also [02](02-setup-ssh-networking.md), [13](13-operations-runbook.md) |
| [`dashcam_anywhere.patch`](../remote/Arman/dashcam_anywhere/dashcam_anywhere.patch) | Unified diff (headers `orig/` and `new/`) against openpilot v0.11.1 `release-tizi` at `70e1574`: adds `common/dashcam_anywhere.py` and changes 9 files (card, calibrationd and its test, pandad, selfdrived, the settings device page, ui_state, hardwared, process_config); 10 files, +375 / −25 | device | apply inside `/data/openpilot` with `patch -p1`, after a `--dry-run` | patch | 2 · current (errata 21, 22) | [11](11-dashcam-anywhere-design.md); also [14](14-device-changes-and-revert.md) |
| [`dashcam.sh`](../remote/Arman/dashcam_anywhere/dashcam.sh) | Laptop control script for the era‑2 mode | laptop | `./dashcam.sh [-y] CMD [IP]` with CMD = `status`, `reset-calib`, `enable`, `disable`, `restore-civic` or `poweroff`; IP from the argument, else `$COMMA_IP`, else `../find_comma.sh`; `-y` must come first | bash, ssh (`BatchMode=yes`) | 2 · current (erratum 20) | [12](12-dashcam-anywhere-field-guide.md); also [11](11-dashcam-anywhere-design.md), [14](14-device-changes-and-revert.md) |
| [`replay_calib.py`](../remote/Arman/dashcam_anywhere/replay_calib.py) | Read-only replay of calibrationd's `Calibrator` on logged `rlog.zst` files (configurations `stock`, `lowspeed_only`, `dashcam`, `dashcam_vision`; subsets all, CAN < 6.7 m/s, CAN < 3.1 m/s), ending with `ACCEPTANCE: PASS` or `FAIL` | device | `[--root /data/media/0/realdata] [SEGMENT ...]` (19 built-in segment names) | numpy, zstandard, device openpilot with the patch | 2 · reference; `replay_rlogs/` is not included | [11](11-dashcam-anywhere-design.md) |
| [`status.py`](../remote/Arman/dashcam_anywhere/status.py) | Read-only one-screen status: flag, calibration marker, pending reset, DisableUpdates, CarParams, IsOnroad, panda safety with TX and forward counters and the harness status, `sendcan` count, calibration, GPS or vision speed source, thermal state, processes down, latest segment. Installed as `/data/dashcam_anywhere/status.py` | device | `status.py [LISTEN_SECONDS]` (3); usually called by `dashcam.sh status` | device openpilot | 2 · current | [12](12-dashcam-anywhere-field-guide.md); also [11](11-dashcam-anywhere-design.md) |

> [!CAUTION]
> With the patch installed, `dashcam.sh enable` creates `/data/force_onroad` and reboots: from then on the device is onroad and records whenever it has power, including the cabin camera, and audio when the stock `RecordAudio` setting is on. `disable` also reboots, `restore-civic` overwrites the calibration and learned params from the backup, and `reset-calib` acts without asking. Undo with `dashcam.sh disable` or the full rollback in [14](14-device-changes-and-revert.md#era-2-rollback); the consent note for recording people is in [11](11-dashcam-anywhere-design.md#known-limitations).

## The remote/Arman/_selftest_out folder

Both files come from `cp_export.py --selftest` and use the neutral example origin 37.7749295, −122.4194155. For real missions, always pass your own mission origin with `--ref-lat/--ref-lon`.

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`selftest.csv`](../remote/Arman/_selftest_out/selftest.csv) | Sample STÄHLE CSV: two `#` lines (reference and frame), the column header, then 22 points (index 0–21) of a left curve at 28.8 kph (8 m/s) | — | — | — | — · sample | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md) |
| [`selftest.json`](../remote/Arman/_selftest_out/selftest.json) | Sample segment JSON: `ref`, `"stop": 0` and one left arc (radius 49.644 m, velocity 8.0 m/s) | — | — | — | — · sample | [05](05-curvepoints-pipeline.md); also [06](06-client-interface-spec.md) |

## The docs folder

| File | Title |
|---|---|
| [`README.md`](README.md) | Documentation index |
| [`01-overview.md`](01-overview.md) | Overview |
| [`02-setup-ssh-networking.md`](02-setup-ssh-networking.md) | Setup, SSH and networking |
| [`03-telemetry-stream.md`](03-telemetry-stream.md) | Telemetry stream (reg_export) |
| [`04-control-principles-and-frenet.md`](04-control-principles-and-frenet.md) | Control principles and Frenet outputs |
| [`05-curvepoints-pipeline.md`](05-curvepoints-pipeline.md) | Curvepoints pipeline (STÄHLE TrackDriver) |
| [`06-client-interface-spec.md`](06-client-interface-spec.md) | Client interface specification |
| [`07-longitudinal-stop.md`](07-longitudinal-stop.md) | Longitudinal stop command (Civic, era 1) |
| [`08-vision-stop-objstopd.md`](08-vision-stop-objstopd.md) | Vision stop daemon (objstopd) |
| [`09-stop-signal-udp.md`](09-stop-signal-udp.md) | 0/1 stop signal over UDP |
| [`10-no-can-mode-sunnypilot.md`](10-no-can-mode-sunnypilot.md) | No-CAN truck/bench mode (sunnypilot era) |
| [`11-dashcam-anywhere-design.md`](11-dashcam-anywhere-design.md) | dashcam-anywhere: design and validation |
| [`12-dashcam-anywhere-field-guide.md`](12-dashcam-anywhere-field-guide.md) | dashcam-anywhere: field guide |
| [`13-operations-runbook.md`](13-operations-runbook.md) | Operations runbook |
| [`14-device-changes-and-revert.md`](14-device-changes-and-revert.md) | Device changes and revert |
| [`15-file-reference.md`](15-file-reference.md) | File reference (this page) |
| [`16-errata-and-crosswalk.md`](16-errata-and-crosswalk.md) | Errata and crosswalk |

| File | Purpose | Runs on | CLI and key defaults | Dependencies | Era · status | Docs |
|---|---|---|---|---|---|---|
| [`img/objstop_view_selftest.png`](img/objstop_view_selftest.png) | Render of `vision/objstop_view.py --selftest` (1650 × 901), shown in the vision stop document | — | — | — | — · sample | [08](08-vision-stop-objstopd.md) |

## Generated and sample outputs

Most self-tests write into the current directory, so run them from a scratch folder. `cp_export.py --selftest` is the exception: it always writes next to the script and so rewrites the tracked samples in `remote/Arman/_selftest_out/`.

```bash
# laptop
mkdir -p /tmp/op4a_selftest && cd /tmp/op4a_selftest
python3 <clone>/remote/frenet_view.py --selftest           # -> ./frenet_selftest.png
python3 <clone>/remote/dashboard.py --ip x --selftest      # -> ./dashboard_selftest.png
```

| Output | Produced by | Written to | In git? |
|---|---|---|---|
| `dashboard_selftest.png`, `unified_selftest.png`, `frenet_selftest.png` | `--selftest` of `dashboard.py`, `unified.py`, `frenet_view.py` | current directory | samples kept in `remote/` |
| `cp_view_selftest.png` | `cp_view.py --selftest` | current directory | sample kept in `remote/Arman/` |
| `objstop_view_selftest.png` | `vision/objstop_view.py --selftest` | current directory | copy kept in `docs/img/` |
| `selftest.csv`, `selftest.json` | `cp_export.py --selftest` (`_selftest()`) | `remote/Arman/_selftest_out/`, next to the script | tracked samples (rewritten by every run) |
| `track_live.csv`, `track_live.json` | `cp_export.py --mode live` | `--out-dir` (default `./cp_out`), replaced atomically through `<file>.tmp` | ignored (`cp_out/`, `*.tmp`) |
| `route_track.csv`, `route_track.json` | `cp_export.py --mode record` | `--out-dir`, rewritten every 2 s and at Ctrl‑C | ignored |
| `reg_log.csv` or a `.parquet` file | `recv_log.py` | `--out` | ignored (`reg_log.csv`, `*.parquet`) |
| controls CSV | `controls_monitor.py --csv FILE` | `FILE` | not ignored |
| `traj_<unix s>.csv` | `frenet_view.py --dump-csv DIR` | `DIR`, once per second | not ignored |
| `annotated.jpg` | `vision/yolo_infer.py --image IMG` | `--out` | not ignored |
| `ped_report.json` | `vision/ped_analysis.py` | `--out` | not ignored |
| `/tmp/objstop_status.json`, `/tmp/objstop_last.jpg`, `/tmp/op_stop_requested`, `/tmp/op_stop_intent` | `objstopd.py` | device tmpfs (cleared by a reboot) | never |
| `/tmp/stop_udp.log` | `stop_udp_start.sh` | device tmpfs | never |
| `/data/onroad_debug.log` | the era‑1 hardwared hook from `force_onroad_v2.py` | device, persistent | never |
| `cabin_audio_44100_mono_s16le.raw` | the era‑1 micd patch from `enable_cabin_audio.py` | current segment folder under `/data/media/0/realdata/` | never (`*.raw` ignored) |
| route segments (`fcamera.hevc`, `qcamera.ts`, `rlog.zst`, …) | loggerd on the device | `/data/media/0/realdata/<route>--<seg>/` | never (`*.hevc`, `*.ts`, `*.zst` ignored) |

The offline test results on this snapshot (Python 3.12.2) were: `frame.py --test` 10 PASS, `curvepoints.py --test` 15 PASS, `frenet.py --test` 7 PASS, `cp_export.py --selftest` 10 PASS, `vision/test_stopsm.py` 38 PASS, `controls_monitor.py --selftest` OK, and each viewer `--selftest` wrote its PNG.

## Not included, and where it lives

| Item | What it is | Where it lives | Docs |
|---|---|---|---|
| Era‑1 patched openpilot files | The planner stop patch v1 and v2 (`longitudinal_planner.py`), the Honda `interface.py` start-accel change, the controlsd "VISION: ..." display hook, the reg_export entry in `process_config.py` | the era‑1 device under `/data/openpilot`; erased by the re-flash. The hardwared, process_config, events and micd edits can be read from the patcher scripts above | [07](07-longitudinal-stop.md), [08](08-vision-stop-objstopd.md), [10](10-no-can-mode-sunnypilot.md), [14](14-device-changes-and-revert.md) |
| Deployed exporter variants | The exporter with `stopFlag`, and the no‑CAN copy `exporter_nocan.py` | the era‑1 device (`/data/openpilot/tools/reg_export/exporter.py`, `/data/objstop/exporter_nocan.py`); gone | [03](03-telemetry-stream.md), [06](06-client-interface-spec.md), [10](10-no-can-mode-sunnypilot.md) |
| ONNX models | `yolov8n_320.onnx`, `yolov8n.onnx`, optionally `yolov8s_320.onnx` | the era‑1 device in `/data/objstop/`. Export your own with Ultralytics; YOLOv8 is AGPL‑3.0 | [08](08-vision-stop-objstopd.md) |
| PyTorch weights | `yolov8n.pt`, `yolov8s.pt` for `ped_analysis.py` | loaded by name through the `ultralytics` package (`YOLO(name + ".pt")`); obtain them under the Ultralytics license | [08](08-vision-stop-objstopd.md) |
| Test-dummy videos | The 2026‑08‑04 route segments read by `ped_analysis.py --dir` | the original machines; not published | [08](08-vision-stop-objstopd.md) |
| `stop_command.py`, `common/params.cc` (`StopRequested`) | The param-based reference design | a separate openpilot 0.9.8 checkout; never deployed | [07](07-longitudinal-stop.md) |
| `replay_rlogs/` | 19 Civic rlog segments (206 MB, reported in LAPTOP_GUIDE §1.1) used by `replay_calib.py` | the desktop only | [11](11-dashcam-anywhere-design.md) |
| `/data/dashcam_backup/20261003/` | Backup of the Civic's calibration and learned params plus the git revision | the era‑2 device | [11](11-dashcam-anywhere-design.md), [14](14-device-changes-and-revert.md) |
| The client's "CP Definition" PDF | Curvepoint definition from the client | the client | [05](05-curvepoints-pipeline.md), [06](06-client-interface-spec.md) |
| Raw drive data | About 1.1 GB of route segments (rlog, qlog, qcamera, hevc) | the laptop; withheld for privacy (GPS traces, driver camera) | — |
| `remote/OPERATIONS.md`, `remote/Arman/cp_out/` | A byte-identical copy of `remote/Arman/OPERATIONS.md`, and bench output of `cp_export.py` | dropped from the snapshot | [16](16-errata-and-crosswalk.md) (erratum 14) |
| sunnypilot 0.9.7.1 source | The code behind the `file:line` references in `controls_principles.md` and in the docstrings of the era‑1 patchers | upstream sunnypilot | [04](04-control-principles-and-frenet.md), [10](10-no-can-mode-sunnypilot.md) |
| openpilot v0.11.1 source | The code the patch applies to, including the stock thermal, mount and power constants | upstream openpilot `release-tizi` | [11](11-dashcam-anywhere-design.md) |

> [!NOTE]
> **Described, not included.** The launchers `tools/objstop_launcher.py` and `tools/fake_ignition_launcher.py` are not separate files in this repository: their full source is embedded as strings in `enable_dashcam_mode.py` and `enable_fake_ignition_autostart.py`, which wrote them on the device.

## Duplicates and near-duplicates

| Files | Relationship | Why both exist |
|---|---|---|
| `remote/stream_lib.py`, `remote/Arman/stream_lib.py` | byte-identical | `remote/Arman/` is self-contained: `cp_export.py`, `cp_view.py` and `_stream_dump.py` import `stream_lib` from their own folder (`Arman/README.md` calls it the "vendored reg_export TCP client") |
| `remote/Arman/objstopd.py`, `remote/Arman/vision/objstopd.py` | same state machine; differ in the intent flag, the model paths, the `--save-every` default and the exit message | the first is the canonical v2.1; the second stays because `vision/test_stopsm.py` imports `objstopd` from its own folder (erratum 1) |
| `remote/OPERATIONS.md` | byte-identical to `remote/Arman/OPERATIONS.md` | dropped from this snapshot |
| `openpilot_controls_slides.html`, `openpilot_controls_slides.pdf` | the PDF is a print of the HTML deck | the PDF renders on GitHub; the HTML must be opened locally |
| `cp_view_selftest.png` and the image inside `cp_slides.html` | the deck embeds a base64 copy of the render | the deck is a single self-contained file |
| `frenet.py` → `_menger_curvature()`, `curvepoints.py` → `_signed_kappa()` | the same three-point formula | the sign meaning comes from the frame: the car frame (y right) makes κ > 0 a right turn, the ENU frame (y north) makes κ > 0 a left turn |
| `watch_detect.py` → `ped_gate()`, `objstopd.py` → `to_measurements()` | `ped_gate()` re-computes the pedestrian gates for display | the viewer only reads the status file, so it repeats the thresholds; keep its options in line with the daemon's |

To check the first two rows yourself:

```bash
# laptop
cd <clone>
cmp remote/stream_lib.py remote/Arman/stream_lib.py && echo identical
diff remote/Arman/objstopd.py remote/Arman/vision/objstopd.py
```

## Appendix: constants and defaults

Every value below was read from the code or the note named in the last column. Symbols are given as `file` → `symbol`.

### Network and transport

| Fact | Value | Defined at |
|---|---|---|
| Telemetry server | TCP 7700 on 0.0.0.0. `REG_EXPORT_PORT` and `REG_EXPORT_BIND` override the defaults and even explicit `--port`/`--bind`. Bind retried 30 times, 1 s apart; listen backlog 8; `TCP_NODELAY` per client | [`exporter_device.py`](../remote/exporter_device.py) → `main()`, `Fanout`, `Client` |
| Telemetry clients | Port 7700 by default everywhere; `stream()` uses a 5 s socket timeout and reconnects after 1 s | [`stream_lib.py`](../remote/stream_lib.py) → `stream()`; `cp_export.py`, `cp_view.py`, `experiment.py` → `main()`; `find_comma.sh` |
| Record rate | One JSON line per `carState` update (about 100 Hz). Arrays of `modelV2` and `longitudinalPlan` (20 Hz services) appear only on frames where that service updated | `exporter_device.py` → `main()`, `build_record()`, `HEAVY` |
| Per-client buffer | 300 records; the oldest is dropped when the laptop is slow | `exporter_device.py` → `Client` |
| Client JSON over UDP | `--udp HOST[:PORT]`; a bare host uses `--udp-port` (5005). At most `--udp-hz` (10) datagrams per second (record mode: one per 2 s snapshot, `stop` always 0); compact JSON with `ref`, `stop`, `segments`; payloads over 60,000 B are skipped; no sequence number and no acknowledgement | [`cp_export.py`](../remote/Arman/cp_export.py) → `run()` (`udp_send`) |
| Output files | Live: rewritten when more than 0.05 s has passed (at most 20 Hz). Record: every 2 s and at Ctrl‑C. Always through `<file>.tmp` and an atomic rename; JSON pretty-printed with indent 2 | `cp_export.py` → `run()`, `_atomic_write()`, `write_segments_json()` |
| stdout output | `--stdout` (live mode only) prints one JSON object per live update (default separators, not pretty-printed), on the same stdout as the `[cp_export]` and `[stream]` log lines, so keep only lines that start with `{` | `cp_export.py` → `run()` |
| 0/1 stop byte | Payload `b"0"` or `b"1"`; 10 Hz by default; destination host and port required | [`stop_udp.py`](../remote/Arman/stop_udp.py) → `main()`, `stop_now()` |
| Laptop fallback sender | 172.20.10.2:5005, 10 Hz, initial payload "1" | [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) → `main()` |
| UDP test tools | `_udp_testsend.py`: 10 Hz for 15 s to 172.20.10.2:5005. `_udp_probe.py`: 5 probes 0.4 s apart, same default | module-level code of both scripts |
| Example addresses | comma tethering 192.168.43.1; Ethernet Plan A 10.42.0.x; Plan B 192.168.5.2 (laptop 192.168.5.1); iPhone hotspot 172.20.10.x; lab Wi‑Fi 192.168.1.231 (DHCP) | LAPTOP_GUIDE §3; ETHERNET_SETUP; `stop_udp_start.sh`; OPERATIONS §1 |

SSH options used by the tools:

| Tool | Options |
|---|---|
| `experiment.py` → `ssh()` | `StrictHostKeyChecking=no`, `ConnectTimeout=6`, 10 s overall timeout |
| `watch_detect.py` → `main()` | `StrictHostKeyChecking=no`, `ConnectTimeout=8`, `ServerAliveInterval=5` |
| `vision/objstop_view.py` → `pull()` | `StrictHostKeyChecking=no`, `ConnectTimeout=4`, 8 s overall timeout |
| `stop_udp_start.sh`, `stop_udp_stop.sh` | `StrictHostKeyChecking=no`, `ConnectTimeout=6` |
| `find_comma.sh` | `StrictHostKeyChecking=no`, `ConnectTimeout=3`, `BatchMode=yes` |
| `dashcam_anywhere/dashcam.sh` | `ConnectTimeout=8`, `BatchMode=yes`; no host-key override, so a changed host key makes it fail |

### Flag and state files

| File | Format and semantics | Defined at |
|---|---|---|
| `/tmp/op_stop_requested` (actuation) | `d=<m, %.2f> t=<time.monotonic(), %.3f> src=v`, rewritten atomically on every 50 ms tick while a stop is wanted, only with `--arm`; `d=0.00` means stop now. Planner rules (on-disk mirror): absent → normal, empty → stop now, garbled → stop now, `t` missing or older than 1 s → ignored, `d ≤ 0` → stop now, otherwise glide to `d`. objstopd deletes only files that contain `src=v`; `experiment.py stop` writes an empty file, `go` removes the file. An armed objstopd that starts its own stop overwrites a manual file and deletes it when that stop ends | [`objstopd.py`](../remote/Arman/objstopd.py) → `STOP_FLAG`, `write_flag()`, `main()`; [`test_stopsm.py`](../remote/Arman/vision/test_stopsm.py) → `parse_flag()`; `experiment.py` → `FLAG`, `main()` |
| `/tmp/op_stop_intent` | Same format; written on every tick while a stop is wanted, whether or not `--arm` is set; removed when no stop is wanted and on a clean exit; read by `stop_udp.py` (existence) and, according to OPERATIONS §3.2, by the deployed exporter's `stopFlag` (described, not included) | `objstopd.py` → `INTENT_FLAG`, `main()` |
| `/tmp/op_stop_release` | `touch` = one-shot operator release; objstopd deletes it and forces RESUMING from BRAKING or any STOPPED state | `objstopd.py` → `RELEASE_FLAG`, `main()`, `VisionStopSM.update()`; `experiment.py release` |
| `/tmp/objstop_status.json` | Rewritten atomically on every tick: `t` (device wall clock), `state`, `reason`, `ped_hold`, `alert`, `action`, `next`, `level`, `screen1`, `screen2`, `wait_left`, `flag` (null, "now" or a distance), `armed`, `v_ego`, `infer_ms`, `tracks` (per class `d`, `hits`, `latched`, `waived`, or null), `dets` | `objstopd.py` → `main()` |
| `/tmp/objstop_last.jpg` | Annotated detector input every `--save-every` seconds (0 disables) | `objstopd.py` → `InferThread.run()` |
| `/tmp/stop_udp.log` | Output of the device sender | `stop_udp_start.sh` |
| `/data/force_onroad` | **Era 1:** checked on every hardwared loop by the hook, and by the manager conditions of the fake-ignition rig, so a change needs no reboot (Analysis (from code; not field-tested)). **Era 2:** read once when manager starts; reboot to apply | `enable_dashcam_mode.py` → `HOOK`; `force_onroad_v2.py` → `NEW_HOOK`; `enable_fake_ignition_autostart.py` → `FUNCS`; patch `common/dashcam_anywhere.py` → `ENABLED` |
| `/data/objstop/manual_mode` | Era 1: stops the objstopd autostart | `enable_dashcam_mode.py` → `objstop_auto()` (string in `main()`) |
| `/data/onroad_debug.log` | Era 1: one line per change of `should_start` or of the ignition source | `force_onroad_v2.py` → `LOG_ADD` |
| `/data/record_audio` | Era 1: enables cabin audio; the patched micd re-checks it about every 2 s | `enable_cabin_audio.py` → `CONST_ADD`, `METHOD_ADD` |
| `/data/reset_calib` | Era 2: calibration reset request; calibrationd consumes it at start and, in dashcam mode, checks for it every second | patch `selfdrive/locationd/calibrationd.py` → `consume_reset_request()`, `main()`; `dashcam.sh reset-calib` |
| `/data/calib_from_dashcam` | Era 2: marker created on entering dashcam mode and removed on leaving it; each change drops `CalibrationParams` | patch `calibrationd.py` → `reset_on_mode_change()`; `dashcam.sh restore-civic` removes it |

### Device paths

| Path | Era | Defined at |
|---|---|---|
| `/data/openpilot/tools/reg_export/exporter.py` | 1 | `remote/README.md` §1; `exporter_device.py` docstring |
| `/data/objstop/` (objstopd, yolo_infer, models, `stop_udp.py`, staged `exporter_nocan.py`, patcher scripts, `fake_ignition.py`, `manual_mode`) | 1 | `objstopd.py` → `main()`; `enable_dashcam_mode.py`; `stop_udp_start.sh`; `enable_fake_ignition_autostart.py` |
| `/data/openpilot/tools/objstop_launcher.py`, `/data/openpilot/tools/fake_ignition_launcher.py` | 1 | `enable_dashcam_mode.py` → `main()`; `enable_fake_ignition_autostart.py` → `LAUNCHER` |
| `/data/dashcam_anywhere/` (`status.py`, `replay_calib.py`, `replay_rlogs/`) | 2 | `dashcam.sh`; docstrings of `status.py` and `replay_calib.py`; dashcam README |
| `/data/dashcam_backup/20261003/` | 2 | `dashcam.sh` → `BACKUP`; dashcam README "回滚" (rollback) |
| `/data/params/d/<Key>` | 1+2 | `experiment.py` → `main()`; `dashcam.sh` → `confirm()`, `restore-civic` |
| `/data/media/0/realdata/<route>--<seg>/` | 1+2 | `status.py` → `REALDATA`; `replay_calib.py` → `main()`; `enable_cabin_audio.py` → `METHOD_ADD`; LAPTOP_GUIDE §7 |
| `/data/log/swaglog.*` | 1+2 | `_modeld_diag.py`; LAPTOP_GUIDE §9 |

### Versions and identities

| Fact | Defined at |
|---|---|
| sunnypilot 0.9.7.1 (era 1) | `remote/README.md`; `exporter_device.py` docstring; OPERATIONS header; STOP_COMMAND |
| openpilot v0.11.1 `release-tizi`; parent `70e157462304e5ce7d03ffbec6cb7f45bf347bb7`; local commit `8acb496`; tag `dashcam-anywhere-v1` (era 2) | dashcam README (header and rollback) |
| "0.9.8 repo" reference design | STOP_COMMAND "Reference implementation" |
| 2020 Civic Bosch, `HONDA_CIVIC_BOSCH` | `controls_principles.md` |
| Road camera OX03C10, 1928 × 1208, f = 2648 px; subsampled by 2 for detection (964 × 604) | `objstopd.py` → `F_NARROW`, `NATIVE_W`, `NATIVE_H`, `SUBSAMPLE`; `watch_detect.py` → `FRAME_W`, `FRAME_H` |
| Object sizes for the pinhole model: stop sign 0.75 m, traffic-light housing 1.07 m (person 1.7 m, display only) | `objstopd.py` → `SIGN_H`, `LIGHT_H`; `watch_detect.py` → `ped_gate()` |
| Wheelbase 2.70 m; default steer ratio 16.7 | `exporter_device.py` → `WHEELBASE`, `DEFAULT_STEER_RATIO` |
| WGS84 a = 6378137.0 m, f = 1/298.257223563 | `frame.py` → `_A`, `_F` |

### Device interpreters

| Era | Interpreter | Defined at |
|---|---|---|
| 1 | `/usr/local/pyenv/versions/3.11.4/bin/python3` with `PYTHONPATH=/data/openpilot`, or `PYTHONPATH=/data/openpilot:/data` for scripts that import from `/data` | `exporter_device.py` docstring; `remote/README.md` §1; OPERATIONS §2.5; `stop_udp_start.sh`; `fake_ignition.py`; `write_carparams_mock.py` |
| 2 | `/usr/local/venv/bin/python3 -B` with `PYTHONPATH=/data/openpilot` and `PYTHONDONTWRITEBYTECODE=1` | `dashcam.sh` → `OPPY`; docstrings of `status.py` and `replay_calib.py` |

The era‑1 patchers, the three device probes, STOP_COMMAND, the EXPERIMENT_RUNBOOK revert and OPERATIONS §9 use a bare `python3`; these docs show the explicit form.

### Thresholds and constants

| Area | Values | Defined at |
|---|---|---|
| Curvepoint spacing | d = clip(0.3·v, 0.6, 5) m (`DSDV`, `D_MIN`, `D_MAX`); `V_FLOOR` 0.3 m/s | `curvepoints.py` → constants, `spacing_for()` |
| Heading and curvature | θ in (−π, π]; \|κ\| < 1/200 → 0 | `curvepoints.py` → `theta_kappa()` |
| Segments | runs shorter than 3 points merged (`min_run`); the final segment's velocity becomes 0.0 when its mean speed is ≤ `V_FLOOR` + 0.05 = 0.35 m/s | `curvepoints.py` → `to_segments()` |
| cp_export | `HIST_TAIL` 5 ego points, at least 1.0 m apart; `RECORD_MIN_MOVE` 0.5 m; heartbeat every 1 s | `cp_export.py` → constants, `run()` |
| Frenet reference line | inner lane lines used when both probabilities exceed `MIN_LANE_PROB` 0.3, otherwise the path itself | `frenet.py` → `reference_line()` |
| Planner ramp (on-disk mirror) | a = 0.8 m/s²; v_cap = √(2·0.8·d_eff); d_eff = d − 0.5·v; hold when already holding, d_eff < 2 m or v_cap < 0.5 m/s | `objstopd.py` → `A_STOP`, `ramp_v()`; `test_stopsm.py` → `planner_ramp()` |
| objstopd latch | at least 3 hits; d_line = d − setback must exceed 0.5 m (else waived, "too close"); v²/(2·d_line) ≤ 1.1 m/s² (else waived, "dilemma zone") | `objstopd.py` → `A_MAX_LATCH`, `VisionStopSM._try_latch()` |
| objstopd Kalman filter | measurement σ_d = d²·6 px/(f·H), variance at least 0.04; gate max(3 m, 3σ); re-initialised after 4 rejects when not latched; an unlatched track resets after 3 s without updates | `objstopd.py` → `meas_R()`, `H_PX_NOISE`, `Track`, `VisionStopSM.update()` |
| objstopd distances | stop signs measured on the narrow camera only, accepted for 3 m < d < 90 m; setbacks 3 m (sign) and 10 m (light); BRAKING gives up when the target is passed by more than 5 m | `objstopd.py` → `to_measurements()`, `main()`, `VisionStopSM.update()` |
| objstopd timing | standstill below 0.3 m/s; while RESUMING, new tracks must start at ≥ 12 m (sign) or ≥ 10 m (light); RESUMING ends after 8 m or 15 s; green confirmed = ≥ 2 green events in the last 1.5 s, the first ≥ 0.5 s ago, the last < 0.8 s ago (events at least 0.15 s apart); a red light is released on approach by a confirmed green above 1 m/s; pedestrian hold = 2 sightings within 1 s, released after `--clear-sec` (1.5 s) without one; alerts after 20 s (pedestrian) and 120 s (red, when no red has been seen for over 10 s and no green is recorded) | `objstopd.py` → `VisionStopSM._feed()`, `_green_confirmed()`, `_ped_update()`, `update()` |
| objstopd inference | 640 model when v_ego > 8 m/s on the narrow camera, otherwise 320; wide-camera ROI = top 55 % × middle 60 %, alternated with the narrow camera only in STOPPED_RED; result queue of 8; control loop 20 Hz | `objstopd.py` → `InferThread.run()`, `main()` |
| yolo_infer | NMS IoU 0.45; letterbox padding 114; 4 intra-op threads; lit pixels = S > 60 and V > 90; hue votes (PIL 0–255 scale) red < 12 or > 244, yellow 12–49, green 50–109 | `yolo_infer.py` → `nms()`, `letterbox()`, `Detector`, `classify_light_color()` |
| Viewer freshness | LIVE below 300 ms (`unified.py`), 400 ms (`cp_view.py`), 1.5 s (`objstop_view.py`, device clock) | `update()` in each viewer |
| Dashcam calibration (era 2) | `MIN_SPEED_FILTER` 9 km/h (stock 15 mph); `MAX_VEL_ANGLE_STD` 1° (stock 0.25°); yaw-rate gate 2°/s × min(1, `trans[0]` / 15 mph ≈ 6.7 m/s); GPS speed used when younger than 2 s, `hasFix` and `speedAccuracy` < 1 m/s, otherwise visual odometry; equal-weight block mean; `CalibrationParams` saved after every block | patch `calibrationd.py`; `status.py` → `GPS_MAX_AGE`, `GPS_MAX_SPEED_STD` |
| Dashcam boot (era 2) | pandad started with `STARTED=1` and `FAKESEND=1`; skipped startup checks `up_to_date`, `accepted_terms`, `completed_training`, `registered_device`, `no_excessive_actuation`; 17 processes restart in place if they crash (`DASHCAM_RESTART_IF_CRASH`) | patch `pandad.py`, `hardwared.py`, `process_config.py` |

### CLI defaults

| Tool | Synopsis | Defaults |
|---|---|---|
| `stream_lib.py` | `--ip IP [--port P]` | 7700 |
| `recv_log.py` | `--ip IP [--port P] [--out FILE] [--warmup N]` | 7700; `reg_log.csv`; 80 |
| `live_plot.py` | `--ip IP [--port P] [--seconds S]` | 7700; 20 |
| `dashboard.py` | `--ip IP [--port P] [--window S] [--selftest]` | 7700; 12; `--ip` required even with `--selftest` |
| `controls_monitor.py` | `[--ip IP] [--port P] [--csv FILE] [--selftest]` | 7700; no CSV |
| `unified.py` | `[--ip IP] [--port P] [--bus-max-lat-acc A] [--selftest]` | 7700; 2.0 m/s² |
| `frenet.py` | `[--test]` | — |
| `frenet_view.py` | `[--ip IP] [--port P] [--bus-wheelbase L] [--bus-max-steer-deg D] [--bus-max-lat-acc A] [--dump-csv DIR] [--selftest]` | 7700; 12 m; 40°; 2.0 m/s²; no dump |
| `exporter_device.py` | `[--port P] [--bind ADDR]` | 7700; 0.0.0.0; environment variables win |
| `Arman/frame.py`, `Arman/curvepoints.py` | `[--test]` | — |
| `Arman/cp_export.py` | `--ip IP [--port P] [--mode live\|record] [--ref-lat LAT --ref-lon LON] [--ref-alt ALT] [--out-dir DIR] [--smooth N] [--stdout] [--udp HOST[:PORT]] [--udp-port P] [--udp-hz HZ] [--local-frame]`, or `--selftest` | live; 7700; first valid fix; 0; `./cp_out`; 5 (record) or 0 (live); 5005; 10 |
| `Arman/cp_view.py` | `[--ip IP] [--port P] [--mode live\|record] [--ref-lat LAT --ref-lon LON] [--ref-alt ALT] [--selftest]` | live; 7700; first valid fix; 0 |
| `Arman/experiment.py` | `--ip IP [--user U] [--port P] {check,stop,go,release,status}` | `comma`; 7700 |
| `Arman/objstopd.py` | `[--arm] [--onnx-320 F] [--onnx-640 F] [--conf C] [--ped-conf C] [--wait-sec S] [--clear-sec S] [--sign-setback M] [--tl-setback M] [--tl-max-cy R] [--ped-min-h PX] [--ped-band-lo R] [--ped-band-hi R] [--ped-min-bottom R] [--save-every S]` | shadow; `/data/objstop/yolov8n_320.onnx`; `/data/objstop/yolov8n.onnx` (`''` disables it); 0.4; 0.30; 3; 1.5; 3; 10; 0.6; 90 (native px); 0.2; 0.8; 0.45; 0.3 |
| `Arman/vision/objstopd.py` | as above | as above, except `yolov8n_320.onnx` and `yolov8n.onnx` (relative) and `--save-every 0.0` |
| `Arman/watch_detect.py` | `[--ip IP] [--user U] [--hz HZ] [--all] [--ped-min-h PX] [--ped-band-lo R] [--ped-band-hi R] [--ped-min-bottom R]` | 172.20.10.3; `comma`; 4 (minimum 0.5); changes only; 90; 0.2; 0.8; 0.45 |
| `Arman/stop_udp.py` | `HOST PORT [--hz HZ]` | 10 |
| `Arman/manual_stop_send.py` | `[HOST] [PORT] [--hz HZ] [--value 0\|1] [--duration S] [--pulse S]` | 172.20.10.2; 5005; 10; 1; 0 (forever); 0 (off) |
| `Arman/_udp_probe.py` | `[HOST] [PORT]` | 172.20.10.2; 5005 |
| `Arman/_udp_testsend.py` | `[HOST] [PORT] [SECONDS]` | 172.20.10.2; 5005; 15 |
| `Arman/_stream_dump.py` | `[IP]` | 172.20.10.3 |
| `Arman/stop_udp_start.sh` | `DEST_IP DEST_PORT [HZ]` | 10; device fixed at 172.20.10.3 |
| `Arman/stop_udp_stop.sh` | — | device fixed at 172.20.10.3 |
| `Arman/stop_udp_watch.sh` | `PORT` | — |
| `Arman/find_comma.sh` | `[-v]` | quiet |
| `vision/yolo_infer.py` | `--onnx PATH [--image IMG] [--imgsz N] [--conf C] [--bench N] [--out FILE]` | 640; 0.35; 0; `annotated.jpg` |
| `vision/objstop_view.py` | `[--ip IP] [--user U] [--selftest]` | `comma` |
| `vision/ped_analysis.py` | `--dir DIR [--fps F] [--conf C] [--out FILE]` | 5; 0.30; `ped_report.json` |
| `vision/test_stopsm.py` | — | — |
| `dashcam_anywhere/dashcam.sh` | `[-y] CMD [IP]` | IP from the argument, then `$COMMA_IP`, then `../find_comma.sh` |
| `dashcam_anywhere/status.py` | `[LISTEN_SECONDS]` | 3 |
| `dashcam_anywhere/replay_calib.py` | `[--root DIR] [SEGMENT ...]` | `/data/media/0/realdata`; 19 built-in segments |
| era‑1 patchers and device probes | no arguments | — |

### Era-1 backups, created files and params

> [!WARNING]
> **Historical (sunnypilot era).** These backups and files existed on the era‑1 device only. The revert procedure is in [14](14-device-changes-and-revert.md).

| File under `/data/openpilot` | Backup suffix | Created by | The backup holds | Defined at |
|---|---|---|---|---|
| `selfdrive/controls/lib/longitudinal_planner.py` | `.bak_arman` | v1 stop patch (2026‑07‑17) | stock | STOP_COMMAND (deployed section) |
| same | `.bak_arman2` | v2 distance ramp (2026‑07‑25) | the v1 patch | STOP_SIGN_VISION v2 ("Planner backup") |
| `selfdrive/car/honda/interface.py` | `.bak_arman2` | `startingState=True, startAccel=0.6` (v2) | the file before that change | STOP_SIGN_VISION v2 ("Launch") |
| `selfdrive/controls/controlsd.py` | `.bak_arman_ui` | the "VISION: ..." display hook | the file before the hook | OPERATIONS §9 |
| `system/hardware/hardwared.py` | `.bak_arman` | `enable_dashcam_mode.py` | stock | `enable_dashcam_mode.py` → `main()` |
| same | `.bak_arman_v2` | `force_onroad_v2.py` | the v1 hook | `force_onroad_v2.py` → `MARKER`, `main()` |
| `tools/reg_export/exporter.py` | `.bak_arman_nocan` | `enable_dashcam_mode.py` | the exporter as it was before the no‑CAN copy | `enable_dashcam_mode.py` → `main()` |
| `system/manager/process_config.py` | `.bak_arman_auto` | `enable_dashcam_mode.py` | the file before the objstopd autostart; it already contains the reg_export entry (no backup from before that entry is recorded) | `enable_dashcam_mode.py` → `main()` |
| same | `.bak_arman_fakeign` | `enable_fake_ignition_autostart.py` | the file before the fake-ignition entries | `enable_fake_ignition_autostart.py` → `MARKER`, `main()` |
| `selfdrive/controls/lib/events.py` | `.bak_arman_carprompt` | `suppress_car_prompt.py` | stock | `suppress_car_prompt.py` → `PATH`, `MARKER` |
| `system/micd.py` | `.bak_arman_audio` | `enable_cabin_audio.py` | stock | `enable_cabin_audio.py` → `PATH`, `MARKER` |

Files created on the era‑1 device: `tools/reg_export/exporter.py` (the manual install), `tools/objstop_launcher.py`, `tools/fake_ignition_launcher.py`, the contents of `/data/objstop/`, `/data/force_onroad`, `/data/objstop/manual_mode`, `/data/record_audio`, `/data/onroad_debug.log` and the per-segment `cabin_audio_44100_mono_s16le.raw` files.

Params:

| Param | Value | Era | Defined at |
|---|---|---|---|
| `ExperimentalLongitudinalEnabled` | 1 (OP long, from 2026‑07‑17) | 1 | STOP_COMMAND |
| `DisengageOnAccelerator` | 0 (gas overrides instead of disengaging) | 1 | OPERATIONS §0; OPERATIONS §9 sets it back to true |
| `DisableUpdates` | 1 | 2 | dashcam README; the full rollback removes it |
| `EnforceTorqueLateral`, `CustomStockLong` | 1 (baseline device settings recorded in the note) | 1 | `controls_principles.md` |

## See also

- [Documentation index](README.md)
- [Overview](01-overview.md)
- [Device changes and revert](14-device-changes-and-revert.md)
- [Errata and crosswalk](16-errata-and-crosswalk.md)
- [Third-party notices](../THIRD_PARTY_NOTICES.md)
