# openpilot decel-to-stop command (Civic Bosch)

## ✅ DEPLOYED on experimental device 192.168.1.231 (sunnypilot 0.9.7.1)
This device runs **sunnypilot 0.9.7.1**, not the 0.9.8 repo below, and has **no**
route-following. So on the device the stop uses a **file flag** (no param, no C++
rebuild) — one edited Python file:
- `selfdrive/controls/lib/longitudinal_planner.py` — added `import os` and, at the
  `force_slow_decel` hook: `stop_requested = os.path.exists('/tmp/op_stop_requested')`
  → `if force_slow_decel or stop_requested: v_cruise = 0.0`. Backup at
  `longitudinal_planner.py.bak_arman`.
- `ExperimentalLongitudinalEnabled = 1` set → OP longitudinal enabled (verified after reboot).
- `/tmp` is tmpfs → a reboot always clears a stale stop.

**Trigger (from laptop <TAILSCALE_IP>, over SSH to the car):**
```bash
# STOP (decelerate to a full stop)
ssh comma@192.168.1.231 'touch /tmp/op_stop_requested'
# GO (resume normal speed)
ssh comma@192.168.1.231 'rm -f /tmp/op_stop_requested'
# status
ssh comma@192.168.1.231 'ls -l /tmp/op_stop_requested 2>/dev/null && echo STOP-ARMED || echo GO'
```
**Revert everything:**
```bash
ssh comma@192.168.1.231 'cp /data/openpilot/selfdrive/controls/lib/longitudinal_planner.py.bak_arman \
  /data/openpilot/selfdrive/controls/lib/longitudinal_planner.py'
ssh comma@192.168.1.231 'python3 -c "from openpilot.common.params import Params; Params().remove(\"ExperimentalLongitudinalEnabled\")"'
ssh comma@192.168.1.231 'sudo reboot'   # back to stock ACC + radar + AEB
```

---
## Reference implementation (0.9.8 repo — param-based, NOT the deployed device)

Send a "stop" at any moment → the car **gradually decelerates to a full stop**, reusing
openpilot's own controlled-decel path (the MPC produces a smooth, jerk-limited stop; the
longitudinal state machine finishes it via `LongCtrlState.stopping`).

> ⚠️ **This actuates the brakes on a real vehicle.** Test only in a closed area, at low
> speed, with a driver ready to take over. Enabling OP longitudinal is a safety-layer
> change — read the whole file first.

## How it works
`longitudinal_planner.py` reads a `StopRequested` param each cycle. When set, it forces
`v_cruise = 0` (exactly the `forceDecel` path). The MPC then decelerates to 0 →
`shouldStop` → `stopping` state → `ACCEL_COMMAND` brakes to a stop.

Chain (verified file:line, this repo):
- `longitudinal_planner.py` — `if force_slow_decel or stop_requested: v_cruise = 0.0`
- `longitudinal_planner.py:66` — `should_stop` when `v_target < vEgoStopping`
- `longcontrol.py:71` — `stopping`: `output_accel` ramps down at `stoppingDecelRate` to `stopAccel`
- `honda/carcontroller.py:211-216` — `ACCEL_COMMAND` (only when `openpilotLongitudinalControl`)

## Code changes made (in this repo)
1. `common/params.cc` — registered `{"StopRequested", CLEAR_ON_MANAGER_START}` (a stale
   stop is auto-cleared on reboot).
2. `selfdrive/controls/lib/longitudinal_planner.py` — honor `StopRequested` (forces `v_cruise=0`).
3. `Arman/stop_command.py` — device-side helper to set/clear the stop.

## HARD prerequisite: enable OP longitudinal control
On the stock-PCM Civic, `openpilotLongitudinalControl=False` and **accel is not sent to
CAN** — so the stop is inert until OP long is enabled:
```bash
# on the device
python3 -c "from openpilot.common.params import Params; Params().put_bool('ExperimentalLongitudinalEnabled', True)"
# then reboot so CarParams re-inits
```
What this changes (Honda Bosch, `interface.py:33-41,195`):
- `openpilotLongitudinalControl=True`, `pcmCruise=False` (openpilot manages cruise, not the stalk).
- **stock radar disabled** (`radarUnavailable=True`) — longitudinal uses the vision model only, no radar lead/AEB.
- panda gets `FLAG_HONDA_BOSCH_LONG`; accel clipped to `[BOSCH_ACCEL_MIN, BOSCH_ACCEL_MAX]`.

## Deploy
The `params.cc` change adds a new key, so the C++ params lib must be rebuilt on the device
(same as when `RouteFollowEnabled` was added):
```bash
# copy the 3 changed files to the device's openpilot, then:
cd /data/openpilot && scons -j4 common/   # rebuild params
# (full: scons -j4)  then reboot
```

## Use (closed course)
```bash
# device or via SSH
python3 Arman/stop_command.py --stop     # begin decel-to-stop
python3 Arman/stop_command.py --go       # clear -> resume
python3 Arman/stop_command.py --status
```
Watch it live with `cp_view.py` on the laptop (speed tile → 0). Trigger a stop from a
script/route logic by setting the same param when you want (route end, obstacle, timer…).

## Safety checklist (every test)
- [ ] Closed/empty area, low speed (≤ ~15 km/h to start).
- [ ] Driver hands ready, foot over the brake; a real brake press overrides everything.
- [ ] Confirm OP long is actually engaged (LONG ● in cp_view / controls_monitor).
- [ ] First test `--stop` from a slow crawl; verify smooth decel, no jerk, full stop.
- [ ] `--go` clears cleanly and the car resumes only as expected.
- [ ] Reboot clears `StopRequested` (CLEAR_ON_MANAGER_START) — verify.

## Open item to confirm before deploying
This repo is openpilot **0.9.8**. Confirm which codebase/version is actually on the car
(memory notes a v0.11.1 device) and that these three files exist there with the same
`routeFollowState`/planner structure before copying — otherwise field/param paths may differ.
```
