"""MARKETING RESEARCH – what brands DO (activities, campaigns, online vs offline) and what the market CARES about
(hospitals, rising phrases, Google search suggestions)."""
from __future__ import annotations

from datetime import timedelta

import design as d
import plotly.express as px
import streamlit as st
from ui import SEQUENTIAL, SOURCE_LABELS, ViewContext, brand_list, style

from vnlisten.analytics import keywords, metrics, research
from vnlisten.pipeline.activity import activity_channel, activity_name, activity_short

SEGMENTS = {"bv_cong_vn": ("Public · VN", d.BLUE, "#1f43c4"), "bv_tu_vn": ("Private · VN", d.GREEN, "#05603a"),
            "bv_chau_a": ("Asia", d.ORANGE, "#9a3c12"), "bv_chau_au": ("Europe", d.VIOLET, "#4a3aa7")}


def render(ctx: ViewContext) -> None:
    tax, cur = ctx.tax, ctx.cur
    crumb = f"{tax.name} · {ctx.period_label}" + (f" · search “{ctx.query}”" if ctx.query else "")
    st.markdown(d.header(crumb, "Marketing Research", "research", d.ORANGE), unsafe_allow_html=True)

    window = timedelta(days=ctx.days)
    act_cur = cur[cur["activities"].map(len) > 0]
    act_prev = ctx.prev[ctx.prev["activities"].map(len) > 0]
    summary = research.activity_summary(cur)
    total = int(summary["mentions"].sum())
    offline = int(summary.loc[summary["channel"] == "offline", "mentions"].sum())
    hashtags = research.top_hashtags(cur, 30)
    sugg = research.suggestion_table(ctx.repo.suggestion_history(tax.industry))
    active = len({b for lst in act_cur["brands"] for b in lst})
    g = (len(act_cur) - len(act_prev)) / len(act_prev) if len(act_prev) else None
    new_sugg = int(sugg["is_new"].sum()) if not sugg.empty else 0
    st.markdown(d.kpis(
        {"label": "Marketing activity posts", "value": f"{len(act_cur):,}", "note": "promotions, events, KOL, livestream…",
         "pill": (("▲ " if g >= 0 else "▼ ") + d.signed(g)) if g is not None else "", "pill_good": (g or 0) >= 0},
        [{"label": "Brands running activities", "value": f"{active} / {len(tax.brands)}", "icon": "users", "color": d.BLUE},
         {"label": "Offline share", "value": f"{offline / total:.0%}" if total else "–", "icon": "pin", "color": d.ORANGE,
          "note": "events, sampling, free check-ups"},
         {"label": "Campaign hashtags", "value": str(len(hashtags)), "icon": "hash", "color": d.PINK},
         {"label": "New search suggestions", "value": str(new_sugg), "icon": "spark", "color": d.GREEN,
          "note": "▲ new on Google Autocomplete" if new_sugg else "Google Autocomplete", "note_ink": d.UP if new_sugg else d.FLAT}]),
        unsafe_allow_html=True)

    if any(c in tax.categories for c in SEGMENTS):
        _hospitals(ctx)

    left, right = st.columns([2, 3], gap="medium")
    with left, st.container(border=True):
        st.markdown(d.title("Activity types") + d.wrap(f"<div style='font-size:12px;font-weight:500;color:{d.INK2};margin:-4px 0 8px'>"
                    f"<b style='color:{d.BLUE}'>■</b> Online &nbsp; <b style='color:{d.ORANGE}'>■</b> Offline</div>"), unsafe_allow_html=True)
        top = int(summary["mentions"].max()) if total else 1
        st.markdown(d.hbars([{"label": r.name, "value": str(r.mentions), "ratio": r.mentions / top,
                              "color": d.ORANGE if r.channel == "offline" else d.BLUE,
                              "title": f"{r.name}: {r.mentions} posts, {r.brands} brands"} for r in summary.itertuples()], 150, 40),
                    unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown(d.title("Brand × activity", "Posts per brand and activity type"), unsafe_allow_html=True)
        matrix = research.activity_matrix(cur)
        if matrix.empty:
            st.markdown(d.wrap(d.empty("No marketing activity detected in this period.")), unsafe_allow_html=True)
        else:
            matrix["brand"] = matrix["brand"].map(tax.brand_name)
            matrix["activity"] = matrix["activity"].map(activity_short)
            topb = matrix.groupby("brand")["mentions"].sum().nlargest(10).index
            pivot = matrix[matrix["brand"].isin(topb)].pivot_table(index="brand", columns="activity", values="mentions",
                                                                   fill_value=0).reindex(topb)
            fig = px.imshow(pivot, color_continuous_scale=SEQUENTIAL, aspect="auto", text_auto=True, labels={"color": "Posts", "x": "", "y": ""})
            fig.update_xaxes(side="top")
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(style(fig, 340), width="stretch")

    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown(d.title("Rising phrases", f"{ctx.period_label} vs the previous {ctx.days} days"), unsafe_allow_html=True)
        trends = research.trending_phrases(ctx.df_all, ctx.now, window, limit=10)
        top = float(trends["lift"].max()) if not trends.empty else 1.0
        st.markdown(d.hbars([{"label": r.phrase, "value": f"×{r.lift:.1f}", "ratio": r.lift / top, "color": d.ORANGE,
                              "color2": "#ffc078", "title": f"{r.phrase}: {r.current} posts (prev {r.previous})"}
                             for r in trends.itertuples()], 170, 56, gradient=True), unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown(d.title("What people search for", "Google Autocomplete rank · not search volume"), unsafe_allow_html=True)
        if sugg.empty:
            st.markdown(d.wrap(d.empty("Collected by the daily run.")), unsafe_allow_html=True)
        else:
            seed = st.selectbox("Seed keyword", sugg["seed"].unique(), label_visibility="collapsed")
            sub = sugg[sugg["seed"] == seed].head(10)
            st.markdown(d.grid([("#", "28px", "l"), ("Suggestion", "1fr", "l"), ("", "64px", "r")],
                               [[f"<b style='color:{d.INK3}'>{r.rank}</b>", d.esc(r.suggestion),
                                 d.pill("▲ New", "#dcfae6", d.UP) if r.is_new else ""] for r in sub.itertuples()]), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(d.title("Campaign hashtags & top activity posts"), unsafe_allow_html=True)
        rows = []
        for r in act_cur.sort_values("interactions", ascending=False).head(12).itertuples():
            acts = ", ".join(activity_name(a) for a in r.activities)
            off = any(activity_channel(a).value == "offline" for a in r.activities)
            link = f"<a href='{d.esc(r.url)}' target='_blank' style='font-weight:700'>Open</a>" if r.url else ""
            rows.append([f"<span style='color:{d.INK3}'>{r.published_at.tz_convert('Asia/Ho_Chi_Minh'):%d/%m}</span>",
                         d.esc(brand_list(tax, r.brands)) or "–",
                         d.pill(acts[:40], "rgba(232,89,12,0.12)" if off else "rgba(47,91,234,0.1)", "#9a3c12" if off else "#1f43c4"),
                         d.esc((r.title or r.content)[:200]), d.esc(SOURCE_LABELS.get(r.source, r.source)), f"<b>{r.interactions:,}</b>", link])
        st.markdown(d.grid([("Date", "52px", "l"), ("Brand", "minmax(90px,1fr)", "l"), ("Activity", "minmax(120px,1.2fr)", "l"),
                            ("Post", "minmax(220px,3fr)", "l"), ("Source", "80px", "l"), ("Interact.", "70px", "r"), ("", "48px", "l")],
                           rows, main_col=3), unsafe_allow_html=True)
        if not hashtags.empty:
            st.markdown(d.wrap("<div style='display:flex;flex-wrap:wrap;gap:8px;margin-top:12px'>" + "".join(
                f"<span class='chip' data-tap style='padding:6px 12px;border-radius:16px;background:#ffffff;border:1px solid rgba(214,51,108,.2);"
                f"font-size:12px;font-weight:700;color:{d.PINK}'>{d.esc(r.hashtag)} <span style='color:{d.INK3};font-weight:500'>· "
                f"{d.esc(tax.brand_name(r.brand)) if r.brand else ''} · {r.interactions:,}</span></span>" for r in hashtags.head(15).itertuples()) + "</div>"),
                unsafe_allow_html=True)


def _hospitals(ctx: ViewContext) -> None:
    tax = ctx.tax
    with st.container(border=True):
        c1, c2 = st.columns([2, 3], vertical_alignment="center")
        c1.markdown(d.title("Hospitals in the conversation", "Public & private hospitals in Vietnam, Asia and Europe"), unsafe_allow_html=True)
        labels = ["All"] + [v[0] for v in SEGMENTS.values()]
        picked = c2.segmented_control("Segment", labels, default="All", label_visibility="collapsed") or "All"
        cats = [c for c, v in SEGMENTS.items() if picked in ("All", v[0])]
        hosp_ids = {b for c in cats for b in tax.brands_in_category(c)}
        m = metrics.entity_metrics(ctx.cur, "brands")
        m = m[m["entity"].isin(hosp_ids)].head(12)
        rows = []
        for r in m.itertuples():
            b = tax.brands[r.entity]
            seg, color, fg = SEGMENTS[tax.category_of_brand(r.entity)]
            info = b.info
            kw = keywords.entity_keywords(ctx.cur, tax, brand_id=r.entity, min_count=1, limit=3)
            rows.append([f"<b>{d.esc(b.name)}</b>", d.pill(seg, d.tint(color, .12), fg),
                         d.esc(", ".join(x for x in (info.get("city"), info.get("country")) if x and x != "Vietnam") or info.get("city", "–")),
                         d.esc(info.get("specialty", "–")), f"<b>{r.mentions:,}</b>", f"<b style='color:{d.ink(r.nsr)}'>{d.signed(r.nsr)}</b>",
                         d.esc(", ".join(kw["keyword"].tolist())) or "–"])
        if not rows:
            st.markdown(d.wrap(d.empty("No hospital mentioned in this period.")), unsafe_allow_html=True)
            return
        st.markdown(d.grid([("Hospital", "minmax(170px,1.8fr)", "l"), ("Segment", "112px", "l"), ("Location", "minmax(90px,1fr)", "l"),
                            ("Specialty", "minmax(120px,1.3fr)", "l"), ("Mentions", "76px", "r"), ("NSR", "60px", "r"),
                            ("Top keywords", "minmax(150px,1.6fr)", "l")], rows, 0), unsafe_allow_html=True)
