# Bàn giao cho AI tiếp theo — 14/11/2026

**23/11/2026 — mới nhất: đã reboot được duyệt, 3 chu kỳ SIM PASS; điện thoại vẫn FAIL do thiếu NAT.**
Chủ đã cho phép một reboot bình thường và ba chu kỳ data off/on; đã thực hiện
qua DevicePower/QuickSettings. Boot khôi phục AP+SIM, cả ba lần HTTPS buộc qua
SIM đạt, giữ AP/USB, BAM active/on và không thêm lỗi resume. Không hỏi lại quyền
này hoặc tự reboot thêm. Nội dung chờ duyệt bên dưới là lịch sử đã được thay thế.

Chủ tiếp tục báo điện thoại không có Internet, quản trị chậm: nghiệm thu đầu cuối
hiện FAIL. Đọc [AP_NAT_RESTORE_2026_11_23.md](AP_NAT_RESTORE_2026_11_23.md). Trước
reboot có NAT NM; hiện AP shared/DHCP/DNS và SIM trên USB hoạt động nhưng không
còn NAT/masquerade. SYN công khai từ client đi tới SIM, không thấy SYN-ACK về;
gói quản trị/DNS có trả lời. Chưa xác định chính xác tác nhân xóa bảng. NAT riêng
có giới hạn/consent source `ec5a752` đã cài sau push/PR CI PASS gồm EXE: 942 test
PASS/2 skip, nhóm liên quan 106 PASS. Worker tự khôi phục NAT đúng interface SIM,
không toggle AP/data/reboot. 17 hash/722 file chủ và mạng/firewall nền/gadget giữ
nguyên; usage còn, sync. Chrome 4 độ rộng đạt, GET Windows qua USB 200/56 ms.
Đang chờ chủ thử lại điện thoại; không dùng HTTPS tại USB để kết luận đã có mạng
trên điện thoại. Đỉnh nhiệt lấy mẫu 75 C, không thêm lỗi resume; cần theo dõi dài.

**23/11/2026 — lỗi mới sau tắt/bật data: đã bắt lỗi kernel BAM-DMUX, chờ reboot/test.**
Đọc [SIM_DATA_TOGGLE_BAM_PM.md](SIM_DATA_TOGGLE_BAM_PM.md). Lần này NM/MM có
bearer/IP và receipt hoàn tất, proof đúng revision, nhưng 4 HTTPS/2 ping và phép
thử IP trực tiếp đều FAIL. IP/gateway/DNS/route khớp; BAM runtime_status=error,
kernel `Failed to resume: -22`, modem RX/TX không tăng. Đây là bằng chứng lỗi tầng
truyền dữ liệu cho lần này, không suy ra mọi lần cũ hoặc tối ưu UI là nguyên nhân.

Source `fb7ece2` đã cài sau push/PR CI PASS gồm EXE; 920 test PASS/2 skip. Status
không còn nhận bearer kẹt là data usable; Quick Settings cảnh báo driver màu vàng.
Guard trước Network.up của profile SIM giữ riêng BAM-DMUX thức qua data off/on;
không tự mở data, không tác động AP/USB. Radio-off thả hold do guard sở hữu; có
thể tăng điện/nhiệt. Biện pháp giảm rủi ro resume, chưa phải sửa kernel triệt để.
Probe trên USB xác nhận phát hiện/không ghi khi đã error; Chrome thật 4 độ rộng
đạt, 16 hash/721 file chủ/mạng/firewall/DNS/gadget/power giữ nguyên khi cài, sync.

ĐÃ HỎI chủ cho reboot bình thường một lần rồi thử 3 chu kỳ off/on data: đang CHỜ
PHÊ DUYỆT, chưa reboot/chưa thử chu kỳ. Power vẫn auto/error, data SIM vẫn chưa
được khôi phục. Không unbind driver/reset remoteproc/flash hay đổi APN/radio để
che lỗi. Nếu chủ đồng ý, dùng DevicePower có checkpoint/receipt, giữ nguyên USB;
kiểm tra boot restore, hold active/on, HTTPS SIM thật và giữ AP/USB qua 3 chu kỳ.

**23/11/2026 — cập nhật mới nhất từ chủ: truy cập điện thoại đã OK, không còn lỗi lúc này.**
Chủ xác nhận “Hiện tại từ điện thoại vào ok rồi ấy, không lỗi”. Các mục FAIL phía
dưới là lịch sử, không mô tả tình trạng hiện tại. Không tiếp tục reset/đổi mạng để
sửa một lỗi đang không tái hiện. Không có cài mã hay thay cấu hình USB trong lượt
ghi nhận này; mã đang cài vẫn `0026828` cùng các bản mạng/usage trước đó.
Đây là xác nhận truy cập hoạt động do chủ báo, không phải phép đo mới của agent;
chủ chưa mô tả riêng URL, website công khai và trạng thái dữ liệu di động trong
lần xác nhận mới. Không suy ra đã sửa tận gốc lỗi gián đoạn hoặc đạt soak/cold boot.
Không còn cần IP/Gateway chỉ để chứng minh một lỗi hiện đang không xuất hiện.

**23/11/2026 — kết quả điện thoại mới nhất: vào Wi-Fi, không vào quản trị/Internet.**
Đọc mục Owner follow-up trong [báo cáo AP](AP_VISIBILITY_RECHECK_2026_11_23.md).
Nghiệm thu đầu cuối vẫn FAIL, không chỉ đang chờ. Chưa đổi code/mạng hay restart AP
trong lượt kiểm tra này. Một station xác thực có lease đúng subnet, nhưng capture
35 giây chỉ thấy 22 ARP đi ra AP, không frame vào/không tăng RX-TX station; 2 ping
nội bộ tới lease không trả lời, ARP không phân giải dù route đúng wlan0. Probe
HTTP gắn wlan0 tại USB trả 200, DHCP/DNS/8765 được firewall cho phép. Chưa có thao
tác điện thoại được xác nhận trùng lúc capture; không suy ra ngay lỗi driver hay
firewall. Đang hỏi IP/Gateway thật trên điện thoại và kết quả URL chính xác
http://192.168.8.1:8765/overview. Giữ AP để bắt lỗi, không thêm reset mù.

**23/11/2026 — điện thoại báo không thấy/kết nối Wi-Fi; đã khôi phục và sửa kiểm tra profile.**
Đọc [AP_VISIBILITY_RECHECK_2026_11_23.md](AP_VISIBILITY_RECHECK_2026_11_23.md).
Không coi lần nghiệm thu điện thoại đang chờ bên dưới là PASS: chủ đã báo FAIL.
Lúc đó AP/supplicant báo chạy, SIM có Internet, nhưng hai lượt quét Windows không
thấy SSID/BSSID USB. Một lần down/up AP hiện có giữ phiên SIM/tên/mật khẩu/radio;
sau đó directed scan thấy mạng, ba lượt broadcast và một lượt sau cài đều có frame
mới đúng mạng. Một station xác thực, DNS AP đạt; chưa có chủ xác nhận Internet.

Source `0026828` đã cài sau push/PR CI PASS gồm EXE; 907 test PASS/2 skip. Sửa lỗi
NM bỏ hidden=false khi chuẩn hóa profile làm validator chặn bật AP lại. Mặc định
vắng key chỉ chấp nhận khi lưu hidden=false; hidden=true vẫn fail closed. Probe
validator dùng file thật với transport giả, không nhận là thử bật radio/cold boot.
14 hash/721 file chủ và mạng/route/firewall/DNS/gadget giữ nguyên khi cài, SIM và
usage hoạt động, sync xong. Không reboot/reset modem/power-cycle radio hoặc đổi
firmware. Nguyên nhân AP biến mất gián đoạn vẫn UNVERIFIED; không thêm tự restart
mù hoặc nói đã sửa triệt để driver. Chờ trả lời phép thử lại điện thoại mới nhất.

**23/11/2026 — đã sửa và cài phục hồi phiên SIM + thống kê dung lượng.**
Đọc [SIM_RECOVERY_RECHECK_2026_11_23.md](SIM_RECOVERY_RECHECK_2026_11_23.md) và
[SIM_USAGE_BAM_DMUX.md](SIM_USAGE_BAM_DMUX.md). Source mạng `4125c2e`, usage
`a368faa`, nhánh UI/PR #7; cả hai có push/PR CI PASS, gồm Windows EXE. Suite cuối
902 PASS/2 skip Windows, exit 0. Không merge main/dev hoặc tạo release.

Lúc lỗi, SIM đăng ký LTE nhưng NM disconnected, không bearer/IP; proof phục hồi
không khớp revision đang lưu. Bản mới ghi proof ngay trong giao dịch data-on và
chuyển proof/budget qua lần lưu AP, không cần đợi poll. Phép thử race có kiểm soát
trên USB giữ lock qua data-on/AP-save rồi ngắt một phiên: worker thật nối lại sau
42,8 giây, Internet buộc qua SIM đạt, mở lại forwarding AP. Không kết luận nguyên
nhân ban đầu làm rớt modem hoặc quy lỗi tối ưu UI; hành động thật của chủ cách nhau
khoảng 38 giờ, không phải bằng chứng chủ thao tác race 20 giây. Profile toàn bộ
không giữ nguyên: AP hidden/randomization/timestamp và cellular timestamp đổi;
SSID/PSK và field khác không đổi. Không gọi phép so hash profile đó là PASS.

