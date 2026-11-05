#!/usr/bin/env bash
# stop_udp_start.sh — ONE-CLICK (run on the LAPTOP).
# Makes the comma stream ONLY "0"/"1" over UDP to the destination you give.
#
#   ./stop_udp_start.sh <DEST_IP> <DEST_PORT> [HZ]
#   ./stop_udp_start.sh 192.168.1.50 5005          # 10 Hz default
#   ./stop_udp_start.sh 192.168.1.50 5005 20
#
# Finds the comma automatically (hotspot/ethernet/wifi). Stop it with:
#   ./stop_udp_stop.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

DEST_IP="${1:?usage: stop_udp_start.sh <DEST_IP> <DEST_PORT> [HZ]}"
DEST_PORT="${2:?usage: stop_udp_start.sh <DEST_IP> <DEST_PORT> [HZ]}"
HZ="${3:-10}"
USER_HOST="comma"

echo "finding comma ..."
#IP="$("$DIR/find_comma.sh" 2>/dev/null || true)"
IP=172.20.10.3
[ -z "$IP" ] && { echo "ERROR: comma not found on any network (is it powered/on the network?)"; exit 1; }
# IP = "172.20.10.3"
echo $IP
echo "comma at $IP"

SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 $USER_HOST@$IP"

# make sure the sender script is on the device (self-heal if missing)
if ! $SSH 'test -f /data/objstop/stop_udp.py'; then
  echo "installing stop_udp.py on the comma ..."
  scp -o StrictHostKeyChecking=no "$DIR/stop_udp.py" "$USER_HOST@$IP:/data/objstop/stop_udp.py"
fi

# kill any previous sender. MUST be its own ssh call: if the pkill shares a
# command line with the python invocation below, `pkill -f` matches its own
# parent shell and kills the whole remote command before it can start anything.
$SSH "pkill -f '[s]top_udp.py' 2>/dev/null; sleep 1; echo cleaned" || true

# start a fresh one detached (survives ssh logout)
$SSH "PYTHONPATH=/data/openpilot nohup /usr/local/pyenv/versions/3.11.4/bin/python3 \
  /data/objstop/stop_udp.py $DEST_IP $DEST_PORT --hz $HZ \
  > /tmp/stop_udp.log 2>&1 < /dev/null & echo started"

sleep 1
echo "--- sender log ---"; $SSH 'head -2 /tmp/stop_udp.log'
echo
echo "✅ comma is now sending '0'/'1' UDP -> $DEST_IP:$DEST_PORT at ${HZ} Hz"
echo "   watch what it sends:   ./stop_udp_watch.sh $DEST_PORT      (if this laptop is the receiver)"
echo "   stop it:               ./stop_udp_stop.sh"
