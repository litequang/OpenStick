# Phase 00 — Hybrid Mode baseline audit

Ngày kiểm tra: 2026-11-12 (Asia/Saigon). Phạm vi nhiệm vụ dừng sau Phase 04. Không triển khai mạng, SMS/USSD, EDL hoặc thay firmware.

## Baseline và phạm vi review

- HEAD ban đầu: `232fb377334c07cabf3f0ec19dc300e1b9eadcf3`, branch `main`, working tree sạch.
- Origin: `https://github.com/litequang/OpenStick.git`; fetch và đối chiếu tag v0.1.1, target đúng HEAD trên. [Release v0.1.1](https://github.com/litequang/OpenStick/releases/tag/v0.1.1) là prerelease.
- Branch làm việc mới: `codex/hybrid-v2-feasibility`. Không sửa/merge main, không tạo release trong nhiệm vụ này.
- Đã đọc toàn bộ các module Python hiện có trong `uz801_manager`, HTML/CSS/JS, toàn bộ 9 tệp test baseline, launcher, spec, build/package/smoke scripts, pyproject, lockfile và workflow CI trước khi sửa sản phẩm.

## Kiến trúc và kết luận audit

| Thành phần | Cơ chế đang có | Kết luận / giới hạn |
|---|---|---|
| Windows launcher | Python/EXE, Waitress 127.0.0.1, khóa ứng dụng theo tài khoản | Không đọc USB tại startup; chỉ loopback Windows, không phải localhost của máy khác |
| Web/API | Token, Host/Origin/Fetch-Site, JSON POST, CSP, textContent | Không có API remote command hoặc ghi firmware; audit mới phải dùng cùng guard và Jobs |
| ADB | Chỉ một transport; identity HMAC nội bộ từ CID/boot ID; exec-out probe tổng hợp | Không phải chứng thực chống thiết bị độc hại; dữ liệu inspector cũ không phải bộ lọc xuất công khai tổng quát |
| ADB SYNC | RECV/LIST, packet <=64 KiB, size/DONE, timeout/cancel | Binary-safe, không PTY; không seek. Không mở rộng allowlist backup để phục vụ audit mạng |
| Backup | Full raw + 10 sidecar trích từ raw, fsync/hash/readback, giữ bản dở | Không thay đổi thuật toán đã thử trên USB; full backup không phải snapshot nguyên tử |
| GPT | MBR, CRC header/array, bounds, overlap, GUID/name duplicate, hai bản GPT | Primary-only inspection được phân biệt với full verifier; sentinel MBR FFFFFFFF được cảnh báo, không dùng làm dung lượng |
| Verifier | Hash/size đủ file, cả hai GPT, sidecar khớp raw | PASS là toàn vẹn cấu trúc/tệp, không phải chứng nhận restore; manifest không ký số |
| EDL inspector | Windows PnP + CLI help + kiểm tra tệp programmer cục bộ | Không chứng minh Sahara/Firehose. Không gọi inspector EDL hoặc programmer trong audit Hybrid này |
| History/locking | SQLite, một worker, OS lock, error code cố định | Audit mới phải không chồng tác vụ backup; không lưu raw stdout hoặc identifiers vào history |
| Demo | Ảnh giả lập 2 MiB, không USB | Báo cáo fixture phải đánh dấu demo rõ, không trở thành hardware VERIFIED |
| UI native picker | Tk dialog chọn thư mục | Người dùng đã xác nhận ở v0.1.1; chưa coi là kiểm thử UI mới của branch này |

Điểm ghi nhận chưa sửa: ADB host bị ghim 127.0.0.1:5037; nếu daemon chưa chạy có thể trả ADB_FAILED. Không tự restart daemon/USB hoặc thay driver trong Compatibility Audit. Mã baseline dùng các executable cục bộ do người dùng cấu hình; không chứng thực executable tùy ý. Đây là mô hình tin cậy máy tính cục bộ, không phải sandbox chống malware.

Các số đo model/board Android không xác định được PCB, DTB Linux, driver hoặc modem firmware. Driver/node xuất hiện trên Android không chứng minh API userspace Debian có thể dùng nó.

## Kiểm thử baseline thực chạy

Môi trường: Windows 10 x64 build 19045, Python 3.14.7, PyInstaller 6.22.3; Tcl 9.0.4 trong EXE hiện tại. `requires-python >=3.11` là khai báo hỗ trợ, chưa chạy ma trận Python 3.11/3.12/3.13 hoặc máy Windows sạch trong nhiệm vụ này.

| Lệnh/kiểm tra | Exit code | Kết quả |
|---|---:|---|
| `.venv/Scripts/python.exe -m pytest -q` | 0 | 111 passed, 4.76 s |
| `python -m pip check` | 0 | No broken requirements |
| `python scripts/smoke_exe.py` | 0 | Frozen self-test, HTTP/assets, token/Host guards PASS; không USB |
| `node --check uz801_manager/static/app.js` | 0 | Syntax PASS |
| `python -m compileall -q uz801_manager tests` | 0 | PASS |

EXE baseline vẫn chạy được trên máy hiện tại. Bản build audit sẽ được kiểm tra riêng cuối Phase 04; kết quả baseline không thay cho kiểm tra branch mới.

## Backup đã tồn tại — không chỉnh sửa

Đọc metadata của bản full thật gần nhất: `source=adb-live`, `status=complete`, 3.875.536.896 byte eMMC, 11 ảnh (raw + 10 sidecar), 27 phân vùng. Báo cáo lưu sẵn: SHA-256 PASS, GPT PASS, readback PASS, `critical_content=REVIEW_REQUIRED` vì `fsc`, `restore_test=NOT_TESTED`, `flash_ready=false`.

Phase 00 chỉ ghi nhận kết quả lưu sẵn, chưa gọi đó là phép verify lại trong audit này. Phase 03 sẽ gọi verifier **chỉ đọc tệp**, không dùng endpoint `/api/verify` vì endpoint đó ghi lại verification.json. Chụp size/mtime của mọi tệp backup vào artifacts riêng để đối chiếu cuối nhiệm vụ. Không đưa manifest, hash firmware riêng, raw image hoặc identifiers vào commit.

Thêm ignore `/BACKUP/` ở cấp repository vì ignore cũ chủ yếu che ảnh/manifest/log nhưng không che mọi report/checksum trong thư mục người dùng tạo. Đây là thay đổi bảo vệ dữ liệu trên host, không sửa tệp backup hoặc cơ chế backup.

## Hướng triển khai Phase 01

Module audit riêng, allowlist đọc metadata và LIST directory, không shell/PTY, không mở device node modem, không gọi RIL/QMI/AT, không đọc SMS/calibration/SIM identifiers. Chỉ xuất field đã parse/giới hạn; giá trị không nhận diện được giữ UNVERIFIED hoặc BLOCKED. Tách trạng thái observation Android khỏi khả năng Linux và luôn giữ device deployment NO-GO khi recovery/driver chưa được chứng minh.