BAM-DMUX trả sysfs RX/TX=0 dù có lưu lượng. Collector hiện đọc stats modem đúng
bearer, v2 giữ tổng/ngày/tháng/start date, không cộng ngược phần lịch sử đã mất.
USB thật tải 1 MiB: RX +1.131.849, TX +61.686 byte (gồm lưu lượng nền/protocol), API
và checkpoint 0600 tăng; không manual tick/reset. Đã kiểm tra Chrome trang USB
320/390/768/1366 px, không lỗi JS/overflow/mutation; không phải test điện thoại.

Cài đặt và kiểm tra cuối giữ 721 file chủ, mạng/route/firewall/DNS/gadget; 13 hash
mạng/band/usage đúng. SIM Internet, AP, USB admin, radio đã lưu đạt, sync xong.
Chỉ restart hai portal + worker startup, không reboot/NM/MM/AP, firmware hay gỡ
package. Hai mẫu tải trực tiếp SIM khoảng 13,39/12,88 Mbps, không phải Speedtest
điện thoại hay cam kết tốc độ. Chờ chủ xác nhận lại Internet qua Wi-Fi điện thoại;
chưa thử nguồn lạnh/soak. Số liệu ngày 21 bên dưới là lịch sử, không ghi đè kết quả
ngày 23. Khi rollback usage v2 phải giữ tổng mới (xem tài liệu), không phục hồi bộ
đếm cũ làm mất phần đã tích lũy.

**21/11/2026 — đã cài hiển thị băng LTE thật, source `9e78ce7`.**
Đọc [SERVING_LTE_BAND.md](SERVING_LTE_BAND.md). Hai CI PASS gồm EXE; 877 test
local PASS/2 skip Windows. Ba file thêm/sửa sau gói phục hồi SIM; không đổi mạng.
Decoder cài trên USB trả B3/1800 MHz, DL 1835,1 MHz, EARFCN 1501. Chrome mở trang
USB thật ở 320/390/768/1366 px thấy `4G · B3`, chi tiết cả SIM và Mạng & sóng;
popover trong viewport, đổi icon/bấm ngoài đóng đúng, không JS error/mutation.
Đây là Chrome trên PC dùng trang USB thật, không phải nghiệm thu điện thoại.
Hash/asset, 721 file chủ, mạng/route/firewall/DNS/gadget giữ nguyên, sync xong.
Không khẳng định thông tin băng chứng minh Internet hoặc sửa nguyên nhân rớt sóng.

**21/11/2026 — đã cài sửa phục hồi phiên SIM, kiểm chứng worker thật.**
Đọc [CELLULAR_RECOVERY.md](CELLULAR_RECOVERY.md). Sáu file ở source `eaa7471`
đã cài sau hai CI PASS; baseline USB thực tế có cả thay đổi cache/radio từ nhánh
dev, không còn được mô tả đầy đủ bởi `747f49c`. Đã tích hợp hai nhánh trên nhánh
UI/PR #7, không merge main/dev. Worker thật nối lại hai lần ngắt có kiểm soát sau
47,3 và 31,7 giây; HTTPS buộc qua SIM đạt. Tắt data giữ tắt sau 45 giây, rồi bật
lại thành công. Giữ AP, radio đã lưu và USB quản trị. Không nhận kiểm thử này là
đã sửa nguyên nhân modem rớt phiên hoặc treo beacon Wi-Fi; chưa thử nguồn/điện
thoại mới. Kiểm tra byte profile đầu tiên không đạt; đối chiếu toàn bộ field ở
lần sau chỉ đổi cellular connection.timestamp, cấu hình/0600 giữ nguyên.
Phần hiển thị băng LTE đang dùng được bổ sung riêng, đọc GetCellInfo; tuyệt đối
không dùng CurrentBands/SupportedBands thay cho băng phục vụ thật. Đọc
[SERVING_LTE_BAND.md](SERVING_LTE_BAND.md) và kết quả cài sau CI trước khi kết luận.

**21/11/2026 — đã khôi phục khả năng nhìn thấy AP bằng một lần restart riêng Wi-Fi.**
Chủ không thấy mạng trên điện thoại. USB báo AP/kênh 6, không ẩn, supplicant
completed; quét Windows mới thấy 13 mạng nhưng không thấy AP USB. Một lần
down/up profile AP hiện có (giữ USB quản trị, tên/mật khẩu, radio và phiên SIM)
đã hoàn tất. Quét mới sau đó thấy AP USB trong 9 mạng; Internet SIM vẫn đạt.
Chủ đã xác nhận điện thoại thấy mạng và vào Internet được sau restart (trả lời
phép thử yêu cầu tắt dữ liệu di động điện thoại). Đây là nghiệm thu điện thoại
thật do chủ xác nhận, không phải fixture. Chưa rõ nguyên nhân treo
phát hoặc độ bền sau đó; không gọi restart là sửa driver triệt để. Không cài mã
mới, nguồn USB vẫn `747f49c`. Chi tiết trong báo cáo SIM bên dưới. Lưu ý giới
hạn client lưu 10 nhưng supplicant đang báo 128; chưa nghiệm thu giới hạn thực.

**21/11/2026 — kiểm tra SIM/hotspot chỉ đọc; chưa cài bản sửa trạng thái.**
Đọc [SIM_NETWORK_DIAGNOSIS_2026_11_19.md](SIM_NETWORK_DIAGNOSIS_2026_11_19.md).
USB hiện có Internet SIM thật (4 phép HTTPS 204, 2 ping); AP/DHCP/DNS, NAT và
luật `wlan*` có mặt, không chặn client. Ban đầu 1 station, sau còn 0; đợt đếm
gói không thấy yêu cầu IPv4 từ client. Đang chờ chủ thử lại điện thoại; không
nhận đó là nghiệm thu Internet qua Wi-Fi. Không đổi mạng/dịch vụ/radio trên USB.
Mã nguồn sửa lỗi core modem báo connected trong khi 3GPP đang searching đã qua
815 PASS/2 skip trên Windows; chưa cài USB (vẫn `747f49c`). Giữ nguyên radio đã
lưu, không tự khóa PLMN hay bật retry dữ liệu để che lỗi. Các số đo 19/11 phía
dưới là lịch sử, có lúc đăng ký/bearer nhưng không có Internet.

**19/11/2026 — đã cài gói tối ưu ưu tiên và đo trước/sau USB thật.**
Đọc [PORTAL_OPTIMIZATION_2026_11_19.md](PORTAL_OPTIMIZATION_2026_11_19.md).
Source đang cài `747f49c4486e698e9d5bbac7877f48912b43fd92`, nhánh UI/PR #7;
chưa merge/release. Catalog metadata không quét cây file; asset portal/FileGator
có hash, hỗ trợ numeric cachebuster thật của FileGator; stale hiển thị ngay,
pending GET backoff, header tối đa một followup; LED 6 s, setup bỏ đọc NM thừa;
log allowlist xoay trong worker startup, archive riêng giới hạn và backup log cũ.
802 PASS/2 Windows skip, hai CI source cuối PASS gồm EXE; Linux log fixture PASS.
Năm lượt File Manager: trung vị 7,911 → 1,102 s; inventory 5.517,703 → 20,252 ms.
Cache browser thật lượt hai 11/11 JS/CSS hit, 0 byte tải lại cho các asset đó.
CPU nền mẫu ~1 phút 14,21 → 11,65%, nhưng RAM khả dụng sau thấp hơn, chưa chứng
minh tiết kiệm RAM; AP/đọc phần cứng còn dao động. Không tuyên bố mọi màn nhanh hơn.
USB thật: 160 layout/8 ngang ở gói chính, FileGator 8 rộng ở source cuối,
không override, không JS error/mutation; không ảnh/trace. Kiểm tra cuối 41 hash,
717 file bảo vệ, mạng/route/firewall/DNS/gadget và 20 GET LAN đạt, worker/usage
tiến, checkpoint riêng hợp lệ, tổng usage không giảm, hai log archive đúng, backup
checksum đạt, không pending, sync xong. Chỉ restart portal và setup/LED/startup
cần thiết, không reboot/đổi mạng/Tunnel/Nginx. Không thử thao tác file hay radio
thật, chu kỳ nguồn hoặc điện thoại; giữ phạm vi nghiệm thu trong báo cáo.

