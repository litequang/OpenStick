# Portal performance audit — 2026-11-19

## Kết luận từ USB thật

Trang Tổng quan dựng HTML nhanh nhưng đợi dữ liệu chậm. Điểm nghẽn đã đo nằm ở
đường đọc trạng thái và hàng đợi HTTP, chưa có bằng chứng cho thấy hiệu ứng CSS
hoặc thiếu RAM là nguyên nhân chính. Chưa triển khai thay đổi kiến trúc hiệu năng;
các thử nghiệm cục bộ đã tách khỏi bản sửa trạng thái/nút nguồn.

Phạm vi rà soát: cấu trúc nguồn và đường chạy của Linux portal, hai listener,
Host/Origin/token/LAN authentication, các route và worker bất đồng bộ, header,
Tổng quan/Quick Settings, Wi-Fi/AP/Internet, modem/SMS/USSD, website/file manager,
power/usage collectors và các vòng polling. Windows backup/ADB/EDL là đường chạy
riêng, không tham gia tải Tổng quan; không sửa cơ chế backup. Đây là audit hiệu
năng theo đường chạy, không phải chứng nhận mọi nhánh chương trình đều được thử
trên phần cứng hoặc một kiểm toán bảo mật toàn diện.

Số đo là một mẫu tại thời điểm kiểm tra, không phải p95 hoặc cam kết tốc độ.
Không gửi SMS/USSD, không bật SIM data, không đổi AP/profile/route hoặc reboot.
Browser tự chạy đúng các yêu cầu đọc trạng thái hiện có của trang. Không ghi
SSID/MAC, địa chỉ LAN thực, dữ liệu SIM, nội dung tin nhắn hay thông tin website.

| Đo trên USB đang chạy | Kết quả |
| --- | --- |
| Chrome Windows, DOMContentLoaded Tổng quan | 0,123 giây |
| Chrome, số liệu Tổng quan xuất hiện lần đầu | 9,157 giây |
| GET header, gọi tuần tự trên USB | 8,727 giây |
| GET Quick Settings | 2,774 giây |
| GET trạng thái setup AP | 0,806 giây |
| GET hotspot summary | 2,532 giây |
| GET danh sách Wi-Fi đã lưu | 4,078 giây |
| Công việc overview hoàn tất, gồm polling | 11,158 giây |
| CSS khi có nhiều GET trạng thái đồng thời | 3,752 giây |
| Trang Manage trong cùng mẫu đồng thời | 3,703 giây |
| Chrome, khoảng 25 giây quan sát | 22 request; 4 GET header |
| CSS/JS chính của Tổng quan | khoảng 79 KiB, chưa nén |
| Lỗi JavaScript trong mẫu browser | 0 |

Một profile đọc trạng thái riêng lúc hệ thống ít bận hơn mất khoảng 1,7 giây.
Vì vậy không thể quy toàn bộ 8–11 giây cho riêng một lệnh modem: tải đồng thời,
khởi tạo subprocess và hàng đợi cũng góp phần đáng kể.

RAM khả dụng tại mẫu API khoảng 119 MiB; tổng RSS của 10 tiến trình Python ở mẫu
khác khoảng 140 MiB (cộng RSS có thể đếm trùng trang dùng chung, không phải PSS).
Swap đang dùng nằm trên zram, khoảng 171 MiB; swap khác đang dùng 0. Trong mẫu
10 giây không có tăng pswpin/pswpout/major faults. Chưa có bằng chứng swapping ra
eMMC gây chậm trong lần đo này. Không suy diễn rằng hệ thống luôn đủ RAM ở mọi tải.

## Các điểm cần xử lý

| Ưu tiên | Bằng chứng trong nguồn | Hệ quả và hướng xử lý |
| --- | --- | --- |
| P0 | `hosting.py` GET `/api/header` gọi `backend.call('status')` đồng bộ; mỗi listener ở `hosting_device.py`/`lan_device.py` chỉ có 2 thread | Hai yêu cầu đọc chậm có thể giữ hết thread và làm HTML/CSS/API khác phải xếp hàng. Tách thu thập telemetry khỏi thread HTTP, một công việc đang chạy cho mỗi nguồn; trả pending/stale rõ ràng. |
| P0 | `portal_nav.js` gọi header riêng; `quick.js` gọi lại header sau GET quick; overview job đọc lại Wi-Fi/modem trong `hosting.py:REMOTE` | Cùng một màn hình đọc lại cùng nguồn. Một nguồn trạng thái hiển thị và một Promise dùng chung trong mỗi tab; không để mỗi component tự đọc modem. |
| P1 | `LocalWifi.call()` khởi chạy Python và thực thi REMOTE cho mỗi lần đọc; overview gọi cả system/Wi-Fi/services | Tốn khởi tạo/import và lệnh NM lặp. Coalesce các lần đọc trùng, tách mẫu nhanh (RAM/uptime) khỏi modem/service ít đổi. Không cache kết quả kiểm tra trước thao tác. |
| P1 | `setup.js` đọc header mỗi 5 giây bên cạnh header chung mỗi 15 giây; một số refresh không có cờ đang đọc hoặc timeout | Có thể chồng request khi USB bận; cần giới hạn một request đang chạy, backoff khi lỗi, dừng khi tab ẩn và timeout cho đọc trạng thái. Không tự gửi lại hành động ghi. |
| P1 | `QuickSettings.status()` gọi `tethering.status()` hai lần | Đọc lại trạng thái dịch vụ/nft trong cùng mẫu; lấy một lần rồi dùng lại, giữ nguyên kiểm tra thật khi thao tác. |
| P1 | `system_snapshot()` duyệt toàn bộ journal modem để tính SMS mỗi lần; `service_snapshot()` gọi lần lượt dịch vụ | Chi phí tăng theo lịch sử. Tổng hợp số đếm riêng, làm mới dịch vụ ít thường xuyên hơn; không xóa lịch sử SMS hoặc bỏ bước xác minh. Chưa benchmark lịch sử lớn. |
| P2 | Mọi response, kể cả static assets, đều `no-store` | Tải lại khoảng 79 KiB tài nguyên chính khi chuyển trang. Chỉ cân nhắc asset có phiên bản/hash; HTML/API/auth/file riêng vẫn no-store. Đây không phải nguyên nhân chính của 9 giây chờ dữ liệu. |
| P2 | File manager tính revision/hash và duyệt cây; các thao tác ZIP lớn chạy riêng theo yêu cầu | Có thể gây tải khi upload/unzip, nhưng không thấy là nguyên nhân ở mẫu mở Tổng quan. Giữ transactional checks; benchmark dữ liệu giả trước khi thay cơ chế lưu file. |

