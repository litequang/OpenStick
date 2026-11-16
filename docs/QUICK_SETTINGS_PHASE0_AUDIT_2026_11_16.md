# Quick Settings UZ801 V3.2 — Phase 0, 16/11/2026

**Kết luận: GO có điều kiện cho phát triển, NO-GO cho chứng nhận/chuyển mạng
thật trong lượt này.** Chủ xác nhận USB hiện không lắp SIM. Không coi báo cáo
SIM missing là modem hỏng. Cần lớp điều phối trước khi đưa các công tắc độc lập
lên giao diện. Theo yêu cầu tiếp theo, chuẩn bị mã Phase 1 với test mô phỏng;
không triển khai hoặc thực hiện thao tác mạng trên USB.

Baseline `c704264eac765006a62d6549cbfbad0b58cbd8cf`, nhánh
`codex/uz801-v32-postmarketos`. Đã đọc AGENTS, tài liệu tiếp tục/bàn giao và
sáu module được yêu cầu; SHA-256 sáu module trên USB khớp nguồn. Có hai tệp
untracked từ trước, giữ nguyên. Không merge main, không tạo release.

## Bằng chứng đã lọc

- Kernel `6.12.1-msm8916`, NetworkManager 1.52.2, wpa_supplicant 2.11,
  ModemManager 1.25.95, dnsmasq 2.92rel2.
- `wlan0`: managed, NM state 100, supplicant completed; một NM, một
  wpa_supplicant, không có tiến trình hostapd. NM dùng DNS dnsmasq, DHCP
  internal, firewall nftables. Điều khiển AP qua NM/supplicant, không phải
  một hostapd độc lập đang chạy. Chưa chuyển sang AP để xác minh lại hôm nay.
- Driver `wcn36xx`, phy có managed/AP/AP-VLAN, 2,4 GHz/CCMP; không báo valid
  interface combinations, không báo max associated stations, không báo AES-CMAC.
- Supplicant quảng bá `sae`/PMF và AP; đây là khả năng phần mềm. Handoff ghi
  lần thử AP PMF lỗi AES-CMAC/EINVAL; cấu hình đang dùng `pmf=1` (disabled).
- Modem object có Enable/SetPowerState nhưng state FAILED, failed reason 2
  (SIM missing), không có SIM object hoặc bearer kết nối. Các interface SMS/
  USSD không được export ở trạng thái hiện tại. Saved/current mode hiện là
  `[8,0]`; giá trị `[12,8]` ở tài liệu cũ không phải trạng thái hiện tại.
- NCM là chức năng duy nhất được link vào gadget và UDC đang bound. Không đọc
  serial hoặc MAC gadget. `usb0` up, NM ethernet/manual, `172.16.42.1/16`;
  Windows adapter up, DHCP `172.16.42.2/24`, DHCP server là USB, không có default
  route USB. Khác prefix /16 và /24 được ghi nhận, không sửa trong audit.
- DHCP USB thực tế là **unudhcpd**, đang bind usb0 với server/client IP nêu
  trên; không phải dịch vụ dnsmasq AP. Dispatcher có nhánh manual/shared và
  thao tác rebind UDC. Chuyển USB profile sang shared bằng NM có thể reset
  kết nối gadget: không dùng làm đường tắt cho yêu cầu bảo toàn USB.
- IPv4 forwarding toàn hệ thống/usb0 đều 0; IPv6 forwarding 0; không có NAT
  chain. Forward chain policy drop nhưng có accept `usb*`, `wlan*` và
  established/related. Default route thiết bị qua wlan0; route USB link là
  `172.16.0.0/16`. DNS đang nghe loopback, không nghe USB/wildcard.
- Hai pending setup/hotspot đều vắng; policy disabled, cellular consent false;
  AP/SIM profiles autoconnect false; setup recovery enabled. Không bật AP/data.

Lệnh `ip -j` không được bản ip trên USB hỗ trợ; đã đọc lại bằng output text có
lọc. Truy vấn đầu giả định USB /24 không khớp; lần đọc prefix thực tế xác nhận
/16. Không dùng hai kết quả âm do sai giả định làm kết luận phần cứng.
Boot, profile và cấu hình kiểm tra trước/sau probe không đổi. Không thu thập
IMEI/IMSI/ICCID, SSID/MAC thật, khóa, mật khẩu hoặc nội dung SMS/USSD vào báo cáo.

