# Y0UNG Control — quản lý kênh có xác nhận

## Khởi chạy
1. Giải nén ZIP, đổi `.env.example` thành `.env` và điền `DISCORD_TOKEN`.
2. Bật Message Content Intent trong Discord Developer Portal.
3. Chạy `start.bat` trên Windows, hoặc `pip install -r requirements.txt` rồi `python main.py`.
4. Cấp cho bot quyền View Channel, Send Messages, Manage Channels.

## Lệnh
- `$help`: danh sách lệnh.
- `$channels`: xem ID các kênh.
- `$backup_channels`: sao lưu thông tin kênh.
- `$delete_selected <ID1> ...`: xóa 1–10 kênh được chọn sau khi xác nhận.
- `$delete_channel <ID>`: xóa một kênh sau khi xác nhận.
- `$create_channels <1-10> <tên>`: tạo tối đa 10 kênh.
- `$rename_channel <ID> <tên mới>`: đổi tên kênh.
- `$nuke <ID1> ... <ID10>`: chủ máy chủ chọn 1–10 kênh cần xóa, nhận file sao lưu, xác nhận bằng nút, sau đó bot xóa các kênh đã chọn và tạo 200 kênh văn bản `hbao-001` ... `hbao-200`.

**Quan trọng:** Không có `managed_channels.json`. `$nuke` không xóa tất cả kênh máy chủ; không xóa kênh dùng để xác nhận. Bản sao lưu JSON chỉ là danh sách cấu trúc, **không lưu tin nhắn và không tự phục hồi đầy đủ**. Việc xóa kênh không thể hoàn tác. Bot giới hạn tốc độ thao tác; discord.py tự xử lý rate limit theo HTTP API, nhưng không bảo đảm không phát sinh lỗi 429. Discord có giới hạn số lượng kênh; bot sẽ kiểm tra trước khi chạy.
