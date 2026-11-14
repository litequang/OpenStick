"""Evidence collector, not a Linux compatibility certification or network manager."""
import re
import threading
from datetime import datetime, timezone

from .adb import ADB
from .audit_transport import AuditTransport, MODULES, DIRS, allowed_file
from .errors import Cancelled, SafetyError

STATUSES = {"VERIFIED", "UNVERIFIED", "BLOCKED"}
KEYS = {
    "android_identity": "Thuộc tính Android", "physical_board": "Board vật lý",
    "kernel": "Kernel đang chạy", "device_tree": "Device tree đang chạy",
    "memory": "RAM và eMMC", "partition_layout": "Layout kernel",
    "usb_gadget": "USB gadget hiện tại", "network_interfaces": "Giao diện mạng hiện có",
    "wifi_components": "Thành phần Wi-Fi", "modem_components": "Thành phần modem",
    "userspace": "Userspace hiện có", "modem_firmware": "Tương thích modem firmware",
    "wifi_sta": "Wi-Fi Client hoạt động", "wifi_ap": "Wi-Fi AP capability (ngoài phạm vi triển khai)",
    "usb_uplink": "Internet vào USB", "lte_data": "LTE Data hoạt động",
    "sms": "SMS backend hoạt động", "ussd": "USSD backend hoạt động",
}
CODES = {"AUDIT_READ_UNAVAILABLE", "AUDIT_DATA_INVALID", "AUDIT_LIMIT", "SYNC_PROTOCOL",
         "STREAM_FAILED", "STREAM_TIMEOUT", "SYNC_UNAVAILABLE", "ADB_NOT_FOUND", "ADB_FAILED",
         "ADB_TIMEOUT", "NO_DEVICE", "MULTIPLE_DEVICES", "TRANSPORT_UNSUPPORTED", "DEVICE_CHANGED",
         "AUDIT_FAILED"}
LIMITATIONS = [
    "VERIFIED chỉ xác nhận quan sát Android hiện tại, không chứng nhận chức năng Debian/V3.2.",
    "Không đọc SIM identifiers, SMS, MAC/IP/SSID, credentials hoặc dữ liệu calibration; không mở modem nodes.",
    "Chỉ parse thuộc tính build allowlist; không lưu/xuất build.prop hoặc lỗi remote nguyên bản.",
    "Không gửi AT/QMI/RIL, SMS/USSD, không bật data, không thay route/Wi-Fi/USB hoặc thử failover.",
    "Không phát hiện thành phần không có nghĩa phần cứng không hỗ trợ; lỗi đọc có thể là thiếu file/quyền.",
    "Board vật lý, firmware/DTB Linux và recovery chưa được xác minh; triển khai lên thiết bị NO-GO.",
]
STATIC_UNKNOWN = {
    "physical_board": "Chưa đối chiếu PCB vật lý; tên Android không xác minh V3.2.",
    "modem_firmware": "Không đọc modem/calibration image; chưa đối chiếu hash firmware với kernel Linux mục tiêu.",
    "wifi_sta": "Không association/scan/connect; interface hoặc driver không chứng minh STA hoạt động.",
    "wifi_ap": "Không thử AP; hotspot nằm ngoài mục tiêu sản phẩm.",
    "usb_uplink": "RNDIS/gadget hiện diện không chứng minh USB nhận Internet từ Windows; không đổi ICS/route.",
    "lte_data": "Không kích hoạt bearer/mobile data hoặc thử lưu lượng.",
    "sms": "Chỉ nhận diện ứng viên backend; không mở channel, đọc nội dung hoặc gửi SMS.",
    "ussd": "Chưa chứng minh backend/vendor/network hỗ trợ; không tạo session USSD.",
}
WIFI_MODULES = {"wlan", "8189es", "8189fs", "rtl8189es", "rtl8189fs", "bcmdhd", "dhd",
                "cfg80211", "mac80211", "ath6kl_sdio", "ath10k_sdio", "ath10k_core", "wcn36xx",
                "wcnss_core", "qcom_wcnss", "qca_cld"}


def empty_report(source):
    return {"schema_version": 1, "source": source,
            "created_utc": datetime.now(timezone.utc).isoformat(), "status": "UNVERIFIED",
            "session": "UNVERIFIED", "deployment": "NO_GO", "flash_enabled": False,
            "observations": [], "issues": [], "limits": list(LIMITATIONS),
            "read_bytes": 0, "requests": 0}


