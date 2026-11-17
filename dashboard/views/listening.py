"""SOCIAL LISTENING: what are people SAYING – volume, SOV, NSR, ranking, product keywords, crises."""
from __future__ import annotations

import html
from datetime import timedelta

import plotly.express as px
import streamlit as st
from ui import (
    keyword_cloud, MAGNITUDE, NEGATIVE, SENTIMENT_COLORS, SENTIMENT_LABELS, SERIES, SOURCE_LABELS, Kpi, ViewContext, brand_list,
    kpi_row, nsr_of, pct_delta, section, style,
)
from views import insight

from vnlisten.analytics import communities, keywords, metrics
from vnlisten.domain.models import Severity

DATE_COL = st.column_config.DatetimeColumn("Published", format="DD/MM HH:mm")
LINK_COL = st.column_config.LinkColumn("Link", display_text="Open")


def render(ctx: ViewContext) -> None:
    tax, cur, prev = ctx.tax, ctx.cur, ctx.prev
    alerts_24h = [a for a in ctx.repo.recent_alerts(100, tax.industry) if a.created_at > ctx.now - timedelta(days=1)]
    high = sum(a.severity is Severity.HIGH for a in alerts_24h)
    nsr_now, nsr_prev = nsr_of(cur), nsr_of(prev)
    kpi_row([
        Kpi("Mentions", f"{len(cur):,}", pct_delta(len(cur), len(prev)), len(cur) >= len(prev) if len(prev) else None),
        Kpi("Interactions", f"{int(cur['interactions'].sum()):,}"),
        Kpi("Net sentiment (NSR)", f"{nsr_now:+.0%}",
            f"{(nsr_now - nsr_prev) * 100:+.0f} pts" if len(prev) else "", nsr_now >= nsr_prev if len(prev) else None),
        Kpi("Negative posts", f"{(cur['sentiment'] == 'negative').sum():,}"),
        Kpi("Alerts (24h)", str(len(alerts_24h)), f"{high} high severity" if high else "", False if high else None),
    ])

    tabs = st.tabs(["Overview", "Product keywords", "Communities", "Ranking", "Risks & alerts", "Marketplace",
                    "Insights", "Posts"])
    brand = metrics.entity_metrics(cur, "brands")
    brand["name"] = brand["entity"].map(tax.brand_name)

    with tabs[0]:
        _overview(ctx, brand)
    with tabs[1]:
        _product_keywords(ctx, brand)
    with tabs[2]:
        _communities(ctx)
    with tabs[3]:
        _ranking(ctx, brand)
    with tabs[4]:
        _risks(ctx)
    with tabs[5]:
        _marketplace(ctx)
    with tabs[6]:
        insight.render(ctx)
    with tabs[7]:
        _posts(ctx)


# ---------------------------------------------------------------------------
def _overview(ctx: ViewContext, brand) -> None:
    tax, cur = ctx.tax, ctx.cur
    left, right = st.columns([3, 2])
    with left, section("Mentions over time"):
        picked = st.multiselect("Compare brands (max 5)", brand["name"].tolist(),
                                default=brand["name"].head(4).tolist(), max_selections=5)
        tl = metrics.timeline(cur, "h" if ctx.days == 1 else "D")
        tl["name"] = tl["entity"].map(tax.brand_name)
        tl = tl[tl["name"].isin(picked)]
        fig = px.line(tl, x="time", y="mentions", color="name", markers=True, line_shape="spline",
                      category_orders={"name": picked}, color_discrete_sequence=SERIES,
                      labels={"time": "", "mentions": "Mentions", "name": "Brand"})
        st.plotly_chart(style(fig), width="stretch")
    with right, section("Share of voice"):
        sov = brand.head(10).sort_values("sov")
        fig = px.bar(sov, x="sov", y="name", orientation="h", text=sov["sov"].map("{:.0%}".format),
                     labels={"sov": "SOV", "name": ""}, color_discrete_sequence=[MAGNITUDE])
        fig.update_xaxes(tickformat=".0%")
        fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
        st.plotly_chart(style(fig, 390), width="stretch")

    left, right = st.columns([3, 2])
    with left, section("Sentiment by brand"):
        top = brand.head(10)
        sent = top.melt(id_vars="name", value_vars=["positive", "neutral", "negative"],
                        var_name="sentiment", value_name="n")
        sent["sentiment"] = sent["sentiment"].map(SENTIMENT_LABELS)
        fig = px.bar(sent, x="n", y="name", color="sentiment", orientation="h",
                     category_orders={"name": top["name"].tolist(), "sentiment": list(SENTIMENT_COLORS)},
                     color_discrete_map=SENTIMENT_COLORS, labels={"n": "Mentions", "name": "", "sentiment": ""})
        st.plotly_chart(style(fig, 380), width="stretch")
    with right, section("Mentions by source"):
        src = cur.groupby("source").size().reset_index(name="n").sort_values("n")
        src["source"] = src["source"].map(lambda s: SOURCE_LABELS.get(s, s))
        fig = px.bar(src, x="n", y="source", orientation="h", text="n",
                     labels={"n": "Mentions", "source": ""}, color_discrete_sequence=[MAGNITUDE])
        fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
        st.plotly_chart(style(fig, 380), width="stretch")


