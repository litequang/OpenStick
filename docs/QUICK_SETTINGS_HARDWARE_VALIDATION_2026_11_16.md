# Quick Settings: kiểm chứng UZ801 V3.2, 16/11/2026

Nhánh `codex/uz801-v32-postmarketos`. Chủ đã cho phép cài và thử thay đổi
mạng, bật dữ liệu SIM và sau đó cho phép lưu chế độ tethering + reboot bình
thường. Không merge main, tạo release, flash hoặc đổi firmware.

## Những lỗi đã sửa

- Trang HTTP thật không có `crypto.randomUUID()`: tạo UUID v4 bằng
  `crypto.getRandomValues`, không cần HTTPS/secure context. Test Chrome đã
  cố ý bỏ `randomUUID`; Hủy/Escape không gửi lại thao tác.
- Dashboard dùng cùng năm ô với `/quick`: máy bay, data, nhận Wi-Fi, phát
  Wi-Fi, USB tethering. Không còn ô “Chia sẻ SIM” riêng. Có hai biểu tượng
  nhận/phát khác nhau; bản Tổng quan gọn trên điện thoại.
- AP và data độc lập: data bật + AP bật chia sẻ SIM; data tắt vẫn giữ AP quản
  trị. Bật AP không ép tắt data. Tắt AP không tự bật station Wi-Fi cũ.
- dnsmasq setup bị thoát do chiếm loopback DNS của NM, dù OpenRC supervisor
  vẫn báo started: thêm `--except-interface=lo`. Kiểm tra tiến trình con và
  socket thật, không chỉ rc-service. Chủ đã xác nhận điện thoại nhận IP và
  vào Tổng quan sau sửa.
- Quy tắc nftables ban đầu bị lỗi do đóng chain/table trên cùng dòng: sửa
  thành nhiều dòng; `nft -c` trên kernel thật đã chấp nhận. Giới hạn trong
  các bảng riêng; không flush hoặc viết lại firewall nền.
- Tethering trực tiếp đã chạy nhưng PC cắm sẵn cần renew DHCP. Theo yêu cầu
  chủ, **thay bằng lưu trên USB + một reboot**, không có tiện ích PC. Giao
  diện đợi receipt qua reboot và lấy lại token mới bằng GET, không POST lại.

## Bằng chứng thật và giới hạn

| Hạng mục | Kết quả |
| --- | --- |
| SIM | Nhận SIM, đăng ký mạng nhà; PIN2 không bị hiểu là khóa PIN1 |
| Radio | Lựa chọn đã lưu/đọc `[8,0]` (4G only); không đổi RAT/APN để tạo PASS |
| Data SIM | NM có interface dữ liệu; DNS và HTTPS buộc qua SIM đạt 204 |
| Data on → AP on | AP thật, SIM vẫn connected và Internet đạt; không STA/AP đồng thời |
| AP + data off → data on | Hai chu kỳ kết nối lại thành công; mỗi lần probe SIM đạt 204 |
| AP không bị cycle khi data off | Profile SSID/PSK/IPv4, AP UUID, IPv4 và PID/start-time DHCP giữ nguyên ở lượt đối chiếu; không nối STA |
| AP off | NM disconnected/driver managed, không active STA; data SIM và USB quản trị vẫn chạy |
| Máy bay on/off | MM disabled rồi registered lại; AP quản trị và USB còn; airplane-off chưa data, sau thao tác data-on riêng probe SIM 204 |
| Điện thoại → SIM Internet | Chủ xác nhận đã tắt data điện thoại, kết nối Wi-Fi USB và mở được Internet lẫn trang quản trị |
| USB → Wi-Fi Internet | DNS/HTTPS source USB đạt 204 trên Windows thật |
| USB → SIM Internet | STA ngắt, AP đang phát, SIM-bound probe đạt; DNS/HTTPS source USB trên PC đạt 204 |
| Tethering off + reboot | Windows tự bỏ gateway/DNS USB, không renew hoặc reset adapter thủ công |
| Tethering on + reboot | Windows tự nhận gateway/DNS; DNS và HTTPS source USB 204, exit 0; không phần mềm PC |
| Sau reboot | USB admin, Wi-Fi Internet, website loopback HTTP 200 và dịch vụ Tunnel/portal chạy lại |
| Máy PC/OS khác, tải lâu | UNVERIFIED; chỉ máy Windows hiện tại được kiểm chứng |
| SMS/USSD | Không thử trong lượt này theo lựa chọn mới nhất của chủ |
| RF vật lý, rút nguồn nhiều lần | Không dùng trạng thái MM làm phép đo RF; chưa chứng nhận |

“Internet 204” ở đây là request nhỏ có buộc interface và DNS, không phải
speedtest, chứng nhận mọi nhà mạng hoặc website/Tunnel public. Điện thoại là
nghiệm thu do chủ xác nhận; Chrome headless không thay thế quan sát đó.

## Lỗi kết nối lại SIM còn phải theo dõi

