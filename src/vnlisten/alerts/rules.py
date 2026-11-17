"""Luật cảnh báo. Thêm luật mới = thêm 1 class implement AlertRule (OCP)."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from ..domain.models import Alert, Mention, Sentiment, Severity

NameResolver = Callable[[str], str]


class CrisisKeywordRule:
    """Brand xuất hiện cùng từ khoá rủi ro (sữa giả, thu hồi, ngộ độc...) trong cửa sổ gần nhất.

    Chỉ báo khi đủ "độ lớn" (số bài HOẶC tổng tương tác) để tránh spam vì 1 comment lẻ.
    """

    name = "crisis_keyword"

    def __init__(self, brand_name: NameResolver, window: timedelta = timedelta(hours=24),
                 min_mentions: int = 3, min_interactions: int = 300,
                 high_mentions: int = 8, high_interactions: int = 1500):
        self._brand_name = brand_name
        self._window = window
        self._min = (min_mentions, min_interactions)
        self._high = (high_mentions, high_interactions)

    def evaluate(self, mentions: Sequence[Mention], now: datetime) -> list[Alert]:
        groups: dict[str, list[Mention]] = defaultdict(list)
        for m in mentions:
            if m.published_at >= now - self._window and m.risk_terms:
                for brand in m.brands:
                    groups[brand].append(m)

        alerts = []
        for brand, items in groups.items():
            count = len(items)
            reach = sum(i.engagement.interactions for i in items)
            if count < self._min[0] and reach < self._min[1]:
                continue
            terms = Counter(t for i in items for t in i.risk_terms).most_common(4)
            top = max(items, key=lambda i: i.engagement.interactions)
            high = count >= self._high[0] or reach >= self._high[1]
            alerts.append(Alert(
                rule=self.name,
                severity=Severity.HIGH if high else Severity.MEDIUM,
                title=f"[{self._brand_name(brand)}] {count} posts with risk keywords in 24h ({reach:,} interactions)",
                detail=(f"Keywords: {', '.join(f'{t} ({n})' for t, n in terms)}\n"
                        f"Top post: {top.title or top.content[:120]}\n{top.url}"),
                key=f"{self.name}:{brand}:{now:%Y-%m-%d}",
                created_at=now,
            ))
        return alerts


class NegativeSpikeRule:
    """Số mention tiêu cực 24h qua tăng đột biến so với trung bình/ngày của N ngày trước đó."""

    name = "negative_spike"

    def __init__(self, brand_name: NameResolver, baseline_days: int = 7, ratio: float = 2.0, min_count: int = 5):
        self._brand_name = brand_name
        self._baseline_days = baseline_days
        self._ratio = ratio
        self._min = min_count

    def evaluate(self, mentions: Sequence[Mention], now: datetime) -> list[Alert]:
        day_ago = now - timedelta(days=1)
        base_start = day_ago - timedelta(days=self._baseline_days)
        current: Counter[str] = Counter()
        baseline: Counter[str] = Counter()
        for m in mentions:
            if m.sentiment is not Sentiment.NEGATIVE:
                continue
            bucket = current if m.published_at > day_ago else baseline if m.published_at > base_start else None
            if bucket is not None:
                bucket.update(m.brands)

        alerts = []
        for brand, count in current.items():
            avg = baseline[brand] / self._baseline_days
            if count >= self._min and count >= self._ratio * max(avg, 1.0):
                alerts.append(Alert(
                    rule=self.name,
                    severity=Severity.HIGH if count >= 3 * max(avg, 1.0) else Severity.MEDIUM,
                    title=f"[{self._brand_name(brand)}] Negative spike: {count} posts in 24h (avg {avg:.1f}/day)",
                    detail="Check the negative feed on the dashboard to find the source.",
                    key=f"{self.name}:{brand}:{now:%Y-%m-%d}",
                    created_at=now,
                ))
        return alerts
