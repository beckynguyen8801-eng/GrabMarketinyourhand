"""Shared UI: theme (Montserrat + glass tone), palette, labels, chart styling, view context.

Typography (Montserrat only):
    Page title ........ ExtraBold 800
    KPI numbers ....... Bold 700
    Section titles .... SemiBold 600
    Labels, nav ....... Medium 500
    Body, tables ...... Regular 400
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
import streamlit as st

from vnlisten.storage.sqlite_repo import SqliteRepository
from vnlisten.taxonomy import Taxonomy

FONT = "Montserrat, system-ui, sans-serif"
INK, INK_2, INK_3 = "#101828", "#3b4459", "#5b6478"
PRIMARY = "#2f5bea"

# Categorical: fixed order (adjacent pairs checked for colour-blind separation)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MAGNITUDE = "#2f5bea"
NEGATIVE = "#e34948"
SEQUENTIAL = ["#eef2ff", "#c7d4fb", "#9db3f6", "#6d8ef0", "#2f5bea", "#1f43c4", "#142c86"]
SENTIMENT_COLORS = {"Positive": "#2f5bea", "Neutral": "#b9bfcc", "Negative": "#e34948"}
CHANNEL_COLORS = {"Online": "#2f5bea", "Offline": "#eb6834"}

SENTIMENT_LABELS = {"positive": "Positive", "neutral": "Neutral", "negative": "Negative"}
SOURCE_LABELS = {"facebook": "Facebook", "tiktok": "TikTok", "youtube": "YouTube", "google_news": "News",
                 "threads": "Threads", "forum": "Forums", "tiki": "Tiki"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
/* Text elements only – a blanket selector would also hit Streamlit's Material icon font
   (icons then render as words like "keyboard_double_arrow_left"). */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th, .stApp [data-baseweb="select"] div,
.stApp [data-baseweb="tag"] span {{
  font-family: {FONT} !important;
}}
.stApp {{ background: linear-gradient(160deg, #f3f5ff 0%, #e4eafd 45%, #d3ddfb 100%) fixed; color: {INK}; }}
h1 {{ font-weight: 800 !important; letter-spacing: -0.02em; color: {INK}; }}
h2, h3 {{ font-weight: 600 !important; letter-spacing: -0.01em; color: {INK}; }}
label, [data-testid="stWidgetLabel"] p, .stTabs button p {{ font-weight: 500 !important; }}
[data-testid="stSidebar"] > div:first-child {{
  background: rgba(255,255,255,0.55); backdrop-filter: blur(18px); border-right: 1px solid rgba(255,255,255,0.7);
}}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
  background: rgba(255,255,255,0.68); backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.85) !important; border-radius: 22px !important;
  box-shadow: 0 8px 28px rgba(47,91,234,0.08);
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stButton button, .stDownloadButton button {{ border-radius: 12px; font-weight: 600; }}
.kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin: 4px 0 8px; }}
.kpi {{ border-radius: 22px; padding: 18px 20px; background: rgba(255,255,255,0.7); backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.9); box-shadow: 0 8px 28px rgba(47,91,234,0.08); }}
.kpi .label {{ font-size: 13px; font-weight: 500; color: {INK_3}; }}
.kpi .value {{ font-size: 30px; font-weight: 700; letter-spacing: -0.02em; color: {INK}; margin: 6px 0 4px; }}
.kpi .delta {{ font-size: 12px; font-weight: 600; }}
.kpi.hero {{ background: linear-gradient(135deg, #2f5bea 0%, #4f86f7 55%, #8cc8fb 100%); border: 0;
  box-shadow: 0 14px 34px rgba(47,91,234,0.32); }}
.kpi.hero .label, .kpi.hero .value, .kpi.hero .delta {{ color: #ffffff; }}
/* Micro-interactions: lift on hover, press on click (tactile feel) */
.kpi, [data-testid="stVerticalBlockBorderWrapper"] {{ transition: transform .18s ease, box-shadow .18s ease; }}
.kpi:hover {{ transform: translateY(-3px); box-shadow: 0 16px 36px rgba(47,91,234,0.16); }}
.stButton button, .stFormSubmitButton button, .stTabs button {{ transition: transform .12s ease, box-shadow .12s ease; }}
.stButton button:hover, .stFormSubmitButton button:hover {{ transform: translateY(-1px); box-shadow: 0 8px 18px rgba(47,91,234,0.25); }}
.stButton button:active, .stFormSubmitButton button:active, .stTabs button:active {{ transform: scale(0.96); }}
.pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: rgba(47,91,234,0.10); color: #1f43c4; margin: 0 6px 6px 0; }}
.info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;
  margin: 4px 0 14px; padding: 12px 14px; border-radius: 16px; background: rgba(47,91,234,0.06); }}
.info-grid div span {{ display: block; font-size: 12px; font-weight: 500; color: {INK_3}; }}
.info-grid div b {{ font-size: 14px; font-weight: 600; color: {INK}; }}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


@dataclass(frozen=True)
class Kpi:
    label: str
    value: str
    delta: str = ""
    good: bool | None = None  # True = green, False = red, None = neutral


def kpi_row(items: list[Kpi]) -> None:
    """KPI cards; the first one is the gradient 'hero' card."""
    cards = []
    for i, k in enumerate(items):
        color = {True: "#067647", False: "#c01c28", None: INK_3}[k.good]
        delta = f'<div class="delta" style="color:{"#ffffff" if i == 0 else color}">{html.escape(k.delta)}</div>'
        cards.append(f'<div class="kpi{" hero" if i == 0 else ""}"><div class="label">{html.escape(k.label)}</div>'
                     f'<div class="value">{html.escape(k.value)}</div>{delta if k.delta else ""}</div>')
    st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)


@dataclass
class ViewContext:
    """Everything a view needs – views never read the sidebar or DB setup themselves."""

    tax: Taxonomy
    repo: SqliteRepository
    now: datetime
    start: date
    end: date
    query: str
    df_all: pd.DataFrame   # current + previous period (same length) for growth metrics
    cur: pd.DataFrame
    prev: pd.DataFrame
    base_cur: pd.DataFrame | None = None  # current period WITHOUT the search filter (community relevance)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def period_label(self) -> str:
        return f"{self.start:%d/%m/%Y} – {self.end:%d/%m/%Y}"


def style(fig, height: int = 340):
    fig.update_layout(
        height=height, margin=dict(l=8, r=48, t=8, b=8), legend_title_text="",
        font=dict(family=FONT, color=INK_2, size=12), hovermode="closest", bargap=0.35,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_family=FONT),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(16,24,40,0.08)")
    fig.update_traces(selector=dict(type="scatter"), line_width=2.5, marker_size=8)
    return fig


def nsr_of(frame: pd.DataFrame) -> float:
    pos, neg = (frame["sentiment"] == "positive").sum(), (frame["sentiment"] == "negative").sum()
    return (pos - neg) / (pos + neg) if pos + neg else 0.0


def brand_list(tax: Taxonomy, ids: list[str]) -> str:
    return ", ".join(tax.brand_name(x) for x in ids)


def pct_delta(cur: float, prev: float) -> str:
    return f"{(cur - prev) / prev:+.0%} vs previous period" if prev else ""


def section(title: str, caption: str = ""):
    """A glass card with a section title. Use as: with section('...'):"""
    box = st.container(border=True)
    box.subheader(title)
    if caption:
        box.caption(caption)
    return box


# ---- Keyword cloud: size & weight = mentions, hue = tone, muted colour = fewer mentions ----
CLOUD_VIVID = {"pos": ["#0e9f6e", "#e8590c", "#b7791f"], "neg": ["#d92d32"], "neu": ["#3b4459"]}
CLOUD_MUTED = {"pos": ["#3f7d66", "#a2593a", "#8a6d32"], "neg": ["#a2484b"], "neu": ["#6b7385"]}
CLOUD_TIERS = [(0.6, 40, 800), (0.35, 28, 700), (0.2, 20, 600), (0.0, 15, 400)]  # (min ratio, px, weight)


def keyword_cloud(kw: pd.DataFrame) -> str:
    """HTML keyword cloud from an entity_keywords table (keyword, mentions, nsr)."""
    if kw.empty:
        return ""
    top = int(kw["mentions"].max())
    words, pos_i = [], 0
    for row in kw.sort_values("mentions", ascending=False).itertuples():
        ratio = row.mentions / top
        tier = next(i for i, (lim, _, _) in enumerate(CLOUD_TIERS) if ratio >= lim)
        _, size, weight = CLOUD_TIERS[tier]
        kind = "pos" if row.nsr > 0.2 else "neg" if row.nsr < -0.2 else "neu"
        palette = (CLOUD_VIVID if tier <= 1 else CLOUD_MUTED)[kind]
        color = palette[pos_i % len(palette)] if kind == "pos" else palette[0]
        pos_i += kind == "pos"
        words.append(f'<span title="{html.escape(row.keyword)} · {row.mentions} posts" '
                     f'style="font-size:{size}px;font-weight:{weight};color:{color}">{html.escape(row.keyword)}</span>')
    ordered: list[str] = []
    for i, w in enumerate(words):  # biggest in the middle
        ordered.insert(0, w) if i % 2 == 0 else ordered.append(w)
    legend = ('<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:14px;padding-top:10px;'
              'border-top:1px solid rgba(16,24,40,.06);font-size:11px;font-weight:500;color:#5b6478">'
              '<span><b style="color:#0e9f6e">●</b><b style="color:#e8590c">●</b><b style="color:#b7791f">●</b> Positive</span>'
              '<span><b style="color:#5b6478">●</b> Neutral</span><span><b style="color:#d92d32">●</b> Negative</span>'
              '<span>Bigger & bolder = more mentions · muted = fewer</span></div>')
    return ('<div style="background:#fff;border-radius:20px;padding:22px;border:1px solid rgba(47,91,234,.12);'
            'height:460px;box-sizing:border-box;display:flex;flex-direction:column">'
            '<div style="flex:1;display:flex;flex-wrap:wrap;align-items:center;align-content:space-evenly;'
            f'justify-content:space-evenly;gap:10px 20px;line-height:1.1;text-align:center">{"".join(ordered)}</div>'
            f'{legend}</div>')
