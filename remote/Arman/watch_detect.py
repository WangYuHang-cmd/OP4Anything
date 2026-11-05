#!/usr/bin/env python3
"""watch_detect.py — 在 LAPTOP 上实时查看 comma 的检测细节。

用一条常驻 SSH 连接流式读取设备上的 /tmp/objstop_status.json，打印状态机、
距离跟踪、以及**每一个原始检测框**，并对 person 逐项显示行人三个门槛的判定
（居中带 / 够近 / 够低），这样能直接看出"看到人了但没触发"是卡在哪一条。

    python3 watch_detect.py                      # 默认 172.20.10.3
    python3 watch_detect.py --ip 172.20.10.5
    python3 watch_detect.py --all                # 每帧都打（默认只在变化时打）
    python3 watch_detect.py --hz 4               # 拉取频率

门槛取自 objstopd.py 的默认参数；若你用非默认参数启动 objstopd，用同名选项对齐。
"""
import argparse
import json
import subprocess
import sys
import time

# objstopd.py 侧的常量：narrow 1928x1208，SUBSAMPLE=2 -> 检测器看到 964x604
NATIVE_W, NATIVE_H = 1928, 1208
SUB = 2
FRAME_W, FRAME_H = NATIVE_W // SUB, NATIVE_H // SUB

C = {"r": "\033[31m", "g": "\033[32m", "y": "\033[33m", "b": "\033[34m",
     "m": "\033[35m", "c": "\033[36m", "w": "\033[37m", "B": "\033[1m", "0": "\033[0m"}


def col(s, c):
  return f"{C[c]}{s}{C['0']}"


def ped_gate(d, a):
  """复算 objstopd.to_measurements() 里 person 的三个条件，返回逐项结果。"""
  x1, y1, x2, y2 = d["box"]
  cx = 0.5 * (x1 + x2)
  h = y2 - y1
  in_band = a.ped_band_lo * FRAME_W <= cx <= a.ped_band_hi * FRAME_W
  close = h * SUB >= a.ped_min_h
  ahead = y2 >= a.ped_min_bottom * FRAME_H
  # 用针孔模型给个距离感（人按 1.7m 估）
  dist = (2648.0 * 1.7 / (h * SUB)) if h > 0 else None
  return in_band, close, ahead, dist, cx, h


def fmt_dets(dets, a):
  out = []
  for d in dets:
    name = d.get("name", "?")
    conf = d.get("conf", 0)
    box = d.get("box", [0, 0, 0, 0])
    color = d.get("color")
    if name == "person":
      in_band, close, ahead, dist, cx, h = ped_gate(d, a)
      ok = in_band and close and ahead
      marks = (f"{col('居中✓','g') if in_band else col('居中✗','r')} "
               f"{col('够近✓','g') if close else col('够近✗','r')} "
               f"{col('够低✓','g') if ahead else col('够低✗','r')}")
      d_s = f"~{dist:.0f}m" if dist else "?"
      verdict = col("→ 触发", "g") if ok else col("→ 不触发", "y")
      out.append(f"    {col('person','m')} conf={conf:.2f} {d_s} "
                 f"cx={cx:.0f}/{FRAME_W} h={h:.0f}px  {marks}  {verdict}")
    else:
      cs = f" color={color}" if color else ""
      out.append(f"    {name} conf={conf:.2f} box={box}{cs}")
  return out


def snapshot(js, a):
  st = js.get("state")
  reason = js.get("reason") or "-"
  ped = js.get("ped_hold")
  flag = js.get("flag")
  tracks = js.get("tracks") or {}
  dets = js.get("dets") or []

  sc = "g" if st == "DRIVING" else ("r" if ped else "y")
  head = (f"{col(st, sc)}  reason={reason}  "
          f"ped_hold={col('TRUE', 'r') if ped else 'false'}  "
          f"flag={col(str(flag), 'r') if flag else 'None'}  "
          f"→UDP={col('1', 'r') if flag else col('0', 'g')}")
  sub = (f"  v_ego={js.get('v_ego', 0):.1f}m/s  infer={js.get('infer_ms', 0):.0f}ms  "
         f"armed={js.get('armed')}  检测数={len(dets)}")
  tr = []
  for k, v in tracks.items():
    if v is not None:
      tr.append(f"{k}={v:.1f}m" if isinstance(v, (int, float)) else f"{k}={v}")
  if tr:
    sub += "  tracks: " + " ".join(tr)
  lines = [head, sub]
  if js.get("alert"):
    lines.append("  " + col("ALERT: " + js["alert"], "y"))
  lines.append("  " + (js.get("action") or ""))
  lines.extend(fmt_dets(dets, a))
  return "\n".join(lines)


def key(js):
  """判断"有没有变化"的指纹。"""
  return (js.get("state"), js.get("ped_hold"), bool(js.get("flag")),
          tuple(sorted(d.get("name", "") for d in (js.get("dets") or []))))


def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--ip", default="172.20.10.3")
  ap.add_argument("--user", default="comma")
  ap.add_argument("--hz", type=float, default=4.0, help="拉取频率，默认 4")
  ap.add_argument("--all", action="store_true", help="每帧都打印（默认仅变化时）")
  # 与 objstopd.py 对齐的行人门槛
  ap.add_argument("--ped-min-h", type=float, default=90.0)
  ap.add_argument("--ped-band-lo", type=float, default=0.2)
  ap.add_argument("--ped-band-hi", type=float, default=0.8)
  ap.add_argument("--ped-min-bottom", type=float, default=0.45)
  a = ap.parse_args()

  period = 1.0 / max(a.hz, 0.5)
  remote = (f"while true; do cat /tmp/objstop_status.json 2>/dev/null; "
            f"printf '\\n'; sleep {period:.2f}; done")
  cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
         "-o", "ServerAliveInterval=5", f"{a.user}@{a.ip}", remote]

  print(f"连接 {a.user}@{a.ip} …  (Ctrl-C 退出)")
  print(f"行人门槛: 居中带 {a.ped_band_lo}-{a.ped_band_hi}W  最小高度 {a.ped_min_h}px(native)  "
        f"底边 ≥{a.ped_min_bottom}H   [帧 {FRAME_W}x{FRAME_H}]\n")

  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  last = None
  nempty = 0
  try:
    for line in p.stdout:
      line = line.strip()
      if not line:
        nempty += 1
        if nempty % 40 == 0:
          print(col("  … status 文件为空 —— objstopd 可能没在跑", "y"))
        continue
      nempty = 0
      try:
        js = json.loads(line)
      except json.JSONDecodeError:
        continue
      k = key(js)
      if a.all or k != last:
        last = k
        print(f"[{time.strftime('%H:%M:%S')}] " + snapshot(js, a))
  except KeyboardInterrupt:
    pass
  finally:
    p.terminate()
    err = p.stderr.read() if p.stderr else ""
    if err.strip():
      print("\nSSH stderr:", err.strip()[:300], file=sys.stderr)


if __name__ == "__main__":
  main()
