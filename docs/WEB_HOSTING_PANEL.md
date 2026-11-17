# Panel nhiều website tĩnh — 17/11/2026

Nhánh `codex/uz801-v32-postmarketos`. Mở **Website** ở menu dưới hoặc `/website`.
Đây là panel cho HTML/CSS/JS và tài nguyên tĩnh, không phải môi trường chạy
Node.js/PHP/WordPress. Không cài thư viện server, chạy npm hoặc thực thi ZIP.

## Sử dụng

1. Website cũ là **Website hiện tại**, vẫn dùng thư mục gốc và tên miền gốc.
   Bấm **Tạo website** để có thư mục riêng; có thể để trống tên miền lúc đầu.
   Bộ chọn ở đầu trang xác định website của mọi thao tác file.
2. **File manager**: tìm file theo đường dẫn; chọn thư mục rồi **Mở thư mục**;
   breadcrumb quay lại cha/gốc. Có tạo file/thư mục, sửa UTF-8, đổi tên, di
   chuyển, sao chép, xóa có xác nhận, tải file và tải thư mục thành ZIP.
   Đích của copy/move phải chưa tồn tại, không tự ghép hoặc ghi đè thư mục.
3. **Tải lên & giải nén**: chọn nhiều file hoặc cả thư mục. Đường dẫn tương đối
   được giữ; xem danh sách ghi đè rồi xác nhận xuất bản. Upload theo thứ tự;
   nếu lỗi, các file đã hoàn tất vẫn giữ. Sau lỗi phải đọc lại danh sách đích
   trước khi xác nhận lượt mới, không tự retry kết quả chưa rõ.
4. ZIP: chọn file ở ô ZIP hoặc ô tải file thường; panel tự nhận `.zip`/`.ZIP`
   và tải lên kiểm tra, chưa ghi website. Tiến độ và lỗi hiện ngay trong tab
   tải lên. Khi đổi thư mục đích, bấm **Tải ZIP & kiểm tra lại**. Xem file
   mới/ghi đè, tổng dung lượng và vị trí `index.html`, rồi **Giải nén vào website**.
   Không trộn ZIP và file thường trong một lượt; không tự bỏ thư mục bọc ngoài;
   file cũ không có trong ZIP được giữ. Không xóa cả website khi import.
5. **Tên miền**: sửa danh sách, mỗi dòng một hostname. Một hostname chỉ thuộc
   một website. Tên miền gốc được bảo vệ. Lưu registry chưa thay đổi dịch vụ.
   **Áp dụng Nginx & Tunnel** có xác nhận riêng, áp dụng toàn bộ registry;
   reload Nginx và restart Tunnel có thể gây ngắt ngắn website công khai.

Chỉnh sửa file là bản nháp trong tab, chưa lưu lâu dài và mất khi đóng tab.
Chuyển website/bỏ bản sửa có cảnh báo. Không chạy HTML trong origin quản trị;
URL công khai mở tab riêng. Panel chưa có lịch sử phiên bản, thùng rác,
giải nén RAR/7z/TAR, chuyển file giữa hai website, xóa cả hồ sơ website,
hay tạo/kiểm tra DNS tự động. Xóa file/thư mục là vĩnh viễn sau xác nhận.

## Giới hạn

| Hạng mục | Giới hạn mới |
| --- | --- |
| Website | 8 |
| Hostname / website | 10 |
| Upload file | 32 MiB, truyền multipart theo luồng |
| ZIP tải lên | 128 MiB |
| Website / tổng dữ liệu giải nén | 256 MiB |
| File và thư mục / website | 2.000 |
| Trình sửa văn bản | 2 MiB UTF-8 |
| Độ sâu / độ dài đường dẫn | 16 cấp / 240 ký tự |
| Dung lượng dự phòng | Ít nhất 32 MiB ngoài phần thao tác cần dùng |

Giới hạn theo website không đặt trước dung lượng. Dung lượng trống thực tế
và vùng làm việc/rollback có thể chặn upload trước khi đạt giới hạn danh
nghĩa. Xuất ZIP dùng ZIP_STORED để giảm tải CPU; ZIP tải xuống của website lớn
có thể vượt giới hạn ZIP nhập 128 MiB, cần tách bộ mã khi nhập lại.

Waitress của cả USB và LAN chấp nhận request 129 MiB, với input spill-to-disk
64 KiB; Flask chỉ nâng hạn mức cho endpoint multipart này. Endpoint điều
khiển Wi-Fi/mạng vẫn giữ mức cũ. File không được base64 hóa trong API mới.
API `/api/site` cũ vẫn có hợp đồng và giới hạn cũ để tương thích.

Multipart decoder có headroom 256 KiB để chứa buffer đọc 64 KiB cộng phần
boundary dở. Đây không phải giới hạn kích thước file hay bộ nhớ giữ cả file.
HTTP 413 báo riêng request bị từ chối, không tự suy thành ZIP vượt 128 MiB.
Đã tái hiện ZIP mẫu 27 MiB nhận 413 trên USB trước sửa; cùng ZIP nhận 200 và
mở nút giải nén sau sửa. Chỉ kiểm tra, không xuất bản bộ mã vào website chủ.

## Bảo toàn dữ liệu và xử lý lỗi

- File, metadata, ZIP dùng chung khóa thread + flock của portal; hai listener
  USB/LAN và API cũ không ghi đồng thời. SHA-256 giữ chống ghi đè bản sửa file
  cũ; revision cây thư mục dựa trên đường dẫn, loại, kích thước, mtime_ns và
  inode chống thao tác trên danh sách lỗi thời. Đây không phải khóa với công
  cụ sửa file bên ngoài portal; không sửa website qua SSH trong lúc import.