**19/11/2026 — đã rà hiệu năng toàn USB, chưa cài tối ưu mới (mốc trước triển khai).**
Đọc [DEVICE_PERFORMANCE_REVIEW_2026_11_19.md](DEVICE_PERFORMANCE_REVIEW_2026_11_19.md).
Source vẫn `06d151a`, cùng nhánh UI/PR #7. Đo USB thật: RAM khả dụng 114–142 MiB
trong lượt mở ba màn, CPU trung bình tổng bốn lõi 17,12%; zram thực dùng 51,5 MiB,
không có swap đĩa. Nút thắt File Manager: inventory 4,793 s trước navbar 5,882 s;
profile xác nhận listing 676 mục chiếm 3,494/3,505 s, metadata đơn thuần dưới 1 ms.
Ưu tiên metadata nhẹ, asset version/cache, giảm đọc/polling thụ động và giới hạn log.
Package đồ họa/âm thanh là ứng viên giảm dung lượng đĩa, chưa đủ bằng chứng gỡ an toàn;
không được coi dung lượng LLVM/Mesa là RAM đang dùng. Giữ dịch vụ mạng, FileGator,
mDNS/NTP, worker recovery; chưa hợp nhất portal hoặc xóa fallback. Không đổi runtime,
package, mạng hay reboot. Kiểm tra cuối: 32 source/717 file bảo vệ và trạng thái mạng
giữ nguyên, không pending. Đây là audit ngắn, chưa benchmark tải nặng/soak hoặc sau sửa.

**19/11/2026 — đã gộp Phát Wi-Fi và nhúng FileGator.**
Source đang cài `06d151aacec526ef9acf7562365b62a7b33d3bd5`, cùng nhánh UI/PR #7,
chưa merge/release. Đọc [AP_AND_FILEGATOR_UI.md](AP_AND_FILEGATOR_UI.md).
Chỉ còn menu Phát Wi-Fi `/setup/ap`; `/hotspot` và `/setup/recovery` chuyển về
đây. File manager tự mở FileGator trong khung, không cần bấm thêm; Mở riêng là
tùy chọn. Giữ xác nhận, cấu hình, phiên cũ và giới hạn bảo mật cùng origin.
790 PASS/1 Windows skip, hai CI source cuối PASS; USB thật: 160 layout + 8 ngang
ở bản gộp, bản cuối mở FileGator thật ở 8 kích thước, không đăng nhập lần hai,
không lỗi JS/thao tác ghi, hai alias AP đúng. Hash 32 file nguồn, 717 file riêng,
mạng/route/firewall/gadget/dịch vụ và 20 GET LAN đạt; worker/usage tiến, sync xong.
Không thử file-write, radio/AP/tethering, reboot hay điện thoại thật. FileGator
mount Vue sau load; chờ DOM tối đa 20 giây, không retry yêu cầu file. Hai lần
kiểm tra trước đó bắt được báo lỗi tải giả, không gọi chúng là nghiệm thu PASS.
Chủ vừa yêu cầu rà toàn USB để đề xuất tối ưu/loại phần thừa; audit tiếp theo
chỉ đọc/đo, chưa có lựa chọn cho việc bỏ dịch vụ hoặc thay kiến trúc mới.

**19/11/2026 — đã cài màn con riêng và bỏ điều khiển file cũ khi có FileGator.**
Source đang cài `61125aa3dab81001232ab862679fe9bba669645e` trên nhánh
`ui/settings-parent-child-nav-20261119`, PR #7; chưa merge main/dev, chưa release.
Đọc [SETTINGS_CHILD_SCREENS.md](SETTINGS_CHILD_SCREENS.md) và đầu HANDOFF.
Wi-Fi nhận/đã lưu/phát/client/dự phòng, USB, usage SIM, quyền quản trị và website
có URL riêng; chỉ hiện phần đang chọn. FileGator không còn menu/nút upload,
kiểm tra ZIP hoặc editor cũ. Backend thao tác và xác nhận giữ nguyên.
788 PASS/1 Windows skip, hai CI PASS; Chrome preview hai chế độ và USB thật
đạt 176 trang/kích thước + 8 ngang, không lỗi JS. Kiểm tra USB chỉ điều hướng,
không gửi thao tác mạng/nguồn/file/SMS. Hash 28 file nguồn, 717 file bảo vệ,
mạng/route/firewall/gadget và quyền LAN đạt; worker/usage vẫn tiến, sync xong.
Sau kiểm tra toàn bộ ở `66b5850`, bản `61125aa` chuyển thông báo Wi-Fi ra ngoài
phần ẩn; CI hai nhánh PASS, 10 layout Wi-Fi và lỗi đọc thông tin kết nối được
kiểm tra lại trên HTML USB thật (response lỗi mô phỏng, không đọc mật khẩu).
Chủ đã tắt/rút/cắm giữa lần kiểm tra V4 cũ; dùng mốc sau thao tác đó, giữ receipt.
Website nội bộ HTTP 200; public Cloudflare **530 trước và sau lần cài này**,
log Tunnel có `network is unreachable`. Không đổi Tunnel/mạng để che lỗi đó.
Không nhận public Internet, đăng nhập lại mật khẩu hay điện thoại thật là PASS.
Các ghi chú dưới đây là lịch sử; source `4cca1fa` đã được thay bằng bản này.
**19/11/2026 — đã cài nhớ trạng thái cho toàn bộ cài đặt USB.**
Đọc [SETTINGS_STATE_CACHE.md](SETTINGS_STATE_CACHE.md). 14 màn cài đặt khôi phục
ngay trạng thái gần nhất khi mở lại trang/tab rồi đọc nền; không khóa do refresh,
giữ bản nháp đang chỉnh. Cache chọn trường rõ ràng, 8 giờ, theo origin/phiên LAN;
không lưu mật khẩu/username APN/CSRF/SMS/USSD/file contents/receipt. Client inventory
chỉ nhớ trong tab. APN đọc lại username khi Lưu để không xóa nhầm thông tin bí mật.
GET policy/profiles độc lập job; thao tác vẫn xác nhận và kiểm tra backend thật.
793 PASS/1 Windows skip; nhóm ảnh hưởng cuối 115 PASS, cache/usage cuối 2 PASS.
Preview 24 layout PASS; Chrome USB 14 route có chặn GET để kiểm tra restore PASS,
tab mới Quick PASS, không JS error/tràn ngang/mutation. 21 hash/API/asset và file
riêng/mạng/route/firewall/boot đã đối chiếu; followup usage hash/sync đạt. Lần cài
đầu gặp timeout xác minh/khóa rollback; mã mới vẫn còn và đã xác minh độc lập,
không giả định rollback thành công. Xem báo cáo cho archive/giới hạn. Không thử
radio/band/data/power thật, không đổi cấu hình chủ. Mã/báo cáo được ghi cùng commit
trên nhánh dev; xem Git history, CI theo dõi riêng. Không merge main/release.

**19/11/2026 — đã cài khóa mạng gốc, chọn băng LTE và refresh không khóa giao diện.**
Đọc [RADIO_ROAMING_REFRESH.md](RADIO_ROAMING_REFRESH.md) và đầu HANDOFF.
Roaming OFF khóa đăng ký về mạng gốc đọc từ SIM, yêu cầu tắt data và policy trước.
Băng LTE được lọc theo modem; Auto khuyên dùng, nhóm Việt Nam chưa đo tốc độ/phủ sóng.
Modem status dùng GET độc lập; đọc nền giữ nút và bản nháp, chu kỳ 60 giây.
Đã giữ tối ưu stale/backoff/header follow-up và điều hướng đang cài từ nhánh UI,
không ghi đè những tệp khác. Đã cài 10 file, hash/API/asset đạt; cấu hình chủ,
website/Tunnel/SSH, mạng/route/firewall/boot giữ nguyên. 792 PASS/1 skip trước tích
hợp baseline cuối, 32 test ảnh hưởng cuối PASS; preview 24 layout + 4 width PASS,
Chrome USB 8 layout chỉ GET PASS. Chưa thử lệnh roaming/band/reboot thật, không bật
data. Watcher không restart; replay chưa nghiệm thu. Source local chưa commit/push.

**19/11/2026 — đã cài tối ưu telemetry và đo trước/sau trên USB thật.**
Đọc [PORTAL_TELEMETRY.md](PORTAL_TELEMETRY.md) và đầu HANDOFF. GET snapshot có
producer nền giới hạn/TTL, gộp đọc trùng, metric không chờ modem, dịch vụ chỉ đọc
khi mở mục kỹ thuật. Không cache kiểm tra trước thao tác hoặc tự gửi lại POST.
Source đang cài `461e913`, CI hai nhánh PASS; 781 PASS/1 Windows skip, pip/self-test/JS
PASS. Hash đủ 13 file/API/asset thật đạt; cấu hình riêng/mạng/route/firewall giữ
nguyên, worker nguồn/usage vẫn tiến, sync xong. Năm lượt Chrome trước/sau: trung
vị số liệu đầu 14,359 → 0,156 giây, lượt đầu sau cài 1,752 giây. Các lượt sau dùng
mẫu còn mới trong 5 giây, không phải đọc lại phần cứng trong 0,156 giây. Sáu GET
đồng thời vẫn có lượt 2,503 giây; chưa cam kết mọi thao tác dưới 1 giây. Chỉ restart
portal USB/LAN; không đổi mạng, radio, AP, gadget, reboot hoặc thử nút nguồn thật.
Các mục bên dưới là lịch sử; dùng trạng thái đầu tài liệu và HANDOFF làm hiện tại.

