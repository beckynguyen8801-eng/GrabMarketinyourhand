"""Taxonomy ngành hàng: category -> brand -> product (+ alias). Mỗi ngành = 1 file YAML.

Thêm ngành mới = thêm 1 file vào config/industries/, KHÔNG sửa code (OCP).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .domain.models import Tier, TrackingQuery


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Brand:
    id: str
    name: str
    aliases: tuple[str, ...]
    # Category khai báo trực tiếp – bắt buộc với entity không có "sản phẩm" (bệnh viện, phòng khám...)
    category: str = ""
    # Thông tin mô tả hiển thị trên dashboard: country, city, type, specialty...
    meta: tuple[tuple[str, str], ...] = ()

    @property
    def info(self) -> dict[str, str]:
        return dict(self.meta)


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    brand: str
    category: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Taxonomy:
    industry: str
    name: str
    categories: dict[str, Category]
    brands: dict[str, Brand]
    products: dict[str, Product]
    risk_terms: tuple[str, ...]
    hourly_keywords: tuple[str, ...]
    # Từ vựng sentiment đặc thù ngành, cộng thêm vào từ điển chung
    positive_terms: tuple[str, ...] = ()
    negative_terms: tuple[str, ...] = ()
    # Từ khoá nhận diện hoạt động MKT đặc thù ngành, cộng thêm vào bộ chung
    activity_terms: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Seed cho keyword research (Google Autocomplete)
    research_seeds: tuple[str, ...] = ()
    # Khía cạnh hay được nhắc kèm sản phẩm (giá, chất lượng, chờ lâu...)
    aspects: tuple[str, ...] = ()
    # Chủ đề ngành + cách viết khác: {"sữa công thức": ("sct", ...)} – gộp về 1 keyword, đủ để giữ bài
    topic_terms: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def topic_aliases(self) -> dict[str, str]:
        """Cách viết (kể cả tên chuẩn) -> tên chuẩn."""
        out: dict[str, str] = {}
        for canonical, variants in self.topic_terms.items():
            for v in (canonical, *variants):
                out.setdefault(v, canonical)
        return out

    def keyword_lexicon(self) -> tuple[str, ...]:
        """Toàn bộ từ khoá 'đã biết' của ngành: khía cạnh + sentiment + rủi ro + hoạt động + từ khoá ngành con."""
        terms = [*self.topic_aliases(), *self.aspects, *self.positive_terms, *self.negative_terms, *self.risk_terms]
        terms += [t for ts in self.activity_terms.values() for t in ts]
        terms += [k for c in self.categories.values() for k in c.keywords]
        return tuple(dict.fromkeys(terms))

    def brand_name(self, brand_id: str) -> str:
        brand = self.brands.get(brand_id)
        return brand.name if brand else brand_id

    def products_of_brand(self, brand_id: str) -> list[Product]:
        return [p for p in self.products.values() if p.brand == brand_id]

    def brands_in_category(self, category_id: str) -> list[str]:
        return [b for b in self.brands if self.category_of_brand(b) == category_id]

    def product_name(self, product_id: str) -> str:
        product = self.products.get(product_id)
        return product.name if product else product_id

    def category_name(self, category_id: str) -> str:
        cat = self.categories.get(category_id)
        return cat.name if cat else category_id

    def category_of_brand(self, brand_id: str) -> str:
        brand = self.brands.get(brand_id)
        if brand and brand.category:
            return brand.category
        for product in self.products.values():
            if product.brand == brand_id:
                return product.category
        return ""

    def tracking_queries(self, tier: Tier) -> list[TrackingQuery]:
        if tier is Tier.HOURLY:
            return [TrackingQuery(k, "", Tier.HOURLY, self.industry) for k in self.hourly_keywords]

        queries: list[TrackingQuery] = []
        for cat in self.categories.values():
            queries += [TrackingQuery(k, cat.id, industry=self.industry) for k in cat.keywords]
        # Tìm bằng alias tiếng Việt đầu tiên (VD "bệnh viện 108"), KHÔNG dùng tên hiển thị tiếng Anh
        # ("Military Central Hospital 108") – tên tiếng Anh kéo về toàn bài nước ngoài.
        for brand_id, brand in self.brands.items():
            term = brand.aliases[0] if brand.aliases else brand.name
            queries.append(TrackingQuery(term, self.category_of_brand(brand_id), industry=self.industry))
        for product in self.products.values():
            term = product.aliases[0] if product.aliases else product.name
            queries.append(TrackingQuery(term, product.category, industry=self.industry))
        return queries


def load_taxonomy(path: str | Path) -> Taxonomy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    categories = {
        cid: Category(cid, c["name"], tuple(c.get("keywords", [])))
        for cid, c in raw.get("categories", {}).items()
    }
    categories_ids = set(categories)
    brands: dict[str, Brand] = {}
    for bid, b in raw.get("brands", {}).items():
        if b.get("category") and b["category"] not in categories_ids:
            raise ValueError(f"[{path}] Brand {bid} trỏ tới category không tồn tại: {b['category']}")
        brands[bid] = Brand(bid, b["name"], tuple(b.get("aliases", [])), b.get("category", ""),
                            tuple((str(k), str(v)) for k, v in (b.get("meta") or {}).items()))
    products: dict[str, Product] = {}
    for p in raw.get("products", []):
        if p["brand"] not in brands:
            raise ValueError(f"[{path}] Product {p['id']} trỏ tới brand không tồn tại: {p['brand']}")
        if p["category"] not in categories:
            raise ValueError(f"[{path}] Product {p['id']} trỏ tới category không tồn tại: {p['category']}")
        products[p["id"]] = Product(p["id"], p["name"], p["brand"], p["category"], tuple(p.get("aliases", [])))

    sentiment = raw.get("sentiment", {}) or {}
    return Taxonomy(
        industry=raw["industry"],
        name=raw.get("name", raw["industry"]),
        categories=categories,
        brands=brands,
        products=products,
        risk_terms=tuple(raw.get("risk_terms", [])),
        hourly_keywords=tuple(raw.get("hourly_keywords", [])),
        positive_terms=tuple(sentiment.get("positive", [])),
        negative_terms=tuple(sentiment.get("negative", [])),
        activity_terms={k: tuple(v) for k, v in (raw.get("activity_terms") or {}).items()},
        research_seeds=tuple(raw.get("research_seeds", [])),
        aspects=tuple(raw.get("aspects", [])),
        topic_terms={str(k): tuple(str(x) for x in (v or [])) for k, v in (raw.get("topic_terms") or {}).items()},
    )


class IndustryRegistry:
    """Tập hợp tất cả ngành hàng đang theo dõi."""

    def __init__(self, taxonomies: list[Taxonomy]):
        if not taxonomies:
            raise ValueError("Chưa có ngành hàng nào trong config/industries/")
        self._items = {t.industry: t for t in taxonomies}

    @classmethod
    def from_dir(cls, directory: str | Path) -> IndustryRegistry:
        return cls([load_taxonomy(p) for p in sorted(Path(directory).glob("*.yaml"))])

    def get(self, industry: str) -> Taxonomy:
        return self._items[industry]

    def all(self) -> list[Taxonomy]:
        return list(self._items.values())

    def ids(self) -> list[str]:
        return list(self._items)

    def __contains__(self, industry: str) -> bool:
        return industry in self._items
