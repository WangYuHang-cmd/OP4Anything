# OPERATIONS — 完整操作手册(comma × laptop,全场景)

> 设备:comma 3X(实验机,sunnypilot 0.9.7.1)· 笔记本:`~/Desktop/Drive/remote/Arman/`
> 每条命令都标注了**在哪台机器上执行**。⚠️ 安全:OP 纵向开启时无原厂 AEB;`--arm`/手动 stop 只在封闭场地;驾驶员是唯一安全网。

---
## 0. 系统总览(现在设备上生效/待命的东西)

| 组件 | 位置 | 作用 |
|---|---|---|
| planner 距离斜坡 v2 | `selfdrive/controls/lib/longitudinal_planner.py` | 读 `/tmp/op_stop_requested`(`d=<m> t=<ts>`)平滑滑行到停止线;空文件=立即停;过期 1s 自动释放 |
| 起步助推 | `selfdrive/car/honda/interface.py` | `startingState=True, startAccel=0.6`,停稳后有力起步 |
| controlsd 屏显钩子 | `selfdrive/controls/controlsd.py` | comma 屏显示 `VISION: RED LIGHT / braking...`(LOWEST 优先级,纯显示) |
| 视觉停车守护 objstopd v2.1 | `/data/objstop/` | 相机→YOLO→距离KF→状态机→停车旗标;shadow 默认 |
| exporter(stopFlag) | `tools/reg_export/exporter.py` | TCP:7700 数据流,含 `stopFlag.stop=0/1` |
| `DisengageOnAccelerator=0` | params | 油门=覆盖放行,不脱开(刹车仍立即脱开) |
| dashcam 模式(**待启用**) | `/data/objstop/enable_dashcam_mode.py` | 无 CAN 时 `touch /data/force_onroad` 强制相机/模型/GPS 运行 |

所有备份:`*.bak_arman*`(见 §9 还原表)。

---
## 1. 网络:三种连法,laptop 侧完全一样

```bash
# laptop——任何网络下第一步:
cd ~/Desktop/Drive/remote/Arman
IP=$(./find_comma.sh)          # 自动找到 comma;失败会打印原因
```
| 连法 | 步骤 |
|---|---|
| **手机热点** | comma 与 laptop 连同一热点(安卓优先,iPhone 可能客户端隔离)→ `find_comma.sh` |
| **网线直连** | comma USB-C→RJ45 适配器→laptop 网口;laptop 一次性:`nmcli con add type ethernet ifname <网口名> con-name comma-share ipv4.method shared && nmcli con up comma-share` → comma 自动获得 10.42.0.x → `find_comma.sh`。适配器不识别(`ssh comma@旧IP 'ip -br link'` 无新接口)→ 回退热点。详见 `ETHERNET_SETUP.md` |
| **实验室 WiFi** | 现网 IP 192.168.1.231 |

---
## 2. 场景 A:Civic,有 CAN(正常控车实验)

### 2.1 上电与自检
1. 车点火 → comma 自动 onroad(屏幕出路面画面)。
2. **laptop**:`python3 experiment.py --ip $IP check`
   全 ✓ 才继续;engage 后 `longActive ✗` → `ssh comma@$IP 'sudo reboot'`,45s 后重试。

### 2.2 甲方 JSON 输出(文件 + UDP,含 "stop":0/1)
```bash
# laptop:
python3 cp_export.py --ip $IP --mode live --out-dir ./cp_out \
        --udp <甲方IP>:<端口>            # UDP 可选;--udp-hz 10 默认
# 产物:./cp_out/track_live.json (甲方格式,顶层 "stop":0/1) + track_live.csv (STÄHLE)
# 心跳应显示:[cp_export] OK -> track_live.{csv,json} segs=N
# 整条路线录制:--mode record → Ctrl-C 时写 route_track.{csv,json}
# 固定原点:--ref-lat 37.7749295 --ref-lon -122.4194155
```
`"stop"` 语义:1=车辆正被命令停车(视觉触发或手动),0=正常行驶/起步。

### 2.3 可视化(laptop,可选,各开一个终端)
```bash
python3 cp_view.py --ip $IP                    # ENU 轨迹图(甲方坐标系)
python3 vision/objstop_view.py --ip $IP        # 检测状态板:三目标 tile + NEXT 动作
```

