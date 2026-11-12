import copy
import json
import struct
import subprocess
import threading
from pathlib import Path

import jsonschema
import pytest

from uz801_manager.adb import ADB
from uz801_manager.audit_transport import AuditTransport, FILES, DIRS, allowed_file, keep_entry
from uz801_manager.compatibility import CompatibilityAuditor, KEYS, STATIC_UNKNOWN, report_markdown, validate_report
from uz801_manager.errors import SafetyError
from uz801_manager.web import create_app
from test_adb_sync import reader, packet, dent

BASE = "http://127.0.0.1:8765"
SECRET = "867530900001234"
SCHEMA = json.loads((Path(__file__).parents[1] / "uz801_manager/schemas/hardware-audit.schema.json").read_text())


class FakeTransport:
    def __init__(self, transport, *, cancel=None):
        assert transport == "4"
        self.cancel = cancel
        self.bytes_read = self.requests = 0
        self.trace = []
        self.files = {
            "/system/build.prop": b"ro.product.model=UZ801\nro.product.name=msm8916_32_512\nro.product.board=ALK\nro.board.platform=msm8916\nro.build.version.release=4.4.4\nril.imei=" + SECRET.encode() + b"\nsubscriberid=001019999999999\n",
            "/proc/version": b"Linux version 3.10.28 (private-user@private-host)\n",
            "/proc/meminfo": b"MemTotal: 397824 kB\n",
            "/sys/class/block/mmcblk0/size": b"7569408\n",
            "/sys/class/block/mmcblk0/queue/logical_block_size": b"512\n",
            "/sys/class/block/mmcblk0/device/name": b"XINYH\n",
            "/sys/class/block/mmcblk0p1/start": b"131072",
            "/sys/class/block/mmcblk0p1/size": b"131072",
            "/sys/class/net/wlan0/device/uevent": b"DRIVER=8189fs\nIMEI=" + SECRET.encode(),
            "/sys/class/net/wlan0/operstate": b"up",
            "/sys/class/android_usb/android0/functions": b"rndis,adb," + SECRET.encode(),
            "/sys/class/android_usb/android0/idVendor": b"05c6",
            "/sys/class/android_usb/android0/idProduct": b"90b6",
            "/sys/class/android_usb/android0/enable": b"1",
            "/sys/class/android_usb/android0/state": b"CONFIGURED",
            "/proc/modules": b"8189fs 123 0 - Live 0x00000000\nprivate-module 0 0\n",
        }
        self.dirs = {"/sys/class/net": ["wlan0", "rmnet0"], "/sys/class/block": ["mmcblk0p1"],
                     "/sys/module": ["8189fs", "qmi_wwan"], "/dev": ["smd11", "diag"],
                     "/system/bin": ["rild", "wpa_supplicant"], "/system/lib": ["libril-qc-qmi-1.so"],
                     "/system/app": ["Mms.apk"]}

    def read(self, path):
        assert allowed_file(path)
        self.trace.append(("RECV", path))
        self.requests += 1
        if path not in self.files:
            raise SafetyError("AUDIT_READ_UNAVAILABLE")
        value = self.files[path]
        self.bytes_read += len(value)
        return value

    def list(self, path):
        assert path in DIRS
        self.trace.append(("LIST", path))
        self.requests += 1
        return self.dirs.get(path, [])


def audit(factory=FakeTransport, changed=False):
    calls = []
    def run(args, **kwargs):
        assert args == ["fake", "-H", "127.0.0.1", "-P", "5037", "devices", "-l"]
        assert kwargs["shell"] is False
        calls.append(args)
        tid = 5 if changed and len(calls) > 1 else 4
        return subprocess.CompletedProcess(args, 0, f"{SECRET} device transport_id:{tid}\n".encode(), b"")
    report = CompatibilityAuditor(ADB("fake", run=run), transport_factory=factory).inspect()
    jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(report)
    return report


def test_android_observation_does_not_prove_linux_capabilities():
    report = audit()
    assert report["session"] == "VERIFIED"
    assert report["status"] == "UNVERIFIED" and report["deployment"] == "NO_GO"
    rows = {r["key"]: r for r in report["observations"]}
    assert rows["android_identity"]["status"] == "VERIFIED"
    assert "driver=8189fs" in rows["wifi_components"]["facts"]
    for key in STATIC_UNKNOWN:
        assert rows[key]["status"] == "UNVERIFIED"
    assert report["flash_enabled"] is False


