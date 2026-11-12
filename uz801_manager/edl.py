"""Passive Windows EDL inventory and local tool checks; never connects Firehose."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from .adb import CREATE_FLAGS
from .errors import SafetyError
from .storage import local_directory

# Fixed script. Device instance IDs are filtered locally, never returned or logged.
PNP_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$items = @(Get-CimInstance Win32_PnPEntity | Where-Object {
  $_.PNPDeviceID -like 'USB\*'
} | ForEach-Object {
  [PSCustomObject]@{ Name=$_.Name; PNPDeviceID=$_.PNPDeviceID;
    Service=$_.Service; ConfigManagerErrorCode=$_.ConfigManagerErrorCode; Status=$_.Status }
})
ConvertTo-Json -InputObject $items -Compress
"""


def summarize_usb(rows):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise SafetyError("EDL_PROBE_FAILED")
    devices = []
    for row in rows:
        instance = str(row.get("PNPDeviceID", "")).upper()
        if "VID_05C6&PID_9008" not in instance:
            continue
        service = str(row.get("Service") or "").lower()
        code = row.get("ConfigManagerErrorCode")
        state = "PASS" if code == 0 and service else "FAIL"
        # A bound QDLoader driver does not prove that a given libusb backend works.
        known_service = service if service in ("winusb", "qcusbser", "qcusbser2k", "libusbk", "libusb0", "usbser") else "other/unknown"
        devices.append({"name": "Qualcomm USB 05C6:9008", "driver_service": known_service,
                        "driver_status": state, "problem_code": code if isinstance(code, int) else None,
                        "communication": "NOT_TESTED"})
    return {"edl_detected": bool(devices), "devices": devices,
            "driver_status": "NOT_TESTED" if not devices else ("PASS" if all(d["driver_status"] == "PASS" for d in devices) else "FAIL"),
            "usb_device_count": len(rows)}


class EDLInspector:
    def __init__(self, *, run=subprocess.run, executable=None, windows=None):
        self.run = run
        self.executable = executable or os.environ.get("UZ801_EDL") or shutil.which("edl")
        self.windows = os.name == "nt" if windows is None else windows

    def inventory(self):
        if not self.windows:
            return {"edl_detected": False, "devices": [], "driver_status": "NOT_TESTED", "platform": "unsupported"}
        powershell = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        try:
            result = self.run([powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PNP_SCRIPT],
                              capture_output=True, timeout=30, shell=False, creationflags=CREATE_FLAGS)
            if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
                raise SafetyError("EDL_PROBE_FAILED")
            rows = json.loads(result.stdout.decode("utf-8-sig"))
            return summarize_usb(rows if isinstance(rows, list) else [rows])
        except (OSError, subprocess.TimeoutExpired, ValueError):
            raise SafetyError("EDL_PROBE_FAILED") from None

    def tool_check(self):
        if not self.executable or not Path(self.executable).is_file():
            return {"status": "MISSING", "message": "Chưa tìm thấy công cụ bkerler/edl. Không tự cài đặt."}
        executable = Path(self.executable).resolve()
        # Never invoke .bat/.cmd through Windows' implicit shell or a user web command.
        if executable.suffix.lower() not in ((".exe",) if self.windows else ("", ".exe")):
            return {"status": "NOT_TESTED", "message": "Chỉ kiểm tra launcher EDL thực thi; đặt UZ801_EDL tới edl.exe."}
        try:
            result = self.run([str(executable), "--help"], capture_output=True, timeout=15,
                              shell=False, creationflags=CREATE_FLAGS)
        except (OSError, subprocess.TimeoutExpired):
            return {"status": "FAIL", "code": "EDL_PROBE_FAILED"}
        # --help exits before opening USB in the reviewed bkerler CLI.
        output = result.stdout + result.stderr
        valid = result.returncode == 0 and any(word in output.lower() for word in (b"sahara", b"firehose", b"qualcomm"))
        return {"status": "PASS" if valid else "FAIL", "scope": "CLI_HELP_ONLY", "communication": "NOT_TESTED"}

    def inspect(self, programmer=None):
        try:
            inventory = self.inventory()
        except SafetyError:
            inventory = {"edl_detected": False, "devices": [], "driver_status": "FAIL", "code": "EDL_PROBE_FAILED"}
        return {**inventory, "tool": self.tool_check(), "programmer": check_programmer(programmer),
                "offline_backup": "LOCKED_UNVERIFIED_RECOVERY", "recovery_verified": False,
                "flash_enabled": False,
                "guidance": "Ưu tiên EDL offline sau khi có bằng chứng programmer và đường khôi phục. Phát hiện 9008/driver không chứng minh recovery hoạt động. Không tự đổi driver, nạp programmer hay reboot."}


def check_programmer(value):
    if not value:
        return {"status": "MISSING", "compatibility": "UNKNOWN", "executed": False}
    if not isinstance(value, str):
        raise SafetyError("PATH_INVALID")
    path = Path(value)
    if os.name == "nt" and (value.startswith(("\\\\", "//")) or ":" in str(path)[2:]):
        raise SafetyError("PATH_INVALID")
    parent = local_directory(str(path.parent))
    if path.is_symlink() or path.resolve().parent != parent or path.suffix.lower() not in (".mbn", ".elf", ".bin"):
        raise SafetyError("PATH_INVALID")
    if not path.is_file() or not 0 < path.stat().st_size <= 32 * 1024 * 1024:
        raise SafetyError("INPUT_INVALID")
    data = path.read_bytes()
    return {"status": "INSPECTED", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
            "format": "ELF" if data.startswith(b"\x7fELF") else "MBN_OR_UNKNOWN",
            "compatibility": "UNKNOWN", "executed": False,
            "reason": "Tên file/SoC/SHA-256 không chứng minh programmer phù hợp board và khóa ký. Chưa có bằng chứng Sahara/Firehose trên đúng thiết bị."}


def readiness():
    # No evidence supplied by a browser can unlock a write operation in this release.
    return {"flash_enabled": False, "status": "LOCKED", "phase": "1–3",
            "checks": [
                {"name": "Board vật lý FY_UZ801_V3.2", "status": "NOT_VERIFIED"},
                {"name": "Firmware đúng V3.2 và đúng biến thể", "status": "NOT_VERIFIED"},
                {"name": "Backup nhất quán và thử khôi phục", "status": "NOT_TESTED"},
                {"name": "Programmer và đường EDL thực tế", "status": "NOT_TESTED"},
                {"name": "Phê duyệt riêng cho Phase 5", "status": "NOT_REQUESTED"},
            ]}
