# dashcam-anywhere：comma 3X 装到任意小车/机器人上当 dashcam，并自动标定

设备：`comma@192.168.1.231`（comma 3X，dongle `<DONGLE_ID>`），openpilot v0.11.1 release-tizi + 本补丁。
- 补丁提交：本地 release-tizi 分支的 commit `8acb496`，tag `dashcam-anywhere-v1`，父提交为原厂 `70e1574`。
- 补丁文件：本目录下的 `dashcam_anywhere.patch`。

## 它做了什么

文件 `/data/force_onroad` 存在时（**开机时读一次，改动后必须重启**），设备变为：

| 功能 | 做法 |
|---|---|
| 通电即录像，不需要点火/harness/CAN | pandad 带上 `STARTED=1` 伪造点火；hardwared 强制 ignition；UI 始终显示路面画面 |
| 跳过其他启动检查 | 跳过更新/联网（同时设了 `DisableUpdates=1`）、条款、训练、注册、excessive actuation 检查。**温度和磁盘检查保留** |
| 永不控车 | 不做指纹识别，也不发 VIN/FW 查询，直接用 MOCK 车（passive）。<br>card 互锁：只允许写 noOutput 的 CarParams。<br>pandad 把 panda 设为 noOutput，并用 `FAKESEND=1` 丢弃所有 sendcan |
| 无 CAN 自动标定 pitch/yaw/height | 速度源：GPS（fix 良好时）或视觉里程计。<br>门槛 **9 km/h**、直线、偏航率门槛随速度缩放、等权块平均。<br>相机高度不确定时不学高度。<br>每完成一块（约 5 s 有效样本）就保存一次，断电不丢进度 |
| 标定跨重启保留 + 手动重置 | `dashcam.sh reset-calib`（或 `touch /data/reset_calib`），约 1 s 内从零开始；也可以用 UI 的 Settings → Device → Reset Calibration |
| Civic 与 dashcam 模式互不污染 | 进入或退出 dashcam 模式时，标定都会自动清空（由 marker 文件 `/data/calib_from_dashcam` 控制） |
| 无人值守 | 录像、标定、温控相关进程崩溃后约 1 s 内自动重启 |
| 屏幕 | 显示 "Dashcam Mode"；标定中显示 "Calibrating: x% / Drive Above 9 km/h" |

`/data/force_onroad` 不存在时，行为与原厂完全一致。唯一例外是标定的 marker 和 reset 旗标。

## 日常使用（在桌面机或 laptop 上执行）

**详细的 laptop 现场操作指南见 [`LAPTOP_GUIDE.md`](LAPTOP_GUIDE.md)**，包括联网、标定、下载数据和故障排查。


```bash
cd ~/Desktop/Drive/openpilot/Arman/dashcam_anywhere
./dashcam.sh status       192.168.1.231   # 一屏状态：onroad、panda 安全模式、标定、速度源、温度、磁盘
./dashcam.sh reset-calib  192.168.1.231   # 换了车或支架后，从零重新标定
./dashcam.sh poweroff     192.168.1.231   # 正常关机（onroad 时 UI 没有关机按钮）
./dashcam.sh enable|disable 192.168.1.231 # 开/关此模式（会重启）
./dashcam.sh restore-civic 192.168.1.231  # 关闭后在 offroad 状态下执行：恢复 Civic 的标定和学习参数
```
- 不填 IP 时，会读取 `$COMMA_IP`，再不行就调用 `../find_comma.sh` 自动发现。
- ⚠ 局域网里可能有多台 comma，所以改状态的命令会先显示 dongle id，等你确认后再执行。

## 换到新车/机器人时的标定步骤

1. **安装**：居中、朝正前方。俯仰 −5.2°（朝上）~ +9.7°（朝下），偏航 ±4°，不能侧倾。
2. **供电**：建议 12 V（OBD-C/harness box），电源 ≥18 W。5 V USB 在满载时可能掉电，输入低于 4 V 会被系统硬关机。**不要接 CAN 线**。
3. **重置标定**：`./dashcam.sh reset-calib <IP>`，或在屏幕上 Settings → Device → Reset Calibration（请在静止时操作）。
4. **开始标定**：直线行驶，GPS 车速 **≥ 9.5–10 km/h**（GPS 读数比实际偏低约 3%）。
   - 累计约 25 s 有效样本后显示 calibrated（回放实测：低速约 1–2 分钟）；
   - 累计约 4 分钟样本填满 50 块的窗口。
   - 室外有 GPS 时速度源用 GPS；没有 GPS 时用视觉速度。离线冷启动后首次 GPS 定位需要 1–2 分钟。
5. **确认**：用 `./dashcam.sh status <IP>` 查看 `status=calibrated`，以及 pitch/yaw/height 是否合理。

