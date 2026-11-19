# Tối ưu portal và ghi log — 19/11/2026

Triển khai gói ưu tiên từ
[báo cáo rà USB](DEVICE_PERFORMANCE_REVIEW_2026_11_19.md). Không gỡ package hay
hợp nhất portal/worker. Giữ website, Tunnel, thông tin truy cập, modem/radio,
Wi-Fi/AP, USB gadget, route và firewall. Trạng thái cài và kết quả đo thật được
ghi ở cuối tài liệu khi nghiệm thu, không suy ra từ unit test.

## Thay đổi

- `WebsitePanel` thêm action chỉ đọc `catalog`: đọc/validate registry và revision,
  trả metadata cùng routing, không duyệt cây file để tính dung lượng/số mục.
  FileGator selector dùng action này; bytes/entries chưa đo là `null`, không phải
  0. Action `sites`, kiểm tra file/ZIP/root/revision/transaction và các xác nhận
  thao tác vẫn giữ nguyên để tương thích client cũ.
- Portal JS/CSS có URL chứa hash nội dung. Chỉ GET/HEAD thành công với đúng hash
  được cache public immutable; URL cũ/sai hash/lỗi vẫn no-store. FileGator thật
  đang dùng tên bundle không có hash: bridge gắn hash vào tham chiếu JS/CSS trong
  HTML của package, không sửa upstream package. HTML giới hạn 2 MiB; API,
  download, dữ liệu website riêng, cookie, login, SMS và cấu hình không cache.
  Tài nguyên có tên hash sẵn cũng cần đúng loại nội dung public được phép.
  Hai portal tạo manifest khi khởi động; deploy phải restart cả hai sau khi thay
  source/asset. Không nén mỗi request hoặc thêm dependency/runtime cache đĩa.
- GET telemetry hiển thị ngay mẫu cũ còn trong giới hạn do server kiểm tra, dùng
  dấu stale sẵn có. Pending ban đầu backoff 1/2/4/4 giây trong cửa sổ khoảng
  15 giây; không poll stale mỗi giây. Header có tối đa một lượt đọc tiếp sau hai
  giây khi producer đang refresh. Coalescing, tuổi mẫu, xác thực trước cache và
  invalidation sau thao tác giữ nguyên; không tự gửi lại mutation.
- Setup AP bỏ lượt hỏi NM thụ động khi ý định đã lưu thuộc chủ điều khiển Wi-Fi
  khác. Nhánh pending thực thi/rollback vẫn chạy trước điều kiện thoát này.
  LED theo mạng đọc mỗi sáu giây thay vì ba; LED có thể phản ánh chậm thêm vài
  giây. Không thay profile hay luật LED đã lưu, chu kỳ power/usage/radio/replay.
- `LogRetention` chạy trong vòng lặp worker startup hiện hữu, tối đa mỗi phút,
  bỏ qua lúc power pending. Chỉ xét allowlist service log, không quét website,
  credential, SMS, receipt hoặc backup. Lỗi retention không ngắt worker mạng.

## Chính sách log và đánh đổi

| Log cố định | Ngưỡng xoay | Mỗi archive tối đa | Số archive |
| --- | ---: | ---: | ---: |
| Cloudflared | 8 MiB | 16 MiB | 2 |
| Portal USB | 2 MiB | 4 MiB | 2 |
| Portal LAN / supervisor OpenStick / supervisor Nginx | 1 MiB mỗi log | 2 MiB mỗi log | 2 |

Các ngưỡng là kiểm tra định kỳ, không phải trần tuyệt đối theo từng byte ghi:
log có thể vượt ngưỡng giữa hai lượt hoặc khi worker bận/dừng. Archive là đuôi
file giới hạn, mode 0600. Copy/truncate giữ inode để writer đang mở tiếp tục ghi;
không restart Tunnel/Nginx để reopen log. Như copytruncate thông thường, vài byte
ghi đồng thời lúc copy/truncate có thể mất; đây không phải nhật ký giao dịch.
Refuse symlink, hardlink và file không thường. Bản log trước khi bật retention
được lưu riêng trong backup deployment private; không đẩy lên GitHub.

## Kiểm thử trước cài

- 801 unit/regression PASS, hai Windows skip (quyền symlink và bài bảo vệ link
  dành Linux), exit 0. Có test catalog không gọi listing, auth/origin/registry
  lỗi, URL/hash/304/no-store, bundle FileGator không hash, stale/backoff hữu hạn,
  nhánh recovery trước idle shortcut, inode writer/giới hạn archive/lỗi ghi.
- pip check, self-test ứng dụng và cú pháp toàn bộ JS PASS, exit 0.
- Chrome preview metadata/site switch, iframe mount trễ, lỗi mạng không retry và
  usage thiếu/stale PASS; mutation bị giả lập trong preview, không gửi tới USB.
- Mốc USB trước cài: source khớp `06d151a`, 717 file chủ được bảo vệ, không pending,
  saved-network replay đã hoàn tất hoặc không cần chạy lại ở boot hiện tại.

Năm lượt File Manager trước cài (Chrome 390 × 844, read-only guard làm tắt HTTP
cache): 7,911 / 5,281 / 4,598 / 11,131 / 7,938 giây tới navbar thật; trung vị
7,911 giây. Cách đo cache riêng dùng CDP kiểm soát mutation mà vẫn bật cache:
hai lượt đều 11 asset JS/CSS, không cache hit, mỗi lượt truyền 1.295.665 byte
bao gồm header. Không trộn hai phương pháp thành một phép đo duy nhất.

Mẫu nền riêng 61,93 giây trước cài: CPU tổng bốn lõi 14,21%, 464 tiến trình mới,
RAM khả dụng 142,8–153,2 MiB. Đây là một mẫu với chi phí SSH/probe, chưa phải tải
kiểm soát hay bằng chứng nguyên nhân của từng tiến trình. Không khẳng định mọi
màn/thao tác nhanh hơn hoặc RAM giảm khi chưa đo sau cài.

## Trạng thái bàn giao

Source đã kiểm thử cục bộ; chờ CI đúng commit, sau đó mới cài và đo trên USB.
Chưa nghiệm thu reboot, chuyển Wi-Fi/AP/SIM, tethering, gửi SMS/USSD, thao tác
ghi file thật, độ chính xác traffic SIM, tải nhiều người dùng hoặc soak dài hạn
trong gói này. Lỗi Tunnel public đã ghi trước đó vẫn là vấn đề riêng.
