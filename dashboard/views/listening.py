"""SOCIAL LISTENING – what people SAY: volume, SOV, sentiment, product keywords, ranking, posts."""
from __future__ import annotations

from datetime import timedelta

import design as d
import pandas as pd
import plotly.express as px
import streamlit as st
from ui import SERIES, SOURCE_LABELS, ViewContext, brand_list, nsr_of, style
from views import insight

from vnlisten.analytics import keywords, metrics
from vnlisten.domain.models import Severity

SENT = {"positive": ("Positive", "rgba(47,91,234,0.1)", "#1f43c4"), "neutral": ("Neutral", "rgba(91,100,120,0.12)", d.INK2),
        "negative": ("Negative", "rgba(229,72,77,0.12)", d.DOWN)}


def render(ctx: ViewContext) -> None:
    tax, cur, prev = ctx.tax, ctx.cur, ctx.prev
    crumb = f"{tax.name} · {ctx.period_label}" + (f" · search “{ctx.query}”" if ctx.query else "")
    st.markdown(d.header(crumb, "Social Listening", "listening", d.BLUE), unsafe_allow_html=True)

    alerts_24h = [a for a in ctx.repo.recent_alerts(100, tax.industry) if a.created_at > ctx.now - timedelta(days=1)]
    high = sum(a.severity is Severity.HIGH for a in alerts_24h)
    growth = (len(cur) - len(prev)) / len(prev) if len(prev) else None
    nsr_now, nsr_prev = nsr_of(cur), nsr_of(prev)
    neg_now, neg_prev = int((cur["sentiment"] == "negative").sum()), int((prev["sentiment"] == "negative").sum())
    st.markdown(d.kpis(
        {"label": "Mentions", "value": f"{len(cur):,}", "note": "vs previous period of equal length",
         "pill": (("▲ " if growth >= 0 else "▼ ") + d.signed(growth)) if growth is not None else "", "pill_good": (growth or 0) >= 0},
        [{"label": "Interactions", "value": _short(int(cur["interactions"].sum())), "icon": "heart", "color": d.PINK,
          "note": "likes + comments + shares"},
         {"label": "Net sentiment (NSR)", "value": d.signed(nsr_now), "icon": "smile", "color": d.GREEN,
          "note": f"{'▲' if nsr_now >= nsr_prev else '▼'} {abs(round((nsr_now - nsr_prev) * 100))} pts" if len(prev) else "",
          "note_ink": d.UP if nsr_now >= nsr_prev else d.DOWN},
         {"label": "Negative posts", "value": f"{neg_now:,}", "icon": "warn", "color": d.ORANGE,
          "note": (f"▲ +{neg_now - neg_prev} – watch" if neg_now > neg_prev else f"▼ {neg_now - neg_prev}") if len(prev) else "",
          "note_ink": d.DOWN if neg_now > neg_prev else d.UP},
         {"label": "Alerts (24h)", "value": str(len(alerts_24h)), "icon": "bell", "color": d.AMBER,
          "note": f"▲ {high} high severity" if high else "No high-severity alert", "note_ink": d.DOWN if high else d.FLAT}]),
        unsafe_allow_html=True)

    brand = metrics.entity_metrics(cur, "brands")
    brand["name"] = brand["entity"].map(tax.brand_name)

    left, right = st.columns([3, 2], gap="medium")
    with left, st.container(border=True):
        st.markdown(d.title("Mentions over time"), unsafe_allow_html=True)
        picked = st.multiselect("Compare brands", brand["name"].tolist(), default=brand["name"].head(3).tolist(),
                                max_selections=5, label_visibility="collapsed")
        tl = metrics.timeline(cur, "h" if ctx.days == 1 else "D")
        tl["name"] = tl["entity"].map(tax.brand_name)
        tl = tl[tl["name"].isin(picked)]
        fig = px.line(tl, x="time", y="mentions", color="name", markers=True, line_shape="spline",
                      category_orders={"name": picked}, color_discrete_sequence=SERIES,
                      labels={"time": "", "mentions": "Mentions", "name": ""})
        st.plotly_chart(style(fig, 320), width="stretch")
    with right, st.container(border=True):
        st.markdown(d.title("Share of voice"), unsafe_allow_html=True)
        top = brand.head(8)
        st.markdown(d.hbars([{"label": r.name, "value": f"{r.sov:.0%}", "ratio": r.sov / top["sov"].max(),
                              "color": d.BLUE, "title": f"{r.name}: {r.mentions} mentions"} for r in top.itertuples()],
                            110, 48, gradient=True), unsafe_allow_html=True)

    _product_keywords(ctx, brand)

    left, right = st.columns([3, 2], gap="medium")
    with left, st.container(border=True):
        st.markdown(d.title("Brand ranking", "Score = 45% mentions · 35% interactions · 20% NSR"), unsafe_allow_html=True)
        growth_df = metrics.buzz_growth(ctx.df_all, ctx.now, timedelta(days=ctx.days))[["entity", "growth"]]
        ranked = metrics.rank(brand).merge(growth_df, on="entity", how="left").head(10)
        rows = []
        for r in ranked.itertuples():
            g = None if pd.isna(r.growth) else float(r.growth)
            rows.append([f"<b style='color:{d.INK3}'>{r.rank}</b>", f"<b>{d.esc(r.name)}</b>",
                         f"<span style='display:flex;align-items:center;gap:8px'><span style='flex:1;height:8px;border-radius:4px;background:rgba(47,91,234,.08)'>"
                         f"<span class='bar' data-tap style='display:block;height:8px;width:{round(r.score * 100)}%;border-radius:4px;background:{d.BLUE}'></span></span><b>{r.score:.2f}</b></span>",
                         f"{r.mentions:,}", f"{r.sov:.0%}", f"<b style='color:{d.ink(r.nsr)}'>{d.signed(r.nsr)}</b>",
                         f"<b style='color:{d.ink(g or 0)}'>{d.signed(g) if g is not None else '–'}</b>"])
        st.markdown(d.grid([("#", "34px", "l"), ("Brand", "minmax(110px,1.4fr)", "l"), ("Score", "minmax(130px,1.6fr)", "l"),
                            ("Mentions", "80px", "r"), ("SOV", "56px", "r"), ("NSR", "64px", "r"), ("Buzz", "64px", "r")], rows),
                    unsafe_allow_html=True)
    with right:
        insight.render(ctx)

    with st.container(border=True):
        st.markdown(d.title("Latest posts", f"{len(cur):,} posts in this period" + (f" matching “{d.esc(ctx.query)}”" if ctx.query else "")),
                    unsafe_allow_html=True)
        feed = cur.sort_values("published_at", ascending=False).head(15)
        rows = []
        for r in feed.itertuples():
            label, bg, fg = SENT.get(r.sentiment, SENT["neutral"])
            link = f"<a href='{d.esc(r.url)}' target='_blank' style='font-weight:700'>Open</a>" if r.url else ""
            rows.append([f"<span style='color:{d.INK3}'>{r.published_at.tz_convert('Asia/Ho_Chi_Minh'):%d/%m %H:%M}</span>",
                         d.esc(SOURCE_LABELS.get(r.source, r.source)), d.esc((r.title or r.content)[:220]),
                         d.esc(brand_list(tax, r.brands)) or "–", d.pill(label, bg, fg), f"<b>{r.interactions:,}</b>", link])
        st.markdown(d.grid([("Time", "86px", "l"), ("Source", "84px", "l"), ("Post", "minmax(220px,3fr)", "l"),
                            ("Brand", "minmax(90px,1fr)", "l"), ("Tone", "84px", "l"), ("Interact.", "70px", "r"), ("", "48px", "l")],
                           rows, main_col=2), unsafe_allow_html=True)

    market = metrics.marketplace_ranking(ctx.repo.latest_snapshots(tax.industry))
    if not market.empty:
        with st.container(border=True):
            st.markdown(d.title("Marketplace best sellers", "High buzz but low sales → conversion problem"), unsafe_allow_html=True)
            top = market.head(10)
            st.markdown(d.hbars([{"label": r.name[:40], "value": f"{r.sold_count:,}", "ratio": r.sold_count / max(top["sold_count"].max(), 1),
                                  "color": d.ORANGE, "title": f"{r.name} · {r.brand}"} for r in top.itertuples()], 220, 70),
                        unsafe_allow_html=True)


