"""Tìm bài PUBLIC trên mạng xã hội qua công cụ tìm kiếm – không cần API của Meta/TikTok.

    site:facebook.com/groups "sữa công thức"   -> bài trong group public (Google chỉ index group public)
    site:tiktok.com "sữa công thức"            -> video TikTok
    site:threads.net / site:instagram.com      -> Threads / Instagram public

Backend (chọn 1, đều miễn phí):
  - SearXNG tự host (khuyên dùng): `docker run -p 8888:8080 searxng/searxng`, bật format json trong settings.yml.
  - Google Programmable Search JSON API: 100 truy vấn/ngày miễn phí, cần API key + Search Engine ID.
    ⚠ Google đã ngừng nhận khách hàng mới cho API này – nếu tài khoản của bạn không tạo được, dùng SearXNG.

Hạn chế: chỉ thấy đoạn trích (snippet) chứ không có toàn bài, không có số tương tác, độ trễ index vài ngày.
=> Dùng để PHÁT HIỆN bài & community, còn đọc sâu thì dùng browser extension.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from ..domain.models import Mention, SourceType, TrackingQuery
from ..pipeline.text import strip_html
from .http import PoliteClient

SITES: dict[SourceType, tuple[str, ...]] = {
    SourceType.FACEBOOK: ("facebook.com/groups", "facebook.com"),
    SourceType.TIKTOK: ("tiktok.com",),
    SourceType.THREADS: ("threads.net", "threads.com"),
    SourceType.INSTAGRAM: ("instagram.com",),
}


class SearchBackend(Protocol):
    def search(self, query: str, days: int) -> list[dict]: ...


class SearxngBackend:
    def __init__(self, base_url: str, client: PoliteClient | None = None):
        self._url = base_url.rstrip("/") + "/search"
        self._client = client or PoliteClient(min_interval=2.0)

    def search(self, query: str, days: int) -> list[dict]:
        time_range = "day" if days <= 1 else "week" if days <= 7 else "month" if days <= 31 else "year"
        data = self._client.get(self._url, params={"q": query, "format": "json", "language": "vi",
                                                   "time_range": time_range}).json()
        return parse_searxng(data)


class GoogleCseBackend:
    API = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cx: str, client: PoliteClient | None = None):
        self._key, self._cx = api_key, cx
        self._client = client or PoliteClient(min_interval=1.0)

    def search(self, query: str, days: int) -> list[dict]:
        data = self._client.get(self.API, params={"key": self._key, "cx": self._cx, "q": query, "num": 10,
                                                  "gl": "vn", "lr": "lang_vi", "dateRestrict": f"d{max(days, 1)}"}).json()
        return parse_google_cse(data)


def parse_searxng(data: dict) -> list[dict]:
    out = []
    for r in data.get("results", []):
        published = r.get("publishedDate")
        out.append({"url": r.get("url", ""), "title": r.get("title", ""), "snippet": r.get("content", ""),
                    "published": published})
    return out


def parse_google_cse(data: dict) -> list[dict]:
    out = []
    for item in data.get("items", []):
        meta = ((item.get("pagemap") or {}).get("metatags") or [{}])[0]
        out.append({"url": item.get("link", ""), "title": item.get("title", ""),
                    "snippet": meta.get("og:description") or item.get("snippet", ""),
                    "published": meta.get("article:published_time")})
    return out


def _source_of(url: str) -> SourceType | None:
    for source, sites in SITES.items():
        if any(site.split("/")[0] in url for site in sites):
            return source
    return None


def _date(value: str | None) -> datetime:
    if value:
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


class WebSearchConnector:
    """MentionSource: 1 TrackingQuery -> N truy vấn site:... trên các nền tảng đã chọn."""

    source = SourceType.WEB

    def __init__(self, backend: SearchBackend, platforms: tuple[SourceType, ...] = tuple(SITES)):
        self._backend = backend
        self._platforms = platforms

    def queries_for(self, keyword: str) -> list[str]:
        return [f'site:{SITES[p][0]} "{keyword}"' for p in self._platforms]

    def fetch(self, query: TrackingQuery, since: datetime) -> list[Mention]:
        days = max(1, (datetime.now(UTC) - since).days)
        mentions = []
        for q in self.queries_for(query.keyword):
            for r in self._backend.search(q, days):
                source = _source_of(r["url"])
                text = strip_html(f"{r['title']}. {r['snippet']}").strip()
                if source is None or len(text) < 10:
                    continue
                mentions.append(Mention(
                    source=source, external_id=r["url"], url=r["url"], title=strip_html(r["title"]),
                    content=strip_html(r["snippet"]), published_at=_date(r.get("published")),
                    keyword=query.keyword, category=query.category, industry=query.industry,
                    # Google/SearXNG chỉ trả về trang công khai
                    visibility="public",
                ))
        return mentions
