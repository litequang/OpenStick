# Bàn giao cho AI tiếp theo — 14/11/2026

**Bản mới nhất `272777e`:** đã cài LED theo trạng thái: chọn trạng thái rồi
phối ba màu tắt/sáng/nháy với thời gian riêng. Worker LED được supervise, đọc
metadata mỗi khoảng 3 giây, không đổi mạng hay probe SIM. Cấu hình cũ/baseline
được giữ; deployment không tự bật quy tắc mới. Đã thử driver thật đồng thời đỏ
sáng, xanh lá 200/800 ms, xanh dương 700/300 ms; lấy mẫu đủ hai pha, replay đạt,
sau đó khôi phục đèn/cấu hình chủ. Role thật lúc thử là offline; các role khác
được test bằng metadata giả, chưa nhận là thử chuyển mạng thật. Header/Tổng
quan giữ số liệu cũ trong lúc refresh/lỗi, có đánh dấu cũ; trạng thái ngắt mạng,
mất SIM và số 0 thật vẫn cập nhật. Ô sức khỏe eMMC không có dữ liệu được ẩn;
lượng ghi vẫn giữ. 436 tests pass / 1 skip. Xem phần đầu handoff và
`docs/LED_STATE_RULES_AND_DASHBOARD_2026_11_15.md`. Mới đọc USB: Wi-Fi/data đều
ngắt, không pending; không tự bật SIM theo các checkpoint cũ bên dưới.

**Tên quản trị trên Android đã xác nhận:** cấu hình DNS `5660c77` đã cài.
Android trước đó báo NXDOMAIN dù mDNS trên wlan0 trả đúng AP; đã thêm DNS
thường cho `openstick.local` vào dnsmasq hotspot. Chủ nối lại Wi-Fi và xác nhận
mở tên miền được. PC USB vẫn phân giải/mở cùng tên HTTP 200; probe SIM vẫn đạt.
Hotspot hiện AP/data bật, enabled=true, không pending. Script DHCP setup cũng
đã có DNS nội bộ, mới kiểm tra cú pháp/tham số thật, chưa bật setup để thử bằng
điện thoại. Không restart NM/reboot/nối lại WWAN. Xem phần đầu handoff và
`docs/LOCAL_MANAGEMENT_ADDRESS.md`; kiểm tra lại trạng thái trước thay đổi.

**Cập nhật LED/SIM:** USB đã cài source đến `3bd728a`. Đèn vỏ đỏ/xanh lá/xanh
dương có mục `/settings/leds`, đã thử driver bật/nháy rồi khôi phục; boot replay
đã bật nhưng chưa thử reboot riêng. APN hiện rõ tại `/hotspot#sim-apn`, có nút
lưu riêng không bật data hay đổi mật khẩu Wi-Fi. APN tự nhận đã truy cập HTTPS
204 qua SIM trong lượt thử thật. Lỗi probe cũ đọc sai DNS dạng `A | B` đã sửa;
probe mới buộc cả DNS/HTTPS qua SIM cũng đạt 204. Sau bản sửa, chủ đã xác nhận
điện thoại thấy Wi-Fi USB và vào Internet được; đọc lại USB cũng thấy AP/data
active, Start thành công và probe SIM đạt. Nút giữ chỉ cho bấm khi AP/cellular
đã sẵn sàng. Chưa thử autostart/reboot sau Keep; agent không bấm giữ thay chủ.
Xem `docs/LED_AND_SIM_HOTSPOT_2026_11_15.md` và phần đầu handoff. Checkpoint sau
deploy: không pending, data/AP tắt, 5 profile Wi-Fi lưu/0 active, setup/policy
đang tắt do chủ chọn. Đọc sau đó: AP/data bật, trial còn 222 giây, enabled=false.
Chủ đang thử nên phải đọc lại trạng thái mới, không restart web giữa trial. Chưa sửa
lỗi router nhà cũ, chưa chứng nhận Tunnel public (403 ở lần kiểm tra trước).

