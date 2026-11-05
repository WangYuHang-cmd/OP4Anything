#!/usr/bin/env python3
"""test_stopsm.py — v2 simulation tests: distance KF, stop ramp, state machine, flag protocol.

Pure simulation (simulated clock, no camera/car). Covers the three field problems:
imprecise stops, difficult resume (green / sign-out-of-view / wait), re-trigger.
"""
import argparse
import math
import random
import sys

from objstopd import (Track, VisionStopSM, ramp_v, pinhole_d, SIGN_H, F_NARROW,
                      DRIVING, BRAKING, STOPPED_SIGN, STOPPED_RED, STOPPED_PED, RESUMING)

ok = True


def chk(name, cond, detail=""):
  global ok
  print(("PASS " if cond else "FAIL ") + name + (f"   {detail}" if detail else ""))
  ok = ok and cond


def mkargs(**kw):
  d = dict(wait_sec=3.0, clear_sec=1.5, sign_setback=3.0, tl_setback=10.0,
           tl_max_cy=0.6, ped_min_h=90.0, ped_band_lo=0.2, ped_band_hi=0.8,
           ped_min_bottom=0.45)
  d.update(kw)
  return argparse.Namespace(**d)


# ---------- planner flag parser (mirror of the device planner v2 patch) ----------
def parse_flag(txt, now):
  """Returns 'none' | 'ignore' | 'now' | ('dist', d)."""
  if txt is None:
    return "none"
  txt = txt.strip()
  if not txt:
    return "now"                      # legacy empty file (manual touch)
  try:
    parts = dict(p.split("=", 1) for p in txt.split())
    d = float(parts.get("d", 0.0))
    t = float(parts.get("t", 0.0))
    if now - t > 1.0:
      return "ignore"                 # stale -> daemon died, release
    return ("dist", d) if d > 0.0 else "now"
  except Exception:
    return "now"                      # garbled -> fail-safe stop


# ---------- 1. KF ----------
def test_kf():
  rng = random.Random(0)
  tr = Track(SIGN_H)
  v, dt = 8.0, 0.05
  d_true = 40.0
  t = 0.0
  det_period = 0.2
  next_det = 0.0
  errs_near = []
  while d_true > 5.0:
    tr.predict(v * (1 + rng.uniform(-0.02, 0.02)), dt)
    if t >= next_det:
      next_det += det_period
      h_true = F_NARROW * SIGN_H / d_true
      h_meas = h_true + rng.gauss(0, 1.0) * 2   # ±1 px input quantization ~ 2 native px @320-sub2
      d_meas = F_NARROW * SIGN_H / max(h_meas, 1.0)
      tr.update(d_meas, t)
    if tr.d is not None and d_true <= 15.0:
      errs_near.append(abs(tr.d - d_true))
    d_true -= v * dt
    t += dt
  chk("KF: |err|<1m inside 15m", max(errs_near) < 1.0, f"max={max(errs_near):.2f}m")

  # 2 s dropout -> dead-reckon drift small
  tr2 = Track(SIGN_H)
  d_true, t = 25.0, 0.0
  for _ in range(10):
    tr2.predict(v, dt)
    tr2.update(F_NARROW * SIGN_H / (F_NARROW * SIGN_H / d_true), t)
    d_true -= v * dt; t += dt
  for _ in range(int(2.0 / dt)):      # dropout, 2% speed error
    tr2.predict(v * 1.02, dt)
    d_true -= v * dt; t += dt
  chk("KF: 2s dropout drift <0.5m", abs(tr2.d - d_true) < 0.5, f"drift={abs(tr2.d-d_true):.2f}m")

  # outlier gate: a 2x-distance jump must be rejected
  before = tr2.d
  accepted = tr2.update(before * 2.0, t)
  chk("KF: 2x outlier rejected", (not accepted) and abs(tr2.d - before) < 1e-9)


# ---------- 2. closed-loop ramp precision ----------
def sim_vehicle_step(v, v_target, dt, lag=0.4, a_min=-1.2, a_max=1.5):
  a = max(a_min, min(a_max, (v_target - v) / lag))
  return max(v + a * dt, 0.0), a


def planner_ramp(d, v, hold):
  """Mirror of device planner v2: returns (v_cruise_cap, hold)."""
  d_eff = d - v * 0.5
  if hold or d_eff < 2.0 or ramp_v(d_eff) < 0.5:
    return 0.0, True
  return ramp_v(d_eff), hold