# ---------------------------------------------------------------------------
def _product_keywords(ctx: ViewContext, brand) -> None:
    """Pick a brand -> product: every keyword people use when talking about it."""
    tax = ctx.tax
    box = section("Product keywords",
                  "Type any brand and product – e.g. “enfa” + “enfa A2”, or “vinmec” alone. Accents optional. "
                  "Known = matched against the industry vocabulary; Discovered = recurring phrases worth a look.")
    with box:
        top_brand = tax.brand_name(brand["entity"].iloc[0]) if not brand.empty else ""
        with st.form("product_keywords", border=False):
            c1, c2, c3 = st.columns([2, 3, 1], vertical_alignment="bottom")
            brand_text = c1.text_input("Brand", value=top_brand, placeholder="Type any brand, e.g. enfa")
            product_text = c2.text_input("Product", placeholder="Type any product, e.g. enfa A2 (empty = brand-wide)")
            c3.form_submit_button("Find keywords", type="primary", width="stretch")

        lookup = keywords.free_text_keywords(ctx.cur, tax, brand_text, product_text)
        matched = []
        if lookup.brand_id:
            matched.append(f"Brand · {tax.brand_name(lookup.brand_id)}")
        if lookup.product_id:
            matched.append(f"Product · {tax.product_name(lookup.product_id)}")
        note = {"product": "", "brand": "", "text": "no exact product match – searching post text"}[lookup.mode]
        st.markdown("Matched: " + "".join(f'<span class="pill">{html.escape(m)}</span>' for m in matched)
                    + f" <small>{lookup.posts:,} posts{' · ' + note if note else ''}</small>",
                    unsafe_allow_html=True)

        info = tax.brands[lookup.brand_id].info if lookup.brand_id else {}
        if info:
            cells = "".join(f"<div><span>{html.escape(k.title())}</span><b>{html.escape(v)}</b></div>"
                            for k, v in info.items())
            st.markdown(f'<div class="info-grid">{cells}</div>', unsafe_allow_html=True)

        kw = lookup.table
        if kw.empty:
            st.info("No keywords yet for this selection in the chosen period.")
            return
        left, right = st.columns([2, 3])
        with left:
            st.markdown(keyword_cloud(kw.head(32)), unsafe_allow_html=True)
        with right:
            st.dataframe(kw, hide_index=True, width="stretch", height=460, column_config={
                "keyword": "Keyword", "type": "Type", "mentions": "Posts",
                "share": st.column_config.NumberColumn("Share of posts", format="percent"),
                "positive": "Pos.", "negative": "Neg.",
                "nsr": st.column_config.NumberColumn("NSR", format="percent"),
                "interactions": st.column_config.NumberColumn("Interactions", format="%d"),
                "example": st.column_config.TextColumn("Example post", width="large"),
            })


# ---------------------------------------------------------------------------
TIER_COLORS = {"High potential": "#0e9f6e", "Worth testing": "#e8590c", "Monitor": "#8a93a6"}


