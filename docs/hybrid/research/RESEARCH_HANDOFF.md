# Research handoff — UZ801 V3.2 Linux

Ngày bàn giao: 2026-11-12. Branch: `research/linux-compatibility`. Commit nghiên cứu (ma trận, nguồn, câu hỏi): `48b7b7ee2fc2308f3ba84a9ce9308a4229d0dff4`. Base `main` quan sát trên GitHub: `232fb377334c07cabf3f0ec19dc300e1b9eadcf3`. Commit tạo chính tệp handoff này nằm sau commit nghiên cứu; SHA cuối cùng của branch được nêu trong PR và báo cáo bàn giao, tránh tự tham chiếu SHA trong nội dung commit.

## Trạng thái đồng bộ và phạm vi

- Khi bắt đầu, `litequang/OpenStick` trên GitHub có `main` ở SHA nêu trên, một branch `main`, không có PR mở. Đã đọc `docs/HARDWARE_VALIDATION_v0.1.1.md`, `docs/TECHNICAL_REPORT.md`, `docs/TEST_REPORT.md`, `docs/RISKS.md`, `docs/RECOVERY.md` và `WEB_HOSTING_ROADMAP.md` từ commit trên. Không thấy tài liệu audit mới trong `docs/hybrid/research/` tại base.
- Chỉ bốn tài liệu trong `docs/hybrid/research/` thuộc branch nghiên cứu này. Không sửa Windows Manager, ADB transport, backup, test hay source code. Không dùng USB/ADB, không chạy flash/programmer/firmware, không tạo controller hoặc release.
- Các phép đo Android trong `HARDWARE_VALIDATION_v0.1.1.md` **đã commit trên GitHub**, nhưng không có cơ sở nói mọi công việc local của Codex PC đã đồng bộ. Không đánh dấu Debian hoặc chức năng mạng trên thiết bị dự án là hardware `VERIFIED`.

## Kết luận có bằng chứng

