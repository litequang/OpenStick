"""Metadata-only compatibility transport. Separate from the proven backup API.

No shell, exec, modem-node opens, AT/QMI calls, or write SYNC operations.
Unknown directory entries are discarded before returning to the collector.
"""
import re
import struct
import threading
import time

from .adb_sync import SyncReader
from .errors import Cancelled, SafetyError

MODULES = frozenset({"wlan", "8189es", "8189fs", "rtl8189es", "rtl8189fs", "bcmdhd", "dhd",
                    "cfg80211", "mac80211", "ath6kl_sdio", "ath10k_sdio", "ath10k_core", "wcn36xx",
                    "wcnss_core", "qcom_wcnss", "qca_cld", "rmnet", "rmnet_data", "rmnet_smd",
                    "qmi_wwan", "cdc_ether", "rndis_host", "usbnet", "cdc_ncm", "cdc_mbim",
                    "qcom_smd", "qcom_smd_rpm", "qcom_q6v5_mss", "rpmsg_wwan_ctrl", "bam_dmux"})
BINARIES = frozenset({"rild", "qmuxd", "netmgrd", "qmi_proxy", "wpa_supplicant", "hostapd",
                     "iw", "ip", "netcfg", "ndc", "ModemManager", "mmcli", "qmicli", "uqmi"})
LIBRARIES = frozenset({"libril.so", "libreference-ril.so", "libril-qc-qmi-1.so", "libqcril.so",
                      "libqmi.so", "libqmi_cci.so", "libqmi_client_qmux.so", "libqmi_common_so.so"})
FIRMWARE = frozenset({"wlan", "WCNSS_qcom_wlan_nv.bin", "WCNSS_cfg.dat", "wcnss.mdt", "wcnss.b00",
                     "wcnss.b01", "wcnss.b02", "fw_bcmdhd.bin", "fw_bcm40181a2.bin",
                     "fw_bcm4330.bin", "fw_bcm43438a1.bin", "rtl8189es", "rtl8189fs"})
APPS = frozenset({"Mms.apk", "TeleService.apk", "Phone.apk", "TelephonyProvider.apk"})
NET = r"(?:lo|(?:wlan|usb|rndis|eth|wwan|p2p|rmnet|rmnet_usb|rmnet_data|rmnet_sdio)[0-9]{1,2})"
SDIO = r"mmc[0-9]:[0-9a-f]{4}:[0-7]"
NODE = r"(?:diag|qmi|(?:smd|smdcntl|smdpkt|ttyUSB|ttyACM|cdc-wdm)[0-9]{1,2}|wwan[0-9]{1,2}(?:at|qmi|mbim)[0-9]{1,2})"
FILES = frozenset({"/system/build.prop", "/proc/version", "/proc/meminfo", "/proc/modules",
                   "/sys/devices/soc0/soc_id", "/sys/devices/soc0/family",
                   "/proc/device-tree/model", "/proc/device-tree/compatible",
                   "/sys/class/block/mmcblk0/size", "/sys/class/block/mmcblk0/device/name",
                   "/sys/class/block/mmcblk0/queue/logical_block_size",
                   "/sys/class/android_usb/android0/idVendor", "/sys/class/android_usb/android0/idProduct",
                   "/sys/class/android_usb/android0/functions", "/sys/class/android_usb/android0/enable",
                   "/sys/class/android_usb/android0/state"})
DIRS = frozenset({"/sys/class/net", "/sys/class/block", "/sys/class/ieee80211",
                  "/sys/bus/sdio/devices", "/sys/module", "/dev", "/system/bin", "/system/xbin",
                  "/system/lib", "/system/vendor/lib", "/system/lib/modules", "/system/vendor/modules",
                  "/system/etc/firmware", "/system/vendor/firmware", "/system/etc/firmware/wlan",
                  "/system/vendor/firmware/wlan", "/system/app", "/system/priv-app"})


def allowed_file(path):
    return isinstance(path, str) and (path in FILES or any(re.fullmatch(pattern, path) for pattern in (
        rf"/sys/class/net/{NET}/(?:type|operstate|device/uevent|phy80211/name)",
        r"/sys/class/block/mmcblk0p[1-9][0-9]{0,2}/(?:start|size)",
        rf"/sys/bus/sdio/devices/{SDIO}/(?:vendor|device|uevent)",
    )))


