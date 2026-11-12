import subprocess

import pytest

from uz801_manager.adb import ADB
from uz801_manager.errors import SafetyError


def runner(output, code=0):
    def run(args, **kwargs):
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(args, code, output, b"private error")
    return run


def test_disconnected():
    with pytest.raises(SafetyError, match="NO_DEVICE"):
        ADB("adb", run=runner(b"List of devices attached\n")).connection()


def test_connected():
    adb = ADB("adb", run=runner(b"List of devices attached\nsample device product:x transport_id:4\n"))
    assert adb.connection() == ("sample", "4")


def test_multiple_devices():
    with pytest.raises(SafetyError, match="MULTIPLE_DEVICES"):
        ADB("adb", run=runner(b"a device transport_id:1\nb device transport_id:2")).connection()


def test_old_host_adb_rejected():
    with pytest.raises(SafetyError, match="TRANSPORT_UNSUPPORTED"):
        ADB("adb", run=runner(b"a device product:x")).connection()


def test_raw_stderr_not_disclosed():
    with pytest.raises(SafetyError, match="^ADB_FAILED$"):
        ADB("adb", run=runner(b"", 1)).connection()


def test_shell_key_and_transport_injection_rejected():
    adb = ADB("adb", run=lambda *a, **k: pytest.fail("must not execute"))
    for transport, key in [("1; reboot", "model"), ("1", "model; reboot")]:
        with pytest.raises(SafetyError, match="INPUT_INVALID"):
            adb._read(transport, key)
