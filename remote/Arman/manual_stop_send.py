#!/usr/bin/env python3
"""manual_stop_send.py — 兜底发送器，直接在 LAPTOP 上跑。

绕开 comma 和 objstopd，由笔记本自己向接收端发 "0"/"1"，协议和设备上的
stop_udp.py 完全一致：每个数据报载荷是单个 ASCII 字节 b"0" 或 b"1"。

    python3 manual_stop_send.py                    # -> 172.20.10.3:5005 持续发 "1" @10Hz
    python3 manual_stop_send.py --value 0          # 持续发 "0"
    python3 manual_stop_send.py 172.20.10.7 5005   # 换目标
    python3 manual_stop_send.py --hz 20 --duration 30
    python3 manual_stop_send.py --pulse 3          # 发 3s "1" 后自动转 "0" 并保持

终端是 tty 时支持热键（无需回车）：
    1 = 切到 "1"    0 = 切到 "0"    空格 = 翻转    q / Ctrl-C = 退出
"""
import argparse
import contextlib
import os
import select
import socket
import sys
import termios
import time
import tty


@contextlib.contextmanager
def raw_stdin():
  """tty 下切到 raw 模式读单键；非 tty（管道/nohup）则原样让出。"""
  if not sys.stdin.isatty():
    yield False
    return
  fd = sys.stdin.fileno()
  saved = termios.tcgetattr(fd)
  try:
    tty.setcbreak(fd)
    yield True
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def read_key():
  if select.select([sys.stdin], [], [], 0)[0]:
    return sys.stdin.read(1)
  return None


def main():
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("host", nargs="?", default="172.20.10.2")
  ap.add_argument("port", nargs="?", type=int, default=5005)
  ap.add_argument("--hz", type=float, default=10.0, help="发送频率，默认 10")
  ap.add_argument("--value", choices=["0", "1"], default="1", help="初始载荷，默认 1")
  ap.add_argument("--duration", type=float, default=0.0, help="发满 N 秒后退出，0=一直发")
  ap.add_argument("--pulse", type=float, default=0.0,
                  help="先发 N 秒 '1'，然后自动转 '0' 继续发（不退出）")
  a = ap.parse_args()

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  dst = (a.host, a.port)
  period = 1.0 / max(a.hz, 0.01)
  val = a.value.encode()

  print(f"[manual] -> {a.host}:{a.port}  {a.hz:g} Hz  起始载荷 '{a.value}'")
  if a.pulse:
    print(f"[manual] pulse: {a.pulse:g}s 后自动转 '0'")
  print("[manual] 热键: 1=发1  0=发0  空格=翻转  q=退出\n")

  t0 = time.monotonic()
  sent = 0
  errs = 0
  last_report = t0
  pulsed = False

  try:
    with raw_stdin() as interactive:
      while True:
        now = time.monotonic()
        if a.duration and (now - t0) >= a.duration:
          break
        if a.pulse and not pulsed and (now - t0) >= a.pulse:
          val = b"0"
          pulsed = True
          print(f"\n[manual] pulse 结束，转为 '0'")

        if interactive:
          k = read_key()
          if k in ("q", "\x03"):
            break
          if k == "1":
            val = b"1"
          elif k == "0":
            val = b"0"
          elif k == " ":
            val = b"0" if val == b"1" else b"1"

        try:
          sock.sendto(val, dst)
          sent += 1
        except OSError as e:
          errs += 1
          if errs <= 3:
            print(f"\n[manual] 发送失败: {e}")

        if now - last_report >= 1.0:
          last_report = now
          el = now - t0
          sys.stdout.write(f"\r[manual] {el:6.1f}s  载荷='{val.decode()}'  "
                           f"已发 {sent} 包  失败 {errs}   ")
          sys.stdout.flush()

        time.sleep(period)
  except KeyboardInterrupt:
    pass

  el = time.monotonic() - t0
  print(f"\n[manual] 结束：{el:.1f}s，共发 {sent} 包，失败 {errs}")
  if errs and errs == sent:
    print("[manual] 全部失败 —— 检查目标是否可达（ping 一下）")


if __name__ == "__main__":
  main()
