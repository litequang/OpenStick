# Chia sẻ Internet từ OpenStick sang máy tính

Ngày kiểm chứng: 16/11/2026, UZ801 V3.2 chạy postmarketOS.

**Cập nhật cuối ngày:** hai lượt bật/tắt bằng reboot bên dưới đã PASS, nhưng
sau cold replug Windows giữ lease quản trị cũ 42 ngày, thiếu gateway/DNS USB.
Thiết bị vẫn bật DHCP/NAT và quản trị được; không coi đó là PC có Internet.
Cold replug/PC mới chưa được chứng nhận. Xem
[bằng chứng và việc cần kiểm tra](QUICK_WIFI_APN_2026_11_16.md).

Mở **Tổng quan → USB tethering**, đọc xác nhận rồi bấm áp dụng. USB lưu chế
độ và khởi động lại bình thường **một lần**. Giữ USB cắm; trang đợi thiết bị
trở lại. Website và Tunnel tạm ngắt trong lúc reboot. Không mở trang nào tự
khởi động lại hoặc tự bật Internet SIM.

Ở hai lượt reboot đã thử, PC tự xin cấu hình IP/gateway/DNS khi thiết bị trở lại. Không cần ứng dụng
Windows, script gia hạn DHCP hoặc rút/cắm. Chế độ lưu **trên USB**, nên vẫn
dùng khi chuyển máy. Máy mới phải có driver USB NCM tương thích; đã kiểm
chứng máy Windows hiện tại với `UsbNcm Host Device`, chưa thử máy/OS khác.

Nếu báo đã lưu nhưng không reboot được, có thể rút nguồn USB 10 giây rồi
cắm lại bình thường. Không giữ reset hoặc chạm chân USB. Worker không tự
gửi lại reboot sau lỗi. Nếu báo chưa áp dụng được sau boot, giữ USB để
kiểm tra; không coi biểu tượng bật là chứng nhận Internet.

USB cần nguồn Internet hoạt động: Wi-Fi đã lưu hoặc dữ liệu SIM do chủ bật.
Tethering **không tự bật SIM**, kể cả sau reboot. Khi bật máy bay hoặc tắt
data, PC có thể vẫn nhận gateway USB nhưng không có Internet nếu không còn
nguồn khác. Trang quản trị USB vẫn dùng được.

## Bằng chứng thật

- Luồng cũ bật dịch vụ trực tiếp đã truy cập được HTTPS qua USB nhưng cần
  gia hạn DHCP trên PC; **không còn là luồng nút hiện tại**.
- Luồng mới tắt → một reboot: Windows tự bỏ gateway/DNS USB, quản trị còn.
- Luồng mới bật → một reboot: Windows tự nhận gateway/DNS; DNS qua USB
  thành công; HTTPS buộc source USB trả **204**, exit **0**. Không dùng
  `ipconfig /renew`, tiện ích PC hoặc reset adapter trong hai lượt này.
- Sau boot, Wi-Fi Internet, website HTTP 200, Tunnel và hai portal chạy lại.
- Khi đổi Wi-Fi station sang AP và bật dữ liệu SIM, PC qua USB tiếp tục
  truy cập DNS/HTTPS 204; probe DNS/HTTPS buộc qua SIM cũng đạt.
- Chỉ `connection.timestamp` của profile USB đổi do dispatcher upstream
  lưu profile khi boot; chưa thay thuộc tính mạng hay gadget/VID/PID.

## Thiết kế và triển khai

`usb-tethering-intent.json` riêng tư lưu lựa chọn và receipt operation UUID.
Worker `openstick-usb-tether` ghi trạng thái chờ boot trước khi gọi reboot;
boot mới chỉ áp dụng lựa chọn, không yêu cầu reboot tiếp. Giao dịch modem
đang chạy giữ reboot ở trạng thái chờ. Hỏng áp dụng có deadline, không lặp
reboot hoặc tự tạo bearer SIM.

NetworkManager giữ nguyên profile USB manual. Hook cấu hình được upstream
hỗ trợ tại `/etc/unudhcpd.conf` chọn DHCP/DNS riêng khi đã lưu tethering on.
Nếu không chọn hoặc dịch vụ không khởi động được, giữ DHCP quản trị upstream.
Không chỉnh dispatcher vendor hoặc gọi reapply/shared để ép rebind UDC.

Các tệp cài một lần trên **USB**, không trên PC:

- `scripts/openrc/openstick-usb-dhcp` → `/etc/init.d/openstick-usb-dhcp`.
- `scripts/openrc/openstick-usb-tether` → `/etc/init.d/openstick-usb-tether`,
  thêm runlevel `default`.
- Nối nội dung `scripts/unudhcpd-openstick.conf` vào `/etc/unudhcpd.conf`
  **sau khi sao lưu và xác nhận dispatcher còn source tệp này**. Không ghi
  đè cấu hình cũ hoặc nối trùng marker.
- Cài module `uz801_manager.usb_tethering` cùng portal đã qua test.

DHCP/DNS chỉ bind `usb0`, loại trừ loopback; NAT/filter chỉ dùng bảng riêng
`inet openstick_usb_tether`. Không flush firewall, thay default route USB,
đổi địa chỉ quản trị, driver Windows, SSH, website hoặc Tunnel. IP forwarding
chỉ trả về 0 nếu thuộc quyền tính năng này và không có AP shared cần nó.

Các giới hạn còn lại: IPv4, một client USB; chưa thử máy mới, cold power-only,
mọi OS, mất nguồn giữa ghi intent hoặc nhiều giờ tải thực. Không coi NCM link
Up hoặc LTE registered là kiểm chứng truy cập Internet.
