# Rà hiệu năng và phần dư trên USB — 19/11/2026

Đã đo trực tiếp UZ801 đang chạy source
`06d151aacec526ef9acf7562365b62a7b33d3bd5`, sau lần gộp màn Phát Wi-Fi và nhúng
FileGator. Đây là **báo cáo điều tra**, chưa cài tối ưu, gỡ package, dừng dịch vụ
hay đổi mạng. Nhánh bàn giao `ui/settings-parent-child-nav-20261119`, PR #7;
không merge/release.

Ưu tiên làm nhẹ đường lấy danh sách website, dữ liệu hiển thị và tài nguyên
trình duyệt. Chưa có bằng chứng thiếu RAM hoặc CPU chạy hết khiến mọi màn chậm.
Có thư viện đồ họa/âm thanh đáng xem xét cho bản hệ thống không màn hình, nhưng
đó là dung lượng lưu trữ; gỡ chúng chưa chắc làm giao diện nhanh hơn.

## Phạm vi và cách đo

- Đọc `/proc`, `/sys`, runlevel OpenRC, thông tin package APK, dung lượng thư mục
  cố định và kích thước log; không xuất nội dung log hoặc dòng lệnh tiến trình.
- Mẫu nền 10,48 giây và mẫu 75,59 giây bao gồm mở ba màn bằng Chrome thật qua USB.
  Mẫu dài gồm cả chuẩn bị/thử lại công cụ đo; không phải benchmark tải liên tục
  được kiểm soát. Có chi phí SSH, sampler và các lệnh đọc trạng thái.
- Đo PSS để phân bổ thư viện dùng chung, không cộng RSS rồi coi là RAM thực dùng.
  CPU tổng tính trên bốn lõi; số tiến trình mới tính toàn hệ thống, gồm công cụ
  kiểm tra và tiến trình ngắn hạn, chưa quy hết cho một dịch vụ.
- Browser 390 × 844, mỗi màn một trang mới trong cùng context, theo dõi thêm
  15 giây sau khi nội dung sẵn sàng. Chặn thao tác ghi trước khi gửi, gồm thao tác
  FileGator; không lưu ảnh/trace, mật khẩu, địa chỉ mạng thật hay nội dung SMS.
- Profile chỉ gọi `WebsitePanel.read()/public()` trên mã đang cài; không gọi
  publisher apply, sửa file hay tạo transaction/lock ghi.
- Đọc mã portal, transport hiển thị, worker mạng/modem/AP/USB/LED, thống kê,
  website/FileGator và cấu hình khởi động liên quan. Không stress test upload,
  unzip, nhiều client AP, traffic SIM, SMS/USSD hoặc reboot trong lượt này.

Artifact thô và helper đo nằm trong `artifacts/` bị Git ignore. Các lượt đo hoàn
tất có exit code 0. Không lấy kết quả kiểm thử giả làm nghiệm thu phần cứng.

## Tài nguyên thực tế

| Chỉ số | Mẫu nền | Mẫu mở các màn |
| --- | ---: | ---: |
| CPU bận trung bình, tổng bốn lõi | 7,76% | 17,12% |
| I/O wait | 0,02% | 0,16% |
| RAM khả dụng trong cửa sổ đo | 130,6–135,4 MiB | 114,2–142,1 MiB |
| Tiến trình mới toàn hệ thống | 92 / 10,48 s | 730 / 75,59 s |
| Trang swap vào / ra | 0 / 54 | 36 / 4 |
| Major page fault | 0 | 49 |

Linux nhận 376,3 MiB RAM. Zram chứa khoảng 171,6 MiB swap logic nhưng thực dùng
khoảng **51,5 MiB RAM** cho dữ liệu nén và quản lý; không có swap đĩa/file đang
hoạt động. Không được cộng swap logic như thêm từng ấy RAM vật lý đã dùng.
PSI memory avg10 ở mẫu nền bằng 0; các mẫu ngắn này chưa cho thấy memory thrashing
hoặc rò RAM kéo dài. Cần soak test riêng nếu nghi ngờ lỗi sau nhiều giờ/ngày.