def token_set(value, choices):
    # Only emit canonical vocabulary, never substrings of arbitrary device output.
    return sorted(set(value.split()) & set(choices))


def number(value, maximum):
    if not re.fullmatch(r"[0-9]{1,16}", value) or not 0 < int(value) <= maximum:
        raise SafetyError("AUDIT_DATA_INVALID")
    return int(value)


class CompatibilityAuditor:
    def __init__(self, adb=None, *, transport_factory=AuditTransport, demo=False):
        self.adb, self.transport_factory, self.demo = adb or ADB(), transport_factory, demo

    def inspect(self, cancel=None):
        cancel = cancel or threading.Event()
        report = empty_report("demo" if self.demo else "android-live")

        def add(key, facts=(), sources=(), verified=False):
            report["observations"].append({"key": key,
                "status": "VERIFIED" if verified and not self.demo else "UNVERIFIED",
                "facts": list(facts), "sources": list(sources)})

        for key, text in STATIC_UNKNOWN.items():
            add(key, [text])
        if self.demo:
            for key in KEYS.keys() - STATIC_UNKNOWN.keys():
                add(key, ["Mô phỏng: không đọc thiết bị; chưa có bằng chứng hardware."])
            return report

        transport = None
        try:
            connection = self.adb.connection()  # serial stays in memory, never exported
            transport = self.transport_factory(connection[1], cancel=cancel)

            def optional(path, listing=False):
                try:
                    if cancel.is_set():
                        raise Cancelled()
                    value = transport.list(path) if listing else transport.read(path)
                    if listing:
                        return value
                    return value.decode("utf-8", errors="strict").strip()
                except UnicodeDecodeError:
                    report["issues"].append({"source": path, "code": "AUDIT_DATA_INVALID"})
                    return ""
                except SafetyError as exc:
                    if exc.code != "AUDIT_READ_UNAVAILABLE":
                        raise
                    report["issues"].append({"source": path, "code": exc.code})
                    return [] if listing else ""

            def numeric(path, maximum):
                value = optional(path)
                if not value:
                    return None
                try:
                    return number(value, maximum)
                except SafetyError:
                    report["issues"].append({"source": path, "code": "AUDIT_DATA_INVALID"})
                    return None

            build = optional("/system/build.prop")
            props = dict(line.split("=", 1) for line in build.splitlines()
                         if "=" in line and not line.lstrip().startswith("#"))
            accepted = {"ro.product.model": {"UZ801"}, "ro.product.name": {"msm8916_32_512"},
                        "ro.product.board": {"ALK", "msm8916", "UZ801", "FY_UZ801_V3.2"},
                        "ro.board.platform": {"msm8916"}, "ro.build.version.release": {"4.4.4"}}
            identity = [f"{key}={props[key]}" for key, values in accepted.items() if props.get(key) in values]
            add("android_identity", identity or ["Không có giá trị nhận diện nằm trong allowlist."],
                ["/system/build.prop"], len(identity) == len(accepted))
            del build, props
            kernel = optional("/proc/version")
            match = re.match(r"Linux version ([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,3})(?:[\s+-]|$)", kernel)
            add("kernel", ["release=" + match[1]] if match else ["Không đọc được release hợp lệ."],
                ["/proc/version"], bool(match))

            dt = []
            for path in ("/proc/device-tree/model", "/proc/device-tree/compatible"):
                value = optional(path).replace("\0", " ")
                candidates = {"qcom,msm8916", "qcom,msm8916-mtp", "qcom,msm8916-qrd",
                              "yiming,uz801-v3", "thwc,uf896", "thwc,ufi001c"}
                dt.extend(token_set(value, candidates))
            add("device_tree", sorted(set(dt)) or ["DTB/model không được nhận diện; không suy đoán từ SoC."],
                ["/proc/device-tree/model", "/proc/device-tree/compatible"], bool(dt))

            ram = optional("/proc/meminfo")
            match = re.search(r"^MemTotal:\s+([0-9]{1,9})\s+kB\s*$", ram, re.M)
            sectors = numeric("/sys/class/block/mmcblk0/size", 2**40)
            logical = numeric("/sys/class/block/mmcblk0/queue/logical_block_size", 65536)
            name = optional("/sys/class/block/mmcblk0/device/name")
            memory = ([f"ram_kb={int(match[1])}"] if match else [])
            if sectors:
                memory.extend([f"sectors_512={sectors}", f"emmc_bytes={sectors * 512}"])
            if logical:
                memory.append(f"logical_sector={logical}")
            if name in {"XINYH"}:
                memory.append("emmc_name=" + name)
            add("memory", memory, ["/proc/meminfo", "/sys/class/block/mmcblk0/size",
                                   "/sys/class/block/mmcblk0/device/name"], bool(match and sectors and logical))
            layout = []
            names = optional("/sys/class/block", True)
            for name in names:
                start = numeric(f"/sys/class/block/{name}/start", 2**40)
                size = numeric(f"/sys/class/block/{name}/size", 2**40)
                if start and size and sectors and start + size <= sectors:
                    layout.append(f"{name}:start={start},sectors={size}")
            add("partition_layout", layout, ["/sys/class/block"], bool(names and len(layout) == len(names)))

            usb = []
            base = "/sys/class/android_usb/android0/"
            for field in ("idVendor", "idProduct"):
                value = optional(base + field)
                if re.fullmatch(r"[0-9a-fA-F]{4}", value):
                    usb.append(field + "=" + value.lower())
            functions = optional(base + "functions").replace(",", " ")
            usb.extend("function=" + x for x in token_set(functions,
                {"adb", "rndis", "diag", "serial_smd", "rmnet", "acm", "mtp", "ptp", "mass_storage"}))
            enabled = optional(base + "enable")
            if enabled in {"0", "1"}:
                usb.append("enabled=" + enabled)
            state = optional(base + "state")
            if state in {"CONNECTED", "CONFIGURED", "DISCONNECTED"}:
                usb.append("state=" + state)
            add("usb_gadget", usb, [base + "functions", base + "idVendor", base + "idProduct"], bool(usb))

            interfaces = optional("/sys/class/net", True)
            network, drivers = [], set()
            for name in interfaces:
                network.append("interface=" + name)
                state = optional(f"/sys/class/net/{name}/operstate")
                if state in {"up", "down", "unknown", "dormant", "lowerlayerdown", "notpresent", "testing"}:
                    network.append(name + ":operstate=" + state)
                events = optional(f"/sys/class/net/{name}/device/uevent")
                for line in events.splitlines():
                    if line.startswith("DRIVER=") and line[7:] in MODULES:
                        drivers.add(line[7:])
            add("network_interfaces", network, ["/sys/class/net"], bool(interfaces))

            modules = set(optional("/sys/module", True))
            for line in optional("/proc/modules").splitlines():
                parts = line.split()
                if parts and parts[0] in MODULES:
                    modules.add(parts[0])
            firmware, ko = set(), set()
            for path in ("/system/etc/firmware", "/system/vendor/firmware",
                         "/system/etc/firmware/wlan", "/system/vendor/firmware/wlan"):
                firmware.update(optional(path, True))
            for path in ("/system/lib/modules", "/system/vendor/modules"):
                ko.update(optional(path, True))
            wifi = ["module=" + n for n in sorted(modules & WIFI_MODULES)] + ["driver=" + n for n in sorted(drivers & WIFI_MODULES)]
            wifi += ["module_file=" + n for n in sorted(ko) if n.removesuffix(".ko") in WIFI_MODULES]
            wifi += ["firmware_entry=" + n for n in sorted(firmware)]
            wifi += ["wiphy=" + n for n in optional("/sys/class/ieee80211", True)]
            for dev in optional("/sys/bus/sdio/devices", True):
                values = []
                for field in ("vendor", "device"):
                    value = optional(f"/sys/bus/sdio/devices/{dev}/{field}")
                    if re.fullmatch(r"0x[0-9a-fA-F]{4}", value):
                        values.append(field + "=" + value.lower())
                if len(values) == 2:
                    wifi.append("SDIO:" + ",".join(values))
                for line in optional(f"/sys/bus/sdio/devices/{dev}/uevent").splitlines():
                    if line.startswith("DRIVER=") and line[7:] in WIFI_MODULES:
                        wifi.append("sdio_driver=" + line[7:])
            add("wifi_components", wifi, ["/sys/module", "/sys/class/ieee80211", "/sys/bus/sdio/devices"], bool(wifi))

            nodes = optional("/dev", True)
            modem = ["node=" + n for n in nodes] + ["module=" + n for n in sorted(modules - WIFI_MODULES)]
            add("modem_components", modem or ["Không thấy thành phần trong allowlist; không mở node."],
                ["/dev", "/sys/module"], bool(modem))
            userspace = []
            for path in ("/system/bin", "/system/xbin", "/system/lib", "/system/vendor/lib",
                         "/system/app", "/system/priv-app"):
                userspace += [path + "/" + n for n in optional(path, True)]
            add("userspace", userspace or ["Không thấy executable/library trong allowlist."],
                ["/system/bin", "/system/lib", "/system/app"], bool(userspace))
            if self.adb.connection() != connection:
                raise SafetyError("DEVICE_CHANGED")
            report["session"] = "VERIFIED"
        except Cancelled:
            raise
        except (SafetyError, OSError) as exc:
            code = exc.code if isinstance(exc, SafetyError) and exc.code in CODES else "AUDIT_FAILED"
            report["issues"].append({"source": "session", "code": code})
            report["status"] = report["session"] = "BLOCKED"
            for item in report["observations"]:
                item["status"] = "UNVERIFIED"  # incomplete/disconnected snapshot cannot be promoted
        finally:
            if transport:
                report["read_bytes"] = transport.bytes_read
                report["requests"] = transport.requests
        seen = {o["key"] for o in report["observations"]}
        for key in KEYS.keys() - seen:
            add(key, ["Chưa hoàn tất phép đọc."], verified=False)
        validate_report(report)
        return report


