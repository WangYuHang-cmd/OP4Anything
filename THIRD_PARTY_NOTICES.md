# Third-party notices

The original work in this repository is released under the MIT License (see [`LICENSE`](LICENSE)).
Some files are derived from, embed short excerpts of, or are patches against the third-party
projects listed below. Those portions remain under their original licenses.

This project is **not affiliated with, endorsed by, or supported by** comma.ai, the openpilot
project, the sunnypilot project, or Ultralytics.

> [!CAUTION]
> openpilot describes itself as "ALPHA QUALITY SOFTWARE FOR RESEARCH PURPOSES ONLY. THIS IS NOT
> A PRODUCT." The modifications documented here go further: they enable openpilot longitudinal
> control without the stock radar/AEB, brake on camera detections, force the device onroad and
> skip startup checks. Use them only for research, on a closed course, with a safety driver.

## openpilot (MIT)

<https://github.com/commaai/openpilot>

Where it appears in this repository:

| File | Relationship |
|---|---|
| `remote/Arman/dashcam_anywhere/dashcam_anywhere.patch` | Patch against openpilot v0.11.1 (`release-tizi`). It modifies 9 existing openpilot files and adds 1 new module (`common/dashcam_anywhere.py`), so it contains openpilot source (context and modified lines). |
| `remote/Arman/objstopd.py`, `remote/Arman/vision/objstopd.py` | `yuv_to_rgb()` / `extract_image()` are adapted from openpilot `system/camerad/snapshot/snapshot.py`. |
| `remote/Arman/enable_dashcam_mode.py`, `force_onroad_v2.py`, `enable_fake_ignition_autostart.py`, `suppress_car_prompt.py`, `enable_cabin_audio.py` | Device-side patcher scripts that embed short anchor excerpts of the openpilot/sunnypilot files they modify. |
| `remote/exporter_device.py` and other device-side tools | Use openpilot's `cereal` / `msgq` / `VisionIPC` APIs at runtime (imported, not copied). |

License text:

```
Copyright (c) 2018, Comma.ai, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## sunnypilot (MIT)

<https://github.com/sunnypilot/sunnypilot> — a fork of openpilot. The first-era tools
(July–August 2026) ran on and patched sunnypilot 0.9.7.1. Its license file carries the same
MIT text and copyright line as openpilot above
(<https://github.com/sunnypilot/sunnypilot/blob/master/LICENSE>).

## Ultralytics YOLOv8 (AGPL-3.0) — not included

<https://github.com/ultralytics/ultralytics> (<https://github.com/ultralytics/ultralytics/blob/main/LICENSE>)

- No Ultralytics code and **no model weights** are included in this repository.
- `remote/Arman/vision/ped_analysis.py` imports the `ultralytics` package (installed separately)
  and loads `yolov8n.pt` / `yolov8s.pt`.
- `remote/Arman/vision/yolo_infer.py` and `objstopd.py` expect YOLOv8 models exported to ONNX
  (`yolov8n_320.onnx`, `yolov8n.onnx`, optionally `yolov8s_320.onnx`).
- Ultralytics distributes YOLOv8 code and weights under AGPL-3.0 (or a commercial Enterprise
  License). Obtaining, exporting and deploying these models is the user's responsibility and may
  carry AGPL-3.0 obligations.

## Python packages (not vendored)

The tools import packages that are installed separately and remain under their own licenses,
e.g. `numpy`, `matplotlib`, `Pillow`, `onnxruntime`, `pandas`, `pyarrow`, `zstandard`.