## Ma trận chức năng

Trạng thái là cho chức năng nêu ở từng dòng, không suy rộng từ việc có API.
VERIFIED có ghi rõ quan sát hôm nay hay bằng chứng lịch sử trên chính USB này.

| Chức năng | Trạng thái | Bằng chứng, giới hạn và ưu tiên |
| --- | --- | --- |
| Wi-Fi STA, USB quản trị | VERIFIED trên USB thật | Quan sát hôm nay: NM 100, USB DHCP/card mạng hoạt động. P0 bảo toàn. |
| AP nội bộ WPA2/CCMP | VERIFIED trên USB thật | Handoff có AP/DHCP/LAN login và chủ xác nhận điện thoại; hôm nay không bật lại AP. P0. |
| SIM Internet → AP | VERIFIED trên USB thật | Lượt thử cũ có SIM-bound probe và chủ xác nhận điện thoại có Internet. Không đồng nghĩa mọi lần handoff hoặc boot replay đã đạt. |
| Tắt/bật modem riêng, giữ Wi-Fi/USB | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | Enable/SetPowerState export; chưa thực thi, hiện không SIM. P0. |
| Chế độ máy bay bền vững với worker hiện tại | BLOCKED/UNSUPPORTED | Chưa có intent airplane; watch_radio có thể Enable(True) trong chu kỳ 30 giây, tối đa 3 lần/process. Cần sửa điều phối trước. P0. |
| Tắt data giữ modem/SMS/USSD trong vai trò STA | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | data_off tắt policy/autoconnect/CELL_UUID; không Disable modem. Unit test có; không thử hôm nay. P0. |
| Tắt data khi SIM AP đang chạy → AP nội bộ không Internet | BLOCKED/UNSUPPORTED | data_off bị assert_station_role chặn; Hotspot.stop còn dừng AP rồi thử Wi-Fi cũ. Cần giao dịch mới theo yêu cầu chủ. P0. |
| Giữ SSID/key khi setup AP → SIM AP | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | _adopt_setup_ap sao chép wifi/security, chuyển manual sang shared; fixture có snapshot/checkpoint/rollback. Luồng smart handoff đầy đủ chưa nghiệm thu. P0. |
| WPA3-only/transition | BLOCKED/UNSUPPORTED | Có SAE trong userspace nhưng PMF đã lỗi trên AP/driver hiện tại. NO-GO cung cấp như chức năng hoạt động; không kết luận silicon vĩnh viễn không thể. |
| Hidden SSID AP | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | libnm có hidden; profile AP chưa đặt. Khác STA hidden đã có; không phải cơ chế bảo mật. P2. |
| Danh sách client AP | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | Supplicant export Stations/StaAuthorized/StaDeauthorized. AP chưa active hôm nay nên không có kiểm chứng client list; lease không đồng nghĩa association. P1. |
| Giới hạn client | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | Supplicant MaxNumSta read/write, giá trị đọc là 128; NM không có max-clients/max-num-sta. 128 là cấu hình userspace, không phải chứng nhận 128 thiết bị trên UZ801. Max phần cứng UNVERIFIED. P2. |
| Chặn MAC client qua NM mac-address-denylist | BLOCKED/UNSUPPORTED | Property chọn loại trừ MAC của adapter chạy profile, không phải ACL client AP. Không dùng sai property. P2. |
| ACL client AP bằng backend khác | UNVERIFIED | Chưa có đường điều khiển được kiểm chứng trong portal/NM hiện tại; nft lọc Internet không đồng nghĩa chặn association hoặc lưu lượng cùng BSS. P2. |
| AP isolation | SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED | libnm ap-isolation; supplicant ApIsolate read/write, hiện 0; profile chưa đặt. Cần hai client để chứng minh L2 isolation, không chỉ ping USB. P1. |
| Wi-Fi STA + AP đồng thời, repeater | BLOCKED/UNSUPPORTED | Driver hiện không quảng bá combination; thiết kế một radio chỉ một vai trò. |
| USB CDC NCM/card mạng/DHCP | VERIFIED trên USB thật | Configfs NCM/UDC, NM usb0 và Windows DHCP đã đối chiếu. P0. |
| Chia sẻ Internet qua USB hiện tại | BLOCKED/UNSUPPORTED | Chưa cấu hình forwarding/NAT/DNS/default route cho PC. Không nhầm mạng quản trị với tethering. |
| USB tethering mới, giữ gadget không rebind | UNVERIFIED | Có đường phát triển bằng routing/NAT riêng; không dùng dispatcher shared hiện tại. Cần chấp nhận route/DNS opt-in phía PC. P1 sau P0. |

