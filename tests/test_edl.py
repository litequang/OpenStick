import subprocess

from uz801_manager.edl import EDLInspector, check_programmer, readiness, summarize_usb


def test_edl_no_driver():
    result = summarize_usb([{"PNPDeviceID": r"USB\VID_05C6&PID_9008\private-id", "ConfigManagerErrorCode": 28}])
    assert result["edl_detected"] is True
    assert result["driver_status"] == "FAIL"
    assert "private-id" not in str(result)


def test_edl_driver_success_is_not_recovery_proof():
    result = summarize_usb([{"PNPDeviceID": r"USB\VID_05C6&PID_9008\private", "ConfigManagerErrorCode": 0, "Service": "WinUSB"}])
    assert result["driver_status"] == "PASS"
    assert result["devices"][0]["communication"] == "NOT_TESTED"
    assert readiness()["flash_enabled"] is False


def test_edl_tool_error(tmp_path):
    tool = tmp_path / "edl.exe"
    tool.touch()
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, b"", b"private sensitive error")
    result = EDLInspector(run=run, executable=str(tool), windows=True).tool_check()
    assert result["status"] == "FAIL"
    assert calls[0][1:] == ["--help"]
    assert "private" not in str(result)


def test_edl_inventory_error():
    def run(*a, **k):
        raise subprocess.TimeoutExpired("private", 30)
    result = EDLInspector(run=run, executable="missing", windows=True).inspect()
    assert result["driver_status"] == "FAIL"
    assert result["recovery_verified"] is False


def test_programmer_never_assumed_compatible(tmp_path):
    path = tmp_path / "prog_emmc_firehose_8916.mbn"
    path.write_bytes(b"\x7fELFfake")
    result = check_programmer(str(path))
    assert result["format"] == "ELF"
    assert result["compatibility"] == "UNKNOWN"
    assert result["executed"] is False
