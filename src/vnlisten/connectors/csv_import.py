"""Import mention từ file CSV – "cửa sau" cho Facebook group / TikTok / Threads khi chưa có crawler.

Cách dùng thực tế (0 đồng):
  - Dùng extension export comment/post miễn phí, hoặc copy tay các bài nổi bật vào Google Sheet
  - Export CSV với các cột (tối thiểu: content, published_at):
      external_id, url, title, content, author, published_at, likes, comments, shares, views
  - vnlisten import-csv file.csv --source facebook

Data sau đó đi qua đúng pipeline như các nguồn khác => dashboard tự cập nhật.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from ..domain.models import Engagement, Mention, SourceType


def _int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    parsed = datetime.fromisoformat(value.strip())
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def read_csv(path: str | Path, source: SourceType, category: str = "", industry: str = "") -> list[Mention]:
    """industry để trống => router tự đoán ngành dựa trên brand/sản phẩm được nhắc."""
    mentions = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            content = (row.get("content") or "").strip()
            if not content:
                continue
            ext_id = row.get("external_id") or hashlib.sha1(
                f"{row.get('url', '')}{content}".encode()
            ).hexdigest()
            mentions.append(
                Mention(
                    source=source,
                    external_id=ext_id,
                    url=row.get("url", ""),
                    title=row.get("title", ""),
                    content=content,
                    author=row.get("author", ""),
                    published_at=_date(row["published_at"]),
                    engagement=Engagement(
                        likes=_int(row.get("likes")), comments=_int(row.get("comments")),
                        shares=_int(row.get("shares")), views=_int(row.get("views")),
                    ),
                    keyword="csv-import",
                    category=category,
                    industry=industry,
                )
            )
    return mentions