Trạng thái ModemManager là lỗi khác: OpenRC báo stopped trong khi tiến trình và
D-Bus owner vẫn tồn tại. Bản sửa đọc `NameHasOwner` trên **bus daemon** với timeout,
không introspect/activate ModemManager. D-Bus lỗi là UNKNOWN; không biến lỗi đọc
thành “đã dừng”. Dịch vụ đang chạy cũng không tự chứng minh SIM có Internet.

## Phương án để chọn

1. **Khuyến nghị: tối ưu đường trạng thái trước.** Một nguồn telemetry có TTL,
   single-flight và tuổi mẫu; HTTP không chờ modem. Header/Quick/Overview dùng
   chung mẫu hiển thị, gộp polling, giới hạn request và làm mới từng phần độc lập.
   Tối ưu này không cần đổi framework hoặc cài thêm dịch vụ nặng. Đánh đổi: số liệu
   có thể trễ vài giây và phải hiển thị pending/stale/unknown đúng nghĩa.
2. **Sau đó tối ưu backend.** Giảm subprocess và lệnh NM/DBus lặp, một mẫu tethering,
   service/SMS counters có nhịp riêng; đo RAM trước khi tăng HTTP thread. Có thể
   giảm cả độ trễ lẫn CPU. Đánh đổi: thay phần đọc phần cứng cần regression và
   nghiệm thu USB kỹ hơn; không dùng GetAll chứa định danh để lấy tiện dữ liệu.
3. **Cuối cùng tối ưu tải tài nguyên và file manager.** Asset versioning/cache,
   nén phù hợp và phân trang cây file lớn. Đánh đổi: thêm cơ chế invalidation và
   revision; lợi ích Tổng quan nhỏ hơn hai bước đầu. Không đề xuất viết lại UI chỉ
   để đổi thư viện hoặc tắt hiệu ứng khi chưa có bằng chứng đó là nút thắt.

## Điều kiện trước khi triển khai tối ưu

- Auth/Host/Origin/token phải chạy trước khi đọc cache. Không dùng chung cache
  thông tin riêng giữa người dùng hoặc xuất qua Tunnel. Metadata không chứa ID.
- Cache chỉ dùng hiển thị; modem/network/AP/power vẫn đọc thật, giữ lock, consent,
  receipt và rollback. Không tự bật data hoặc gửi SMS/USSD khi chỉ mở giao diện.
- Một producer đang chạy, hàng đợi hữu hạn, TTL/max-age/backoff rõ ràng; quá hạn
  phải unknown/stale, không giả “đang kết nối”. Không cache auth/credentials hay
  receipt của hành động và không tự gửi lại POST khi mất kết nối.
- Regression phải giữ HTML/CSS/power status trả trong mục tiêu dưới 1 giây ở
  fixture có producer telemetry bị chặn và nhiều client; fixture không phải
  hardware PASS. Kiểm tra producer lỗi/USB mất liên lạc/invalidate khi mutation.
- Đo USB trước/sau ít nhất 5 lượt: DOM, số liệu đầu tiên, request count, latency
  trạng thái/tài nguyên, CPU/RAM/swap. Mục tiêu mẫu Tổng quan ấm dưới 3 giây; nếu
  chưa đạt phải ghi số thật và tìm tiếp, không rút ngắn timeout để che lỗi.
- Chỉ triển khai sau test PASS và backup source/config hash để rollback; không
  thay nguồn mạng, firmware, gadget hoặc thử reboot để benchmark giao diện.

Xem [SESSION_HANDOFF.md](SESSION_HANDOFF.md) để phân biệt bản sửa trạng thái/nút
nguồn đã cài với giai đoạn tối ưu hiệu năng còn đề xuất.

Bản sửa trạng thái/nút nguồn **`045ff7e` đã cài**, test 772 PASS/1 skip, CI hai
nhánh PASS. Hash/asset/header và Overview API thật đã xác nhận trạng thái
ModemManager đúng. Chưa thay kiến trúc hiệu năng; không coi bản sửa này là đã
giải quyết xong độ trễ 9–11 giây của Tổng quan.
