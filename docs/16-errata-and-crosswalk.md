# Errata and crosswalk

The original notes in `remote/` were written in English and Chinese across two device eras, and parts of them no longer match the code or the device. This page explains how to read those notes, lists every known inconsistency between the notes and the code with the evidence and the corrected fact, and maps each original note and section to the document that now covers it. The 28 numbered errata come from a design review and were each re-checked against the code for this page; seventeen further items found while writing and reviewing these docs, the A-items A1–A17, follow them.

## At a glance

| | |
|---|---|
| Audience | Everyone who reads the original notes, and authors who cite them |
| Runs on | — (reading); a few read-only checks run on the laptop or the device |
| Era | Both: Era 1 — sunnypilot 0.9.7.1, and Era 2 — openpilot v0.11.1 `release-tizi` + dashcam-anywhere |
| Status | Reference, checked against the redacted snapshot published with these docs |
| Key files | [`OPERATIONS.md`](../remote/Arman/OPERATIONS.md), [`STOP_SIGN_VISION.md`](../remote/Arman/vision/STOP_SIGN_VISION.md), [`STOP_COMMAND.md`](../remote/Arman/STOP_COMMAND.md), [`EXPERIMENT_RUNBOOK.md`](../remote/Arman/EXPERIMENT_RUNBOOK.md), [`Arman/README.md`](../remote/Arman/README.md), [`remote/README.md`](../remote/README.md), [`controls_principles.md`](../remote/controls_principles.md), [`dashcam_anywhere/README.md`](../remote/Arman/dashcam_anywhere/README.md), [`LAPTOP_GUIDE.md`](../remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md) |

## How to read the original notes

The notes are kept as they were written; the snapshot only redacted identifiers. They are working notes: each one describes the device on the day it was last edited, and later work changed some of what they say. Where a note and the code disagree, the code in this repository wins, unless the note describes something that only existed on the device (marked "described, not included" below).

### Languages

- **English:** `remote/README.md` (except one section), `Arman/README.md`, `EXPERIMENT_RUNBOOK.md`, `STOP_COMMAND.md`, `ETHERNET_SETUP.md`, `vision/STOP_SIGN_VISION.md`, both slide decks, and most docstrings.
- **Chinese:** `Arman/OPERATIONS.md`, `controls_principles.md`, `dashcam_anywhere/README.md`, `dashcam_anywhere/LAPTOP_GUIDE.md`, the section "Control-command & trajectory tools (added)" and the "说明" (note) paragraph of `remote/README.md`, and the docstrings and help strings of `watch_detect.py` and `manual_stop_send.py`.

These docs translate the Chinese notes; numbers, commands, paths and flags are copied literally. Quotes below give the Chinese text followed by a translation.

### Eras and dates

- **Era 1 — sunnypilot 0.9.7.1** (2026‑07 → 2026‑08; Honda Civic + truck/bench no‑CAN). Every note except the two in `dashcam_anywhere/` belongs to this era.
- **Era 2 — openpilot v0.11.1 `release-tizi` + dashcam‑anywhere** (from 2026‑10‑03; robots/small vehicles). The device was re-flashed between the eras, at an unrecorded date between 2026‑08‑13 (the last era‑1 file) and 2026‑10‑03 (the era‑2 patch).

> [!WARNING]
> **Historical (sunnypilot era).** The era‑1 notes describe a device state that no longer exists: the re-flash erased every era‑1 change (patched files, `/data/objstop/`, the exporter, flags and params). Read them as a record of what was done, not as instructions for the current device.

Dates below are the original last-modified dates of the files unless the note itself states a date.

### Note-by-note status

| Note | Language | Era | Last modified | Still useful for | Stale or wrong (erratum or A-item) | Now covered by |
|---|---|---|---|---|---|---|
| [`remote/README.md`](../remote/README.md) | English + Chinese section | 1 | 2026‑07‑14 | exporter install, laptop tools, record schema | manual `tmux` start (8); schema without `liveParams` (10); "accel 命令不发 CAN" ("accel command not sent to CAN") (16) | [02](02-setup-ssh-networking.md), [03](03-telemetry-stream.md), [04](04-control-principles-and-frenet.md) |
| [`controls_principles.md`](../remote/controls_principles.md) | Chinese | 1 | 2026‑07‑14 | control chain with sunnypilot `file:line` references | stock-PCM longitudinal only (16) | [04](04-control-principles-and-frenet.md) |
| [`openpilot_controls_slides.html`](../remote/openpilot_controls_slides.html) / [`.pdf`](../remote/openpilot_controls_slides.pdf) | English | 1 | 2026‑07‑14 | six-slide overview | slide 3 "NOT sent to CAN" (16) | [04](04-control-principles-and-frenet.md) |
| [`Arman/cp_slides.html`](../remote/Arman/cp_slides.html) | English | 1 | 2026‑07‑14 | eight-slide curvepoints deck | JSON without `"stop"` (23); test claim on slide 8 (28); record mode "on exit" (A3); slide 2 omits `loc.vel` (A8) | [05](05-curvepoints-pipeline.md) |
| [`Arman/README.md`](../remote/Arman/README.md) | English | 1 | 2026‑07‑17 | client frame, distance rule, formats, options | JSON without `"stop"` (23); `--local-frame` (13); record mode "on Ctrl-C" (A3); "Data source" omits `loc.vel` (A8) | [05](05-curvepoints-pipeline.md), [06](06-client-interface-spec.md) |
| [`STOP_COMMAND.md`](../remote/Arman/STOP_COMMAND.md) | English | 1 | 2026‑07‑17 | the deployed v1 file flag, the OP-long prerequisite | 0.9.8 reference design never deployed (2); open item and unbalanced fence (27); "LONG ● in cp_view" and the cp_view speed tile (A13) | [07](07-longitudinal-stop.md), [14](14-device-changes-and-revert.md) |
| [`EXPERIMENT_RUNBOOK.md`](../remote/Arman/EXPERIMENT_RUNBOOK.md) | English | 1 | 2026‑07‑17 | Civic experiment procedure | v1 objstopd flags in §4 (4); `--local-frame` (13); JSON without `"stop"` (23); record mode "on Ctrl-C" (A3); the heartbeat "should print" `OK` (A9) | [07](07-longitudinal-stop.md), [13](13-operations-runbook.md) |
| [`ETHERNET_SETUP.md`](../remote/Arman/ETHERNET_SETUP.md) | English | 1, cited in 2 | 2026‑08‑06 | Ethernet Plans A and B | field checklist without a result (27); "all tools take `--ip`" (5) | [02](02-setup-ssh-networking.md) |
| [`vision/STOP_SIGN_VISION.md`](../remote/Arman/vision/STOP_SIGN_VISION.md) | English | 1 | v2.1 header 2026‑08‑06 | v1 → v2 → v2.1 history, reported figures | v1 CLI (4); `DisengageOnAccelerator=0` "pending" (19); "always clears the flag on exit" (25); "Not yet done" (27); "LONG ● in controls_monitor / cp_view" (A13); "objstopd never deletes a file it didn't write" (A16) | [08](08-vision-stop-objstopd.md), with parts in [07](07-longitudinal-stop.md) and [14](14-device-changes-and-revert.md) |
| [`Arman/OPERATIONS.md`](../remote/Arman/OPERATIONS.md) | Chinese | 1 | 2026‑08‑06 | all era‑1 scenarios | §0 "待启用" ("pending enable") (3); `"stop"` in record mode (12); `--local-frame` (13); §9 revert (15); 7700 (17); §2.5 vs §3.3 (18); record mode "Ctrl-C 时写" ("written on Ctrl-C") (A3); "心跳应显示" ("the heartbeat should show") `OK` (A9); "末段 velocity=0.0=终点停车" ("final-segment velocity 0.0 = stop at the end") (A10) | [13](13-operations-runbook.md), with parts in [01](01-overview.md), [02](02-setup-ssh-networking.md), [05](05-curvepoints-pipeline.md)–[10](10-no-can-mode-sunnypilot.md), [14](14-device-changes-and-revert.md) |
| [`udp_snippet.py`](../remote/Arman/udp_snippet.py) docstring | English | 1 | 2026‑08‑06 | wire format and open questions for the client | `send_track()` omits `"stop"` (11); final velocity 0.0 "when the track ends in a stop" (A10) | [06](06-client-interface-spec.md) |
| Docstrings of [`watch_detect.py`](../remote/Arman/watch_detect.py), [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) | Chinese | 1 (sender: any) | 2026‑08‑13 | tool usage | wrong default host of `manual_stop_send.py` (6); its `--pulse` help (A12) | [08](08-vision-stop-objstopd.md), [09](09-stop-signal-udp.md) |
| [`dashcam_anywhere/README.md`](../remote/Arman/dashcam_anywhere/README.md) | Chinese | 2 | 2026‑10‑03 | patch behaviour, validation, rollback | desktop path (7); confirmation claim (20); "no low-voltage protection" (21) | [11](11-dashcam-anywhere-design.md), with parts in [12](12-dashcam-anywhere-field-guide.md) and [14](14-device-changes-and-revert.md) |
| [`dashcam_anywhere/LAPTOP_GUIDE.md`](../remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md) | Chinese | 2 | 2026‑10‑03 | field procedure | laptop and desktop paths (7); confirmation claim (20); "不会自动关机" ("does not shut down automatically", §8) (21); copying a private key between machines in §1.2 is discouraged (see [02](02-setup-ssh-networking.md)) | [12](12-dashcam-anywhere-field-guide.md), with parts in [02](02-setup-ssh-networking.md) and [13](13-operations-runbook.md) |

