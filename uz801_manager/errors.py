class SafetyError(Exception):
    """Only fixed, non-sensitive diagnostic codes cross the UI/log boundary."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class Cancelled(SafetyError):
    def __init__(self):
        super().__init__("CANCELLED")


MESSAGES = {
    "ADB_NOT_FOUND": "Không tìm thấy ADB. Cài Android Platform Tools hoặc đặt adb.exe tại C:\\adb.",
    "ADB_FAILED": "ADB báo lỗi. Kiểm tra cáp, quyền truy cập và trạng thái USB.",
    "ADB_TIMEOUT": "ADB không phản hồi trong thời gian cho phép.",
    "NO_DEVICE": "Không có thiết bị ADB sẵn sàng (có thể offline hoặc chưa cấp quyền).",
    "MULTIPLE_DEVICES": "Có nhiều thiết bị ADB. Chỉ kết nối một USB cần sao lưu.",
    "TRANSPORT_UNSUPPORTED": "ADB thiếu transport_id. Cần Android Platform Tools mới hơn.",
    "NO_ROOT": "ADB chưa có quyền root; ứng dụng không tự nâng quyền.",
    "IDENTITY_UNAVAILABLE": "Không đọc được dấu nhận dạng riêng để kiểm tra thay thiết bị.",
    "DEVICE_CHANGED": "Thiết bị hoặc phiên kết nối đã thay đổi. Tác vụ bị dừng.",
    "INVALID_DEVICE_DATA": "Thông tin thiết bị thiếu hoặc không hợp lệ.",
    "GPT_INVALID": "GPT thiếu, hỏng CRC, vượt giới hạn hoặc hai bản không khớp.",
    "LAYOUT_MISMATCH": "Bảng phân vùng GPT không khớp thông tin kernel.",
    "CRITICAL_MISSING": "Thiếu phân vùng quan trọng; không thể xác nhận backup đầy đủ.",
    "STREAM_FAILED": "Luồng đọc nhị phân lỗi; backup chưa hoàn tất.",
    "STREAM_TIMEOUT": "Luồng đọc ngừng truyền dữ liệu quá lâu.",
    "SIZE_MISMATCH": "Kích thước dữ liệu đọc không đúng dung lượng dự kiến.",
    "REMOTE_READ_FAILED": "Thiết bị không xác nhận đọc thành công; exec-out có thể không được hỗ trợ.",
    "DISK_SPACE": "Ổ đĩa không đủ chỗ trống để sao lưu và giữ khoảng dự phòng.",
    "IO_ERROR": "Không đọc/ghi được tệp trên máy tính. Kiểm tra dung lượng và quyền truy cập.",
    "BUSY": "Đang có tác vụ chạy. Hãy đợi hoàn tất hoặc hủy tác vụ hiện tại.",
    "CANCELLED": "Đã hủy an toàn; tệp dở dang không được coi là backup hợp lệ.",
    "PATH_INVALID": "Chọn thư mục cục bộ hợp lệ; không dùng đường dẫn mạng, thiết bị hoặc liên kết.",
    "MANIFEST_INVALID": "Manifest không hợp lệ hoặc đường dẫn tệp không an toàn.",
    "HASH_MISMATCH": "SHA-256 không khớp. Không sử dụng bản backup này để khôi phục.",
    "BACKUP_INCOMPLETE": "Backup còn thiếu tệp hoặc chưa hoàn tất.",
    "CONTENT_SUSPICIOUS": "Phân vùng quan trọng toàn byte 00/FF; cần điều tra trước khi khôi phục.",
    "CONSENT_REQUIRED": "Cần cho phép đọc thiết bị trong giao diện trước khi kiểm tra.",
    "INSPECT_REQUIRED": "Cần kiểm tra thiết bị thành công trước khi sao lưu.",
    "EDL_PROBE_FAILED": "Không kiểm tra được công cụ EDL hoặc thông tin USB Windows.",
    "INPUT_INVALID": "Dữ liệu yêu cầu không hợp lệ.",
    "INTERNAL_ERROR": "Lỗi nội bộ; tác vụ đã dừng. Không có lệnh ghi thiết bị nào được thực hiện.",
}


def message(code):
    return MESSAGES.get(code, MESSAGES["INTERNAL_ERROR"])