PSS tại cuối mẫu nền, đã làm tròn:

| Thành phần | PSS | Ý nghĩa |
| --- | ---: | --- |
| Portal LAN | 29,1 MiB | Một ứng dụng Python và cache riêng |
| Portal USB | 28,8 MiB | Một ứng dụng Python và cache riêng |
| Cloudflared | 27,8 MiB | Tunnel chủ yêu cầu giữ |
| NetworkManager | 5,8 MiB | Điều khiển mạng |
| Network startup | 5,2 MiB | Khôi phục ý định, usage, worker nguồn |
| USB tether worker / modem worker | 4,1 / 4,1 MiB | Mỗi worker một tiến trình |
| ModemManager / LED / setup AP | 3,8 / 3,7 / 3,5 MiB | Điều khiển và theo dõi phần cứng |
| PHP-FPM idle | 2,7 MiB | Master; child on-demand đã thoát ở mẫu này |
| Network policy / hotspot worker | 2,1 / 1,6 MiB | Policy và khôi phục phiên |
| Toàn bộ Nginx, bốn tiến trình | 1,3 MiB | Website và FileGator |
| Avahi / chronyd | 0,34 / 0,38 MiB | `.local` và đồng bộ thời gian |
| 19 supervisor / 7 getty | 0,48 / 0,10 MiB | Tổng mỗi nhóm, không phải mỗi tiến trình |

Không có căn cứ gỡ PHP, Avahi, chronyd hoặc supervisor để thu hồi hàng chục MiB.
Hai portal cộng gần 58 MiB đáng nghiên cứu về kiến trúc, nhưng không phải hai
listener có thể tùy tiện bỏ một: USB và LAN có ranh giới quyền truy cập riêng.

## Đường chậm đã xác định

| Màn thật | DOM sẵn sàng | Nội dung đầu sẵn sàng | Request trong lượt quan sát |
| --- | ---: | ---: | ---: |
| Tổng quan | 0,247 s | RAM đầu tiên 1,277 s | 21 / 16,29 s |
| Phát Wi-Fi | 0,166 s | Form sẵn sàng 0,278 s | 14 / 15,29 s |
| File Manager | 0,343 s | Navbar FileGator 5,882 s | 28 / 20,90 s |

Ba lượt hoàn tất không có lỗi JS hoặc thao tác ghi. Có một browser long task
69 ms ở Tổng quan; hai màn còn lại không có. Đây là Chrome trên PC, chưa đại
diện tốc độ vẽ trên điện thoại yếu. Mỗi màn chỉ đo một lượt, chưa phải p95 hay
so sánh trước/sau một tối ưu mới. Một request Phát Wi-Fi còn đang bay lúc đóng
trang; số request và response hoàn tất vì vậy khác nhau.

### 1. Danh sách website quét cây file dù chỉ cần chọn website — ưu tiên P0

`website_panel.py: WebsitePanel.public()` gọi `SiteFiles.listing()` cho mọi site
để tính bytes/entries. `site_files.py` duyệt cây, stat, kiểm tra đường dẫn và tạo
revision từ metadata. **Không đọc/hash toàn bộ nội dung từng file** trong đoạn
này. Kiểm tra đường dẫn là cần cho thao tác file, nhưng không cần lặp lại để lấy
tên và ID website cho thanh chọn FileGator.

Trong lượt browser, `/api/websites` action `sites` mất **4,793 s**; bản thân các
request FileGator đo được tối đa 172 ms mỗi request. Profile đọc riêng trên USB:
một website, tổng 676 mục, inventory 3,505 s; `listing()` chiếm 3,494 s, trong đó
676 lần `path()` cộng dồn 2,668 s. Đọc registry và revision nhỏ mất
0,695 / 0,412 / 0,320 ms trong ba lượt. Có overhead profiler và điều kiện cache
khác nhau; không suy ra thời gian UI sau sửa chỉ từ phép chia này.

