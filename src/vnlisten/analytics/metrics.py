"""Metric MKT chuẩn của social listening. Hàm thuần (input -> output), dễ test.

- Mentions        : số lượt nhắc
- Interactions    : like + comment + share
- SOV             : Share of Voice = mentions brand / tổng mentions các brand trong cùng phạm vi
- NSR             : Net Sentiment Rate = (pos - neg) / (pos + neg), từ -100% tới +100%
- Buzz growth     : % thay đổi mentions so với kỳ trước cùng độ dài
- Ranking score   : điểm tổng hợp để xếp hạng (xem RANKING_WEIGHTS)
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

import pandas as pd

from ..domain.models import Mention, ProductSnapshot

RANKING_WEIGHTS = {"mentions": 0.45, "interactions": 0.35, "nsr": 0.20}

MENTION_COLUMNS = [
    "uid", "source", "url", "title", "content", "author", "published_at", "industry", "category", "keyword",
    "brands", "products", "risk_terms", "sentiment", "sentiment_score", "activities", "hashtags",
    "community_id", "community_name", "community_type", "community_url", "visibility",
    "likes", "comments", "shares", "views", "interactions",
]


def to_frame(mentions: Sequence[Mention]) -> pd.DataFrame:
    rows = [
        {
            "uid": m.uid, "source": m.source.value, "url": m.url, "title": m.title, "content": m.content,
            "author": m.author, "published_at": m.published_at, "industry": m.industry,
            "category": m.category, "keyword": m.keyword,
            "brands": m.brands, "products": m.products, "risk_terms": m.risk_terms,
            "sentiment": m.sentiment.value, "sentiment_score": m.sentiment_score,
            "activities": m.activities, "hashtags": m.hashtags,
            "community_id": m.community_id, "community_name": m.community_name,
            "community_type": m.community_type, "community_url": m.community_url, "visibility": m.visibility,
            "likes": m.engagement.likes, "comments": m.engagement.comments,
            "shares": m.engagement.shares, "views": m.engagement.views,
            "interactions": m.engagement.interactions,
        }
        for m in mentions
    ]
    df = pd.DataFrame(rows, columns=MENTION_COLUMNS)
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    return df


def explode(df: pd.DataFrame, column: str) -> pd.DataFrame:
    exploded = df.explode(column)
    return exploded[exploded[column].notna() & (exploded[column] != "")]


def _nsr(pos: pd.Series, neg: pd.Series) -> pd.Series:
    denom = (pos + neg).replace(0, pd.NA)
    return ((pos - neg) / denom).astype("Float64").fillna(0.0)


def entity_metrics(df: pd.DataFrame, entity: str = "brands") -> pd.DataFrame:
    """Bảng metric theo brand hoặc product (entity = 'brands' | 'products')."""
    cols = ["entity", "mentions", "interactions", "views", "positive", "neutral", "negative", "nsr", "sov"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    ex = explode(df, entity)
    if ex.empty:
        return pd.DataFrame(columns=cols)
    g = ex.groupby(entity)
    out = pd.DataFrame({
        "mentions": g.size(),
        "interactions": g["interactions"].sum(),
        "views": g["views"].sum(),
        "positive": g["sentiment"].apply(lambda s: (s == "positive").sum()),
        "neutral": g["sentiment"].apply(lambda s: (s == "neutral").sum()),
        "negative": g["sentiment"].apply(lambda s: (s == "negative").sum()),
    })
    out["nsr"] = _nsr(out["positive"], out["negative"]).astype(float)
    out["sov"] = out["mentions"] / out["mentions"].sum()
    return out.reset_index(names="entity")[cols].sort_values("mentions", ascending=False, ignore_index=True)


def buzz_growth(df: pd.DataFrame, now: datetime, window: timedelta, entity: str = "brands") -> pd.DataFrame:
    """% tăng/giảm mentions của kỳ hiện tại so với kỳ liền trước."""
    if df.empty:
        return pd.DataFrame(columns=["entity", "current", "previous", "growth"])
    now_ts = pd.Timestamp(now)
    cur = df[df["published_at"] > now_ts - window]
    prev = df[(df["published_at"] <= now_ts - window) & (df["published_at"] > now_ts - 2 * window)]
    c = explode(cur, entity).groupby(entity).size().rename("current")
    p = explode(prev, entity).groupby(entity).size().rename("previous")
    out = pd.concat([c, p], axis=1).fillna(0).astype(int)
    out["growth"] = (out["current"] - out["previous"]) / out["previous"].replace(0, pd.NA)
    out["growth"] = out["growth"].astype("Float64")
    return out.reset_index(names="entity").sort_values("current", ascending=False, ignore_index=True)


def rank(metrics: pd.DataFrame) -> pd.DataFrame:
    """Xếp hạng: percentile của mentions & interactions + NSR quy về 0..1, nhân trọng số."""
    if metrics.empty:
        return metrics.assign(score=[], rank=[])
    m = metrics.copy()
    m["score"] = (
        RANKING_WEIGHTS["mentions"] * m["mentions"].rank(pct=True)
        + RANKING_WEIGHTS["interactions"] * m["interactions"].rank(pct=True)
        + RANKING_WEIGHTS["nsr"] * (m["nsr"] + 1) / 2
    ).round(3)
    m = m.sort_values("score", ascending=False, ignore_index=True)
    m["rank"] = range(1, len(m) + 1)
    return m


def timeline(df: pd.DataFrame, freq: str = "D", entity: str = "brands") -> pd.DataFrame:
    """Số mention theo thời gian cho từng entity (long format: time, entity, mentions)."""
    if df.empty:
        return pd.DataFrame(columns=["time", "entity", "mentions"])
    ex = explode(df, entity)
    ex = ex.assign(time=ex["published_at"].dt.tz_convert("Asia/Ho_Chi_Minh").dt.floor(freq))
    wide = ex.groupby(["time", entity]).size().unstack(fill_value=0)
    # Điền 0 cho các mốc không có bài => đường không bị "đứt" / nối sai
    full_range = pd.date_range(wide.index.min(), wide.index.max(), freq=freq)
    wide = wide.reindex(full_range, fill_value=0)
    wide.index.name = "time"
    return wide.reset_index().melt(id_vars="time", var_name="entity", value_name="mentions")


def risk_term_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["term", "mentions"])
    ex = explode(df, "risk_terms")
    return ex.groupby("risk_terms").size().reset_index(name="mentions").rename(
        columns={"risk_terms": "term"}).sort_values("mentions", ascending=False, ignore_index=True)


def marketplace_ranking(snapshots: Sequence[ProductSnapshot], category: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame([s.__dict__ for s in snapshots])
    if df.empty:
        return df
    df["source"] = df["source"].astype(str)
    if category:
        df = df[df["category"] == category]
    return df.sort_values("sold_count", ascending=False, ignore_index=True)
