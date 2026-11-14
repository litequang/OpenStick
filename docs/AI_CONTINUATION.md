# Bàn giao cho AI tiếp theo — 14/11/2026

Đây là trạng thái phát triển trên USB thật, không chỉ là bản thiết kế giao
diện. Đọc tài liệu này trước khi sửa UI hoặc triển khai lại. Nhánh đang dùng:
`codex/uz801-v32-postmarketos`. Bản Windows v0.1.1 trong README là ứng dụng
backup cũ; panel Linux trên USB là luồng riêng.

## Yêu cầu đã thống nhất với chủ USB

- SMS gửi/nhận được bật theo khả năng modem/SIM; dữ liệu SIM mặc định tắt.
  Chỉ bật Internet SIM khi người dùng chọn, không tự cấp quyền dùng dữ liệu.
- SIM và mức sóng chung một icon; icon Wi-Fi thể hiện đang nhận hay phát.
- SMS giống ứng dụng điện thoại: danh sách hội thoại, màn hội thoại riêng,
  màn soạn mới riêng. Không nhúng form gửi SMS vào mọi màn.
- USSD cần phản hồi mới theo từng lần gửi, kể cả nội dung giống lần trước.
  Có nút nhanh `*101#`; không tự gửi lại khi chưa biết kết quả.
- Hotspot cài đặt phải độc lập với SIM/Internet. Điện thoại truy cập để nhập
  Wi-Fi; có cả nút quét/danh sách và nhập tay cho SSID ẩn. Chọn mạng chỉ điền
  tên, không đổi kết nối trước khi bấm Lưu.
- Luồng mới chủ USB yêu cầu: lưu cấu hình → khởi động lại một lần → thử các
  Wi-Fi đã lưu → chỉ phát hotspot nếu không nối được mạng nào. **Luồng reboot
  này chưa được triển khai trong snapshot hiện tại.**
- USB đã nối Wi-Fi có IP nội bộ thì vẫn quản trị được khi mạng mất Internet.
  Không chuyển sang hotspot chỉ vì kiểm tra Internet thất bại.
- Chủ USB muốn tiếp tục tối ưu giao diện từ GitHub và giữ bàn giao đủ chi tiết.

## Truy cập và môi trường

- Máy làm việc: Windows PowerShell, workspace `D:\CODE\USB`, Python trong
  `.venv`. Thiết bị: FY_UZ801 V3.2, postmarketOS v26.06/Alpine v3.24 ARM64,
  kernel `6.12.1-msm8916`, Wi-Fi wcn36xx, NetworkManager 1.52.2.
- USB: `http://172.16.42.1`, SSH `user@172.16.42.1`, sudo không tương tác.
  Không còn phụ thuộc máy công ty. Khóa máy công ty vẫn được giữ.
- Khóa SSH riêng máy nhà: `runtime/usb-ssh/manager_ed25519`; host pin:
  `runtime/usb-ssh/pmos_known_hosts`. Không đưa nội dung khóa lên chat/GitHub.
- SSH cần `-F NUL`, `BatchMode=yes`, `IdentitiesOnly=yes`, `IdentityAgent=none`,
  `StrictHostKeyChecking=yes`, đúng identity và known_hosts nêu trên.
- Package thật: `/opt/openstick/uz801_manager`. USB listener gắn `usb0:80`;
  LAN listener gắn wlan0, port 8765, mật khẩu quản trị có sẵn do chủ USB đặt.
- Hotspot setup dùng `192.168.8.1:8765/setup`. SSID/password riêng được sinh
  trên thiết bị, xem qua trang `/setup` hoặc thẻ kết nối. Không có password mặc định.
- Station dùng IP DHCP: đọc trạng thái/router, không hardcode IP nhà vào repo.
- Website `/var/www/openstick`, Nginx loopback 8080 và Tunnel đang được giữ lại.
  Không thêm panel quản trị/SMS vào public Tunnel.

## Bản đồ mã nguồn cho người sửa giao diện

