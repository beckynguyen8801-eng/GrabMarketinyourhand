# Chạy VN Listen 24/7 – miễn phí 100%

```
GitHub Actions (lịch tự động)  ──►  thu thập dữ liệu  ──►  lưu DB vào nhánh `data` của repo
                                                                     │
Streamlit Community Cloud  ◄──────────  đọc DB (10 phút/lần)  ◄──────┘
   (dashboard có link riêng, chỉ email được mời mới xem được)
```

| Thành phần | Dịch vụ | Chi phí | Cần thẻ? |
|---|---|---|---|
| Thu thập theo lịch | GitHub Actions | 0đ (2.000 phút/tháng cho repo private – tool dùng ~1.200) | Không |
| Dashboard 24/7 | Streamlit Community Cloud | 0đ | Không |
| Lưu dữ liệu | Nhánh `data` trong chính repo | 0đ | Không |
| Cảnh báo về điện thoại (tuỳ chọn) | Telegram bot | 0đ | Không |

---

## Bước 1 – Cho GitHub Actions chạy lần đầu (5 phút)

1. Vào repo trên GitHub → tab **Actions**.
   Nếu thấy nút *"I understand my workflows, go ahead and enable them"* → bấm để bật.
2. Chọn workflow **Collect data** ở cột trái → **Run workflow** → để `daily` → **Run workflow**.
3. Đợi ~10–15 phút đến khi có dấu ✅. Repo sẽ xuất hiện nhánh **`data`** chứa file `vnlisten.db`.

Từ đó trở đi workflow **tự chạy**:
- mỗi 2 giờ: quét từ khoá khủng hoảng + cảnh báo
- 06:23 sáng (giờ VN): chạy đầy đủ (Google News, Tiki, gợi ý Google, YouTube nếu có key, nhận định)

> Nếu bước Collect báo lỗi đỏ: mở log, copy đoạn lỗi gửi lại để sửa.

## Bước 2 – Tạo token chỉ-đọc cho dashboard (3 phút)

Repo là private nên dashboard cần 1 token **chỉ đọc**, **chỉ cho repo này**:

1. GitHub → ảnh đại diện → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Đặt tên `vnlisten-dashboard`, Expiration: 1 năm.
3. **Repository access** → *Only select repositories* → chọn `MarketResearch`.
4. **Permissions** → *Repository permissions* → **Contents: Read-only** (không cấp gì khác).
5. **Generate token** → copy chuỗi `github_pat_...` (chỉ hiện 1 lần).

## Bước 3 – Đưa dashboard lên Streamlit Community Cloud (5 phút)

1. Vào **https://share.streamlit.io** → đăng nhập bằng GitHub → cho phép truy cập repo private khi được hỏi.
2. **Create app** → *Deploy a public app from GitHub* (app vẫn riêng tư vì repo private) và điền:
   - Repository: `nlksthu8801/MarketResearch`
   - Branch: `main`
   - Main file path: `dashboard/app.py`
3. **Advanced settings**:
   - Python version: **3.12**
   - **Secrets** – dán:
     ```toml
     VNLISTEN_REMOTE_REPO = "nlksthu8801/MarketResearch"
     GITHUB_TOKEN = "github_pat_xxx_dán_token_ở_bước_2"
     ```
4. **Deploy** → đợi 2–4 phút → được link dạng `https://<tên-app>.streamlit.app`.
5. Trong app → **Share** → chỉ mời email của bạn/đồng nghiệp. Người ngoài không xem được.

## Bước 4 (tuỳ chọn) – Thêm nguồn & cảnh báo

GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret | Lấy ở đâu (miễn phí) | Tác dụng |
|---|---|---|
| `YOUTUBE_API_KEY` | Google Cloud Console → bật *YouTube Data API v3* → tạo API key | Thêm video + comment YouTube |
| `TELEGRAM_BOT_TOKEN` | Nhắn `@BotFather` trên Telegram → `/newbot` | Cảnh báo khủng hoảng về điện thoại |
| `TELEGRAM_CHAT_ID` | Nhắn `@userinfobot` để lấy ID của bạn | (đi kèm token trên) |

## Theo dõi thêm từ khoá

Dashboard trên cloud là **chỉ đọc**. Muốn thu thập thêm từ khoá: mở `config/watchlist.yaml` trên GitHub → ✏️ sửa → thêm dòng → **Commit**. Lần chạy daily kế tiếp sẽ tự lấy.

```yaml
me_va_be:
  - sữa công thức
  - sữa đạm A2
y_te_suc_khoe:
  - bệnh viện tư
```

Thêm brand / sản phẩm / bệnh viện: sửa `config/industries/*.yaml` tương tự.

---

## Giới hạn cần biết (nói thẳng)

- **Facebook / TikTok qua browser extension không chạy trên cloud** – extension cần `vnlisten serve` trên máy bạn
  (xem `extension/README.md`). Dữ liệu capture đó hiện chỉ nằm ở máy bạn, chưa đồng bộ lên cloud.
- **GitHub Actions dùng IP máy chủ Mỹ/Azure**: Google News thường ổn; Tiki có thể chặn → khi đó phần "Marketplace" trống.
- **Không có SearXNG** (cần máy chạy 24/7) → nguồn "web search" Facebook group public tắt, trừ khi bạn có Google CSE key.
- Quota private repo 2.000 phút/tháng: **đừng** đổi lịch dày hơn mỗi 2 giờ. Xem mức dùng ở GitHub → Settings → Billing.
- Streamlit Cloud cho app "ngủ" nếu ~12 giờ không ai mở – mở link lên là nó tự thức dậy sau ~30 giây.
- Dữ liệu GitHub Actions xoá workflow nếu repo **không có hoạt động 60 ngày** – thỉnh thoảng commit 1 thay đổi nhỏ là đủ.

## Phương án dự phòng: chạy trên máy của bạn (cũng 0đ)

```bash
pip install -e ".[dev]"
vnlisten schedule      # để cửa sổ này chạy – thu thập theo lịch khi máy bật
vnlisten dashboard     # mở http://localhost:8501
vnlisten serve         # (nếu dùng browser extension)
```
Hợp khi bạn dùng extension nhiều; nhược điểm: máy tắt là ngừng thu thập.