Đây là trạng thái phát triển trên USB thật, không chỉ là bản thiết kế giao
diện. Đọc tài liệu này trước khi sửa UI hoặc triển khai lại. Nhánh đang dùng:
`codex/uz801-v32-postmarketos`. Bản Windows v0.1.1 trong README là ứng dụng
backup cũ; panel Linux trên USB là luồng riêng.

**Bản trước cập nhật LED/SIM:** USB đã cài `ea9fcc8`, gồm giao diện `0dda4fc`, địa chỉ
chung `http://openstick.local:8765` qua USB/Wi-Fi/hotspot, cùng icon nhà mạng
và cột sóng. Xem `docs/USB_UI_DEPLOYMENT_2026_11_14.md` và phần đầu handoff.
Trạng thái quan sát cuối là AP cài đặt; không có pending setup, vẫn còn 4
profile station. Một router nhà từng dùng được vẫn chưa nối lại được, còn
router khác nối được sau AP. Khóa/tham số profile mục tiêu khớp backup, không
có denylist hay khóa BSSID trong profile. Chưa giải quyết lỗi riêng router đó.

## Yêu cầu đã thống nhất với chủ USB

- SMS gửi/nhận được bật theo khả năng modem/SIM; dữ liệu SIM mặc định tắt.
  Chỉ bật Internet SIM khi người dùng chọn, không tự cấp quyền dùng dữ liệu.
- Yêu cầu icon mới: SIM hiển thị tên nhà mạng; mục Mạng hiển thị công nghệ và
  cột sóng, bấm xem chi tiết. Icon Wi-Fi thể hiện đang nhận hay phát.
- SMS giống ứng dụng điện thoại: danh sách hội thoại, màn hội thoại riêng,
  màn soạn mới riêng. Không nhúng form gửi SMS vào mọi màn.
- USSD cần phản hồi mới theo từng lần gửi, kể cả nội dung giống lần trước.
  Có nút nhanh `*101#`; không tự gửi lại khi chưa biết kết quả.
- Hotspot cài đặt phải độc lập với SIM/Internet. Điện thoại truy cập để nhập
  Wi-Fi; có cả nút quét/danh sách và nhập tay cho SSID ẩn. Chọn mạng chỉ điền
  tên, không đổi kết nối trước khi bấm Lưu.
- Luồng mới chủ USB yêu cầu: lưu cấu hình → khởi động lại một lần → thử các
  Wi-Fi đã lưu → chỉ phát hotspot nếu không nối được mạng nào. **Luồng reboot
  này đã được triển khai và thử reboot thật thành công trên mạng mới.**
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
- Địa chỉ chung mới: `http://openstick.local:8765`. Avahi trên `usb0,wlan0`
  tự cập nhật địa chỉ theo DHCP/AP; PC nối USB cũng có listener cổng 8765.
  Không nới Host/Origin thành wildcard; giữ exact Origin theo từng Host.
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
- Bộ test gần nhất: **379 passed, 1 skipped** (quyền symlink Windows), khoảng
  75 giây. Đây không phải chứng nhận tất cả chức năng phần cứng đã đạt.
- Current và saved radio mode đọc gần nhất đều `[12,8]`. Chủ USB tự chọn;
  không ghi đè bằng `[8,0]` từ tài liệu phiên cũ.

## Lỗi chặn cần ưu tiên

**Đã đối chiếu được với mạng khác: Wi-Fi mới thành công.** Chủ USB nhập
thông tin qua trang setup; USB nhận IPv4 và probe Internet gắn wlan0 đạt.
Sau đó thử worker lưu/reboot thật với keyfile của mạng mới: boot đổi, đúng
profile, DHCP/Internet/LAN login HTTP 200 đều đạt sau khoảng 74 giây. Bài thử
worker dùng lại PSK đã dẫn xuất trong file riêng, không lấy mật khẩu ra chat.

