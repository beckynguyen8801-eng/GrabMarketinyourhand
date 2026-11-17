"""MARKETING RESEARCH: what brands are DOING (campaigns, online/offline activity) and what the market CARES about
(keywords, search suggestions, rising phrases)."""
from __future__ import annotations

from datetime import timedelta

import plotly.express as px
import streamlit as st
from ui import (
    CHANNEL_COLORS, MAGNITUDE, SEQUENTIAL, SOURCE_LABELS, Kpi, ViewContext, brand_list, kpi_row, pct_delta, section,
    style,
)
from views import insight

from vnlisten.analytics import research
from vnlisten.domain.models import Tier
from vnlisten.pipeline.activity import activity_name, activity_short


def render(ctx: ViewContext) -> None:
    tax, cur = ctx.tax, ctx.cur
    window = timedelta(days=ctx.days)
    campaign_cur = cur[cur["activities"].map(len) > 0]
    campaign_prev = ctx.prev[ctx.prev["activities"].map(len) > 0]
    summary = research.activity_summary(cur)
    total_act = int(summary["mentions"].sum())
    offline = int(summary.loc[summary["channel"] == "offline", "mentions"].sum())
    hashtags = research.top_hashtags(cur, 30)
    suggestions = research.suggestion_table(ctx.repo.suggestion_history(tax.industry))
    active_brands = len({b for lst in campaign_cur["brands"] for b in lst})

    kpi_row([
        Kpi("Marketing activity posts", f"{len(campaign_cur):,}", pct_delta(len(campaign_cur), len(campaign_prev)),
            len(campaign_cur) >= len(campaign_prev) if len(campaign_prev) else None),
        Kpi("Brands running activities", f"{active_brands} / {len(tax.brands)}"),
        Kpi("Offline share", f"{offline / total_act:.0%}" if total_act else "–"),
        Kpi("Campaign hashtags", str(len(hashtags))),
        Kpi("New search suggestions", str(int(suggestions["is_new"].sum()) if not suggestions.empty else 0)),
    ])

    tab_campaign, tab_keyword, tab_trend, tab_insight = st.tabs(
        ["Campaigns & activities", "Keywords", "Trends", "Insights"])

    with tab_campaign:
        left, right = st.columns([2, 3])
        with left, section("Activity types"):
            s = summary.sort_values("mentions")
            s["Channel"] = s["channel"].str.capitalize()
            fig = px.bar(s, x="mentions", y="name", color="Channel", orientation="h", text="mentions",
                         color_discrete_map=CHANNEL_COLORS, labels={"mentions": "Posts", "name": ""},
                         hover_data={"interactions": ":,", "brands": True})
            fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
            fig = style(fig, 360)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
            st.plotly_chart(fig, width="stretch")
        with right, section("Brand × activity"):
            matrix = research.activity_matrix(cur)
            if matrix.empty:
                st.caption("No activity data in this period.")
            else:
                matrix["brand"] = matrix["brand"].map(tax.brand_name)
                matrix["activity"] = matrix["activity"].map(activity_short)
                top_brands = matrix.groupby("brand")["mentions"].sum().nlargest(12).index
                pivot = (matrix[matrix["brand"].isin(top_brands)]
                         .pivot_table(index="brand", columns="activity", values="mentions", fill_value=0)
                         .reindex(top_brands))
                fig = px.imshow(pivot, color_continuous_scale=SEQUENTIAL, aspect="auto", text_auto=True,
                                labels={"color": "Posts", "x": "", "y": ""})
                fig.update_xaxes(side="top", tickangle=-35)
                fig.update_coloraxes(showscale=False)
                st.plotly_chart(style(fig, 360), width="stretch")

        left, right = st.columns([3, 2])
        with left, section("Online vs offline by brand"):
            split = research.channel_split(cur).head(12)
            split["brand"] = split["brand"].map(tax.brand_name)
            long = split.melt(id_vars="brand", value_vars=["online", "offline"], var_name="Channel", value_name="n")
            long["Channel"] = long["Channel"].str.capitalize()
            fig = px.bar(long, x="n", y="brand", color="Channel", orientation="h",
                         color_discrete_map=CHANNEL_COLORS,
                         category_orders={"brand": split["brand"].tolist()}, labels={"n": "Posts", "brand": ""})
            st.plotly_chart(style(fig, 380), width="stretch")
        with right, section("Campaign hashtags"):
            tags = hashtags.copy()
            tags["brand"] = tags["brand"].map(tax.brand_name)
            st.dataframe(tags[["hashtag", "brand", "mentions", "interactions", "first_seen"]], hide_index=True,
                         width="stretch", height=380,
                         column_config={"hashtag": "Hashtag", "brand": "Brand", "mentions": "Posts",
                                        "interactions": st.column_config.NumberColumn("Interactions", format="%d"),
                                        "first_seen": st.column_config.DatetimeColumn("First seen", format="DD/MM")})

        with section("Top campaign posts"):
            posts = campaign_cur.sort_values("interactions", ascending=False).head(50).copy()
            posts["brands"] = posts["brands"].map(lambda b: brand_list(tax, b))
            posts["activities"] = posts["activities"].map(lambda a: ", ".join(activity_name(x) for x in a))
            posts["source"] = posts["source"].map(lambda s: SOURCE_LABELS.get(s, s))
            st.dataframe(posts[["published_at", "source", "brands", "activities", "content", "interactions", "url"]],
                         hide_index=True, width="stretch",
                         column_config={
                             "published_at": st.column_config.DatetimeColumn("Published", format="DD/MM HH:mm"),
                             "source": "Source", "brands": "Brand", "activities": "Activity", "content": "Content",
                             "interactions": "Interactions",
                             "url": st.column_config.LinkColumn("Link", display_text="Open")})

    with tab_keyword:
        left, right = st.columns([3, 2])
        with left, section("Tracked keyword performance",
                           "Mentions collected per tracked query – not search volume."):
            perf = research.keyword_performance(ctx.df_all, ctx.now, window)
            tracked = {q.keyword for q in tax.tracking_queries(Tier.DAILY)}
            tracked |= {kw for _, kw in ctx.repo.watchlist(tax.industry)}
            st.dataframe(perf[perf["keyword"].isin(tracked)], hide_index=True, width="stretch",
                         column_config={"keyword": "Keyword", "current": "This period", "previous": "Previous",
                                        "growth": st.column_config.NumberColumn("Growth", format="percent"),
                                        "nsr": st.column_config.NumberColumn("NSR", format="percent")})
        with right, section("What people search for (Google)",
                            "Google Autocomplete rank – not search volume."):
            if suggestions.empty:
                st.info("No data yet. Run `vnlisten daily` to fetch Google Autocomplete suggestions.")
            else:
                seed = st.selectbox("Seed keyword", suggestions["seed"].unique())
                sub = suggestions[suggestions["seed"] == seed].copy()
                sub["is_new"] = sub["is_new"].map({True: "New", False: ""})
                st.dataframe(sub[["rank", "suggestion", "is_new"]], hide_index=True, width="stretch",
                             column_config={"rank": "#", "suggestion": "Suggestion", "is_new": ""})

    with tab_trend, section("Rising phrases",
                            f"{ctx.period_label} vs the previous {ctx.days} days. "
                            "Lift = (this period + 1) / (previous + 1)."):
        trends = research.trending_phrases(ctx.df_all, ctx.now, window, limit=12)
        if trends.empty:
            st.caption("Not enough data to detect trends.")
        else:
            t = trends.sort_values("lift")
            fig = px.bar(t, x="lift", y="phrase", orientation="h", text=t["lift"].map("×{:.1f}".format),
                         color_discrete_sequence=[MAGNITUDE], labels={"lift": "Lift", "phrase": ""},
                         hover_data={"current": True, "previous": True})
            fig.update_traces(textposition="outside", cliponaxis=False, marker_cornerradius=6)
            st.plotly_chart(style(fig, 420), width="stretch")

    with tab_insight:
        insight.render(ctx)
