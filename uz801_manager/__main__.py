import argparse
import json
import secrets
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from .adb import ADB
from .demo import DemoADB
from .errors import SafetyError
from .storage import FileLock, data_directory
from .web import create_app


def main():
    parser = argparse.ArgumentParser(description="UZ801 OpenStick Manager — read-only localhost")
    parser.add_argument("--demo", action="store_true", help="Mô phỏng; không truy cập thiết bị thật")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--self-test", action="store_true", help="Kiểm tra gói ứng dụng; không truy cập USB")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be 1024–65535")
    if args.self_test:
        import tkinter
        tcl_version = tkinter.Tcl().eval("info patchlevel")
        with tempfile.TemporaryDirectory(prefix="uz801-selftest-") as directory:
            app = create_app(directory=directory, adb=DemoADB(delay=0), demo=True)
            with app.test_client() as client:
                base = "http://127.0.0.1:8765"
                assert client.get("/", base_url=base).status_code == 200
                assert client.get("/static/app.js", base_url=base).status_code == 200
                assert client.get("/static/app.css", base_url=base).status_code == 200
                assert client.get("/api/state", base_url=base).status_code == 403
                headers = {"X-UZ801-Token": app.extensions["uz801"]["token"], "Origin": base}
                assert client.post("/api/inspect", json={"consent": True}, base_url=base, headers=headers).status_code == 202
                app.extensions["uz801"]["jobs"].thread.join(5)
                response = client.get("/api/state", base_url=base, headers=headers).get_json()
                assert len(response["device"]["partitions"]) == 27
                assert response["readiness"]["flash_enabled"] is False
            print(json.dumps({"packaged_assets": "PASS", "api": "PASS", "demo_inspector": "PASS",
                              "tcl_runtime": tcl_version, "hardware": "NOT_TESTED"}))
        return 0
    directory = args.data_dir or (data_directory() / ("demo" if args.demo else "runtime"))
    # Global per-user lock also covers instances started with different data directories/ports.
    lock = FileLock(data_directory() / "application.lock")
    try:
        lock.acquire()
    except SafetyError:
        print("UZ801 Manager is already running. Close the existing instance first.", file=sys.stderr)
        return 1
    app = None
    try:
        token = secrets.token_urlsafe(32)
        app = create_app(directory=directory, adb=DemoADB() if args.demo else ADB(),
                         port=args.port, token=token, demo=args.demo)
        app.extensions["uz801"]["jobs"].recover_interrupted()
        from waitress import create_server
        server = create_server(app, host="127.0.0.1", port=args.port, threads=6,
                               max_request_body_size=8192, clear_untrusted_proxy_headers=True)
        url = f"http://127.0.0.1:{args.port}/#token={token}"
        print("UZ801 OpenStick Manager — READ ONLY" if sys.stdout.encoding.lower().startswith("utf") else "UZ801 OpenStick Manager - READ ONLY")
        print("Demo: " + str(args.demo))
        print("Open this local session URL (keep it private):\n" + url)
        print("Press Ctrl+C in this window to stop safely.")
        if not args.no_browser:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            server.run()
        finally:
            server.close()
    except KeyboardInterrupt:
        pass
    except OSError:
        print("Cannot start local server or access data directory.", file=sys.stderr)
        return 1
    finally:
        if app:
            app.extensions["uz801"]["jobs"].shutdown()
        lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