Vì vậy không quy tất cả lỗi về việc ngắt hotspot trong lúc lưu. Lỗi bộ phát
cũ vẫn còn, chưa xác định được chính xác tham số tương thích/cấu hình gây lỗi.

Key tính từ mật khẩu lưu trên Windows đã so sánh khớp PSK trong keyfile cũ,
không in mật khẩu/PSK ra log. Khi thử handoff, wpa_supplicant báo handshake/
WRONG_KEY nhưng kernel đồng thời có `hal_join ... err=-5`,
`hal_config_bss ... err=-5`, `hal_delete_sta_self ... err=7` và đôi khi kernel
warning. Không kết luận đơn giản là người dùng nhập sai mật khẩu.

Hai lỗi cần tách riêng:

1. AP không khởi tạo do PMF mặc định: đã xác định key AES-CMAC `alg=4`, index 4
   bị kernel EINVAL. Đặt `wifi-sec.pmf=1` trong profile **AP** giải quyết phát
   hotspot; đã sửa cả hai bộ sinh profile AP. Giữ WPA2/CCMP.
2. Nhận Wi-Fi từ bộ phát cũ: vẫn cần đối chiếu cấu hình. Reload riêng wcn36xx không giải quyết.
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
(state 50). **Đã sửa trong setup worker:** phải state 100 kèm IPv4 mới tính
là có LAN; UUID đang thử không còn chặn timer tự cứu. Không probe Internet
để quyết định có giữ LAN hay không. Có regression test cho trạng thái này.

Luồng reboot lưu `phase=await_boot` trước khi yêu cầu reboot, fsync file và
thư mục, giữ AP đến shutdown. Cùng boot không gọi lại reboot; sau boot mới
thử mạng mới rồi tối đa 5 mạng autoconnect đã lưu (mỗi mạng 20 giây). Nếu hết
45 giây mà reboot chưa xảy ra, khôi phục profile/AP; không lặp reboot. Modem
lock/USSD state chặn reboot khi có giao dịch. UI thông báo reboot rõ ràng,
có link LAN mới trên USB và tự nạp lại token sau boot khi cần.

Bài thử âm thật qua HTTP cũng đạt: gửi SSID không tồn tại, USB reboot một
lần, thử mạng mới không được rồi tự nối Wi-Fi tốt đã lưu sau khoảng 100 giây.
Kết quả `SAVED_WIFI_CONNECTED`, không còn pending intent, không lặp reboot.
Unit test bao gồm sai khóa, khôi phục keyfile cũ, mất nguồn giữa intent,
reboot thất bại, trì hoãn khi USSD/SMS bận và NM state 50.

## Tiếp tục thực hiện

1. Đọc status hiện tại qua USB, pending setup intent, NM state/reason và log
   kernel có lọc; không in credentials/nội dung SMS/USSD.
2. Khôi phục keyfile tốt nếu một thử nghiệm làm mất secret. Giữ USB/SSH chạy.
3. Luồng reboot một lần đã cài; giữ các ràng buộc intent/boot/timeout/modem
   lock khi tối ưu giao diện, không tạo reboot loop.
4. Đã thử mạng mới trước, rồi các profile autoconnect khả dụng/ẩn. Giữ LAN
   khi có IPv4 dù Internet không có. Không thay bằng probe Internet bắt buộc.
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

Trạng thái sau bài reboot mới: USB đang nhận Wi-Fi mới có Internet, tự cứu
vẫn bật, không bật SIM data. Keyfile Wi-Fi cũ giữ nguyên. Profile chẩn đoán
tạm đã xóa. Xem handoff để biết kết quả bài thử âm cuối cùng trước push.

RMTFS giữ RAM-shadow `-r`; không flash/erase/ghi NV, không đoán PIN/PUK.
SIM data failover, Internet sharing từ SIM, nhiệt/uptime và boot chỉ cắm sạc
chưa được xác minh đầu cuối. UI có thể được tối ưu độc lập nhưng phải giữ
token/Host/Origin guard, LAN auth, an toàn hiển thị text và trạng thái unknown.