**Đề xuất:** endpoint/biến thể inventory nhẹ chỉ trả metadata đã xác thực, quyền
và revision registry. Số file/dung lượng tính khi người dùng mở thống kê, cache
có tuổi mẫu hoặc tải sau. Giữ nguyên kiểm tra root, symlink, journal ZIP,
revision, khóa và quyền trước mọi thao tác file/đổi tên miền.

**Đánh đổi:** thống kê dung lượng có thể đến sau hoặc được ghi rõ chưa đo.
Mục tiêu nghiệm thu: trên cùng cây file, thời gian tới FileGator giảm rõ rệt;
đo tối thiểu năm lượt trước/sau, không cam kết con số trước khi triển khai.

### 2. Đọc trạng thái lặp và tạo tiến trình ngắn hạn — ưu tiên P1

Đã có snapshot TTL, coalescing và service panel tải lười theo
[PORTAL_TELEMETRY.md](PORTAL_TELEMETRY.md); không làm lại các tối ưu đã có.
Tuy nhiên:

- `portal_nav.js: portalReadTelemetry()` chờ mẫu mới, GET lại mỗi một giây khi
  pending/stale trong cửa sổ khoảng 15 giây. File Manager phát sinh 10 GET header
  trong 20,9 giây, dù bộ định kỳ header danh nghĩa là 15 giây.
- `hosting_device.py: LocalWifi.call('status')` còn tạo Python subprocess khi
  cache miss; trong đó có nhiều lệnh đọc NM/MM. Cache USB/LAN độc lập.
- LED đọc vai trò mạng mỗi ba giây khi chế độ LED theo mạng được bật, có thể gọi
  3–4 lần `nmcli`. Setup AP tick mỗi năm giây gọi `active('wlan0')` trước khi xét
  `owns_wifi()`; cần xét đường thoát rẻ trước nhưng giữ nhánh pending/recovery.
- Modem watcher 30 giây, USB worker hai giây và startup năm giây có nhiệm vụ
  replay/rollback. Policy tắt trả trạng thái JSON, **không** phải cứ tắt vẫn chạy
  toàn bộ kiểm tra mạng. Hotspot worker không pending chủ yếu đọc JSON/lock.

**Đề xuất:** hiển thị ngay mẫu cũ còn hợp lệ kèm tuổi mẫu; refresh nền có backoff,
gộp yêu cầu và dừng khi tab ẩn. Từng bước dùng một nguồn đọc thụ động NM/MM theo
sự kiện cho các bên cần hiển thị, có fallback giới hạn; ưu tiên tận dụng worker
hiện hữu. Đọc live và khóa gốc vẫn bắt buộc khi thực thi thao tác.

**Đánh đổi:** thông tin/LED có thể chậm thêm vài giây nếu chỉ kéo chu kỳ; event
collector phức tạp hơn và phải xử lý D-Bus restart, timeout, disconnect. Không
được dùng cache để tự bật data, tự gửi lại POST, bỏ xác nhận hoặc báo Internet
chỉ vì LTE đăng ký thành công. Số fork đo được chưa đủ quy trách nhiệm riêng cho
một worker; cần đếm theo nguồn sau khi sửa, với mẫu ít nhất vài phút.

### 3. Asset tĩnh bị tải lại — ưu tiên P1

`hosting.py` áp dụng `Cache-Control: no-store` rộng; portal tải khoảng 97–108 KB
asset trong mỗi lượt, FileGator thêm khoảng 1,28 MB gồm asset và các request đọc.
Browser không có cơ hội tái sử dụng JS/CSS public như cấu hình cache thông thường.

**Đề xuất:** hash/version URL và cache riêng asset package public; precompress
gzip/Brotli ở bước build nếu đường phục vụ hỗ trợ. HTML, API, login, cấu hình,
SMS, file listing và download website riêng tiếp tục no-store. Không gom cả
response FileGator vào một chính sách cache public.

**Đánh đổi:** phải đổi URL/manifest khi deploy để tránh JS cũ; nén lúc build
tránh tăng CPU mỗi request. Hiệu quả lớn hơn ở lần mở lại và mạng chậm, chưa
phải một số RAM tiết kiệm đã được chứng minh.