## 验证记录（2026-10-03）

- **单元测试**：`selfdrive/locationd/test/test_calibrationd.py` 共 15 项（原厂 7 项 + dashcam 8 项）全部通过。
- **回放验证**：用 19 段 Civic rlog 跑 `replay_calib.py`，数据保存在 `replay_rlogs/`。

  | 子集 | dashcam 结果 (pitch / yaw) | 与原厂 CAN 逻辑参考 [3.37°, 0.65°] 之差 | 误触发重新标定 | 最大 yaw spread |
  |---|---|---|---|---|
  | CAN < 6.7 m/s | [3.44°, 0.64°] | 0.07° / 0.02° | 0 | 0.81° |
  | CAN < 3.1 m/s（机器人速度段） | [3.51°, 0.62°] | 0.13° / 0.03° | 0 | 0.68° |

  不加两项低速修正（等权块平均、偏航门槛缩放）时，机器人速度段的 yaw 会偏到 1.02°。

- **台架验收**（2026-10-03，USB 供电，不接车，室内）：
  - 开机 55 s 内 onroad，开始录 route（fcamera/ecamera/dcamera/qcamera/rlog/qlog）；
  - CarParams：brand=mock、passive、safetyConfigs=[noOutput]；
  - panda：ignitionLine=True、safetyModel=noOutput、controlsAllowed=False、safetyTxBlocked=0，三路 CAN 的 tx/fwd 计数都为 0，没有 sendcan；
  - 屏幕显示 "Calibrating: 0% / Drive Above 9 km/h"；Civic 标定已被 marker 逻辑自动清空；
  - `pkill -9 encoderd` 后约 1 s 被 manager 拉起，录像继续；
  - `touch /data/reset_calib` 后 1 s 内被消费，cloudlog 有记录；
  - 单元测试在开关打开时也是 15/15 通过。
  - 注意：在室内台架上静止时，视觉速度的噪声为中位数 0.74 m/s、最大 1.5 m/s，低于 2.5 m/s 的门槛，所以不会误采样。没有 GPS 时（室内）只能靠视觉速度，安装时尽量让相机看到正常的路面场景。

重新跑回放：
```bash
ssh comma@IP 'cd /data/openpilot && PYTHONPATH=/data/openpilot /usr/local/venv/bin/python3 -B /data/dashcam_anywhere/replay_calib.py --root /data/dashcam_anywhere/replay_rlogs'
```
需要先把 `replay_rlogs/` 复制到设备的 `/data/dashcam_anywhere/replay_rlogs`。

## 已知限制

- 模型是在汽车相机高度上训练的。小机器人的相机很低，视觉速度和高度可能有尺度偏差；pitch/yaw 来自运动方向，与尺度无关。用 `status` 看 vision/GPS 速度比值可以评估这一点。
- 只要有电就一直录像，没有自动关机，也没有低压保护，电池要靠外部开关或 BMS 保护。断电时最后一段可能被截断。
- 温度保护（原厂阈值）：开机时高于 75°C 不开录；onroad 时高于 107°C 退出录像，降到 88°C 以下恢复。
- RTC 没有电池：离线时系统时间要等 GPS 定位后才正确；route 名按计数器编号，不受影响。
- 存储：约 230 MB/min（三路摄像头），约 5.5 h 环形缓存，最旧的记录会被自动删除。
- 录音（RecordAudio）、车内摄像头、驾驶员监控照旧开启；有网络时按原厂行为上传 qlog/qcamera。
- HUD 车速显示 0（MOCK 车没有车速）。

## 回滚

- **软回滚**：`./dashcam.sh disable <IP>`。补丁失效，设备需要真实点火才会 onroad。
  - 回 Civic 时执行 `./dashcam.sh restore-civic <IP>`，或直接开车，让 Civic 从零重新标定。
- **完全回滚**（在设备上执行）：
  ```bash
  rm -f /data/force_onroad /data/reset_calib /data/calib_from_dashcam   # 原厂代码不认识这两个文件，留下 marker 将来会误删 Civic 标定
  cd /data/openpilot && git reset --hard 70e157462304e5ce7d03ffbec6cb7f45bf347bb7
  PYTHONPATH=/data/openpilot /usr/local/venv/bin/python3 -c "from openpilot.common.params import Params; Params().remove('DisableUpdates')"
  sudo reboot
  ```
  之后更新器会自动重建 staging，设备回到 release-tizi 的正常更新。
- 备份位置：设备上的 `/data/dashcam_backup/20261003/`，内含 Civic 的 CalibrationParams、CarParams*、LiveParametersV2、LiveDelay、LiveTorqueParameters 和 git rev。