## A — Radio, data và boot

`watch_radio()` gọi status mỗi 30 giây, có thể enable khi SIM unlocked và state
disabled; bộ đếm reset khi worker restart. Nó replay saved mode tối đa ba lần
đổi/process, tránh USSD active. Không có airplane intent hoặc lock mạng trong
worker. Chỉ có modem lock, nên một lệnh disable rời rạc sẽ bị tranh quyền.
`Hotspot.start()` còn gọi WWAN on; policy có thể tạo CELL_UUID nếu consent cũ
còn bật. Keep bật autoconnect AP/CELL cho lần cấp nguồn sau; pending recovery
chỉ phục hồi trial, không phải airplane/data-off supervisor.

Ứng viên API là Enable(false/true), khi cần mới đánh giá SetPowerState sau
disabled. Tác động SMS/USSD: radio disabled thì không đăng ký/giao dịch mạng;
lịch sử SMS đã lưu vẫn đọc được. Không thay 3G/4G preference. Không dùng rfkill
all, stop remoteproc, reset modem hoặc tắt NetworkManager. API export chưa
chứng minh khả năng tắt RF riêng trên phần cứng. Xem [ModemManager API](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.html).

Data-off phải dừng policy và autoconnect owned CELL trước khi disconnect; radio
vẫn enabled để SMS/USSD. Airplane-off **không** khôi phục data, policy hay
autoconnect CELL. Data-on là hành động riêng có consent cước mới.

## B — Phân biệt phần mềm/driver

