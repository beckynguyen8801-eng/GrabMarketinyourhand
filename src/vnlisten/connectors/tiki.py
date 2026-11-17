"""Tiki – API listing public (không cần key). Dùng để ranking sản phẩm theo LƯỢT BÁN thật,
bổ sung cho ranking theo lượt thảo luận (buzz). Buzz cao mà bán thấp = vấn đề chuyển đổi.

Lưu ý: endpoint không chính thức, có thể đổi bất cứ lúc nào => parse phòng thủ.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ..domain.models import ProductSnapshot, SourceType, TrackingQuery
from .http import PoliteClient

LISTING_URL = "https://tiki.vn/api/v2/products"


def parse_listing(payload: dict, query: TrackingQuery, captured_at: datetime) -> list[ProductSnapshot]:
    snapshots = []
    for item in payload.get("data", []):
        sold = item.get("quantity_sold") or {}
        snapshots.append(
            ProductSnapshot(
                source=SourceType.TIKI,
                product_id=str(item.get("id")),
                name=item.get("name", ""),
                brand=item.get("brand_name", "") or "",
                category=query.category,
                price=int(item.get("price") or 0),
                sold_count=int(sold.get("value") or 0) if isinstance(sold, dict) else int(sold or 0),
                rating=float(item.get("rating_average") or 0),
                review_count=int(item.get("review_count") or 0),
                url=f"https://tiki.vn/{item.get('url_path', '')}",
                captured_at=captured_at,
                industry=query.industry,
            )
        )
    return snapshots


class TikiConnector:
    source = SourceType.TIKI

    def __init__(self, limit: int = 40, client: PoliteClient | None = None):
        self._limit = limit
        self._client = client or PoliteClient(min_interval=2.5)

    def fetch_products(self, query: TrackingQuery) -> list[ProductSnapshot]:
        resp = self._client.get(LISTING_URL, params={
            "q": query.keyword, "limit": self._limit, "sort": "top_seller", "page": 1,
        })
        return parse_listing(resp.json(), query, datetime.now(UTC))