**19/11/2026 — đã cài trạng thái ModemManager đúng và menu nguồn trên header.**
Đọc đầu HANDOFF và [PORTAL_PERFORMANCE_AUDIT.md](PORTAL_PERFORMANCE_AUDIT.md).
ModemManager có tiến trình/D-Bus nhưng OpenRC báo stopped; sửa telemetry dùng
NameHasOwner trên bus daemon, lỗi đọc là unknown. Header có menu Nguồn, xác nhận
tắt/khởi động lại, đóng khi bấm ngoài/icon khác/Escape. 772 PASS/1 skip; Chrome
preview 4 layout PASS. Đã cài source `045ff7e`, CI hai nhánh PASS; hash đủ 7 file,
HTML/header/asset và API Overview thật xác nhận modemmanager=true. Power IDLE,
heartbeat/usage vẫn tiến; cấu hình riêng/mạng/route/firewall giữ nguyên, sync xong.
Đã đo USB/Chrome: HTML nhanh, dữ liệu đầu 9–11 giây; không coi hiệu ứng/RAM là
nguyên nhân khi chưa có bằng chứng. Các thử nghiệm tối ưu đã tách khỏi source;
chưa cài kiến trúc cache/collector/thread mới, chưa gửi lệnh nguồn thật.

**19/11/2026 — đã cài nút nguồn lên USB.**
Đọc [DEVICE_POWER.md](DEVICE_POWER.md) và đầu HANDOFF. Source `1d479fa` đã cài;
CI hai nhánh PASS. `/manage` → `/settings/system` có khởi động lại/tắt hệ điều hành,
xác nhận riêng, chờ 5 giây/hủy; không cắt điện USB 5 V. Hash đủ 12 file, trang/API/JS
thật, worker sẵn sàng và tiến heartbeat đã kiểm tra. Không có yêu cầu/receipt nguồn;
worker thống kê SIM vẫn tiến mẫu, checkpoint riêng hợp lệ. Hash cấu hình chủ,
website/Tunnel/SSH, mạng/route/firewall giữ nguyên; dịch vụ chạy và sync xong.
766 PASS / 1 Windows skip; Chrome preview 4 layout PASS. Linux fixture chỉ dùng
executor giả. **Chưa chạy reboot/poweroff thật, chưa nghiệm thu chu kỳ nguồn/LED
hoặc mạng sau chu kỳ nguồn cho hai nút mới.** Không tự thử nút nguồn để nghiệm thu.
Runtime và thông tin truy cập phải ở ngoài Git; xem HANDOFF cho giới hạn kiểm thử.

**18/11/2026 — thống kê dung lượng SIM trên Tổng quan.**
Đã cài source `69111ce`, CI hai nhánh PASS. Hash/HTML/API Tổng quan thật đạt,
worker tự tiến mẫu khi không mở browser; checkpoint riêng mode 0600 hợp lệ.
Cấu hình chủ/mạng/route/firewall giữ nguyên, sync xong; không reboot hay tạo tải
SIM để thử. **Chưa thử cold boot hoặc độ chính xác dung lượng với traffic thật.**
Đọc [SIM_DATA_USAGE.md](SIM_DATA_USAGE.md) và đầu HANDOFF để biết trạng thái cài.
Ô mới có hôm nay/tháng, chi tiết tải lên/xuống, phiên và tổng; UTC+7, tính chung
các SIM trên USB, không nhận diện SIM. Worker cũ thêm một luồng lấy bộ đếm NM/
sysfs thụ động, checkpoint riêng; mở trang không bật data hay sinh traffic probe.
737 PASS / 1 Windows skip; Chrome preview 4 layout PASS, không phải hardware PASS.
Không nhầm có giao diện dữ liệu với có SIM/Internet; không tự thử data/SMS/USSD.

**18/11/2026 — đã cài danh sách client và chặn Internet theo MAC lên USB.**
Đọc [AP_CLIENTS.md](AP_CLIENTS.md) và đầu HANDOFF. `/setup#ap-clients` xem thiết bị,
chặn/bỏ chặn, lưu danh sách riêng; không chặn association hoặc trang quản trị.
Hash mã/asset, HTTP/API và cấu hình riêng đã kiểm tra. MAC giả không kết nối đã
đạt lưu → áp dụng nft thật → đọc lại → bỏ chặn; đã dọn fixture, firewall nền và
cấu hình chủ giữ nguyên, worker chạy lại, sync xong. Không reboot/đổi AP/profile.
Không có client lúc nghiệm thu; **chưa thử packet/điện thoại hoặc Internet SIM**.
Đã sửa fallback BusyBox neighbor và tránh khóa modem chặn GET inventory khi
chưa có SIM; mutation vẫn có lock. 707 PASS / 1 Windows symlink skip, exit 0.
Ghi chú “chưa cài/chờ deployment” bên dưới là lịch sử. Không đưa MAC/IP/tên máy
khách hay policy runtime lên GitHub; không tự chọn MAC thật để thử chặn.

**18/11/2026 — đang bổ sung danh sách client và chặn Internet theo MAC.**
Đọc [AP_CLIENTS.md](AP_CLIENTS.md). UI ở `/setup#ap-clients`; phân biệt association
thật từ driver với lease cũ. Bộ lọc riêng inet forward, giữ DHCP/quản trị; không
phải chặn vào Wi-Fi. Kernel thật không có NF_TABLES_NETDEV; đã chuyển sang inet,
cú pháp đã kiểm tra trên USB. Còn phải nghiệm thu gói cài và client/packet thật;
không lấy fixture hoặc nft --check làm hardware PASS.

**18/11/2026 — mới nhất: đã cài mã tùy chọn AP nâng cao lên USB theo yêu cầu.**
Đọc [AP_ADVANCED_SETTINGS.md](AP_ADVANCED_SETTINGS.md). `/setup` có Hidden SSID,
giới hạn 1–32 client và AP isolation; lưu chỉ staging cho lần phát sau. Hook
supplicant MaxNumSta kiểu string chạy trước mọi AP activation do OpenStick điều
khiển, kiểm tra readback/rollback; không dùng số lease làm giới hạn association.
Mã `393ead1` đã up GitHub trước, CI PASS rồi mới cài theo yêu cầu tiếp theo.
Hash/HTTP/asset/service và cấu hình riêng đã kiểm tra, sync xong; giữ AP/mạng/
firewall, không reboot. Chưa lưu/bật ba tùy chọn; chỉ đọc được thuộc tính backend,
chưa nghiệm thu client thật hoặc Internet SIM. Chủ sẽ lắp SIM sau. Xem HANDOFF.

**18/11/2026 — mới nhất: đã cài lưu/khôi phục chế độ mạng khi bật nguồn.**
Đọc [NETWORK_STARTUP.md](NETWORK_STARTUP.md). Quick Settings lưu lựa chọn thành
công; service mới phục hồi AP trước, chờ SIM đăng ký rồi kết nối theo quyền đã
lưu. Không tự bật data khi tắt máy bay; setup fallback không được giành Wi-Fi
khi đã chọn AP/tắt Wi-Fi. Đã cài, hash đúng, lưu trạng thái SIM + AP đang chạy,
bật service boot, kiểm tra cấu hình riêng giữ nguyên và sync. Chủ cần tháo USB
nên **CHƯA thử reboot/rút-cắm thật**. Đã báo có thể tháo. Lần cắm tới phải kiểm
tra AP/DHCP/quản trị/Internet SIM; không nhận hardware PASS từ fixture/service.

**17/11/2026 — mới nhất: đã cài FileGator 7.16.9 từ GitHub.**
Đọc [FILEGATOR.md](FILEGATOR.md) và đầu SESSION_HANDOFF. `/website` chọn site
→ Mở trình quản lý file; upload ZIP → Unzip, không cần kiểm tra thủ công.
Tên miền/Tunnel giữ OpenStick; unzip giữ backend/journal hiện có. PHP on-demand
+ Nginx loopback riêng, đăng nhập LAN/CSRF giữ nguyên. 637 PASS / 1 skip;
ZIP mẫu 27 MiB trên USB upload/hash/unzip/download đạt trong thư mục tạm.
RSS thêm ~14 MiB idle / ~26 MiB busy; không reboot hoặc đổi mạng/Tunnel.
Chrome mở được FileGator nhưng chưa đạt toàn bộ 4 layout/quay lại. Không ghi
visual/điện thoại/LAN PASS. Không tiếp tục viết file manager riêng. Các ghi chú
ZIP UI cũ bên dưới là lịch sử.

**17/11/2026 — sửa lỗi ZIP 27 MiB bị báo vượt 128 MiB, đã cài USB.**
Nguyên nhân là max_form_memory_size 64 KiB bằng đúng buffer decoder, không
chừa phần boundary còn dở từ chunk nhị phân. Tăng headroom decoder lên 256 KiB,
giữ spill-to-disk 64 KiB và mọi hạn mức file/ZIP/site. HTTP 413 có thông báo
request bị từ chối riêng, không suy thành ZIP vượt hạn mức. ZIP mẫu 28.311.692
byte: trước sửa HTTP 413; sau sửa HTTP 200, kiểm tra thành công trên USB thật,
nút giải nén bật; đã hủy, không xuất bản vào website chủ. 625 PASS / 1 skip.

