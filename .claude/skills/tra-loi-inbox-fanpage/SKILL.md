---
name: tra-loi-inbox-fanpage
description: Đọc và trả lời tin nhắn riêng (inbox) của Trang Facebook trong cửa sổ 24 giờ. Mặc định chỉ đọc. Gửi tin nhắn là gửi trực tiếp cho khách, yêu cầu cờ --dong-y để gửi thật. Chặn gửi nếu hội thoại đã quá hạn 24 giờ. Không gửi hàng loạt.
---

# Đọc và trả lời tin nhắn riêng Trang Facebook

## Đầu vào
- Tên hoặc mã Trang Facebook (`--trang "<tên hoặc mã Trang>"`).
- Khi xem danh sách hội thoại: cờ `--hop-thu`.
- Khi xem nội dung: mã hội thoại `--doc <mã-hội-thoại>`.
- Khi trả lời tin nhắn: mã hội thoại `--hoi-thoai <mã-hội-thoại>` và nội dung trả lời `--tra-loi "..."`.
- Chìa truy cập đã lưu tại kho OPC có quyền nhắn tin (`pages_messaging`).

## Cách chạy
1. Liệt kê các Trang và kiểm tra quyền nhắn tin:
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --liet-ke
   ```
2. Xem danh sách hội thoại gần đây và thời điểm hoạt động cuối:
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "Tên Trang Của Bạn" --hop-thu
   ```
3. Đọc chi tiết các tin nhắn trong một hội thoại:
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "Tên Trang Của Bạn" --doc "t_123456789"
   ```
4. Xem trước tin nhắn trả lời khách (chế độ in thử, không đăng, không gửi thật):
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "Tên Trang Của Bạn" --tra-loi "Chào bạn, mình xin hỗ trợ thông tin" --hoi-thoai "t_123456789"
   ```
5. Gửi tin nhắn thật tới khách sau khi chủ doanh nghiệp duyệt:
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --trang "Tên Trang Của Bạn" --tra-loi "Chào bạn, mình xin hỗ trợ thông tin" --hoi-thoai "t_123456789" --dong-y
   ```
6. Tự kiểm tra script nội bộ:
   ```bash
   python3 ~/.claude/skills/tra-loi-inbox-fanpage/scripts/page_inbox.py --tu-kiem
   ```

## Đầu ra
- Bảng danh sách hội thoại kèm thời gian cập nhật và cột «hoạt động cuối».
- Nội dung tin nhắn theo thứ tự thời gian, lưu tại `~/phong-marketing-ai/out/<mã-Trang>/fanpage-inbox/hoi-thoai-<id>.json`.
- Khi gửi thật: mã tin nhắn gửi đi và thời gian xác nhận cập nhật hộp thư từ Facebook.

## Cổng an toàn
- Trả lời tin nhắn là hành vi **GỬI KHÁCH (cổng customer-message)**: tin nhắn gửi thẳng vào hộp thư riêng của khách hàng thật.
- Quy trình duyệt: chạy lệnh không có cờ `--dong-y` để in bản xem trước → đưa bản xem trước cho chủ doanh nghiệp duyệt → chủ doanh nghiệp đồng ý → chạy lại với cờ `--dong-y`. Đây là quy trình làm việc (luật vận hành), không phải máy chặn.
- **Rào cản cửa sổ 24 giờ**: Facebook quy định chỉ được trả lời trong vòng 24 giờ kể từ tin nhắn cuối của khách hàng. Script tự động phân trang để tìm tin nhắn cuối của khách và chặn gửi ngay từ máy tính nếu đã quá hạn 24 giờ, thiếu giờ, giờ sai định dạng, giờ ở tương lai hoặc thiếu `from.id`, tránh bị khoá quyền nhắn tin.
- Mỗi lần gửi chỉ tới đúng một hội thoại và đúng một khách hàng, tuyệt đối không gửi hàng loạt.
- Dữ liệu tin nhắn chỉ ghi vào thư mục `~/phong-marketing-ai/out/<mã-Trang>/` đã được `git check-ignore` xác nhận nằm ngoài git. Không chép vào dự án OPC, trừ khi chủ doanh nghiệp tự chép vào `DAU-VAO/`.
