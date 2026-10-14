---
name: doc-comment-fanpage
description: Đọc bình luận và số liệu tương tác từ Trang Facebook về máy tính hoặc trả lời một bình luận cụ thể. Mặc định chỉ đọc. Trả lời bình luận là đăng công khai, yêu cầu cờ --dong-y để đăng thật. Dữ liệu bình luận chỉ lưu trong thư mục ~/phong-marketing-ai/out/ được git bỏ qua.
---

# Đọc và trả lời bình luận Trang Facebook

## Đầu vào
- Tên hoặc mã Trang Facebook (`--trang "<tên hoặc mã Trang>"`).
- Tuỳ chọn số lượng bài cần soi: `--so-bai <N>` (mặc định: 10 bài viết gần nhất).
- Tuỳ chọn lọc theo từ khoá: `--tu-khoa "<từ1,từ2>"`.
- Khi trả lời bình luận: mã bình luận `--cmt <id>` và nội dung trả lời `--tra-loi "..."`.
- Chìa truy cập đã lưu tại kho OPC có quyền đọc nội dung (`pages_read_user_content`).

## Cách chạy
1. Liệt kê các Trang bạn quản lý:
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --liet-ke
   ```
2. Đọc bình luận 10 bài gần nhất của Trang:
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "Tên Trang Của Bạn"
   ```
3. Lọc bình luận theo từ khoá:
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "Tên Trang Của Bạn" --tu-khoa "giá,tư vấn"
   ```
4. Xem trước nội dung trả lời bình luận (in thử, không đăng, không gửi thật):
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "Tên Trang Của Bạn" --tra-loi "Dạ em đã gửi thông tin ạ" --cmt "123456_789012"
   ```
5. Đăng câu trả lời thật sau khi chủ doanh nghiệp duyệt:
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --trang "Tên Trang Của Bạn" --tra-loi "Dạ em đã gửi thông tin ạ" --cmt "123456_789012" --dong-y
   ```
6. Tự kiểm tra script nội bộ:
   ```bash
   python3 ~/.claude/skills/doc-comment-fanpage/scripts/page_comments.py --tu-kiem
   ```

## Đầu ra
- Tệp nhật ký các bình luận mới tải về: `~/phong-marketing-ai/out/<mã-Trang>/fanpage-comments/comment-YYYY-MM-DD.jsonl`.
- Sổ ghi nhận diện bình luận đã đọc: `~/phong-marketing-ai/out/<mã-Trang>/fanpage-comments/da-thay.json` để lần sau chỉ tải bình luận mới.
- Khi trả lời thật: mã phản hồi và liên kết bài viết sau khi đã đọc ngược xác nhận từ Facebook.

## Cổng an toàn
- Mặc định công cụ **CHỈ ĐỌC**.
- Trả lời bình luận là hành vi **ĐĂNG CÔNG KHAI (cổng publish)**: bất kỳ ai vào Trang cũng đọc được câu trả lời này.
- Quy trình duyệt: chạy lệnh không có cờ `--dong-y` để in bản xem trước → đưa bản xem trước cho chủ doanh nghiệp duyệt → chủ doanh nghiệp đồng ý → chạy lại với cờ `--dong-y`. Đây là quy trình làm việc (luật vận hành), không phải máy chặn.
- Mỗi lần chỉ trả lời đúng một bình luận duy nhất, không có đường trả lời hàng loạt.
- Dữ liệu người thứ ba (tên người bình luận, nội dung câu chữ) được phân tách theo từng Trang và kiểm tra đúng tệp qua `git check-ignore` trước khi ghi, chỉ ghi vào thư mục `~/phong-marketing-ai/out/<mã-Trang>/` đã được git bỏ qua để tránh đưa nhầm lên kho mã công khai. Không chép vào dự án OPC, trừ khi chủ doanh nghiệp tự chép vào `DAU-VAO/`.