def test_ramp():
  dt = 0.05
  v, d_line = 8.0, 40.0             # distance to the target stop point
  hold = False
  max_dec = 0.0
  t = 0.0
  while (v > 0.05 or not hold) and t < 60:
    cap, hold = planner_ramp(d_line, v, hold)
    v_target = min(15.0, cap)
    v, a = sim_vehicle_step(v, v_target, dt)
    max_dec = min(max_dec, a)
    d_line -= v * dt
    t += dt
  chk("ramp: stops before target", d_line > -0.3, f"remaining={d_line:.2f}m")
  chk("ramp: stops close to target (<4m early)", d_line < 4.0, f"remaining={d_line:.2f}m")
  chk("ramp: decel within -1.2", max_dec >= -1.25, f"max_dec={max_dec:.2f}")

  # jitter through zero must not unlatch the hold
  hold = True
  for d_j in [0.5, -0.5, 1.5, 2.5, -1.0]:
    cap, hold = planner_ramp(d_j, 0.0, hold)
    if cap != 0.0:
      break
  chk("ramp: hold latched under d jitter", hold and cap == 0.0)


# ---------- 3. SM scenarios ----------
def run_sm(sm, script, dt=0.05):
  """script(t, sm_state, v) -> (meas, ped, gas, v). Returns timeline [(t,state,flag)]."""
  t, v = 0.0, 0.0
  tl = []
  n = int(60.0 / dt)
  for _ in range(n):
    meas, ped, gas, v, done = script(t, sm.state, v)
    out = sm.update(t, dt, v, meas, ped, gas)
    tl.append((round(t, 2), out["state"], out["flag"]))
    if done:
      break
    t += dt
  return tl


def first(tl, state, after=0.0):
  for t, s, _ in tl:
    if s == state and t >= after:
      return t
  return None


def test_sm_stop_sign():
  a = mkargs()
  sm = VisionStopSM(a)
  world = {"d_sign": 33.0, "phase": 0, "d_at_stop": None}

  def script(t, state, v):
    if state == STOPPED_SIGN and world["d_at_stop"] is None:
      world["d_at_stop"] = world["d_sign"]
    # vehicle: follow the SM's own flag like the planner would
    meas = []
    if world["d_sign"] > 4.0 and int(t / 0.2) != int((t - 0.05) / 0.2):
      meas = [{"t": t, "cls": "stop_sign", "d": world["d_sign"], "color": None}]
    flag = sm.update.__self__  # not used; we emulate below
    # target speed from last state
    if state in (STOPPED_SIGN, STOPPED_RED, STOPPED_PED):
      vt = 0.0
    elif state == BRAKING:
      cap, _ = planner_ramp(max(world["d_sign"] - a.sign_setback, 0.0), v, False)
      vt = min(6.0, cap)
    else:
      vt = 6.0
    v, _ = sim_vehicle_step(v, vt, 0.05)
    world["d_sign"] -= v * 0.05
    return meas, False, False, v, False

  tl = run_sm(sm, script)
  t_brake = first(tl, BRAKING)
  t_stop = first(tl, STOPPED_SIGN)
  t_res = first(tl, RESUMING)
  t_drv = first(tl, DRIVING, after=(t_res or 0) + 0.01)
  chk("sign: latch->BRAKING", t_brake is not None, f"t={t_brake}")
  chk("sign: reaches STOPPED_SIGN", t_stop is not None, f"t={t_stop}")
  chk("sign: stop near line (0..6m before sign)", world["d_at_stop"] is not None and
      0.0 < world["d_at_stop"] < 6.0,
      f"d_at_stop={world['d_at_stop'] if world['d_at_stop'] is None else round(world['d_at_stop'],2)}")
  chk("sign: resumes after wait_sec", t_res is not None and t_stop is not None and
      2.9 <= (t_res - t_stop) <= 4.0, f"held={None if not t_res else round(t_res-t_stop,2)}s")
  chk("sign: back to DRIVING (pass-tracking exit)", t_drv is not None, f"t={t_drv}")

  # while RESUMING, the served sign re-detected close -> no re-latch
  sm2 = VisionStopSM(a)
  sm2.state = RESUMING
  sm2.resume_odo, sm2.resume_t = 0.0, 0.0
  for i in range(20):
    out = sm2.update(i * 0.05, 0.05, 2.0, [{"t": i * 0.05, "cls": "stop_sign", "d": 2.0, "color": None}], False)
  chk("sign: served sign (d=2) cannot re-latch in RESUMING", sm2.tracks["stop_sign"].d is None)

  # a genuinely NEW sign at 40m during RESUMING accumulates and stops again later
  sm3 = VisionStopSM(a)
  sm3.state = RESUMING
  sm3.resume_odo, sm3.resume_t = 0.0, 0.0
  t = 0.0
  for i in range(400):
    meas = []
    if int(t / 0.2) != int((t - 0.05) / 0.2):
      meas = [{"t": t, "cls": "stop_sign", "d": 40.0 - 3.0 * t, "color": None}]
    out = sm3.update(t, 0.05, 3.0, meas, False)
    t += 0.05
    if out["state"] == BRAKING:
      break
  chk("sign: NEW sign at 40m latches after RESUMING", out["state"] == BRAKING, f"state={out['state']}")