def _communities(ctx: ViewContext) -> None:
    """Scan, score, rank and recommend communities for whatever the user searched (keyword / brand / product)."""
    tax = ctx.tax
    focus = keywords.matching_entities(tax, ctx.query)[0] if ctx.query else set()
    ranked = communities.rank_communities(ctx.base_cur if ctx.base_cur is not None else ctx.cur, ctx.cur, tax,
                                          ctx.days, focus_brands=focus)
    caption = (f"Communities talking about “{ctx.query}”" if ctx.query else "All communities in this industry") + \
        ". Score = 25% activity · 25% engagement · 25% relevance · 15% buying intent · 10% openness."
    with section("Community radar", caption):
        if ranked.empty:
            st.info("No communities yet. Capture Facebook groups / TikTok with the browser extension "
                    "(`vnlisten serve`) or enable web search (SEARXNG_URL) – see README.")
            return
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        types = c1.multiselect("Type", sorted(ranked["type"].unique()), default=sorted(ranked["type"].unique()))
        public_only = c2.toggle("Public only", value=False)
        view = ranked[ranked["type"].isin(types)]
        if public_only:
            view = view[view["visibility"] == "public"]

        cards = []
        for r in view.head(3).itertuples():
            color = TIER_COLORS[r.tier]
            link = f'<a href="{html.escape(r.url)}" target="_blank">Open</a>' if r.url else ""
            cards.append(
                f'<div class="kpi" style="flex:1 1 280px"><div class="label">#{r.rank} · {html.escape(r.type)} · '
                f'{html.escape(r.visibility)}</div><div style="font-size:18px;font-weight:700;margin:6px 0">'
                f'{html.escape(r.name)}</div><span class="pill" style="background:{color}1f;color:{color}">'
                f'{r.tier} · {r.score:.2f}</span><div style="font-size:12px;color:#3b4459;margin:8px 0">'
                f'{html.escape(r.summary)}</div><div style="font-size:13px;font-weight:600">→ '
                f'{html.escape(r.recommendation)}</div><div style="font-size:12px;margin-top:6px">{link}</div></div>')
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:14px;margin-bottom:12px">{"".join(cards)}</div>',
                    unsafe_allow_html=True)

        left, right = st.columns([2, 3])
        with left:
            fig = px.scatter(view, x="relevance", y="avg_interactions", size="posts", color="tier",
                             hover_name="name", color_discrete_map=TIER_COLORS, size_max=36,
                             labels={"relevance": "On-topic share", "avg_interactions": "Avg interactions / post",
                                     "tier": ""},
                             category_orders={"tier": list(TIER_COLORS)})
            fig.update_xaxes(tickformat=".0%")
            st.plotly_chart(style(fig, 420), width="stretch")
            st.caption("Top-right = on-topic AND engaging → best place to be.")
        with right:
            st.dataframe(view[["rank", "name", "type", "visibility", "score", "tier", "posts_per_week",
                               "relevance", "intent", "nsr", "top_brands", "recommendation", "url"]],
                         hide_index=True, width="stretch", height=420, column_config={
                             "rank": "#", "name": "Community", "type": "Type", "visibility": "Access",
                             "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1,
                                                                      format="%.2f"),
                             "tier": "Tier", "posts_per_week": "Posts / week",
                             "relevance": st.column_config.NumberColumn("On-topic", format="percent"),
                             "intent": st.column_config.NumberColumn("Buying intent", format="percent"),
                             "nsr": st.column_config.NumberColumn("NSR", format="percent"),
                             "top_brands": "Top brands",
                             "recommendation": st.column_config.TextColumn("Recommendation", width="large"),
                             "url": LINK_COL})


# ---------------------------------------------------------------------------
def _ranking(ctx: ViewContext, brand) -> None:
    tax = ctx.tax
    growth = metrics.buzz_growth(ctx.df_all, ctx.now, timedelta(days=ctx.days))[["entity", "growth"]]
    ranked = metrics.rank(brand).merge(growth, on="entity", how="left")
    with section("Top brands", "Score = 45% mentions + 35% interactions (percentile) + 20% NSR."):
        st.dataframe(
            ranked[["rank", "name", "score", "mentions", "interactions", "sov", "nsr", "growth", "negative"]],
            hide_index=True, width="stretch",
            column_config={
                "rank": "#", "name": "Brand",
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1, format="%.2f"),
                "mentions": "Mentions", "interactions": st.column_config.NumberColumn("Interactions", format="%d"),
                "sov": st.column_config.NumberColumn("SOV", format="percent"),
                "nsr": st.column_config.NumberColumn("NSR", format="percent"),
                "growth": st.column_config.NumberColumn("Buzz growth", format="percent"),
                "negative": "Negative",
            })
    prod = metrics.rank(metrics.entity_metrics(ctx.cur, "products"))
    if prod.empty:
        return
    prod["name"] = prod["entity"].map(tax.product_name)
    prod["brand"] = prod["entity"].map(lambda p: tax.brand_name(tax.products[p].brand) if p in tax.products else "")
    prod["category"] = prod["entity"].map(
        lambda p: tax.category_name(tax.products[p].category) if p in tax.products else "")
    with section("Top products"):
        st.dataframe(
            prod[["rank", "name", "brand", "category", "score", "mentions", "interactions", "nsr", "negative"]],
            hide_index=True, width="stretch",
            column_config={
                "rank": "#", "name": "Product", "brand": "Brand", "category": "Category",
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=1, format="%.2f"),
                "mentions": "Mentions", "interactions": st.column_config.NumberColumn("Interactions", format="%d"),
                "nsr": st.column_config.NumberColumn("NSR", format="percent"), "negative": "Negative",
            })


