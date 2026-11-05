# Documentation index

This folder is the English reference for OP4Anything: comma 3X tools, device patches and notes built between 2026‑07‑07 and 2026‑10‑03 for the client, Arman, whose downstream consumer is the STÄHLE TrackDriver robot ecosystem. It has 16 documents. Start with the [overview](01-overview.md), then follow the reading path for your role below. Every doc uses the same layout, status labels, placeholders and command conventions, summarized on this page.

## At a glance

| Field | Value |
|---|---|
| **Audience** | Everyone; pick a [reading path](#reading-paths) |
| **Runs on** | Nothing: this page is a map. Each doc says whether its commands run on the laptop or on the device |
| **Era** | Both. Each doc states which era it covers |
| **Status** | Index of the 16 reference docs |
| **Key files** | [01 Overview](01-overview.md), [06 Client interface specification](06-client-interface-spec.md), [15 File reference](15-file-reference.md), [16 Errata and crosswalk](16-errata-and-crosswalk.md) |

## Reading paths

| You are | Read in this order | What you get |
|---|---|---|
| **Integrator** (you receive the data) | [01](01-overview.md) → [06](06-client-interface-spec.md) → [05](05-curvepoints-pipeline.md) | What exists, then the exact wire and file contract, then how the curvepoints are produced |
| **Civic operator** (era 1) | [02](02-setup-ssh-networking.md) → [13](13-operations-runbook.md) → [07](07-longitudinal-stop.md) → [08](08-vision-stop-objstopd.md) | Connecting to the device, the day-of procedures, the stop command, the vision stop daemon |
| **Robot operator** (era 2) | [02](02-setup-ssh-networking.md) → [12](12-dashcam-anywhere-field-guide.md) | Connecting to the device, then the dashcam-anywhere field guide |
| **Developer** | [01](01-overview.md) → [03](03-telemetry-stream.md) → [04](04-control-principles-and-frenet.md) → [05](05-curvepoints-pipeline.md) → [08](08-vision-stop-objstopd.md) → [10](10-no-can-mode-sunnypilot.md) → [11](11-dashcam-anywhere-design.md) → [14](14-device-changes-and-revert.md) → [15](15-file-reference.md) → [16](16-errata-and-crosswalk.md) | The whole system from the stream to the patches, every device change, every file, every known erratum |

> [!WARNING]
> **Historical (sunnypilot era).** The Civic operator path describes era 1. The device was re-flashed to openpilot v0.11.1 between the two eras, so every era‑1 device change is gone, and several of those changes survive only as descriptions. See [14](14-device-changes-and-revert.md) for what was changed and why it is gone.

## Document list

| # | Document | What it covers | Audience | Era |
|---|---|---|---|---|
| 01 | [Overview](01-overview.md) | What the project is and is not, the two firmware eras, the seven work streams and their entry points, architecture diagrams, data products, timeline, included vs not included, conventions, safety and legal notes, glossary | All | Both |
| 02 | [Setup, SSH and networking](02-setup-ssh-networking.md) | Cloning, laptop requirements per tool, SSH as the lowercase `comma` user, host-key changes, the network options (hotspot, comma tethering, lab Wi‑Fi, USB‑C Ethernet), `find_comma.sh`, device interpreters and paths per era, how to tell whether the device is onroad, power | Operator, developer | Both |
| 03 | [Telemetry stream (reg_export)](03-telemetry-stream.md) | The on-device exporter (TCP 7700, newline-delimited JSON, ~100 Hz), install and run, wire protocol, the full record schema, `stream_lib`, and the laptop tools `recv_log`, `live_plot`, `dashboard`, `controls_monitor`, `unified`, `_stream_dump` | Developer, integrator | Era 1 |
| 04 | [Control principles and Frenet outputs](04-control-principles-and-frenet.md) | How sunnypilot 0.9.7.1 turned plans into steering torque and acceleration on the Civic, stock PCM vs OP long (with dates), command vs measured signals, frames and signs, Frenet `(s, d)` outputs, the bus-transferability view, porting to a bus | Developer, researcher | Era 1 |
| 05 | [Curvepoints pipeline (STÄHLE TrackDriver)](05-curvepoints-pipeline.md) | WGS84 → ENU transforms, distance-rule resampling, heading and curvature, STÄHLE rows and line/arc segments, `cp_export` live/record modes and options, `cp_view` and the sign-validation drill, self-tests and sample outputs | Developer, operator | Era 1 (laptop code is era-independent) |
| 06 | [Client interface specification](06-client-interface-spec.md) | The self-contained contract for the client: segment JSON (file and UDP) with the `"stop"` semantics table, STÄHLE CSV, the 0/1 UDP byte, raw TCP 7700; common conventions, receiver guidance, link testing, open questions | Client integrator | Era 1 interfaces |
| 07 | [Longitudinal stop command (Civic, era 1)](07-longitudinal-stop.md) | The OP-long prerequisite, the `/tmp/op_stop_requested` flag (v1 stop-now, v2 distance ramp and latch), companion patches, `experiment.py` actions, the field procedure, `go` vs `release`, safety checklist, the undeployed 0.9.8 param design | Operator, developer | Era 1 |
| 08 | [Vision stop daemon (objstopd)](08-vision-stop-objstopd.md) | On-device YOLOv8 detection of stop signs, red lights and pedestrians: pipeline and threads, relevance gates, pinhole distance and Kalman filter, the state machine, flag and status outputs, full CLI, shadow vs arm, monitoring, tests, the pedestrian study, v1 → v2.1 history, limitations | Developer, operator | Era 1 |
| 09 | [0/1 stop signal over UDP](09-stop-signal-udp.md) | The on-device `stop_udp.py` sender, the laptop start/stop scripts (which hard-code the comma's address) and the watch script, the laptop fallback `manual_stop_send.py`, verification, troubleshooting, limitations | Operator, integrator | Era 1 |
| 10 | [No-CAN truck/bench mode (sunnypilot era)](10-no-can-mode-sunnypilot.md) | The era‑1 patcher scripts that forced the device onroad without CAN (hardwared hook, fake ignition, mock CarParams, car-prompt suppression, cabin audio), the dependency chain, diagnostics, honest limitations, returning to the Civic | Developer | Era 1 (historical) |
| 11 | [dashcam-anywhere: design and validation](11-dashcam-anywhere-design.md) | The openpilot v0.11.1 patch: behaviour when enabled, boot path, the 10 patched files, calibration without CAN, safety interlocks, installing on a re-flashed device, the validation record, re-running the replay, limitations, rollback | Developer | Era 2 |
| 12 | [dashcam-anywhere: field guide](12-dashcam-anywhere-field-guide.md) | The English version of the laptop field guide: cheat sheet, mounting, power and thermals, connecting, the per-experiment procedure, `dashcam.sh` reference, reading `status`, calibration, downloading recordings, shutdown, troubleshooting, returning to the Civic | Operator | Era 2 |
| 13 | [Operations runbook](13-operations-runbook.md) | The English version of `OPERATIONS.md` + `EXPERIMENT_RUNBOOK.md`, by scenario: Civic with CAN, truck without CAN, robot dashcam; device and laptop quick references, after each experiment, a merged troubleshooting matrix, safety | Operator | Both (era‑1 scenarios historical) |
| 14 | [Device changes and revert](14-device-changes-and-revert.md) | How to inventory changes on a device; every era‑1 file, param and flag change with its backup; the ordered full revert; era‑2 changes; soft and full rollback; why era 1 is gone | Maintainer | Both |
| 15 | [File reference](15-file-reference.md) | One table per directory for every file in the repo: purpose, runs on, CLI synopsis and key defaults, dependencies, era, docs; generated samples, what is not included, duplicates, a constants appendix | Developer | Both |
| 16 | [Errata and crosswalk](16-errata-and-crosswalk.md) | How to read the original notes, the 28 numbered errata (inconsistencies between the notes and the code) and 17 additional findings (A-items A1–A17), each with the corrected facts, and a map from every original note section to the doc that replaces it | All | Both |

## Eras

Every doc names the era it describes:

- **Era 1 — sunnypilot 0.9.7.1** (2026‑07 → 2026‑08; Honda Civic + truck/bench no‑CAN)
- **Era 2 — openpilot v0.11.1 `release-tizi` + dashcam‑anywhere** (from 2026‑10‑03; robots/small vehicles)

Era 1 is written in the past tense. `/data/force_onroad` exists in both eras with different semantics, so the docs always say which era they mean. Details and dates: [01 → Hardware and firmware eras](01-overview.md#hardware-and-firmware-eras).

## Status labels

The docs use GitHub alerts. The first line holds only the alert tag; the bold label starts the next line.

| Alert | Label | Used for |
|---|---|---|
| `[!NOTE]` | **Described, not included.** | Something that exists only on the device (era 1, now erased) or on the desktop, described from the notes |
| `[!NOTE]` | **Reported in `<note>`.** | A field claim from an original note that was not re-verified for these docs |
| `[!WARNING]` | **Historical (sunnypilot era).** | A device state that no longer exists after the re-flash |
| `[!CAUTION]` | (safety) | Anything that brakes a car, forces the device onroad, or records people |
| `[!IMPORTANT]`, `[!TIP]` | (as needed) | Inferences to verify, practical hints |

The source of an alert looks like this:

```markdown
> [!NOTE]
> **Described, not included.** The longitudinal planner patch existed only on the era-1 device.
```

and renders like this:

> [!NOTE]
> **Described, not included.** The longitudinal planner patch existed only on the era‑1 device.

Text labels used inline:

- **Analysis (from code; not field-tested)**: reasoning from reading the code, never observed in the field (for example the no-CAN `"stop"` pulse behaviour in [06](06-client-interface-spec.md)).
- **Inferred; verify with ...**: a conclusion drawn from what the repo does *not* contain, with the command that settles it (for example whether the exporter runs on the era‑2 device, in [01](01-overview.md#what-runs-on-the-era-2-device)).
- **Reconstructed procedure**: steps assembled from the code and notes rather than copied from a recorded run (for example in [11](11-dashcam-anywhere-design.md)).
- Dates come from the files' last-modified times unless a note states the date. A last-modified date is not a creation date.

## Placeholders

The published snapshot is redacted. Wherever a redacted value appeared in the notes or the code, one of these placeholders stands in its place; the docs always write them in backticks (GitHub would strip a bare `<...>` as HTML). Not every placeholder occurs in the published files:

| Placeholder | Meaning |
|---|---|
| `<DONGLE_ID>`, `<DONGLE_ID_2>` | comma dongle IDs |
| `weedle-<DONGLE_ID_PREFIX>` | the comma's tethering SSID: `weedle-` + the first 4 characters of the dongle ID |
| `<TAILSCALE_IP>` | VPN address of a laptop |
| `<LAPTOP_USER>` | Linux user |
| `<LAPTOP_HOSTNAME>` | laptop hostname |
| `<COMMA_HOSTNAME>` | device mDNS hostname |
| `<LAB_WIFI_SSID>` | the lab Wi‑Fi saved on the device |
| `<SSH_KEY_FINGERPRINT>` | fingerprint of the SSH key |
| "the client's engineer" | the client contact who confirmed the frame convention |

- **GPS origin 37.7749295, -122.4194155** is a neutral example coordinate, not a mission origin. Always pass your own mission origin with `--ref-lat/--ref-lon`.
- **Private LAN addresses** such as 192.168.1.231, 172.20.10.x, 10.42.0.x, 192.168.43.1 and 192.168.5.x are examples from the notes. `swagswagcomma` is comma's public default tethering password.

## Command and citation conventions

- **Where a command runs.** Every command block starts with `# laptop` or `# device  (ssh comma@$COMMA_IP)`.
- **Device address.** Commands use `$COMMA_IP`. Set it once per shell, then confirm the dongle ID, because more than one comma can share a network:

  ```bash
  # laptop  (from the repo root)
  cd remote/Arman && export COMMA_IP=$(./find_comma.sh)    # or set it by hand
  ssh comma@$COMMA_IP 'cat /data/params/d/DongleId'         # must print <DONGLE_ID>
  ```

  If `find_comma.sh` finds no comma, `$COMMA_IP` stays empty; set it by hand ([01](01-overview.md#device-address-and-command-blocks)).

- **Interpreters.** `python3` on the laptop. On the device, the era‑correct interpreter: era 1 `/usr/local/pyenv/versions/3.11.4/bin/python3` with `PYTHONPATH=/data/openpilot` (plus `:/data` for scripts that import from `/data`); era 2 `/usr/local/venv/bin/python3 -B` with `PYTHONPATH=/data/openpilot` and `PYTHONDONTWRITEBYTECODE=1`.
- **Citations.** A relative link plus a symbol, e.g. [`cp_export.py`](../remote/Arman/cp_export.py) → `write_outputs()`. Line numbers of files in this repository are never cited, because they drift; the `file:line` references in [04](04-control-principles-and-frenet.md) point into the device's sunnypilot source, as quoted from `controls_principles.md`.
- **Errata.** "Erratum 13" (several: "errata 13, 14") refers to the numbered [errata](16-errata-and-crosswalk.md#errata), and "A-item A3" to the [additional findings](16-errata-and-crosswalk.md#additional-inconsistencies-found-in-this-review), both in 16.
- **Paths.** Repo paths are written `remote/...`; device paths are absolute (`/data/...`, `/tmp/...`).
- **Layout.** Each doc has an H1 title, a short summary, an "At a glance" table (audience, runs on, era, status, key files), its sections, and a "See also" list.
- **Images** are in `docs/img/` or next to the tool that rendered them under `remote/`. The self-test renders use synthetic data.

## Original notes

The original notes are kept under `remote/`, redacted but otherwise unchanged, in English and Chinese. They were written in the field, so some are stale or contradict the code. [16](16-errata-and-crosswalk.md) lists the 28 numbered errata and 17 additional findings (A-items A1–A17), with the corrected facts, and maps every original section to the doc that replaces it. The notes refer to the laptop folder `~/Desktop/Drive/remote/` (this repo's `remote/`) and sometimes to a desktop folder `~/Desktop/Drive/openpilot/Arman/` holding the same tools plus the desktop-only `replay_rlogs/`. To keep the original paths working, link your clone there as in [02](02-setup-ssh-networking.md#get-the-code): `mkdir -p ~/Desktop/Drive && ln -s <clone>/remote ~/Desktop/Drive/remote`, where `<clone>` is the clone's absolute path.

| Original | Language | Era, last modified | Known issues (see 16) | Replaced by |
|---|---|---|---|---|
| [`remote/README.md`](../remote/README.md) | English, one Chinese section | Era 1, 2026‑07‑14 | Shows only the manual tmux start; schema omits `liveParams`; "accel not sent to CAN" held only before 2026‑07‑17 | [02](02-setup-ssh-networking.md) (§0 network), [03](03-telemetry-stream.md), [04](04-control-principles-and-frenet.md) |
| [`remote/controls_principles.md`](../remote/controls_principles.md) | Chinese | Era 1, 2026‑07‑14 | Stock-PCM configuration only; its `file:line` refs point into the device's sunnypilot source | [04](04-control-principles-and-frenet.md) |
| [`remote/Arman/README.md`](../remote/Arman/README.md) | English | Era 1, 2026‑07‑17 | JSON example lacks `"stop"`; says record mode writes only at Ctrl‑C (it also rewrites the files every 2 s); presents `--local-frame` as a general no-GPS fallback | [05](05-curvepoints-pipeline.md), [06](06-client-interface-spec.md) |
| [`remote/Arman/STOP_COMMAND.md`](../remote/Arman/STOP_COMMAND.md) | English | Era 1, 2026‑07‑17 | Its 0.9.8 reference design was never deployed; stale "open item"; unbalanced code fence | [07](07-longitudinal-stop.md), [14](14-device-changes-and-revert.md) |
| [`remote/Arman/EXPERIMENT_RUNBOOK.md`](../remote/Arman/EXPERIMENT_RUNBOOK.md) | English | Era 1, 2026‑07‑17 | Its objstopd command uses v1 flags that fail with v2; its JSON example lacks `"stop"`; says record mode writes only at Ctrl‑C; presents `--local-frame` as the no-GPS fallback; expects the live heartbeat to show `OK -> …`, but a working export mostly prints `GPS ok, waiting for modelV2 trajectory` | [07](07-longitudinal-stop.md), [13](13-operations-runbook.md) |
| [`remote/Arman/vision/STOP_SIGN_VISION.md`](../remote/Arman/vision/STOP_SIGN_VISION.md) | English | Era 1, 2026‑08‑06 (sections v2.1 2026‑08‑06, v2 2026‑07‑25, v1 undated) | v1 part is superseded; calls `DisengageOnAccelerator=0` pending (it was applied); lists autostart as not done (done 2026‑08‑06) | [08](08-vision-stop-objstopd.md) |
| [`remote/Arman/ETHERNET_SETUP.md`](../remote/Arman/ETHERNET_SETUP.md) | English | Era 1, 2026‑08‑06 | "Field checklist (tomorrow)" has no recorded result | [02](02-setup-ssh-networking.md) |
| [`remote/Arman/OPERATIONS.md`](../remote/Arman/OPERATIONS.md) | Chinese | Era 1, 2026‑08‑06 | §0 "pending enable" is stale; implies `"stop"` in every mode; §2.5's manual objstopd run omits `touch /data/objstop/manual_mode`, so two instances can run; says record mode writes only at Ctrl‑C; suggests `--local-frame` for indoor/no-GPS use; expects the live heartbeat to show `OK -> …` (same caveat as `EXPERIMENT_RUNBOOK.md`); §9 revert table incomplete and one backup comment backwards | [13](13-operations-runbook.md), with parts in [01](01-overview.md), [02](02-setup-ssh-networking.md), [05](05-curvepoints-pipeline.md), [06](06-client-interface-spec.md), [07](07-longitudinal-stop.md), [08](08-vision-stop-objstopd.md), [10](10-no-can-mode-sunnypilot.md), [14](14-device-changes-and-revert.md) |
| [`remote/Arman/dashcam_anywhere/README.md`](../remote/Arman/dashcam_anywhere/README.md) | Chinese | Era 2, 2026‑10‑03 | Uses the desktop path; "no low-voltage protection" holds only without a car harness; says every state-changing command asks for confirmation (`reset-calib` does not) | [11](11-dashcam-anywhere-design.md), [14](14-device-changes-and-revert.md) |
| [`remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md`](../remote/Arman/dashcam_anywhere/LAPTOP_GUIDE.md) | Chinese | Era 2, 2026‑10‑03 | `reset-calib` does not ask for confirmation; "does not shut down automatically" (§8) holds only without a car harness; copying a private key is discouraged | [12](12-dashcam-anywhere-field-guide.md) (§1.2 and §3 also [02](02-setup-ssh-networking.md)) |
| Docstrings of [`watch_detect.py`](../remote/Arman/watch_detect.py) and [`manual_stop_send.py`](../remote/Arman/manual_stop_send.py) | Chinese | Era 1, 2026‑08‑13 | The `manual_stop_send.py` docstring gives the wrong default host | [08](08-vision-stop-objstopd.md), [09](09-stop-signal-udp.md) |
| Slide decks [`openpilot_controls_slides.pdf`](../remote/openpilot_controls_slides.pdf) (+ [`.html`](../remote/openpilot_controls_slides.html)) and [`cp_slides.html`](../remote/Arman/cp_slides.html) | English | Era 1, 2026‑07‑14 | Stock-PCM slide 3; `cp_slides.html` slide 6 lacks `"stop"`, and its slide 8 overstates what `cp_view` tests and says record mode writes only on exit. The PDF renders on GitHub; open the HTML decks locally | [04](04-control-principles-and-frenet.md), [05](05-curvepoints-pipeline.md) |

## Root files and licences

- [`README.md`](../README.md): the repository front page.
- [`LICENSE`](../LICENSE): MIT, for the original work in this repository.
- [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md): openpilot and sunnypilot (MIT) excerpts in the patch and the patcher scripts, and two objstopd image helpers adapted from openpilot; YOLOv8 (AGPL‑3.0), whose code and weights are not included.
- [`.gitignore`](../.gitignore): keeps tool output, device data and model weights out of the repository.

The project is not affiliated with, endorsed by or supported by comma.ai, openpilot, sunnypilot or Ultralytics. It is research tooling; read the safety notes in [01](01-overview.md#safety-and-legal-notes) before running anything that touches a vehicle.

## See also

- [01 — Overview](01-overview.md): start here
- [06 — Client interface specification](06-client-interface-spec.md): the contract for anyone consuming the data
- [15 — File reference](15-file-reference.md): every file in the repo
- [16 — Errata and crosswalk](16-errata-and-crosswalk.md): where the original notes are wrong, and where each section went
