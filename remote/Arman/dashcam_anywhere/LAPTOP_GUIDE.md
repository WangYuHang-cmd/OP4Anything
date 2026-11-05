# comma 机器人 dashcam：laptop 操作指南

适用设备：comma 3X，dongle `<DONGLE_ID>`（家里网络下的 IP 是 192.168.1.231），运行 openpilot v0.11.1 + dashcam-anywhere 补丁（commit `8acb496`）。
设备行为：**通电即录像，永不控车，用 GPS/视觉速度自动标定，标定跨重启保留**。原理和改动说明见同目录 `README.md`。

---

## 0. 一页速查

```bash
cd ~/Desktop/Drive/remote/Arman/dashcam_anywhere      # 路径按 laptop 上的实际位置改
export COMMA_IP=192.168.43.1                          # 用 comma 热点时；其他网络见 §3

./dashcam.sh status                # 一屏状态（每次实验前看一次）
./dashcam.sh reset-calib           # 换了机器人或支架 → 从零重新标定
./dashcam.sh poweroff              # 正常关机（断电前执行）
./dashcam.sh disable / enable      # 关闭 / 开启 dashcam 模式（会重启）
./dashcam.sh restore-civic         # 关闭后、装回 Civic 前，恢复 Civic 标定
```
- 改变设备状态的命令会先显示 dongle id 并要求输入 `y` 确认。加 `-y` 可跳过确认，例如 `./dashcam.sh -y poweroff`。
- **标定**：直线行驶，GPS 速度 **≥ 10 km/h**，累计约 1–2 分钟，屏幕上的 "Calibrating x%" 会消失。

---

## 1. 一次性准备（只做一次）

### 1.1 把工具拷到 laptop
在**桌面机**上执行（把 `<laptop>` 换成 laptop 的地址，以前用的是 tailscale 的 `<LAPTOP_USER>@<TAILSCALE_IP>`）：
```bash
cd ~/Desktop/Drive/openpilot/Arman
rsync -av --exclude replay_rlogs dashcam_anywhere find_comma.sh ETHERNET_SETUP.md <laptop>:~/Desktop/Drive/remote/Arman/
```
`replay_rlogs/` 有 206 MB，只用于验证标定算法，laptop 上不需要。
没有网络时，用 U 盘拷整个 `dashcam_anywhere/` 文件夹即可。

### 1.2 SSH 钥匙
> 已核对（2026-10-03）：laptop `<LAPTOP_HOSTNAME>`（192.168.1.112）上的 `~/.ssh/id_rsa`（指纹 `<SSH_KEY_FINGERPRINT>`）就在下面这个 GitHub 账号里，**可以直接登录 comma，不需要拷钥匙**。下面的步骤只在换了电脑时才用得到。

设备只接受 GitHub 账号 **wangyuhang-cmd** 的公钥。桌面机上能用的是 `~/.ssh/id_rsa`。laptop 上先测试：
```bash
ssh -o BatchMode=yes comma@<设备IP> 'cat /data/params/d/DongleId'    # 应输出 <DONGLE_ID>
```
如果提示 `Permission denied (publickey)`，在**桌面机**上把钥匙拷过去（改名，避免覆盖 laptop 自己的钥匙）：
```bash
scp ~/.ssh/id_rsa <laptop>:~/.ssh/id_rsa_comma
```
然后在 **laptop** 上执行：
```bash
chmod 600 ~/.ssh/id_rsa_comma
cat >> ~/.ssh/config <<'EOF'
Host 192.168.*.* 10.42.*.* 172.20.*.*
  User comma
  IdentityFile ~/.ssh/id_rsa_comma
  StrictHostKeyChecking accept-new
EOF
```

### 1.3 laptop 需要的软件
- `ssh`、`rsync`（必需）；
- `nmap`（可选，`find_comma.sh` 扫描更快）；
- `ffmpeg`（可选，用来把录像转成 mp4）。

```bash
sudo apt install -y rsync nmap ffmpeg     # Ubuntu
```

---

## 2. 装到机器人上

### 2.1 机械安装（决定标定能否成功）
- **居中、朝正前方**，相机能看到前方地面和路面。
- 角度范围：俯仰 −5.2°（朝上）~ +9.7°（朝下），偏航 ±4°，**不能侧倾**（左右要水平）。
- 支架要牢固、不晃动。振动和晃动会让标定变差。
- 镜头前不要有遮挡物或反光；有挡风玻璃时贴紧玻璃。
- 超出角度范围时照样录像，但屏幕会显示 "Calibration Invalid"，模型输出不可用。

