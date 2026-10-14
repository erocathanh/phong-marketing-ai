---
name: caption-fanpage
description: Soạn caption cho một bài đăng fanpage (video hoặc ảnh) theo luật viết của doanh nghiệp, ra 3 lựa chọn kèm 1 đề xuất và bảng tự soát, để chủ doanh nghiệp duyệt rồi tự đăng. Dùng khi người dùng nói "viết caption", "soạn bài đăng fanpage", "caption cho video này", "3 phương án caption". Không tự đăng bài.
---

# Soạn caption fanpage

## Đầu vào
- Nội dung bài: lời đọc của video, hoặc mô tả ảnh. Mẫu: `~/phong-marketing-ai/references/du-lieu-mau/loi-doc-video-mau.md`.
- Link muốn dẫn người đọc tới (nếu có) — tạo bằng skill `lich-dang-7-ngay` (`~/.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py`) để có mã theo dõi, `kenh` = `organic`.
- Luật viết của doanh nghiệp (nếu có): xưng hô, gọi người đọc là gì, từ cấm, có ghi ngày cụ thể hay không.
  Chưa có thì hỏi người dùng 3 câu: tự xưng thế nào · gọi người đọc là gì · có từ nào cấm dùng không.

## Các bước
1. Đọc nội dung bài, tóm ý chính trong 2 câu, hỏi người dùng tóm vậy đúng chưa.
2. Viết 3 lựa chọn, mỗi lựa chọn một góc khác nhau. Mỗi bản 60–150 chữ; dòng đầu là câu móc, vì Facebook chỉ hiện 2–3 dòng trước nút «Xem thêm»; xuống dòng nhiều, không dùng bảng.
3. Mỗi lựa chọn ghi: tên góc · nguyên văn · mạnh (1 dòng) · yếu (1 dòng).
4. Viết 1 câu «tôi đề xuất bản X vì …» kèm điểm yếu của chính bản đó.
5. Tự soát và ghi bảng: số chữ từng bản · từ cấm = 0 · ngày cụ thể (nếu luật cấm) = 0 · link có mã theo dõi đúng nguyên chuỗi · không hứa kết quả không đo được.
6. Lưu vào `CAC-DU-AN/<mã-dự-án>/DANG-LAM/caption-<ten-bai>_v01_YYYYMMDD.md` (mỗi lần một tệp mới) và trình người dùng.
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.

Bản mẫu đầu ra: `~/phong-marketing-ai/references/ban-mau/caption-mau.md`.

## Xong là gì
3 bản đủ 4 phần · 1 câu đề xuất có lý do · bảng tự soát không có dòng lỗi.

## Không được làm một mình
Đăng bài là đăng công khai: chủ doanh nghiệp duyệt bản cuối rồi tự đăng.