- Metadata chỉ có ID ngẫu nhiên, tên, domains; root không nhận từ request.
  Registry `/var/lib/openstick/web-panel/sites.json` root-only; website mới
  ở `/var/www/openstick-sites/<UUID>`, website gốc `/var/www/openstick` giữ nguyên.
- ZIP được staging ngoài public root. Chặn traversal, đường dẫn tuyệt đối,
  symlink/junction, file đặc biệt, tên ẩn, server code, tên trùng/case collision,
  zip mã hóa và phương thức nén ngoài stored/deflate. File lớn/zip bomb bị
  giới hạn cả metadata trước ZipFile, kích thước khai báo và số byte đọc thật.
- Kiểm tra ZIP không ghi vào public root; khi giải nén, kiểm lại archive hash,
  revision và quota. Sao lưu toàn bộ file bị thay trước khi thay file đầu tiên.
  Nếu có lỗi ghi thông thường thì khôi phục các file và thư mục vừa tạo.
- Thay nhiều file không phải một phép publish nguyên tử với Nginx: client có
  thể đọc bộ mã ở trạng thái đang cập nhật. Không quảng cáo zero downtime.
  Journal có fsync và bản gốc được giữ ngoài public root nếu bị gián đoạn.
  Lần mở sau khóa thao tác ghi, hiện **Khôi phục trước lần giải nén dở** có
  xác nhận. Nếu phát hiện file bị sửa bên ngoài hoặc backup lỗi, từ chối ghi
  đè và giữ vật liệu riêng để kiểm tra. Chưa chứng nhận cắt điện thật/eMMC.
- Work dirs dưới `/var/lib/openstick/web-panel/work/`, mode 0700. Upload/ZIP
  kiểm tra xong được dọn; pending journal được giữ. Không commit nội dung này.
- Auth LAN, Host/Origin, token, cookie và binding USB/Wi-Fi vẫn giữ. Không
  thêm route quản trị vào Tunnel, không đọc token Cloudflare vào trình duyệt.

## Tên miền / Nginx / Cloudflare

Chỉ hỗ trợ cấu hình local-managed đơn giản vốn do dự án cài: ingress hostname
gốc tới `127.0.0.1:8080`, rồi catch-all 404. Schema lạ bị khóa, không tự suy
diễn để ghi đè. Không thay credentials-file hoặc nội dung credentials JSON.

Virtual hosts được sinh vào `/etc/nginx/openstick-panel.conf`; thêm một include
vào khối http của config hiện tại, giữ default server/root cũ. Rule ingress
được thêm trong marker riêng trước catch-all. Các server mới chỉ nghe loopback
8080, không nghe 8765/USB/Wi-Fi. Chạy `nginx -t` và `cloudflared ... tunnel
ingress validate` trước reload/restart. Lỗi thì trả lại config và thử phục hồi
dịch vụ; rollback không xong báo riêng, không giả thành công. Backup riêng
dưới `/var/lib/openstick/web-panel/domain-backups/`: file 0 nginx gốc, file 1
managed include nếu trước đó có, file 2 config Tunnel; không phải credentials.

`CONFIG_SAVED` chỉ cho biết các file config khớp registry, không phải phép đo
HTTP công khai hoặc xác minh DNS. DNS luôn `UNVERIFIED`. Trong Cloudflare,
hostname mới cần CNAME proxied đến `<Tunnel UUID>.cfargotunnel.com` của cùng
Tunnel. Không yêu cầu token zone/DNS trong panel phiên bản này.

Nguồn đối chiếu ngày 17/11/2026:
[Nginx command switches](https://nginx.org/en/docs/switches.html),
[Nginx server names](https://nginx.org/en/docs/http/server_names.html),
[Cloudflare local tunnel DNS](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/).

## Kiểm thử

`tests/test_website_panel.py` bao gồm cô lập roots, registry lỗi, domain trùng,
bảo vệ hostname gốc, thao tác thư mục, overwrite lỗi thời, streaming >1 MiB,
quota, ZIP traversal/collision/symlink, giới hạn central directory trước cấp
phát danh sách members, rollback I/O, giả lập process interruption và phát
hiện external edits. Auth/body limits, domain config validation/rollback dùng
fixtures; không gọi dịch vụ thật trong unit tests.

`python scripts/verify_website_browser.py` dùng Chrome headless và
`scripts/preview_portal.py`, chỉ dữ liệu giả: 12 bố cục, create/switch site,
sửa/copy/rename, upload >1 MiB, ZIP preview/cancel/publish, file/folder download
và bảo toàn website gốc; không phải hardware acceptance. Ảnh cục bộ dưới
`artifacts/website-browser/`, không commit.

Phân biệt mã nguồn, browser demo và cài đặt trên USB trong SESSION_HANDOFF.
Không tuyên bố domain công khai PASS khi chưa có DNS và phép thử thực tế.

Kết quả ngày 17/11: 621 pytest PASS, 1 Windows privilege skip, exit 0.
Đã cài 11 file panel lên USB và đối chiếu SHA-256, chỉ restart hai portal.
Chrome thật đọc panel đạt 12 layout, không lỗi JavaScript/tràn ngang/thao tác
ghi. Fixture riêng trên filesystem USB đạt upload 2.097.169 byte, ZIP preview/
publish/export, hai root độc lập và copy/move, đã dọn xong. Website và cấu hình
riêng không thay đổi. Chưa stress giới hạn 32/128/256 MiB hoặc cắt điện thật;
chưa Apply tên miền/reload dịch vụ thật hay tạo DNS. Mã mới không sửa lỗi
modem/DHCP đã ghi ở các phiên trước.
