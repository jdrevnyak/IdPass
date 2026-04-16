"""
Wi-Fi / link status for kiosk devices (Raspberry Pi OS with NetworkManager).

Uses nmcli when available; falls back to sysfs operstate for a rough link read.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


def _run(args: List[str], timeout: float = 4.0) -> Tuple[bool, str, str]:
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode == 0, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return False, "", str(e)


def _first_wifi_device_nmcli() -> Optional[str]:
    ok, out, _ = _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"])
    if not ok or not out:
        return None
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1].strip() == "wifi":
            return parts[0].strip() or None
    return None


def _wifi_device_sysfs() -> Optional[str]:
    for path in sorted(glob.glob("/sys/class/net/wlan*/operstate")):
        iface = os.path.basename(os.path.dirname(path))
        if iface.startswith("wlan"):
            return iface
    return None


def _ssid_from_iw(iface: str) -> str:
    ok, out, _ = _run(["iw", "dev", iface, "link"], timeout=3.0)
    if not ok or not out:
        return ""
    m = re.search(r"SSID:\s*(\S+)", out)
    return m.group(1) if m else ""


def _signal_from_nmcli() -> Optional[int]:
    """Parse ACTIVE / SSID / SIGNAL lines: yes:MyNet:72 -> 72."""
    ok, out, _ = _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"])
    if not ok or not out:
        return None
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[0].strip().lower() == "yes":
            try:
                return int(parts[2].strip())
            except ValueError:
                return None
    return None


def _read_operstate(iface: str) -> str:
    path = f"/sys/class/net/{iface}/operstate"
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def get_wifi_info() -> Dict[str, object]:
    """
    Return a dict safe to show in the UI:
      - platform: str
      - nmcli_available: bool
      - wifi_device: str or None
      - state: str (e.g. connected, disconnected, unavailable)
      - connected: bool
      - ssid: str
      - signal_percent: int or None
      - detail: str (human-readable extra line)
    """
    result: Dict[str, object] = {
        "platform": sys.platform,
        "nmcli_available": False,
        "wifi_device": None,
        "state": "unavailable",
        "connected": False,
        "ssid": "",
        "signal_percent": None,
        "detail": "",
    }

    if sys.platform != "linux":
        result["detail"] = "Wi-Fi status is only read on Linux (Raspberry Pi)."
        return result

    ok_nm, _, _ = _run(["nmcli", "--version"], timeout=2.0)
    result["nmcli_available"] = ok_nm
    if not ok_nm:
        result["detail"] = "nmcli not found. Install NetworkManager or use Raspberry Pi OS."

    iface = _first_wifi_device_nmcli() or _wifi_device_sysfs()
    result["wifi_device"] = iface

    if not iface:
        result["state"] = "no_wifi_device"
        result["detail"] = "No wireless interface detected (wlan0, …)."
        return result

    ok, out, _ = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    state = "unknown"
    if ok and out:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0].strip() == iface:
                state = parts[2].strip().lower()
                break
    result["state"] = state

    oper = _read_operstate(iface)
    connected = state == "connected" or oper == "up"
    result["connected"] = connected

    if connected:
        ssid = _ssid_from_iw(iface)
        if not ssid and ok_nm:
            ok2, out2, _ = _run(
                ["nmcli", "-t", "-f", "GENERAL.CONNECTION", "device", "show", iface]
            )
            if ok2 and out2:
                for line in out2.splitlines():
                    if line.startswith("GENERAL.CONNECTION:"):
                        ssid = line.split(":", 1)[1].strip()
                        break
        result["ssid"] = ssid or "(connected)"
        sig = _signal_from_nmcli()
        result["signal_percent"] = sig
        if sig is not None:
            result["detail"] = f"Interface {iface} · signal ~{sig}%"
        else:
            result["detail"] = f"Interface {iface}"
    else:
        result["ssid"] = ""
        if oper:
            result["detail"] = f"Interface {iface} · carrier {oper}"
        else:
            result["detail"] = f"Interface {iface} · {state or 'not connected'}"

    return result


def stimulate_wifi_light() -> None:
    """Light nudge to NetworkManager (radio on, rescan). Safe to call periodically."""
    if sys.platform != "linux":
        return
    for args in (
        ["nmcli", "networking", "on"],
        ["nmcli", "radio", "wifi", "on"],
        ["nmcli", "dev", "wifi", "rescan"],
    ):
        _run(args, timeout=8.0)


def try_wifi_reconnect() -> Tuple[bool, str]:
    """
    Best-effort: turn networking/radio on, rescan, ask NM to bring the Wi-Fi device up.
    Does not add new networks; relies on saved connections. May require policykit permissions.
    """
    if sys.platform != "linux":
        return False, "Only available on Linux."

    steps: List[str] = []
    for args in (
        ["nmcli", "networking", "on"],
        ["nmcli", "radio", "wifi", "on"],
    ):
        ok, _, err = _run(args, timeout=6.0)
        steps.append(f"{' '.join(args)} → {'ok' if ok else err or 'failed'}")

    ok, _, _ = _run(["nmcli", "dev", "wifi", "rescan"], timeout=15.0)
    steps.append(f"wifi rescan → {'ok' if ok else 'failed'}")

    iface = _first_wifi_device_nmcli() or _wifi_device_sysfs()
    if iface:
        ok, _, err = _run(["nmcli", "device", "connect", iface], timeout=30.0)
        steps.append(f"device connect {iface} → {'ok' if ok else err or 'failed'}")
        if ok:
            return True, "\n".join(steps)

    return False, "\n".join(steps)
