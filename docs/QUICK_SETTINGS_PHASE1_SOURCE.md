# Quick Settings — mã nguồn và triển khai

**Cập nhật 16/11/2026:** Phần source-only bên dưới là checkpoint lịch sử,
không còn mô tả USB hiện tại. Chủ đã cho phép cài và thử có SIM. Nguồn mới
đã được cài; xem [nghiệm thu thật](QUICK_SETTINGS_HARDWARE_VALIDATION_2026_11_16.md).

Luồng hiện tại có **năm ô chung trên Tổng quan và `/quick`**. Phát Wi-Fi là
một AP: thêm data SIM thì có Internet, tắt data vẫn giữ AP/DHCP; AP-off không
tự nối Wi-Fi nhà. USB tethering không dùng NM shared/rebind để đổi chế độ
live, cũng không cần ứng dụng PC. Nó lưu lựa chọn rồi reboot bình thường một
lần theo xác nhận; boot mới chọn DHCP/DNS/NAT riêng và PC nhận lease mới.
Xem [thiết kế và cách dùng](USB_TETHERING.md). Không tự bật SIM khi boot hoặc
khi tắt máy bay. Tất cả hành động vẫn cần xác nhận/receipt/khóa.

519 pytest PASS / 1 Windows skip; tám layout demo và token đổi qua reboot
PASS. DNS/HTTPS thực qua SIM, phone AP Internet, PC qua USB (Wi-Fi/SIM) và hai
toggle tethering qua reboot đã có bằng chứng riêng. Lỗi MM disconnect kẹt
trước đó **chưa được kết luận sửa triệt để**, dù các chu kỳ mới đã qua.

## Checkpoint lịch sử trước khi chủ cho phép triển khai

Ngày 16/11/2026. Sau Phase 0, chủ yêu cầu tiếp tục làm chức năng và lắp SIM
để thử sau. Đã triển khai nguồn/preview/test; **USB thật vẫn chạy baseline
`c704264`**, không cài package, restart dịch vụ, đổi radio, AP, route, DHCP,
forwarding, NAT hoặc gadget trong lượt này. Không coi test giả là hardware PASS.

## Phần đã viết

| Phần | Hành vi nguồn | Nghiệm thu |
| --- | --- | --- |
| `/quick` | Sáu ô: máy bay, data SIM, Wi-Fi, AP nội bộ, link SIM AP và USB tethering bị khóa | Chrome demo 320/390/768/1280 px PASS; chưa chạy trên USB |
| Máy bay on | Lưu veto trước side effect, dừng policy/autoconnect owned data, tắt data, yêu cầu modem off và NM WWAN off; giữ USB và Wi-Fi | Mock PASS, chưa thử tắt RF thật |
| Máy bay off | Cho phép WWAN/modem hoạt động; data/policy/autoconnect CELL vẫn off; thiếu SIM thì chờ | Mock PASS, chưa thử SIM thật |
| Data on | Cần consent cước và SIM registered; chỉ kích hoạt CELL_UUID có sẵn, giữ vai trò Wi-Fi, không bật boot autoconnect, không báo Internet PASS | Mock PASS, chưa tạo bearer thật |
| Data off khi SIM AP | Tắt data, dừng SIM AP, phát lại setup AP khi SSID/PSK profile khớp; không gọi stop cũ tự nối STA | Mock PASS, cần phone/driver acceptance |
| Lỗi phát lại AP | Data vẫn bị cấm/tắt, receipt UNKNOWN + lỗi cụ thể, hướng dẫn dùng USB; không rollback bằng bật data | Mock PASS |
| AP nội bộ | Bật sau khi tắt data; tắt có cảnh báo mất Wi-Fi và có thể thử STA cũ | Mock backend + Chrome demo; chưa chuyển vai trò thật |
| Radio worker/legacy endpoints | Cùng đọc intent; worker không tự enable/replay mode khi airplane. Boot reconciliation chỉ thi hành off intent đã lưu | Mock PASS, cần reboot/restart worker thật sau này |
| SIM AP sau data bật riêng | Chỉ nhận lại owned CELL khi có Quick Settings intent cho phép, vẫn checkpoint/probe/Keep 5 phút | Mock regression PASS; không nhận foreign bearer |

