# Luật chung của kho phong-marketing-ai

Kho này là một phòng marketing chạy bằng AI thu nhỏ, giúp chủ doanh nghiệp nhỏ và người kinh doanh tự do trải nghiệm và vận hành các hoạt động tiếp thị trên máy tính của mình.

## Bảng 7 skill và các cổng an toàn

| Skill | Chức năng | Cổng an toàn | Cách kiểm soát |
|---|---|---|---|
| `doc-so-quang-cao` | Đọc chi phí mỗi ngày và tính giá mỗi lượt bấm | Đề xuất ngân sách | Chỉ đọc tệp CSV trên máy, không tiêu tiền, không đụng tài khoản quảng cáo |
| `caption-fanpage` | Soạn 3 phương án bài đăng kèm đề xuất | Soạn thảo nội dung | Chỉ soạn nội dung, không tự đăng bài |
| `lich-dang-7-ngay` | Lên kế hoạch lịch đăng 7 ngày và gắn link UTM | Đo lường theo dõi | Chỉ đọc/ghi tệp nội bộ, xuất bảng nháp để duyệt |
| `fb-chia-khoa` | Kiểm tra thời hạn và quyền của chìa Trang | Xác thực Meta | Chỉ kiểm tra chìa đã cất, không in chìa, không sửa tệp |
| `fanpage-post` | Đăng bài viết lên Trang Facebook | Cổng publish (công khai) | In thử cho chủ duyệt, chỉ đăng thật khi có cờ `--dong-y`; đọc ngược xác nhận |
| `doc-comment-fanpage` | Đọc và trả lời từng bình luận trên Trang | Cổng publish (công khai) | Mặc định chỉ đọc; trả lời cần cờ `--dong-y`; dữ liệu lưu tại `out/` |
| `tra-loi-inbox-fanpage` | Đọc và trả lời tin nhắn riêng của khách | Cổng customer-message (gửi khách) | Mặc định chỉ đọc; chặn gửi ngoài cửa sổ 24 giờ; cần cờ `--dong-y` |

> **Quy trình duyệt các cổng publish và customer-message:** Chạy lệnh thiếu cờ `--dong-y` để in bản xem trước → đưa bản xem trước cho chủ doanh nghiệp duyệt → chủ doanh nghiệp đồng ý → chạy lại với cờ `--dong-y`. Đây là quy trình làm việc (luật vận hành), không phải máy chặn tự động.

## Bảng 6 cổng an toàn

| Cổng | Lệnh trong bộ marketing chạm cổng | Ai giữ cổng trên máy học viên (phiên mở ở gốc OPC) |
|---|---|---|
| `ads-account-write` | không có; bộ chỉ đọc tệp CSV chi quảng cáo | không có đường ghi trong bộ; OPC chưa có máy giữ |
| `customer-message` | `page_inbox.py … --dong-y` | cờ `--dong-y` của script. Hook 6 `guard_bulk_send.py` chỉ thấy địa chỉ gửi tin nằm trên dòng lệnh; script này gọi bên trong nên OPC chưa có máy giữ (từ bản OPC v07: hook 6 hỏi theo tên script) |
| `publish` | `page_post.py … --dong-y` · `page_comments.py … --dong-y` | cờ `--dong-y` của script. Danh sách địa chỉ của hook 6 chưa có `/feed`, `/comments`, `/photos`, nên ngay cả lệnh curl đăng bài cũng không bị hỏi; OPC chưa có máy giữ (từ bản OPC v07: hook 6 hỏi theo tên script và ba địa chỉ này) |
| `delete` | không có lệnh xoá | xoá TỆP trên máy: hook 1 `block_mass_delete.py` và luật cấm `Bash(rm:*)` của OPC · xoá BÀI hay BÌNH LUẬN trên Trang qua API: OPC chưa có máy giữ |
| `customer-page-deploy` | không có lệnh đẩy trang | không có đường đẩy trang trong bộ; OPC chưa có máy giữ |
| `crm-bulk-or-edit` | không có; bộ chỉ đọc tệp CSV nội bộ | không có đường ghi trong bộ; OPC chưa có máy giữ |

Chìa Trang: hook 2 `block_secret_leak.py` chặn khi đường chìa nằm trên dòng lệnh (đối số của lệnh đọc, hoặc chuyển hướng `<`); script tự đọc chìa bên trong thì hook không thấy, nên chỗ giữ thật là luật script không in chìa.
Không chép tệp từ `out/` vào `DANG-LAM/`: đây là luật chữ, bộ khung OPC chưa chặn được việc chép bằng lệnh.

## 6 luật an toàn cốt lõi

1. **Không chi tiền.** Không tạo, sửa, bật, tắt quảng cáo, không đổi ngân sách. Công cụ chỉ ĐỀ XUẤT; chủ doanh nghiệp tự quyết và tự thực hiện.
2. **Không đăng công khai, không gửi tin cho khách** khi chủ doanh nghiệp chưa duyệt từng lần qua cờ `--dong-y`.
3. **Bảo vệ dữ liệu khách hàng**: Dữ liệu thô của người thứ ba (bình luận, tin nhắn tải về) chỉ nằm ở `~/phong-marketing-ai/out/<mã-Trang>/` đã được git bỏ qua; không chép vào dự án OPC, trừ khi chủ doanh nghiệp tự chép vào `DAU-VAO/`. Bản nháp ghi vào `CAC-DU-AN/<mã-dự-án>/DANG-LAM/`, chỉ nhắc tên khách khi cần, không ghi số điện thoại, email hay số tài khoản. Bản chốt ghi tệp mới `<tên>_final.md` trong `DAU-RA/`, chỉ khi chủ doanh nghiệp đồng ý.
4. **Không in, không ghi** chìa truy cập, mật khẩu, token vào màn hình hay nhật ký.
5. **Không hứa kết quả không đo được.** Mọi nhận định số liệu đều phải có nguồn từ tệp đo thật.
6. **Nói lời thường** rõ ràng, ngắn gọn; thông báo trước khi chạy lệnh và giải thích kết quả sau khi hoàn thành.
