# phong-marketing-ai — PHÒNG MARKETING CHẠY BẰNG AI THU NHỎ

Bộ này dùng cùng tên ghế và sáu cổng an toàn với phòng marketing của AIBOSS Office bản office-marketing-v0.1.

Kho này là một phòng marketing chạy bằng AI thu nhỏ, giúp chủ doanh nghiệp nhỏ và người làm việc tự do tự động hoá và kiểm soát các công việc marketing: đọc số quảng cáo, lên lịch đăng bài và quản lý tương tác Trang Facebook an toàn trên máy tính của mình.

## Ba việc của bản đầu và 7 skill marketing có sẵn

Ba việc trọng tâm của bản đầu: **đọc số quảng cáo · soạn caption fanpage · lịch đăng 7 ngày**.

| Tên skill | Việc làm được | Cổng kiểm soát | Thời gian chạy |
|---|---|---|---|
| `doc-so-quang-cao` | Đọc chi phí mỗi ngày, tính giá mỗi lượt bấm theo từng mẫu, báo ngày vượt trần | Đề xuất ngân sách | ~1 phút |
| `caption-fanpage` | Soạn 3 phương án bài đăng kèm phân tích mạnh/yếu, 1 đề xuất và bảng tự soát | Soạn thảo nội dung | ~2 phút |
| `lich-dang-7-ngay` | Lên kế hoạch lịch đăng 7 ngày trên Trang và Instagram, gắn link theo dõi UTM chuẩn | Đo lường theo dõi | ~1 phút |
| `fb-chia-khoa` | Kiểm tra thời hạn, danh sách quyền và các Trang Facebook quản lý | Xác thực Meta | ~30 giây |
| `fanpage-post` | Đăng bài lên Trang Facebook: in thử cho chủ duyệt, chỉ đăng thật khi có cờ `--dong-y` | Cổng publish (công khai) | ~1 phút |
| `doc-comment-fanpage` | Đọc và lưu bình luận mới về máy, trả lời từng bình luận công khai sau khi duyệt | Cổng publish (công khai) | ~1 phút |
| `tra-loi-inbox-fanpage` | Đọc và trả lời tin nhắn riêng của khách trong cửa sổ 24 giờ của Meta | Cổng customer-message (gửi khách) | ~1 phút |

> **Quy trình duyệt các thao tác xuất bản và gửi tin:** Chạy lệnh không có cờ `--dong-y` để in bản xem trước → đưa bản xem trước cho chủ doanh nghiệp duyệt → chủ doanh nghiệp đồng ý → mới chạy lại với cờ `--dong-y`. Đây là quy trình làm việc (luật vận hành), không phải máy chặn tự động.

## Tám ghế chuyên môn (subagents)

Học viên làm việc trong phiên Claude mở tại thư mục gốc kho OPC. Phiên gốc gọi tới 8 tệp vai chuyên môn:

| Mã ghế | Tên gọi | Việc chính | Skill dùng |
|---|---|---|---|
| `marketing-lead` | Trưởng phòng marketing | Phân rã mục tiêu, đọc số quảng cáo, lên lịch đăng 7 ngày, nghiệm thu vòng một | `doc-so-quang-cao`, `lich-dang-7-ngay` |
| `content-writer` | Người viết | Soạn bài viết, caption mạng xã hội 3 phương án kèm bảng tự soát | `caption-fanpage` |
| `social-community` | Quản lý cộng đồng | Quản lý lịch đăng, đăng bài sau duyệt, đọc bình luận, trả lời hộp thư 24 giờ | `lich-dang-7-ngay`, `fanpage-post`, `doc-comment-fanpage`, `tra-loi-inbox-fanpage`, `fb-chia-khoa` |
| `email-crm` | Chuyên viên Email và CRM | Thiết kế chuỗi email chăm sóc khách hàng, soạn bản tin định kỳ | Năng lực Claude (cổng `customer-message`) |
| `paid-media` | Chuyên viên Quảng cáo trả phí | Lập cấu trúc chiến dịch, tạo link UTM quảng cáo, phân tích chi phí hằng ngày | `doc-so-quang-cao`, `lich-dang-7-ngay` |
| `video-creative` | Chuyên viên Sáng tạo video | Soạn kịch bản video ngắn, dàn ý hình ảnh, viết caption đi kèm video | `caption-fanpage` |
| `funnel-offer` | Chuyên viên Phễu và chào hàng | Thiết kế hành trình khách hàng, đóng gói gói giải pháp, tạo link trang đích | `lich-dang-7-ngay` |
| `marketing-reviewer` | Người soát xét marketing | Thẩm định độc lập chất lượng nội dung, đối chiếu sự thật, bảo vệ 6 cổng an toàn | Không dùng skill ghi |