def validate_report(report):
    """Closed export envelope; no arbitrary extensions or raw dumps."""
    required = {"schema_version", "source", "created_utc", "status", "session", "deployment",
                "flash_enabled", "observations", "issues", "limits", "read_bytes", "requests"}
    if set(report) != required or report["schema_version"] != 1 or report["source"] not in {"android-live", "demo"}:
        raise SafetyError("AUDIT_DATA_INVALID")
    if report["deployment"] != "NO_GO" or report["flash_enabled"] is not False:
        raise SafetyError("AUDIT_DATA_INVALID")
    if report["status"] not in STATUSES or report["session"] not in STATUSES:
        raise SafetyError("AUDIT_DATA_INVALID")
    if report["status"] == "VERIFIED" or report["limits"] != LIMITATIONS:
        raise SafetyError("AUDIT_DATA_INVALID")
    if not re.fullmatch(r"[0-9T:.+\-Z]+", report["created_utc"]):
        raise SafetyError("AUDIT_DATA_INVALID")
    if type(report["read_bytes"]) is not int or not 0 <= report["read_bytes"] <= 2 * 1024 * 1024:
        raise SafetyError("AUDIT_DATA_INVALID")
    if type(report["requests"]) is not int or not 0 <= report["requests"] <= 256:
        raise SafetyError("AUDIT_DATA_INVALID")
    if len(report["observations"]) != len(KEYS) or {o["key"] for o in report["observations"]} != set(KEYS):
        raise SafetyError("AUDIT_DATA_INVALID")
    for item in report["observations"]:
        if set(item) != {"key", "status", "facts", "sources"} or item["status"] not in STATUSES:
            raise SafetyError("AUDIT_DATA_INVALID")
        if any(not isinstance(s, str) or len(s) > 240 or "\n" in s for s in item["facts"]):
            raise SafetyError("AUDIT_DATA_INVALID")
        if any(not (allowed_file(s) or s in DIRS) for s in item["sources"]):
            raise SafetyError("AUDIT_DATA_INVALID")
    for issue in report["issues"]:
        if set(issue) != {"source", "code"} or issue["code"] not in CODES:
            raise SafetyError("AUDIT_DATA_INVALID")
        if issue["source"] != "session" and not (allowed_file(issue["source"]) or issue["source"] in DIRS):
            raise SafetyError("AUDIT_DATA_INVALID")
    if report["source"] == "demo" and any(o["status"] == "VERIFIED" for o in report["observations"]):
        raise SafetyError("AUDIT_DATA_INVALID")


def report_markdown(report):
    validate_report(report)
    lines = ["# Compatibility Audit — chỉ đọc", "", f"Nguồn: {report['source']}; UTC: {report['created_utc']}",
             f"Trạng thái: {report['status']}; phiên: {report['session']}; triển khai: NO-GO", ""]
    for observation in report["observations"]:
        lines += [f"## {KEYS[observation['key']]} — {observation['status']}", ""]
        lines += ["- " + fact.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;") for fact in observation["facts"]]
        lines += ["", "Nguồn đọc: " + ", ".join(observation["sources"]), ""]
    lines += ["## Giới hạn", "", *["- " + s for s in report["limits"]], "", "## Phép đọc không hoàn tất", ""]
    lines += [f"- {i['source']}: {i['code']}" for i in report["issues"]]
    return "\n".join(lines) + "\n"