def _product_keywords(ctx: ViewContext, brand) -> None:
    tax = ctx.tax
    with st.container(border=True):
        st.markdown(d.title("Product keywords", "Every keyword people use when they talk about the product. "
                            "<b>Known</b> = industry vocabulary · <b>Discovered</b> = recurring new phrases."), unsafe_allow_html=True)
        top_brand = tax.brand_name(brand["entity"].iloc[0]) if not brand.empty else ""
        with st.form("product_keywords", border=False):
            c1, c2, c3 = st.columns([2, 3, 1], vertical_alignment="bottom")
            brand_text = c1.text_input("Brand", value=top_brand, placeholder="Type any brand, e.g. enfa")
            product_text = c2.text_input("Product", placeholder="Type any product, e.g. enfa A2 (empty = brand-wide)")
            c3.form_submit_button("Find keywords", type="primary", width="stretch")
        lookup = keywords.free_text_keywords(ctx.cur, tax, brand_text, product_text)
        chips = []
        if lookup.brand_id:
            chips.append(f"Brand · {tax.brand_name(lookup.brand_id)}")
        if lookup.product_id:
            chips.append(f"Product · {tax.product_name(lookup.product_id)}")
        note = " · no exact product match, searching post text" if lookup.mode == "text" else ""
        st.markdown(d.wrap(f"<div style='font-size:12px;font-weight:500;color:{d.INK3}'>Matched: "
                           + " ".join(d.pill(c, "#ffffff", d.INK) for c in chips) + f" {lookup.posts:,} posts{note}</div>"),
                    unsafe_allow_html=True)
        kw = lookup.table
        info = tax.brands[lookup.brand_id].info if lookup.brand_id else {}
        sub = ctx.cur[ctx.cur["brands"].map(lambda b: lookup.brand_id in b)] if lookup.brand_id else ctx.cur.iloc[0:0]
        facts = [(k.title(), v) for k, v in info.items()] or [
            ("Category", tax.category_name(tax.category_of_brand(lookup.brand_id)) if lookup.brand_id else "–"),
            ("Posts", f"{lookup.posts:,}"), ("NSR", d.signed(nsr_of(sub)) if len(sub) else "–"),
            ("Top source", SOURCE_LABELS.get(sub["source"].mode().iat[0], "–") if len(sub) else "–")]
        st.markdown(d.facts(facts), unsafe_allow_html=True)
        left, right = st.columns([2, 3], gap="medium")
        with left:
            st.markdown(d.keyword_cloud(kw.head(32)), unsafe_allow_html=True)
        with right:
            rows = []
            for r in kw.head(12).itertuples():
                known = r.type == "Known"
                rows.append([f"<b>{d.esc(r.keyword)}</b>",
                             d.pill(r.type, "rgba(47,91,234,0.1)" if known else "rgba(232,89,12,0.12)", "#1f43c4" if known else "#9a3c12"),
                             f"<b>{r.mentions}</b>", f"{r.share:.0%}", f"<b style='color:{d.ink(r.nsr)}'>{d.signed(r.nsr)}</b>",
                             f"<span style='color:{d.INK2}'>{d.esc(r.example[:140])}</span>"])
            st.markdown(d.grid([("Keyword", "minmax(96px,1.1fr)", "l"), ("Type", "92px", "l"), ("Posts", "54px", "r"),
                                ("Share", "58px", "r"), ("NSR", "62px", "r"), ("Example post", "minmax(150px,2.4fr)", "l")], rows, 0),
                        unsafe_allow_html=True)


def _short(n: int) -> str:
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.1f}K" if n >= 1e4 else f"{n:,}"