Ví dụ gọi ghế trong phiên gốc OPC:
> "Nhờ `marketing-lead` đọc số quảng cáo tuần này từ tệp CSV trong thư mục `DAU-VAO` của dự án và đề xuất hướng phân bổ ngân sách."

## Từ bản nháp tới bản chốt

- Bản nháp nằm ở `DANG-LAM/` của dự án, mỗi lần một bản mới.
- Chủ doanh nghiệp đọc và gật.
- Claude tạo tệp MỚI `<tên>_final.md` trong `DAU-RA/`.
- Muốn đổi bản chốt thì làm bản nháp mới rồi chốt lại, không sửa tệp chốt cũ.

## Nối Trang Facebook của bạn (5 bước cài đặt)

**Điều kiện cần trước khi cài đặt:**
- Máy Mac (macOS 13 trở lên).
- Đã cài Git.
- Python 3 đi kèm Command Line Tools (đã có khi cài kho OPC), không cần cài thêm.
- Đã cài Claude Code.
- Kho OPC (`opc-business-harness`) đã cài đặt xong trên máy.

1. **Tải kho về máy:**
   ```bash
   git clone https://github.com/erocathanh/phong-marketing-ai.git ~/phong-marketing-ai
   ```
2. **Cài đặt lối tắt các skill và tệp vai vào môi trường Claude:**
   ```bash
   bash ~/phong-marketing-ai/scripts/install.sh
   ```
3. **Kiểm tra môi trường hệ thống:**
   ```bash
   python3 ~/phong-marketing-ai/scripts/check_setup.py
   ```
   (Kết quả hiển thị `KẾT QUẢ: 13/13 đạt — bộ cài sẵn sàng` là hoàn tất).
4. **Cất chìa truy cập Facebook Page:**
   Học viên TỰ chạy trong Terminal, không nhờ Claude:
   ```bash
   cd ~/opc-business-harness && python3 tools/inbox-reader/save_token.py
   ```
   Nếu anh chị cài kho OPC ở chỗ khác, thay `~/opc-business-harness` bằng đường đó.
   Chìa cần có đủ 7 quyền nền tảng đã liệt kê ở skill `fb-chia-khoa` (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_engagement`, `pages_read_user_content`, `pages_messaging`, `pages_manage_metadata`).
   Một chìa dùng chung cho bộ đọc hộp thư của kho OPC và bộ marketing; cất chìa mới sẽ thay chìa cũ, nên chìa mới phải đủ cả 7 quyền.
   Bộ khung OPC chặn Claude đọc hay in tệp chìa; các script tự dùng chìa bên trong và không in chìa ra.
   Không chép tệp từ `out/` vào `DANG-LAM/`: đây là luật chữ, bộ khung OPC chưa chặn được việc chép bằng lệnh.
5. **Mở phiên làm việc tại gốc kho OPC:**
   ```bash
   cd ~/opc-business-harness && claude
   ```
   Nếu anh chị cài kho OPC ở chỗ khác, thay `~/opc-business-harness` bằng đường đó.
   Claude hỏi có tin cậy thư mục này không thì bấm Đồng ý. Khởi động Claude tại thư mục gốc kho OPC của bạn để toàn bộ các hook an toàn và tệp vai được kích hoạt tự động khi thực hiện các tác vụ marketing.

## Môi trường hỗ trợ

- Hệ điều hành: macOS 13 trở lên (đợt này chưa hỗ trợ Windows, như kho OPC).
- Python: Python 3 đi kèm Command Line Tools (đã có khi cài kho OPC), không cần cài thêm.

## Giấy phép

Xem [LICENSE](LICENSE) — © Eroca Thanh. Dùng để học.