# ---------------------------------------------------------------------------
def _risks(ctx: ViewContext) -> None:
    tax, cur = ctx.tax, ctx.cur
    left, right = st.columns([3, 2])
    with left, section("Recent alerts"):
        alerts = ctx.repo.recent_alerts(30, tax.industry)
        if not alerts:
            st.success("No alerts.")
        for a in alerts:
            level = "High" if a.severity is Severity.HIGH else "Medium"
            with st.expander(f"{level} · {a.title} · {a.created_at.astimezone():%d/%m %H:%M}"):
                st.text(a.detail)
    with right, section("Risk keywords"):
        risk = metrics.risk_term_counts(cur).head(10).sort_values("mentions")
        if risk.empty:
            st.caption("No risk keywords in this period.")
        else:
            fig = px.bar(risk, x="mentions", y="term", orientation="h", text="mentions",
                         labels={"mentions": "Mentions", "term": ""}, color_discrete_sequence=[NEGATIVE])
            fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
            st.plotly_chart(style(fig), width="stretch")

    with section("Top negative posts"):
        neg = cur[cur["sentiment"] == "negative"].sort_values("interactions", ascending=False).head(50).copy()
        neg["brands"] = neg["brands"].map(lambda b: brand_list(tax, b))
        neg["risk_terms"] = neg["risk_terms"].map(", ".join)
        neg["source"] = neg["source"].map(lambda s: SOURCE_LABELS.get(s, s))
        st.dataframe(neg[["published_at", "source", "brands", "content", "risk_terms", "interactions", "url"]],
                     hide_index=True, width="stretch",
                     column_config={"published_at": DATE_COL, "source": "Source", "brands": "Brand",
                                    "content": "Content", "risk_terms": "Risk keywords",
                                    "interactions": "Interactions", "url": LINK_COL})


def _marketplace(ctx: ViewContext) -> None:
    market = metrics.marketplace_ranking(ctx.repo.latest_snapshots(ctx.tax.industry))
    with section("Marketplace best sellers",
                 "High buzz but low sales → conversion problem. High sales but low buzz → content opportunity."):
        if market.empty:
            st.info("No marketplace snapshots yet. Run `vnlisten daily`.")
            return
        market["category"] = market["category"].map(ctx.tax.category_name)
        st.dataframe(market[["name", "brand", "category", "sold_count", "price", "rating", "review_count", "url"]]
                     .head(40), hide_index=True, width="stretch",
                     column_config={"name": "Product", "brand": "Brand", "category": "Category",
                                    "sold_count": st.column_config.NumberColumn("Sold", format="%d"),
                                    "price": st.column_config.NumberColumn("Price (VND)", format="%d"),
                                    "rating": st.column_config.NumberColumn("Rating", format="%.1f ★"),
                                    "review_count": "Reviews", "url": LINK_COL})


def _posts(ctx: ViewContext) -> None:
    feed = ctx.cur.sort_values("published_at", ascending=False).copy()
    feed["brands"] = feed["brands"].map(lambda b: brand_list(ctx.tax, b))
    feed["sentiment"] = feed["sentiment"].map(SENTIMENT_LABELS)
    feed["source"] = feed["source"].map(lambda s: SOURCE_LABELS.get(s, s))
    with section("Posts", f"{len(feed):,} posts" + (f" matching “{ctx.query}”" if ctx.query else "")):
        st.dataframe(feed[["published_at", "source", "brands", "sentiment", "content", "interactions", "url"]]
                     .head(500), hide_index=True, width="stretch",
                     column_config={"published_at": DATE_COL, "source": "Source", "brands": "Brand",
                                    "sentiment": "Sentiment", "content": "Content",
                                    "interactions": "Interactions", "url": LINK_COL})
