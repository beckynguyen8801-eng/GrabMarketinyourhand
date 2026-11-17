"""COMMUNITY RANKING: rà soát, đánh giá nhanh, xếp hạng & đề xuất community hiệu quả cho 1 keyword/brand/sản phẩm.

Điểm (0–1) gồm 5 thành phần – mỗi cái trả lời 1 câu hỏi của người làm MKT:
  activity   25%  Community có sôi nổi không?            (số bài / tuần, percentile)
  engagement 25%  Bài trong đó có được tương tác không?   (tương tác TB / bài, percentile)
  relevance  25%  Có nói về chủ đề MÌNH quan tâm không?   (% bài khớp keyword/brand đang search)
  intent     15%  Thành viên có đang cân nhắc MUA không?  (% bài hỏi/xin review/so sánh/hỏi giá)
  openness   10%  Có vào được không?                       (public 1.0 · unknown 0.6 · private 0.3)
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from ..pipeline.text import normalize_for_match
from ..taxonomy import Taxonomy

WEIGHTS = {"activity": 0.25, "engagement": 0.25, "relevance": 0.25, "intent": 0.15, "openness": 0.10}
OPENNESS = {"public": 1.0, "unknown": 0.6, "private": 0.3}
TYPE_LABELS = {
    "fb_group": "Facebook group", "fb_page": "Facebook page", "tiktok_account": "TikTok account",
    "ig_account": "Instagram account", "threads_account": "Threads account", "youtube_channel": "YouTube channel",
    "forum": "Forum", "news_site": "News site",
}
# Dấu hiệu người đang cân nhắc mua (khớp không dấu)
INTENT_TERMS = (
    "cho hoi", "cho em hoi", "cho minh hoi", "nen mua", "nen dung", "loai nao", "cai nao", "review", "xin kinh nghiem",
    "so sanh", "mua o dau", "gia bao nhieu", "bao nhieu tien", "co tot khong", "co nen", "tu van", "phan van",
    "recommend", "dat lich", "kham o dau", "hop khong",
)
_INTENT_RE = re.compile(r"(?<![0-9a-z])(?:" + "|".join(re.escape(t) for t in INTENT_TERMS) + r")(?![0-9a-z])")

COLUMNS = ["rank", "community_id", "name", "type", "url", "visibility", "posts", "posts_per_week",
           "matched_posts", "relevance", "avg_interactions", "intent", "nsr", "top_brands", "score", "tier",
           "recommendation", "summary"]


def _pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True) if len(s) > 1 else pd.Series(1.0, index=s.index)


def rank_communities(base: pd.DataFrame, matched: pd.DataFrame, tax: Taxonomy, days: int,
                     focus_brands: set[str] | None = None, min_posts: int = 5) -> pd.DataFrame:
    """base = toàn bộ bài trong kỳ (để biết community 'nói gì nói chung');
    matched = bài khớp keyword/brand người dùng đang search (= base nếu không search).
    focus_brands = brand người dùng quan tâm (để phát hiện "sân nhà đối thủ")."""
    if base.empty or "community_id" not in base:
        return pd.DataFrame(columns=COLUMNS)
    base = base[base["community_id"] != ""]
    if base.empty:
        return pd.DataFrame(columns=COLUMNS)
    matched_ids = set(matched["uid"]) if not matched.empty else set()
    weeks = max(days / 7, 1 / 7)
    focus_brands = focus_brands or set()

    rows = []
    for cid, g in base.groupby("community_id"):
        if len(g) < min_posts:
            continue
        hits = g[g["uid"].isin(matched_ids)]
        texts = (g["title"].fillna("") + " " + g["content"].fillna("")).map(normalize_for_match)
        pos, neg = (hits["sentiment"] == "positive").sum(), (hits["sentiment"] == "negative").sum()
        brand_counts = Counter(b for lst in g["brands"] for b in lst)
        visibility = g["visibility"].mode().iat[0] if not g["visibility"].empty else "unknown"
        rows.append({
            "community_id": cid,
            "name": g["community_name"].replace("", pd.NA).dropna().mode().iat[0]
            if g["community_name"].ne("").any() else cid.split(":", 1)[-1],
            "type": TYPE_LABELS.get(g["community_type"].iat[0], g["community_type"].iat[0]),
            "url": g["community_url"].replace("", pd.NA).dropna().iat[0] if g["community_url"].ne("").any() else "",
            "visibility": visibility,
            "posts": len(g),
            "posts_per_week": round(len(g) / weeks, 1),
            "matched_posts": len(hits),
            "relevance": len(hits) / len(g),
            "avg_interactions": round(float(g["interactions"].mean()), 1),
            "intent": float(texts.map(lambda t: bool(_INTENT_RE.search(t))).mean()),
            "nsr": float((pos - neg) / (pos + neg)) if pos + neg else 0.0,
            "brand_counts": brand_counts,
            "top_brands": ", ".join(tax.brand_name(b) for b, _ in brand_counts.most_common(3)),
        })
    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    out = pd.DataFrame(rows)
    out["score"] = (
        WEIGHTS["activity"] * _pct_rank(out["posts_per_week"])
        + WEIGHTS["engagement"] * _pct_rank(out["avg_interactions"])
        + WEIGHTS["relevance"] * out["relevance"]
        + WEIGHTS["intent"] * out["intent"].clip(upper=0.6) / 0.6
        + WEIGHTS["openness"] * out["visibility"].map(OPENNESS).fillna(0.6)
    ).round(3)
    out = out[out["matched_posts"] > 0].sort_values("score", ascending=False, ignore_index=True)
    out["tier"] = out["score"].map(lambda s: "High potential" if s >= 0.65 else "Worth testing" if s >= 0.45
                                   else "Monitor")
    # Ngưỡng TƯƠNG ĐỐI so với các community khác trong cùng kết quả – số tuyệt đối (VD 30% on-topic)
    # quá phụ thuộc độ rộng của từ khoá người dùng gõ.
    ctx = {
        "relevance_hi": min(0.6, max(0.15, float(out["relevance"].median()) * 1.15)),
        "intent_hi": max(0.15, float(out["intent"].median())),
        "reach_hi": float(out["avg_interactions"].quantile(0.75)),
    }
    out["recommendation"] = [_recommend(r, focus_brands, ctx) for r in out.itertuples()]
    out["summary"] = [_summary(r) for r in out.itertuples()]
    out["rank"] = range(1, len(out) + 1)
    return out[COLUMNS]


def _recommend(r, focus_brands: set[str], ctx: dict[str, float]) -> str:
    """Quy tắc đề xuất – ưu tiên rủi ro trước, cơ hội sau."""
    brands: Counter = r.brand_counts
    own = sum(brands[b] for b in focus_brands)
    rival = sum(c for b, c in brands.items() if b not in focus_brands)
    on_topic = r.relevance >= ctx["relevance_hi"]
    if r.nsr <= -0.3 and r.matched_posts >= 5:
        return "Crisis watch – reply with facts, brief the admin, track daily"
    if r.visibility == "private":
        return "Request to join; observe 1–2 weeks before posting"
    if focus_brands and rival > 2 * max(own, 1):
        return "Competitor stronghold – sponsor the admin or run a comparison review"
    if on_topic and r.intent >= ctx["intent_hi"]:
        return "Buyers asking questions – seed honest KOC reviews and answer threads"
    if on_topic:
        return "Core community – build a long-term presence (expert answers, AMA)"
    if r.avg_interactions >= ctx["reach_hi"]:
        return "Big reach, broad topic – awareness content or minigame"
    if r.intent >= ctx["intent_hi"]:
        return "Active buyers, other topics – answer questions where your product fits"
    return "Keep monitoring – test with 1–2 helpful posts"


def _summary(r) -> str:
    return (f"{r.posts_per_week:g} posts/week · {r.relevance:.0%} on-topic · "
            f"{r.intent:.0%} buying questions · avg {r.avg_interactions:,.0f} interactions · NSR {r.nsr:+.0%}")
