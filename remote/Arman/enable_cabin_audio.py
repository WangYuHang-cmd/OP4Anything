#!/usr/bin/env python3
"""enable_cabin_audio.py — record in-cabin microphone audio. RUN ON DEVICE after review.

    scp enable_cabin_audio.py comma@<ip>:/data/objstop/
    ssh comma@<ip> 'python3 /data/objstop/enable_cabin_audio.py'
    ssh comma@<ip> 'pkill -f "[s]ystem.micd"'      # manager restarts it with the patch

    touch /data/record_audio     # <- record  (this script creates it)
    rm    /data/record_audio     # <- stop recording, micd otherwise unchanged

Why a patch and not a new daemon: micd already holds the only PortAudio/ALSA capture
stream on the device (sdm845-tavil-snd-card), and capture devices generally can't be
opened twice. Patching micd keeps it to one stream.

What it changes: system/micd.py (backup .bak_arman_audio)
micd computes a sound pressure level from the mic and then throws the samples away
(`self.measurements = self.measurements[FFT_SAMPLES:]`). This keeps a copy of the raw
samples and writes them to the segment loggerd is currently filling, so the existing
loggerd deleter cleans audio up together with the video — important, /data runs ~90% full.

Output: <segment>/cabin_audio_44100_mono_s16le.raw   (headerless PCM, ~5 MB/min)
Headerless on purpose: a WAV header is only finalized on close, so pulling power mid-drive
would leave a corrupt file. Convert on the laptop:
    ffmpeg -f s16le -ar 44100 -ac 1 -i cabin_audio_44100_mono_s16le.raw cabin_audio.wav

The SPL path is untouched, and every added step is wrapped so an audio failure can never
take micd down.

Revert: cp system/micd.py.bak_arman_audio system/micd.py  (then restart micd)
"""
import py_compile
import shutil
import sys

PATH = "/data/openpilot/system/micd.py"
MARKER = "bak_arman_audio"

IMPORT_ANCHOR = "import numpy as np\n"
IMPORT_ADD = ("import collections\n"
              "import glob\n"
              "import os\n")

PARAMS_ANCHOR = "from openpilot.common.swaglog import cloudlog\n"
PARAMS_ADD = ("from openpilot.common.params import Params\n")

CONST_ANCHOR = "SAMPLE_BUFFER = 4096 # (approx 100ms)\n"
CONST_ADD = ("\n"
             "# Arman cabin audio recording (see " + MARKER + "). Gated on /data/record_audio,\n"
             "# same convention as /data/force_onroad. Raw s16le mono @ SAMPLE_RATE.\n"
             "AUDIO_FLAG = '/data/record_audio'\n"
             "AUDIO_NAME = f'cabin_audio_{SAMPLE_RATE}_mono_s16le.raw'\n"
             "AUDIO_SEG_RECHECK = 20  # update() runs at RATE Hz -> re-check segment every 2s\n")

INIT_ANCHOR = "    self.sound_pressure_level_weighted = 0\n"
INIT_ADD = ("\n"
            "    # Arman cabin audio: callback only queues, update() does the file I/O — blocking\n"
            "    # writes inside the PortAudio callback would cause input overruns.\n"
            "    self.audio_q: collections.deque = collections.deque()\n"
            "    self.audio_f = None\n"
            "    self.audio_seg = None\n"
            "    self.audio_tick = 0\n"
            "    self.audio_params = Params()\n")

SEND_ANCHOR = ("    self.pm.send('microphone', msg)\n"
               "    self.rk.keep_time()\n")
SEND_NEW = ("    self.pm.send('microphone', msg)\n"
            "    self.write_audio()\n"
            "    self.rk.keep_time()\n")

CB_ANCHOR = "    self.measurements = np.concatenate((self.measurements, indata[:, 0]))\n"
CB_ADD = ("\n"
          "    if self.audio_f is not None:\n"
          "      self.audio_q.append(indata[:, 0].copy())\n")

METHOD_ANCHOR = "  def callback(self, indata, frames, time, status):\n"
METHOD_ADD = '''  def current_segment(self):
    """Directory loggerd is filling right now, or None when offroad."""
    route = self.audio_params.get("CurrentRoute", encoding="utf8")
    if not route:
      return None
    segs = glob.glob(f"/data/media/0/realdata/{route}--*")
    if not segs:
      return None
    return max(segs, key=lambda p: int(p.rsplit("--", 1)[-1]))

  def write_audio(self):
    """Drain queued mic samples into the current segment. Never raises."""
    try:
      self.audio_tick += 1
      if self.audio_tick % AUDIO_SEG_RECHECK == 0:
        seg = self.current_segment() if os.path.exists(AUDIO_FLAG) else None
        if seg != self.audio_seg:
          if self.audio_f is not None:
            self.audio_f.close()
            self.audio_f = None
          self.audio_seg = seg
          self.audio_q.clear()
          if seg is not None:
            self.audio_f = open(os.path.join(seg, AUDIO_NAME), "ab")
            cloudlog.info(f"cabin audio -> {seg}/{AUDIO_NAME}")

      if self.audio_f is None:
        return
      while self.audio_q:
        chunk = self.audio_q.popleft()
        self.audio_f.write((np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16).tobytes())
      self.audio_f.flush()
    except Exception:
      cloudlog.exception("cabin audio write failed")
      try:
        if self.audio_f is not None:
          self.audio_f.close()
      except Exception:
        pass
      self.audio_f = None
      self.audio_seg = None

'''


def main():
  src = open(PATH).read()
  if MARKER in src:
    print("micd: already patched")
    return 0

  edits = [(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_ADD),
           (PARAMS_ANCHOR, PARAMS_ANCHOR + PARAMS_ADD),
           (CONST_ANCHOR, CONST_ANCHOR + CONST_ADD),
           (INIT_ANCHOR, INIT_ANCHOR + INIT_ADD),
           (SEND_ANCHOR, SEND_NEW),
           (CB_ANCHOR, CB_ANCHOR + CB_ADD),
           (METHOD_ANCHOR, METHOD_ADD + METHOD_ANCHOR)]

  out = src
  for anchor, replacement in edits:
    if out.count(anchor) != 1:
      print(f"ERROR: anchor not unique/found ({out.count(anchor)}x) — aborting, nothing changed:\n{anchor!r}")
      return 1
    out = out.replace(anchor, replacement, 1)

  shutil.copy(PATH, PATH + "." + MARKER)
  open(PATH, "w").write(out)
  try:
    py_compile.compile(PATH, doraise=True)
  except py_compile.PyCompileError as e:
    shutil.copy(PATH + "." + MARKER, PATH)
    print(f"ERROR: patched file does not compile, rolled back: {e}")
    return 1
  print(f"micd: PATCHED + compiled (backup .{MARKER})")

  open("/data/record_audio", "w").close()
  print("/data/record_audio CREATED -> recording enabled (rm it to stop)")
  print("\nApply now:  pkill -f '[s]ystem.micd'   # manager restarts it")
  return 0


if __name__ == "__main__":
  sys.exit(main())