**17/11/2026 — đã sửa phản hồi và nút giải nén ZIP, cài trên USB.**
ZIP chọn ở ô tải file thường cũng được chuyển sang tự tải/kiểm tra. Card ZIP
ở đầu tab, có shortcut trong File manager; tiến độ/lỗi hiện tại chỗ. Chỉ bật
nút Giải nén vào website sau kiểm tra, vẫn phải xác nhận. 622 PASS / 1 skip;
Chrome demo kiểm tra picker, HTTP lỗi/mất kết nối và không tự gửi lại. Trên
USB thật đã thử ZIP fixture: nút bật, hủy không giải nén; ZIP bị chặn hiện tên
file. Không ghi website chủ, đổi mạng, domain hoặc reboot. Đọc đầu HANDOFF.

**17/11/2026 — mới nhất: đã cài panel nhiều website / file manager trên USB.**
Đọc [WEB_HOSTING_PANEL.md](WEB_HOSTING_PANEL.md) và đầu SESSION_HANDOFF.
8 website tĩnh, root riêng, tên miền lưu riêng và Apply có xác nhận; DNS vẫn
thủ công/chưa xác minh. File manager có thư mục/tìm kiếm/sửa/copy/move/rename/
xóa/tải xuống, upload 32 MiB/file, ZIP 128 MiB, website 256 MiB. ZIP kiểm tra
riêng trước publish, rollback và journal khôi phục khi gián đoạn; không atomic
nhiều file đối với Nginx. 621 PASS / 1 Windows skip, browser demo và read-only
USB 12 layout PASS; fixtures filesystem thật 2 MiB và ZIP/copy/move PASS.
Không áp dụng domain, đổi DNS, sửa website chủ, restart Tunnel/Nginx hay reboot.
Chỉ restart hai portal; cấu hình riêng và mạng giữ nguyên. Các lỗi MM/DHCP cũ
vẫn mở. Không tự sửa mạng/firmware trong khi phát triển panel web.

**16/11/2026 — mới hơn: nhiều APN và dọn các nút mạng cũ.**
Đọc [UI_ACTION_AUDIT_2026_11_16.md](UI_ACTION_AUDIT_2026_11_16.md).
APN có danh sách tối đa 20 tên riêng: lưu/sửa không áp dụng, Apply riêng và
không bật data; không nhận diện SIM. Bỏ luồng gộp SIM→AP, data-off riêng,
start/stop setup AP cũ và đổi RAT/gửi nhanh trong USSD. Chỉ giữ UI xử lý
hotspot trial nếu pending. Fallback on/off chỉ lưu, không dừng AP. Luồng
setup Save → một reboot giữ nguyên. Các ghi chú "chỉ một APN" sau đây là cũ.
Không tự kiểm thử SMS/USSD hoặc APN nhà mạng. Lỗi MM và cold DHCP vẫn mở.

**16/11/2026 — MỚI NHẤT: đã cài popup Quick Wi-Fi, APN nâng cao và root → Tổng quan.**
Đọc [bàn giao mới](QUICK_WIFI_APN_2026_11_16.md). Tổng quan ngoài cùng bên phải.
Đã sửa cache quét rỗng sau AP; hai lượt AP → saved station thật đạt, Wi-Fi có
Internet. APN có auth/credentials/IP/roaming, chỉ lưu; 20 offline roundtrip
trên NM thật đạt, không thay APN thật. Chủ đã tháo SIM; chưa kiểm thử custom
APN hoặc chuyển AP → STA giữ SIM sau bản sửa. 573 PASS / 1 Windows skip.
**Cold replug tethering hiện có lỗi lease PC:** Windows giữ lease quản trị cũ,
không gateway/DNS, dù device sharing ON. Không lấy hai reboot PASS trước làm
chứng nhận cold boot/PC mới. USB admin, Wi-Fi và website vẫn hoạt động.
Không tự sửa initramfs/gadget/firmware hoặc renew/reset Windows để che lỗi.
Checkpoint cuối: Wi-Fi station, data intent OFF, saved tether ON; đọc mới
trước khi đổi mạng. Website/Tunnel/LAN/SSH/radio được giữ nguyên.

**16/11/2026 — MỚI NHẤT: Quick Settings đã cài và thử trên USB có SIM.**
Các ghi chú “source only / chưa cài / không có SIM” bên dưới là lịch sử.
Đọc [báo cáo phần cứng](QUICK_SETTINGS_HARDWARE_VALIDATION_2026_11_16.md)
và [USB tethering](USB_TETHERING.md) trước khi tiếp tục. Tổng quan và `/quick`
dùng năm ô, không có “Chia sẻ SIM” riêng. Data/AP độc lập; data-off giữ AP/DHCP;
AP-off không tự nối station. Đã sửa UUID trên HTTP, DHCP setup chiếm loopback
và cú pháp nft. Chủ xác nhận điện thoại nhận IP, quản trị và Internet SIM.
PC USB qua Wi-Fi và SIM đều đạt DNS/HTTPS bound 204. Hai chu kỳ data off/on
và kết nối sau một chu kỳ máy bay đạt; không tự data-on khi airplane-off.

Chủ từ chối cài tiện ích PC, chọn lưu chế độ tethering + một reboot USB.
Đã cài worker/hook DHCP, thử off/on bằng reboot thật: Windows tự nhận/bỏ
gateway/DNS, không renew thủ công, reset adapter hoặc phần mềm PC. Không đổi
dispatcher vendor, gadget/VID/PID; chế độ lưu trên USB. Bật sau reboot không
tự kích hoạt SIM. Website/Tunnel/LAN/SSH/radio giữ nguyên; profile USB chỉ đổi
timestamp do upstream ghi khi boot. Checkpoint sau test: AP/data SIM/tethering
đã bật thành công; sau đó chủ tiếp tục thao tác, nên đọc lại trước mọi thay đổi.

**Chưa gọi lỗi MM kẹt “Bearer already being disconnected” đã sửa triệt để.**
Đã có bằng chứng DBus lỗi InProgress trước đó; restart MM một lần không phải
bản vá gốc. Nguồn mới báo DATA_CONNECT_FAILED và fail closed, không tự retry,
đổi APN/RAT hoặc reset radio. Các lượt mới không tái hiện. Không gửi SMS/USSD
theo lựa chọn mới của chủ. 519 pytest PASS / 1 Windows skip; Chrome demo 8
layout và đổi token qua reboot PASS; phân biệt demo với nghiệm thu thật.

**16/11/2026 — Quick Settings: audit thật, mã Phase 1 CHƯA CÀI USB.**
Chủ xác nhận hiện không lắp SIM; MM báo SIM missing không phải kết luận modem
hỏng. Nguồn mới có `/quick`, radio/data intent, receipt, veto watchdog/legacy
và luồng data-off → AP nội bộ có xác nhận. Không cài/restart/đổi mạng trên USB;
USB vẫn là baseline `c704264`. Không nhầm HEAD mới với code đã triển khai.
USB NCM/DHCP quản trị đã đối chiếu Windows; chưa chia sẻ Internet (forwarding
0, không NAT/default route USB). Dispatcher shared hiện rebind UDC nên giữ
tethering khóa. WPA3 bị chặn PMF; MaxNumSta 128 chỉ là metadata userspace.
Xem `docs/QUICK_SETTINGS_PHASE0_AUDIT_2026_11_16.md` và
`docs/QUICK_SETTINGS_PHASE1_SOURCE.md` trước khi tiếp tục.

**16/11/2026 — Đã rà/sửa phần cài đặt và cài lên USB thật:** Chủ không dùng
Computer Use; kiểm tra bằng fixture và Chrome headless. Thanh mục cài đặt
thống nhất; `/setup` hiển thị Wi-Fi hiện tại, đổi mạng station qua API sẵn có,
giữ luồng setup AP reboot một lần. Thêm giải thích nút khóa, giữ bản nháp
chính sách khi hủy refresh, chặn gửi trùng mật khẩu LAN và ẩn credentials.
469 pytest PASS, 1 SKIP Windows; 24 bố cục Chrome preview PASS, không lỗi JS
hoặc tràn ngang. Đã sao lưu và cài 11 tệp, kiểm tra hash/HTTP/dịch vụ; Wi-Fi,
cấu hình, website, Tunnel, radio, quyền SSH và boot ID giữ nguyên. Không tự
gửi SMS/USSD, bật SIM, đổi Wi-Fi hoặc reboot để thử. Xem đầu
`docs/SESSION_HANDOFF.md` và `docs/SETTINGS_UX_REVIEW_2026_11_16.md`.

**16/11/2026 — Đã sửa firewall mDNS trên USB thật:** tái hiện truy vấn A từ
Wi-Fi với TTL 1/64 bị chặn, TTL 255 trả đúng IP. Quy tắc cũ yêu cầu TTL 255
cho cả query; đã thêm đúng ngoại lệ multicast `224.0.0.251`/UDP5353 trên
`wlan0`, giữ quy tắc unicast cũ và không flush firewall. Sau sửa cả ba TTL
đều nhận đúng địa chỉ WLAN, RCODE 0 và transaction ID. Không restart dịch vụ,
đổi Wi-Fi, bật SIM hay reboot. Chủ đã xác nhận IP mở được, rồi xác nhận tên
`openstick.local:8765/setup` mở được trên điện thoại sau sửa và nối lại Wi-Fi.
Client chỉ dùng DNS router vẫn là trường hợp
riêng. Đọc đầu `docs/SESSION_HANDOFF.md` và `docs/LOCAL_MANAGEMENT_ADDRESS.md`.