Lượt trước đã bắt đúng lỗi MM trả cho NM:
`org.freedesktop.ModemManager1.Error.Core.InProgress` /
`Bearer already being disconnected`. Khi đó bearer báo Connected=false nhưng
tác vụ disconnect nội bộ chưa kết thúc; LTE registered không chứng nhận data.
Restart riêng ModemManager đã được thực hiện một lần khi không có bearer active,
giữ nguyên cấu hình, USB và boot. Chủ cũng xác nhận bật/tắt máy bay rồi kết nối
data/AP được. Sau đó chủ tháo SIM; SIM missing lúc ấy là đúng, không phải lỗi
mới. Chủ đã lắp lại SIM để chạy các bài mạng bên trên.

**Chưa kết luận sửa triệt để lỗi nội bộ ModemManager.** Hai chu kỳ gần nhất
và một lượt kết nối sau chu kỳ máy bay không tái hiện; không coi việc restart dịch vụ, radio hoặc reboot là bản vá
gốc. Khi NM không kết nối được, receipt mới báo `DATA_CONNECT_FAILED`, bỏ
data intent, không tự retry, tự đổi APN/RAT, restart MM hoặc bật/tắt radio.
Người dùng có thể chủ động xác nhận chu kỳ máy bay, đợi đăng ký rồi bật data.

Mã upstream phân biệt trạng thái disconnect nội bộ với thuộc tính Connected;
tham khảo [mm-base-bearer.c](https://github.com/linux-mobile-broadband/ModemManager/blob/main/src/mm-base-bearer.c)
và [Bearer D-Bus API](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Bearer.html).
Không dùng bản upstream mới nhất để khẳng định đã sửa bản MM đang cài.

## Cài đặt, bảo toàn và kiểm thử nguồn

Nguồn Quick Settings đã **cài trên USB thật**, không còn baseline source-only
`c704264`. Các lần cài kiểm tra hash trước/sau, sao lưu riêng tư trên thiết bị,
kiểm tra HTTP và bảo toàn mạng trong lúc cài. Chỉ restart worker/portal liên
quan; không restart NetworkManager. Reboot về sau là bài test tethering được
chủ cho phép riêng. Dispatcher vendor không bị sửa; hook dùng
`/etc/unudhcpd.conf` hiện hữu.

Sau reboot, profile USB chỉ đổi `connection.timestamp` do dispatcher lưu
profile; không đổi địa chỉ, method hoặc các cấu hình chức năng. Cấu hình
website, Tunnel, LAN, SSH và lựa chọn radio được bảo toàn; các cấu hình
policy/autoconnect owned AP/CELL đổi đúng theo thao tác Quick Settings.
Không đưa credentials, SSID/MAC, SIM ID, nội dung SMS/USSD hoặc snapshot riêng
tư vào Git. `runtime/` và `artifacts/` tiếp tục ignored.

Test nguồn: **519 PASS, 1 Windows symlink privilege SKIP**, exit 0. Chrome
preview: tám layout trên hai trang, 320/390/768/1280 px, không tràn ngang/lỗi
JS; consent/Escape/no-SIM/HTTP thiếu randomUUID và receipt qua token đổi sau
reboot đều PASS. Đây là test mô phỏng, tách khỏi hardware ở bảng trên.

Chrome thật đã thực hiện các nút AP/data/tethering và airplane-on bằng đúng
một POST sau xác nhận. Lần mở Chrome để airplane-off bị crash do host thiếu
bộ nhớ ảo, chưa gửi POST; hoàn tất airplane-off/data-on bằng HTTP API với
token và operation UUID mới, một POST, theo quyền thử mạng chủ đã cấp. Không
gọi đây là nghiệm thu hình ảnh của bước cuối. Mất nguồn để chủ lắp SIM là
thao tác riêng; hai reboot do worker là hai xác nhận bật/tắt tethering.

Đọc bộ nhớ riêng: Device Tree khai 512 MiB, Linux MemTotal 376.3 MiB. Có khoảng
130 MiB MemAvailable ở lần đo sau; swap là zram, 134 MiB dữ liệu swap dùng khoảng
39 MiB RAM nén, không phải swap trên eMMC. Các worker Python cộng khoảng 91 MiB
PSS và 108 MiB SwapPss; cloudflared khoảng 23/2 MiB, nginx khoảng 1/1 MiB.
Số liệu thay đổi theo tải; không cộng RSS trùng các trang shared hoặc coi
376 MiB là kích thước chip RAM. Đây là telemetry, không phải stress test.

Sao lưu triển khai riêng tư gần nhất:

- `/var/lib/openstick/deploy-backups/quick-validation-1794815530291706814/`
  (20 source/assets, trước cài luồng reboot).
- `/var/lib/openstick/deploy-backups/usb-boot-1794815604776475036/`
  (dịch vụ DHCP, worker boot và hook cấu hình; có danh sách tệp trước đó chưa tồn tại).
- `/var/lib/openstick/deploy-backups/setup-dhcp-1794800526282679557/`
  (sửa loại trừ loopback).

Không khôi phục toàn bộ protected config từ archive một cách mù quáng vì chủ
đã thử mạng sau snapshot. Khi rollback mã, đối chiếu trước và chỉ phục hồi tệp
thuộc thay đổi cần bỏ. Hướng dẫn dùng tethering: [USB_TETHERING.md](USB_TETHERING.md).
