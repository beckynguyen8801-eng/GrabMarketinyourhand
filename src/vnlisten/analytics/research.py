"""Metric cho module RESEARCH: hoạt động MKT, chiến dịch (hashtag), keyword, trend.

Khác Social Listening ở câu hỏi trả lời:
- Listening: "người ta đang NÓI gì về brand?"  (mentions, SOV, NSR, khủng hoảng)
- Research : "brand đang LÀM gì & thị trường đang QUAN TÂM gì?" (campaign, kênh, keyword, trend)
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta

import pandas as pd

from ..domain.models import KeywordSuggestion
from ..pipeline.activity import activity_channel, activity_name
from .metrics import explode
from .phrases import diversify, drop_subphrases, phrases

def _window(df: pd.DataFrame, now: datetime, window: timedelta) -> tuple[pd.DataFrame, pd.DataFrame]:
    now_ts = pd.Timestamp(now)
    cur = df[df["published_at"] > now_ts - window]
    prev = df[(df["published_at"] <= now_ts - window) & (df["published_at"] > now_ts - 2 * window)]
    return cur, prev


def activity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mỗi loại hoạt động: bao nhiêu bài, tương tác, bao nhiêu brand đang làm."""
    cols = ["activity", "name", "channel", "mentions", "interactions", "brands"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    ex = explode(df, "activities")
    if ex.empty:
        return pd.DataFrame(columns=cols)
    g = ex.groupby("activities")
    out = pd.DataFrame({
        "mentions": g.size(),
        "interactions": g["interactions"].sum(),
        "brands": g["brands"].apply(lambda s: len({b for lst in s for b in lst})),
    }).reset_index(names="activity")
    out["name"] = out["activity"].map(activity_name)
    out["channel"] = out["activity"].map(lambda a: activity_channel(a).value)
    return out[cols].sort_values("mentions", ascending=False, ignore_index=True)


def activity_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Ma trận brand x loại hoạt động (long format) – thấy ngay brand nào đang chơi kênh nào."""
    if df.empty:
        return pd.DataFrame(columns=["brand", "activity", "mentions"])
    ex = explode(explode(df, "activities"), "brands")
    return ex.groupby(["brands", "activities"]).size().reset_index(name="mentions").rename(
        columns={"brands": "brand", "activities": "activity"})


def channel_split(df: pd.DataFrame) -> pd.DataFrame:
    """Tỷ trọng hoạt động online vs offline theo brand."""
    m = activity_matrix(df)
    if m.empty:
        return pd.DataFrame(columns=["brand", "online", "offline", "offline_share"])
    m["channel"] = m["activity"].map(lambda a: activity_channel(a).value)
    out = m.pivot_table(index="brand", columns="channel", values="mentions", aggfunc="sum", fill_value=0)
    for col in ("online", "offline"):
        if col not in out:
            out[col] = 0
    out["offline_share"] = out["offline"] / (out["online"] + out["offline"])
    return out.reset_index()[["brand", "online", "offline", "offline_share"]].sort_values(
        "online", ascending=False, ignore_index=True)


def top_hashtags(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """Hashtag = dấu vết chiến dịch. Gắn brand xuất hiện nhiều nhất cùng hashtag."""
    cols = ["hashtag", "mentions", "interactions", "brand", "first_seen", "last_seen"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    ex = explode(df, "hashtags")
    if ex.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for tag, grp in ex.groupby("hashtags"):
        brands = Counter(b for lst in grp["brands"] for b in lst)
        rows.append({
            "hashtag": f"#{tag}", "mentions": len(grp), "interactions": int(grp["interactions"].sum()),
            "brand": brands.most_common(1)[0][0] if brands else "",
            "first_seen": grp["published_at"].min(), "last_seen": grp["published_at"].max(),
        })
    return pd.DataFrame(rows, columns=cols).sort_values("interactions", ascending=False, ignore_index=True).head(limit)


def keyword_performance(df: pd.DataFrame, now: datetime, window: timedelta) -> pd.DataFrame:
    """Hiệu suất từng keyword đang theo dõi: lượt nhắc kỳ này / kỳ trước / NSR."""
    cols = ["keyword", "current", "previous", "growth", "nsr"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    cur, prev = _window(df, now, window)
    c = cur.groupby("keyword").agg(
        current=("uid", "size"),
        pos=("sentiment", lambda s: (s == "positive").sum()),
        neg=("sentiment", lambda s: (s == "negative").sum()),
    )
    p = prev.groupby("keyword").size().rename("previous")
    out = c.join(p, how="outer").fillna(0)
    out["growth"] = ((out["current"] - out["previous"]) / out["previous"].replace(0, pd.NA)).astype("Float64")
    denom = (out["pos"] + out["neg"]).replace(0, pd.NA)
    out["nsr"] = ((out["pos"] - out["neg"]) / denom).astype("Float64").fillna(0.0)
    out[["current", "previous"]] = out[["current", "previous"]].astype(int)
    return out.reset_index(names="keyword")[cols].sort_values("current", ascending=False, ignore_index=True)


def trending_phrases(df: pd.DataFrame, now: datetime, window: timedelta, sizes: tuple[int, ...] = (2, 3),
                     min_count: int = 3, limit: int = 15) -> pd.DataFrame:
    """Cụm từ tăng mạnh nhất kỳ này so với kỳ trước – radar bắt trend MKT / chủ đề mới.

    Gộp n-gram nhiều độ dài rồi bỏ cụm con: có "men vi sinh" thì bỏ "men vi", "vi sinh".
    """
    cols = ["phrase", "current", "previous", "lift"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    cur, prev = _window(df, now, window)
    count_cur: Counter[str] = Counter()
    count_prev: Counter[str] = Counter()
    for n in sizes:
        count_cur.update(p for text in cur["content"] for p in phrases(text, n))
        count_prev.update(p for text in prev["content"] for p in phrases(text, n))

    kept = drop_subphrases({p: c for p, c in count_cur.items() if c >= min_count})
    rows = [
        {"phrase": p, "current": c, "previous": count_prev.get(p, 0), "lift": (c + 1) / (count_prev.get(p, 0) + 1)}
        for p, c in kept.items()
    ]
    out = pd.DataFrame(rows, columns=cols).sort_values(["lift", "current"], ascending=False, ignore_index=True)
    return diversify(out, "phrase").head(limit)


def suggestion_table(history: Sequence[KeywordSuggestion]) -> pd.DataFrame:
    """Gợi ý Google mới nhất theo seed; đánh dấu gợi ý MỚI xuất hiện so với các lần quét trước."""
    cols = ["seed", "suggestion", "rank", "is_new"]
    if not history:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame([s.__dict__ for s in history])
    latest_at = df.groupby("seed")["captured_at"].transform("max")
    latest = df[df["captured_at"] == latest_at]
    older = set(zip(df.loc[df["captured_at"] < latest_at, "seed"], df.loc[df["captured_at"] < latest_at, "suggestion"],
                    strict=True))
    has_history = df.groupby("seed")["captured_at"].nunique() > 1
    latest = latest.assign(is_new=[
        bool(has_history.get(s)) and (s, sug) not in older for s, sug in zip(latest["seed"], latest["suggestion"], strict=True)
    ])
    return latest[cols].sort_values(["seed", "rank"], ignore_index=True)