### 2.2 供电
- **推荐 12 V**（经 harness box 或 OBD-C 线输入），电源 **≥ 18 W**。
- 5 V USB-C 也能跑，但满载时余量只有约 1 V，电压一掉到 4 V 以下设备就会被强制关机。
- **不要接任何 CAN 线**（机器人上没有车辆 CAN，接到其他速率的总线上可能干扰总线）。
- 设备没有电池：断电即关机。正常收工请先执行 `./dashcam.sh poweroff`，等屏幕熄灭后再断电，否则最后约 1 分钟的录像可能损坏。
- **散热**：台架上（室内、无风）实测最高 84 °C，风扇 87%。高于 107 °C 会停止录像，开机时高于 75 °C 不会开始录像。机器人上要保证通风，避免暴晒。

### 2.3 上电后会发生什么
1. 约 30–60 s 开机，屏幕进入路面画面（onroad），**自动开始录像**，不需要点火，也不需要任何操作。
2. 底部提示 **"Dashcam Mode"**；未标定时显示 **"Calibrating: x% / Drive Above 9 km/h"**。
3. 标定完成后只剩 "Dashcam Mode"。

---

## 3. 现场让 laptop 连上设备（选一种）

| 方式 | 设备侧 | laptop 侧 | 设备 IP |
|---|---|---|---|
| **A. comma 热点**（不需要任何其他设备） | **每次开机后**在屏幕上点左侧栏的齿轮 → Settings → **Network** → 打开 **Enable Tethering**。热点设置不会跨重启保留。 | 连接 WiFi `weedle…`（如 `weedle-<DONGLE_ID_PREFIX>`），默认密码 `swagswagcomma`（可在 Tethering Password 修改） | **192.168.43.1** |
| **B. 手机热点 / 便携路由器**（推荐，长期最省事） | 第一次在屏幕上 Settings → Network 选择该热点并输入密码，之后设备开机会自动连接 | 连接同一个热点 | `../find_comma.sh` 自动查找，或看手机热点的已连接设备列表 |
| **C. 实验室 WiFi**（设备已保存 `<LAB_WIFI_SSID>`） | 在信号范围内会自动连接 | 连接同一个 WiFi | 192.168.1.231（DHCP 分配，可能会变） |
| **D. USB-C 网卡（有线）** | 见 `../ETHERNET_SETUP.md` | 同左 | 见该文档 |

注意：
- Settings 页面 10 s 无操作会自动回到路面画面，要连续操作。
- 设定 IP 并确认连到的是这台设备：
  ```bash
  export COMMA_IP=192.168.43.1        # 换成实际 IP
  ssh comma@$COMMA_IP 'cat /data/params/d/DongleId'     # 必须是 <DONGLE_ID>
  ```
  局域网里还有另一台 comma（Mazda CX-3 那台），**一定要核对 dongle id**。

---

## 4. 每次实验的标准流程

1. **上电**：等屏幕出现路面画面（约 1 分钟）。
2. **连网**：按 §3 连上，设好 `COMMA_IP`。
3. **检查**：`./dashcam.sh status`，对照 §5 的"正常值"逐项看。
4. **换机器人或换支架时**：`./dashcam.sh reset-calib`，屏幕回到 "Calibrating: 0%"。
   - 同一台机器人、支架没动过：**不要** reset，标定会保留。
5. **标定行驶**：在开阔平坦的地方**直线**行驶，速度 ≥ 10 km/h（GPS），尽量匀速，少转弯，少急加速和急刹。
   - 每完成约 5 s 有效行驶（一块），进度约 +20%，并自动保存，断电不会丢。
   - 约 25 s 有效行驶后显示 calibrated（低速时实际要 1–2 分钟）；继续行驶约 4 分钟会更稳。
   - 用 `./dashcam.sh status` 或看屏幕确认 `status=calibrated`。
6. **正式实验**：一直在录像，不需要任何操作。
7. **收工**：`./dashcam.sh poweroff`，等屏幕熄灭后断电。
8. **下载数据**：见 §7。设备磁盘大约只能存最近 5.5 小时的录像，旧的会被自动删除，**要及时下载**。

---

## 5. `status` 输出逐项说明（正常值）

