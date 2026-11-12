# UZ801 OpenStick Manager

Ứng dụng Windows quản lý UZ801 theo nguyên tắc **chỉ đọc thiết bị**. Bản 0.1.0 triển khai Phase 1–3: kiểm tra ADB/GPT, sao lưu eMMC, xác minh tệp và kiểm tra EDL thụ động. **Không có flash, erase, restore, reboot, đổi driver hay thay đổi IMEI.**

## Chạy ngay trên Windows

Tải executable tại [GitHub Releases của litequang/OpenStick](https://github.com/litequang/OpenStick/releases). Bản đầu được đánh dấu prerelease vì chưa kiểm thử trên USB thật.

Mở `dist/UZ801-OpenStick-Manager.exe` hoặc `run.bat`. Ứng dụng mở trình duyệt tại `127.0.0.1:8765`. Giữ cửa sổ chương trình mở; dùng Ctrl+C để dừng an toàn. Bản `.exe` kèm Python và giao diện, không cần Node.js. ADB/EDL không được đóng gói hoặc tự tải xuống.

1. Tích ô cho phép đọc và bấm **Kiểm tra USB**. Chỉ kết nối một thiết bị ADB sẵn sàng. Có thể bật tự kiểm tra mỗi 30 giây.
2. Chọn thư mục máy tính, chọn **Toàn bộ eMMC + phân vùng quan trọng**, rồi bấm **Bắt đầu sao lưu**. Không cần nhập lệnh Linux.
3. Xem kết quả xác minh; có thể kiểm tra lại bằng thư mục chứa `manifest.json`.

Mở bản mô phỏng không truy cập USB:

```powershell
.\dist\UZ801-OpenStick-Manager.exe --demo
```

Mỗi phiên có token riêng trong liên kết mở trình duyệt, được chuyển vào sessionStorage và xóa khỏi thanh địa chỉ. Không chia sẻ liên kết phiên. Không mở bằng địa chỉ LAN/`localhost`; backend chỉ phục vụ `127.0.0.1`. Đóng ứng dụng trước khi chạy bản demo hoặc một phiên khác.

## Điều kiện backup ADB

- Tìm ADB tại `C:\adb\adb.exe`, tiếp theo trong PATH; có thể đặt biến môi trường `UZ801_ADB` tới executable tin cậy.
- Host ADB phải cung cấp `transport_id`; thiết bị phải sẵn có `uid=0`. Ứng dụng không chạy `adb root`, `su`, cài APK hoặc sửa hệ thống.
- Thiết bị phải hỗ trợ `exec-out`, các lệnh đọc `cat`/`dd`, CID eMMC và boot ID. **Khả năng exec-out trên Android 4.4.4 thực tế chưa được kiểm thử**. Nếu không hỗ trợ, ứng dụng dừng; không chuyển sang PTY hoặc PowerShell redirection có thể làm hỏng dữ liệu.
- GPT chính, GPT dự phòng và dữ liệu sysfs phải khớp. Số phân vùng tham chiếu là 27; vị trí được lấy từ GPT, không dùng số phân vùng hardcode để đọc.
- Thư mục đích phải tồn tại trên ổ cục bộ, không phải UNC, ổ mạng ánh xạ hoặc liên kết. Cần dung lượng cho toàn bộ ảnh + các tệp phân vùng riêng + 128 MiB dự phòng (khoảng 7–8 GiB cho cấu hình đã mô tả).

## Dữ liệu được tạo

Mỗi lần sao lưu tạo thư mục mới `backup-<UTC>-<random>`:

```text
manifest.json       Trạng thái, layout, kích thước, SHA-256 và nguồn dữ liệu
emmc.img            Chỉ có trong chế độ full; toàn bộ user area mmcblk0
pNNN.img            Các phân vùng quan trọng theo chỉ số GPT thực tế
verification.json   Kết quả kiểm tra cuối cùng
report.txt          Báo cáo sao lưu
backup.log          Mốc thao tác và mã lỗi, không ghi CID/IMEI
*.part              Tệp dở dang, không được xem là backup hợp lệ
```

Chế độ phân vùng gồm `modemst1`, `modemst2`, `fsg`, `fsc`, `persist`, `sbl1`, `aboot`, `boot`, `system`, `userdata`. Chế độ full trích các tệp riêng từ ảnh raw đã lưu; chế độ critical đọc trực tiếp từng phân vùng. Critical-only không có ảnh GPT nhị phân nên kết quả GPT là `NOT_TESTED`.

`mmcblk0` không bao gồm eMMC boot0/boot1, RPMB, fuse hoặc một bản QCN xuất qua DIAG. Không tuyên bố đây là bản sao tất cả trạng thái phần cứng. Ứng dụng không truy cập RPMB.

Lịch sử SQLite nằm tại `%LOCALAPPDATA%\UZ801Manager\runtime` (demo nằm riêng ở `demo`). Có thể đổi thư mục lịch sử bằng `--data-dir`. Thư mục backup được chọn riêng trong giao diện. Dữ liệu backup chứa thông tin riêng tư, không đưa lên GitHub hoặc gửi công khai.

## Hiểu kết quả

| Kết quả | Ý nghĩa |
|---|---|
| PASS | Tệp đọc lại đúng kích thước/hash và các kiểm tra được báo đã đạt |
| REVIEW_REQUIRED | Ví dụ: dữ liệu hiệu chuẩn toàn 00/FF hoặc số phân vùng khác 27 |
| FAIL / failed | Tác vụ lỗi, thiếu byte, mất kết nối, GPT/hash sai… |
| NOT TESTED / NOT_TESTED | Chưa thực hiện phép kiểm tra đó |
| SKIP | Chủ động không chạy, ví dụ thao tác ghi firmware bị loại khỏi phạm vi |

**SHA-256 PASS không chứng minh backup live nhất quán, dữ liệu modem đúng ngữ nghĩa, firmware tương thích hoặc khôi phục sẽ thành công.** Manifest không có chữ ký; hash phát hiện hỏng tệp vô ý, không chống người sửa đồng thời tệp và manifest. Sao chép bản backup đã kiểm tra sang nơi lưu trữ riêng là bước bảo quản tiếp theo.

## EDL và recovery

Nút EDL đọc danh sách USB/PnP Windows, tìm `05C6:9008`, kiểm tra tình trạng driver và chạy duy nhất `edl.exe --help` nếu đã cài. Có thể cấu hình `UZ801_EDL` tới executable tin cậy. Không tải hoặc chạy programmer. Chọn `.mbn/.elf/.bin` chỉ để xem kích thước, dấu định dạng và SHA-256.

Programmer luôn là `UNKNOWN` khi chưa có bằng chứng phù hợp với đúng board, eMMC và khóa ký. Driver hoạt động không đồng nghĩa libusb/Firehose đã giao tiếp được. Backup EDL offline là phương án ưu tiên **sau khi** chứng minh đường recovery; bản này chưa có chức năng thực thi backup EDL.

Xem [hướng dẫn recovery](docs/RECOVERY.md), [báo cáo kỹ thuật](docs/TECHNICAL_REPORT.md), [kết quả kiểm thử](docs/TEST_REPORT.md) và [rủi ro còn lại](docs/RISKS.md).

## Phát triển và đóng gói

Python 3.11 trở lên. Đã xây dựng trên Windows 10 x64, Python 3.14.7.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uz801_manager --demo
.\build.ps1
.\.venv\Scripts\python.exe scripts\smoke_exe.py
```

`build.ps1` chạy tests, PyInstaller và self-test của executable. Để chỉ kiểm tra gói không chạm USB:

```powershell
.\dist\UZ801-OpenStick-Manager.exe --self-test
```

Phần mềm chưa ký số. Bản phát hành chỉ được kiểm chứng trên máy build này; Windows khác, ADB stock thật, programmer và quy trình khôi phục thật còn cần kiểm thử có sự cho phép.
