"""Test the frozen Windows server over loopback without accessing real USB."""
import json
import argparse
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=Path(__file__).resolve().parents[1] / "dist/UZ801-OpenStick-Manager.exe")
    executable = parser.parse_args().exe.resolve()
    subprocess.run([str(executable), "--self-test"], check=True, timeout=60)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="uz801-exe-smoke-") as directory:
        proc = subprocess.Popen([str(executable), "--demo", "--no-browser", "--port", str(port), "--data-dir", directory],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 30
            while True:
                if proc.poll() is not None:
                    raise RuntimeError("Frozen server exited before startup")
                try:
                    with urllib.request.urlopen(base, timeout=1) as response:
                        html = response.read().decode("utf-8")
                        assert "CHẾ ĐỘ MÔ PHỎNG" in html
                        break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.2)
            for asset in ("/static/app.js", "/static/app.css"):
                with urllib.request.urlopen(base + asset, timeout=5) as response:
                    assert response.status == 200 and len(response.read()) > 1000
            try:
                urllib.request.urlopen(base + "/api/state", timeout=5)
                raise AssertionError("Unauthenticated request should be rejected")
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
            request = urllib.request.Request(base, headers={"Host": "evil.example"})
            try:
                urllib.request.urlopen(request, timeout=5)
                raise AssertionError("Unexpected Host should be rejected")
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
            print(json.dumps({"frozen_http_server": "PASS", "packaged_assets_http": "PASS", "auth_host_guards": "PASS", "real_usb": "NOT_TESTED"}))
        finally:
            # Kill only this test's process tree; PyInstaller onefile has a child process.
            if proc.poll() is None:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, check=True)
            proc.wait(timeout=10)


if __name__ == "__main__":
    main()