`quick_intent.py` là nguồn veto bền vững version 1 cho airplane/data. Thiếu file
giữ hành vi cũ; file lỗi fail closed. NM vẫn là nguồn observed link/role, MM/QMI
là nguồn modem/session; không ghi SSID/key hoặc SIM ID vào intent/receipt.
Chưa thay toàn bộ legacy policy/setup/hotspot bằng một state machine mới.

Khóa theo network → modem, preflight chặn pending trial, USSD kể cả session QMI
riêng, kết nối/profile GSM autoconnect ngoài quyền sở hữu. Receipt UUID tạo
exclusive trước mutation, không tự gửi lại khi timeout/mất HTTP. Mở trang chỉ
GET status; API vẫn dưới Host/Origin/token/LAN authentication hiện hữu.
Một UUID đã ghi không được dùng lại. Orphan STARTED không được replay sau reboot;
giao diện có deadline 210 giây và báo chưa xác minh để kiểm tra thủ công.

Trong vai trò STA, data-off không gọi tắt Wi-Fi. Khi đang SIM AP thì hộp xác
nhận nói rõ Wi-Fi có thể ngắt rồi phát lại **không Internet**. Nếu cấu hình AP
đã được sửa chờ áp dụng, SSID/PSK không còn khớp, không hứa giữ mạng cũ: data
vẫn tắt và báo cần quản trị USB. Cơ chế cut-off còn thử disconnect CELL khi lưu
automation gặp lỗi, nhưng lỗi một phần luôn là UNKNOWN, không chứng nhận off.

Các thao tác Quick Settings radio/data tắt Internet policy. Muốn bật lại
failover phải có thao tác/consent mới ở trang nguồn Internet. Link SIM AP vẫn
đưa đến luồng cũ có consent và Keep 5 phút; không tự bật SIM hoặc xác nhận Keep.

## Những phần cố ý chưa cho áp dụng

- USB tethering: NO-GO với dispatcher đang rebind UDC và host chưa có route.
  Ô hiển thị lý do, không có action/API bật NAT hoặc sửa USB.
- WPA3/PMF: bị chặn theo audit; không thêm một switch có thể làm mất AP.
- Hidden SSID, client limit, station list/isolation/ACL: bằng chứng phần mềm đã
  ghi ở Phase 0, chưa có controller áp dụng/đọc client hoàn chỉnh. Không dùng
  NM adapter denylist làm client ACL hoặc MaxNumSta=128 làm chứng nhận driver.
- Chưa nghiệm thu giữ AP nội bộ qua cold boot, radio off thực tế, SIM data,
  USSD tương tác, thay vai trò live hoặc hành vi USB tethering. Không đổi saved
  3G/4G mode để tạo điều kiện test. Không build/cài USB chỉ để mở các nút này.

## Kiểm thử và cách xem

Local pytest cuối: **498 PASS, 1 SKIP**, exit 0. Skip Windows thiếu quyền tạo
symlink. Có 29 test mới so với baseline, gồm consent/schema, no-SIM, status
không tạo file, lock/session conflict, receipt chống replay, boot off-only,
replay đúng saved mode sau một chu kỳ airplane,
veto legacy modem/hotspot/policy, cut-off khi lỗi, AP identity và UUID đang
configuring chưa phải data connected. Self-test package/API và Node syntax PASS.

Chrome headless demo: bốn độ rộng, không tràn ngang/lỗi JS; mở trang không
mutation, nút data khóa khi thiếu SIM, Hủy/Escape không gửi lệnh, airplane-off
không data-on, AP nội bộ không gỡ airplane intent. Demo dùng memory backend,
không tạo RadioControl/Network thật. Script hỗ trợ chạy lặp có reset **chỉ**
dữ liệu giả của preview, không phải endpoint reset của sản phẩm.

```powershell
.venv\Scripts\python.exe scripts/preview_portal.py
python scripts/verify_quick_browser.py
```

Xem **http://127.0.0.1:8771/quick** trên máy phát triển. Đây không phải URL
USB; `/quick` trên USB chưa được cài. Python chạy script browser cần Playwright
và Chrome. Ảnh/report demo trong ignored `artifacts/quick-settings-audit/`.

Trước rollout, chạy các bài SIM/phone/boot trong báo cáo
[Phase 0](QUICK_SETTINGS_PHASE0_AUDIT_2026_11_16.md) theo phạm vi được cho phép.
Không tự chuyển mạng thật để thay cho phần nghiệm thu còn thiếu.
