#!/usr/bin/env python3
"""Scans the local network with arp-scan and (optionally) speaks a summary."""
import subprocess
import re
import sys

def scan():
    result = subprocess.run(
        ["sudo", "arp-scan", "--interface=eth6", "--localnet"],
        capture_output=True, text=True
    )
    devices = []
    for line in result.stdout.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s+(.*)$", line)
        if m:
            ip, mac, vendor = m.groups()
            devices.append({"ip": ip, "mac": mac, "vendor": vendor.strip()})
    return devices

if __name__ == "__main__":
    devices = scan()
    print(f"Found {len(devices)} device(s):")
    for d in devices:
        print(f"  {d['ip']:<15} {d['mac']}  {d['vendor']}")
    if "--speak" in sys.argv:
        subprocess.run(["/home/abinand/jarvis/speak.sh", f"I found {len(devices)} devices on your network."])