| Luồng | Tệp chính |
|---|---|
| USB/LAN Flask và guard | `hosting.py`, `hosting_device.py`, `lan_device.py`, `lan_access.py` |
| Wi-Fi thường, HTML gốc | Chuỗi `HTML` và script `REMOTE` trong `hosting.py` |
| Header/dock/theme | `templates/portal_chrome.html`, `static/portal_nav.js`, `static/portal.css` |
| SMS | `templates/sms.html`, `static/sms.css`, `static/sms_conversations.js`, `sms_archive.py` |
| USSD/mạng SIM | `templates/modem.html`, `modem.py`, `modem_device.py`, `ussd_qmi.py` |
| Wi-Fi setup/fallback | `setup_ap.py`, `setup_web.py`, `templates/setup.html`, `static/setup.js` |
| Hotspot Internet SIM | `hotspot.py`, `hotspot_web.py`, `templates/hotspot.html` |
| Chính sách Internet | `network_policy.py`, `network_web.py`, `templates/internet.html`, `static/internet.js` |
| Tổng quan/site editor | `portal_metrics.py`, `templates/overview.html`, `static_site.py` |

Các đường dẫn trong bảng thuộc `uz801_manager/`. CSS/JS/templates là package
data; build EXE vẫn phải có đủ asset. Không thay Flask portal bằng Sites.

## Đã kiểm tra được

- Wi-Fi installer API từng kết nối được Wi-Fi nhà với đúng khóa, MAC ổn định,
  powersave tắt, timeout dài hơn. Chưa chứng minh chạy Wi-Fi lâu dài ổn định.
- SMS UI/SQLite archive/tombstone/xác minh xóa và chống gửi lại kết quả không
  rõ đã có. Agent không gửi SMS thật. Các fixture dùng tin giả.
- USSD backend typed GI/libqmi: 3 lần prototype, 4 lần production controller,
  2 lần API web thành công, kể cả cùng nội dung. Hai kết quả API còn nguyên sau
  job refresh status. Không công khai nội dung phản hồi hay số thuê bao.
- Thiết bị đã có `py3-gobject3` từ APK chính thức được xác minh chữ ký;
  libqmi/Qmi typelib/qmi-proxy có sẵn. Không dùng lệnh AT thô.
- Hotspot setup thực sự phát WPA2/CCMP; DHCP và firewall chạy. **Chủ USB đã xác
  nhận điện thoại đăng nhập vào được trang cài đặt.** Không bật dữ liệu SIM.
- Quét mới tìm 3 mạng, trở về AP sau khoảng 14 giây. Mạng không tồn tại trả về
  AP sau khoảng 33 giây. Chọn danh sách và nhập tay đều chờ bấm Lưu mới submit.
- Bộ test gần nhất: **374 passed, 1 skipped** (quyền symlink Windows), khoảng
  71 giây. Đây không phải chứng nhận tất cả chức năng phần cứng đã đạt.
- Current và saved radio mode đọc gần nhất đều `[12,8]`. Chủ USB tự chọn;
  không ghi đè bằng `[8,0]` từ tài liệu phiên cũ.

## Lỗi chặn cần ưu tiên

**AP → Wi-Fi nhà chưa thành công. Không báo là đã fix hoàn chỉnh.**

Key tính từ mật khẩu lưu trên Windows đã so sánh khớp PSK trong keyfile cũ,
không in mật khẩu/PSK ra log. Khi thử handoff, wpa_supplicant báo handshake/
WRONG_KEY nhưng kernel đồng thời có `hal_join ... err=-5`,
`hal_config_bss ... err=-5`, `hal_delete_sta_self ... err=7` và đôi khi kernel
warning. Không kết luận đơn giản là người dùng nhập sai mật khẩu.

Hai lỗi cần tách riêng:

1. AP không khởi tạo do PMF mặc định: đã xác định key AES-CMAC `alg=4`, index 4
   bị kernel EINVAL. Đặt `wifi-sec.pmf=1` trong profile **AP** giải quyết phát
   hotspot; đã sửa cả hai bộ sinh profile AP. Giữ WPA2/CCMP.
2. Nhận Wi-Fi sau AP: vẫn cần xử lý. Reload riêng wcn36xx không giải quyết.
   Thử tháo wcn36xx/btqcomsmd, stop/start riêng WCNSS remoteproc rồi nạp lại
   cũng timeout. Một reboot bình thường sau đó vẫn thấy HAL errors. Không
   tiếp tục lặp các thử nghiệm này như thể chưa làm.

