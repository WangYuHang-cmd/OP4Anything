# openpilot 控制原理速查（sunnypilot 0.9.7.1 · 2020 Civic Bosch）

> 代码证据取自设备 `comma@192.168.1.231:/data/openpilot`。本车关键 param：
> `EnforceTorqueLateral=1`（横向走 Torque 控制器）、`openpilotLongitudinalControl=False`（股票 PCM 纵向）、`CustomStockLong=1`。

## 1. 横向：期望曲率 → 转向力矩
| 跳 | 量 | 公式/来源 | 单位 | file:line |
|---|---|---|---|---|
| 规划 | `modelV2.action.desiredCurvature` | 模型输出 | 1/m | log.capnp Action |
| 限幅 | `desired_curvature` | `clip_curvature`，速率≤ `MAX_LATERAL_JERK/v²`（jerk=5） | 1/m | controlsd.py:649；drive_helpers.py:260 |
| 控制器 | `actuators.steer` | **LatControlTorque**：`a_lat=κ·v²` → `ff=a_lat/1.6917+0.2546` → PID(kp1.0,ki0.1) → `steer=−output∈[−1,1]`；角度命令≡0 | 归一 | latcontrol_torque.py:177,262,286 |
| CAN | `steerOutputCan` | `apply_steer=int(−steer×STEER_MAX)`，`STEER_MAX=4096` | ±4096 | carcontroller.py:212 |
| 发送 | `STEERING_CONTROL.STEER_TORQUE` | =apply_steer（lkas_active 时） | ±4096 | hondacan.py:123 |

**torque 换算参数**（torque_data，legend=[latAccelFactor, maxLatAccel, friction]）：`HONDA_CIVIC_BOSCH=[1.6917, 0.4013, 0.2546]`。
**最终实发值** = `carOutput.actuatorsOutput.steerOutputCan`。`actuators.steer` 只是中间归一量。

## 2. 纵向：速度规划 → 加速度（本车不发 CAN）
| 量 | 公式/来源 | 单位 | file:line |
|---|---|---|---|
| 规划 | `longitudinalPlan.speeds/accels` | MPC 解 | m/s, m/s² | longitudinal_planner.py |
| 控制器 | `actuators.accel` | 状态机 off/pid/stopping/starting + PID(err=v_target−vEgo, ff=a_target)，Bosch 限[−3.5,2.0] | m/s² | longcontrol.py:132；controlsd.py:643 |
| **实发** | — | **本车 `openpilotLongitudinalControl=False`：accel 只进日志,不发 CAN**；OP 仅假点巡航键(`SCM_BUTTONS`)改股票 ACC 设定速度 | — | carcontroller.py:269;interface.py:50 |

Bosch 若开 OP 纵向 → 发 `ACC_CONTROL.ACCEL_COMMAND`（车 PCM 执行），**无踏板百分比命令**（compute_gb 返回 0）。Nidec 才发 `BRAKE_COMMAND`+`PCM_GAS`。

## 3. 踏板/传感器（只有实测）
| 字段 | CAN 信号 | 单位 | file:line |
|---|---|---|---|
| `carState.steeringAngleDeg` | STEERING_SENSORS.STEER_ANGLE | 度 | carstate.py:185 |
| `carState.steeringRateDeg` | STEER_ANGLE_RATE | 度/s | :186 |
| `carState.steeringTorque`（驾驶员） | STEER_STATUS.STEER_TORQUE_SENSOR | 原始 | :207 |
| `carState.steeringTorqueEps`（EPS 实际） | STEER_MOTOR_TORQUE.MOTOR_TORQUE | 原始 | :208 |
| `carState.gas` | POWERTRAIN_DATA.PEDAL_GAS | DBC 刻度（非 0-1，需自标定%） | :204 |
| `carState.brake` | VSA_STATUS.USER_BRAKE | VSA 模拟量 | :244 |
| `carState.vEgo/aEgo` | 轮速/变速箱 KF | m/s, m/s² | :167-178 |

## 4. 命令 vs 实测 对照（下游订阅）
- 转向力矩：`carControl.steer`[-1,1]（cmd）→ `carOutput.steerOutputCan`±4096（实发）→ `carState.steeringTorqueEps`（EPS 实际）。仅比符号/趋势，刻度不可直接比。
- 转向角：torque 模式无原生角度命令 → exporter 派生 `controlsState.desSteerAngleDeg = deg(atan(L·κ))·steerRatio+offset`（L=2.7，steerRatio 用 liveParameters）；实测 `carState.steeringAngleDeg`。
- 速度：`controlsState.vCruise`（设定，kph）vs `carState.vEgo`（实测，m/s）。
- 加速度：`carControl.accel`（规划，**本车不实发**）vs `carState.aEgo`（实测）。
- 油门/刹车：本车只有实测踏板（自标定 %），无命令百分比。

## 5. 坐标系与符号
- 车体系：x 前、**y 右**、z 下 → `κ>0` = 右转（+y）。模型的 `position/laneLines` 都在此系。
- 全局链：geodetic ↔ ECEF ↔ NED（定位）。
- 符号在代码中已核实：`latcontrol_torque` 返回 `−output_torque`（"left is positive"）；`carcontroller` 注释 "positive when steering right"。
- κ↔转角（自行车模型）：`δ_wheel≈atan(L·κ)`，`δ_steer≈δ_wheel·steerRatio+offset`。

## 迁移到大巴（结论）
- **可迁移**：轨迹 / `κ(s), θ(s), v(s), a(s)` / Frenet `(s,d)` —— 纯物理量。
- **须重建**：κ→大巴转向（长轴距/铰接/线控 + 力矩或角度缩放）、a→动力/缓速/气刹映射、安全层（panda 等价物）、能力包络（最大横向加速度/最小转弯半径远更紧）。`frenet_view.py` 的可迁移性面板用 `v²κ(s)` 对比大巴包络、超限红色着色。