**16/11/2026 — Đã cài giao diện quản lý/navigation V2 commit `fddda78`
lên USB thật.** Sao lưu bốn tệp trước khi cài, kiểm tra SHA-256 sau khi
cài; Wi-Fi hiện tại, SIM, Tunnel, cấu hình và phiên thử mạng giữ nguyên.
467 pytest PASS, 1 SKIP trên Windows. Dịch vụ quản trị USB và LAN chạy
tốt; trang LAN không có phiên đăng nhập vẫn chuyển đến `/login`.
Kiểm tra mDNS từ PC qua Wi-Fi với TTL 255 xác nhận USB trả đúng IP LAN,
nhưng router gia đình trả NXDOMAIN khi hỏi DNS thường cho
`openstick.local`. Vì vậy chưa thể kết luận Android trên mạng gia đình
truy cập được bằng tên này; cần mDNS ở máy khách hoặc bản ghi DNS trên
router. Xem đầu `docs/SESSION_HANDOFF.md` để biết backup, kiểm thử và
giới hạn nghiệm thu.

**15/11/2026 — Đã chỉnh lại giao diện `/setup` và triển khai lên USB thật:**
Hai thẻ rõ ràng cho USB nhận Wi-Fi và USB phát Wi-Fi (cấu hình chung với
hotspot SIM). Trên điện thoại các thẻ xếp dọc, máy tính xếp hai cột; các
biểu mẫu, cảnh báo và nút lưu đã được sắp lại, thêm nút hiện/ẩn mật khẩu.
Chức năng điều khiển điểm phát nâng cao được thu gọn. Giữ nguyên backend,
SSID/mật khẩu đã lưu, lựa chọn radio, Tunnel, trang web, quyền SSH và kết nối
Wi-Fi hiện tại. Kiểm tra nguồn: 465 PASS, 1 SKIP Windows, 36 test setup PASS;
Chrome preview trên 1280/390/320px không tràn ngang nhưng **chưa thay thế
kiểm thử trực quan trên điện thoại thật**.

**Cập nhật tiếp giao diện nâng cao (cùng ngày):** Bốn nút lớn trước đây được
gom thành hai dòng cài đặt (tự phát khi mất kết nối; phát Wi-Fi thủ công),
mỗi dòng hiện trạng thái bật/tắt hoặc đang phát và chỉ một hành động phù hợp.
Fixture JavaScript đã kiểm tra cả chu trình enable/disable/start/stop; toàn bộ
pytest 465 PASS, 1 SKIP. Đã cài lần hai trên USB, kiểm tra SHA-256, trang web,
dịch vụ Wi-Fi và LAN, không đổi cấu hình Wi-Fi. Sao lưu lần hai:
`/var/lib/openstick/deploy-backups/home-20261114/before-setup-ui-1794751697.tar.gz`.

Đã cài ba tệp `setup.html`, `setup.js`, `portal.css`, xác nhận SHA-256 sau
triển khai, bốn dịch vụ đều started và năm URL HTTP 200. Wi-Fi `wlan0`
không đổi kết nối, không có pending trial; không reboot, không bật dữ liệu SIM.
Backup: `/var/lib/openstick/deploy-backups/home-20261114/before-setup-ui-1794751001.tar.gz`.
Xem đầu `docs/SESSION_HANDOFF.md` để biết phạm vi và giới hạn nghiệm thu.

**15/11/2026 — đã cài bộ chọn LED style mới lên USB thật:** Nhánh
`ui/led-style-gallery-20261115` đã gộp vào `codex/uz801-v32-postmarketos`.
Trang `/settings/leds` có 12 style nhấp nháy/sáng/tắt và 4 bộ style chọn nhanh
cho 6 trạng thái mạng; chỉ bấm **Lưu quy tắc** mới gửi thay đổi xuống USB.
Đã triển khai ba tệp `leds.js`, `portal.css`, `leds.html` sau 465 pytest PASS,
1 SKIP (Windows), 34 test LED PASS. SHA-256 trên USB khớp cả ba; bốn dịch vụ
LED/Wi-Fi/LAN/hotspot đang chạy, sáu tài nguyên HTTP 200. Cấu hình LED đã
lưu, Wi-Fi đang kết nối và pending trial đều giữ nguyên. Bản sao lưu:
`/var/lib/openstick/deploy-backups/home-20261114/before-led-gallery-1794748543.tar.gz`.
Đọc `docs/LED_STYLE_GALLERY_2026_11_15.md` để biết giới hạn phần cứng ba LED
nhị phân. Chưa xác nhận trực quan bằng điện thoại hoặc nhịp sáng của 12 mẫu
trên LED thật; không tự ý bật một bộ style hay thay quy tắc đang lưu.

**15/11/2026 — đã triển khai cấu hình Wi-Fi phát dùng chung lên USB thật:**
`/setup#usb-ap-settings` cho đổi một bộ SSID/mật khẩu/kênh cho Wi-Fi cài đặt
và Wi-Fi chia sẻ Internet SIM; `/hotspot` trỏ về cùng mục, APN vẫn độc lập.
Lưu cấu hình chỉ áp dụng ở lần phát tiếp theo; nếu đang phát hotspot SIM sẽ
không tự ngắt. Không được sửa khi đang có handoff chờ xác nhận. Đã cài đúng 7
tệp portal, sao lưu và xác minh SHA-256 trên USB; 3 dịch vụ đều started, các
trang `/setup`, `/hotspot`, `/overview` và 2 JS trả HTTP 200. Kết nối `wlan0`
trước/sau không đổi, không có pending; **không reboot hoặc chuyển mạng**.
Source đã qua **465 pytest PASS, 1 SKIP Windows**. Chưa kiểm thử thao tác đổi
SSID/mật khẩu hoặc xác minh Internet từ điện thoại sau bản mới. Xem
`docs/SHARED_WIFI_2026_11_15.md` và đầu `docs/SESSION_HANDOFF.md` để biết
đường dẫn bản sao lưu và điều kiện kiểm thử thật.

**15/11/2026 — hotspot SIM thông minh đã cài lên USB:** Khi setup AP đang
phát, `/hotspot` có thể chuyển sang dùng Internet SIM với cùng SSID/mật khẩu,
địa chỉ `192.168.8.1:8765` và `openstick.local:8765`; người dùng vẫn phải
đồng ý dùng dữ liệu SIM, kết nối lại và xác nhận giữ trong 5 phút. Đã cài
`hotspot.py`, `hotspot_web.py`, `templates/hotspot.html` trên USB thật; ba
dịch vụ và HTTP `/hotspot`, `/overview`, `/setup` hoạt động, setup AP vẫn active,
không có pending trial, không bật SIM để thử. Source đã qua **448 pytest PASS,
1 SKIP Windows**. Chưa có kiểm chứng điện thoại + dữ liệu SIM đầu cuối cho luồng
mới; chủ máy cần thực hiện thủ công. Đọc
`docs/SMART_SIM_HOTSPOT_2026_11_15.md` và đầu `docs/SESSION_HANDOFF.md` trước
khi sửa/triển khai thêm. Tuyệt đối không nhầm HTTP 200 với phát SIM thành công.

**15/11/2026 — điều hướng giữa các trang:** Status strip và Tổng quan đã lưu
snapshot hiển thị trong phiên trình duyệt, phục hồi trước khi cập nhật ngầm.
Hai tệp giao diện đã triển khai trên USB thật, kiểm tra HTTP thành công;
436 test PASS, một SKIP do Windows. Xem đầu `docs/SESSION_HANDOFF.md`
để biết đường dẫn backup/rollback và giới hạn kiểm chứng giao diện Android.
Đây vẫn là điều hướng tải trang HTML, không phải SPA.

**Bản mới nhất `272777e`:** đã cài LED theo trạng thái: chọn trạng thái rồi
phối ba màu tắt/sáng/nháy với thời gian riêng. Worker LED được supervise, đọc
metadata mỗi khoảng 3 giây, không đổi mạng hay probe SIM. Cấu hình cũ/baseline
được giữ; deployment không tự bật quy tắc mới. Đã thử driver thật đồng thời đỏ
sáng, xanh lá 200/800 ms, xanh dương 700/300 ms; lấy mẫu đủ hai pha, replay đạt,
sau đó khôi phục đèn/cấu hình chủ. Role thật lúc thử là offline; các role khác
được test bằng metadata giả, chưa nhận là thử chuyển mạng thật. Header/Tổng
quan giữ số liệu cũ trong lúc refresh/lỗi, có đánh dấu cũ; trạng thái ngắt mạng,
mất SIM và số 0 thật vẫn cập nhật. Ô sức khỏe eMMC không có dữ liệu được ẩn;
lượng ghi vẫn giữ. 436 tests pass / 1 skip. Xem phần đầu handoff và
`docs/LED_STATE_RULES_AND_DASHBOARD_2026_11_15.md`. Mới đọc USB: Wi-Fi/data đều
ngắt, không pending; không tự bật SIM theo các checkpoint cũ bên dưới.