### 4. Thống kê SMS có chi phí tăng theo lịch sử — ưu tiên P2

`portal_metrics.py: system_snapshot()` duyệt operation JSON mỗi lần tính số SMS
đã gửi. Đây là rủi ro khi lịch sử dài, chưa chứng minh là nút thắt hiện tại;
không đọc/xuất nội dung SMS để benchmark. Có thể dùng bộ đếm tăng dần hoặc cache
riêng với reconciliation. Giữ receipt, trạng thái chưa rõ và quy tắc múi giờ;
không xóa lịch sử để đạt chỉ số nhanh.

## Dung lượng và phần có thể tinh giản

Root còn khoảng **1.249 MiB trống**. Portal cài khoảng 1,95 MiB, FileGator
14,95 MiB, cache APK 12,29 MiB, `/tmp` 6,40 MiB, log 13,27 MiB, các bản rollback
portal 31,94 MiB. Đây là số thư mục riêng, không cộng thành RAM đang dùng hoặc
coi tất cả là dữ liệu thừa có thể xóa.

Cloudflared log khoảng 9,69 MiB, log portal USB 2,05 MiB. Mẫu nền cloudflared tăng
409 byte/10 giây; tốc độ này chưa đại diện mức ghi mỗi ngày. Chưa cài package
logrotate, không có daily job hoặc rule logrotate cho các log OpenStick/Tunnel
đã kiểm tra. Cần thêm rotation/retention có giới hạn, bảo toàn chẩn đoán và xử
lý đúng file descriptor sau xoay log. Xóa log một lần không giải quyết tăng log.

Lỗi Tunnel public 530 và `network is unreachable` đã ghi nhận trước lượt audit
này là vấn đề kết nối riêng; không tắt Tunnel để làm nhẹ máy hoặc tuyên bố đã
sửa chỉ vì tiến trình còn chạy. Origin nội bộ từng trả 200. Cần kiểm tra hồi phục
Tunnel trong một bài test mạng được cho phép riêng.

464 package đã cài, tổng installed-size do APK báo khoảng 584,4 MiB; không có các
gói gcc/g++/make/cmake/git/pip/dev/header/debugger đã dò. Không thấy desktop
Phosh/Plasma/GNOME/Xfce hoặc browser trong nhóm tên package đã kiểm tra. Tuy nhiên
base image console vẫn kéo stack đồ họa/âm thanh:

| Ứng viên rà cho bản hệ thống không màn hình | Installed size APK | Phụ thuộc/đánh đổi |
| --- | ---: | --- |
| `llvm22-libs` + `mesa` | 167,8 + 35,7 MiB | LLVM được Mesa cần; các gói Mesa GL/GLES/GBM/DRI/EGL cần Mesa. Không xóa thư viện trực tiếp |
| `font-droid-nonlatin` | 13,3 MiB | Gói world rõ ràng; kiểm tra console/boot rendering trước khi bỏ |
| `glib-lang`, `networkmanager-lang`, `xkeyboard-config-lang` | 9,6 + 8,1 + 7,0 MiB | Có thể bớt bản dịch cục bộ; cần kiểm tra APK install-if và cập nhật không tự kéo lại |
| PulseAudio / PipeWire / GStreamer | Phụ thuộc nhiều gói | Có audio backend trong world; không thấy daemon audio trong mẫu tiến trình. Cần quyết định bỏ nhu cầu âm thanh/thoại tương lai và kiểm tra đồ thị phụ thuộc |

Các số trên là **dung lượng package**, chưa phải dung lượng sẽ thu hồi sau một
transaction APK hợp lệ, càng không phải mức RAM tiết kiệm. Đã đọc reverse
dependencies; chưa chạy gỡ giả lập/thật, chưa xác nhận boot sau khi cắt base
meta-package. Giữ kernel, DTB, firmware và modem/network dependencies. Nên chuẩn
bị manifest hệ thống headless riêng để thử có rollback trước, không gỡ mò trên
USB đang phục vụ. Không xóa firmware vì thư mục nhìn nhỏ hay không có daemon.

