from __future__ import annotations

from collections.abc import Iterable, Sequence

from ..domain.models import Mention
from ..domain.ports import Enricher


class EnrichmentPipeline:
    """Chạy lần lượt các Enricher. Thêm bước mới (topic, spam filter...) = thêm 1 class."""

    def __init__(self, enrichers: Sequence[Enricher], keep_unmatched: bool = False):
        self._enrichers = list(enrichers)
        self._keep_unmatched = keep_unmatched

    def run(self, mentions: Iterable[Mention]) -> list[Mention]:
        result: list[Mention] = []
        seen: set[str] = set()
        for mention in mentions:
            if mention.uid in seen:
                continue
            seen.add(mention.uid)
            for enricher in self._enrichers:
                mention = enricher.enrich(mention)
            # Bỏ các bài không nhắc brand & không có risk term & không có category => nhiễu
            if self._keep_unmatched or mention.brands or mention.risk_terms or mention.category:
                result.append(mention)
        return result