def test_no_identifiers_or_raw_build_error_exported():
    report = audit()
    for text in (json.dumps(report), report_markdown(report)):
        for private in (SECRET, "001019999999999", "private-user", "private-host", "private-module"):
            assert private not in text


def test_sensitive_value_in_allowlisted_property_is_suppressed():
    def factory(*a, **k):
        t = FakeTransport(*a, **k)
        t.files["/system/build.prop"] = b"ro.product.model=" + SECRET.encode()
        return t
    report = audit(factory)
    assert SECRET not in json.dumps(report)
    assert next(r for r in report["observations"] if r["key"] == "android_identity")["status"] == "UNVERIFIED"


def test_linux_v3_dtb_string_does_not_certify_physical_v32():
    def factory(*a, **k):
        t = FakeTransport(*a, **k)
        t.files["/proc/device-tree/compatible"] = b"yiming,uz801-v3\0qcom,msm8916\0"
        return t
    rows = {r["key"]: r for r in audit(factory)["observations"]}
    assert "yiming,uz801-v3" in rows["device_tree"]["facts"]
    assert rows["device_tree"]["status"] == "VERIFIED"
    assert rows["physical_board"]["status"] == "UNVERIFIED"


def test_no_device_has_no_verified_observations():
    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, b"List of devices attached\n", b"")
    report = CompatibilityAuditor(ADB("fake", run=run)).inspect()
    assert report["status"] == "BLOCKED"
    assert report["issues"][-1]["code"] == "NO_DEVICE"
    assert not any(r["status"] == "VERIFIED" for r in report["observations"])


@pytest.mark.parametrize("code", ["STREAM_FAILED", "STREAM_TIMEOUT", "SYNC_PROTOCOL", "AUDIT_LIMIT"])
def test_disconnect_or_incomplete_snapshot_is_never_verified(code):
    def factory(*a, **k):
        t = FakeTransport(*a, **k)
        def broken(path):
            raise SafetyError(code)
        t.list = broken
        return t
    report = audit(factory)
    assert report["status"] == report["session"] == "BLOCKED"
    assert not any(r["status"] == "VERIFIED" for r in report["observations"])


def test_replaced_transport_downgrades_all_observations():
    report = audit(changed=True)
    assert report["issues"][-1]["code"] == "DEVICE_CHANGED"
    assert report["status"] == "BLOCKED"
    assert all(r["status"] == "UNVERIFIED" for r in report["observations"])


def test_demo_never_opens_transport_or_claims_hardware_verified():
    def forbidden(*a, **k):
        pytest.fail("demo must not open USB")
    report = CompatibilityAuditor(transport_factory=forbidden, demo=True).inspect()
    assert report["source"] == "demo"
    assert all(r["status"] == "UNVERIFIED" for r in report["observations"])
    validate_report(report)
    jsonschema.validate(report, SCHEMA)


@pytest.mark.parametrize("path", ["/dev/smd11", "/dev/diag", "/dev/cdc-wdm0", "/dev/block/mmcblk0",
    "/dev/block/mmcblk0p13", "/data/data/com.android.providers.telephony/databases/mmssms.db",
    "/proc/cmdline", "/proc/cpuinfo", "/sys/class/net/wlan0/address", "/sys/devices/soc0/serial_number",
    "/sys/class/net/wlan0/../address", "/system/build.prop;reboot", "/data/misc/wifi/wpa_supplicant.conf"])
def test_sensitive_and_mutating_paths_blocked_before_connection(path):
    sync, sock = reader(b"")
    t = AuditTransport("42", sync=sync)
    with pytest.raises(SafetyError, match="AUDIT_PATH_REJECTED"):
        t.read(path)
    assert not sock.sent


@pytest.mark.parametrize("path", ["/data", "/dev/block", "/proc/1", "/system/bin;reboot"])
def test_list_allowlist(path):
    sync, sock = reader(b"")
    with pytest.raises(SafetyError, match="AUDIT_PATH_REJECTED"):
        AuditTransport("42", sync=sync).list(path)
    assert not sock.sent


def test_wire_requests_are_only_recv_list_and_preserve_split_payload():
    sync, sock = reader(packet(b"DATA", b"Linux version 3.10.28\n") + packet(b"DONE"))
    t = AuditTransport("42", sync=sync)
    assert t.read("/proc/version") == b"Linux version 3.10.28\n"
    assert sock.sent[-1] == packet(b"RECV", b"/proc/version")
    sync, sock = reader(dent(b"smd11") + dent(SECRET.encode()) + dent(b"mmssms.db") + b"DONE" + bytes(16))
    assert AuditTransport("42", sync=sync).list("/dev") == ["smd11"]
    assert sock.sent[-1] == packet(b"LIST", b"/dev")


