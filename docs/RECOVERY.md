# Kiểm tra khả năng khôi phục

Đây là checklist chuẩn bị, không phải lệnh flash hoặc hướng dẫn chập chân mạch.

1. Giữ firmware gốc và manifest đã kiểm tra ở ít nhất hai nơi. Ghi lại nguồn firmware, phiên bản board vật lý và biến thể linh kiện; không dựa vào `ro.product.board` để suy ra PCB V3.2.
2. Kiểm tra ảnh raw có GPT chính/dự phòng hợp lệ, đủ phân vùng hiệu chuẩn và bootloader. Giữ nguyên cả tệp lỗi/dở dang để điều tra, không đổi đuôi `.part` thành `.img` nhằm bỏ qua xác minh.
3. Xác định cách vào và thoát EDL từ tài liệu đúng board. Chưa có quy trình V3.2 được kiểm chứng trên thiết bị này; không làm theo pinout của board khác.
4. Khi thiết bị đã ở EDL bằng một thao tác được người dùng phê duyệt riêng, kiểm tra Windows có `VID_05C6&PID_9008`, không có mã lỗi driver. Có thể kiểm tra PnP mà không đổi driver.
5. Phân biệt driver QDLoader COM, WinUSB, UsbDk và backend mà phiên bản EDL cụ thể dùng. Không tự thay driver đang dùng chỉ vì xuất hiện lỗi `libusb`.
6. Programmer cần nguồn đáng tin cậy, hash xác minh, bằng chứng khớp HWID/PK hash và kiểm tra giao tiếp trên đúng thiết bị. Tên file chứa `8916`, header ELF hay một hash do người dùng tự nhập đều chưa đủ.
7. Sau khi có xác nhận riêng về nạp programmer vào RAM và giao tiếp EDL, ưu tiên một bản dump offline đầy đủ, rồi kiểm tra độc lập trước khi cân nhắc quy trình ghi. Bản manager này không thực hiện bước nạp programmer hoặc giao tiếp Firehose.
8. Chỉ thiết kế và mở Phase 5 sau khi có firmware đúng biến thể, backup đã kiểm chứng, đường khôi phục và phê duyệt riêng cho thao tác ghi. Các phân vùng modem/calibration/bootloader không được tự ghi đè.

Không thể chứng minh recovery bằng một đèn báo 9008. Một dump raw hợp lệ cũng không chứng minh bootloader/programmer sẽ cho phép ghi lại. Trạng thái của ứng dụng luôn giữ `flash_enabled=false`.