**Tên quản trị trên Android đã xác nhận:** cấu hình DNS `5660c77` đã cài.
Android trước đó báo NXDOMAIN dù mDNS trên wlan0 trả đúng AP; đã thêm DNS
thường cho `openstick.local` vào dnsmasq hotspot. Chủ nối lại Wi-Fi và xác nhận
mở tên miền được. PC USB vẫn phân giải/mở cùng tên HTTP 200; probe SIM vẫn đạt.
Hotspot hiện AP/data bật, enabled=true, không pending. Script DHCP setup cũng
đã có DNS nội bộ, mới kiểm tra cú pháp/tham số thật, chưa bật setup để thử bằng
điện thoại. Không restart NM/reboot/nối lại WWAN. Xem phần đầu handoff và
`docs/LOCAL_MANAGEMENT_ADDRESS.md`; kiểm tra lại trạng thái trước thay đổi.

**Cập nhật LED/SIM:** USB đã cài source đến `3bd728a`. Đèn vỏ đỏ/xanh lá/xanh
dương có mục `/settings/leds`, đã thử driver bật/nháy rồi khôi phục; boot replay
đã bật nhưng chưa thử reboot riêng. APN hiện rõ tại `/hotspot#sim-apn`, có nút
lưu riêng không bật data hay đổi mật khẩu Wi-Fi. APN tự nhận đã truy cập HTTPS
204 qua SIM trong lượt thử thật. Lỗi probe cũ đọc sai DNS dạng `A | B` đã sửa;
probe mới buộc cả DNS/HTTPS qua SIM cũng đạt 204. Sau bản sửa, chủ đã xác nhận
điện thoại thấy Wi-Fi USB và vào Internet được; đọc lại USB cũng thấy AP/data
active, Start thành công và probe SIM đạt. Nút giữ chỉ cho bấm khi AP/cellular
đã sẵn sàng. Chưa thử autostart/reboot sau Keep; agent không bấm giữ thay chủ.
Xem `docs/LED_AND_SIM_HOTSPOT_2026_11_15.md` và phần đầu handoff. Checkpoint sau
deploy: không pending, data/AP tắt, 5 profile Wi-Fi lưu/0 active, setup/policy
đang tắt do chủ chọn. Đọc sau đó: AP/data bật, trial còn 222 giây, enabled=false.
Chủ đang thử nên phải đọc lại trạng thái mới, không restart web giữa trial. Chưa sửa
lỗi router nhà cũ, chưa chứng nhận Tunnel public (403 ở lần kiểm tra trước).

Đây là trạng thái phát triển trên USB thật, không chỉ là bản thiết kế giao
diện. Đọc tài liệu này trước khi sửa UI hoặc triển khai lại. Nhánh đang dùng:
`codex/uz801-v32-postmarketos`. Bản Windows v0.1.1 trong README là ứng dụng
backup cũ; panel Linux trên USB là luồng riêng.

**Bản trước cập nhật LED/SIM:** USB đã cài `ea9fcc8`, gồm giao diện `0dda4fc`, địa chỉ
chung `http://openstick.local:8765` qua USB/Wi-Fi/hotspot, cùng icon nhà mạng
và cột sóng. Xem `docs/USB_UI_DEPLOYMENT_2026_11_14.md` và phần đầu handoff.
Trạng thái quan sát cuối là AP cài đặt; không có pending setup, vẫn còn 4
profile station. Một router nhà từng dùng được vẫn chưa nối lại được, còn
router khác nối được sau AP. Khóa/tham số profile mục tiêu khớp backup, không
có denylist hay khóa BSSID trong profile. Chưa giải quyết lỗi riêng router đó.

## Yêu cầu đã thống nhất với chủ USB

- SMS gửi/nhận được bật theo khả năng modem/SIM; dữ liệu SIM mặc định tắt.
  Chỉ bật Internet SIM khi người dùng chọn, không tự cấp quyền dùng dữ liệu.
- Yêu cầu icon mới: SIM hiển thị tên nhà mạng; mục Mạng hiển thị công nghệ và
  cột sóng, bấm xem chi tiết. Icon Wi-Fi thể hiện đang nhận hay phát.
- SMS giống ứng dụng điện thoại: danh sách hội thoại, màn hội thoại riêng,
  màn soạn mới riêng. Không nhúng form gửi SMS vào mọi màn.
- USSD cần phản hồi mới theo từng lần gửi, kể cả nội dung giống lần trước.
  Có nút nhanh `*101#`; không tự gửi lại khi chưa biết kết quả.
- Hotspot cài đặt phải độc lập với SIM/Internet. Điện thoại truy cập để nhập
  Wi-Fi; có cả nút quét/danh sách và nhập tay cho SSID ẩn. Chọn mạng chỉ điền
  tên, không đổi kết nối trước khi bấm Lưu.
- Luồng mới chủ USB yêu cầu: lưu cấu hình → khởi động lại một lần → thử các
  Wi-Fi đã lưu → chỉ phát hotspot nếu không nối được mạng nào. **Luồng reboot
  này đã được triển khai và thử reboot thật thành công trên mạng mới.**
- USB đã nối Wi-Fi có IP nội bộ thì vẫn quản trị được khi mạng mất Internet.
  Không chuyển sang hotspot chỉ vì kiểm tra Internet thất bại.
- Chủ USB muốn tiếp tục tối ưu giao diện từ GitHub và giữ bàn giao đủ chi tiết.

## Truy cập và môi trường

- Máy làm việc: Windows PowerShell, workspace `D:\CODE\USB`, Python trong
  `.venv`. Thiết bị: FY_UZ801 V3.2, postmarketOS v26.06/Alpine v3.24 ARM64,
  kernel `6.12.1-msm8916`, Wi-Fi wcn36xx, NetworkManager 1.52.2.
- USB: `http://172.16.42.1`, SSH `user@172.16.42.1`, sudo không tương tác.
  Không còn phụ thuộc máy công ty. Khóa máy công ty vẫn được giữ.
- Khóa SSH riêng máy nhà: `runtime/usb-ssh/manager_ed25519`; host pin:
  `runtime/usb-ssh/pmos_known_hosts`. Không đưa nội dung khóa lên chat/GitHub.
- SSH cần `-F NUL`, `BatchMode=yes`, `IdentitiesOnly=yes`, `IdentityAgent=none`,
  `StrictHostKeyChecking=yes`, đúng identity và known_hosts nêu trên.
- Package thật: `/opt/openstick/uz801_manager`. USB listener gắn `usb0:80`;
  LAN listener gắn wlan0, port 8765, mật khẩu quản trị có sẵn do chủ USB đặt.
- Hotspot setup dùng `192.168.8.1:8765/setup`. SSID/password riêng được sinh
  trên thiết bị, xem qua trang `/setup` hoặc thẻ kết nối. Không có password mặc định.
- Station dùng IP DHCP: đọc trạng thái/router, không hardcode IP nhà vào repo.
- Địa chỉ chung mới: `http://openstick.local:8765`. Avahi trên `usb0,wlan0`
  tự cập nhật địa chỉ theo DHCP/AP; PC nối USB cũng có listener cổng 8765.
  Không nới Host/Origin thành wildcard; giữ exact Origin theo từng Host.
- Website `/var/www/openstick`, Nginx loopback 8080 và Tunnel đang được giữ lại.
  Không thêm panel quản trị/SMS vào public Tunnel.

## Bản đồ mã nguồn cho người sửa giao diện

| Luồng | Tệp chính |
|---|---|
| USB/LAN Flask và guard | `hosting.py`, `hosting_device.py`, `lan_device.py`, `lan_access.py` |
| Wi-Fi thường, HTML gốc | Chuỗi `HTML` và script `REMOTE` trong `hosting.py` |
| Header/dock/theme | `templates/portal_chrome.html`, `static/portal_nav.js`, `static/portal.css` |
| SMS | `templates/sms.html`, `static/sms.css`, `static/sms_conversations.js`, `sms_archive.py` |
| USSD/mạng SIM | `templates/modem.html`, `modem.py`, `modem_device.py`, `ussd_qmi.py` |
| Wi-Fi setup/fallback | `setup_ap.py`, `setup_web.py`, `templates/setup.html`, `static/setup.js` |
| Hotspot Internet SIM | `hotspot.py`, `hotspot_web.py`, `templates/hotspot.html` |
| Chính sách Internet | `network_policy.py`, `network_web.py`, `templates/internet.html`, `static/internet.js` |
| Tổng quan/site editor | `portal_metrics.py`, `templates/overview.html`, `static_site.py` |

Các đường dẫn trong bảng thuộc `uz801_manager/`. CSS/JS/templates là package
data; build EXE vẫn phải có đủ asset. Không thay Flask portal bằng Sites.

## Đã kiểm tra được

- Wi-Fi installer API từng kết nối được Wi-Fi nhà với đúng khóa, MAC ổn định,
  powersave tắt, timeout dài hơn. Chưa chứng minh chạy Wi-Fi lâu dài ổn định.
