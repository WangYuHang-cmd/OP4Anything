#!/usr/bin/env bash
# find_comma.sh — auto-discover the comma device's IP on any network
# (phone hotspot OR direct ethernet). Prints the IP on stdout, logs to stderr.
#
#   IP=$(./find_comma.sh)             # then: python3 cp_export.py --ip $IP ...
#   ./find_comma.sh -v                # verbose candidates
#
# Strategy: for every non-loopback IPv4 subnet this machine is on, scan for hosts
# with TCP/22 open, then verify it's the comma by the reg_export port (7700) or
# an SSH banner. Small subnets are swept fully; /24 or larger use nmap if present.
set -u
VERBOSE=${1:-}

log() { echo "$@" >&2; }

subnets=$(ip -o -4 addr show scope global | awk '{print $4}')
[ -z "$subnets" ] && { log "no active IPv4 interfaces"; exit 1; }

candidates=""
for cidr in $subnets; do
  log "scanning $cidr ..."
  if command -v nmap >/dev/null 2>&1; then
    found=$(nmap -n -p22 --open -T4 --host-timeout 2s "$cidr" -oG - 2>/dev/null |
            awk '/22\/open/{print $2}')
  else
    # fallback (no nmap): parallel TCP/22 sweep of the /24 around our own address
    base=$(echo "$cidr" | cut -d/ -f1 | cut -d. -f1-3)
    found=$(for i in $(seq 1 254); do
      (timeout 0.4 bash -c "echo > /dev/tcp/$base.$i/22" 2>/dev/null && echo "$base.$i") &
    done; wait)
  fi
  candidates="$candidates $found"
done

self_ips=$(ip -o -4 addr show | awk '{print $4}' | cut -d/ -f1)
for ip in $candidates; do
  case " $self_ips " in *" $ip "*) continue;; esac
  [ -n "$VERBOSE" ] && log "candidate: $ip"
  # comma check 1: reg_export exporter port
  if timeout 1 bash -c "echo > /dev/tcp/$ip/7700" 2>/dev/null; then
    log "FOUND comma at $ip (port 7700 open)"
    echo "$ip"; exit 0
  fi
  # comma check 2: ssh as comma with agnos marker
  if timeout 5 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=yes \
       "comma@$ip" 'test -d /data/openpilot' 2>/dev/null; then
    log "FOUND comma at $ip (ssh verified)"
    echo "$ip"; exit 0
  fi
done
log "comma not found on: $subnets"
exit 1
