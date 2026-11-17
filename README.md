# VN Listen – Social listening & MKT research đa ngành hàng

Tool thu thập → phân tích → cảnh báo → dashboard cho thảo luận về sản phẩm theo ngành hàng.
Thiết kế **0 đồng**: SQLite, nguồn miễn phí, sentiment rule-based / model local, LLM local (tuỳ chọn).

## Chạy nhanh

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # điền YOUTUBE_API_KEY, TELEGRAM_* nếu có

vnlisten seed-demo                # dữ liệu giả lập -> data/demo.db
vnlisten --db data/demo.db dashboard

vnlisten industries               # liệt kê ngành đang cấu hình
vnlisten daily                    # thu thập thật (Google News + YouTube + Tiki + Google Suggest) + cảnh báo + insight
vnlisten insight --industry y_te_suc_khoe
vnlisten watch add "sữa công thức" --industry me_va_be   # thêm từ khoá tự do cho job daily
vnlisten schedule                 # chạy liên tục: hourly :07, daily 06:23 (giờ VN)
vnlisten dashboard
pytest
```

## Ngành hàng & module

| Ngành | File |
|---|---|
| Mother & Baby (Mẹ & Bé) | `config/industries/me_va_be.yaml` |
| Healthcare (Y tế / Sức khoẻ) – dược, TPCN, thiết bị, nhà thuốc **+ 35 BV công VN, 19 BV tư VN, 23 BV châu Á, 13 BV châu Âu** | `config/industries/y_te_suc_khoe.yaml` |

> ⚠ Thông tin `meta` của bệnh viện (thành phố, loại hình, chuyên khoa) được tổng hợp sẵn – nên rà soát trước khi dùng cho báo cáo chính thức.

**UI tiếng Anh, dữ liệu & ô tìm kiếm tiếng Việt.** Sidebar dashboard: Industry · Module · Date range (khoảng bất kỳ) ·
Search (gõ bất kỳ từ nào, có dấu hay không dấu) · Sources. Từ khoá search có thể bấm **Track** để job daily thu thập.

**Thêm ngành = thêm 1 file YAML**, không sửa code. Mỗi ngành tự khai báo: ngành con, brand, sản phẩm + alias,
từ khoá rủi ro, từ vựng sentiment riêng, từ khoá hoạt động MKT riêng, seed keyword research.

Dashboard: chọn **ngành** + **module** ở sidebar.

| Module | Trả lời câu hỏi | Metric |
|---|---|---|
| Social Listening › **Communities** | Nên vào group/kênh nào? | Rà soát, chấm điểm (activity, engagement, relevance, buying intent, openness), xếp hạng & đề xuất hành động cho từng community theo từ khoá đang search |
| Social Listening | Người ta đang **nói** gì về brand? | Lượt nhắc, tương tác, SOV, NSR, buzz growth, ranking, sắc thái, **Product keywords** (mọi keyword nhắc kèm 1 sản phẩm/brand/bệnh viện), cảnh báo, top sàn |
| Marketing Research | Brand đang **làm** gì, thị trường **quan tâm** gì? | Loại hoạt động MKT, online vs offline, brand × hoạt động, hashtag chiến dịch, hiệu suất keyword, gợi ý Google, cụm từ đang lên |

## Kiến trúc

```
Taxonomy (YAML) ──┐
                  ▼
Connectors ──► EnrichmentPipeline ──► Repository ──► Analytics ──► Dashboard (Streamlit)
(MentionSource)   IndustryRouter         (SQLite)     metrics.py      │
                   ├ EntityMatcher                    research.py     ├─► AlertService (theo ngành) ──► Console / Telegram
                   ├ Sentiment (+từ vựng ngành)                       └─► InsightService (theo ngành) ──► RuleBased / Ollama
                   └ ActivityClassifier (+hashtag)
MarketplaceSource, KeywordSource ─────────►
```

| Thư mục | Vai trò |
|---|---|
| `domain/` | Model + **ports (Protocol)**. Không phụ thuộc IO. |
| `connectors/` | Mỗi nguồn 1 class: `google_news`, `youtube`, `tiki`, `csv_import` |
| `pipeline/` | Router theo ngành, match brand/sản phẩm/từ khoá rủi ro, sentiment, phân loại hoạt động MKT |
| `storage/` | `SqliteRepository` implement các repository port |
| `analytics/` | `metrics.py` (listening) · `research.py` (hoạt động, hashtag, keyword, trend) · `keywords.py` (search + product keywords) · `phrases.py` (n-gram dùng chung) |
| `alerts/` | Luật cảnh báo + notifier |
| `insights/` | Sinh nhận định & đề xuất hành động |
| `services.py` | Use-case, chỉ phụ thuộc ports |
| `container.py` | **Composition root**: nơi duy nhất chọn class cụ thể |

**Mở rộng (OCP):**
- Thêm nguồn: viết class có `source` + `fetch(query, since)`, đăng ký trong `container.py`.
- Thêm luật cảnh báo: class có `name` + `evaluate(mentions, now)`.
- Thêm ngành hàng: tạo `config/industries/<nganh>.yaml`.
- Thêm module dashboard: thêm 1 file `dashboard/views/<module>.py` + 1 dòng trong `MODULES` (`dashboard/app.py`).
- Đổi sentiment sang PhoBERT: `pip install -e ".[ml]"`, đổi `LexiconSentimentAnalyzer` → `TransformerSentimentAnalyzer`.

## Nguồn dữ liệu (miễn phí)

| Nguồn | Trạng thái | Ghi chú |
|---|---|---|
| Google News RSS | ✅ | Báo chí, cực quan trọng để bắt khủng hoảng |
| YouTube Data API | ✅ (cần key free) | 10k units/ngày ≈ 80 lượt search. Lấy cả comment |
| Tiki | ✅ | Ranking theo lượt bán thật. Endpoint không chính thức |
| Google Autocomplete | ✅ | Keyword research: người dùng đang gõ tìm gì. Không có search volume |
| Facebook / TikTok / Instagram / Threads | ✅ Browser extension | `vnlisten serve` + cài `extension/` – gửi bài **bạn đang xem** về máy (xem `extension/README.md`) |
| Facebook group public / TikTok / Threads / IG | ✅ Web search | `site:facebook.com/groups "từ khoá"` qua SearXNG tự host (`SEARXNG_URL`) hoặc Google CSE |
| Bất kỳ | ✅ CSV import | `vnlisten import-csv file.csv --source facebook` |

### Vì sao không "cào API" Facebook/TikTok?
Meta khai tử Groups API (2024); Threads/IG API chỉ đọc tài khoản của chính bạn (Threads có keyword search nhưng giới hạn);
TikTok Research API chỉ cấp cho giới học thuật. Bot tự đăng nhập để cào = khoá tài khoản + rủi ro pháp lý.
=> 0 đồng thì dùng 2 đường: **extension đọc thứ bạn đang xem** (không tự động hoá) + **tìm kiếm web cho nội dung public**.

## Metric

- **SOV**: mentions brand / tổng mentions các brand
- **NSR**: (tích cực − tiêu cực) / (tích cực + tiêu cực)
- **Buzz growth**: % thay đổi so với kỳ liền trước
- **Điểm xếp hạng**: 45% mentions + 35% tương tác (percentile) + 20% NSR, chỉnh tại `analytics/metrics.py`
