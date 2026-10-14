---
name: fanpage-post
description: Đăng bài viết lên Trang Facebook có bước in thử duyệt trước — đọc nội dung từ văn bản hoặc tệp markdown, in thử để chủ doanh nghiệp duyệt, và chỉ đăng thật khi có cờ --dong-y. Đăng xong tự động đọc ngược từ Facebook để xác nhận. Không đăng hàng loạt.
---

# Đăng bài lên Trang Facebook

## Đầu vào
- Tên hoặc mã Trang Facebook bạn muốn đăng bài (`--trang "<tên hoặc mã Trang>"`).
- Nội dung bài đăng: nhập trực tiếp qua `--noi-dung "..."` hoặc đọc từ tệp markdown qua `--tep-noi-dung <đường-dẫn>`.
- Đường dẫn liên kết muốn đính kèm (tuỳ chọn): `--link "<url>"`.
- Chìa truy cập đã lưu tại kho OPC có quyền quản lý bài đăng (`pages_manage_posts`).

## Cách chạy
1. Liệt kê danh sách Trang bạn có quyền đăng:
   ```bash
   python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --liet-ke
   ```
2. Xem trước bài đăng (chế độ in thử, không đăng, không gửi thật):
   ```bash
   python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "Tên Trang Của Bạn" --noi-dung "Nội dung bài viết mới"
   ```
   Hoặc đọc từ tệp bài viết (bản chốt trong DAU-RA của dự án OPC):
   ```bash
   python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "Tên Trang Của Bạn" --tep-noi-dung CAC-DU-AN/<mã-dự-án>/DAU-RA/caption-bai-01_final.md
   ```
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.
3. Đăng bài thật sau khi chủ doanh nghiệp đã duyệt:
   ```bash
   python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --trang "Tên Trang Của Bạn" --tep-noi-dung CAC-DU-AN/<mã-dự-án>/DAU-RA/caption-bai-01_final.md --dong-y
   ```
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.
4. Tự kiểm tra script nội bộ:
   ```bash
   python3 ~/.claude/skills/fanpage-post/scripts/page_post.py --tu-kiem
   ```

## Đầu ra
- Khi in thử: màn hình hiển thị đầy đủ Trang đích, liên kết và nội dung xem trước để duyệt.
- Khi đăng thật: mã bài viết trên Facebook, thời gian đăng, liên kết bài viết công khai và bản ghi lưu trong `~/phong-marketing-ai/out/posted.json`.

## Cổng an toàn
- Đăng bài là hành vi **ĐĂNG CÔNG KHAI (cổng publish)**: ai trên mạng cũng đọc được.
- Quy trình duyệt: chạy lệnh không có cờ `--dong-y` để in bản xem trước → đưa bản xem trước cho chủ doanh nghiệp duyệt → chủ doanh nghiệp đồng ý → chạy lại với cờ `--dong-y`. Đây là quy trình làm việc (luật vận hành), không phải máy chặn.
- Mỗi lệnh chỉ gửi đúng một bài viết đến đúng một Trang, không có tính năng đăng hàng loạt.
- Đăng xong tự động gọi lại Facebook để đọc ngược và xác nhận bài viết đã thực sự xuất hiện trên Trang.
