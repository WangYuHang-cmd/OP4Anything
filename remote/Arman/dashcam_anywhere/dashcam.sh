#!/usr/bin/env bash
# dashcam.sh: control the comma dashcam-anywhere mode from the laptop/desktop.
#
#   ./dashcam.sh status       [IP]   live status (onroad, panda safety, calibration, speed source)
#   ./dashcam.sh reset-calib  [IP]   restart camera calibration from scratch (after moving to another vehicle)
#   ./dashcam.sh enable       [IP]   turn dashcam-anywhere mode on  (reboots)
#   ./dashcam.sh disable      [IP]   turn it off, back to normal car mode (reboots)
#   ./dashcam.sh restore-civic [IP]  after disable: restore the Civic calibration/learned params from the backup
#   ./dashcam.sh poweroff     [IP]   clean shutdown (the onroad UI has no power-off button)
#
# IP: argument, else $COMMA_IP, else auto-discovery with ../find_comma.sh. Commands that change the device
# print its dongle id and ask for confirmation; -y skips the prompt.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YES=""
if [ "${1:-}" = "-y" ]; then YES=1; shift; fi
CMD="${1:-}"
IP="${2:-${COMMA_IP:-}}"
BACKUP=/data/dashcam_backup/20261003
OPPY="cd /data/openpilot && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/data/openpilot /usr/local/venv/bin/python3 -B"

usage() { sed -n '2,14p' "$0"; exit 1; }
[ -z "$CMD" ] && usage

if [ -z "$IP" ]; then
  echo "no IP given, discovering ..." >&2
  IP=$("$HERE/../find_comma.sh") || { echo "comma not found; pass the IP" >&2; exit 1; }
fi
SSH=(ssh -o ConnectTimeout=8 -o BatchMode=yes "comma@$IP")

confirm() {
  local dongle
  dongle=$("${SSH[@]}" 'cat /data/params/d/DongleId 2>/dev/null' || true)
  echo "device $IP  dongle ${dongle:-?}  -> $1"
  if [ -z "$YES" ]; then
    read -r -p "proceed? [y/N] " ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "aborted"; exit 1; }
  fi
}

case "$CMD" in
  status)
    "${SSH[@]}" "$OPPY /data/dashcam_anywhere/status.py"
    ;;
  reset-calib)
    "${SSH[@]}" 'touch /data/reset_calib'
    echo "reset requested; calibrationd consumes it within ~1 s while onroad (or at its next start)"
    ;;
  enable)
    confirm "ENABLE dashcam-anywhere (forced onroad, no car control) and reboot"
    if ! "${SSH[@]}" 'test -f /data/openpilot/common/dashcam_anywhere.py'; then
      echo "dashcam-anywhere patch is not installed on this device"; exit 1
    fi
    "${SSH[@]}" 'touch /data/force_onroad && sudo reboot' || true  # the reboot drops the connection
    echo "rebooting; expect the onroad camera view within ~1 min"
    ;;
  disable)
    confirm "DISABLE dashcam-anywhere and reboot (device then needs a real ignition to go onroad)"
    "${SSH[@]}" 'rm -f /data/force_onroad && sudo reboot' || true
    echo "rebooting into normal mode. Before driving the Civic either run '$0 restore-civic $IP' (offroad)"
    echo "or just drive: the robot calibration is dropped automatically and the Civic recalibrates from scratch."
    ;;
  restore-civic)
    confirm "restore Civic CalibrationParams/CarParamsPersistent/learned params from $BACKUP"
    "${SSH[@]}" "set -e; test ! -e /data/force_onroad || { echo 'dashcam mode still on, run disable first'; exit 1; }
      test \"\$(cat /data/params/d/IsOnroad)\" = 0 || { echo 'device is onroad, retry offroad'; exit 1; }
      for k in CalibrationParams CarParamsPersistent LiveParametersV2 LiveDelay LiveTorqueParameters; do
        [ -f $BACKUP/\$k ] && cp -p $BACKUP/\$k /data/params/d/\$k && echo restored \$k; done
      rm -f /data/calib_from_dashcam; sync"
    ;;
  poweroff)
    confirm "power off"
    "${SSH[@]}" "$OPPY -c 'from openpilot.common.params import Params; Params().put_bool(\"DoShutdown\", True, block=True)'"
    echo "shutting down cleanly"
    ;;
  *)
    usage
    ;;
esac
