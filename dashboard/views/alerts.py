"""ALERTS & CRISIS – risk keywords, negative spikes, response playbook, most-shared negative posts."""
from __future__ import annotations

from datetime import timedelta

import design as d
import plotly.express as px
import streamlit as st
from ui import SOURCE_LABELS, ViewContext, brand_list, style

from vnlisten.analytics import metrics
from vnlisten.domain.models import Severity

PLAYBOOK = ["Verify the source, batch numbers and screenshots", "Publish an official statement within 24h",
            "Brief customer care & fanpage admins with one approved answer", "Share a genuine-vs-fake / how-to-use guide",
            "Track the topic daily until mentions return to normal"]


def render(ctx: ViewContext) -> None:
    tax, cur = ctx.tax, ctx.cur
    st.markdown(d.header(f"{tax.name} · {ctx.period_label}", "Alerts & crisis", "bell", d.AMBER), unsafe_allow_html=True)
    alerts = [a for a in ctx.repo.recent_alerts(50, tax.industry) if a.created_at.date() >= ctx.start]

    left, right = st.columns([2, 3], gap="medium")
    with left:
        if not alerts:
            st.markdown(d.wrap(f'<div class="card" data-tap style="{d.CARD}; padding: 22px; display:flex; gap:14px; align-items:center">'
                               f'{d.tile("shield", d.GREEN, 46, 15, 22)}<div><b style="font-size:16px">No alerts</b><div style="font-size:13px;color:{d.INK3}">'
                               f'No risk keyword or negative spike crossed the thresholds in this period.</div></div></div>'), unsafe_allow_html=True)
        for a in alerts[:12]:
            st.markdown(d.alert_card("High" if a.severity is Severity.HIGH else "Medium",
                                     f"{a.created_at.astimezone():%H:%M %d/%m}", a.rule.replace("_", " ").capitalize(), a.title, a.detail),
                        unsafe_allow_html=True)
    with right:
        neg = cur[cur["sentiment"] == "negative"]
        with st.container(border=True):
            st.markdown(d.title("Negative posts over time", "Spikes here are what the alert rules react to"), unsafe_allow_html=True)
            if neg.empty:
                st.markdown(d.wrap(d.empty("No negative posts in this period.")), unsafe_allow_html=True)
            else:
                freq = "h" if ctx.days <= 2 else "D"
                ts = neg.assign(t=neg["published_at"].dt.tz_convert("Asia/Ho_Chi_Minh").dt.floor(freq)).groupby("t").size().reset_index(name="n")
                peak = ts["n"].max()
                ts["color"] = ts["n"].map(lambda v: "Peak" if v >= max(3, peak * .7) else "Normal")
                fig = px.bar(ts, x="t", y="n", color="color", color_discrete_map={"Peak": "#e5484d", "Normal": "rgba(229,72,77,0.35)"},
                             labels={"t": "", "n": "Negative posts", "color": ""})
                fig.update_traces(marker_cornerradius=6)
                st.plotly_chart(style(fig, 260), width="stretch")
        c1, c2 = st.columns(2, gap="medium")
        with c1, st.container(border=True):
            st.markdown(d.title("Risk keywords"), unsafe_allow_html=True)
            risk = metrics.risk_term_counts(cur).head(8)
            top = int(risk["mentions"].max()) if not risk.empty else 1
            st.markdown(d.hbars([{"label": r.term, "value": str(r.mentions), "ratio": r.mentions / top, "color": "#e5484d"}
                                 for r in risk.itertuples()], 100, 36), unsafe_allow_html=True)
        with c2, st.container(border=True):
            st.markdown(d.title("Response playbook"), unsafe_allow_html=True)
            for i, step in enumerate(PLAYBOOK):
                st.checkbox(step, key=f"playbook-{i}")

    with st.container(border=True):
        st.markdown(d.title("Most-shared negative posts"), unsafe_allow_html=True)
        rows = []
        for r in cur[cur["sentiment"] == "negative"].sort_values("interactions", ascending=False).head(12).itertuples():
            link = f"<a href='{d.esc(r.url)}' target='_blank' style='font-weight:700'>Open</a>" if r.url else ""
            rows.append([f"<span style='color:{d.INK3}'>{r.published_at.tz_convert('Asia/Ho_Chi_Minh'):%d/%m %H:%M}</span>",
                         d.esc(SOURCE_LABELS.get(r.source, r.source)), d.esc((r.title or r.content)[:220]),
                         d.esc(brand_list(tax, r.brands)) or "–",
                         " ".join(d.pill(t, "rgba(229,72,77,.12)", d.DOWN) for t in r.risk_terms[:3]) or "–", f"<b>{r.interactions:,}</b>", link])
        st.markdown(d.grid([("Time", "86px", "l"), ("Source", "80px", "l"), ("Post", "minmax(220px,3fr)", "l"), ("Brand", "minmax(90px,1fr)", "l"),
                            ("Risk keywords", "minmax(120px,1.2fr)", "l"), ("Interact.", "70px", "r"), ("", "48px", "l")], rows, main_col=2),
                    unsafe_allow_html=True)
