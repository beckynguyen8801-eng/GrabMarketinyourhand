"""Chuyển dữ liệu từ browser extension "VN Listen Capture" thành Mention.

Extension chạy trong trình duyệt CỦA BẠN, đọc các bài đang hiển thị khi bạn lướt
Facebook / TikTok / Instagram / Threads (đã đăng nhập sẵn), rồi POST về máy bạn:

    POST http://127.0.0.1:8765/ingest
    {"source": "facebook", "page_url": "...", "page_title": "...",
     "community": {"name": "Hội mẹ bỉm sữa", "url": "https://facebook.com/groups/...", "visibility": "public"},
     "items": [{"url": "...", "text": "...", "author": "...", "published_at": "2026-11-17T08:00:00Z",
                "likes": "1,2K", "comments": "35", "shares": 4, "views": 0}]}

Không lưu tên/ID người đăng dạng thô: author được băm (giảm rủi ro dữ liệu cá nhân – NĐ 13/2023).
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from ..domain.models import Engagement, Mention, SourceType

_SOURCES = {s.value: s for s in SourceType}
# Đơn vị chỉ hợp lệ khi KHÔNG có chữ cái ngay sau: "35 bình luận" không phải 35 tỷ, "3 người" không phải 3 nghìn
_NUM_RE = re.compile(r"([\d.,]+)\s*([kKmMbB]|N|n|Tr|tr)?(?![^\W\d_])")
_MULT = {"k": 1e3, "n": 1e3, "m": 1e6, "tr": 1e6, "b": 1e9}
MAX_ITEMS = 500
MAX_TEXT = 5000


def parse_count(value: object) -> int:
    """'1,2K' -> 1200, '3,4 N' -> 3400, '2.5M' -> 2500000, '1.234' -> 1234, 35 -> 35."""
    if value is None or value == "":
        return 0
    if isinstance(value, int | float):
        return int(value)
    m = _NUM_RE.search(str(value).replace(" ", " "))
    if not m:
        return 0
    num, unit = m.group(1), (m.group(2) or "").lower()
    if unit:
        num = num.replace(",", ".")              # "1,2K" -> 1.2
        if num.count(".") > 1:
            num = num.replace(".", "", num.count(".") - 1)
        return int(float(num) * _MULT[unit])
    return int(re.sub(r"[.,]", "", num) or 0)    # "1.234" / "1,234" -> 1234


def _date(value: object) -> datetime:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / (1000 if value > 1e12 else 1), tz=UTC)
    if isinstance(value, str) and value:
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)  # nền tảng hay ghi "2 giờ" – không đủ chính xác, dùng thời điểm capture


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()[:12] if value else ""


def capture_to_mentions(payload: dict) -> list[Mention]:
    source = _SOURCES.get(str(payload.get("source", "")).lower())
    if source is None:
        raise ValueError(f"Unknown source: {payload.get('source')!r}")
    community = payload.get("community") or {}
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ValueError("items must be a list")

    mentions = []
    for item in items[:MAX_ITEMS]:
        text = str(item.get("text") or "").strip()[:MAX_TEXT]
        if len(text) < 5:
            continue
        url = str(item.get("url") or payload.get("page_url") or "")
        mentions.append(Mention(
            source=source,
            external_id=str(item.get("id") or _hash(f"{url}|{text[:200]}")),
            url=url,
            title="",
            content=text,
            author=_hash(str(item.get("author") or "")),
            published_at=_date(item.get("published_at")),
            engagement=Engagement(likes=parse_count(item.get("likes")), comments=parse_count(item.get("comments")),
                                  shares=parse_count(item.get("shares")), views=parse_count(item.get("views"))),
            keyword="browser-capture",
            industry=str(payload.get("industry") or ""),
            community_name=str(item.get("community_name") or community.get("name") or "")[:200],
            community_url=str(item.get("community_url") or community.get("url") or ""),
            visibility=str(community.get("visibility") or "unknown")
            if community.get("visibility") in ("public", "private") else "unknown",
        ))
    return mentions