### 2.4 手动纵向控制(封闭场地)
```bash
# laptop:
python3 experiment.py --ip $IP stop      # ■ 平滑减速停
python3 experiment.py --ip $IP go        # ▶ 清除手动停车
python3 experiment.py --ip $IP release   # ⏩ 强制视觉守护放行(假人场景)
python3 experiment.py --ip $IP status    # 配置+旗标状态
```

### 2.5 视觉停车(先 SHADOW,后 ARM)
```bash
# comma(ssh comma@$IP):
cd /data/objstop && PYTHONPATH=/data/openpilot \
  /usr/local/pyenv/versions/3.11.4/bin/python3 objstopd.py --save-every 0.3
#   shadow:只显示不刹车。laptop 开 objstop_view 看 STATE/tile 是否正确。
#   确认可靠后 Ctrl-C,加 --arm 重启:
  ... objstopd.py --arm --save-every 0.3
# 常用参数:--wait-sec 3  --tl-setback 10  --sign-setback 3  --ped-conf 0.30
#           --onnx-320 yolov8s_320.onnx   (换大模型,2Hz,一般不需要)
```
**行为**:stop sign 停 3s 自动走(标志仍可见也走);红灯等确认绿灯;行人在前方停、离开 1.5s 走。
**卡住时放行**(按方便):①轻点油门(现在=覆盖放行,不脱开)②laptop `release` ③行人真离开。
**comma 屏**会同步显示 `VISION: ...` 状态条。

---
## 3. 场景 B:卡车 / 无 CAN → dashcam 模式(仍输出甲方 JSON)

> 无 CAN 时不可能控车(没有执行器),但**相机检测 + GPS 轨迹 + 甲方 JSON(含 stop 0/1)全部照常输出**。

### 3.1 现状:**已启用,通电即进 dashcam**(2026-08-06 应用并验证)
- `/data/force_onroad` 为持久文件 → **设备一通电就自动 onroad**:相机/模型/GPS 启动,
  **objstopd 自动运行**(manager 托管,shadow),exporter 无 CAN 也照常发流。
- 已实测:无车状态重启 → IsOnroad=1、camerad/modeld/locationd/objstopd/7700 全部在线。
- **回 Civic 正常用车前**:`ssh comma@$IP 'rm /data/force_onroad'`(否则熄火后设备一直
  onroad 录像耗电)。重新进 dashcam:`touch /data/force_onroad`。
- ⚠️ **供电**:强制 onroad 满载功耗高——桌面弱 USB 充电器可能带不动(会掉电断连)。
  卡车上用车载 12V→USB-C 足瓦数电源(≥18W);台架测试用好充电器。

### 3.2 卡车上的完整输出流程(设备侧零操作!)
```bash
# comma:通电即可——objstopd 已自启(shadow),什么都不用敲。
# laptop:
IP=$(./find_comma.sh)
python3 cp_export.py --ip $IP --mode live --out-dir ./cp_out --udp <甲方IP>:<端口>
#    室外等 GPS fix(心跳会提示);室内/无 GPS:加 --local-frame(车体系,非真北)
python3 vision/objstop_view.py --ip $IP        # 可选:看检测状态板
```
**"stop":0/1 语义(dashcam)**:objstopd 即使 shadow 也写"意图旗标"——检测到该停
(stop sign/红灯/行人)→ JSON/UDP 顶层 `"stop":1`,恢复 → `0`。甲方可直接用它驱动
卡车自己的制动。手动强制:`experiment.py stop/go` 照常可用(actuation 旗标优先)。

### 3.3 手动 --arm 与自启实例的关系(仅 Civic 场景需要)
自启实例是 shadow。要手动跑 `--arm`:
```bash
ssh comma@$IP 'touch /data/objstop/manual_mode'   # manager 停掉自启实例
cd /data/objstop && ... objstopd.py --arm ...      # 手动带刹车运行
ssh comma@$IP 'rm /data/objstop/manual_mode'       # 结束后恢复自启
```
**"stop":0/1 在 dashcam 下的语义**:视觉系统"本会"命令停车(检到 stop sign/红灯/行人)→ 1;甲方可用它驱动他们卡车自己的制动。
**诚实的限制**:①无 vEgo → 距离 KF 无航位推算,估距精度降(检测本身不受影响);②modelV2 轨迹用的是 Civic 存的相机标定,装到卡车挡风玻璃角度不同,轨迹几何有偏差——卡车上建议以 **GPS record 模式**产 route 或以视觉 stop 旗标为主要交付;③dashcam 会录像,`/data/media` 会涨,长时间用后注意清理。

