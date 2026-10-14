---
name: lich-dang-7-ngay
description: Lên kế hoạch và khung lịch đăng bài 7 ngày cho Trang Facebook và Instagram, gắn link theo dõi UTM chuẩn cho từng bài, xuất bảng Markdown và tệp CSV để chủ doanh nghiệp duyệt. Dùng khi người dùng nói "lên lịch đăng tuần", "lịch đăng 7 ngày", "kế hoạch nội dung tuần", "tạo link utm", "gắn mã theo dõi". Chỉ đọc và ghi tệp nội bộ trên máy, không tự đăng bài.
---

# Lịch đăng 7 ngày và gắn mã theo dõi

## Vì sao cần
Đăng bài ngẫu hứng thường dẫn đến gián đoạn kênh, thiếu nhất quán thông điệp và không đo lường được bài viết nào mang lại kết quả.
Lên khung lịch 7 ngày giúp chủ doanh nghiệp chủ động nội dung cả tuần, cân bằng các định dạng (ảnh, video, câu chuyện), và mỗi bài viết đều có link gắn mã theo dõi (UTM) chuẩn xác để biết người xem đến từ bài nào.

## Đầu vào
- Thông tin tuần: mô tả ngắn doanh nghiệp, mục tiêu tuần, danh sách chủ đề hoặc góc bài, ngày có thể đăng. Mẫu: `~/phong-marketing-ai/references/du-lieu-mau/ke-hoach-tuan-mau.json`.
- Bảng kế hoạch link UTM bổ sung (nếu có chiến dịch riêng): `~/phong-marketing-ai/references/du-lieu-mau/ke-hoach-utm.csv`.
  Cột: `trang_dich, nguon, kenh, dot, mau, noi_dung`. Cột `kenh` mặc định là `organic` cho bài đăng thường, `paid` cho quảng cáo trả tiền.

## Các bước
1. Tự kiểm tra các công cụ:
   ```bash
   python3 ~/.claude/skills/lich-dang-7-ngay/scripts/build_schedule.py --tu-kiem
   python3 ~/.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py --tu-kiem
   ```
   Cả hai lệnh phải báo đạt hết tất cả các tiêu chí.
2. Tạo khung lịch 7 ngày:
   ```bash
   python3 ~/.claude/skills/lich-dang-7-ngay/scripts/build_schedule.py --input ~/phong-marketing-ai/references/du-lieu-mau/ke-hoach-tuan-mau.json --ra CAC-DU-AN/<mã-dự-án>/DANG-LAM
   ```
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.

   Lệnh xuất ra `CAC-DU-AN/<mã-dự-án>/DANG-LAM/lich-dang-7-ngay_vNN_YYYYMMDD.md` (bảng Markdown dễ đọc) và `lich-dang-7-ngay_vNN_YYYYMMDD.csv` (dữ liệu 9 cột chi tiết). Nếu thiếu `--ra`, script mặc định ghi vào `~/phong-marketing-ai/out/`.
3. Tạo link UTM riêng lẻ hoặc theo danh sách khi cần:
   ```bash
   # Tạo theo danh sách kế hoạch
   python3 ~/.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py --plan ~/phong-marketing-ai/references/du-lieu-mau/ke-hoach-utm.csv --ra CAC-DU-AN/<mã-dự-án>/DANG-LAM
   # Hoặc tạo một link cụ thể
   python3 ~/.claude/skills/lich-dang-7-ngay/scripts/make_utm_links.py --url https://example.com/landing --campaign tuan-01 --source facebook --medium organic
   ```
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.
4. Trình chủ doanh nghiệp duyệt khung lịch tuần trước khi tiến hành viết chi tiết từng bài.

Bản mẫu đầu ra:
- `~/phong-marketing-ai/references/ban-mau/lich-dang-7-ngay-mau.md`
- `~/phong-marketing-ai/references/ban-mau/link-utm-mau.csv`

## Xong là gì
- Đủ 7 dòng tương ứng 7 ngày trong tuần (hoặc các ngày đăng dự kiến).
- Mỗi dòng có đủ 9 cột: thứ trong tuần · giờ đăng · kênh (Trang Facebook hay Instagram) · dạng bài · chủ đề hoặc góc · câu mở · lời kêu gọi · link gắn utm · trạng thái (nháp / chờ duyệt / đã đăng).
- Mọi link UTM đều hợp lệ, không chứa ký tự cấm, đúng tham số `utm_medium` (`organic` hoặc `paid`).

## Không được làm một mình
Đăng bài lên kênh công khai là hành động phát ngôn của thương hiệu: chủ doanh nghiệp duyệt nội dung và tự quyết định thời điểm phát hành.
