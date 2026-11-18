# VN Listen Capture (browser extension)

Gửi các bài **bạn đang xem** trên Facebook / TikTok / Instagram / Threads về VN Listen chạy trên máy bạn.

## Cài đặt (Chrome / Edge / Cốc Cốc)
1. Mở `chrome://extensions` → bật **Developer mode** → **Load unpacked** → chọn thư mục `extension/` này.
2. Ghim icon VN Listen lên thanh công cụ.

## Chế độ GitHub (mặc định – dùng với dashboard trên cloud, KHÔNG cần chạy server)
1. Tạo token: https://github.com/settings/personal-access-tokens/new
   - Repository access: **Only select repositories** → chọn repo của bạn
   - Permissions → Repository permissions → **Contents: Read and write** (không cấp gì khác)
2. Bấm icon extension → **Settings** → *Send to*: **GitHub** → điền Repository (`owner/tên-repo`) và token.
3. Mỗi lần Capture, bài được lưu vào nhánh `captures`; lần chạy tự động kế tiếp (≤ 2 giờ) đưa vào dashboard.

> Token chỉ nằm trong trình duyệt của bạn. Đừng cài extension này trên máy dùng chung.

## Chế độ Local server (chạy tool trên máy)
Chạy `vnlisten serve` rồi chọn *Send to*: **Local server**.

## Sử dụng
- Vào group / trang search / hashtag cần theo dõi → bấm icon → **Capture this page**.
- Bật **Auto-capture while I scroll**: cứ lướt bình thường, bài mới hiện ra sẽ tự gửi sau ~2.5s dừng cuộn.
- Bôi đen đoạn văn bất kỳ → chuột phải → **Send selected text to VN Listen** (dùng được cả khi layout nền tảng đổi).

## Nói thẳng về rủi ro
- Extension **không** tự đăng nhập, tự cuộn hay tự click – chỉ đọc thứ đang hiển thị. Rủi ro bị khoá tài khoản thấp hơn nhiều
  so với bot cào, nhưng việc trích xuất dữ liệu vẫn trái điều khoản của các nền tảng. Dùng cho nghiên cứu cá nhân, khối lượng vừa phải.
- Tên người đăng được **băm** trước khi lưu (không lưu danh tính) – phù hợp tinh thần NĐ 13/2023 về dữ liệu cá nhân.
- Các nền tảng đổi giao diện thường xuyên → bộ chọn (selector) trong `content.js` có thể hỏng. Khi đó dùng chuột phải gửi đoạn chọn,
  hoặc báo lại để sửa selector.
