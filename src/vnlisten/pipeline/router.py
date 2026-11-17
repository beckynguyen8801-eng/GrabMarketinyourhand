"""Định tuyến mention về đúng ngành để dùng đúng taxonomy + từ điển của ngành đó."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..domain.models import Mention
from ..domain.ports import Enricher
from ..taxonomy import IndustryRegistry
from .activity import ActivityClassifier
from .community import CommunityResolver
from .entity_matcher import EntityMatcher
from .sentiment import LexiconSentimentAnalyzer


class IndustryRouter:
    """Enricher tổng hợp.

    - Mention đã biết ngành (từ query / CSV import) -> chạy chuỗi enricher của ngành đó.
    - Chưa biết ngành -> thử match brand/product của TẤT CẢ ngành, chọn ngành khớp nhiều nhất.
    """

    def __init__(self, matchers: Mapping[str, EntityMatcher], chains: Mapping[str, Sequence[Enricher]]):
        self._matchers = matchers
        self._chains = chains

    def enrich(self, mention: Mention) -> Mention:
        if mention.industry not in self._chains:
            mention.industry = self._detect(mention)
        if not mention.industry:
            return mention
        for enricher in self._chains[mention.industry]:
            mention = enricher.enrich(mention)
        return mention

    def _detect(self, mention: Mention) -> str:
        best, best_score = "", 0
        for industry, matcher in self._matchers.items():
            probe = matcher.enrich(_copy(mention))
            score = 2 * len(probe.products) + len(probe.brands)
            if score > best_score:
                best, best_score = industry, score
        return best


def _copy(m: Mention) -> Mention:
    return Mention(source=m.source, external_id=m.external_id, url=m.url, title=m.title, content=m.content,
                   published_at=m.published_at)


def build_router(registry: IndustryRegistry) -> IndustryRouter:
    matchers = {t.industry: EntityMatcher(t) for t in registry.all()}
    chains = {
        t.industry: [
            matchers[t.industry],
            LexiconSentimentAnalyzer(t.positive_terms, t.negative_terms),
            ActivityClassifier(t.activity_terms),
            CommunityResolver(),
        ]
        for t in registry.all()
    }
    return IndustryRouter(matchers, chains)
