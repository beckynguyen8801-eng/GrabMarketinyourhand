from __future__ import annotations

from collections.abc import Iterable, Sequence

from ..domain.models import Mention
from ..domain.ports import Enricher
from .relevance import is_relevant


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
            # Chỉ giữ bài tiếng Việt & thật sự liên quan (xem relevance.py)
            if self._keep_unmatched or is_relevant(mention):
                result.append(mention)
        return result
