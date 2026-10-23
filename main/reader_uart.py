"""Turn on the Raspberry Pi header UART the ESP32 card reader uses.

The reader is wired to GPIO 14 (physical pin 8) and GPIO 15 (physical pin 10).
Those pins do nothing for the app until two boot settings are in place:

- enable_uart=1 in the boot config (serial hardware on)
- no console=serial0 / ttyAMA0 / ttyS0 in cmdline.txt (no login shell)

That is the same result as raspi-config: login shell over serial "No",
serial port hardware "Yes". On a Pi 5 the header UART is a separate device
from the debug header, so the header also needs dtoverlay=uart0-pi5, which
appears as /dev/ttyAMA0. /dev/ttyAMA10 is the debug header, not the reader.

Boot-config changes apply on the next reboot. The script reboots once when it
changes something, and it will not reboot again if that change does not stick.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys

_CONSOLE_TOKEN = re.compile(
    r"console=(?:serial0|ttyAMA0|ttyS0)(?:,\d+\w*)?$"
)
_ENABLE_UART_LINE = re.compile(r"(?m)^(?P<indent>\s*)enable_uart\s*=\s*\S+")
_ENABLE_UART_ON = re.compile(r"(?m)^\s*enable_uart\s*=\s*1\s*(?:#.*)?$")
_UART0_PI5 = re.compile(r"(?m)^\s*dtoverlay\s*=\s*uart0-pi5\b")

_STAMP_PATH = "/var/lib/idpass/reader-uart.stamp"
_SERIAL_GETTYS = (
    "serial-getty@serial0.service",
    "serial-getty@ttyAMA0.service",
    "serial-getty@ttyS0.service",
)

CONFIG_CANDIDATES = ("/boot/firmware/config.txt", "/boot/config.txt")


def is_raspberry_pi():
    return os.path.isfile("/proc/device-tree/model") or os.path.isdir("/boot/firmware")


def pi_model():
    try:
        with open("/proc/device-tree/model", "rb") as model_file:
            return model_file.read().replace(b"\x00", b"").decode("utf-8", "replace")
    except OSError:
        return ""


def is_pi5(model=None):
    text = pi_model() if model is None else model
    return (
        "Raspberry Pi 5" in text
        or "Raspberry Pi 500" in text
        or "Compute Module 5" in text
    )


def find_boot_files():
    """Return (config.txt path, cmdline.txt path) or (None, None)."""
    for config_path in CONFIG_CANDIDATES:
        if os.path.isfile(config_path):
            cmdline_path = os.path.join(os.path.dirname(config_path), "cmdline.txt")
            return config_path, cmdline_path
    return None, None


def _normalize_cmdline(cmdline):
    return " ".join(cmdline.split())


def strip_serial_console(cmdline):
    """Drop the serial login console and keep the HDMI console token."""
    kept = [
        token for token in cmdline.split()
        if not _CONSOLE_TOKEN.fullmatch(token)
    ]
    return " ".join(kept)


def plan_reader_uart(config, cmdline, pi5):
    """Return (config, cmdline, changed) with the reader UART enabled.

    Unchanged text is returned as it was read, so a rewrite is not triggered
    by a trailing newline or a run of spaces.
    """
    new_config = config
    if not _ENABLE_UART_ON.search(new_config):
        if _ENABLE_UART_LINE.search(new_config):
            new_config = _ENABLE_UART_LINE.sub(
                r"\g<indent>enable_uart=1", new_config, count=1
            )
        else:
            if new_config and not new_config.endswith("\n"):
                new_config += "\n"
            if new_config and not new_config.endswith("\n\n"):
                new_config += "\n"
            new_config += (
                "# IdPass card reader on GPIO 14 and GPIO 15\n"
                "enable_uart=1\n"
            )

    if pi5 and not _UART0_PI5.search(new_config):
        if new_config and not new_config.endswith("\n"):
            new_config += "\n"
        new_config += "dtoverlay=uart0-pi5\n"

    new_cmdline = strip_serial_console(cmdline)
    config_changed = new_config != config
    cmdline_changed = new_cmdline != _normalize_cmdline(cmdline)
    if not config_changed and not cmdline_changed:
        return config, cmdline, False

    if not cmdline_changed:
        new_cmdline = cmdline
    elif not new_cmdline.endswith("\n"):
        new_cmdline += "\n"
    return new_config, new_cmdline, True


def boot_hash(config, cmdline):
    payload = config + "\n---\n" + _normalize_cmdline(cmdline)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def should_reboot(boot_changed, group_changed, stamp_text, boot_digest, user):
    """Reboot once per distinct change. A repeated change means it did not stick."""
    lines = set(stamp_text.splitlines())
    boot_blocked = boot_changed and f"boot:{boot_digest}" in lines
    group_key = f"group:{user}" if user else ""
    group_blocked = bool(group_changed and group_key and group_key in lines)
    if (boot_changed and not boot_blocked) or (group_changed and not group_blocked):
        return "reboot"
    if boot_blocked or group_blocked:
        return "stuck"
    return "ok"


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _write_text(path, text):
    temporary = path + ".idpass-tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)


def _read_stamp():
    try:
        return _read_text(_STAMP_PATH)
    except OSError:
        return ""


def _write_stamp(text):
    directory = os.path.dirname(_STAMP_PATH)
    os.makedirs(directory, exist_ok=True)
    _write_text(_STAMP_PATH, text if text.endswith("\n") or text == "" else text + "\n")


def _remember_stamp(line):
    """Record one boot hash, and one dialout line per user."""
    existing = [item for item in _read_stamp().splitlines() if item]
    if line.startswith("boot:"):
        existing = [item for item in existing if not item.startswith("boot:")]
    else:
        existing = [item for item in existing if item != line]
    existing.append(line)
    _write_stamp("\n".join(existing) + "\n")


def user_in_dialout(user):
    try:
        import grp
        import pwd
        group = grp.getgrnam("dialout")
    except KeyError:
        return True
    if user in group.gr_mem:
        return True
    try:
        return pwd.getpwnam(user).pw_gid == group.gr_gid
    except KeyError:
        return True


def _target_user():
    user = os.environ.get("SUDO_USER") or ""
    if user and user != "root":
        return user
    return ""


def _stop_serial_gettys():
    if not shutil.which("systemctl"):
        return
    for unit in _SERIAL_GETTYS:
        subprocess.run(
            ["systemctl", "disable", "--now", unit],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _add_dialout(user):
    result = subprocess.run(
        ["usermod", "-aG", "dialout", user],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        print(f"[UART] Could not add {user} to dialout: {detail}")
        return False
    print(f"[UART] Added {user} to the dialout group.")
    return True


def apply_boot_config():
    """Enable the reader UART. Returns 'ok', 'reboot', 'stuck', or 'skipped'."""
    config_path, cmdline_path = find_boot_files()
    if config_path is None:
        print("[UART] No boot config found. Serial port was left unchanged.")
        return "skipped"

    config = _read_text(config_path)
    if os.path.isfile(cmdline_path):
        cmdline = _read_text(cmdline_path)
    else:
        cmdline = ""

    new_config, new_cmdline, boot_changed = plan_reader_uart(config, cmdline, is_pi5())
    user = _target_user()
    group_changed = bool(user) and not user_in_dialout(user)
    digest = boot_hash(new_config, new_cmdline)
    decision = should_reboot(boot_changed, group_changed, _read_stamp(), digest, user)

    if decision == "stuck":
        print(
            "[UART] Serial settings were applied once and did not stay in effect. "
            "Not rebooting again."
        )
        _stop_serial_gettys()
        return "stuck"

    if decision != "reboot":
        print("[UART] Header UART is already enabled.")
        _stop_serial_gettys()
        return "ok"

    wrote_boot = False
    if boot_changed:
        _write_text(config_path, new_config)
        if cmdline:
            _write_text(cmdline_path, new_cmdline)
        _remember_stamp(f"boot:{digest}")
        wrote_boot = True
        print(f"[UART] Enabled the card-reader UART in {config_path}.")

    added_group = False
    if group_changed and _add_dialout(user):
        _remember_stamp(f"group:{user}")
        added_group = True

    _stop_serial_gettys()
    if wrote_boot or added_group:
        return "reboot"
    return "ok"


def _reboot():
    reboot_bin = shutil.which("reboot") or shutil.which("systemctl")
    if reboot_bin and os.path.basename(reboot_bin) == "systemctl":
        command = [reboot_bin, "reboot"]
    elif reboot_bin:
        command = [reboot_bin]
    else:
        return False
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0


def apply():
    """Root entry point. Exit 10 means a reboot was requested and failed."""
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print("[UART] Run as root: sudo python3 main/reader_uart.py --apply")
        return 1
    status = apply_boot_config()
    if status != "reboot":
        return 0
    print("[UART] Rebooting so the card reader UART turns on.")
    if _reboot():
        return 0
    print("[UART] Reboot did not start. Reboot this Pi to finish enabling the reader.")
    return 10


def ensure_reader_uart():
    """Enable the header UART before the app opens the serial port.

    Does nothing on a machine that is not a Raspberry Pi. A reboot, when one
    is required, is started from the root helper. Exit 0 after a successful
    reboot request so the update monitor leaves the screen down until the
    Pi comes back.
    """
    if not is_raspberry_pi():
        return

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        code = apply()
        if code == 0:
            return
        print("[UART] Reboot this Pi to finish enabling the card reader.")
        return

    script = os.path.abspath(__file__)
    try:
        result = subprocess.run(
            ["sudo", "-n", sys.executable, script, "--apply"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        print(f"[UART] Could not enable the serial port: {err}")
        return

    output = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
    )
    if output:
        print(output)
    if result.returncode == 0:
        if "Rebooting so the card reader" in output:
            sys.exit(0)
        return
    lowered = output.lower()
    if result.returncode == 1 or "password" in lowered:
        print("[UART] Passwordless sudo is required to enable the serial port.")
        print("[UART] Run: sudo python3 main/reader_uart.py --apply")
        return
    print(f"[UART] Serial setup exited {result.returncode}.")


def main():
    sys.exit(apply())


if __name__ == "__main__":
    main()
