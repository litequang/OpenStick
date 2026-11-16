# Quick Wi-Fi, APN và trang mặc định — 16/11/2026

Đã cài trên UZ801 V3.2 thật, nhánh `codex/uz801-v32-postmarketos`.
Không flash, đổi gadget/driver Windows, reboot hoặc gửi SMS/USSD trong lượt
cập nhật này. Chủ tháo SIM giữa lượt kiểm tra; không đánh dấu những phép thử
cần SIM sau đó là PASS.

## Cách sử dụng

- `http://openstick.local:8765/` chuyển đến `/overview`. Qua Wi-Fi vẫn cần
  đăng nhập; truy cập trực tiếp `/setup` vẫn mở đúng cài đặt Wi-Fi.
- Tổng quan nằm ngoài cùng bên phải thanh điều hướng dưới ở cả bố cục
  5, 6 và 7 mục; biểu tượng, liên kết và trạng thái đang chọn được giữ.
- **Nhận Wi-Fi**, khi chưa nối: xác nhận để quét và thử các mạng đã lưu.
  Thất bại thì thử khôi phục vai trò trước và mở hộp chọn mạng.
- Khi đã nối, bấm ô này để xem mạng hiện tại, mạng đã lưu và kết quả quét;
  chọn mạng đã lưu không cần nhập lại mật khẩu. **Quét lại** và ngắt/kết nối
  đều có xác nhận. Mở cửa sổ chỉ đọc trạng thái; không tự đổi mạng.
- Mật khẩu mạng mới được nhập trong cửa sổ, xóa khỏi ô khi đóng; không lưu
  trong sessionStorage hoặc receipt. Chỉ hỗ trợ cấu hình WPA-PSK hiện có;
  không quảng cáo hỗ trợ WPA3-only, Enterprise hoặc mạng mở từ biểu mẫu này.
- **Quản lý → APN tùy chỉnh**, hoặc **Mạng SIM → APN tùy chỉnh**, mở
  `/sim/apn`: tên cấu hình, APN tự động/thủ công, tài khoản, giữ/thay/xóa
  mật khẩu, xác thực tự động/không/PAP/CHAP/PAP hoặc CHAP, giao thức
  tự động/IPv4/IPv6/IPv4v6 và cho phép roaming có xác nhận.
- Đây là cấu hình cho **một kết nối SIM hiện tại**, chưa phải kho nhiều APN.
  Lưu không bật data, đổi RAT, phát Wi-Fi hoặc reboot. Giữ các chốt yêu cầu
  dừng dữ liệu/AP và chính sách tự quản lý trước khi sửa. SIM có thể lắp sau.
  Chế độ tự nhận xóa tài khoản/mật khẩu APN thủ công, có giải thích khi xác nhận.
- API chỉ trả `password_saved`, không trả mật khẩu. Mật khẩu lưu trong keyfile
  root-only; không nằm trong `hotspot.json`, lịch sử thao tác hoặc tham số CLI.
  Giao thức IPv6 phụ thuộc nhà mạng/modem; tethering/hotspot hiện chia sẻ IPv4.
  Không thêm trường MMS/proxy điện thoại giả như thể chúng có tác dụng cho web.

## Bằng chứng và giới hạn

| Phép thử | Kết quả và phạm vi |
| --- | --- |
| Tự nối saved Wi-Fi khi offline | VERIFIED trên USB; DHCP và HTTPS bound Wi-Fi 204 |
| Ngắt station, chọn lại saved profile | VERIFIED trên USB; không dùng lại mật khẩu từ chat |
| Quét khi đang nhận Wi-Fi | VERIFIED; UUID, IPv4, boot, radio và data intent không đổi |
| AP → quét → khôi phục AP | VERIFIED thao tác; lần quét đầu có thể thành công nhưng rỗng |
| AP → tự nối saved Wi-Fi sau sửa | Hai lượt VERIFIED trên USB; Wi-Fi-bound HTTPS 204 sau lượt cuối |
| AP → station giữ SIM data hoạt động | UNVERIFIED; lượt trước gặp quét rỗng, sau đó chủ tháo SIM/rút cắm; không suy từ fixture |
| Kết nối Wi-Fi mới bằng mật khẩu nhập trong popup | Fixture/Chrome demo PASS; chưa thử mật khẩu mới trên phần cứng |
| Root URL, dock, popup Wi-Fi và form APN thật | Chrome headless trên USB PASS ở 320/390/768/1280 px; không tràn ngang/lỗi JS, không gửi lệnh thay đổi |
| APN 5 kiểu xác thực × 4 giao thức | NetworkManager trên USB đọc/ghi **offline** 20 trường hợp PASS; cấu hình thật không đổi |
| Ký tự đặc biệt và khoảng trắng đầu/cuối mật khẩu | Offline roundtrip PASS sau sửa parser; không dùng credentials thật |
| Kết nối nhà mạng bằng APN tùy chỉnh | UNVERIFIED, cần SIM và APN do chủ chọn; không tự thay APN đang lưu |