1. Debian **có thể boot** trên ít nhất một board được báo là `FY_UZ801_V3.2`, nhưng ngay báo cáo đó mất `usb0`, `wlan0`, `wwan0qmi0` ([Builder #21](https://github.com/kinsamanka/OpenStick-Builder/issues/21)). Một báo cáo khác nêu V3.2 chạy Bookworm với LTE, AP Wi-Fi và USB Ethernet, song có thời điểm im sau vài giờ/ngày và mất ADB sau upgrade ([OpenStick #46](https://github.com/OpenStick/OpenStick/issues/46#issuecomment-1762124078)). Đây là bằng chứng cộng đồng khác image/firmware, không phải phép thử trên máy dự án.
2. DTS `msm8916-yiming-uz801v3` [ghi model **V3.0**](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/msm8916-yiming-uz801v3.dts), dù [builder Debian](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/configs/extlinux.conf) dùng mặc định. [Loader firmware](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/scripts/msm-firmware-loader.sh) đòi blob modem/WCNSS/persist đúng máy. Một tác giả upstream [đính chính nhầm firmware V3.0 là V3.2](https://github.com/OpenStick/OpenStick/issues/46#issuecomment-1705546392). Không có chứng cứ một DTB/firmware V3.0 an toàn cho mọi V3.2.
3. Trên một V3.2 khác, [ModemManager thấy tín hiệu LTE 76% nhưng `registration: idle`](https://github.com/OpenStick/OpenStick/issues/97#issuecomment-4231932018). Có sóng/port QMI không chứng minh LTE Data; APN, SIM/operator, region/MCFG và firmware cần kiểm tra riêng.
4. Builder có RNDIS USB gadget, SSH, LTE/USB NetworkManager profiles và Debian arm64; Cloudflare cung cấp binary arm64/armhf; Nginx có thể phục vụ file tĩnh. Đây là **khả năng phần mềm**, còn tính ổn định, tài nguyên và uplink trên đúng máy chưa được đo. RAM Android dự án là `MemTotal=397824 kB` (~388.5 MiB), eMMC ~3.88 GB [theo audit đã commit](https://github.com/litequang/OpenStick/blob/232fb377334c07cabf3f0ec19dc300e1b9eadcf3/docs/HARDWARE_VALIDATION_v0.1.1.md).
5. Không tìm thấy log V3.2 Debian chứng minh Wi-Fi **STA** (bằng chứng V3.2 chủ yếu là AP), SMS gửi/nhận, USSD, SMS/USSD trong lúc LTE Data, cloudflared chạy, hoặc failover Wi-Fi/USB→LTE. Ma trận để các mục này `CONDITIONAL` hoặc `UNVERIFIED`, không `SUPPORTED_ON_EXACT_VARIANT`.

## Hướng kế thừa từ openstick.de và upstream

[openstick.de/reference](https://openstick.de/referenz-en.html) là bản đồ cộng đồng hữu ích: nó dẫn image OpenStick v1, [OpenStick-Builder](https://github.com/kinsamanka/OpenStick-Builder), [redwoz Docker build](https://github.com/redwoz/msm8916-openstick-build) và postmarketOS. **Không cần viết lại Debian image, kernel, modem stack hay USB gadget từ đầu.** Hướng hợp lý là chọn **một** baseline upstream có nguồn/build rõ, kiểm tra đúng board, rồi thêm cấu hình dịch vụ theo nhu cầu sau khi các cổng phần cứng đạt. Đây là hướng kế thừa để nghiên cứu, chưa chọn image để flash.

| Thành phần có thể kế thừa | Nguồn hiện có | Việc phải xác minh/điều chỉnh cho máy dự án |
| --- | --- | --- |
| Debian arm64, kernel và boot layout | [Builder README](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/README.md), [recipe](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/scripts/debootstrap.sh); redwoz tách [kernel/rootfs/provisioning](https://github.com/redwoz/msm8916-openstick-build/blob/355ebc8/README.md) như một lựa chọn khác. | Chọn một baseline có commit/hash cố định; kiểm tra PCB/boot chain, kernel config, DTB và layout phân vùng. Không trộn các bước của hai builder hoặc image cũ. |
| Firmware loader, modem/LTE, Wi-Fi và USB/SSH | [Builder firmware loader](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/scripts/msm-firmware-loader.sh), [setup](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/scripts/setup.sh), [USB gadget service](https://github.com/kinsamanka/OpenStick-Builder/blob/5724497/configs/system/usb-gadget.service) và NetworkManager profiles. | Giữ firmware modem/WCNSS/NV từ **stock đúng máy**, xác nhận interface/registration/STA và SSH độc lập; APN, USB gadget và địa chỉ có thể khác giữa image/host. |
| SMS/USSD và website/tunnel | ModemManager có [API SMS/USSD](https://manpages.debian.org/bookworm/modemmanager/mmcli.1.en.html); Debian/Nginx và [cloudflared ARM64](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/) có gói sẵn. | Dùng phần mềm có sẵn sau khi chứng minh modem support; chỉ thêm cấu hình/dịch vụ cần thiết, đo RAM/CPU/eMMC, DNS/TLS và thử SMS/USSD đồng thời data. |
| Failover | [NetworkManager route metrics](https://networkmanager.dev/docs/api/latest/settings-ipv4.html) và [connectivity check](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html) là nền có thể dùng. | Phần policy/health check/failback cho Wi-Fi/USB→LTE cần thiết kế và thử riêng. USB gadget `method=shared` hiện là mạng thiết bị cấp cho host, chưa phải USB uplink. |

Giới hạn của site: [guide](https://openstick.de/guide-en.html) và reference nêu quy trình UZ801 **V3.0**; [saga](https://openstick.de/saga-en.html) mô tả **MF800B-E LCD** với GPT 22 phân vùng, còn stock máy dự án có **27 phân vùng**. Site tự ghi là tổng hợp không chính thức, thông tin tới tháng 5/2026. Kế thừa cấu trúc và cách chẩn đoán, **không sao chép** GPT, bootloader, DTB, firmware hoặc lệnh flash từ các board/image đó. Bài [UZ801 V3.2 + postmarketOS](https://ryjelsum.me/homelab/uz801-v3.2-postmarketos/) là đối chiếu boot chain bổ sung, không xác nhận Debian V3.2.

## Điểm còn thiếu và câu hỏi PC phải trả lời

Xem [ma trận](LINUX_COMPATIBILITY_MATRIX.md) để biết trạng thái, URL và điều kiện từng chức năng; xem [danh sách câu hỏi PC](HARDWARE_QUESTIONS_FOR_PC.md) để thu thập bằng chứng. Các điểm quyết định là:

- **Định danh**: chữ in PCB có thực là `FY_UZ801_V3.2` không; stock firmware/baseband/MCFG/WCNSS hash, vùng RF và boot chain là gì? Hiện Android chỉ báo board `ALK`.
- **Bảo toàn/recovery**: full backup được phép, GPT chính/dự phòng, readback/hash, phân vùng modem/NV/persist và đường UART/khôi phục đúng board đã chứng minh chưa? Audit GitHub hiện chưa có full backup và GPT dự phòng.
- **Debian nếu có nhiệm vụ triển khai riêng**: kernel `.config`, DTB/hash/boot log; USB gadget/SSH và UART, WCNSS STA, MPSS/QMI, SIM/registration/bearer/APN thực sự có hoạt động, có sống qua mất mạng và nhiều giờ tải không?
- **Chức năng nâng cao**: SMS hai chiều, USSD, đồng thời với LTE data, Nginx+cloudflared dưới RAM thực, và failover có health check/route/DNS/failback đã thử trên đúng image chưa? USB gadget `method=shared` không mặc định là USB uplink Internet.

## Khuyến nghị

**Tiếp tục nghiên cứu và đối chiếu thiết bị stock theo quyền đọc đã có; tạm dừng Hybrid Mode trên thiết bị.** Không chọn image để flash và không triển khai Hybrid Controller chỉ từ báo cáo cộng đồng. Quyết định thay đổi hệ điều hành đang `BLOCKED` bởi thiếu full backup/GPT dự phòng và phương án recovery được chứng minh; độc lập với đó, USB/Wi-Fi/LTE trên đúng V3.2 còn `CONDITIONAL`, SMS/USSD/failover `UNVERIFIED`. Mọi thử nghiệm thay đổi thiết bị sau này thuộc nhiệm vụ và quyền cho phép riêng.