```
== dashcam-anywhere
flag /data/force_onroad: present   calib marker: present   pending reset: no   DisableUpdates: True
this boot: CarParams brand=mock passive=True safetyConfigs=['noOutput']
IsOnroad: True
== panda
ignitionLine=True safetyModel=noOutput controlsAllowed=False safetyTxBlocked=0 txCnt=[0, 0, 0] fwdCnt=[0, 0, 0] harness=notConnected
sendcan messages in 3 s: 0
== calibration
status=calibrated calPerc=100% validBlocks=50 valid=True
pitch +x.xx deg (+ = pointing down)  yaw +x.xx deg (+ = pointing left)  height x.xxx m  spread ...
== speed used for calibration
GPS: hasFix=True speed=.. km/h acc=0.xx m/s age=0.x s ...
vision: .. km/h
vision/GPS speed ratio: 1.0x
source: GPS
== device
thermalStatus=ok maxTempC=.. fan=..% freeSpace=..% started=True
processes that should run but are down: none
latest segment: 000000xx--xxxxxxxxxx--N
```
| 项 | 正常值 | 不正常时 |
|---|---|---|
| `flag` | present | absent 表示 dashcam 模式没开，执行 `./dashcam.sh enable` |
| `brand / passive / safetyConfigs` | mock / True / ['noOutput'] | 其他值：立即 `poweroff`，把 status 输出发给我 |
| `IsOnroad`、`started` | True | False：看温度（开机时高于 75 °C 不会开录）；1–2 分钟后仍是 False 就重启 |
| `safetyModel` | noOutput | 刚开机几秒内可能是 elm327，之后应变为 noOutput |
| `txCnt / fwdCnt` | 全为 0 | 不为 0 说明有 CAN 发送：**马上断电**并检查是否接了 CAN 线 |
| `status`（标定） | 实验时应为 calibrated | uncalibrated：继续标定行驶；`invalid`：安装角度超限，调整支架后 reset-calib；`recalibrating`：检测到支架变动，正在重新学 |
| `pitch / yaw` | 稳定，与安装大致吻合 | 每次重启数值都差很多：支架在松动 |
| `GPS hasFix` | 室外为 True | 离线冷启动后首次定位要 1–2 分钟；室内没有 GPS，此时用视觉速度 |
| `vision/GPS ratio` | 约 0.9–1.1 | 偏离很大：相机很低时视觉速度有尺度偏差，记下来告诉我（标定时 GPS 优先，影响不大） |
| `thermalStatus` | ok/yellow | red/danger：要散热，否则会停录 |
| `processes ... down` | none | 偶尔出现会在约 1 s 内自动重启；持续出现就重启设备 |
| `latest segment` | 每分钟加 1 | 不增长说明没在录像，重启设备 |

---

## 6. 标定详解与排查

**采样条件**（全部满足的那一帧才计入）：
- 速度 > 9 km/h。有 GPS fix 时 GPS 速度和视觉速度都要大于 9 km/h；没有 GPS 时只看视觉速度。
- 几乎直线：允许的偏航率随速度降低，低速时转向要更少。
- 视觉位姿足够确定。

| 现象 | 原因 / 处理 |
|---|---|
| 一直 0%，不动 | 车速不到 9 km/h（status 里看 GPS 和视觉速度，**按 10 km/h 以上开**）；一直在转弯；相机被挡 |
| 进度时快时慢 | 正常，只有直线、匀速的片段才计入 |
| 断电后进度还在 | 正常：每完成一块就保存一次 |
| `Calibration Invalid` | 安装角度超出范围（俯仰 −5.2°~+9.7°，偏航 ±4°），调整后执行 reset-calib |
| `Recalibrating` | 自动检测到支架变动（偏航变化 >2° 或俯仰变化 >4°），会自动重新学 |
| 换车或换支架之后 | **一定要** `./dashcam.sh reset-calib`，否则会先沿用旧标定，要很久才能被新数据冲掉 |

屏幕上 Settings → Device → Reset Calibration 的效果与 `reset-calib` 相同，请在机器人静止时操作。

---

## 7. 下载录像与日志

**数据位置**：`/data/media/0/realdata/<route>--<段号>/`，每段 1 分钟。route 名形如 `00000066--3f2a9c1b7e`，每次开机生成一个新 route。

| 文件 | 内容 | 每分钟大小 |
|---|---|---|
| `fcamera.hevc` | 前向窄角路面相机（高清） | ~75 MB |
| `ecamera.hevc` | 前向广角相机 | ~75 MB |
| `dcamera.hevc` | 车内（驾驶员）相机 | ~75 MB |
| `qcamera.ts` | 低清预览视频（可直接播放） | ~1 MB |
| `rlog.zst` | 完整日志：GPS、IMU、模型输出、标定等 | ~10 MB |
| `qlog.zst` | 精简日志 | ~0.2 MB |

文件旁边有 `*.lock` 表示这一段正在写，下载时可以忽略。

