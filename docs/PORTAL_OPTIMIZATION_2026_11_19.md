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

- 802 unit/regression PASS, hai Windows skip (quyền symlink và bài bảo vệ link
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

## Kết quả sau cài trên USB thật

Source cuối **`747f49c4486e698e9d5bbac7877f48912b43fd92`** đã cài, sau source gói
chính `3bec6b5`. CI Windows đúng source cuối đều PASS, gồm build EXE, self-test và
smoke test: [push](https://github.com/litequang/OpenStick/actions/runs/44493694369),
[PR](https://github.com/litequang/OpenStick/actions/runs/44493705113).
Chỉ nhánh UI/PR #7; chưa merge/release.

| Chỉ số | Trước | Sau |
| --- | ---: | ---: |
| File Manager tới navbar thật, trung vị năm lượt | 7,911 s | 1,102 s |
| Inventory website, trung vị năm lượt | 5.517,703 ms | 20,252 ms |
| JS/CSS truyền lại ở lượt mở thứ hai, phép đo cache riêng | 1.295.665 byte | 0 byte |
| Asset JS/CSS được browser tái sử dụng ở lượt đó | 0/11 | 11/11 |
| CPU tổng bốn lõi, mẫu nền khoảng một phút | 14,21% | 11,65% |
| Chênh lệch bộ đếm `processes` trong `/proc/stat` | 464 / 61,93 s | 317 / 62,04 s |
| RAM khả dụng trong cửa sổ mẫu nền | 142,8–153,2 MiB | 128,3–135,6 MiB |

Năm lượt sau: **3,304 / 1,102 / 1,109 / 1,052 / 1,072 giây**. Trung vị giảm
86,07%; lượt đầu vẫn mất 3,304 giây, không cam kết mọi lần dưới một giây. Hai
cohort này đều dùng guard làm tắt HTTP cache, nên không lấy lợi ích browser cache
để giải thích toàn bộ mức giảm của inventory. Trong phép đo cache riêng có CDP
giữ cache bật và chặn mutation trước dispatch, cả bảy asset portal và bốn bundle
FileGator được tái sử dụng. Số byte 0 chỉ tính 11 JS/CSS, không phải HTML/API hoặc
mọi request của trang; chưa đại diện download/upload hoặc lần đầu mở.

Lần kiểm tra cache đầu bắt được FileGator tự gắn `?<filemtime>` vào bundle URL;
bản `3bec6b5` mới cache được bảy asset portal. Bản cuối thay numeric cachebuster
bằng hash và xử lý cả thuộc tính có/không dấu nháy, có regression test; không
thay query tùy ý có thể mang token. Không gọi lần chỉ cache 7/11 là nghiệm thu đủ.

Mẫu CPU/processes là trước/sau ngắn trong các thời điểm khác nhau, có chi phí
probe/SSH và tải nền, không phải thử nghiệm cô lập từng thay đổi. **Chưa chứng
minh tiết kiệm RAM:** RAM khả dụng sau thấp hơn; hai portal và worker vừa nạp lại
có PSS khác trước, zram thực dùng khoảng 52,5 → 53,5 MiB. Có thể có ảnh hưởng
trang bộ nhớ được làm nóng sau restart, chưa quy nguyên nhân hoặc chứng minh rò
RAM. Không đổi cấu hình zram, không thêm swap đĩa và không gỡ chức năng để làm đẹp
số đo. Cần soak test riêng trước khi kết luận lâu dài.

Lượt ba màn bổ sung (mỗi màn một lượt, cùng guard, không phải benchmark năm lượt)
cho thấy số GET header Tổng quan 6 → 2 và File Manager 10 → 3 trong cửa sổ quan
sát tương ứng. Tổng quan RAM đầu 1,277 → 1,384 s; form Phát Wi-Fi 0,278 → 1,419 s,
summary hotspot 0,586 → 2,627 s. Các mẫu này dao động và **chưa cho thấy mọi màn
đều nhanh hơn**; phần đọc phần cứng NM/MM vẫn có thể chậm, còn là hướng tối ưu
tiếp. Hai response 503 pending ban đầu ở Tổng quan được helper xử lý, không phải
lỗi JS hoặc thao tác bị gửi lại. Không tăng TTL hay bỏ kiểm tra live của action
để che giới hạn này.

Nghiệm thu khác:

- Chrome thật trên USB ở source gói chính: 160 tổ hợp trang/kích thước và tám
  chiều ngang PASS, zero JS error/mutation; không lưu ảnh. Source cuối kiểm tra
  FileGator mount thực tế, không login lần hai, cùng-origin header, hai alias AP
  và tám chiều rộng 320–1280 PASS, candidate browser override OFF.
- Linux fixture trên USB kiểm tra writer giữ inode, tiếp tục append, hai archive
  giới hạn mode 0600, từ chối symlink/hardlink PASS. Fixture dùng thư mục tạm và
  không chạm log dịch vụ thật. Retention thật đã tạo hai archive riêng hợp lệ.
- Lần cài chính thay 25 file, restart portal USB/LAN và worker setup/LED/startup;
  bản sửa một file sau chỉ restart hai portal. Không reboot, đổi mạng hoặc
  restart Tunnel/Nginx. Nguồn/usage worker được kiểm tra tiếp tục chạy sau khi
  nạp lại. Backup source, metadata và log trước retention có checksum riêng,
  chỉ lưu private trên USB, không lên GitHub.
- Kiểm tra độc lập cuối exit 0: 41 file nguồn đúng hash, 717 file chủ được bảo vệ
  không đổi, network/routes/firewall/DNS/gadget/services khớp trước cài, worker
  nguồn/usage tiếp tục tiến, checkpoint riêng hợp lệ và tổng usage không giảm.
  20 GET LAN được xác thực, yêu cầu login và giới hạn quyền USB/LAN PASS; đây là
  session QA tạo trong bộ nhớ, không phải thử nhập lại mật khẩu bằng điện thoại.
  Không pending, backup source/log khớp checksum, sync xong. Raw artifact/helper
  đo vẫn ở `artifacts/` bị Git ignore.

## Giới hạn nghiệm thu

Chưa nghiệm thu reboot, chuyển Wi-Fi/AP/SIM, tethering, gửi SMS/USSD, thao tác
ghi file thật, độ chính xác traffic SIM, tải nhiều người dùng hoặc soak dài hạn
trong gói này. Lỗi Tunnel public đã ghi trước đó vẫn là vấn đề riêng.
