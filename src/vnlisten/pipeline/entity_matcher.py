"""Gắn brand / product / risk term vào mention dựa trên alias trong taxonomy."""
from __future__ import annotations

import re
from collections.abc import Iterable

from ..domain.models import Mention
from ..taxonomy import Taxonomy
from .text import is_negated_no_accent, normalize_for_match


class _AliasIndex:
    """Map nhiều alias -> 1 id, so khớp theo ranh giới từ trên text đã bỏ dấu."""

    def __init__(self, entries: Iterable[tuple[str, str]], longest_only: bool = False,
                 skip_negated: bool = False):
        """longest_only : 'bóc phốt' đã khớp thì không tính thêm 'phốt' nằm bên trong.
        skip_negated : 'bé KHÔNG bị táo bón' thì không tính là risk term.
        """
        self._longest_only = longest_only
        self._skip_negated = skip_negated
        normalized = {(normalize_for_match(alias), target) for alias, target in entries}
        self._patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(rf"(?<![0-9a-z]){re.escape(norm)}(?![0-9a-z])"), target)
            for norm, target in sorted(normalized, key=lambda x: len(x[0]), reverse=True)
            if norm
        ]

    def find(self, normalized_text: str) -> list[str]:
        """Trả về các target theo THỨ TỰ XUẤT HIỆN trong câu (thứ được nhắc trước đứng trước)."""
        found: dict[str, int] = {}
        taken: list[tuple[int, int]] = []
        for pattern, target in self._patterns:  # alias dài duyệt trước
            for match in pattern.finditer(normalized_text):
                start, end = match.span()
                if self._longest_only and any(s <= start and end <= e for s, e in taken):
                    continue
                if self._skip_negated and is_negated_no_accent(normalized_text, start):
                    continue
                taken.append((start, end))
                found[target] = min(start, found.get(target, start))
        return sorted(found, key=found.__getitem__)


class EntityMatcher:
    def __init__(self, taxonomy: Taxonomy):
        self._taxonomy = taxonomy
        # Có khai báo alias thì CHỈ dùng alias (tên hiển thị như "An Khang" có thể trùng từ thông dụng);
        # không khai báo thì mới dùng tên làm alias.
        # longest_only: "bệnh viện đại học y dược huế" chỉ là BV Huế, không tính thêm UMC TP.HCM
        self._products = _AliasIndex(
            ((alias, p.id) for p in taxonomy.products.values() for alias in (p.aliases or (p.name,))),
            longest_only=True,
        )
        self._brands = _AliasIndex(
            ((alias, b.id) for b in taxonomy.brands.values() for alias in (b.aliases or (b.name,))),
            longest_only=True,
        )
        # Chủ đề: bỏ từ 1 âm tiết có dấu ("mát") – bỏ dấu dễ trùng nghĩa khác ("mắt", "mất")
        self._topics = _AliasIndex(
            ((alias, canonical) for alias, canonical in taxonomy.topic_aliases().items()
             if " " in alias.strip() or normalize_for_match(alias) == alias.strip().lower()),
            longest_only=True,
        )
        self._risks = _AliasIndex(((term, term) for term in taxonomy.risk_terms),
                                  longest_only=True, skip_negated=True)

    def enrich(self, mention: Mention) -> Mention:
        text = normalize_for_match(mention.text)

        products = self._products.find(text)
        brands = self._brands.find(text)
        for pid in products:  # nhắc "Similac" => ngầm nhắc Abbott
            brand = self._taxonomy.products[pid].brand
            if brand not in brands:
                brands.append(brand)

        mention.products = products
        mention.brands = brands
        mention.risk_terms = self._risks.find(text)
        mention.topics = self._topics.find(text)
        if not mention.category and products:
            mention.category = self._taxonomy.products[products[0]].category
        if not mention.category and brands:
            mention.category = self._taxonomy.category_of_brand(brands[0])
        return mention
