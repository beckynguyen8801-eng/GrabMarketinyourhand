"""Ports (interfaces) – các tầng trên chỉ phụ thuộc vào đây (DIP).

Interface được tách nhỏ (ISP): connector mạng xã hội và connector sàn TMĐT
là 2 hợp đồng khác nhau, repository cũng tách theo từng nhu cầu đọc/ghi.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from .models import Alert, KeywordSuggestion, Mention, ProductSnapshot, SourceType, TrackingQuery


@runtime_checkable
class MentionSource(Protocol):
    """Nguồn trả về bài viết/video/comment theo từ khoá."""

    source: SourceType

    def fetch(self, query: TrackingQuery, since: datetime) -> list[Mention]: ...


@runtime_checkable
class MarketplaceSource(Protocol):
    """Nguồn trả về danh sách sản phẩm trên sàn (để ranking theo lượt bán)."""

    source: SourceType

    def fetch_products(self, query: TrackingQuery) -> list[ProductSnapshot]: ...


@runtime_checkable
class KeywordSource(Protocol):
    """Nguồn gợi ý từ khoá (Google Autocomplete, sau này: Keyword Planner...)."""

    def suggest(self, seed: str, industry: str) -> list[KeywordSuggestion]: ...


class Enricher(Protocol):
    """1 bước xử lý trong pipeline: match brand, sentiment, topic..."""

    def enrich(self, mention: Mention) -> Mention: ...


class MentionRepository(Protocol):
    def save_mentions(self, mentions: Sequence[Mention]) -> int: ...

    def load_mentions(self, since: datetime, until: datetime | None = None,
                      industry: str | None = None) -> list[Mention]: ...


class SnapshotRepository(Protocol):
    def save_snapshots(self, snapshots: Sequence[ProductSnapshot]) -> int: ...

    def latest_snapshots(self, industry: str | None = None) -> list[ProductSnapshot]: ...


class AlertRepository(Protocol):
    def alert_exists(self, key: str) -> bool: ...

    def save_alert(self, alert: Alert) -> None: ...

    def recent_alerts(self, limit: int = 50, industry: str | None = None) -> list[Alert]: ...


class InsightRepository(Protocol):
    def save_insight(self, text: str, created_at: datetime, industry: str = "") -> None: ...

    def latest_insight(self, industry: str | None = None) -> tuple[datetime, str] | None: ...


class KeywordRepository(Protocol):
    def save_suggestions(self, suggestions: Sequence[KeywordSuggestion]) -> int: ...

    def suggestion_history(self, industry: str) -> list[KeywordSuggestion]: ...


class WatchlistRepository(Protocol):
    def add_watch(self, industry: str, keyword: str) -> None: ...

    def remove_watch(self, industry: str, keyword: str) -> None: ...

    def watchlist(self, industry: str | None = None) -> list[tuple[str, str]]: ...


class AlertRule(Protocol):
    name: str

    def evaluate(self, mentions: Sequence[Mention], now: datetime) -> list[Alert]: ...


class Notifier(Protocol):
    def send(self, alert: Alert) -> None: ...