```bash
# 列出设备上的 route 和段
ssh comma@$COMMA_IP 'ls /data/media/0/realdata | grep -- -- | sed "s/--[0-9]*$//" | sort | uniq -c'

# 下载整条 route（所有段）
ROUTE=00000066--3f2a9c1b7e
mkdir -p ~/robot_data && rsync -av --progress "comma@$COMMA_IP:/data/media/0/realdata/${ROUTE}--*" ~/robot_data/

# 只下载预览视频和精简日志（很快）
rsync -avm --include='*/' --include='qcamera.ts' --include='qlog.zst' --exclude='*' \
  comma@$COMMA_IP:/data/media/0/realdata/ ~/robot_data/

# 把 hevc 转成 mp4（无损封装，20 fps）
ffmpeg -r 20 -i ~/robot_data/${ROUTE}--0/fcamera.hevc -c copy ~/robot_data/${ROUTE}--0_fcamera.mp4
```
- **传输速度**：WiFi 热点约 5–10 MB/s，1 小时的完整录像约 14 GB。大量下载请用有线（§3 D），或者只下需要的段。
- **时间戳**：设备没有 RTC 电池，离线开机后要等 GPS 定位才校正系统时间（约 1–2 分钟）。在这之前，文件和日志里的墙钟时间是错的（会显示 2026-03-24 左右）。需要和其他设备对时时，以 rlog 里的 GPS 时间为准。
- 有网络时，设备会照常自动把 qlog/qcamera 上传到 comma connect。

---

## 8. 关机与断电

- 正常关机：`./dashcam.sh poweroff`（onroad 时屏幕上没有关机按钮）。
- 重启：`ssh comma@$COMMA_IP 'sudo reboot'`，或在屏幕上 Settings → Device → Reboot。
- 直接断电也可以，但最后约 1 分钟的录像可能不完整。
- 设备在通电期间一直录像，**不会自动关机**。机器人的电池保护要靠机器人自己的开关或 BMS。

---

## 9. 常见故障

| 现象 | 处理 |
|---|---|
| 屏幕一直不出路面画面 | 等 2 分钟；看温度（开机时高于 75 °C 不开录，散热后会自动开始）；`status` 看 started 和 processes |
| `ssh: Permission denied (publickey)` | 钥匙问题，见 §1.2 |
| `find_comma.sh` 找不到 | 确认 laptop 和设备在同一网络；用 comma 热点时 IP 固定为 192.168.43.1 |
| 找到的是另一台 comma | 核对 dongle id（应为 `<DONGLE_ID>`），用 `COMMA_IP` 指定 IP |
| 屏幕提示 Calibration Invalid | 安装角度超限，见 §2.1 和 §6 |
| 磁盘满 | 不会满：旧的录像会被自动删除。要保留的数据请及时下载 |
| 录像中断或段号不增长 | `status` 看 processes down；崩溃的进程约 1 s 内自动重启；仍不行就重启设备 |
| 异常且查不出原因 | 先 `./dashcam.sh status > status.txt`，再执行 `ssh comma@$COMMA_IP 'tail -n 300 /data/log/swaglog.*' > swaglog.txt`，把两个文件发给我 |

---

## 10. 装回 Civic（恢复正常 openpilot）

```bash
./dashcam.sh disable           # 关闭 dashcam 模式并重启；之后需要真实点火才会 onroad
./dashcam.sh restore-civic     # 设备重启完成、处于 offroad 时执行：恢复 Civic 的标定和学习参数
```
- 不执行 restore-civic 也可以：机器人的标定会被自动清空，Civic 会从零重新标定（以 >24 km/h 直线行驶几分钟）。
- 之后再装回机器人：`./dashcam.sh enable`。首次进入 dashcam 模式时，Civic 的标定会自动清空，不会带到机器人上。
- 完全还原成原厂 openpilot（含恢复自动更新）：见 `README.md` 的"回滚"一节。

---

## 11. 文件一览

| 文件 | 用途 |
|---|---|
| `dashcam.sh` | laptop 端控制脚本（本指南的主要工具） |
| `status.py` | 设备端状态脚本（位于设备 `/data/dashcam_anywhere/`，由 `dashcam.sh status` 调用） |
| `README.md` | 补丁原理、验证记录、完全回滚步骤 |
| `dashcam_anywhere.patch` | 补丁本体（设备重刷后用它重新安装） |
| `replay_calib.py` + `replay_rlogs/` | 标定算法回放验证（只在桌面机上用） |
| `../find_comma.sh`、`../ETHERNET_SETUP.md` | 自动找设备 IP、有线连接方法 |
