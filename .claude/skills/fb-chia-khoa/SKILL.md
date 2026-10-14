---
name: fb-chia-khoa
description: Kiểm tra chìa truy cập Facebook Page đã cất trong kho OPC — kiểm tra thời hạn, danh sách quyền và các Trang đang quản lý. Dùng khi mới thiết lập kho hoặc khi các skill khác báo thiếu quyền hay hết hạn. Không in giá trị chìa.
---

# Kiểm tra chìa Facebook Page

## Đầu vào
- Tệp chìa truy cập do công cụ `tools/inbox-reader/save_token.py` của kho OPC tạo (quyền 600), hoặc chỉ định qua biến môi trường `META_PAGE_TOKEN_FILE`.
- Chìa cần có đủ 7 quyền nền tảng phục vụ các skill:
  1. `pages_show_list` (xem danh sách Trang)
  2. `pages_read_engagement` (đọc số liệu tương tác)
  3. `pages_manage_posts` (đăng bài viết lên Trang)
  4. `pages_manage_engagement` (quản lý tương tác và trả lời bình luận)
  5. `pages_read_user_content` (đọc nội dung và bình luận)
  6. `pages_messaging` (đọc và gửi tin nhắn riêng)
  7. `pages_manage_metadata` (quản trị thông tin và cấu hình Trang cho bộ đọc hộp thư)
  Một chìa dùng chung cho bộ đọc hộp thư của kho OPC và bộ marketing; cất chìa mới sẽ thay chìa cũ, nên chìa mới phải đủ cả 7 quyền.

## Cách chạy
1. Kiểm tra trạng thái chìa và các quyền nền tảng:
   ```bash
   python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py
   ```
2. Liệt kê danh sách Trang mà chìa quản lý:
   ```bash
   python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py --liet-ke
   ```
3. Tự kiểm tra script nội bộ:
   ```bash
   python3 ~/.claude/skills/fb-chia-khoa/scripts/page_token.py --tu-kiem
   ```

## Đầu ra
- Trạng thái hiệu lực của chìa (hợp lệ / không hợp lệ), thời hạn sử dụng.
- Đánh giá từng quyền bắt buộc (ĐẠT hoặc THIẾU).
- Danh sách các Trang bạn đang quản lý (tên Trang và mã Trang).

## Cổng an toàn
- Không bao giờ in giá trị chìa khoá ra màn hình hay ghi vào nhật ký.
- Không nhận đường dẫn chìa qua dòng lệnh.
- Script chỉ kiểm tra tình trạng chìa, không cất hay sửa đổi tệp chìa trên máy của bạn.
