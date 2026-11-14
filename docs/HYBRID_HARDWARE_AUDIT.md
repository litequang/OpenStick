# Phase 01 — Hardware discovery và Compatibility Audit

Ngày 2026-11-12. Có USB thật trong phiên audit. Báo cáo đã lọc: [hardware-audit-observed.json](hardware-audit-observed.json); schema: [hardware-audit.schema.json](../uz801_manager/schemas/hardware-audit.schema.json). Timestamp UTC nằm trong JSON. Không dùng fixture để gắn nhãn hardware VERIFIED.

## Quy ước trạng thái

- **VERIFIED**: phép quan sát cụ thể trên Android hiện tại thành công, ở phạm vi fact được ghi.
- **UNVERIFIED**: chưa thử chức năng, thiếu bằng chứng hoặc không nhận diện được. Không có nghĩa unsupported.
- **BLOCKED**: không thể hoàn tất phiên audit, như mất USB, sai giao thức, thay transport hoặc hết budget. Observation của phiên không hoàn chỉnh bị hạ xuống UNVERIFIED.

Tổng thể compatibility vẫn UNVERIFIED, deployment NO_GO, flash_enabled=false. Chưa có phép thử Debian, SMS/USSD, LTE bearer, Wi-Fi STA hoặc failover.

## Kết quả trực tiếp trên Android

| Lớp / hạng mục | Bằng chứng thu được | Trạng thái và ý nghĩa |
|---|---|---|
| Model / build properties | UZ801, msm8916_32_512, board ALK, platform msm8916, Android 4.4.4 | VERIFIED với thuộc tính phần mềm; không chứng minh PCB V3.2 |
| Board vật lý | Chưa đối chiếu ảnh/chữ in/linh kiện | UNVERIFIED |
| Kernel | release 3.10.28 từ /proc/version | VERIFIED kernel hiện tại; kernel Linux mục tiêu khác là UNVERIFIED |
| Device tree | /proc/device-tree/model và compatible không đọc được | UNVERIFIED; không kết luận thiếu DTB hoặc tự chọn DTB uz801v3 |
| RAM / eMMC | 397824 kB; XINYH; 7569408 × 512 = 3875536896 byte | VERIFIED theo proc/sysfs |
| Partition layout | 27 mmcblk0p*, start/size đọc từ sysfs | VERIFIED layout kernel; lần audit này không đọc block/GPT/calibration |
| USB gadget | VID:PID 05c6:90b6, functions được nhận diện diag/rndis, enabled=1, state=CONFIGURED | VERIFIED cấu hình đang báo; không thay USB functions hoặc mở diag |
| Giao diện | wlan0/rndis0 up; rmnet0..7 và rmnet_usb0 down; lo unknown | VERIFIED trạng thái quan sát, không suy ra Internet/SIM đăng ký hoặc AP/STA mode |
| Wi-Fi driver/module | wlan, cfg80211, wlan.ko, phy0, thư mục firmware wlan | VERIFIED thành phần hiện diện; chipset/firmware cụ thể và STA/AP capability UNVERIFIED |
| Modem transport/node | smd*, smdcntl*, diag; bam_dmux, cdc_ncm | VERIFIED hiện diện. Không suy ra smd11 luôn là AT hoặc QMI nào sử dụng được |
| Userspace Android | rild, qmuxd, netmgrd, libril/libreference-ril, vendor libril-qc-qmi-1 và libqmi* | Ứng viên RIL/QMI được nhận diện; functional backend SMS/USSD UNVERIFIED |
| Telephony/Wi-Fi software | TelephonyProvider, Mms, TeleService, wpa_supplicant, hostapd | VERIFIED tệp hiện diện; không đọc database/nội dung, không chạy binary |
| Modem firmware trên Debian | Không extract/chuyển firmware trong nhiệm vụ này | UNVERIFIED, không trộn với trạng thái driver/userspace |

Đã nhận 59971 byte SYNC trong 110 request metadata/LIST. 12 phép đọc optional không thành công: hai path DT và uevent của các interface ảo. Không có error string từ thiết bị trong report; không phân biệt thiếu file với thiếu quyền khi SYNC chỉ trả FAIL. Không thu thập IMSI/ICCID/IMEI/số điện thoại/SMS/keys/calibration. Không đọc MAC/IP/SSID, proc/cmdline, proc/cpuinfo hoặc serial number sysfs. CID/boot ID không được đọc bởi module mới.

Giới hạn quan trọng: allowlist chỉ nhận diện một tập driver/chip/property biết trước. Thành phần lạ bị bỏ khỏi báo cáo; không được dùng sự vắng mặt trong báo cáo làm chứng cứ phần cứng không hỗ trợ. Chưa định danh chính xác chip Wi-Fi và revision firmware. Không chạy iw scan, association, AT, RIL RPC, QMI request hoặc kiểm tra Internet để lấp chỗ thiếu đó.

## Thiết kế triển khai

- `audit_transport.py`: chỉ RECV/LIST trên danh sách metadata cố định và tên interface/partition bị giới hạn; không mở /dev node, /dev/block, /data, calibration/firmware binary. Có budget 2 MiB/256 request/90 giây, per-stream timeout, cancellation, giới hạn packet và directory.
- `compatibility.py`: pin transport ở đầu/cuối, parse sang vocabulary/number allowlist, không lưu raw build.prop/uevent/error. Chỉ các property model/product/board/platform/Android được nhận diện được xuất; giá trị ngoài allowlist giữ UNVERIFIED.
- Không thay `adb.py`, `adb_sync.py`, `backup.py`, `gpt.py`, `edl.py`. Reuse framing SYNC qua composition, không nới allowlist backup.
- Report JSON đóng schema, no additionalProperties; Markdown sinh từ cùng report đã validate. Runtime validator bổ sung các ràng buộc không được nâng cấp thành compatibility/flash-ready.
- UI có consent riêng, nút audit thủ công, bảng evidence và tải JSON/Markdown. Không auto-audit khi load trang. Demo không mở USB và không xuất VERIFIED. Dùng cùng token/Host/Origin/Jobs lock với Manager.

## Thao tác bằng giao diện

1. Mở build audit từ branch này trên Windows, dùng URL token của launcher.
2. Tại **Compatibility Audit**, tích quyền audit metadata rồi bấm **Kiểm tra tương thích**.
3. Đọc facts cùng giới hạn. VERIFIED tại dòng thành phần không phải Go cho Debian.
4. **Tải JSON** hoặc **Tải Markdown** xuất báo cáo đã lọc. Không có trường nhập lệnh, channel modem hoặc đường dẫn remote.
5. Nếu USB ngắt, xem BLOCKED và chạy lại khi kết nối ổn định. Không thay driver hoặc USB mode để tự vượt lỗi.

Kiểm tra Phase 01: 152 tests PASS, exit code 0; JavaScript syntax exit code 0. Bao gồm mock ADB devices-only, packet split/short/malformed, byte/request/time budget (kể cả stream nhỏ giọt)/cancel, deny sensitive paths, injection trong property, privacy JSON/Markdown, transport replacement, demo, auth/CSRF/consent và schema validation. Test deadline mới từng FAIL vì fixture trả hết payload trước thời điểm hết hạn; đã sửa fixture để chia từng byte và chạy lại toàn bộ suite, không bỏ test. Chưa khẳng định UI mới đã được kiểm tra trực quan trên mọi viewport; packaged/API smoke được báo ở Phase 04.