def test_sm_red_light():
  a = mkargs()
  sm = VisionStopSM(a)
  d = {"v": 6.0, "dist": 45.0, "green_from": None}

  def script(t, state, v):
    meas = []
    if int(t / 0.2) != int((t - 0.05) / 0.2):
      if d["green_from"] is not None and t >= d["green_from"]:
        meas = [{"t": t, "cls": "red_light", "d": None, "color": "green"}]   # wide cam
      elif d["dist"] > 12.0:
        meas = [{"t": t, "cls": "red_light", "d": d["dist"], "color": "red"}]
      # between 12m and stop: light out of narrow view, NOTHING seen (the hard case)
    if state in (STOPPED_RED,):
      vt = 0.0
    elif state == BRAKING:
      cap, _ = planner_ramp(max(d["dist"] - a.tl_setback, 0.0), v, False)
      vt = min(6.0, cap)
    else:
      vt = 6.0
    v, _ = sim_vehicle_step(v, vt, 0.05)
    d["dist"] -= v * 0.05
    return meas, False, False, v, False

  tl = run_sm(sm, script)
  t_stop = first(tl, STOPPED_RED)
  chk("red: stops (setback point)", t_stop is not None and 8.0 < d["dist"] < 16.0,
      f"dist_to_light={d['dist']:.1f}m")
  # red now invisible for a long time -> MUST NOT resume (old bug: absent-timeout)
  after = [s for tt, s, _ in tl if t_stop is not None and t_stop + 5.0 <= tt <= t_stop + 12.0]
  chk("red: light invisible != resume (holds)", after and all(s == STOPPED_RED for s in after))

  # feed green -> resumes
  sm_g = sm
  t0 = tl[-1][0]
  res = None
  for i in range(200):
    t = t0 + i * 0.05
    meas = []
    if i % 4 == 0:
      meas = [{"t": t, "cls": "red_light", "d": None, "color": "green"}]
    out = sm_g.update(t, 0.05, 0.0, meas, False)
    if out["state"] == RESUMING:
      res = t - t0
      break
  chk("red: green confirmed -> RESUMING", res is not None and res < 3.0, f"after={res}s")


def test_sm_red_escapes():
  a = mkargs()
  sm = VisionStopSM(a)
  sm.state = STOPPED_RED
  sm.t_standstill = 0.0
  alerted = False
  for i in range(int(125.0 / 0.5)):
    out = sm.update(i * 0.5, 0.5, 0.0, [], False)
    alerted = alerted or bool(out["alert"])
  chk("red: >120s no light -> alert but HOLDS", alerted and out["state"] == STOPPED_RED)
  out = sm.update(126.0, 0.05, 0.0, [], False, gas_pressed=True)
  chk("red: driver gas -> RESUMING", out["state"] == RESUMING)


def test_sm_green_on_approach():
  a = mkargs()
  sm = VisionStopSM(a)
  # latch a red at 40m while moving
  t = 0.0
  for i in range(12):
    sm.update(t, 0.05, 6.0, [{"t": t, "cls": "red_light", "d": 40.0, "color": "red"}], False)
    t += 0.05
  chk("green-approach: latched BRAKING", sm.state == BRAKING)
  # light turns green while still moving -> release
  for i in range(40):
    sm.update(t, 0.05, 5.0, [{"t": t, "cls": "red_light", "d": 35.0, "color": "green"}], False)
    t += 0.05
    if sm.state == RESUMING:
      break
  chk("green-approach: releases to RESUMING", sm.state == RESUMING)