- SMS UI/SQLite archive/tombstone/xác minh xóa và chống gửi lại kết quả không
  rõ đã có. Agent không gửi SMS thật. Các fixture dùng tin giả.
- USSD backend typed GI/libqmi: 3 lần prototype, 4 lần production controller,
  2 lần API web thành công, kể cả cùng nội dung. Hai kết quả API còn nguyên sau
  job refresh status. Không công khai nội dung phản hồi hay số thuê bao.
- Thiết bị đã có `py3-gobject3` từ APK chính thức được xác minh chữ ký;
  libqmi/Qmi typelib/qmi-proxy có sẵn. Không dùng lệnh AT thô.
- Hotspot setup thực sự phát WPA2/CCMP; DHCP và firewall chạy. **Chủ USB đã xác
  nhận điện thoại đăng nhập vào được trang cài đặt.** Không bật dữ liệu SIM.
- Quét mới tìm 3 mạng, trở về AP sau khoảng 14 giây. Mạng không tồn tại trả về
  AP sau khoảng 33 giây. Chọn danh sách và nhập tay đều chờ bấm Lưu mới submit.
- Bộ test gần nhất: **379 passed, 1 skipped** (quyền symlink Windows), khoảng
  75 giây. Đây không phải chứng nhận tất cả chức năng phần cứng đã đạt.
- Current và saved radio mode đọc gần nhất đều `[12,8]`. Chủ USB tự chọn;
  không ghi đè bằng `[8,0]` từ tài liệu phiên cũ.

## Lỗi chặn cần ưu tiên

**Đã đối chiếu được với mạng khác: Wi-Fi mới thành công.** Chủ USB nhập
thông tin qua trang setup; USB nhận IPv4 và probe Internet gắn wlan0 đạt.
Sau đó thử worker lưu/reboot thật với keyfile của mạng mới: boot đổi, đúng
profile, DHCP/Internet/LAN login HTTP 200 đều đạt sau khoảng 74 giây. Bài thử
worker dùng lại PSK đã dẫn xuất trong file riêng, không lấy mật khẩu ra chat.

Vì vậy không quy tất cả lỗi về việc ngắt hotspot trong lúc lưu. Lỗi bộ phát
cũ vẫn còn, chưa xác định được chính xác tham số tương thích/cấu hình gây lỗi.

Key tính từ mật khẩu lưu trên Windows đã so sánh khớp PSK trong keyfile cũ,
không in mật khẩu/PSK ra log. Khi thử handoff, wpa_supplicant báo handshake/
WRONG_KEY nhưng kernel đồng thời có `hal_join ... err=-5`,
`hal_config_bss ... err=-5`, `hal_delete_sta_self ... err=7` và đôi khi kernel
warning. Không kết luận đơn giản là người dùng nhập sai mật khẩu.

Hai lỗi cần tách riêng:

1. AP không khởi tạo do PMF mặc định: đã xác định key AES-CMAC `alg=4`, index 4
   bị kernel EINVAL. Đặt `wifi-sec.pmf=1` trong profile **AP** giải quyết phát
   hotspot; đã sửa cả hai bộ sinh profile AP. Giữ WPA2/CCMP.
2. Nhận Wi-Fi từ bộ phát cũ: vẫn cần đối chiếu cấu hình. Reload riêng wcn36xx không giải quyết.
   Thử tháo wcn36xx/btqcomsmd, stop/start riêng WCNSS remoteproc rồi nạp lại
   cũng timeout. Một reboot bình thường sau đó vẫn thấy HAL errors. Không
   tiếp tục lặp các thử nghiệm này như thể chưa làm.

Thử ép station PMF/RSN/CCMP với PSK được giữ lại vẫn timeout. Đã khôi phục
keyfile station từ backup trước thử nghiệm. **Cẩn thận:** `nmcli
connection modify` sau một lỗi auth có thể ghi lại profile khi secret trong
RAM đã bị NM bỏ, gây mất PSK trong keyfile. Chỉnh sửa qua file riêng root-600,
giữ backup và reload profile; không ghi đè khóa tốt bằng profile thiếu secret.
Backup keyfile trước thử nghiệm nằm dưới thư mục private nêu bên dưới.

`Network.active()` chỉ đọc UUID, có thể trả UUID cả khi NM đang configuring
(state 50). **Đã sửa trong setup worker:** phải state 100 kèm IPv4 mới tính
là có LAN; UUID đang thử không còn chặn timer tự cứu. Không probe Internet
để quyết định có giữ LAN hay không. Có regression test cho trạng thái này.

Luồng reboot lưu `phase=await_boot` trước khi yêu cầu reboot, fsync file và
thư mục, giữ AP đến shutdown. Cùng boot không gọi lại reboot; sau boot mới
thử mạng mới rồi tối đa 5 mạng autoconnect đã lưu (mỗi mạng 20 giây). Nếu hết
45 giây mà reboot chưa xảy ra, khôi phục profile/AP; không lặp reboot. Modem
lock/USSD state chặn reboot khi có giao dịch. UI thông báo reboot rõ ràng,
có link LAN mới trên USB và tự nạp lại token sau boot khi cần.

Bài thử âm thật qua HTTP cũng đạt: gửi SSID không tồn tại, USB reboot một
lần, thử mạng mới không được rồi tự nối Wi-Fi tốt đã lưu sau khoảng 100 giây.
Kết quả `SAVED_WIFI_CONNECTED`, không còn pending intent, không lặp reboot.
Unit test bao gồm sai khóa, khôi phục keyfile cũ, mất nguồn giữa intent,
reboot thất bại, trì hoãn khi USSD/SMS bận và NM state 50.

## Tiếp tục thực hiện

1. Đọc status hiện tại qua USB, pending setup intent, NM state/reason và log
   kernel có lọc; không in credentials/nội dung SMS/USSD.
2. Khôi phục keyfile tốt nếu một thử nghiệm làm mất secret. Giữ USB/SSH chạy.
3. Luồng reboot một lần đã cài; giữ các ràng buộc intent/boot/timeout/modem
   lock khi tối ưu giao diện, không tạo reboot loop.
4. Đã thử mạng mới trước, rồi các profile autoconnect khả dụng/ẩn. Giữ LAN
   khi có IPv4 dù Internet không có. Không thay bằng probe Internet bắt buộc.
5. Kiểm tra thật: AP/điện thoại → Lưu Wi-Fi đúng → boot/STA có IP → LAN login;
   sai pass/SSID → AP cũ; reboot giữa intent; nhiều lần lặp. Không bật SIM data.
6. Cập nhật tài liệu với kết quả và trạng thái máy chính xác, deploy source
   khớp commit, push nhánh phát triển. Không gọi phần chưa thử là PASS.

## Triển khai/kiểm thử

`python -m pytest -q`, `node --check` các JS đã sửa, `python -m uz801_manager
--self-test`. Test synthetic setup nằm `tests/setup_ui_fixture.cjs`;
SMS/USSD/network có fixture và unit test riêng. Browser automation trên máy
này chưa sẵn sàng; không có chụp màn hình xác nhận độc lập.

Để sửa UI mà không cần USB: chạy `python scripts/preview_portal.py`, mở
`http://127.0.0.1:8771/modem/sms` hoặc `/setup`. Preview dùng tin nhắn, mạng
và số liệu giả, có banner MÔ PHỎNG; không SSH/đọc SIM/gửi SMS/đổi mạng thật.
Đây là công cụ xem giao diện, không thay thế kiểm thử luồng thật trên thiết bị.

Deploy package vào `/opt/openstick`, không xóa thư mục website/credential/NM.
OpenRC scripts trong `scripts/openrc`: wifi, lan, modem, hotspot, policy,
setup, setup-dhcp. `openstick-setup` ở default runlevel; **không** thêm DHCP
setup vào default, worker chỉ bật nó khi AP setup chạy. Listener LAN gắn
ifindex; nếu tạo lại wlan0 phải restart `openstick-lan` để bind lại.

Khóa dùng chung `/run/openstick/network.lock` và modem lock; không giữ modem
lock rồi gọi API web modem (worker API cũng cần cùng lock). Backup package và
keyfile: `/var/lib/openstick/deploy-backups/home-20261114/`. Dữ liệu evidence
và script cá nhân dưới ignored `runtime/usb-ssh/` chỉ có trên máy hiện tại.
AI trên máy khác cần chủ USB cấp cách truy cập riêng, không có khóa trong repo.

Trạng thái sau bài reboot mới: USB đang nhận Wi-Fi mới có Internet, tự cứu
vẫn bật, không bật SIM data. Keyfile Wi-Fi cũ giữ nguyên. Profile chẩn đoán
tạm đã xóa. Xem handoff để biết kết quả bài thử âm cuối cùng trước push.

RMTFS giữ RAM-shadow `-r`; không flash/erase/ghi NV, không đoán PIN/PUK.
SIM data failover, Internet sharing từ SIM, nhiệt/uptime và boot chỉ cắm sạc
chưa được xác minh đầu cuối. UI có thể được tối ưu độc lập nhưng phải giữ
token/Host/Origin guard, LAN auth, an toàn hiển thị text và trạng thái unknown.
