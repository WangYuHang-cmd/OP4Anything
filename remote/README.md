# comma reg_export — laptop client

Real-time openpilot planning/control signals from a comma 3X (sunnypilot 0.9.7.1)
over a phone hotspot. No openpilot install needed — pure Python.

## 0. Network (phone hotspot)
1. Turn on your phone hotspot (**Android preferred** — iPhone may isolate clients).
2. On the comma: Settings → Network → join the hotspot; note the comma's IP.
3. On this laptop: join the same hotspot.
4. Verify reachability: `ping <comma_ip>` must work. If not, the hotspot has client
   isolation — use an Android hotspot or a cheap travel router.

## 1. Start the exporter on the comma (once, via SSH)
```
ssh comma@<comma_ip>
cd /data/openpilot && tmux new -s reg \
  'PYTHONPATH=/data/openpilot /usr/local/pyenv/versions/3.11.4/bin/python3 tools/reg_export/exporter.py'
```
It serves JSON-lines on TCP **:7700**. (Data only flows when the car is **onroad** —
openpilot's modeld/controlsd only run when connected to the car.)

## 2. Use it on this laptop
Set `IP` to the comma's hotspot IP.

- **Quick check / print rate:**
  ```
  python stream_lib.py --ip <comma_ip>
  ```
- **Log to CSV / parquet:**
  ```
  python recv_log.py --ip <comma_ip> --out drive.csv
  python recv_log.py --ip <comma_ip> --out drive.parquet   # pip install pandas pyarrow
  ```
- **Live plot (simple):**
  ```
  pip install matplotlib
  python live_plot.py --ip <comma_ip>
  ```
- **Dashboard (pretty — bird's-eye trajectory + throttle/brake/steer):**
  ```
  pip install matplotlib
  python dashboard.py --ip <comma_ip>
  # preview without a device: python dashboard.py --ip x --selftest  (writes dashboard_selftest.png)
  ```
  Left = vehicle-frame bird's-eye (planned path, 4 lane lines, 2 road edges, lead, ego at origin).
  Right = speed / planned accel (throttle+/brake−) / curvature time-series. Bottom = engage & command status.
- **Feed your own program (real-time):**
  ```python
  from stream_lib import stream
  for rec in stream("<comma_ip>"):
      curv = rec["carControl"]["curvature"]     # final lateral command (1/m)
      acc  = rec["longitudinalPlan"]["aTarget0"]# near-term planned accel (accels[0])
      des  = rec["modelV2"]["desiredCurvature"] # model lateral plan
      # ... your downstream logic ...
  ```

## Control-command & trajectory tools (added)
- **`controls_monitor.py --ip <ip>`** — terminal table:每个信号的 COMMAND / SENT-CAN / MEASURED（steering angle/rate/torque、speed、accel、gas/brake %）。`--csv` 落盘,`--selftest` 演示。
- **`frenet.py`** — 把轨迹转成**车辆无关**的 Frenet 输出:①相对车道中心 `(s,d)`;②弧长参数化 `s,x,y,θ,κ,v,a`。`frenet.to_csv()` 导出给大巴规划器。`python3 frenet.py --test` 跑单测。
- **`frenet_view.py --ip <ip>`** — 四联可视化:d(s)、κ(s)、v/a(s)、**大巴可迁移性**面板(所需 v²κ vs 大巴包络,超限红色)。参数:`--bus-wheelbase 12 --bus-max-steer-deg 40 --bus-max-lat-acc 2.0`。`--selftest` 出 PNG。
- **`dashboard.py`** — 已升级:planned accel 面板拆 throttle+(绿)/brake−(红),状态条显示实测 gas/brake %。
- **`controls_principles.md`** — 控制原理速查(公式+file:line+对照表)。
- 幻灯片见 `openpilot_controls_slides.pdf`(英文,6 页,含坐标系转换与迁移性)。

> 说明:本车(Civic Bosch, 股票 PCM)**accel 命令不发 CAN**(仅假点巡航键改设定速度);Bosch 无踏板百分比命令,gas/brake 只有实测。转向走 torque(±4096),角度命令由曲率派生 `desSteerAngleDeg`。

## Record schema (one JSON object per ~10 ms)
Top level: `t_wall` (unix s), `t_mono` (s), `seq`. Then per-service blocks; each has
`_upd` (updated this frame), `_valid`, `_mono` (source logMonoTime, for alignment).

| block | key fields | what it is |
|---|---|---|
| `carState` | vEgo, aEgo, vCruise, steeringAngleDeg, steeringTorque, gas/brake, cruiseEnabled, standstill | vehicle feedback (100 Hz) |
| `carControl` | enabled, latActive, longActive, **steer, curvature, accel**, longControlState | **final control command** (100 Hz) |
| `carOutput` | steer, curvature, accel | actually-sent (post-limit) values |
| `controlsState` | state, **desiredCurvature**, curvature, upAccelCmd/uiAccelCmd/ufAccelCmd, lat{...} | controller internals (100 Hz) |
| `longitudinalPlan` | **aTarget0** (=accels[0]), vTarget0, hasLead, source, fcw, speeds[], accels[] | longitudinal plan / MPC solution (20 Hz; arrays when `_upd`) |
| `modelV2` | **desiredCurvature**, pos_x/y/z[], vel_x[], orient_z[], laneChange*, confidence | trajectory + lateral plan (20 Hz; arrays when `_upd`) |
| `loc` | lat, lon, yaw, vel | localization (liveLocationKalman, 20 Hz) |
| `radar` | status, dRel, vRel, vLead | lead vehicle |

Heavy arrays (`pos_x`, `speeds`, ...) are only present on frames where that 20 Hz
service updated — check `_upd` or key presence.

## Notes
- The exporter is **read-only** (msgq broadcast) — it cannot affect driving.
- A slow laptop just **drops old frames**; it never stalls sampling on the car.
- Must match the device version (0.9.7.1). If the device is re-flashed to another
  version, the field paths in `exporter.py` may need updating.
