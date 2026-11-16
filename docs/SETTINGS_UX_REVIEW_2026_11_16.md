# Rà soát trải nghiệm cài đặt — 16/11/2026

Phạm vi: Wi-Fi nhận/phát, SIM, nguồn Internet/dự phòng, quản trị LAN và bố cục
cài đặt LED. Chủ yêu cầu không dùng Computer Use; kiểm tra trình duyệt bằng
Playwright với Chrome headless và preview cục bộ có dữ liệu mô phỏng.

## Tham khảo mã nguồn mở

- [Tabler](https://github.com/tabler/tabler/tree/46bd1d781a964202dc9be180da866f1feed3ccf5),
  MIT: bố cục biểu mẫu, thanh mục cài đặt và phân cấp thông tin.
- [RaspAP](https://github.com/RaspAP/raspap-webgui/tree/b24c577602079a69243e0eacc4452c38e0c83875),
  GPL-3.0: tham khảo cách phân biệt Wi-Fi client, access point và cấu hình mạng.

Không sao chép mã nguồn RaspAP, không chạy installer, không thêm framework,
CDN hay tài nguyên tải từ bên ngoài. CSS/JS mới viết riêng cho Flask portal.
Giữ dock thophuongpro và bảng màu UFI Panel đã có.

## Lỗi và thay đổi

| Vấn đề trong mã cũ | Cách xử lý |
| --- | --- |
| `/setup` chỉ cho connect khi setup AP active, nhưng được giới thiệu là nơi đổi mọi Wi-Fi | Chọn transport theo trạng thái: station dùng API Wi-Fi hiện hữu; setup AP giữ nguyên durable handoff/reboot một lần. Backend vẫn kiểm tra lại vai trò thực tế. |
| Không có thông tin Wi-Fi đang nhận ngay trong màn cài đặt | Thêm tên mạng, vai trò, IPv4, sóng, TX/RX; không gọi TX/RX là tốc độ Internet. |
| Thông báo đổi mạng ở xa biểu mẫu | Phản hồi ngay cạnh nút kết nối; xác nhận trước chuyển mạng; hướng dẫn truy cập lại khi mất kết nối; không tự gửi lại POST. |
| Nhiều tầng điều hướng SIM/Wi-Fi khác nhau | Một thanh danh mục cài đặt, chỉ hiện backend có sẵn; mục con Wi-Fi giữ URL/anchor cũ. |
| Không biết vì sao nút hotspot/APN bị khóa | Hiện điều kiện thiếu: chưa cấu hình Wi-Fi USB, chưa đồng ý dùng SIM, đang thử hoặc đang dùng dữ liệu. |
| Hotspot cập nhật khóa mọi button, gồm header/đăng xuất | Chỉ khóa nút của hotspot; cập nhật nền không thay thông báo thao tác vừa làm. |
| Làm mới chính sách Internet xóa bản nháp không báo | Cần xác nhận bỏ bản nháp; mỗi chế độ có mô tả tác động; Chỉ Wi-Fi không giữ tích cho phép SIM. |
| Form mật khẩu LAN không khóa trong lúc lưu | Chặn gửi trùng, xóa mật khẩu khỏi ô sau gửi, báo nhập lại chưa khớp và đưa focus về ô đó; có nút đọc lại trạng thái. |
| Thông tin mật khẩu Wi-Fi đã hiện không có nút ẩn | Nút xem/ẩn, xóa nội dung khi ẩn; không đưa vào storage. |
| Giới hạn SSID tính ký tự thay vì byte ở giao diện | Chặn SSID UTF-8 vượt 32 byte trước POST; backend giữ nguyên kiểm tra. |

Không thay backend backup, firmware, cơ chế rollback mạng, consent dữ liệu SIM,
xác nhận hotspot 5 phút, khóa modem, Origin/Host/CSRF hoặc giới hạn quản trị LAN.
Chuyển mạng station giữ hành vi backend sẵn có; không tuyên bố có rollback mới.

## Kiểm thử

- Baseline: 468 PASS, 1 SKIP, exit 0.
- Sau sửa: 469 PASS, 1 SKIP, exit 0. Skip: tài khoản Windows không có quyền tạo
  symlink trong test đường dẫn website.
- Fixture JavaScript: AP handoff vẫn gửi đúng action/confirm; station dùng đúng
  API, hủy không gửi, SSID quá dài không gửi, ẩn xóa mật khẩu; chính sách giữ
  bản nháp khi hủy refresh và không cho bật SIM thiếu consent; LAN không gửi trùng.
- Chrome headless: 6 màn × 320/390/768/1280 px, không tràn ngang, không lỗi JS.
  Thử hủy/xác nhận kết nối, lỗi mật khẩu, mất kết nối không retry, giữ bản nháp
  AP/SSID qua polling, giữ APN qua polling, xem/ẩn credentials, lỗi xác nhận LAN.
- `--self-test`, `pip check`, Node syntax và `git diff --check`: exit 0.

Lặp lại kiểm tra trình duyệt bằng hai terminal:

```powershell
.venv\Scripts\python.exe scripts/preview_portal.py
python scripts/verify_settings_browser.py
```

Python chạy lệnh thứ hai cần Playwright và Chrome. Script chỉ dùng
`127.0.0.1:8771`; screenshot/report nằm trong `artifacts/settings-browser/`
được Git bỏ qua. Mọi dữ liệu là mẫu; các thao tác mạng được mock. Đây không phải
nghiệm thu điện thoại hay chuyển mạng thật.

## Cách dùng

Mở `/manage` để chọn nhóm cài đặt. Trong `/setup`, xem kết nối hiện tại trước;
nếu đã kết nối, mở “Chọn hoặc đổi mạng Wi-Fi” khi cần đổi. “Mạng đã lưu” không
yêu cầu nhập lại mật khẩu. “Mạng USB phát” đặt SSID/mật khẩu chung, chỉ dùng ở
lần phát tiếp theo. Mỗi nút đổi mạng có phần giải thích tác động và xác nhận.

`/internet` chọn nguồn Internet và dự phòng; `/hotspot` quản lý APN và phát Wi-Fi
từ SIM; `/modem/network` chọn sóng 3G/4G. Mật khẩu quản trị LAN đổi qua USB ở
`/manage` → Truy cập quản trị. Mật khẩu này khác mật khẩu mạng Wi-Fi.

Kết quả triển khai thật, bản sao lưu và CI được ghi trong `SESSION_HANDOFF.md`.
