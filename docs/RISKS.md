# Rủi ro và giới hạn còn tồn tại

1. **Chưa thử với thiết bị thật.** Không có kết quả thực tế về ADB stock, tốc độ backup 3.61 GiB, mất cáp thật, root, CID, GPT hoặc RAM của USB đang cắm. Các số người dùng cung cấp là tham chiếu, không phải kết quả đo của ứng dụng.
2. **Android 4.4.4 có thể không hỗ trợ exec-out.** Bản đầu dừng an toàn khi binary transport/trailer không hợp lệ; chưa có transport fallback đã kiểm chứng.
3. **Backup live không nhất quán tuyệt đối.** Modem/system/userdata có thể thay đổi trong khi đọc; hash không chứng minh một snapshot tại cùng thời điểm. Chưa có backup offline EDL hoặc thử restore.
4. **Ảnh raw chỉ gồm user area eMMC.** Không bao gồm RPMB, boot0/boot1, fuse hoặc QCN độc lập. Tuyệt đối không gọi là bảo đảm cứu brick 100%.
5. **Chưa chứng minh firmware/loader V3.2.** Model UZ801 hoặc tên MSM8916 không đủ để khẳng định tương thích; chưa đối chiếu PCB, Wi-Fi/RF/eMMC, secure boot và khóa ký trên thiết bị thực.
6. **Kiểm tra nội dung calibration có giới hạn.** Chỉ đủ byte/hash/không toàn 00/FF; chưa giải mã cấu trúc vendor hoặc kiểm tra khả năng đăng ký mạng. Partition fsc toàn 00 có thể hợp lệ với một firmware nhưng vẫn cần xem xét riêng.
7. **Đổi thiết bị được phát hiện bằng transport/serial/CID/boot ID.** Không chống thiết bị độc hại giả toàn bộ nhận dạng. Quyền admin/malware cục bộ có thể sửa code, file backup, manifest hoặc đọc token.
8. **Backup không mã hóa.** Tệp có thể chứa dữ liệu modem và thông tin riêng tư. Chọn nơi lưu riêng tư; chương trình không gửi dữ liệu này lên mạng.
9. **Manifest chưa ký số.** Không dùng SHA-256 tự lưu như chứng thực nguồn gốc chống đối thủ sửa cả manifest và ảnh. Giữ bản hash ở nơi độc lập nếu cần kiểm tra nguồn gốc.
10. **Chưa ký executable/chưa kiểm thử mọi Windows.** Build/test trên Windows 10 x64; máy sạch khác, Windows 11, ARM64, phần mềm antivirus và filesystem khác chưa được thử.
11. **Không tự sửa GPT/backup.** Hai GPT không khớp hoặc sysfs không khớp làm khóa backup thông thường. Cứu dữ liệu thiết bị có GPT hỏng cần quy trình riêng được xem xét, không bypass guard.
12. **Dung lượng và mất điện.** Có kiểm tra trống và fsync nhưng không thể loại trừ mất điện, lỗi ổ đĩa, đầy đĩa do tiến trình khác hoặc RAM lỗi. Backup dở không được resume/ghép với phiên khác.
13. **Chưa xác minh đường EDL.** PnP/CLI help không mở USB, không kiểm tra Sahara/Firehose. Không tự cài driver, tải loader hay chạy lệnh EDL đọc dù tên lệnh là read-only vì có thể nạp programmer vào RAM.
