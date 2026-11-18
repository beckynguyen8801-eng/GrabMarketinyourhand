"""COMMUNITIES – scan, score, rank and recommend groups / channels for the searched keyword, brand or product."""
from __future__ import annotations

import design as d
import plotly.graph_objects as go
import streamlit as st
from ui import ViewContext, style

from vnlisten.analytics import communities, keywords

COMPONENTS = [("Activity", 25, "Posts per week", d.BLUE, "trend"), ("Engagement", 25, "Avg interactions per post", d.PINK, "heart"),
              ("Relevance", 25, "Share of on-topic posts", d.GREEN, "search"),
              ("Buying intent", 15, "Questions, reviews, price asks", d.ORANGE, "spark"),
              ("Openness", 10, "Public › unknown › private", d.AMBER, "users")]
TIERS = {"High potential": ("rgba(14,159,110,0.14)", "#05603a", d.GREEN), "Worth testing": ("rgba(232,89,12,0.14)", "#9a3c12", d.ORANGE),
         "Monitor": ("rgba(138,147,166,0.18)", d.INK2, "#8a93a6")}
MEDALS = [("linear-gradient(150deg,#fff6d6,#f5b400)", "#5c3d00"), ("linear-gradient(150deg,#ffffff,#c9d1e3)", "#2c3445"),
          ("linear-gradient(150deg,#ffe8d9,#e8590c)", "#ffffff")]