Driver trả cache rỗng ngay sau AP down. Đã đo riêng: lần đầu 0 mạng, sau
2 giây có mạng. Quick Wi-Fi quét tối đa ba lần, chỉ chờ thêm khi cache rỗng;
không reset modem, reload driver hoặc reboot để che lỗi. Fixture kiểm tra
giới hạn và khôi phục AP khi không tìm thấy mạng. Kết nối saved dùng giới
hạn hiện có: tối đa năm ứng viên, 20 giây mỗi ứng viên.

Giao dịch dùng lock mạng rồi modem hiện có, không chạy tiến trình SSH con
để giành lại cùng lock. Dừng automation khi đổi vai trò thủ công; quét không
tự đổi chính sách. Rollback phục hồi keyfile cũ khi thay mật khẩu thất bại.
Receipt chỉ hoàn tất sau khi đọc trạng thái cuối thành công.

573 pytest PASS / 1 Windows symlink privilege SKIP, exit 0. Self-test và
Node syntax PASS. Chrome demo: tám layout Quick Settings, bốn APN, xác nhận/
hủy, xóa mật khẩu, UUID trên HTTP và token đổi qua reboot mô phỏng PASS.
Các phép mô phỏng này tách riêng với bảng hardware bên trên.

## Dung lượng thật

eMMC đo được 3.876 GB (3.609 GiB), 27 phân vùng. Filesystem hệ điều hành
1.975 GiB, dùng khoảng 0.591 GiB, khả dụng khoảng 1.289 GiB tại lần đọc.
Phân vùng lớn nhất 2.452 GiB, các phân vùng còn lại khoảng 1.053 GiB.
Không đánh đồng filesystem, kích thước phân vùng và dung lượng chip; chưa
xác định đầy đủ chênh lệch bên trong phân vùng lớn. Không resize/format.
Dashboard hiển thị riêng tổng hệ điều hành, chỗ trống và tổng eMMC đo từ
sysfs; không tự điền nhãn 4 GB khi không đọc được.

## Trạng thái cuối và việc còn mở

Wi-Fi station có Internet; data intent OFF, không có SIM theo xác nhận chủ;
tethering lưu ON. Critical website/Tunnel/LAN password/SSH/radio checksums
giữ nguyên, RAT `[8,0]`, không còn setup/hotspot pending.

**Tethering sau cold replug chưa đạt:** Windows hiện giữ lease quản trị cũ
42 ngày và không có gateway/DNS USB, dù server DNS/DHCP owned đang chạy,
forwarding/NAT có và Wi-Fi Internet hoạt động. HTTPS source USB không đạt
ở checkpoint này. Chưa kết luận chính xác thời điểm lease được cấp; initfs
có DHCP quản trị riêng và dispatcher rootfs là yếu tố cần đối chiếu. Hai
luồng bật/tắt bằng reboot ở báo cáo trước đã PASS, nhưng không chứng minh
cold replug hoặc PC mới. Không tự renew/reset adapter, đổi UDC, sửa initramfs
hay flash để che giới hạn này. Ưu tiên kiểm tra boot DHCP trước chứng nhận
"cắm máy nào cũng có Internet". Trang quản trị USB vẫn truy cập được.

Lỗi MM cũ `Bearer already being disconnected` vẫn chưa có bản vá gốc;
không gọi đã sửa triệt để từ các lượt data thành công trước đó.

Sao lưu riêng tư của lượt triển khai cuối:
`/var/lib/openstick/deploy-backups/quick-validation-1794821201506118600/`;
28 source/assets, SHA-256 archive
`8174210a6e45c9c4412237033681b0fb01c1a98890535256ec5cd1ef6e4b9129`.
Không phục hồi toàn bộ config mù quáng: các thao tác mạng của chủ sau snapshot
vẫn phải được giữ. Không thêm background worker cho popup/APN.

Ánh xạ phần mềm đối chiếu từ nguồn chính thức:
[GSM settings](https://networkmanager.dev/docs/api/latest/settings-gsm.html),
[PPP authentication flags](https://networkmanager.dev/docs/api/latest/settings-ppp.html),
[GSM bearer construction](https://github.com/NetworkManager/NetworkManager/blob/main/src/core/devices/wwan/nm-modem-broadband.c),
[keyfile format](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html).
Tài liệu upstream không phải chứng nhận SIM/driver; bộ parser NetworkManager
đang cài đã được kiểm tra offline riêng như bảng trên.
