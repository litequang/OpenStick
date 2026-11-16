# Rà soát thao tác và nhiều APN — 16/11/2026

Phạm vi: toàn bộ màn Linux portal, template/JavaScript, route và các backend
mạng liên quan. Windows backup UI là sản phẩm riêng, không xóa các nút của nó.

| Màn | Kết luận và thay đổi |
| --- | --- |
| Tổng quan / Cài đặt nhanh | Giữ năm ô dùng chung cùng backend/receipt; đây là hai lối vào cùng chức năng, không có hai cơ chế bật mạng |
| Phát Wi-Fi | Xóa bật thử SIM → Wi-Fi, checkbox dùng SIM và nút tắt cả AP/data; xóa biểu mẫu APN thứ hai; chuyển sang trạng thái đọc mới và liên kết đúng màn |
| Phiên hotspot cũ | Chỉ hiện Giữ / Hủy-hoàn tác khi thật sự còn pending; giữ backend/worker để không bỏ rơi phiên dở |
| Nguồn Internet | Xóa nút data-off riêng bị chặn khi AP chạy; giữ form chính sách ưu tiên/dự phòng vì đây là automation có xác nhận, khác công tắc tức thời |
| Wi-Fi | Xóa Phát ngay / Dừng và thử Wi-Fi cũ; điều khiển tức thời về Quick Settings. Tắt fallback chỉ lưu, không ngắt AP hay nối mạng cũ |
| Wi-Fi: chọn mạng, saved, thẻ kết nối | Giữ nhập mật khẩu/quên mạng và đặc biệt Save → một reboot khi đang setup AP. Giữ chốt policy/AP; không sửa luồng reboot đã kiểm chứng |
| Mạng SIM | Không hiện nút Enable modem cũ khi có Quick Settings; giữ lựa chọn RAT có xác nhận tại một màn |
| USSD | Xóa gửi nhanh *101# bỏ qua checkbox và hai nút đổi RAT; giữ nhập/gửi có xác nhận, trả lời và hủy phiên, liên kết sang Mạng SIM |
| SMS | Giữ hội thoại, gửi có xác nhận, đồng bộ và xóa; không có nút bật data/đổi RAT cạnh tranh |
| Website, LED, LAN/login | Giữ tạo/sửa/xóa file, lưu LED, mật khẩu/quyền LAN; chúng khác chức năng và có các chốt hiện có. Không thay website/Tunnel/credentials |
| Header | Sửa liên kết Wi-Fi khỏi `/` (nay là Tổng quan) và luồng hotspot cũ, trỏ về cấu hình Wi-Fi |

Không xóa API/worker cũ phục vụ rollback, compatibility và test chỉ vì bỏ
nút khỏi giao diện hiện tại. Các GET mới chỉ đọc, không kích hoạt data/AP.
Không bật/tắt modem, gửi SMS/USSD, đổi mạng hoặc reboot để kiểm tra giao diện.

## Danh sách APN theo SIM/gói cước

`/sim/apn` lưu tối đa 20 cấu hình có tên riêng, sửa hoặc xóa từng bản. Tên
không được trùng; có thể lưu bản sao cấu hình hiện tại mà không tải mật khẩu
về trình duyệt. Tạo/sửa/lưu danh sách vẫn được khi AP/data/policy đang chạy.
Chỉ **Áp dụng** mới đổi keyfile kết nối SIM, dùng các chốt AP/data/policy cũ;
áp dụng không bật data. Đổi SIM không tự chọn APN, không lưu SIM ID/IMEI.
Profile đang áp dụng không xóa được; sửa bản lưu không tự đổi cấu hình live.

File riêng `/var/lib/openstick/apn-profiles.json`, atomic, root-only 0600,
không đồng bộ Git. API/receipt không trả mật khẩu. Giữ/thay/xóa mật khẩu rõ
ràng, file hỏng fail closed. Không tạo nhiều profile GSM tự kết nối cạnh tranh:
chỉ áp dụng bản được chọn vào kết nối do OpenStick quản lý.

Kiểm tra nguồn: 580 pytest PASS / 1 Windows symlink privilege skip; Chrome
demo 24 layout cài đặt, 8 layout Quick, 4 APN PASS. Test APN bao gồm nhiều bản,
sửa/giữ password, áp dụng/xóa, chặn áp dụng lúc data/AP hoạt động, file hỏng,
tên trùng, giới hạn, không activation khi lưu. Fixture cũ được cập nhật sang
luồng mới; backend tests không bỏ. Chỉ kiểm tra UI/HTTP và bảo toàn cấu hình
trên USB trong lượt này; không chứng nhận kết nối nhiều SIM/APN nhà mạng.

Các giới hạn cũ vẫn còn: modem disconnect InProgress chưa có bản vá gốc;
Windows giữ lease cũ sau cold replug tethering. Xem báo cáo Quick Wi-Fi/APN
trước đó. Không gọi rà soát nút là đã giải quyết hai lỗi phần cứng/mạng này.

Đã cài 35 source/assets lên USB, không reboot/đổi mạng; checksum cấu hình
được bảo toàn trước/sau triển khai. Sao lưu riêng tư:
`/var/lib/openstick/deploy-backups/quick-validation-1794823675563370873/`.
