# UZ801 v0.1.1 — kiểm thử phần cứng

Ngày: 2026-11-12. Baseline: `005957b6a4b6e887323af9c659fe0af17edbd944`, release v0.1.0.
Người dùng đã cho phép đọc thông tin và mẫu nhỏ tối đa 4 MiB; chưa cho phép backup lớn. Không chạy reboot, chuyển EDL, flash, erase, format, restore hoặc provisioning.

## CI baseline

Cả [run main 43140025726](https://github.com/litequang/OpenStick/actions/runs/43140025726) và [run tag 43140115557](https://github.com/litequang/OpenStick/actions/runs/43140115557) đều `completed/success`. Không có test bị bỏ hoặc xóa để xử lý CI.

## Kết quả USB thật

| Hạng mục | Kết quả đo / giới hạn |
|---|---|
| Model / product | UZ801 / msm8916_32_512 |
| Board Android | ALK; chưa xác minh chữ in PCB V3.2 |
| Chipset / platform | Qualcomm Technologies, Inc MSM8916 / msm8916 |
| Android / kernel | 4.4.4 / 3.10.28 |
| Root | adbd có cả real/effective/saved/fs UID 0, đọc qua `/proc/self/status` |
| RAM | MemTotal 397824 kB; không đồng nghĩa toàn bộ RAM vật lý |
| eMMC | XINYH, 7569408 sector × 512 = 3875536896 byte |
| CID / boot ID | Đọc được, đúng định dạng, HMAC đối chiếu lại PASS; giá trị riêng không lưu công khai |
| GPT chính | Header CRC và entry-array CRC PASS; hình học hợp lệ |
| GPT / kernel layout | 27 phân vùng, tất cả start/size khớp sysfs; đủ 10 phân vùng quan trọng đúng chỉ số tham chiếu |
| Protective MBR | Signature 55AA, một entry EE bắt đầu LBA 1, kích thước sentinel FFFFFFFF |
| GPT dự phòng | **CHƯA ĐỌC**, chỉ kiểm tra sau full backup được phê duyệt riêng |
| Mẫu nhị phân | Đọc lặp prefix 64 KiB giống từng byte; CRC và layout giống nhau; có byte 00/0A/0D/1A/FF |
| Full firmware backup / restore | **CHƯA THỬ**; không tạo ảnh firmware thật |

Tổng payload block được lấy vào bộ nhớ trong phiên: 5 × 65536 = 327680 byte. Bộ đếm SYNC nhận ở phía host cùng phần dự phòng header nhỏ: 397552 byte, chưa gồm một ít text metadata của phép thử baseline trước đó. Tổng ở cấp ứng dụng nhỏ hơn 4 MiB. Không đo physical read-ahead của kernel/ADB; SYNC prefix đóng stream sớm và không coi đó là full transfer thành công. Chỉ giữ báo cáo cục bộ đã lọc, không lưu/publish mẫu raw, CID, boot ID, serial, GUID đĩa hoặc build hostname.

## Lỗi tương thích và cách sửa

Host Platform Tools 33.0.1, adb protocol version 1.0.41. `exec-out` với payload printf nhỏ trả `error: closed`; không có stdout. Đây là kết quả của firmware đang cắm, không suy rộng cho mọi ROM Android 4.4.4. Lệnh `uname` cũng không có; phiên bản kernel nay lấy từ `/proc/version`, chỉ hiển thị release, không lộ người/máy build.

ADB SYNC v1 dùng `RECV` qua socket host loopback 5037, ghim transport ID; stream DATA giữ byte nguyên vẹn, DONE xác nhận kết thúc. Mã chỉ triển khai RECV/LIST; không có SEND/ghi/xóa. Metadata cũng đọc qua SYNC. Không gọi PTY cho dữ liệu nhị phân hoặc metadata trong implementation v0.1.1. Phép kiểm tra baseline ban đầu từng dùng shell cho text; đã loại bỏ đường đó khỏi mã mới.

Nguồn giao thức được đối chiếu, implementation viết riêng: [AOSP Android 4.4.4 file_sync_service.c](https://github.com/aosp-mirror/platform_system_core/blob/android-4.4.4_r2/adb/file_sync_service.c), [header](https://github.com/aosp-mirror/platform_system_core/blob/android-4.4.4_r2/adb/file_sync_service.h), [services.c](https://github.com/aosp-mirror/platform_system_core/blob/android-4.4.4_r2/adb/services.c). RECV mở file chỉ đọc; shell cũ có PTY, không dùng làm fallback. SYNC v1 không có seek, nên đọc GPT ở cuối mmcblk0 sẽ kéo theo gần toàn bộ eMMC.

Inspector fallback chỉ xác nhận GPT chính, cảnh báo GPT dự phòng đang chờ và khóa critical-only. Chấp nhận sentinel MBR FFFFFFFF có cảnh báo; các kích thước sai khác vẫn bị từ chối. Không sửa byte trên thiết bị. Dung lượng lấy từ sysfs, GPT phải nằm trong giới hạn và khớp layout kernel.

Backup full được cho phép **thu thập bằng chứng** khi có xác nhận backup riêng trong UI. Chỉ hoàn tất nếu nhận đúng toàn bộ số byte + DONE, identity không đổi, readback/hash đạt, cả hai GPT trong ảnh hợp lệ và giống nhau, sidecar khớp ảnh. Mất DONE, CRC sai, lệch layout, thiếu/thừa byte đều thất bại. Đây không phải cơ chế bỏ qua kiểm tra GPT dự phòng hay chứng minh recovery.

## Giao diện Windows

Đã khởi chạy ứng dụng demo trên Windows tại `http://127.0.0.1:8765`; API HTTP thật ghi nhận demo inspector hoàn tất, 27 phân vùng, flash vẫn khóa. Edge đã mở đúng cửa sổ OpenStick. Browser connector không khả dụng; Computer Use chụp cửa sổ timeout cả lần thử lại, nên không có kiểm chứng ảnh chụp tự động.

Người dùng kiểm tra trực tiếp và xác nhận **cả ba hoạt động**: dashboard 27 phân vùng, bố cục khi thu hẹp cửa sổ, nút Chọn mở hộp thư mục native và trả lại đường dẫn. Đây là manual acceptance của người dùng, không phải screenshot automation PASS. Không đo chính xác viewport 375/768 px. UI live với dữ liệu USB thật chưa được xác nhận trực quan riêng; logic inspector thật đã được thử trực tiếp.

## Bước tiếp theo bằng giao diện

1. Đóng demo, mở bản v0.1.1 thường; giữ cửa sổ launcher chạy. Chỉ cắm một USB cần kiểm tra.
2. Tích quyền **đọc thông tin USB và GPT**, bấm **Kiểm tra USB**. Đối chiếu XINYH, dung lượng, 27 phân vùng, root và cảnh báo GPT dự phòng. Không bật tự kiểm tra nếu chỉ cần một lần đọc nhỏ.
3. Chỉ sau khi chủ thiết bị đồng ý backup lớn: chọn thư mục ổ cục bộ đủ khoảng 8 GiB trống, chọn **Toàn bộ eMMC + phân vùng quan trọng**, tích ô cho phép backup lớn riêng rồi bấm **Bắt đầu sao lưu**.
4. Chờ kết quả. Nếu failed/cancelled/REVIEW_REQUIRED, giữ tệp và xem mã lỗi, không coi là backup đã được chứng nhận. Không resume hoặc ghép tệp từ nhiều phiên.
5. Bấm **Xác minh bản sao lưu** với thư mục vừa tạo để kiểm tra lại. Chỉ kết quả GPT chính + dự phòng PASS mới chứng minh phép kiểm tra đó đã diễn ra. Flash/recovery vẫn khóa.

Đợt kiểm thử này dừng trước bước 3 trên USB thật. Không tạo bản backup lớn để “thử cho chắc”.