def render(ctx: ViewContext) -> None:
    tax = ctx.tax
    crumb = f"Social Listening › Communities · {tax.name}" + (f" · search “{ctx.query}”" if ctx.query else "")
    st.markdown(d.header(crumb, "Community Radar", "users", d.PINK), unsafe_allow_html=True)

    focus = keywords.matching_entities(tax, ctx.query)[0] if ctx.query else set()
    ranked = communities.rank_communities(ctx.base_cur if ctx.base_cur is not None else ctx.cur, ctx.cur, tax, ctx.days,
                                          focus_brands=focus)
    if ranked.empty:
        with st.container(border=True):
            st.markdown(d.title("No communities yet"), unsafe_allow_html=True)
            st.markdown(d.wrap(d.empty("Communities come from Facebook groups, TikTok and Threads accounts found by the web search "
                                       "(runs inside the daily job) and from posts sent by the VN Listen Capture browser extension. "
                                       "They appear here after the next daily run.")), unsafe_allow_html=True)
        return

    c1, c2 = st.columns([4, 1], vertical_alignment="center")
    types = ["All", *sorted(ranked["type"].unique())]
    picked = c1.segmented_control("Type", types, default="All", label_visibility="collapsed") or "All"
    public_only = c2.toggle("Public only")
    view = ranked if picked == "All" else ranked[ranked["type"] == picked]
    if public_only:
        view = view[view["visibility"] == "public"]

    cards = []
    for i, r in enumerate(view.head(3).itertuples()):
        bg, fg, _ = TIERS[r.tier]
        medal_bg, medal_ink = MEDALS[i]
        link = f"<a href='{d.esc(r.url)}' target='_blank' style='font-size:12px;font-weight:700'>Open community ↗</a>" if r.url else ""
        cards.append(f"""<article class="card" data-tap style="{d.CARD}; padding: 22px; display: flex; flex-direction: column; gap: 12px; min-width: 0;{' background: linear-gradient(150deg,#ffffff 0%,#ffe3ee 100%);' if i == 0 else ''}">
          <div style="display:flex;align-items:center;gap:12px"><span class="tile" style="flex:0 0 44px;height:44px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;color:{medal_ink};background:{medal_bg};box-shadow:inset 0 1px 0 rgba(255,255,255,.9),inset 0 -5px 10px rgba(16,24,40,.12),0 8px 18px rgba(16,24,40,.12)">{i + 1}</span>
          <div style="min-width:0"><div style="font-size:12px;font-weight:500;color:{d.INK3}">{d.esc(r.type)} · {d.esc(r.visibility)}</div><div style="font-size:17px;font-weight:700;line-height:1.3">{d.esc(r.name)}</div></div></div>
          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">{d.pill(r.tier, bg, fg)}<span style="font-size:30px;font-weight:700;letter-spacing:-.03em">{r.score:.2f}</span></div>
          <div style="font-size:12px;line-height:1.6;color:{d.INK2}">{d.esc(r.summary)}</div>
          <div style="display:flex;gap:10px;align-items:flex-start;padding:12px;border-radius:14px;background:{'rgba(214,51,108,.10)' if i == 0 else 'rgba(47,91,234,.06)'}"><span style="flex:0 0 18px">{d.svg('arrow', 18, 2.4)}</span><span style="font-size:13px;font-weight:600;line-height:1.45">{d.esc(r.recommendation)}</span></div>{link}</article>""")
    st.markdown(d.wrap(f'<section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:8px 0 16px">{"".join(cards)}</section>'),
                unsafe_allow_html=True)

    left, right = st.columns([1, 2], gap="medium")
    with left, st.container(border=True):
        st.markdown(d.title("How the score works", "Five signals, weighted for marketing value"), unsafe_allow_html=True)
        st.markdown(d.wrap("".join(
            f'<div class="card" data-tap style="display:flex;align-items:center;gap:12px;padding:12px;margin-bottom:8px;border-radius:16px;background:rgba(47,91,234,.04)">'
            f'{d.tile(icon, color, 40, 13, 20)}<div><div><b style="font-size:14px">{label}</b> <b style="font-size:12px;color:{color}">{w}%</b></div>'
            f'<div style="font-size:12px;font-weight:500;color:{d.INK3};line-height:1.35">{hint}</div></div></div>'
            for label, w, hint, color, icon in COMPONENTS)), unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown(d.title("Relevance × reach", "Top-right = on-topic and engaging → best place to be"), unsafe_allow_html=True)
        fig = go.Figure()
        for tier, (_, _, color) in TIERS.items():
            sub = view[view["tier"] == tier]
            fig.add_trace(go.Scatter(x=sub["relevance"], y=sub["avg_interactions"], mode="markers+text", name=tier,
                                     text=sub["rank"].astype(str), textfont=dict(color="#ffffff", size=11),
                                     marker=dict(color=color, line=dict(color="#ffffff", width=2)),
                                     customdata=sub[["name", "score"]], hovertemplate="%{customdata[0]}<br>score %{customdata[1]:.2f}<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", title="On-topic share")
        fig.update_yaxes(title="Avg interactions / post")
        fig = style(fig, 340)
        for trace in fig.data:  # style() resets marker size – restore bubble size = activity
            sub = view[view["tier"] == trace.name]
            trace.marker.size = (sub["posts_per_week"].clip(lower=1) ** 0.5 * 4 + 22).tolist()
        st.plotly_chart(fig, width="stretch")
        st.markdown(d.wrap('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:6px 14px">' + "".join(
            f'<div class="row" data-tap style="display:flex;align-items:center;gap:8px;padding:4px;border-radius:8px;font-size:12px;font-weight:500;color:{d.INK2}">'
            f'<span style="flex:0 0 20px;height:20px;border-radius:10px;background:{TIERS[r.tier][2]};color:#fff;font-size:10px;font-weight:800;display:flex;align-items:center;justify-content:center">{r.rank}</span>{d.esc(r.name)}</div>'
            for r in view.head(12).itertuples()) + "</div>"), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(d.title("All communities"), unsafe_allow_html=True)
        rows = []
        for r in view.itertuples():
            acc_bg, acc_fg = ("rgba(14,159,110,0.14)", "#05603a") if r.visibility == "public" else ("rgba(245,159,0,0.22)", "#7a4a00")
            link = f" <a href='{d.esc(r.url)}' target='_blank'>↗</a>" if r.url else ""
            rows.append([f"<b style='color:{d.INK3}'>{r.rank}</b>",
                         f"<b>{d.esc(r.name)}</b>{link}<br><span style='font-size:11px;color:{d.INK3}'>{d.esc(r.type)}</span>",
                         d.pill(r.visibility, acc_bg, acc_fg),
                         f"<span style='display:flex;align-items:center;gap:8px'><span style='flex:1;height:8px;border-radius:4px;background:rgba(16,24,40,.06)'>"
                         f"<span class='bar' data-tap style='display:block;height:8px;width:{round(r.score * 100)}%;border-radius:4px;background:{TIERS[r.tier][2]}'></span></span><b>{r.score:.2f}</b></span>",
                         f"{r.posts_per_week:g}", f"{r.relevance:.0%}", f"{r.intent:.0%}",
                         f"<b style='color:{d.ink(r.nsr)}'>{d.signed(r.nsr)}</b>", d.esc(r.recommendation)])
        st.markdown(d.grid([("#", "34px", "l"), ("Community", "minmax(160px,1.6fr)", "l"), ("Access", "76px", "l"),
                            ("Score", "minmax(130px,1.2fr)", "l"), ("Posts/wk", "70px", "r"), ("On-topic", "70px", "r"),
                            ("Intent", "60px", "r"), ("NSR", "60px", "r"), ("Recommendation", "minmax(180px,2fr)", "l")], rows),
                    unsafe_allow_html=True)
