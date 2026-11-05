#!/usr/bin/env bash
# stop_udp_stop.sh — stop the comma's 0/1 UDP sender (run on the LAPTOP).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
IP=172.20.10.3
[ -z "$IP" ] && { echo "comma not found (may already be off)"; exit 0; }
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 "comma@$IP" \
  "pkill -f '[s]top_udp.py' && echo 'sender stopped' || echo 'no sender running'"
