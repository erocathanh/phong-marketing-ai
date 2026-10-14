---
name: doc-so-quang-cao
description: Đọc số quảng cáo mỗi ngày từ tệp CSV chi tiêu xuất từ trình quản lý quảng cáo (kèm tệp danh sách đăng ký nếu có) và ra báo cáo chi phí từng mẫu quảng cáo, kèm đề xuất giữ · xem lại · ngày vượt trần. Dùng khi người dùng nói "đọc số quảng cáo", "quảng cáo hôm nay thế nào", "mẫu nào hiệu quả", "chi phí mỗi đăng ký". Chỉ đọc tệp, không đụng tài khoản quảng cáo, không chi tiền.
---

# Đọc số quảng cáo mỗi ngày

## Khi nào dùng
Mỗi sáng, trước khi quyết giữ, giảm hay tăng tiền cho mẫu quảng cáo nào.

## Đầu vào
- CSV chi tiêu: cột `ngay, quang_cao, utm_campaign, chi_vnd, hien_thi, bam_link`.
- CSV đăng ký: cột `ngay, ma_nguoi, utm_campaign`. Không cần tên hay số điện thoại.
- Trần chi mỗi ngày (số tiền).
Chưa có tệp của bạn thì chạy trên dữ liệu mẫu trong `~/phong-marketing-ai/references/du-lieu-mau/`.

## Các bước
1. Kiểm dữ liệu chạy được: `python3 ~/.claude/skills/doc-so-quang-cao/scripts/read_ad_spend.py --tu-kiem` phải ra `5/5 đạt`.
2. Chạy báo cáo:
   - Dữ liệu mẫu: `python3 ~/.claude/skills/doc-so-quang-cao/scripts/read_ad_spend.py --ra CAC-DU-AN/<mã-dự-án>/DANG-LAM`
   - Dữ liệu của bạn: `python3 ~/.claude/skills/doc-so-quang-cao/scripts/read_ad_spend.py --spend <tệp-chi>.csv --signups <tệp-đăng-ký>.csv --daily-cap <trần> --ra CAC-DU-AN/<mã-dự-án>/DANG-LAM`
   Thay `<mã-dự-án>` bằng tên thư mục dự án của bạn trong `CAC-DU-AN/`, ví dụ `CAC-DU-AN/khach-hang-a`.
3. Đọc báo cáo trong `CAC-DU-AN/<mã-dự-án>/DANG-LAM/bao-cao-quang-cao_vNN_YYYYMMDD.md` (hoặc `~/phong-marketing-ai/out/bao-cao-quang-cao_vNN_YYYYMMDD.md` nếu không truyền `--ra`): chi phí mỗi đăng ký từng mẫu, mẫu nào chưa có đăng ký, ngày nào vượt trần.
4. Nói lại cho người dùng bằng lời thường: mẫu tốt nhất, mẫu cần xem lại, có vượt trần không.

Bản mẫu đầu ra (chạy trên dữ liệu mẫu): `~/phong-marketing-ai/references/ban-mau/bao-cao-quang-cao-mau.md`.

## Xong là gì
- Tổng chi trong báo cáo bằng tổng cột `chi_vnd` của tệp CSV.
- Số đăng ký có mã theo dõi bằng số dòng có `utm_campaign` trong tệp đăng ký.
- Báo cáo có dòng `SỐ: chi= · kq= · nguon=` để ghi sổ.

## Không được làm một mình
Tắt, bật hay đổi tiền cho quảng cáo là việc của chủ doanh nghiệp. Skill này chỉ ĐỀ XUẤT.
