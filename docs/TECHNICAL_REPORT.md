# Báo cáo kỹ thuật — 2026-11-12

## Phạm vi triển khai

Bản 0.1.0 triển khai Phase 1–3 ở mức mã nguồn, mô phỏng và kiểm thử trên Windows. Phase 4 chỉ có đánh giá bằng chứng ban đầu. Phase 5 chưa được triển khai; không có endpoint hoặc wrapper lệnh ghi thiết bị.

Kiến trúc: Flask + Waitress trên IPv4 loopback, HTML/CSS/JavaScript thuần, SQLite history, một worker tác vụ, subprocess ADB có phạm vi lệnh hẹp, PyInstaller onefile. Không cần Node.js, server ngoài, telemetry hoặc firmware tải tự động.

## Nguồn đã đọc

- [Basistiy/openstick-installer README](https://github.com/Basistiy/openstick-installer), [devices.py](https://github.com/Basistiy/openstick-installer/blob/main/openstick/devices.py), [edl.py](https://github.com/Basistiy/openstick-installer/blob/main/openstick/edl.py): danh mục model tổng quát, tìm loader, đọc/ghi raw eMMC. Luồng tự chuyển EDL, ghi ảnh, đổi driver và tìm loader theo tên không được đưa vào manager này. Không thấy chứng nhận riêng cho chiếc FY_UZ801_V3.2 của người dùng trong các tệp đã đọc.
- [iterminatorheart/UZ801-USB_MODEM](https://github.com/iterminatorheart/UZ801-USB_MODEM): thông tin board 3.2, Android 4.4.4/MSM8916, ví dụ dump EDL và kinh nghiệm driver. Đây là kinh nghiệm cộng đồng, chưa phải xác minh firmware hoặc loader cho thiết bị đang có.
- [bkerler/edl README](https://github.com/bkerler/edl), [edl.py](https://github.com/bkerler/edl/blob/master/edl.py), [GPT reader](https://github.com/bkerler/edl/blob/master/edlclient/Library/gpt.py): phân biệt lệnh đọc `rf/r/rs` và lệnh ghi, cách chọn loader/USB backend. Manager chỉ kiểm tra CLI `--help`, không nhúng hay chạy mã Firehose. GPT parser của manager được viết riêng, không sao chép mã GPL.
- [OpenStick/OpenStick](https://github.com/OpenStick/OpenStick): tài liệu nêu ảnh cài thay đổi bảng phân vùng và bootloader. Không lấy việc dự án hỗ trợ MSM8916 làm bằng chứng ảnh V3.0 tương thích V3.2.
- [OpenStick Community backup safety](https://openstick.org/getting-started/backup-safety/): nhấn mạnh giữ các phân vùng NV/calibration và backup trước khi cài. Chỉ dùng làm tài liệu bối cảnh, không dùng để xác nhận an toàn của một loader.

Nguồn được truy cập qua web và đọc mã nguồn thật, không chạy script/installer upstream. Nhánh upstream có thể thay đổi; các nhận xét trên giới hạn ở tệp đã đọc trong phiên triển khai. Chưa có bộ firmware/programmer kèm hash và bằng chứng thử trên đúng board để xác nhận tương thích Debian.

## Device Inspector

Chỉ truy vấn các thuộc tính được liệt kê sẵn: model/product/board/platform/Android, uname, uid, MemTotal, Hardware CPU, sysfs eMMC name/sector count/logical sector. Không gọi `getprop` toàn bộ hoặc ghi log `/proc/cpuinfo` nguyên bản.

CID và boot ID chỉ được dùng tạm thời tạo HMAC với khóa ngẫu nhiên trong bộ nhớ. ADB serial và transport ID giữ nội bộ. Manifest/history/UI không chứa CID, IMEI hay serial. Dùng transport ID ghim phiên kết nối và HMAC để chặn rút/cắm hoặc đổi thiết bị giữa các bước. Đây không phải chứng thực mật mã với thiết bị bị kiểm soát chủ động.

GPT reader kiểm tra protective MBR, signature/revision/header CRC, entry CRC, giới hạn LBA, GUID, tên trùng, phân vùng chồng lấn và sự tương đương giữa hai GPT. Bảng GPT phải khớp start/size sysfs. Giới hạn table <=4 MiB, <=4096 entries. Chỉ hỗ trợ sector logic 512 byte trong phiên bản này.

Các số phân vùng cấu hình tham chiếu chỉ sinh cảnh báo. Đường dẫn block được dựng từ chỉ số entry GPT đã xác minh. PCB vẫn là `NOT_VERIFIED` dù Android báo tên board giống mong đợi.

## Backup và xác minh

Luồng `adb -t <id> exec-out` không PTY, stdout nhị phân được đọc bằng Python, không dùng Windows shell hoặc PowerShell redirect. `cat`/`dd` chỉ có input. Các số offset/count được kiểm tra; stderr remote được bỏ để tránh lẫn binary. Mã thoát remote được gửi bằng trailer cố định, bắt buộc xuất hiện sau đúng số byte dự kiến; còn kiểm tra mã thoát ADB host.

Reader thread + queue giới hạn 8 chunk giúp hủy và timeout khi mất USB; idle timeout 30 giây, bộ nhớ không tăng theo dung lượng ảnh. Tệp `.part` được ghi, hash khi stream, flush/fsync, đọc lại toàn bộ/hash rồi mới đổi tên. Hủy hoặc lỗi giữ manifest failed/cancelled/incomplete. Không có resume ghép nhiều phiên đọc.

Full backup đọc raw một lần, kiểm tra GPT rồi trích các sidecar từ cùng ảnh. Đọc lại các sidecar và đối chiếu hash với phạm vi trong raw. Critical-only đọc từng block riêng, không tuyên bố GPT đã kiểm tra từ backup. Phân vùng calibration toàn 00/FF gây REVIEW_REQUIRED; đây chỉ là heuristic cấu trúc, không giải mã QCN/EFS hoặc chứng minh IMEI đúng.

SHA-256 chỉ bảo đảm các byte cục bộ không thay đổi giữa lần ghi/đọc; không bảo đảm firmware nhất quán trong khi Android vẫn chạy. Không gửi lệnh freeze/mount/sync vì bản này chỉ đọc thiết bị.

## An toàn và lịch sử

- Waitress bind `127.0.0.1`, kiểm tra Host, Origin, Fetch-Site, session token ngẫu nhiên và JSON cho POST. Không bật CORS. CSP chặn script ngoài/inline, frame-ancestors none, no-store.
- Frontend dùng textContent để hiển thị dữ liệu thiết bị, tránh chèn HTML.
- Không nhận executable/remote shell từ API. ADB/EDL path chỉ cấu hình cục bộ trước khi chạy.
- Từ chối UNC, mapped network drive, traversal, symlink/junction. Manifest chỉ nhận đúng tên tệp dự kiến từ layout, không có API tải raw nội dung.
- Một instance ứng dụng trên mỗi tài khoản Windows bằng OS file lock. Worker có khóa thread + khóa file để chặn hai tác vụ; history ghi SQLite transaction, đóng connection sau mỗi lần dùng.
- Exception subprocess không đưa stdout/stderr vào log; UI nhận mã lỗi cố định. Log backup chỉ chứa sự kiện/tên sidecar do ứng dụng tạo.
- Tiến trình chết đột ngột để lại manifest incomplete hoặc failed; history running được đánh dấu interrupted khi mở lại. Không xóa dữ liệu backup tự động.

## EDL và trạng thái cài Linux

Windows PnP inventory chỉ trả kết quả lọc 05C6:9008, trạng thái driver và service rút gọn. Không trả USB instance ID. Driver PASS chỉ chứng minh PnP không báo lỗi, tool PASS chỉ là `--help` chạy được. Programmer checker tính hash và nhận diện ELF ở mức dấu magic; compatibility luôn UNKNOWN khi chưa có bằng chứng.

EDL offline backup chưa có implementation thực thi. Recovery readiness giữ false và ghi rõ các điều kiện còn thiếu. Đây là giới hạn có chủ đích để không nạp một programmer chưa xác minh lên thiết bị.

## Bàn giao

Mã nguồn, test, launcher, build script, executable Windows, README/hướng dẫn recovery/báo cáo/rủi ro. Xem TEST_REPORT.md để phân biệt kết quả mô phỏng với những phép thử chưa thực hiện trên phần cứng.
