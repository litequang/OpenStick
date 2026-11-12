# Câu hỏi bàn giao cho Codex PC

Nghiên cứu Cloud dừng trước mọi thao tác trên thiết bị. Các câu hỏi dưới đây là **tiêu chí thu thập bằng chứng trong phiên PC được chủ thiết bị cho phép riêng**; không phải chỉ dẫn chạy ngay, không yêu cầu flash/erase/reboot. Ưu tiên đọc và che mọi serial, IMEI, IMSI, ICCID, số điện thoại, credential, GUID đĩa và nội dung SMS trước khi chia sẻ.

## A. Trước khi chọn image: định danh và bảo toàn đường quay lại

1. PCB thật in gì trên cả hai mặt? Có đúng `FY_UZ801_V3.2` không? Chụp/ghi rõ chip WCNSS/RF, eMMC, SIM/eSIM và mọi revision. Android `ro.product.board=ALK` hiện có [không đủ định danh PCB](https://github.com/litequang/OpenStick/blob/232fb377334c07cabf3f0ec19dc300e1b9eadcf3/docs/HARDWARE_VALIDATION_v0.1.1.md).
2. Stock firmware/build/baseband/region và kernel chính xác là gì? Lưu hash các blob modem/WCNSS và bản đồ phân vùng theo đúng máy; kiểm tra từ nguồn stock, không chép firmware cộng đồng bị gắn nhầm [V3.0/V3.2](https://github.com/OpenStick/OpenStick/issues/46#issuecomment-1705546392).
3. Người dùng đã cho phép **full backup riêng** chưa? Nếu có, backup user area + phân vùng modem/NV/persist và xác minh cả GPT chính/dự phòng, readback/hash, manifest, bản sao thứ hai đã đạt chưa? Tài liệu hiện tại chỉ xác nhận GPT chính và mẫu nhỏ [R1](UPSTREAM_EVIDENCE.md).
4. Có đường UART độc lập, bootloader/EDL nhận diện đúng PCB và phương án khôi phục được review/diễn tập an toàn theo nhiệm vụ riêng không? Ai giữ backup và thao tác nếu USB/SSH không lên? Không coi một ảnh flash có sẵn là recovery đã chứng minh.

## B. Nếu sau này Debian được triển khai trong nhiệm vụ khác

5. Image, kernel release và hash, `.config`, DTB filename/hash/compatible thực tế là gì? DTS `msm8916-yiming-uz801v3` [ghi model V3.0](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/msm8916-yiming-uz801v3.dts). Boot log có probe lỗi, firmware request thất bại, remoteproc/rmtfs crash hay watchdog không?
6. `ip link`, sysfs USB gadget/UDC, host USB enumeration và `sshd` có cho đường SSH quản trị thực sự không? Host có nhận RNDIS/ECM/NCM phù hợp? DHCP/địa chỉ/SSH hoạt động trước và sau khi LTE rớt không? Nếu không có USB networking, UART còn truy cập được chứ?
7. WCNSS probe và `wlan0` có xuất hiện không? Driver/firmware/NVRAM tên, hash nào được nạp? `iw list` có managed/STA không; scan, association, DHCP, DNS, giữ kết nối và reconnect có thành công? AP thành công không thay thế câu trả lời STA.
8. MPSS và ModemManager thấy modem/port nào (`rpmsg*`, `wwan*`, `wwan0qmi0` hay khác)? SIM PIN/registration/operator/signal/band/APN/bearer/IP/DNS/traffic thực tế ra sao? Nếu `registration: idle` dù có signal như [issue #97](https://github.com/OpenStick/OpenStick/issues/97), lưu log chẩn đoán đã ẩn định danh và tách lỗi firmware/MCFG, nhà mạng, RF, APN.
9. Trên đúng SIM/firmware và operator, SMS **gửi và nhận** có hoạt động, với trạng thái gửi/nhận và encoding đúng không? USSD initiate/respond/cancel có hoạt động với mã test an toàn không? Ghi ModemManager version/capabilities/error code; chỉ chia sẻ log đã che dữ liệu cá nhân.
10. Khi bearer LTE đang truyền lưu lượng, SMS và USSD có hoạt động không? Có làm rớt bearer, route, DNS hoặc làm modem reset không? Lặp sau reconnect và đo trước/trong/sau, không suy từ việc API tồn tại.
11. USB là đường quản trị/gadget hay có uplink Internet từ host thật? Nếu dự kiến Wi-Fi/USB là primary, default route/metric/DNS và health check nào chứng minh mất Internet ngay cả khi link còn? LTE takeover/failback có giữ SSH và tunnel, tránh route flap không?
12. Với Debian thực tế: `uname -m`/`dpkg --print-architecture`, `MemAvailable`, RSS/PSS Nginx + cloudflared + ModemManager, OOM, CPU, dung lượng eMMC trống, log writes, nhiệt độ/thermal throttling và điện áp/nguồn USB đo dưới tải ra sao? Có chạy ổn định 24 giờ (mục tiêu roadmap) rồi dài hơn không? [Báo cáo V3.2](https://github.com/OpenStick/OpenStick/issues/46#issuecomment-1762124078) có hiện tượng im sau vài giờ/ngày.

## Đầu ra Codex PC nên trả lại

- Bảng cho từng câu: `PASS`/`FAIL`/`NOT_TESTED`, phiên bản board/firmware/kernel/DTB, thời điểm, phương pháp, log đã lọc, giới hạn.
- Phân biệt quan sát từ **Android stock** và **Debian sau này**; giữ nguyên phiên bản image/driver/firmware của mỗi lần thử.
- Mọi kết quả `FAIL` về USB quản trị, WCNSS/MPSS, registration hoặc recovery phải được báo rõ trước khi đề xuất Hybrid Mode. Không gắn nhãn hardware `VERIFIED` chỉ bằng tài liệu upstream.