def keep_entry(path, name):
    if path == "/sys/class/net":
        return bool(re.fullmatch(NET, name))
    if path == "/sys/class/block":
        return bool(re.fullmatch(r"mmcblk0p[1-9][0-9]{0,2}", name))
    if path == "/sys/class/ieee80211":
        return bool(re.fullmatch(r"phy[0-9]{1,2}", name))
    if path == "/sys/bus/sdio/devices":
        return bool(re.fullmatch(SDIO, name))
    if path == "/dev":
        return bool(re.fullmatch(NODE, name))
    if path == "/sys/module":
        return name in MODULES
    if path.endswith(("/bin", "/xbin")):
        return name in BINARIES
    if path.endswith("/lib"):
        return name in LIBRARIES
    if path.endswith("/modules"):
        return name in {n + ".ko" for n in MODULES}
    if path.endswith(("/app", "/priv-app")):
        return name in APPS
    return name in FIRMWARE


class AuditTransport:
    def __init__(self, transport, *, cancel=None, sync=None, max_bytes=2 * 1024 * 1024, max_seconds=90):
        self.sync = sync or SyncReader(transport, timeout=5)
        self.cancel = cancel or threading.Event()
        self.max_bytes, self.bytes_read, self.requests = max_bytes, 0, 0
        self.deadline = time.monotonic() + max_seconds

    def is_set(self):
        # SyncReader checks this on every socket receive, including handshakes.
        # A peer that drips bytes must not bypass the overall audit deadline.
        if time.monotonic() > self.deadline:
            raise SafetyError("AUDIT_LIMIT")
        return self.cancel.is_set()

    def begin(self):
        if self.is_set():
            raise Cancelled()
        if self.requests >= 256:
            raise SafetyError("AUDIT_LIMIT")
        self.requests += 1

    def exact(self, sock, length):
        if time.monotonic() > self.deadline or self.requests > 256:
            raise SafetyError("AUDIT_LIMIT")
        if self.bytes_read + length > self.max_bytes:
            raise SafetyError("AUDIT_LIMIT")
        data = self.sync.exact(sock, length, self)
        self.bytes_read += len(data)
        return data

    def read(self, path):
        if not allowed_file(path):
            raise SafetyError("AUDIT_PATH_REJECTED")
        self.begin()
        data = bytearray()
        with self.sync.session(self) as sock:
            self.sync.request(sock, b"RECV", path)
            while True:
                kind, size = struct.unpack("<4sI", self.exact(sock, 8))
                if kind == b"FAIL":
                    raise SafetyError("AUDIT_READ_UNAVAILABLE")
                if kind == b"DONE":
                    if size:
                        raise SafetyError("SYNC_PROTOCOL")
                    return bytes(data)
                if kind != b"DATA" or not 0 < size <= 65536 or len(data) + size > 65536:
                    raise SafetyError("SYNC_PROTOCOL")
                data.extend(self.exact(sock, size))

    def list(self, path):
        if path not in DIRS:
            raise SafetyError("AUDIT_PATH_REJECTED")
        self.begin()
        names, total = [], 0
        with self.sync.session(self) as sock:
            self.sync.request(sock, b"LIST", path)
            for _ in range(4097):
                kind = self.exact(sock, 4)
                if kind == b"FAIL":
                    raise SafetyError("AUDIT_READ_UNAVAILABLE")
                if kind not in (b"DENT", b"DONE"):
                    raise SafetyError("SYNC_PROTOCOL")
                fields = struct.unpack("<4I", self.exact(sock, 16))
                if kind == b"DONE":
                    if any(fields) or len(names) != len(set(names)):
                        raise SafetyError("SYNC_PROTOCOL")
                    return sorted(names)
                length = fields[3]
                total += length + 20
                if not 0 < length <= 255 or total > 256 * 1024:
                    raise SafetyError("SYNC_PROTOCOL")
                name = self.exact(sock, length).decode("ascii", errors="replace")
                if keep_entry(path, name):
                    names.append(name)
            raise SafetyError("AUDIT_LIMIT")