NM có hidden/ap-isolation và supplicant có MaxNumSta/SAE nhưng phải test riêng
trên driver. Không đổi backend sang hostapd chỉ vì có tài liệu hostapd.
Không dùng BssMaxCount (cache scan) làm giới hạn client. Không dùng số lease
của dải DHCP làm khả năng association. Không hứa 10/32/128 client khi chưa đo.
[NM wireless](https://www.networkmanager.dev/docs/api/latest/settings-802-11-wireless.html),
[NM security/PMF](https://www.networkmanager.dev/docs/api/latest/settings-802-11-wireless-security.html),
[supplicant DBus](https://w1.fi/wpa_supplicant/devel/dbus.html).

Yêu cầu bổ sung của chủ: khi tắt data trong SIM AP, xác nhận trước rằng web/
Tunnel và các máy dùng hotspot sẽ mất Internet; AP có thể ngắt rồi phát lại
để quản trị. Giữ cùng SSID/key khi đã xác minh identity khớp. Đích là AP nội
bộ không Internet; không tự nối Wi-Fi cũ. Nếu AP khôi phục lỗi, data vẫn tắt,
báo lỗi rõ và giữ đường quản trị USB. Không hoàn tác bằng bật lại data.

## C — Tethering không phá mạng quản trị

Không đổi USB gadget, VID/PID, UDC, địa chỉ usb0 hoặc profile USB; không chuyển
profile sang shared vì dispatcher hiện rebind UDC. Không chạy đồng thời DHCP
mới với unudhcpd. Xung đột DHCP này cũng được upstream ghi nhận:
[postmarketOS tethering design](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/3819/commits),
[unudhcpd issue](https://gitlab.com/postmarketOS/unudhcpd/-/issues/1).

Phương án Phase sau: một bảng nft do OpenStick sở hữu, chỉ NAT nguồn USB trên
uplink đã chọn, chặn rò sang uplink chưa consent; giữ bảng firewall nền. Chỉ
đọc route uplink và bám thay đổi, không thay default route thiết bị. Quản lý
forwarding có ownership/refcount vì NM hotspot cũng có thể dùng sysctl; không
restore 0 nếu còn bên khác đang dùng. DNS USB phải bind usb0, giữ resolver hiện
tại. Không expose quản trị ra WAN/Tunnel.

Windows hiện không có default route USB. Bật server NAT không đủ làm PC tự
dùng Internet USB. Nếu tuyệt đối không cho thay/đặt thêm route/DNS ở PC, tự
động tethering là NO-GO. Cần một bước opt-in host riêng, không reset adapter,
không thay route đang có; có thể thêm route phù hợp khi được phép. Không thực
hiện bước đó trong audit. Prefix /16 và /24 cần test riêng, không tự sửa.

## D — Nguồn trạng thái và giao dịch đề xuất

Một intent versioned root-private; phân biệt desired/observed/capability,
error/unknown/stale. Không suy ra data có Internet từ LTE registered. Mỗi tile
gồm trạng thái, lý do bị khóa, operation/phase và hạn chờ; chỉ GET khi mở UI.
Không lưu SIM ID, client MAC, SSID/key, nội dung tin nhắn trong receipt.

Thứ tự: bảo toàn quản trị USB → airplane/data-off của chủ → pending recovery
→ vai trò STA/AP độc quyền → Internet policy trong quyền consent còn hiệu lực
→ worker tự động. Khóa theo một thứ tự network.lock rồi modem.lock, fail busy;
không giữ modem lock rồi gọi API tự lấy modem lock lần nữa. Các worker và cả
legacy endpoints phải cùng kiểm tra intent, không chỉ ẩn nút trên UI.

Trước mutation: kiểm tra schema/confirm/consent, trạng thái fresh, foreign
connection và pending trial; ghi attempt UUID bền vững trước side effect.
Receipt COMPLETED/FAILED/UNKNOWN; timeout/mất HTTP không tự gửi lại POST.
Airplane/data-off là fail-closed: lỗi giữ lệnh cấm data, không rollback sang
bearer on. Transaction đổi vai trò có deadline độc lập browser, rollback AP/
profile được sở hữu; không checkpoint usb0. Reboot: invalidate deadline
monotonic theo boot, không replay SMS/USSD, không tự replay data-on chưa chứng
nhận; airplane-off chỉ cho phép radio, data vẫn off.

## Test cần chạy và Go/No-Go

| Ưu tiên | Bài thử được phép ở Phase sau | GO khi |
| --- | --- | --- |
| P0 | Unit: airplane vs watchdog/policy/Hotspot.start/legacy enable; race, corrupt intent, duplicate UUID, mất HTTP | Không writer nào bật modem/data trái intent; không replay side effect. |
| P0 | SIM thật: data off giữ registration/SMS/USSD; airplane on/off giữ Wi-Fi/USB; đợi >90 giây và restart worker có kiểm soát | Không tự re-enable, không tự có bearer sau airplane-off; preference giữ nguyên. |
| P0 | SIM AP → data-off → local AP, 2 điện thoại, đóng browser/mất response | Cùng SSID/key, LAN login hoạt động, không Internet, data không tự phục hồi; lỗi AP vẫn giữ USB. |
| P0 | Mất nguồn giữa intent/receipt; boot với airplane on/off và consent cũ | Không reboot loop, không auto data-on, không mất mạng quản trị. |
| P1 | AP client list/isolation: 2 client, join/leave, ping/ARP/L2 và truy cập quản trị | Danh sách đúng; isolation chặn client-client, vẫn tới USB/Internet đúng chính sách. |
| P1 | Tether qua Wi-Fi rồi SIM, pending conflict, rút/cắm USB, NM/worker restart | Gadget/UDC không đổi, không DHCP trùng, route/DNS host đúng consent; quản trị và website còn hoạt động. |
| P2 | Hidden AP, client cap từng mức có workload, ACL chính xác | Test đúng driver/backend; không đánh dấu pass từ metadata/lease. |

WPA3, repeater STA+AP, cam kết 128 client, ACL giả bằng denylist adapter và
tethering dùng rebind UDC: NO-GO trong baseline này. Không thử chúng bằng đổi
firmware hoặc reload driver.

Local regression hiện có: **469 PASS, 1 SKIP**, exit 0; skip quyền symlink trên
Windows. Chưa có test chức năng Quick Settings mới ở mốc Phase 0. Không build/
cài lại EXE hoặc dịch vụ USB để audit. Evidence đã lọc giữ trong ignored
`artifacts/quick-settings-audit/`, không chứa dữ liệu nhận diện bị cấm.
