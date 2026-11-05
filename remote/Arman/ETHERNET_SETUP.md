# comma ↔ laptop over Ethernet (and hotspot) — setup & runbook

All our tools take `--ip`, so hotspot vs ethernet changes NOTHING except the IP.
`./find_comma.sh` discovers the device on either network:
```bash
IP=$(./find_comma.sh)
python3 experiment.py --ip $IP check
python3 cp_export.py  --ip $IP --mode live --udp <client>:<port>
```

## Physical connection
comma 3X has no RJ45 — use a **USB-C → Ethernet adapter** in the comma's USB-C (OBD-C)
port, cable to the laptop's ethernet port. After plugging, verify the adapter is
recognized:
```bash
ssh comma@<current-ip-via-hotspot> 'ip -br link'     # expect a new ethN/enx… UP
ssh comma@<ip> 'dmesg | tail -20'                    # adapter driver messages
```
If no new interface appears, the adapter chipset isn't supported by AGNOS — fall back
to hotspot (everything still works).

## Plan A (recommended): laptop shares the link (DHCP)
Laptop side (NetworkManager, one-time):
```bash
nmcli con add type ethernet ifname <ETH_IFACE> con-name comma-share ipv4.method shared
nmcli con up comma-share
```
NetworkManager runs a DHCP server on the port; the comma's ethernet gets an address in
**10.42.0.x** automatically. Then:
```bash
IP=$(./find_comma.sh)        # finds it on 10.42.0.0/24
```

## Plan B (fallback): static both ends
Laptop:
```bash
nmcli con add type ethernet ifname <ETH_IFACE> con-name comma-static ipv4.method manual \
  ipv4.addresses 192.168.5.1/24
nmcli con up comma-static
```
comma (over the hotspot SSH first, adapter plugged; AGNOS uses NetworkManager too):
```bash
ssh comma@<hotspot-ip>
sudo nmcli con add type ethernet ifname <ethN> con-name eth-static ipv4.method manual \
  ipv4.addresses 192.168.5.2/24
sudo nmcli con up eth-static
```
Then the device is at **192.168.5.2**.

## Field checklist (tomorrow)
1. Boot both on the hotspot first (known-good path), `./find_comma.sh` → sanity check.
2. Plug the adapter + cable; `ip -br link` on the comma → new interface?
3. Plan A up → `./find_comma.sh` again → should print 10.42.0.x.
4. Re-run `experiment.py --ip <new-ip> check` — everything else is unchanged.
5. Latency check (ethernet should be ~1 ms):  `ping -c 20 <ip>`.
6. If anything misbehaves: unplug, revert to hotspot IP — zero config to undo.

## Notes
- The exporter binds 0.0.0.0:7700 → reachable on every interface automatically.
- Keep the hotspot up as a fallback path during the first ethernet test.
- UDP to the client (`cp_export --udp`) rides whatever route the laptop has to them —
  independent of how the comma is attached.