Cache APK chỉ nên dọn sau khi giữ được bộ cài/rollback cần thiết; giảm khoảng
12 MiB đĩa và mất lợi thế cài lại offline. Các bản deploy backup có thể áp dụng
retention sau khi chủ chọn số bản giữ; không xóa toàn bộ. Không đụng website,
credential, tin nhắn hoặc cấu hình đã lưu.

## Phần nên giữ và lựa chọn kiến trúc

- Giữ FileGator: PHP idle và Nginx nhỏ; bỏ sẽ mất file manager người dùng yêu cầu.
- Giữ NetworkManager, ModemManager, rmtfs, wpa_supplicant, DHCP/DNS/firewall và
  SSH: phục vụ các chức năng thật. Không tắt ModemManager chỉ vì hiện không dùng
  data; SMS/USSD và quản lý SIM cần nó.
- Giữ Avahi và chronyd: ít RAM, giữ `.local` và thời gian đúng khi lên mạng.
- Chưa bỏ supervisor/getty: tiết kiệm PSS rất nhỏ, mất giám sát/đường sửa lỗi.
- Controller upload/editor native cũ không nạp khi có FileGator. Windows backup
  UI riêng cũng không chạy trong portal Linux. Xóa file source ít KB không làm
  giảm RAM đáng kể; bỏ fallback/API là quyết định tương thích riêng.
- Hợp nhất hai portal có thể giảm phần Python dùng riêng, nhưng con số **20–30
  MiB chỉ là ước lượng cần thử**, không phải kết quả. Phải giữ binding theo
  interface, auth USB/LAN và fault isolation; kiểm Host đơn thuần không thay
  được ranh giới interface của Linux. Chưa nên chọn làm bước đầu.
- Hợp nhất nhiều worker có thể giảm vài MiB nhưng một crash ảnh hưởng nhiều
  tính năng. Ưu tiên giảm đọc trùng trước khi thay vòng đời worker/recovery.

## Thứ tự thực hiện đề xuất và nghiệm thu

1. **P0:** inventory nhẹ cho selector FileGator, số liệu dung lượng tải sau.
   Test registry lỗi/quyền/root/ZIP/revision giữ nguyên; đo năm lượt cùng cây file.
2. **P1:** cache asset có version và cải thiện cách dùng snapshot hiển thị.
   Test deploy không dùng JS cũ, auth trước cache, không cache dữ liệu riêng,
   không retry thao tác, stale/unknown đúng và tab ẩn ngừng polling.
3. **P1:** giảm passive polling theo từng nguồn; đo CPU, PSS, fork và request
   trong các cửa sổ tương đương, soak test. Thử lại USB admin, Wi-Fi/AP exclusivity,
   replay/rollback, SIM usage và modem restart với quyền thực hiện bài test đó.
4. **P1/P2:** giới hạn log; tách chẩn đoán Tunnel và retention backup khỏi xóa
   dữ liệu. Chỉ thử rotation sau khi chọn cơ chế reopen/retention phù hợp.
5. **P2:** bộ đếm SMS, bản package headless và hợp nhất portal/worker làm riêng,
   chỉ khi còn nhu cầu sau các bước ít rủi ro hơn.

Chưa có benchmark sau tối ưu vì chưa sửa runtime trong lượt này. Không hứa tăng
tốc bằng phần trăm khi chưa triển khai và đo lại. Lần kiểm tra cuối exit 0:
32 source file vẫn khớp bản cài, 717 file chủ được bảo vệ không đổi,
network/routes/firewall/DNS/gadget/service khớp mốc sau deploy; không có thao tác
pending. Không reboot, đổi mạng hay cài/gỡ package. Không chạy lại unit suite cho
thay đổi chỉ có tài liệu; bản source đang cài trước đó đã đạt 790 PASS/1 Windows
skip và hai CI PASS như [bàn giao giao diện](AP_AND_FILEGATOR_UI.md).
