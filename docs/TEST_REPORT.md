# Kết quả kiểm thử v0.1.1 — 2026-11-12

## Tổng hợp thực tế

| Hạng mục | Kết quả | Bằng chứng / phạm vi |
|---|---|---|
| Unit + integration Python | **PASS: 111 tests** | Giữ 76 test baseline, thêm 35 regression; Windows 10 x64, Python 3.14.7 |
| Python compile | **PASS** | `compileall` cho package và tests |
| JavaScript syntax | **PASS** | `node --check uz801_manager/static/app.js`; Node chỉ dùng trong kiểm tra phát triển |
| Dependency consistency | **PASS** | `pip check`: không có dependency hỏng |
| Build Windows onefile | **PASS** | PyInstaller 6.22.3; exe 18,770,372 byte |
| Self-test của executable | **PASS** | Assets HTML/CSS/JS, API auth, demo inspector, khóa flash, Tcl runtime 9.0.4 |
| HTTP server thật của executable | **PASS** | `scripts/smoke_exe.py`: GET localhost, assets, từ chối thiếu token và sai Host |
| UI demo / responsive / native folder picker | **PASS — người dùng xác nhận trực tiếp** | Windows 127.0.0.1:8765, Edge; dashboard 27 phân vùng, thu hẹp cửa sổ và chọn thư mục. Computer Use capture timeout; không có screenshot automation PASS |
| ADB trên USB thật | **PASS phạm vi nhỏ** | MSM8916, XINYH, root, CID/boot ID, GPT chính + 27 phân vùng khớp sysfs; mẫu SYNC binary-safe lặp giống nhau |
| exec-out trên firmware thật | **UNAVAILABLE — đã xử lý** | Android 4.4.4 trả error: closed; fallback SYNC v1 hoạt động, không PTY |
| GPT dự phòng thật | **NOT TESTED** | SYNC không seek; hoãn tới full backup được cho phép riêng |
| Backup eMMC thật 3.61 GiB | **NOT TESTED** | Tests dùng ảnh tổng hợp 2 MiB và subprocess mô phỏng |
| Driver/EDL/programmer thực tế | **NOT TESTED** | Inventory/tool được mock; không mở phiên Sahara/Firehose |
| Flash / erase / format / restore / reboot | **SKIP** | Không triển khai, không chạy; ngoài phạm vi được phép |
| Chứng nhận tương thích Debian V3.2 | **NOT TESTED** | Chưa có bằng chứng về firmware và biến thể board cụ thể |

Không còn test FAIL trong lần chạy cuối. v0.1.1 sửa uname không có trên firmware, exec-out không hỗ trợ, nhận diện sentinel protective MBR thực tế và thêm consent backup riêng. Xem [bằng chứng USB và hướng dẫn UI](HARDWARE_VALIDATION_v0.1.1.md). Bộ test mới không dùng firmware thật hoặc identifiers của người dùng.

SHA-256 executable v0.1.1 đã kiểm thử (đối chiếu SHA256SUMS.txt của release):

```text
cdacaa5b6e4be02bbded7171feef32fd073217c3e4e0bd2135afab0ef696bbcc
```

## Các tình huống bắt buộc

| Tình huống | Kết quả | Test đại diện |
|---|---|---|
| ADB không kết nối | PASS | `test_disconnected` |
| ADB kết nối thành công | PASS | `test_connected`, `test_actual_inspector_parser_root_and_privacy` |
| Không có root | PASS | `test_actual_inspector_no_root`, `test_no_root_blocks_before_output` |
| USB ngắt giữa backup | PASS (mô phỏng) | `test_incomplete_stream_never_complete[disconnect]`, binary exit error |
| Backup thiếu byte | PASS | `test_binary_errors`, `test_short_file` |
| SHA-256 không khớp | PASS | `test_hash_mismatch` |
| GPT hỏng | PASS | GPT header/table/secondary CRC, geometry sai dù CRC đúng |
| Ổ đĩa đầy | PASS (mô phỏng) | preflight và lỗi OSError giữa stream |
| Thiết bị bị thay thế | PASS (mô phỏng) | `test_swap_device`, `test_replaced_transport_rejected` |
| EDL thiếu driver | PASS (mô phỏng) | `test_edl_no_driver` |
| EDL báo lỗi / timeout | PASS (mô phỏng) | `test_edl_tool_error`, `test_edl_inventory_error` |
| Hai tác vụ đồng thời | PASS | `test_two_jobs_and_two_managers_block` với Windows file lock |

Ngoài ra: hủy luồng bị treo, bảo toàn mọi giá trị byte 00–FF, remote exit trailer, không lộ stderr/CID/serial, traversal/UNC/device paths, CSRF/Origin/Host, không có API lệnh ghi, backup/verify HTTP end-to-end, thiếu sidecar, sidecar không khớp raw dù hash manifest đã cập nhật, history interrupted và đóng database.

Regression v0.1.1: SYNC smart socket/transport pin, header/payload chia nhỏ, mọi byte 00–FF, thiếu DONE dù đủ payload, thiếu/thừa byte, FAIL không lộ nội dung, packet quá lớn/rỗng/không hợp lệ, cancel/timeout, path allowlist, giới hạn metadata, LIST/duplicate, root/kernel không shell, GPT primary-only không bỏ kiểm tra secondary trong full image, sentinel MBR giới hạn đúng giá trị, critical-only khóa khi thiếu secondary, full backup qua parser SYNC thật với ảnh tổng hợp, disk write error phân biệt USB error, consent backup riêng phải là boolean true.

## Tái chạy

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uz801_manager --self-test
.\.venv\Scripts\python.exe scripts\smoke_exe.py
```

Smoke executable cần không có instance manager khác đang mở, do ứng dụng chặn nhiều instance trên cùng tài khoản. Không cần thiết bị thật. CI Windows tái dựng/test, kiểm tra dependency/JS syntax, chạy frozen HTTP smoke và xuất executable. Baseline v0.1.0 main/tag đều success; trạng thái commit v0.1.1 được báo cùng SHA khi bàn giao, không suy ra từ local tests.
