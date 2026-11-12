# Kết quả kiểm thử — 2026-11-12

## Tổng hợp thực tế

| Hạng mục | Kết quả | Bằng chứng / phạm vi |
|---|---|---|
| Unit + integration Python | **PASS: 76 tests** | `python -m pytest -q`, Windows 10 x64, Python 3.14.7 |
| Python compile | **PASS** | `compileall` cho package và tests |
| JavaScript syntax | **PASS** | `node --check uz801_manager/static/app.js`; Node chỉ dùng trong kiểm tra phát triển |
| Dependency consistency | **PASS** | `pip check`: không có dependency hỏng |
| Build Windows onefile | **PASS** | PyInstaller 6.22.3; exe 18,758,631 byte |
| Self-test của executable | **PASS** | Assets HTML/CSS/JS, API auth, demo inspector, khóa flash, Tcl runtime 9.0.4 |
| HTTP server thật của executable | **PASS** | `scripts/smoke_exe.py`: GET localhost, assets, từ chối thiếu token và sai Host |
| UI trực quan / responsive / native folder picker | **NOT TESTED** | Đã thử dùng Computer Use nhưng bộ kiểm soát dừng do không xác định chắc chắn URL Windows; chưa xác nhận bố cục hoặc thao tác bằng trình duyệt |
| ADB trên USB thật | **NOT TESTED** | Không gọi ADB đọc thiết bị thật trong phiên triển khai |
| Backup eMMC thật 3.61 GiB | **NOT TESTED** | Tests dùng ảnh tổng hợp 2 MiB và subprocess mô phỏng |
| Driver/EDL/programmer thực tế | **NOT TESTED** | Inventory/tool được mock; không mở phiên Sahara/Firehose |
| Flash / erase / format / restore / reboot | **SKIP** | Không triển khai, không chạy; ngoài phạm vi được phép |
| Chứng nhận tương thích Debian V3.2 | **NOT TESTED** | Chưa có bằng chứng về firmware và biến thể board cụ thể |

Không còn test FAIL trong lần chạy cuối. Trong quá trình phát triển đã sửa lỗi rò kết nối SQLite trên Windows và chuẩn hóa buffer của GPT parser; các kiểm thử liên quan hiện PASS.

SHA-256 executable đã kiểm thử:

```text
5f7071deecb16f08d99076ed19ff04703840bad330ec593f7f49ffa7a140c6ea
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

## Tái chạy

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uz801_manager --self-test
.\.venv\Scripts\python.exe scripts\smoke_exe.py
```

Smoke executable cần không có instance manager khác đang mở, do ứng dụng chặn nhiều instance trên cùng tài khoản. Không cần thiết bị thật. CI Windows trong repository có thể tái dựng/test và xuất executable; kết quả CI phải được xem riêng, không suy ra từ kết quả local ở trên.