Thử ép station PMF/RSN/CCMP với PSK được giữ lại vẫn timeout. Đã khôi phục
keyfile station từ backup trước thử nghiệm. **Cẩn thận:** `nmcli
connection modify` sau một lỗi auth có thể ghi lại profile khi secret trong
RAM đã bị NM bỏ, gây mất PSK trong keyfile. Chỉnh sửa qua file riêng root-600,
giữ backup và reload profile; không ghi đè khóa tốt bằng profile thiếu secret.
Backup keyfile trước thử nghiệm nằm dưới thư mục private nêu bên dưới.

`Network.active()` chỉ đọc UUID, có thể trả UUID cả khi NM đang configuring
(state 50). Auto fallback phải phân biệt state 100/DHCP với UUID đang thử,
nếu không vòng retry Wi-Fi sẽ ngăn AP tự cứu. Đây là điểm cần kiểm tra/sửa.

## Tiếp tục thực hiện

1. Đọc status hiện tại qua USB, pending setup intent, NM state/reason và log
   kernel có lọc; không in credentials/nội dung SMS/USSD.
2. Khôi phục keyfile tốt nếu một thử nghiệm làm mất secret. Giữ USB/SSH chạy.
3. Hoàn thành luồng reboot một lần do chủ USB chọn, có intent root-private,
   nhận diện boot cũ/mới, giới hạn thời gian thử station và fallback AP. Không
   tạo reboot loop; không reboot giữa SMS send/USSD đang hoạt động.
4. Trước khi phát AP, thử mạng mới rồi các profile đã lưu có thể truy cập.
   Nếu đã nối Wi-Fi có IP nội bộ thì giữ LAN admin dù Internet không có.
5. Kiểm tra thật: AP/điện thoại → Lưu Wi-Fi đúng → boot/STA có IP → LAN login;
   sai pass/SSID → AP cũ; reboot giữa intent; nhiều lần lặp. Không bật SIM data.
6. Cập nhật tài liệu với kết quả và trạng thái máy chính xác, deploy source
   khớp commit, push nhánh phát triển. Không gọi phần chưa thử là PASS.

## Triển khai/kiểm thử

`python -m pytest -q`, `node --check` các JS đã sửa, `python -m uz801_manager
--self-test`. Test synthetic setup nằm `tests/setup_ui_fixture.cjs`;
SMS/USSD/network có fixture và unit test riêng. Browser automation trên máy
này chưa sẵn sàng; không có chụp màn hình xác nhận độc lập.

Để sửa UI mà không cần USB: chạy `python scripts/preview_portal.py`, mở
`http://127.0.0.1:8771/modem/sms` hoặc `/setup`. Preview dùng tin nhắn, mạng
và số liệu giả, có banner MÔ PHỎNG; không SSH/đọc SIM/gửi SMS/đổi mạng thật.
Đây là công cụ xem giao diện, không thay thế kiểm thử luồng thật trên thiết bị.

Deploy package vào `/opt/openstick`, không xóa thư mục website/credential/NM.
OpenRC scripts trong `scripts/openrc`: wifi, lan, modem, hotspot, policy,
setup, setup-dhcp. `openstick-setup` ở default runlevel; **không** thêm DHCP
setup vào default, worker chỉ bật nó khi AP setup chạy. Listener LAN gắn
ifindex; nếu tạo lại wlan0 phải restart `openstick-lan` để bind lại.

Khóa dùng chung `/run/openstick/network.lock` và modem lock; không giữ modem
lock rồi gọi API web modem (worker API cũng cần cùng lock). Backup package và
keyfile: `/var/lib/openstick/deploy-backups/home-20261114/`. Dữ liệu evidence
và script cá nhân dưới ignored `runtime/usb-ssh/` chỉ có trên máy hiện tại.
AI trên máy khác cần chủ USB cấp cách truy cập riêng, không có khóa trong repo.

Trạng thái thiết bị ngay trước khi push: setup AP đang hoạt động, tự cứu bật,
không có setup intent đang chạy. Keyfile station đã được khôi phục; agent không
bật SIM data. Không tuyên bố USB đang kết nối Internet qua Wi-Fi ở mốc này.

RMTFS giữ RAM-shadow `-r`; không flash/erase/ghi NV, không đoán PIN/PUK.
SIM data failover, Internet sharing từ SIM, nhiệt/uptime và boot chỉ cắm sạc
chưa được xác minh đầu cuối. UI có thể được tối ưu độc lập nhưng phải giữ
token/Host/Origin guard, LAN auth, an toàn hiển thị text và trạng thái unknown.
