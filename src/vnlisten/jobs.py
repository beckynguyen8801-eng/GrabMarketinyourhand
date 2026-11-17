"""Các job theo tier + scheduler. Tách khỏi CLI để dễ gọi từ chỗ khác (cron, test...)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from pathlib import Path

import yaml

from .container import App
from .domain.models import Tier, TrackingQuery

log = logging.getLogger(__name__)

LOOKBACK = {Tier.HOURLY: timedelta(hours=6), Tier.DAILY: timedelta(days=3)}


def watchlist_file(path: Path) -> list[tuple[str, str]]:
    """config/watchlist.yaml – watchlist sửa được trên GitHub (chế độ cloud, dashboard chỉ đọc)."""
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [(ind, str(kw).strip()) for ind, kws in raw.items() for kw in (kws or []) if str(kw).strip()]


def all_watch_keywords(app: App) -> list[tuple[str, str]]:
    pairs = app.repo.watchlist() + watchlist_file(app.settings.industries_dir.parent / "watchlist.yaml")
    return [p for p in dict.fromkeys(pairs) if p[0] in app.registry]


def _queries(app: App, tier: Tier) -> list[TrackingQuery]:
    queries = [q for tax in app.registry.all() for q in tax.tracking_queries(tier)]
    if tier is Tier.DAILY:  # từ khoá bấm "Track" trên dashboard + config/watchlist.yaml
        queries += [TrackingQuery(kw, industry=ind) for ind, kw in all_watch_keywords(app)]
    return queries


def run_hourly(app: App) -> None:
    stats = app.collection.collect(
        app.sources_by_tier[Tier.HOURLY], _queries(app, Tier.HOURLY), datetime.now(UTC) - LOOKBACK[Tier.HOURLY],
    )
    alerts = app.alerts.run()
    log.info("[hourly] fetched=%d kept=%d new=%d errors=%d alerts=%d",
             stats.fetched, stats.kept, stats.new, len(stats.errors), len(alerts))


def run_daily(app: App) -> None:
    stats = app.collection.collect(
        app.sources_by_tier[Tier.DAILY], _queries(app, Tier.DAILY), datetime.now(UTC) - LOOKBACK[Tier.DAILY],
    )
    market_queries = [
        TrackingQuery(k, c.id, industry=tax.industry)
        for tax in app.registry.all() for c in tax.categories.values() for k in c.keywords[:2]
    ]
    snapshots = app.marketplace.refresh(market_queries)
    if app.web_search:  # site:facebook.com/groups ... – chỉ từ khoá ngành con + watchlist để tiết kiệm quota
        web_queries = [TrackingQuery(k, c.id, industry=t.industry)
                       for t in app.registry.all() for c in t.categories.values() for k in c.keywords]
        web_queries += [TrackingQuery(kw, industry=ind) for ind, kw in all_watch_keywords(app)]
        web = app.collection.collect([app.web_search], web_queries, datetime.now(UTC) - LOOKBACK[Tier.DAILY])
        log.info("[daily] web search: fetched=%d new=%d errors=%d", web.fetched, web.new, len(web.errors))
    suggestions = sum(app.keywords.refresh(t.industry, t.research_seeds) for t in app.registry.all())
    alerts = app.alerts.run()
    app.insights.run_all()
    log.info("[daily] fetched=%d kept=%d new=%d errors=%d snapshots=%d suggestions=%d alerts=%d",
             stats.fetched, stats.kept, stats.new, len(stats.errors), snapshots, suggestions, len(alerts))


def start_scheduler(app: App) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler  # noqa: PLC0415

    scheduler = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(run_hourly, "cron", minute=7, args=[app], id="hourly", max_instances=1, coalesce=True)
    scheduler.add_job(run_daily, "cron", hour=6, minute=23, args=[app], id="daily", max_instances=1, coalesce=True)
    log.info("Scheduler running: hourly at :07, daily at 06:23 (Asia/Ho_Chi_Minh). Ctrl+C to stop.")
    scheduler.start()
