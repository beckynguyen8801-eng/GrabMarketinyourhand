"""Google News RSS – miễn phí, không cần key, ổn định. Nguồn tốt nhất để bắt khủng hoảng trên báo chí."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from ..domain.models import Mention, SourceType, TrackingQuery
from ..pipeline.text import strip_html
from .http import PoliteClient

RSS_URL = "https://news.google.com/rss/search?q={q}&hl=vi&gl=VN&ceid=VN:vi"


def parse_rss(xml_text: str, query: TrackingQuery, since: datetime) -> list[Mention]:
    root = ET.fromstring(xml_text)
    mentions: list[Mention] = []
    for item in root.iter("item"):
        pub_raw = item.findtext("pubDate")
        published = parsedate_to_datetime(pub_raw) if pub_raw else datetime.now(UTC)
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        if published < since:
            continue
        link = item.findtext("link") or ""
        mentions.append(
            Mention(
                source=SourceType.GOOGLE_NEWS,
                external_id=item.findtext("guid") or link,
                url=link,
                title=strip_html(item.findtext("title") or ""),
                content=strip_html(item.findtext("description") or ""),
                author=item.findtext("source") or "",
                published_at=published,
                keyword=query.keyword,
                category=query.category,
                industry=query.industry,
            )
        )
    return mentions


class GoogleNewsConnector:
    source = SourceType.GOOGLE_NEWS

    def __init__(self, client: PoliteClient | None = None):
        self._client = client or PoliteClient(min_interval=1.5)

    def fetch(self, query: TrackingQuery, since: datetime) -> list[Mention]:
        days = max(1, (datetime.now(UTC) - since).days)
        url = RSS_URL.format(q=quote_plus(f'"{query.keyword}" when:{days}d'))
        return parse_rss(self._client.get(url).text, query, since)
