"""Sinh nhận định + đề xuất hành động từ số liệu.

- RuleBasedInsight: free, deterministic, chạy ngay.
- OllamaInsight: dùng LLM local (Qwen2.5 7B đọc tiếng Việt khá ổn) – vẫn free, chỉ tốn RAM/GPU.
  Lỗi => tự fallback về RuleBasedInsight.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass
class InsightContext:
    industry_name: str
    period_label: str
    total_mentions: int
    total_interactions: int
    overall_nsr: float
    top_brands: list[dict] = field(default_factory=list)      # entity, mentions, sov, nsr
    risers: list[dict] = field(default_factory=list)          # entity, current, previous, growth
    negative_hotspots: list[dict] = field(default_factory=list)  # entity, negative, nsr
    risk_terms: list[dict] = field(default_factory=list)      # term, mentions
    alerts: list[str] = field(default_factory=list)
    # ---- Research ----
    top_activities: list[dict] = field(default_factory=list)  # activity, mentions, channel
    offline_share: float | None = None                        # tỷ trọng bài hoạt động offline / tổng bài hoạt động
    top_hashtags: list[dict] = field(default_factory=list)    # hashtag, brand, interactions
    trending_phrases: list[str] = field(default_factory=list)


class InsightGenerator(Protocol):
    def generate(self, ctx: InsightContext) -> str: ...


class RuleBasedInsight:
    def generate(self, ctx: InsightContext) -> str:
        lines = [f"### {ctx.industry_name} – summary, {ctx.period_label}",
                 f"- **{ctx.total_mentions:,}** mentions, **{ctx.total_interactions:,}** interactions, "
                 f"industry NSR **{ctx.overall_nsr:+.0%}**."]
        if ctx.top_brands:
            leader = ctx.top_brands[0]
            lines.append(f"- Conversation leader: **{leader['entity']}** (SOV {leader['sov']:.0%}, NSR {leader['nsr']:+.0%}).")
        for r in ctx.risers[:3]:
            lines.append(f"- **{r['entity']}** buzz {r['growth']:+.0%} ({r['previous']} → {r['current']}).")
        for h in ctx.negative_hotspots[:3]:
            lines.append(f"- **{h['entity']}**: {h['negative']} negative posts, NSR {h['nsr']:+.0%}.")
        if ctx.risk_terms:
            terms = ", ".join(f"{t['term']} ({t['mentions']})" for t in ctx.risk_terms[:5])
            lines.append(f"- Top risk keywords: {terms}.")

        if ctx.top_activities or ctx.top_hashtags or ctx.trending_phrases:
            lines += ["", "### Marketing activity & trends"]
        if ctx.top_activities:
            acts = ", ".join(f"{a['activity']} ({a['mentions']})" for a in ctx.top_activities)
            lines.append(f"- Most common activities: {acts}.")
        if ctx.offline_share is not None:
            lines.append(f"- Offline accounts for {ctx.offline_share:.0%} of activity posts.")
        for h in ctx.top_hashtags[:3]:
            lines.append(f"- Standout campaign: **{h['hashtag']}** ({h['brand']}, {h['interactions']:,} interactions).")
        if ctx.trending_phrases:
            lines.append(f"- Rising phrases: {', '.join(ctx.trending_phrases)}.")

        lines += ["", "### Recommended actions"]
        actions = []
        if ctx.alerts:
            actions.append("Handle crisis alerts now: verify the source, prepare a statement and a customer-care script within 24h.")
        if ctx.negative_hotspots:
            names = ", ".join(h["entity"] for h in ctx.negative_hotspots[:3])
            actions.append(f"Review the negative feed for {names}: split product issues / service issues / rumours and respond on the right channel.")
        if ctx.risers:
            actions.append(f"Audit **{ctx.risers[0]['entity']}**'s campaigns (Meta Ad Library, TikTok Creative Center) to see which message they push.")
        if ctx.top_brands and ctx.top_brands[0]["nsr"] < 0.2:
            actions.append("The leading brand has a low NSR – an opening for comparison content and genuine KOC reviews.")
        if ctx.top_hashtags:
            actions.append(f"Break down campaign {ctx.top_hashtags[0]['hashtag']}: message, KOLs, reward mechanics – learn from it or avoid overlap.")
        if ctx.trending_phrases:
            actions.append(f"Ride the \"{ctx.trending_phrases[0]}\" trend with content in the next 3–5 days while it is hot.")
        actions.append("Seed conversations in target communities around the hot topics (reviews, buying advice).")
        lines += [f"{i}. {a}" for i, a in enumerate(actions, 1)]
        return "\n".join(lines)


class OllamaInsight:
    PROMPT = (
        "You are a marketing expert for the {industry} industry in Vietnam. Using the social listening data (JSON) below, "
        "write concise markdown IN ENGLISH (quote Vietnamese keywords as-is):\n"
        "1) 3-5 key insights (with numbers)\n2) Risks to monitor\n"
        "3) 3-5 concrete, feasible online/offline marketing actions.\n"
        "Do not invent numbers that are not in the JSON.\n\nJSON:\n{data}"
    )

    def __init__(self, url: str, model: str, fallback: InsightGenerator | None = None):
        self._url = url.rstrip("/") + "/api/generate"
        self._model = model
        self._fallback = fallback or RuleBasedInsight()

    def generate(self, ctx: InsightContext) -> str:
        prompt = self.PROMPT.format(industry=ctx.industry_name, data=json.dumps(asdict(ctx), ensure_ascii=False, default=str))
        try:
            resp = httpx.post(self._url, json={"model": self._model, "prompt": prompt, "stream": False}, timeout=180)
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except (httpx.HTTPError, KeyError) as exc:
            log.warning("Ollama lỗi (%s) – dùng insight rule-based", exc)
            return self._fallback.generate(ctx)