### Chinese terms in the notes

| Term | Meaning in these notes |
|---|---|
| 甲方 | the client (literally "party A"): the receiver of the JSON or UDP output |
| 实发 / 实测 | actually sent on the CAN bus / measured |
| 待启用 / 已启用 | pending enable / enabled |
| 旗标 | flag (file) |
| 放行 / 覆盖 / 脱开 | release (let the vehicle go) / override / disengage |
| 守护 | daemon |
| 心跳 | heartbeat (the 1 Hz status line of `cp_export.py`) |
| 还原 / 回滚 | revert / rollback |
| 卡车 / 大巴 | truck / bus |
| 标定 | camera calibration |
| 热点 / 网线直连 | hotspot / direct Ethernet cable |
| 台架 | bench |
| 段 / 段号 | segment / segment number |
| 速查 / 故障排查 / 常见故障 | quick reference / troubleshooting / common problems |

## Errata

Each row names where the problem is, what is wrong, the evidence in the code (file and symbol) and the corrected fact. The numbering is stable, and other documents cite these numbers as "erratum N" (several: "errata N, M"). Wording marked "Analysis (from code; not field-tested)" is reasoning from the code that was not observed on the device.

The few commands on this page start with `# laptop` (run from the root of your clone) or `# device  (ssh comma@$COMMA_IP)`. Set `COMMA_IP` first, with `cd remote/Arman && export COMMA_IP=$(./find_comma.sh)` or by hand, and check the DongleId ([Finding the device](02-setup-ssh-networking.md#finding-the-device)).

> [!CAUTION]
> Several errata and A-items touch safety-relevant behaviour: openpilot longitudinal control without the stock radar and AEB (erratum 16), stop flags and stop signals (errata 4, 18, 25; A-items A14, A16), and power protection (erratum 21). The era‑1 tools could brake a real car; use them only on a closed course with a driver ready to take over.

| # | Where | Problem | Evidence in the code | Correct |
|---|---|---|---|---|
| 1 | [`Arman/objstopd.py`](../remote/Arman/objstopd.py) and [`Arman/vision/objstopd.py`](../remote/Arman/vision/objstopd.py); both docstrings say "objstopd v2" | Two copies with the same version label behave differently | Only `Arman/objstopd.py` has `INTENT_FLAG` and `write_flag(…, path=…)`: `main()` updates the intent flag on every tick, armed or not (the file exists only while a stop is wanted), and clears it on exit. Model defaults are absolute (`/data/objstop/…`) there and relative in the vision copy; `--save-every` is 0.3 vs 0.0. `VisionStopSM`, `Track` and `to_measurements()` are identical. `vision/test_stopsm.py` imports `objstopd` from its own folder; `InferThread.run()` imports `yolo_infer` from the daemon's folder | Canonical = `remote/Arman/objstopd.py` (v2.1 with the intent flag), deployed in `/data/objstop/` next to `remote/Arman/vision/yolo_infer.py`. The vision copy is an earlier v2.1 without the intent flag, kept for the tests; the state-machine tests hold for both |
| 2 | [`STOP_COMMAND.md`](../remote/Arman/STOP_COMMAND.md), sections "Reference implementation (0.9.8 repo …)", "Code changes made", "Deploy", "Use", and the `StopRequested` checklist item | Describes `common/params.cc` (`StopRequested`) and `Arman/stop_command.py` | Neither file exists in this repository. The deployed section of the same note checks `os.path.exists('/tmp/op_stop_requested')`; `experiment.py` → `FLAG` uses the same file | The deployed design is the file flag `/tmp/op_stop_requested`. The param design was written for a separate openpilot 0.9.8 checkout and never deployed (described, not included) |
| 3 | [`OPERATIONS.md`](../remote/Arman/OPERATIONS.md) §0, row "dashcam 模式(**待启用**)" ("dashcam mode (pending enable)") | Contradicts §3.1 "已启用…(2026-08-06 应用并验证)" ("enabled … applied and verified 2026‑08‑06") | `enable_dashcam_mode.py` → `main()` patches hardwared and creates `/data/force_onroad`; `fake_ignition.py` and `enable_fake_ignition_autostart.py` were last modified 2026‑08‑12 | Enabled 2026‑08‑06 (reported in OPERATIONS §3.1); extended with the fake-ignition rig around 2026‑08‑12 (`fake_ignition.py` was run by hand, per the autostart script's docstring; applying the autostart is not recorded); erased by the later re-flash, whose date is not recorded (between 2026‑08‑13 and 2026‑10‑03) |
| 4 | [`EXPERIMENT_RUNBOOK.md`](../remote/Arman/EXPERIMENT_RUNBOOK.md) §4; [`STOP_SIGN_VISION.md`](../remote/Arman/vision/STOP_SIGN_VISION.md) v1 sections "Files", "Run — SHADOW FIRST", "Arm", "Behaviour / resume rules", "Tuning knobs" and "Honest limitations" | v1 options `--onnx`, `--imgsz`, `--cooldown`, `--stop-min-h`, `--tl-min-h`, and a 2 s stop-sign wait | `objstopd.py` → `main()` defines `--onnx-320` and `--onnx-640`, so `--onnx` fails with "ambiguous option"; `--imgsz`, `--cooldown`, `--stop-min-h` and `--tl-min-h` fail with "unrecognized arguments". argparse exits with status 2 before the daemon starts (reproduced on this snapshot). `--wait-sec` defaults to 3.0 | Only the v2.1 CLI works ([08](08-vision-stop-objstopd.md)). The input size is chosen automatically (320, or 640 above 8 m/s); re-triggering is suppressed by pass-tracking, not a cooldown; the stop-sign wait is 3 s. `--ped-min-h`, `--conf`, `--tl-max-cy`, `--ped-band-lo/hi`, `--ped-min-bottom` and `--clear-sec` still exist. See [the detail](#erratum-4-in-detail-v1-options-against-the-v21-cli) |
| 5 | [`stop_udp_start.sh`](../remote/Arman/stop_udp_start.sh) header ("Finds the comma automatically (hotspot/ethernet/wifi)"); [`stop_udp_stop.sh`](../remote/Arman/stop_udp_stop.sh); [`ETHERNET_SETUP.md`](../remote/Arman/ETHERNET_SETUP.md) ("All our tools take `--ip`") | Both scripts can only reach a device at 172.20.10.3 | Only the start script has the commented-out `find_comma.sh` call and the header claiming discovery; it hard-codes `IP=172.20.10.3` and still prints "finding comma ...". The stop script just hard-codes the same `IP=` and makes no discovery claim; its `[ -z "$IP" ]` guard can never fire. Other fixed defaults: `watch_detect.py` `--ip` and `_stream_dump.py` use 172.20.10.3; `_udp_probe.py` and `_udp_testsend.py` use 172.20.10.2 | Edit the `IP=` line of both scripts before use (in the start script you can instead restore the `find_comma.sh` call), and pass explicit addresses to the other tools. See [the detail](#erratum-5-in-detail-hard-coded-addresses) |
| 6 | [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) docstring: `# -> 172.20.10.3:5005 持续发 "1" @10Hz` (translation: keeps sending "1" at 10 Hz) | Wrong default host | `main()`: positional `host` defaults to `"172.20.10.2"`, `port` to 5005 | The default is 172.20.10.2:5005. Always pass the receiver's host and port |
| 7 | [`dashcam_anywhere/README.md`](../remote/Arman/dashcam_anywhere/README.md) "日常使用" ("daily use"): `cd ~/Desktop/Drive/openpilot/Arman/dashcam_anywhere`; [`LAPTOP_GUIDE.md`](../remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md) §0: `cd ~/Desktop/Drive/remote/Arman/dashcam_anywhere` | Two base paths: the desktop's and the laptop's | LAPTOP_GUIDE §1.1 copies the folder from the desktop and says `replay_rlogs/` (206 MB) is only needed for validation; `dashcam.sh` → `HERE` finds `../find_comma.sh` relative to the script, so the folder works anywhere | Use the repository path `remote/Arman/dashcam_anywhere/`. `replay_rlogs/` exists on the desktop only and is not included |
| 8 | [`remote/README.md`](../remote/README.md) §1 (start the exporter in `tmux`) | Presented as the way the exporter runs | `exporter_device.py` → `main()`: "manager launches this via `mod.main()` (no args), so read config from env/defaults"; `enable_dashcam_mode.py` → `main()` anchors on `PythonProcess("reg_export", "tools.reg_export.exporter", always_run)`; OPERATIONS §4: `pkill -f '[t]ools.reg_export'(manager 自动拉起)` ("manager restarts it") | The `tmux` run was the first install. Afterwards reg_export ran under manager as `always_run`; that `process_config.py` entry is described, not included |
| 9 | OPERATIONS §0 ("exporter(stopFlag)") and §3.2; STOP_SIGN_VISION v2.1 ("exporter adds `stopFlag`"); the docstring of `enable_dashcam_mode.py` | The exporter in this repository has no `stopFlag` | [`exporter_device.py`](../remote/exporter_device.py) → `SERVICES`, `build_record()`; [`cp_export.py`](../remote/Arman/cp_export.py) → `run()` reads `rec.get("stopFlag")` and keeps `last_stop = 0` when it is missing | `exporter_device.py` is the 2026‑07‑14 baseline. The `stopFlag` and no‑CAN (`/data/objstop/exporter_nocan.py`) variants are described, not included. Consumers must treat a missing `stopFlag` as 0 |
| 10 | Docstrings of [`stream_lib.py`](../remote/stream_lib.py) (`{aTarget, shouldStop, …}`), [`recv_log.py`](../remote/recv_log.py) (`longitudinalPlan.aTarget`) and [`live_plot.py`](../remote/live_plot.py); the "Record schema" of `remote/README.md` | Field names the exporter never emits; the `liveParams` block is missing from the README schema and the `stream_lib.py` docstring | `exporter_device.py` → `ext_longitudinalPlan()` emits `aTarget0` and `vTarget0` (its comment: "there is NO aTarget/shouldStop field"); `OUT_KEY` maps `liveParameters` to `liveParams`; `live_plot.py` → `reader()` itself reads `aTarget0` | Use the exporter's names ([03](03-telemetry-stream.md)): `longitudinalPlan.aTarget0`, `vTarget0`, and `liveParams.{steerRatio, angleOffsetDeg, stiffnessFactor, roll, valid}` |
| 11 | [`udp_snippet.py`](../remote/Arman/udp_snippet.py) → `send_track()` | The payload has no `"stop"`, although the docstring's wire format shows it | `send_track()` builds `{"ref": …, "segments": …}` only | The authoritative builder is `cp_export.py` → `run()` → `udp_send()`: compact `{"ref", "stop", "segments"}`. Treat the snippet as an illustration |
| 12 | OPERATIONS §2.2 (heading "甲方 JSON 输出(文件 + UDP,含 "stop":0/1)" — "client JSON output (file + UDP, with "stop": 0/1)" — which also lists `--mode record`) and §6 (UDP format with `"stop":0\|1`, no mode named) | Implies `"stop"` is meaningful in every mode | `cp_export.py` → `run()` → `emit_record()` calls `write_outputs()` and `udp_send()` without `stop`, so it is 0; only the live branch passes `stop=last_stop` | `"stop"` follows the device only with `--mode live`. `--mode record` always writes and sends 0 |
| 13 | `Arman/README.md` options; EXPERIMENT_RUNBOOK §3; OPERATIONS §3.2 ("室内/无 GPS:加 --local-frame" — "indoors / no GPS: add `--local-frame`") and §7 | `--local-frame` is presented as a general no-GPS fallback | `cp_export.py` → `run()`: with no pose the ego is pinned at (0, 0) facing North, so record mode keeps a single point (`RECORD_MIN_MOVE`) and `emit_record()`, which needs 3, never writes; the dummy `ENUOrigin(0.0, 0.0, 0.0)` stays locked, so a fix that arrives later is projected relative to latitude 0, longitude 0. When an origin already exists (`--ref-lat/--ref-lon`, or an earlier fix), the same no-pose fallback sends body-frame tracks under that real `ref`. [`cp_view.py`](../remote/Arman/cp_view.py) → `main()` has no `--local-frame` | Analysis (from code; not field-tested): use `--local-frame` only with `--mode live`, only while GPS stays absent for the whole run, and never together with `--ref-lat/--ref-lon`; restart without it once GPS is available. cp_view shows nothing in this situation. See [the detail](#erratum-13-in-detail-the-local-frame-option) |
| 14 | `cp_export.py` → `_valid_fix()`, also used by `cp_view.py` to lock the origin | Only (0, 0) and non-numeric positions are rejected, so the first numeric fix, however bad, becomes the permanent origin | `_valid_fix()` | Pass your own mission origin with `--ref-lat/--ref-lon` for real missions, and check the `ref_lat`/`ref_lon` header line of the CSV and the JSON `ref` |
| 15 | OPERATIONS §9 "还原总表(全部改动一键回退)" ("revert table: undo all changes at once") | Incomplete; the comment "回v1用.bak_arman" ("for v1 use `.bak_arman`") is backwards; the closing claim "完全回到原厂 ACC + 雷达 + AEB" ("fully back to stock ACC + radar + AEB") overstates it | Backups and files made by `enable_dashcam_mode.py`, `force_onroad_v2.py`, `enable_fake_ignition_autostart.py`, `suppress_car_prompt.py` and `enable_cabin_audio.py` (see their `main()` and `MARKER`); STOP_COMMAND: `longitudinal_planner.py.bak_arman` was taken from stock; STOP_SIGN_VISION v2: `.bak_arman2` was taken from the v1 patch | §9 misses `.bak_arman_auto`, `.bak_arman_fakeign`, `.bak_arman_carprompt`, `.bak_arman_audio`, `.bak_arman_v2`, both launchers, the reg_export entry, the added `tools/reg_export/exporter.py` and `/data/record_audio`. Restoring `.bak_arman2` gives the v1 planner; `.bak_arman` gives stock. Restore the earliest backup of each file and check with `git diff` ([14](14-device-changes-and-revert.md)); era 1 is already gone after the re-flash. See [the detail](#erratum-15-in-detail-what-the-revert-table-misses) |
| 16 | `controls_principles.md` §2 heading "（本车不发 CAN）" ("not sent to CAN on this car") and its "实发" ("actually sent") row; slide 3 of the controls deck; the "说明" note of `remote/README.md` ("accel 命令不发 CAN", "accel command not sent to CAN"); the docstring and banner of [`controls_monitor.py`](../remote/controls_monitor.py) | True only before 2026‑07‑17 | `controls_monitor.py` → `render()` prints "accel command is computed but NOT sent to CAN" unconditionally. STOP_COMMAND records `ExperimentalLongitudinalEnabled = 1` (OP long; `radarUnavailable=True`; `ACCEL_COMMAND` sent) | Two configurations: stock PCM until 2026‑07‑17 (accel only logged; openpilot spoofs cruise buttons) and OP long from 2026‑07‑17 (stock radar and AEB off; `ACC_CONTROL.ACCEL_COMMAND` sent). Ignore the banner and look at `carControl.longActive` |
| 17 | The shortcut "7700 open ⇒ onroad". No note here states it verbatim; OPERATIONS §3.1 lists "7700" among what was online in the verified onroad boot, which invites that reading | An open port does not mean onroad | `enable_dashcam_mode.py` shows reg_export registered as `always_run`; `exporter_device.py` → `main()` binds at start-up but emits only on `carState` updates; the docstring of `write_carparams_mock.py` describes "TCP 7700 connects but streams zero records" | Open port ⇒ the exporter (and manager) is running. Records flowing ⇒ onroad. Ground truth = `/data/params/d/IsOnroad`. In era 2 reg_export is most likely not installed (inferred; verify with `nc -z $COMMA_IP 7700`) |
| 18 | OPERATIONS §2.5 (a manual `objstopd.py` run in the Civic) against §3.3 ("仅 Civic 场景需要" — "only needed in the Civic scenario") | §2.5 does not stop the autostarted instance | `enable_dashcam_mode.py` → `main()` registers `objstop_auto()` = `started and not os.path.exists('/data/objstop/manual_mode')`, which does not depend on `/data/force_onroad` | `touch /data/objstop/manual_mode` before any manual run and remove it afterwards; otherwise two instances run. Analysis (from code; not field-tested): both then write the intent flag and the status file and share the CPU |
| 19 | STOP_SIGN_VISION v2.1, last bullet: "Pending user decision: `DisengageOnAccelerator=0`" | Stale | OPERATIONS §0 lists `DisengageOnAccelerator=0` among the settings in effect; §2.5: "轻点油门(现在=覆盖放行,不脱开)" ("tap the gas: it now overrides and releases, it does not disengage"); §9 sets it back to `True` | Applied in era 1 (reported in OPERATIONS). The revert is in [14](14-device-changes-and-revert.md) |
| 20 | LAPTOP_GUIDE §0; dashcam README "日常使用" ("daily use"); the header comment of [`dashcam.sh`](../remote/Arman/dashcam_anywhere/dashcam.sh) | Say that every command that changes the device asks for confirmation | `dashcam.sh`, `case "$CMD"`: `confirm` runs for `enable`, `disable`, `restore-civic` and `poweroff`; `reset-calib` runs `touch /data/reset_calib` directly | Confirmation (skipped by a leading `-y`) covers enable, disable, restore-civic and poweroff only. `reset-calib` acts at once, so check the device first |
| 21 | dashcam README "已知限制" ("known limitations"): "没有自动关机，也没有低压保护" ("no automatic shutdown and no low-voltage protection"); LAPTOP_GUIDE §8: "不会自动关机" ("does not shut down automatically") | Overstated | Patch, `system/hardware/hardwared.py` hunk: when `dashcam_anywhere.enabled()`, `in_car` (`pandaState.harnessStatus` is not `notConnected`) and `power_monitor.car_voltage_mV < VBATT_PAUSE_CHARGING * 1e3` hold for longer than `VOLTAGE_SHUTDOWN_MIN_OFFROAD_TIME_S`, and `DisablePowerDown` is not set, it sets `DoShutdown` | The test is the panda's harness status, not the vehicle type. While `status` shows `harness=notConnected` (as in the LAPTOP_GUIDE §5 sample, the usual robot setup), nothing protects the battery: rely on the robot's own switch or BMS. When a harness is detected, the device shuts down once the car battery voltage stays low. The thresholds are stock constants and are not in this repository |
| 22 | Every note that says "touch / rm `/data/force_onroad`" (OPERATIONS §0, §3, §7–§9; docstrings of the era‑1 scripts; dashcam README), and the flag line of the `status` sample in LAPTOP_GUIDE §5 | Same file name, different semantics | Era 1: `enable_dashcam_mode.py` → `HOOK` and `force_onroad_v2.py` → `NEW_HOOK` test the file inside hardwared's loop; `enable_fake_ignition_autostart.py` → `dashcam_rig()` is a manager process condition. Era 2: patch `common/dashcam_anywhere.py` → `ENABLED = os.path.isfile(FLAG)`, evaluated at import | Always name the era. Era 1: a live switch (Analysis (from code; not field-tested)). Era 2: read once at manager start; reboot to apply (`dashcam.sh enable` and `disable` reboot for you). See [the detail](#erratum-22-in-detail-the-force_onroad-flag-by-era) |
| 23 | `Arman/README.md` "Two output formats" JSON example; also EXPERIMENT_RUNBOOK §3 and `cp_slides.html` slide 6, which are older than the flag | No top-level `"stop"` | `cp_export.py` → `write_segments_json()` writes `{"ref", "stop", "segments"}`; [`selftest.json`](../remote/Arman/_selftest_out/selftest.json) shows `"stop": 0` | Use the schema in [06](06-client-interface-spec.md) |
| 24 | [`vision/objstop_view.py`](../remote/Arman/vision/objstop_view.py) footer (LIVE/STALE and its age); the "e2e" figure of [`unified.py`](../remote/unified.py) and `cp_view.py` | They compare the device's wall clock with the laptop's | `objstopd.py` → `main()` writes `"t": time.time()`; `objstop_view.py` → `update()` computes `time.time() - st["t"]` (LIVE below 1.5 s); `exporter_device.py` → `build_record()` sets `t_wall`. LAPTOP_GUIDE §7: no RTC battery, so the clock is wrong until a GPS fix | Known limitation: trust STALE and e2e only once the device clock is set. The "age … ms" figure of unified and cp_view uses the laptop's monotonic clock and is reliable |
| 25 | `stop_udp.py` docstring ("1 = the vision/stop system wants the vehicle stopped"); OPERATIONS §2.4 (`go`: "清除手动停车" — "clears the manual stop"); STOP_SIGN_VISION v1 "Arm" ("The daemon always clears the flag on exit (no stale stop)") | (a) The sender checks file existence only. (b) A crashed objstopd leaves a stale "1". (c) `go` does not end a vision hold | [`stop_udp.py`](../remote/Arman/stop_udp.py) → `STOP_FILES`, `stop_now()`; `objstopd.py` → `main()` clears its flags on exit only in `finally:` (not reached on SIGKILL, nor on the SIGHUP of a closed SSH session, for which it installs no handler); `vision/test_stopsm.py` → `parse_flag()` (the planner mirror ignores `t` older than 1 s); [`experiment.py`](../remote/Arman/experiment.py) → `main()`: `go` = `rm -f /tmp/op_stop_requested`, `release` = `touch /tmp/op_stop_release` | Analysis (from code; not field-tested): after a crash the UDP sender keeps sending "1" while the planner already ignores the stale flag. `go` removes the actuation file (during a vision hold, an armed objstopd rewrites it within 50 ms) and never touches the intent flag; use `release` to end a vision hold. See [the detail](#erratum-25-in-detail-who-writes-and-who-clears-the-stop-files) |
| 26 | [`dashboard.py`](../remote/dashboard.py) (speed panel "speed m/s", dashed "set" line) and `live_plot.py` (speed axis) | Plot `vCruise`, a km/h set speed, on an m/s axis | `dashboard.py` → `reader()` and `main()` (the `set_ln` line plots `vCruise`); `live_plot.py` → `reader()`; `controls_principles.md` §4: "controlsState.vCruise（设定，kph）" ("set speed, kph"); `controls_monitor.py` labels the speed row "kph\|m/s" | Display erratum only: divide the set-speed line by 3.6 |
| 27 | STOP_COMMAND "Open item to confirm before deploying" and a stray closing code fence; ETHERNET_SETUP "Field checklist (tomorrow)"; STOP_SIGN_VISION v1 "Not yet done" (autostart) | Stale wording | STOP_COMMAND's first section already says it is deployed on sunnypilot 0.9.7.1, and the file has an odd number (11) of fence lines; no Ethernet result exists anywhere in the repository; `enable_dashcam_mode.py` adds the objstopd autostart, enabled on 2026‑08‑06 (reported in OPERATIONS §3.1) | Historical: the version question was answered (0.9.7.1); Ethernet was never confirmed in the field; the autostart was done on 2026‑08‑06 |
| 28 | [`cp_slides.html`](../remote/Arman/cp_slides.html) slide 8: "All conversions are covered by `--test` / `--selftest` in frame.py, curvepoints.py, cp_export.py, cp_view.py." | `cp_view --selftest` tests nothing | `cp_view.py` → `main()`: the self-test only calls `synthetic()`, renders and saves `cp_view_selftest.png`. The checks live in `frame.py` → `_tests()` (10), `curvepoints.py` → `_tests()` (15) and `cp_export.py` → `_selftest()` (10) | The conversion tests are `frame.py --test`, `curvepoints.py --test` and `cp_export.py --selftest`. `cp_view.py --selftest` is a visual smoke test |

> [!NOTE]
> **Described, not included.** The unpublished `remote/Arman/cp_out/` bench output of 2026‑08‑12 is the source of erratum 14's example: its origin lay in the mid-Atlantic at −2854 m altitude. The folder was dropped from this snapshot, so the example cannot be checked here.

### Erratum 1 in detail: the two objstopd copies

| Aspect | `remote/Arman/objstopd.py` | `remote/Arman/vision/objstopd.py` |
|---|---|---|
| Intent flag `/tmp/op_stop_intent` | written on every tick while a stop is wanted (shadow too); removed otherwise and on exit | absent |
| `write_flag()` | takes a `path` argument | writes `STOP_FLAG` only |
| `--onnx-320` / `--onnx-640` defaults | `/data/objstop/yolov8n_320.onnx`, `/data/objstop/yolov8n.onnx` | `yolov8n_320.onnx`, `yolov8n.onnx` (relative to the working folder) |
| `--save-every` default | 0.3 s (camera panel of `objstop_view.py` works out of the box) | 0.0 (no JPEG unless asked) |
| Exit message | "exit; flags cleared" | "exit; flag cleared" |
| State machine, Kalman filter, relevance gates, status JSON | identical | identical |
| Used by | the device (`/data/objstop/`, the autostart launcher) | `vision/test_stopsm.py` |

Check it yourself:

```bash
# laptop
cd <clone>
diff remote/Arman/objstopd.py remote/Arman/vision/objstopd.py
```

### Erratum 4 in detail: v1 options against the v2.1 CLI

| v1 usage (EXPERIMENT_RUNBOOK §4, STOP_SIGN_VISION v1) | v2.1 behaviour | Use instead |
|---|---|---|
| `--onnx yolov8n_320.onnx` | error: "ambiguous option: --onnx could match --onnx-320, --onnx-640" | `--onnx-320 FILE` (and `--onnx-640 FILE`, or `''` to disable the 640 model) |
| `--imgsz 320` | error: "unrecognized arguments" | nothing: 640 is used above 8 m/s on the narrow camera, 320 otherwise |
| `--cooldown 6` | error: "unrecognized arguments" | nothing: pass-tracking blocks re-latching while RESUMING |
| `--stop-min-h`, `--tl-min-h` | error: "unrecognized arguments" | nothing: stop signs count between 3 m and 90 m by pinhole distance; lights use `--tl-max-cy` |
| `--ped-min-h`, `--conf`, `--tl-max-cy`, `--ped-band-lo/hi`, `--ped-min-bottom`, `--clear-sec`, `--wait-sec`, `--save-every`, `--arm` | still valid | the same option |
| stop-sign wait 2 s | default is now 3 s | `--wait-sec` |

> [!WARNING]
> **Historical (sunnypilot era).** The v2.1 shadow run of OPERATIONS §2.5, for reference only (the device no longer has `/data/objstop/`):

```bash
# device  (ssh comma@$COMMA_IP)   era 1 only
touch /data/objstop/manual_mode          # stop the autostarted instance first (erratum 18)
cd /data/objstop && PYTHONPATH=/data/openpilot /usr/local/pyenv/versions/3.11.4/bin/python3 objstopd.py --save-every 0.3
rm /data/objstop/manual_mode             # afterwards
```

### Erratum 5 in detail: hard-coded addresses

| Tool | Address | How to change it |
|---|---|---|
| `stop_udp_start.sh` | device `IP=172.20.10.3` (the `find_comma.sh` line is commented out) | edit the `IP=` line |
| `stop_udp_stop.sh` | device `IP=172.20.10.3` (no discovery and no discovery claim; its `[ -z "$IP" ]` guard is dead) | edit the `IP=` line |
| `watch_detect.py` | device 172.20.10.3 | `--ip` |
| `_stream_dump.py` | device 172.20.10.3, port 7700 | first argument (the port is fixed) |
| `manual_stop_send.py` | receiver 172.20.10.2:5005 (the docstring says .3) | positional `HOST PORT` |
| `_udp_probe.py`, `_udp_testsend.py` | receiver 172.20.10.2:5005 | positional `HOST PORT` |
| `udp_snippet.py` | receiver 192.168.1.50:5005 | edit `UDP_HOST`, `UDP_PORT` |

The 172.20.10.x addresses come from an iPhone hotspot, where they rotate. Find the current address and check the DongleId before you rely on any of them:

```bash
# laptop
cd <clone>/remote/Arman && grep -n '^IP=' stop_udp_start.sh stop_udp_stop.sh
export COMMA_IP=$(./find_comma.sh) && ssh comma@$COMMA_IP 'cat /data/params/d/DongleId'
```

### Erratum 13 in detail: the local-frame option

Analysis (from code; not field-tested), from `cp_export.py` → `run()`:

| Situation | Live mode | Record mode |
|---|---|---|
| GPS never available, no `--ref-lat/--ref-lon` | Works: the ego is fixed at (0, 0) facing North, so the planned path is drawn in a body frame with forward = North; `ref` is 0.0, 0.0 | Writes nothing: the route never grows past one point |
| GPS available from the start | Not needed: the first fix locks the origin | Not needed |
| GPS arrives after the run started with `--local-frame` | The origin stays at latitude 0, longitude 0, so positions jump to coordinates thousands of kilometres from the origin | The route mixes the (0, 0) point with those coordinates |
| A real origin exists (`--ref-lat/--ref-lon`, or an earlier fix) and there is no valid pose, from the start or after losing it | Body-frame tracks (forward = North, ego at (0, 0)) are sent under the real `ref` and cannot be told apart from ENU; ego-history points from before the loss are still prepended, which adds a spurious segment back to (0, 0) | The route gains a point at (0, 0), the reference point itself; with no fix at all it never reaches 3 points and nothing is written |
| `cp_view.py` | Has no such option and draws nothing without a pose | — |

In every row without a pose, the heartbeat keeps printing `have origin, waiting for valid GPS pose (lat/lon/yaw)` while live files are written, so the `OK -> …` line never appears; judge the run by the files instead ([05](05-curvepoints-pipeline.md#heartbeat-and-log-lines)). A receiver can recognise genuine local-frame output only by its `ref` of (0.0, 0.0) ([06](06-client-interface-spec.md#coordinate-frame-and-origin)).

### Erratum 15 in detail: what the revert table misses

> [!WARNING]
> **Historical (sunnypilot era).** Everything in this table was erased by the re-flash. It matters only for someone rebuilding or auditing an era‑1 device; the procedure is in [14](14-device-changes-and-revert.md).

| Item on the era‑1 device | Made by | In OPERATIONS §9? | Correct handling |
|---|---|---|---|
| `longitudinal_planner.py.bak_arman` (stock) | v1 stop patch | only in the backwards comment | restore it to get stock |
| `longitudinal_planner.py.bak_arman2` (v1) | v2 ramp | restored, which leaves the v1 patch | skip it when the goal is stock |
| `honda/interface.py.bak_arman2` | start-accel change | yes | restore |
| `controlsd.py.bak_arman_ui` | display hook | yes | restore |
| `hardwared.py.bak_arman` (stock) | `enable_dashcam_mode.py` | yes | restore; this also removes the v2 hook |
| `hardwared.py.bak_arman_v2` (v1 hook) | `force_onroad_v2.py` | no | not needed once `.bak_arman` is restored |
| `tools/reg_export/exporter.py.bak_arman_nocan` | `enable_dashcam_mode.py` | yes | restoring it keeps an exporter; the exporter itself is an added file |
| `process_config.py.bak_arman_auto` | `enable_dashcam_mode.py` | no | restore, then remove the reg_export entry, which predates every backup |
| `process_config.py.bak_arman_fakeign` | `enable_fake_ignition_autostart.py` | no | not needed once `.bak_arman_auto` is restored |
| `events.py.bak_arman_carprompt` | `suppress_car_prompt.py` | no | restore |
| `micd.py.bak_arman_audio` | `enable_cabin_audio.py` | no | restore |
| `tools/objstop_launcher.py`, `tools/fake_ignition_launcher.py` | the two enable scripts | no | delete |
| `/data/record_audio` | `enable_cabin_audio.py` | no | delete |
| `/data/force_onroad` | `enable_dashcam_mode.py`, `enable_fake_ignition_autostart.py` | yes | delete |
| `/data/objstop/` (scripts, models, staged exporter, `manual_mode`), `/data/onroad_debug.log`, per-segment `cabin_audio_44100_mono_s16le.raw` | manual staging, `force_onroad_v2.py`, `enable_cabin_audio.py` | no | delete when no longer needed |
| `ExperimentalLongitudinalEnabled`, `DisengageOnAccelerator` | STOP_COMMAND; OPERATIONS §0 | yes | remove; set back to true |

A read-only inventory shows what a device still carries:

```bash
# device  (ssh comma@$COMMA_IP)
git -C /data/openpilot status --short
find /data/openpilot -name '*.bak_arman*'
```

### Erratum 22 in detail: the force_onroad flag by era

| | Era 1 (sunnypilot 0.9.7.1, patched by scripts) | Era 2 (openpilot v0.11.1 + dashcam-anywhere patch) |
|---|---|---|
| Who reads it | the hardwared hook (`HOOK`, later `NEW_HOOK`) and, with the fake-ignition rig, manager's `dashcam_rig()` / `pandad_run()` | `common/dashcam_anywhere.py` → `ENABLED`, imported by `process_config.py` (and so by manager), card, pandad, calibrationd, selfdrived, hardwared and the UI |
| When | on every loop or manager cycle | once: per the module's comment, manager pre-imports the daemons and forks them, so the value holds from manager start to the next reboot |
| To apply a change | none needed (Analysis (from code; not field-tested)); OPERATIONS §3.1 only says `touch` to re-enter | reboot (`dashcam.sh enable` / `disable` do it) |
| Effect | forced ignition; with the rig, synthetic `pandaStates` instead of pandad | forced onroad, MOCK car, `noOutput`, calibration from GPS or vision speed |

Which era is on a device:

```bash
# laptop
ssh comma@$COMMA_IP 'test -f /data/openpilot/common/dashcam_anywhere.py && echo era2 || echo era1-or-stock'
```

### Erratum 25 in detail: who writes and who clears the stop files

| File | Written by | Removed by | Read by |
|---|---|---|---|
| `/tmp/op_stop_requested` | objstopd with `--arm` (`src=v`, every tick while a stop is wanted); `experiment.py stop` (`touch`, empty) | objstopd (only files with `src=v`, when no stop is wanted and on a clean exit; this includes a manual file that an armed objstopd overwrote with its own stop, A-item A16); `experiment.py go` (any file); a reboot | the planner patch (described, not included; ignores `t` older than 1 s); `stop_udp.py` (existence); `experiment.py status` |
| `/tmp/op_stop_intent` | objstopd on every tick while a stop is wanted, armed or shadow | objstopd (when no stop is wanted and on a clean exit); a reboot | `stop_udp.py` (existence); the deployed exporter's `stopFlag` (described, not included) |
| `/tmp/op_stop_release` | `experiment.py release` | objstopd, on its next tick | objstopd (forces RESUMING) |

If objstopd was killed hard, clear its files by hand, or reboot the device:

> [!CAUTION]
> Removing the actuation file is what `experiment.py go` does, so it also ends a manual stop: on an engaged era‑1 Civic with OP long, the car can move off. Do it with a driver ready.

```bash
# device  (ssh comma@$COMMA_IP)   era 1 only
rm -f /tmp/op_stop_requested /tmp/op_stop_intent
```

## Additional inconsistencies found in this review

These seventeen items, the A-items, were found while writing and reviewing these docs, and each was checked against the code. Other documents cite them by ID, for example "A-item A3". Most are minor; A-items A14 and A16 matter for safety, because they concern how the actuation flag is handled. Wording marked "Analysis (from code; not field-tested)" was not observed on the device.

| ID | Where | Problem | Evidence in the code | Correct |
|---|---|---|---|---|
| A1 | [`find_comma.sh`](../remote/Arman/find_comma.sh) header | Says small subnets are swept fully and /24 or larger use nmap, and that the device is verified "by the reg_export port (7700) or an SSH banner" | With nmap installed every subnet is scanned with nmap; without it only the /24 around the laptop's own address is swept. The second check is a key-based login, `ssh -o BatchMode=yes comma@<ip> 'test -d /data/openpilot'`, not a banner. The first host that passes either check is printed | On networks larger than /24, install nmap. Key-based SSH must already work for the second check. Always check the DongleId: any host with TCP 22 and 7700 open passes the first check |
| A2 | [`enable_dashcam_mode.py`](../remote/Arman/enable_dashcam_mode.py) docstring, "What it changes (both backed up …)" | Lists two changes | `main()` makes four: the hardwared hook (`.bak_arman`), the exporter swap (`.bak_arman_nocan`), the objstopd autostart (`tools/objstop_launcher.py` and `process_config.py`, `.bak_arman_auto`), and it creates `/data/force_onroad` | A revert must undo all four ([14](14-device-changes-and-revert.md)) |
| A3 | `Arman/README.md` ("write the whole track on Ctrl-C"); `cp_slides.html` slide 8 ("emit … on exit"); OPERATIONS §2.2 ("Ctrl-C 时写 route_track.{csv,json}" — "writes route_track.{csv,json} on Ctrl-C"); EXPERIMENT_RUNBOOK §3 ("on Ctrl-C") | Record mode also writes, and sends over UDP, during the drive | `cp_export.py` → `run()` calls `emit_record()` (which runs `write_outputs()` and `udp_send()`) whenever more than 2 s passed since the last write, and again in the SIGINT handler | `route_track.{csv,json}` is rewritten about every 2 s (and, with `--udp`, sent with `"stop": 0`) and finalised at Ctrl‑C, as the module docstring says ("on exit (Ctrl-C) or periodically") |
| A4 | `cp_export.py` heartbeat | In `--mode record` it always prints `segs=0` | `run()` updates `last_segs` only in the live branch | Read the "wrote route_track.{csv,json} points=… segments=…" line instead |
| A5 | [`experiment.py`](../remote/Arman/experiment.py) docstring | Lists `check`, `stop`, `go` and `status`, not `release` | `main()` → `choices=["check", "stop", "go", "release", "status"]` | `release` exists and touches `/tmp/op_stop_release` |
| A6 | [`exporter_device.py`](../remote/exporter_device.py) docstring, "Options: --port 7700 --bind 0.0.0.0" | The environment wins over the options | `main()` reads `REG_EXPORT_PORT` and `REG_EXPORT_BIND` first and uses the arguments only as their fallback | Unset those variables when you pass `--port` or `--bind` |
| A7 | [`_udp_testsend.py`](../remote/Arman/_udp_testsend.py) docstring ("shaped exactly like cp_export --udp output") | Test datagrams carry extra keys and different whitespace | The payload adds `test`, `seq` and `ts`, and `json.dumps(payload)` uses the default separators | Receivers must ignore unknown keys and must not depend on whitespace |
| A8 | [`Arman/README.md`](../remote/Arman/README.md) "Data source" ("Fields used: `loc.{lat,lon,alt,yaw}` …, `modelV2.{pos_x,pos_y,vel_x}`"); `cp_slides.html` slide 2 (`loc{lat,lon,yaw}`) | Leave out `loc.vel` | `cp_export.py` → `run()` and `cp_view.py` → `_update_from_rec()` take the ego speed from `loc.vel[0]` (the exporter's `velocityCalibrated`, forward, m/s; `exporter_device.py` → `ext_loc()`), or 0 when it is missing. Floored at `V_FLOOR` (0.3 m/s), it is the speed of every ego-history point (live) and of every route point (record) | A stream that feeds `cp_export.py`, or a re-implementation of it, must carry `loc.vel`; without it those points all get 0.3 m/s ([05](05-curvepoints-pipeline.md#inputs-from-the-stream)) |
| A9 | OPERATIONS §2.2 ("心跳应显示:[cp_export] OK -> track_live.{csv,json} segs=N" — "the heartbeat should show …"); EXPERIMENT_RUNBOOK §3 ("heartbeat should print: [cp_export] OK -> …", and a "waiting for GPS/modelV2" heartbeat means "you're not onroad with a fix yet") | In live mode a working export mostly prints `GPS ok, waiting for modelV2 trajectory (is the car onroad?)` | `cp_export.py` → `run()` builds the heartbeat from the one record that triggers it (`not mv0.get("pos_x")`), and `exporter_device.py` → `ext_modelV2()` adds `pos_x` only to records on which modelV2 updated (20 Hz, against about 100 records per second) | Analysis (from code; not field-tested): expect `OK -> …` on only about one heartbeat in five. Judge the export by the output files being rewritten, or by the receiver ([05](05-curvepoints-pipeline.md#heartbeat-and-log-lines)) |
| A10 | `curvepoints.py` → `to_segments()` docstring ("velocity 0 at the end = stop there"); [`udp_snippet.py`](../remote/Arman/udp_snippet.py) docstring ("the final segment's velocity is 0.0 when the track ends in a stop"); OPERATIONS §6 ("末段 velocity=0.0=终点停车" — "final-segment velocity 0.0 = stop at the end") | Present a final velocity of 0.0 as the stop-at-the-end marker | `to_segments()` sets the last segment's velocity to 0.0 only when that segment's mean point speed is ≤ `V_FLOOR` + 0.05 = 0.35 m/s | Analysis (from code; not field-tested): a track that ends at standstill after slowing down within its last segment keeps a non-zero final velocity (1.761 m/s in the 29 m example of [05](05-curvepoints-pipeline.md#segments)). A final 0.0 means "the last segment averages ≤ 0.35 m/s"; stop commands travel in `"stop"`, in live mode only ([06](06-client-interface-spec.md#track-semantics)) |
| A11 | [`experiment.py`](../remote/Arman/experiment.py) `check`, whose ✓ lines EXPERIMENT_RUNBOOK §1 asks for | A failed SSH call shows ✓ on all three config lines (OP-long param, planner stop patch, device onroad) | `main()` presets `explong = onroad = patched = "?"` and replaces them only when the SSH call returns 0; `yn("?")` prints ✓ because a non-empty string is true, and the SSH error is not printed | Analysis (from code; not field-tested): trust those three lines only when SSH works; `experiment.py … status` prints `failed: …` when it does not ([07](07-longitudinal-stop.md#reading-the-check-output)) |
| A12 | [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) docstring (`--pulse 3  # 发 3s "1" 后自动转 "0" 并保持`: send 1 for 3 s, then switch to 0 and keep it) and `--pulse` help ("先发 N 秒 '1'" — "first send '1' for N seconds"); the closing "全部失败" ("all failed") hint | `--pulse` does not force "1", and the "all failed" hint never appears when every send fails | `main()`: the payload starts as `--value`, and the pulse branch sets it to "0" once N s have passed. `sent` counts only successful sends, so the hint's test `errs == sent` is false whenever every send fails | `--pulse N` sends `--value` (default "1") for N s, then "0"; `--pulse 3 --value 0` sends "0" throughout. Watch the failure counter ("失败 N", "N failed") instead of waiting for the hint ([09](09-stop-signal-udp.md#pulse-and-duration)) |
| A13 | `STOP_COMMAND.md` safety checklist ("Confirm OP long is actually engaged (LONG ● in cp_view / controls_monitor)") and "Use" ("Watch it live with `cp_view.py` on the laptop (speed tile → 0)"); `STOP_SIGN_VISION.md` v1 safety checklist ("LONG ● in controls_monitor / cp_view") | Point to cp_view for engagement and speed | [`cp_view.py`](../remote/Arman/cp_view.py) → `main()` → `update()` draws no engagement indicator, and its VELOCITY tile shows the resampled curvepoint speed a little ahead of the car, floored at `V_FLOOR` (0.3 m/s, about 1.1 kph), so it never reads 0. `unified.py` → `oo()` draws `LONG ●`; `controls_monitor.py` → `render()` prints `long ON`, and `dashboard.py` shows `long ON` in its status strip | Confirm OP long with `controls_monitor.py`, `dashboard.py`, `unified.py` or `experiment.py check` (`longActive`), and read the speed (`vEgo`) there, not in cp_view ([07](07-longitudinal-stop.md#corrections-to-the-original-notes)) |
| A14 | [`objstopd.py`](../remote/Arman/objstopd.py) docstring ("d=0 (or an empty/foreign file) = legacy stop-now") | A foreign file is not always a stop-now | The planner mirror [`vision/test_stopsm.py`](../remote/Arman/vision/test_stopsm.py) → `parse_flag()`: an empty file, text that does not split into `key=value` tokens, or a non-numeric `d` or `t` → stop now; `key=value` text whose `t` is missing or older than 1 s (for example `stop=1`) → ignored; `d` missing or ≤ 0 with a fresh `t` → stop now | Analysis (from code; not field-tested): for a manual stop write an empty file (`experiment.py stop`), never your own `key=value` text. The deployed planner patch is described, not included; the mirror is the only evidence ([07](07-longitudinal-stop.md#parse-rules)) |
| A15 | [`_udp_testsend.py`](../remote/Arman/_udp_testsend.py) docstring (the `python3 -c` listener); the last line of [`_udp_probe.py`](../remote/Arman/_udp_probe.py) | The listener fails as printed, and the probe's hint ignores the port it probed | The docstring splits the listener over two lines and indents the second, so compiling it raises `IndentationError: unexpected indent`. `_udp_probe.py` always prints `nc -u -l 5005` | Use the one-line listener in [06](06-client-interface-spec.md#link-testing), or `nc -u -l PORT` with your port (traditional netcat: `nc -u -l -p PORT`) |
| A16 | `STOP_SIGN_VISION.md` v2 ("Manual stops still work: … objstopd never deletes a file it didn't write (`src=v` tag)"); the docstring of `objstopd.py` → `write_flag()` ("never delete a file we didn't write (manual stops)") | An armed objstopd can cancel a manual stop | `write_flag()` checks for `src=v` only before deleting. To write a stop it always writes `<path>.tmp` and moves it over the file with `os.replace()`, so a manual empty file becomes `d=… t=… src=v` and is deleted when the vision stop ends | Analysis (from code; not field-tested): after a vision stop during a manual hold, issue `experiment.py stop` again if the hold is still needed ([07](07-longitudinal-stop.md#edge-cases), [08](08-vision-stop-objstopd.md#actuation-flag)) |
| A17 | [`dashboard.py`](../remote/dashboard.py) docstring ("Right : planned throttle/brake (accel), steering (curvature + angle) and speed as rolling time-series") | The steering time series shows no angle | `main()` draws only `desiredCurv` (`controlsState.desiredCurvature`) and `carControl.curv` in that panel. `reader()` stores `desAngle` (`carControl.steeringAngleDeg`), but nothing plots it; the measured `carState.steeringAngleDeg` appears only as text in the status strip | Read the steering angle from the status strip, from `live_plot.py` (its steering-angle row) or from the STEER tile of `unified.py` (measured, with the derived command) ([03](03-telemetry-stream.md#dashboard)) |

## Crosswalk from the original notes

| Original | Section or topic | Now covered by |
|---|---|---|
| `OPERATIONS.md` | header (device, laptop folder, safety note) | [13](13-operations-runbook.md) |
| | §0 系统总览 (system overview) | [01](01-overview.md), [14](14-device-changes-and-revert.md) |
| | §1 网络 (network) | [02](02-setup-ssh-networking.md) |
| | §2 场景 A: Civic,有 CAN (scenario A: Civic with CAN): §2.1 power-up and check, §2.2 client JSON, §2.3 visualisation, §2.4 manual longitudinal control, §2.5 vision stop | [07](07-longitudinal-stop.md), [05](05-curvepoints-pipeline.md), [08](08-vision-stop-objstopd.md), [13](13-operations-runbook.md) |
| | §3 场景 B: 卡车 / 无 CAN (scenario B: truck without CAN) | [10](10-no-can-mode-sunnypilot.md), [06](06-client-interface-spec.md), [13](13-operations-runbook.md) |
| | §4 设备速查 (device quick reference), §5 laptop 速查 (laptop quick reference), §7 故障排查 (troubleshooting), §8 每次实验后 (after each experiment) | [13](13-operations-runbook.md) |
| | §6 甲方对接 (client integration) | [06](06-client-interface-spec.md) |
| | §9 还原总表 (revert table) | [14](14-device-changes-and-revert.md) |
| `LAPTOP_GUIDE.md` | §0–§11 | [12](12-dashcam-anywhere-field-guide.md); §1 (one-time preparation, including the SSH keys of §1.2), §2.2 (power) and §3 (connecting) also [02](02-setup-ssh-networking.md); §4 and §8–§10 also [13](13-operations-runbook.md) |
| `dashcam_anywhere/README.md` | 它做了什么 (what it does), 验证记录 (validation record), 已知限制 (known limitations), 回滚 (rollback) | [11](11-dashcam-anywhere-design.md); the rollback also [14](14-device-changes-and-revert.md) |
| | 日常使用 (daily use), 换到新车/机器人时的标定步骤 (calibration steps for a new vehicle or robot) | [12](12-dashcam-anywhere-field-guide.md) |
| `controls_principles.md` | whole note | [04](04-control-principles-and-frenet.md) |
| `remote/README.md` | §0 network | [02](02-setup-ssh-networking.md) |
| | §1–§2, the record schema and Notes | [03](03-telemetry-stream.md) |
| | "Control-command & trajectory tools (added)" | [03](03-telemetry-stream.md), [04](04-control-principles-and-frenet.md) |
| Docstrings of `watch_detect.py` and `manual_stop_send.py` (Chinese) | usage | [08](08-vision-stop-objstopd.md), [09](09-stop-signal-udp.md) |
| `STOP_COMMAND.md` | whole note | [07](07-longitudinal-stop.md), [14](14-device-changes-and-revert.md) |
| `EXPERIMENT_RUNBOOK.md` | whole note | [07](07-longitudinal-stop.md), [13](13-operations-runbook.md) |
| `ETHERNET_SETUP.md` | whole note | [02](02-setup-ssh-networking.md) |
| `STOP_SIGN_VISION.md` | v2.1, v2 and the v1 reference | [08](08-vision-stop-objstopd.md); the v2 planner ramp, the launch assist and the safety checklist also [07](07-longitudinal-stop.md); the backups also [14](14-device-changes-and-revert.md) |
| `Arman/README.md` | whole note | [05](05-curvepoints-pipeline.md), [06](06-client-interface-spec.md) |
| `openpilot_controls_slides.html` / `.pdf` | the six slides | [04](04-control-principles-and-frenet.md) |
| `Arman/cp_slides.html` | the eight slides | [05](05-curvepoints-pipeline.md) |
| `udp_snippet.py` docstring | wire format and open questions | [06](06-client-interface-spec.md) |
| Docstrings and help text of the other scripts | usage | [15](15-file-reference.md), which names the document for each file |

## See also

- [Documentation index](README.md)
- [Overview](01-overview.md)
- [Operations runbook](13-operations-runbook.md)
- [Device changes and revert](14-device-changes-and-revert.md)
- [File reference](15-file-reference.md)
