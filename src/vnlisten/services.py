"""Application services – điều phối use-case, chỉ phụ thuộc vào ports (DIP)."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .analytics import metrics, research
from .domain.models import Alert, Mention, TrackingQuery
from .domain.ports import (
    AlertRepository, AlertRule, InsightRepository, KeywordRepository, KeywordSource, MarketplaceSource,
    MentionRepository, MentionSource, Notifier, SnapshotRepository,
)
from .insights.generators import InsightContext, InsightGenerator
from .pipeline.activity import activity_name
from .pipeline.pipeline import EnrichmentPipeline
from .taxonomy import IndustryRegistry

log = logging.getLogger(__name__)


@dataclass
class CollectStats:
    fetched: int = 0
    kept: int = 0
    new: int = 0
    errors: list[str] = field(default_factory=list)


class CollectionService:
    def __init__(self, pipeline: EnrichmentPipeline, repo: MentionRepository):
        self._pipeline = pipeline
        self._repo = repo

    def collect(self, sources: Sequence[MentionSource], queries: Sequence[TrackingQuery],
                since: datetime) -> CollectStats:
        stats = CollectStats()
        for source in sources:
            for query in queries:
                try:
                    raw = source.fetch(query, since)
                except Exception as exc:  # 1 nguồn lỗi không được làm sập cả job
                    msg = f"{source.source}:{query.keyword}: {exc}"
                    log.warning("Collect lỗi %s", msg)
                    stats.errors.append(msg)
                    continue
                enriched = self._pipeline.run(raw)
                stats.fetched += len(raw)
                stats.kept += len(enriched)
                stats.new += self._repo.save_mentions(enriched)
        return stats

    def ingest(self, mentions: Sequence[Mention]) -> CollectStats:
        """Đưa mention có sẵn (VD: import CSV) qua pipeline rồi lưu."""
        enriched = self._pipeline.run(mentions)
        return CollectStats(fetched=len(mentions), kept=len(enriched), new=self._repo.save_mentions(enriched))


class MarketplaceService:
    def __init__(self, sources: Sequence[MarketplaceSource], repo: SnapshotRepository):
        self._sources = sources
        self._repo = repo

    def refresh(self, queries: Sequence[TrackingQuery]) -> int:
        total = 0
        for source in self._sources:
            for query in queries:
                try:
                    total += self._repo.save_snapshots(source.fetch_products(query))
                except Exception as exc:
                    log.warning("Marketplace %s '%s' lỗi: %s", source.source, query.keyword, exc)
        return total


class KeywordResearchService:
    def __init__(self, source: KeywordSource, repo: KeywordRepository):
        self._source = source
        self._repo = repo

    def refresh(self, industry: str, seeds: Sequence[str]) -> int:
        total = 0
        for seed in seeds:
            try:
                total += self._repo.save_suggestions(self._source.suggest(seed, industry))
            except Exception as exc:
                log.warning("Keyword suggest '%s' lỗi: %s", seed, exc)
        return total


class AlertService:
    """Đánh giá luật cảnh báo RIÊNG cho từng ngành (brand id chỉ có nghĩa trong ngành của nó)."""

    def __init__(self, rules_by_industry: Mapping[str, Sequence[AlertRule]], notifiers: Sequence[Notifier],
                 mentions: MentionRepository, alerts: AlertRepository, lookback_days: int = 8):
        self._rules = rules_by_industry
        self._notifiers = notifiers
        self._mentions = mentions
        self._alerts = alerts
        self._lookback = timedelta(days=lookback_days)

    def run(self, now: datetime | None = None) -> list[Alert]:
        now = now or datetime.now(UTC)
        fired = []
        for industry, rules in self._rules.items():
            data = self._mentions.load_mentions(now - self._lookback, now, industry)
            for rule in rules:
                for alert in rule.evaluate(data, now):
                    alert.industry = industry
                    alert.key = f"{industry}:{alert.key}"
                    if self._alerts.alert_exists(alert.key):
                        continue
                    self._alerts.save_alert(alert)
                    for notifier in self._notifiers:
                        notifier.send(alert)
                    fired.append(alert)
        return fired


class InsightService:
    def __init__(self, generator: InsightGenerator, registry: IndustryRegistry,
                 mentions: MentionRepository, alerts: AlertRepository, insights: InsightRepository):
        self._generator = generator
        self._registry = registry
        self._mentions = mentions
        self._alerts = alerts
        self._insights = insights

    def build_context(self, industry: str, now: datetime, days: int = 7) -> InsightContext:
        tax = self._registry.get(industry)
        window = timedelta(days=days)
        df = metrics.to_frame(self._mentions.load_mentions(now - 2 * window, now, industry))
        current = df[df["published_at"] > now - window] if not df.empty else df
        name = tax.brand_name

        brand = metrics.entity_metrics(current, "brands")
        growth = metrics.buzz_growth(df, now, window)
        risers = growth[(growth["previous"] >= 3) & (growth["growth"] > 0.3)].sort_values("growth", ascending=False)
        hotspots = brand[(brand["negative"] >= 3) & (brand["nsr"] < 0)].sort_values("nsr")
        pos = int((current["sentiment"] == "positive").sum()) if not current.empty else 0
        neg = int((current["sentiment"] == "negative").sum()) if not current.empty else 0
        activities = research.activity_summary(current)
        total_act = int(activities["mentions"].sum())
        offline_act = int(activities.loc[activities["channel"] == "offline", "mentions"].sum())
        hashtags = research.top_hashtags(current, 5)
        trends = research.trending_phrases(df, now, window, limit=5)

        return InsightContext(
            industry_name=tax.name,
            period_label=f"last {days} days",
            total_mentions=len(current),
            total_interactions=int(current["interactions"].sum()) if not current.empty else 0,
            overall_nsr=(pos - neg) / (pos + neg) if pos + neg else 0.0,
            top_brands=[{"entity": name(r.entity), "mentions": int(r.mentions), "sov": float(r.sov), "nsr": float(r.nsr)}
                        for r in brand.head(5).itertuples()],
            risers=[{"entity": name(r.entity), "current": int(r.current), "previous": int(r.previous),
                     "growth": float(r.growth)} for r in risers.head(5).itertuples()],
            negative_hotspots=[{"entity": name(r.entity), "negative": int(r.negative), "nsr": float(r.nsr)}
                               for r in hotspots.head(5).itertuples()],
            risk_terms=metrics.risk_term_counts(current).head(8).to_dict("records"),
            alerts=[a.title for a in self._alerts.recent_alerts(10, industry) if a.created_at > now - window],
            top_activities=[{"activity": activity_name(r.activity), "mentions": int(r.mentions),
                             "channel": r.channel} for r in activities.head(4).itertuples()],
            offline_share=offline_act / total_act if total_act else None,
            top_hashtags=[{"hashtag": r.hashtag, "brand": name(r.brand), "interactions": int(r.interactions)}
                          for r in hashtags.itertuples()],
            trending_phrases=trends["phrase"].tolist(),
        )

    def run(self, industry: str, now: datetime | None = None, days: int = 7) -> str:
        now = now or datetime.now(UTC)
        text = self._generator.generate(self.build_context(industry, now, days))
        self._insights.save_insight(text, now, industry)
        return text

    def run_all(self, now: datetime | None = None) -> None:
        for industry in self._registry.ids():
            self.run(industry, now)