@pytest.mark.parametrize("data,error", [(packet(b"DATA", b"partial"), "STREAM_FAILED"),
    (b"DATA" + struct.pack("<I", 65537), "SYNC_PROTOCOL"),
    (packet(b"FAIL", SECRET.encode()), "AUDIT_READ_UNAVAILABLE"), (packet(b"DONE", b"x"), "SYNC_PROTOCOL")])
def test_partial_and_malformed_sync_responses(data, error):
    sync, _ = reader(data)
    with pytest.raises(SafetyError, match="^" + error + "$"):
        AuditTransport("42", sync=sync).read("/proc/version")


def test_aggregate_budget_stops_read():
    sync, _ = reader(packet(b"DATA", b"abc") + packet(b"DONE"))
    with pytest.raises(SafetyError, match="AUDIT_LIMIT"):
        AuditTransport("42", sync=sync, max_bytes=8).read("/proc/version")


def test_cancel_is_honored():
    event = threading.Event()
    event.set()
    sync, _ = reader(packet(b"DONE"))
    with pytest.raises(SafetyError, match="CANCELLED"):
        AuditTransport("42", sync=sync, cancel=event).read("/proc/version")


@pytest.mark.parametrize("exhaustion", ["deadline", "requests"])
def test_budget_exhaustion_stops_before_new_connection(exhaustion):
    sync, sock = reader(packet(b"DONE"))
    transport = AuditTransport("42", sync=sync)
    if exhaustion == "deadline":
        transport.deadline = 0
    else:
        transport.requests = 256
    with pytest.raises(SafetyError, match="AUDIT_LIMIT"):
        transport.read("/proc/version")
    assert not sock.sent


def test_deadline_checked_while_payload_drips(monkeypatch):
    sync, sock = reader(packet(b"DATA", b"abc") + packet(b"DONE"))
    transport = AuditTransport("42", sync=sync)
    original = sock.recv
    count = 0
    def slow_receive(size):
        nonlocal count
        count += 1
        if count == 10:
            transport.deadline = 0
        return original(min(size, 1))
    monkeypatch.setattr(sock, "recv", slow_receive)
    with pytest.raises(SafetyError, match="AUDIT_LIMIT"):
        transport.read("/proc/version")


def test_empty_metadata_does_not_become_verified():
    def factory(*a, **k):
        t = FakeTransport(*a, **k)
        t.files = dict.fromkeys(t.files, b"")
        t.dirs = {}
        return t
    report = audit(factory)
    assert all(r["status"] == "UNVERIFIED" for r in report["observations"])


def test_schema_rejects_extra_private_fields_and_unlock():
    report = audit()
    private = copy.deepcopy(report)
    private["imei"] = SECRET
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(private, SCHEMA)
    with pytest.raises(SafetyError):
        validate_report(private)
    report["flash_enabled"] = True
    with pytest.raises(SafetyError):
        validate_report(report)


def test_ui_audit_consent_exports_and_guards(tmp_path):
    app = create_app(directory=tmp_path, demo=True, token="test")
    headers = {"X-UZ801-Token": "test", "Origin": BASE}
    with app.test_client() as client:
        assert client.get("/api/compatibility/report", base_url=BASE).status_code == 403
        assert client.get("/api/compatibility/report", base_url=BASE, headers=headers).status_code == 400
        assert client.post("/api/compatibility", base_url=BASE, headers=headers, json={"consent": False}).status_code == 400
        assert client.post("/api/compatibility", base_url=BASE, headers=headers, json={"consent": True, "command": "send sms"}).status_code == 400
        assert client.post("/api/compatibility", base_url=BASE, headers={**headers, "Origin": "http://evil.example"}, json={"consent": True}).status_code == 403
        assert client.post("/api/compatibility", base_url=BASE, headers=headers, json={"consent": True}).status_code == 202
        app.extensions["uz801"]["jobs"].thread.join(5)
        result = client.get("/api/compatibility/report?format=json", base_url=BASE, headers=headers)
        assert result.status_code == 200
        jsonschema.validate(result.get_json(), SCHEMA)
        markdown = client.get("/api/compatibility/report?format=md", base_url=BASE, headers=headers)
        assert markdown.status_code == 200 and b"NO-GO" in markdown.data
        assert client.get("/api/compatibility/report?format=../../private", base_url=BASE, headers=headers).status_code == 400
        assert b"audit-consent" in client.get("/", base_url=BASE).data
    app.extensions["uz801"]["jobs"].shutdown()