def test_sm_pedestrian():
  a = mkargs()
  sm = VisionStopSM(a)
  t = 0.0
  # N-of-M: a single sighting must NOT stop (false-positive protection)...
  out = sm.update(t, 0.05, 5.0, [], True)
  chk("ped: single sighting does NOT stop", out["state"] == DRIVING and out["flag"] is None)
  for _ in range(20):                    # no more sightings -> stays clear
    t += 0.05
    out = sm.update(t, 0.05, 5.0, [], False)
  chk("ped: no repeat -> still DRIVING", out["state"] == DRIVING)
  # ...two sightings within 1 s DO stop
  t += 0.05
  sm.update(t, 0.05, 5.0, [], True)
  t += 0.25
  out = sm.update(t, 0.05, 5.0, [], True)
  chk("ped: 2 sightings in 1s -> BRAKING + stop-now", out["state"] == BRAKING and out["flag"] == ("now",))
  # stop, ped leaves, clear_sec later resume
  for i in range(30):
    t += 0.05
    out = sm.update(t, 0.05, 0.1, [], True)
  chk("ped: STOPPED_PED at standstill", out["state"] == STOPPED_PED)
  t_leave = t
  while t < t_leave + 3.0:
    t += 0.05
    out = sm.update(t, 0.05, 0.0, [], False)
    if out["state"] == RESUMING:
      break
  chk("ped: clears after clear_sec", out["state"] == RESUMING and 1.4 <= t - t_leave <= 2.2,
      f"after={t-t_leave:.2f}s")

  # pedestrian appearing DURING the sign wait (confirmed before expiry) extends the hold
  sm2 = VisionStopSM(a)
  sm2.state = STOPPED_SIGN
  sm2.t_standstill = 0.0
  sm2.update(2.5, 0.05, 0.0, [], True)
  sm2.update(2.75, 0.05, 0.0, [], True)               # confirmed -> ped_hold before 3s expiry
  out = sm2.update(4.0, 0.05, 0.0, [], True)          # wait_sec elapsed but ped present
  chk("ped: blocks sign resume", out["state"] == STOPPED_SIGN and out["flag"] == ("now",))
  out = sm2.update(4.1, 0.05, 0.0, [], True)
  for i in range(60):
    out = sm2.update(4.15 + i * 0.05, 0.05, 0.0, [], False)
    if out["state"] == RESUMING:
      break
  chk("ped: sign resumes after ped clears", out["state"] == RESUMING)


def test_operator_release():
  """Static dummy scenario: pedestrian never leaves -> operator release forces resume."""
  a = mkargs()
  sm = VisionStopSM(a)
  t = 0.0
  for _ in range(4):                     # confirm ped, brake to stop
    t += 0.2
    sm.update(t, 0.2, 2.0, [], True)
  for _ in range(10):
    t += 0.2
    out = sm.update(t, 0.2, 0.0, [], True)
  chk("release: held in STOPPED_PED (dummy present)", out["state"] == STOPPED_PED)
  # hold >20s with dummy still there -> escalation alert, still holding
  for _ in range(110):
    t += 0.2
    out = sm.update(t, 0.2, 0.0, [], True)
  chk("release: >20s alert while holding", "release" in out["alert"] and out["state"] == STOPPED_PED)
  # operator release -> resumes even though dummy is still detected
  out = sm.update(t + 0.2, 0.2, 0.0, [], True, release=True)
  chk("release: forces RESUMING with ped still visible", out["state"] == RESUMING and out["flag"] is None)


def test_dilemma():
  a = mkargs()
  sm = VisionStopSM(a)
  t = 0.0
  for i in range(12):                       # v=12, sign at 20m -> a_req = 144/34 = 4.2
    out = sm.update(t, 0.05, 12.0, [{"t": t, "cls": "stop_sign", "d": 20.0, "color": None}], False)
    t += 0.05
  chk("dilemma: no latch, keeps DRIVING", out["state"] == DRIVING and sm.tracks["stop_sign"].waived)


# ---------- 4. flag protocol ----------
def test_flag_protocol():
  now = 100.0
  chk("flag: valid dist", parse_flag("d=12.30 t=99.8 src=v", now) == ("dist", 12.3))
  chk("flag: d=0 -> now", parse_flag("d=0.00 t=99.9 src=v", now) == "now")
  chk("flag: empty (manual touch) -> now", parse_flag("", now) == "now")
  chk("flag: stale -> ignore", parse_flag("d=12.0 t=90.0 src=v", now) == "ignore")
  chk("flag: garbled -> fail-safe now", parse_flag("hello;;", now) == "now")
  chk("flag: absent -> none", parse_flag(None, now) == "none")


def main():
  test_kf()
  test_ramp()
  test_sm_stop_sign()
  test_sm_red_light()
  test_sm_red_escapes()
  test_sm_green_on_approach()
  test_sm_pedestrian()
  test_operator_release()
  test_dilemma()
  test_flag_protocol()
  print("\nALL V2 TESTS OK" if ok else "\nV2 TESTS FAILED")
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