---
## 4. comma 设备速查

```bash
ssh comma@$IP
# 进程:ps aux | grep -E "objstop|reg_export|modeld"
# 视觉守护日志:直接看 objstopd 前台输出;状态:cat /tmp/objstop_status.json | python3 -m json.tool
# 停车旗标:ls -l /tmp/op_stop_requested(内容 d=.. t=.. src=v)
# 重启 exporter:pkill -f '[t]ools.reg_export'(manager 自动拉起)
# 重启一切:sudo reboot(所有 /tmp 旗标自动清空)
# 磁盘:df -h /data;录像在 /data/media/0/realdata/
```

## 5. laptop 速查

```bash
cd ~/Desktop/Drive/remote/Arman
IP=$(./find_comma.sh)
python3 experiment.py --ip $IP check|stop|go|release|status
python3 cp_export.py --ip $IP --mode live|record [--udp H:P] [--ref-lat .. --ref-lon ..] [--local-frame]
python3 cp_view.py --ip $IP
python3 vision/objstop_view.py --ip $IP
```

## 6. 甲方对接
- UDP:每包一条 UTF-8 JSON,≤10Hz,格式=`{ref:{latitude,longitude}, "stop":0|1, segments:[{start,end,velocity,radius,direction}]}`;代码片段与说明:`udp_snippet.py`(英文,可直接发)。
- 单位:segments velocity=m/s;STÄHLE csv velocity=kph。末段 velocity=0.0=终点停车。

## 7. 故障排查
| 症状 | 查 | 解 |
|---|---|---|
| find_comma 找不到 | 两端是否同网;iPhone 隔离 | 换安卓热点/网线;`ping` 试 |
| check 无流数据 | 车没 onroad / dashcam 未 touch | 点火;或 `touch /data/force_onroad` |
| cp_export 一直 waiting GPS | 室内无 fix | 室外等 1-2min;或 `--local-frame` |
| engage 后 longActive ✗ | CarParams 未按 OP-long 初始化 | `sudo reboot` 后重新 engage |
| 视觉停车不停 | shadow 未 --arm;或未 engage | 加 `--arm`;确认 LONG ● |
| 停住不走 | 看 objstop_view 的 STATE/NEXT | 行人挡→油门轻点/`release`;红灯→等绿或 `release` |
| comma 屏无 VISION 条 | objstopd 没跑 / 未 onroad | 启动 objstopd;屏条 2s 过期属正常 |
| UDP 甲方收不到 | 防火墙/IP 端口 | 先 `nc -lu <端口>` 本地验证;确认路由 |

## 8. 每次实验后
```bash
# comma:确保守护退出(Ctrl-C 会自动清旗标);dashcam 模式记得 rm /data/force_onroad
# laptop:cp_out/ 的 json/csv 即交付物,拷走存档
```

## 9. 还原总表(全部改动一键回退)
```bash
ssh comma@$IP
cd /data/openpilot
cp selfdrive/controls/lib/longitudinal_planner.py.bak_arman2 selfdrive/controls/lib/longitudinal_planner.py   # 撤距离斜坡(回v1用.bak_arman)
cp selfdrive/car/honda/interface.py.bak_arman2 selfdrive/car/honda/interface.py                               # 撤起步助推
cp selfdrive/controls/controlsd.py.bak_arman_ui selfdrive/controls/controlsd.py                               # 撤屏显
cp system/hardware/hardwared.py.bak_arman system/hardware/hardwared.py 2>/dev/null                            # 撤 dashcam 钩子
cp tools/reg_export/exporter.py.bak_arman_nocan tools/reg_export/exporter.py 2>/dev/null                      # 撤 exporter 无CAN 改动
python3 -c "from openpilot.common.params import Params; p=Params(); p.remove('ExperimentalLongitudinalEnabled'); p.put_bool('DisengageOnAccelerator', True)"
rm -f /data/force_onroad; sudo reboot     # → 完全回到原厂 ACC + 雷达 + AEB
```
