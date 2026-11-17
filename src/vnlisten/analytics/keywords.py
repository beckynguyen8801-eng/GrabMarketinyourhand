"""Search tự do + tổng hợp keyword quanh 1 sản phẩm / brand.

- search(): người dùng gõ BẤT KỲ từ nào ("sữa công thức", "enfa a2", "bv bạch mai", "táo bón")
  -> lọc mention khớp nội dung (không phân biệt dấu) HOẶC nhắc tới brand/sản phẩm có alias khớp.
- entity_keywords(): chọn 1 sản phẩm (VD Enfamil A+) -> toàn bộ cụm từ người dùng nói kèm sản phẩm đó,
  có số bài, tỷ trọng, sắc thái, tương tác và 1 câu ví dụ.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from ..pipeline.sentiment import NEGATIVE_TERMS, POSITIVE_TERMS
from ..pipeline.text import is_negated_no_accent, normalize_for_match, normalize_keep_accents
from ..taxonomy import Taxonomy
from .phrases import STOPWORDS, phrases

# Âm tiết chung trong tên entity – không phải tên riêng ("bệnh viện", "nhà thuốc", "sữa"...)
GENERIC_TOKENS = {"benh", "vien", "bv", "nha", "thuoc", "sua", "bim", "ta", "binh", "kham", "phong"}
KEYWORD_COLUMNS = ["keyword", "type", "mentions", "share", "positive", "negative", "nsr", "interactions", "example"]


def matching_entities(tax: Taxonomy, query: str) -> tuple[set[str], set[str]]:
    """Brand / product mà query nhắc tới (query chứa alias, hoặc alias/tên chứa query)."""
    q = normalize_for_match(query)
    if not q:
        return set(), set()

    def hit(names: tuple[str, ...]) -> bool:
        for name in names:
            n = normalize_for_match(name)
            if n and (n == q or f" {n} " in f" {q} " or (len(q) >= 4 and f" {q} " in f" {n} ")):
                return True
        return False

    brands = {b.id for b in tax.brands.values() if hit((*b.aliases, b.name))}
    products = {p.id for p in tax.products.values() if hit((*p.aliases, p.name))}
    return brands, products


def search(df: pd.DataFrame, query: str, tax: Taxonomy | None = None) -> pd.DataFrame:
    q = normalize_for_match(query or "")
    if df.empty or not q:
        return df
    text = (df["title"].fillna("") + " " + df["content"].fillna("")).map(normalize_for_match)
    pattern = re.compile(rf"(?<![0-9a-z]){re.escape(q)}(?![0-9a-z])")
    mask = text.map(lambda t: bool(pattern.search(t)))
    if tax is not None:
        brands, products = matching_entities(tax, query)
        if brands or products:
            mask |= df["brands"].map(lambda bs: bool(brands & set(bs)))
            mask |= df["products"].map(lambda ps: bool(products & set(ps)))
    return df[mask]


def _entity_token_set(tax: Taxonomy, brand_id: str | None, product_id: str | None) -> set[str]:
    names: list[str] = []
    if brand_id and brand_id in tax.brands:
        b = tax.brands[brand_id]
        names += [*b.aliases, b.name]
    if product_id and product_id in tax.products:
        p = tax.products[product_id]
        names += [*p.aliases, p.name]
    return {tok for n in names for tok in normalize_for_match(n).split()} - GENERIC_TOKENS


def entity_keywords(df: pd.DataFrame, tax: Taxonomy, *, product_id: str | None = None,
                    brand_id: str | None = None, min_count: int = 2, limit: int = 40) -> pd.DataFrame:
    """Keyword người dùng nhắc kèm 1 sản phẩm (ưu tiên) hoặc 1 brand. 2 tầng:

    - Known      : khớp từ điển khía cạnh/sentiment/rủi ro/hoạt động của ngành -> chính xác cao.
    - Discovered : cụm 2 âm tiết lặp lại, không chứa stopword / tên brand -> phát hiện chủ đề mới.
      (Tiếng Việt viết cách theo âm tiết nên n-gram dễ cắt ngang từ; tầng này cần người đọc lọc thêm.)
    """
    if df.empty or not (product_id or brand_id):
        return pd.DataFrame(columns=KEYWORD_COLUMNS)
    if product_id:
        subset = df[df["products"].map(lambda ps: product_id in ps)]
        brand_id = brand_id or (tax.products[product_id].brand if product_id in tax.products else None)
    else:
        subset = df[df["brands"].map(lambda bs: brand_id in bs)]
    return keywords_in(subset, tax, brand_id=brand_id, product_id=product_id, min_count=min_count, limit=limit)


@dataclass(frozen=True)
class KeywordLookup:
    """Kết quả ô gõ tự do: đã khớp được entity nào (nếu có) + bảng keyword."""

    brand_id: str | None
    product_id: str | None
    mode: str  # "product" | "brand" | "text"
    posts: int
    table: pd.DataFrame


def free_text_keywords(df: pd.DataFrame, tax: Taxonomy, brand_text: str = "", product_text: str = "",
                       **kwargs) -> KeywordLookup:
    """Người dùng gõ tự do vào 2 ô Brand / Product (VD "enfa" + "enfa a2").

    1. Khớp được sản phẩm  -> keyword của đúng sản phẩm đó.
    2. Chỉ khớp được brand -> keyword toàn brand.
    3. Không khớp entity   -> tìm theo nội dung bài viết (search), rồi trích keyword trên các bài đó.
    """
    brands, _ = matching_entities(tax, brand_text)
    _, products = matching_entities(tax, product_text)
    if brands and products:
        products = {p for p in products if tax.products[p].brand in brands} or products
    if products:
        pid = min(products, key=lambda p: len(tax.products[p].name))
        subset = df[df["products"].map(lambda ps: pid in ps)] if not df.empty else df
        return KeywordLookup(tax.products[pid].brand, pid, "product", len(subset),
                             keywords_in(subset, tax, product_id=pid, brand_id=tax.products[pid].brand, **kwargs))
    if brands and not product_text.strip():
        bid = min(brands, key=lambda b: len(tax.brand_name(b)))
        subset = df[df["brands"].map(lambda bs: bid in bs)] if not df.empty else df
        return KeywordLookup(bid, None, "brand", len(subset), keywords_in(subset, tax, brand_id=bid, **kwargs))
    subset = search(search(df, brand_text, tax), product_text, tax)
    bid = min(brands, key=lambda b: len(tax.brand_name(b))) if brands else None
    return KeywordLookup(bid, None, "text", len(subset), keywords_in(subset, tax, brand_id=bid, **kwargs))


def keywords_in(subset: pd.DataFrame, tax: Taxonomy, *, brand_id: str | None = None,
                product_id: str | None = None, min_count: int = 2, limit: int = 40) -> pd.DataFrame:
    """Trích keyword 2 tầng (Known / Discovered) trên 1 tập bài bất kỳ."""
    if subset.empty:
        return pd.DataFrame(columns=KEYWORD_COLUMNS)

    # Từ điển chung chỉ lấy cụm >= 2 âm tiết ("tốt", "mê" quá mơ hồ để làm keyword)
    terms = (*tax.keyword_lexicon(), *(t for t in (*POSITIVE_TERMS, *NEGATIVE_TERMS) if " " in t))
    terms = sorted(dict.fromkeys(terms), key=len, reverse=True)
    # Cụm nhiều âm tiết: khớp KHÔNG dấu (người dùng hay gõ không dấu).
    lexicon = [(t, re.compile(rf"(?<![0-9a-z]){re.escape(normalize_for_match(t))}(?![0-9a-z])"))
               for t in terms if " " in normalize_for_match(t)]
    # Từ 1 âm tiết: khớp ĐÚNG DẤU – bỏ dấu thì "mê"="mẹ", "đắt"="đặt", "ưng"="ung".
    single = [(t, re.compile(rf"(?<!\w){re.escape(t.lower())}(?!\w)"))
              for t in terms if normalize_for_match(t) and " " not in normalize_for_match(t)]
    lexicon_norm = {normalize_for_match(t) for t, _ in lexicon}
    entity_tokens = _entity_token_set(tax, brand_id, product_id)

    stats: dict[tuple[str, str], dict] = defaultdict(lambda: {"mentions": 0, "positive": 0, "negative": 0,
                                                              "interactions": 0, "example": "", "best": -1})
    for row in subset.itertuples():
        raw_text = f"{row.title} {row.content}"
        norm = normalize_for_match(raw_text)
        found: set[tuple[str, str]] = set()
        taken: list[tuple[int, int]] = []
        known_tokens: set[str] = set()
        for term, pattern in lexicon:  # dài trước: "không phải chờ" thắng "chờ lâu"
            for m in pattern.finditer(norm):
                start, end = m.span()
                if any(start < e0 and s0 < end for s0, e0 in taken):
                    continue  # chồng lấn cụm đã nhận
                taken.append((start, end))
                if is_negated_no_accent(norm, start) and not norm[start:end].startswith(("khong", "ko ")):
                    continue  # "không bị táo bón" không phải keyword "táo bón"
                found.add((term, "Known"))
                known_tokens |= set(norm[start:end].split())
                break
        accented = normalize_keep_accents(raw_text)
        for term, pattern in single:
            if normalize_for_match(term) not in known_tokens and pattern.search(accented):
                found.add((term, "Known"))
        for gram in phrases(raw_text, 2):
            tokens = gram.split()
            g_tokens = set(normalize_for_match(gram).split())
            if (any(t in STOPWORDS for t in tokens) or g_tokens & entity_tokens or g_tokens & known_tokens
                    or g_tokens <= GENERIC_TOKENS or normalize_for_match(gram) in lexicon_norm):
                continue  # bỏ mảnh của tên brand / của keyword Known ("cân đều" từ "tăng cân đều")
            found.add((gram, "Discovered"))
        for key in found:
            st = stats[key]
            st["mentions"] += 1
            st["positive"] += row.sentiment == "positive"
            st["negative"] += row.sentiment == "negative"
            st["interactions"] += int(row.interactions)
            if row.interactions > st["best"]:
                st["best"], st["example"] = row.interactions, row.content[:160]

    rows = []
    for (kw, kind), st in stats.items():
        if st["mentions"] < (1 if kind == "Known" else max(min_count, 3)):
            continue
        polar = st["positive"] + st["negative"]
        rows.append({
            "keyword": kw, "type": kind, "mentions": st["mentions"], "share": st["mentions"] / len(subset),
            "positive": st["positive"], "negative": st["negative"],
            "nsr": (st["positive"] - st["negative"]) / polar if polar else 0.0,
            "interactions": st["interactions"], "example": st["example"],
        })
    out = pd.DataFrame(rows, columns=KEYWORD_COLUMNS)
    if out.empty:
        return out
    out["_order"] = (out["type"] == "Discovered").astype(int)
    out = out.sort_values(["_order", "mentions", "interactions"], ascending=[True, False, False], ignore_index=True)
    return out.drop(columns="_order").head(limit)
