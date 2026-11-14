import hmac
import secrets
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .adb import ADB
from .backup import BackupManager, verify_backup
from .compatibility import CompatibilityAuditor, report_markdown, validate_report
from .edl import EDLInspector, readiness
from .errors import SafetyError, message
from .storage import Jobs, atomic_json, data_directory, local_directory


def create_app(*, directory=None, adb=None, edl=None, auditor=None, port=8765, token=None, demo=False):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=8192, JSON_AS_ASCII=False)
    token = token or secrets.token_urlsafe(32)
    authority = f"127.0.0.1:{port}"
    origin = f"http://{authority}"
    jobs = Jobs(directory or data_directory())
    adb = adb or ADB()
    edl = edl or EDLInspector()
    backup = BackupManager(adb)
    auditor = auditor or CompatibilityAuditor(adb, demo=demo)
    state = {"device": None, "edl": None, "compatibility": None, "last_checked": None, "connection_error": None}
    picker_lock = threading.Lock()
    app.extensions["uz801"] = {"jobs": jobs, "token": token, "state": state, "origin": origin}

    @app.before_request
    def guard():
        if request.host != authority or request.remote_addr not in ("127.0.0.1", None):
            return jsonify(code="HOST_REJECTED"), 403
        if request.headers.get("Origin") not in (None, origin):
            return jsonify(code="ORIGIN_REJECTED"), 403
        if request.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
            return jsonify(code="ORIGIN_REJECTED"), 403
        if request.path.startswith("/api/"):
            supplied = request.headers.get("X-UZ801-Token", "")
            if not hmac.compare_digest(supplied.encode(), token.encode()):
                return jsonify(code="AUTH_REQUIRED", message="Mở ứng dụng bằng launcher để nhận phiên truy cập."), 403
            if request.method != "GET":
                if request.headers.get("Origin") != origin or request.mimetype != "application/json":
                    return jsonify(code="CSRF_REJECTED"), 403

    @app.after_request
    def headers(response):
        response.headers.update({
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
            "Cross-Origin-Resource-Policy": "same-origin",
        })
        return response

    @app.errorhandler(SafetyError)
    def safe_error(exc):
        return jsonify(code=exc.code, message=message(exc.code)), 409 if exc.code == "BUSY" else 400

    @app.errorhandler(Exception)
    def unknown_error(exc):
        if isinstance(exc, HTTPException):
            return jsonify(code="HTTP_ERROR", message="Yêu cầu không được hỗ trợ."), exc.code
        code = "IO_ERROR" if isinstance(exc, OSError) else "INTERNAL_ERROR"
        return jsonify(code=code, message=message(code)), 500

    def body():
        value = request.get_json()
        if not isinstance(value, dict):
            raise SafetyError("INPUT_INVALID")
        return value

    def consent(value):
        if value.get("consent") is not True:
            raise SafetyError("CONSENT_REQUIRED")

    @app.get("/")
    def home():
        return render_template("index.html", demo=demo)

    @app.get("/api/state")
    def status():
        snapshot = state["device"]
        return jsonify(device=snapshot.public() if snapshot else None, edl=state["edl"],
                       compatibility=state["compatibility"],
                       last_checked=state["last_checked"], connection_error=state["connection_error"],
                       jobs=jobs.history(), readiness=readiness(), demo=demo,
                       adb_found=bool(adb.executable), default_folder=str(Path.home()))

    @app.post("/api/inspect")
    def inspect():
        consent(body())
        def work(cancel, update):
            state["device"] = None
            state["connection_error"] = None
            try:
                snapshot = adb.inspect()
                state["device"] = snapshot
                state["last_checked"] = time.time()
                return {"message": "Đã đọc thông tin thiết bị.", "backup_error": snapshot.backup_error}
            except SafetyError as exc:
                state["connection_error"] = message(exc.code)
                state["last_checked"] = time.time()
                raise
        return jsonify(job_id=jobs.start("inspect", work)), 202

    @app.post("/api/backup")
    def start_backup():
        value = body()
        consent(value)
        if value.get("backup_approved") is not True:
            raise SafetyError("BACKUP_CONSENT_REQUIRED")
        snapshot = state["device"]
        if not snapshot:
            raise SafetyError("INSPECT_REQUIRED")
        if snapshot.backup_error:
            raise SafetyError(snapshot.backup_error)
        folder = str(local_directory(value.get("folder")))
        mode = value.get("mode", "full")
        if mode not in ("full", "critical"):
            raise SafetyError("INPUT_INVALID")
        return jsonify(job_id=jobs.start("backup", lambda cancel, update: backup.create(snapshot, folder, mode, cancel, update))), 202

    @app.post("/api/compatibility")
    def compatibility():
        value = body()
        consent(value)
        if set(value) != {"consent"}:
            raise SafetyError("INPUT_INVALID")
        def work(cancel, update):
            state["compatibility"] = None
            report = auditor.inspect(cancel)
            validate_report(report)
            state["compatibility"] = report
            return {"message": "Audit chỉ đọc đã kết thúc; xem bằng chứng và phần chưa xác minh.",
                    "audit_status": report["status"]}
        return jsonify(job_id=jobs.start("compatibility", work)), 202

    @app.get("/api/compatibility/report")
    def compatibility_report():
        report = state["compatibility"]
        if report is None:
            raise SafetyError("AUDIT_REQUIRED")
        validate_report(report)
        format_ = request.args.get("format", "json")
        if format_ not in ("json", "md"):
            raise SafetyError("INPUT_INVALID")
        response = jsonify(report) if format_ == "json" else Response(report_markdown(report), content_type="text/markdown; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="openstick-compatibility.{format_}"'
        return response

    @app.post("/api/verify")
    def verify():
        value = body()
        folder = str(local_directory(value.get("folder")))
        def work(cancel, update):
            result = verify_backup(folder, cancel, update)
            atomic_json(Path(folder) / "verification.json", result)
            return {"folder": folder, "verification": result, "message": "Đã xác minh tệp cục bộ."}
        return jsonify(job_id=jobs.start("verify", work)), 202

    @app.post("/api/edl")
    def inspect_edl():
        value = body()
        consent(value)
        if demo:
            def work(cancel, update):
                state["edl"] = {"edl_detected": False, "driver_status": "NOT_TESTED", "devices": [],
                                "tool": {"status": "NOT_TESTED"}, "programmer": {"compatibility": "UNKNOWN"},
                                "recovery_verified": False, "guidance": "Chế độ mô phỏng không quét USB/EDL thật."}
                return {"message": "Mô phỏng: không gọi EDL thật."}
        else:
            programmer = value.get("programmer")
            if programmer is not None and not isinstance(programmer, str):
                raise SafetyError("INPUT_INVALID")
            def work(cancel, update):
                state["edl"] = edl.inspect(programmer or None)
                return {"message": "Đã kiểm tra USB/driver và công cụ cục bộ. Recovery chưa được chứng minh."}
        return jsonify(job_id=jobs.start("edl", work)), 202

    @app.post("/api/cancel")
    def cancel():
        value = body()
        if not isinstance(value.get("job_id"), str):
            raise SafetyError("INPUT_INVALID")
        return jsonify(cancel_requested=jobs.cancel(value["job_id"]))

    @app.post("/api/pick")
    def pick():
        value = body()
        kind = value.get("kind", "directory")
        if kind not in ("directory", "programmer"):
            raise SafetyError("INPUT_INVALID")
        if not picker_lock.acquire(blocking=False):
            raise SafetyError("BUSY")
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                if kind == "directory":
                    selected = filedialog.askdirectory(parent=root, title="Chọn thư mục UZ801", mustexist=True)
                else:
                    selected = filedialog.askopenfilename(parent=root, title="Chọn programmer để kiểm tra tệp (không chạy)", filetypes=[("Programmer", "*.mbn *.elf *.bin")])
                return jsonify(path=selected or "")
            finally:
                root.destroy()
        finally:
            picker_lock.release()

    return app
