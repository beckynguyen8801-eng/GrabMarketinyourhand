"""HTML building blocks taken from the approved canvas design (design/source/kit.py), filled with real data.

Streamlit renders them with st.markdown(..., unsafe_allow_html=True). No scripts: hover / press feedback is
pure CSS so it also works inside Streamlit. Charts stay Plotly (hover tooltips) inside the same glass cards.
"""
from __future__ import annotations

import html
from urllib.parse import urlencode

import pandas as pd

FONT = "Montserrat, system-ui, sans-serif"
INK, INK2, INK3 = "#101828", "#3b4459", "#5b6478"
UP, DOWN, FLAT = "#067647", "#c01c28", "#5b6478"
BLUE, PINK, ORANGE, AMBER, GREEN, VIOLET = "#2f5bea", "#d6336c", "#e8590c", "#c27c00", "#0e9f6e", "#6250d6"
RGB = {BLUE: "47,91,234", PINK: "214,51,108", ORANGE: "232,89,12", AMBER: "245,159,0", GREEN: "14,159,110",
       VIOLET: "98,80,214", "#e5484d": "229,72,77"}

MODULES = [  # key, label, icon, colour
    ("listening", "Social Listening", "listening", BLUE),
    ("communities", "Communities", "users", PINK),
    ("research", "Marketing Research", "research", ORANGE),
    ("alerts", "Alerts", "bell", AMBER),
]

ICONS = {
    "listening": '<circle cx="12" cy="12" r="2.2"></circle><path d="M8.2 8.2a5.4 5.4 0 0 0 0 7.6M15.8 15.8a5.4 5.4 0 0 0 0-7.6M5.2 5.2a9.6 9.6 0 0 0 0 13.6M18.8 18.8a9.6 9.6 0 0 0 0-13.6"></path>',
    "research": '<circle cx="10.5" cy="10.5" r="6"></circle><path d="m15 15 5 5M10.5 7.5v6M7.5 10.5h6"></path>',
    "users": '<circle cx="9" cy="8.5" r="3.2"></circle><path d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5"></path><circle cx="16.8" cy="9.5" r="2.5"></circle><path d="M16.5 14c2.2 0 3.8 1.5 4.3 4"></path>',
    "bell": '<path d="M6.5 9.5a5.5 5.5 0 0 1 11 0c0 5.5 2.5 7.5 2.5 7.5H4s2.5-2 2.5-7.5"></path><path d="M10.2 20.5a2 2 0 0 0 3.6 0"></path>',
    "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"></path>',
    "smile": '<circle cx="12" cy="12" r="8.5"></circle><path d="M8.5 14c.9 1.3 2.1 2 3.5 2s2.6-.7 3.5-2M9 9.5h.01M15 9.5h.01"></path>',
    "warn": '<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0"></path>',
    "pin": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"></path><circle cx="12" cy="10" r="2.4"></circle>',
    "hash": '<path d="M9 4 7 20M17 4l-2 16M4.5 9h16M3.5 15h16"></path>',
    "spark": '<path d="M12 3.5 13.9 9 19.5 10.5 13.9 12.4 12 18 10.1 12.4 4.5 10.5 10.1 9z"></path>',
    "pulse": '<path d="M3 12h3l3-7 4 14 3-7h5"></path>',
    "trend": '<path d="M3 17 9 11l4 4 8-8M15 7h6v6"></path>',
    "search": '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"></path>',
    "shield": '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"></path><path d="m9 12 2 2 4-4"></path>',
    "building": '<path d="M4 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16M16 9h2a2 2 0 0 1 2 2v10M8 7h4M8 11h4M8 15h4M3 21h18"></path>',
}

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
/* Text elements only – a blanket selector would also hit Streamlit's Material icon font */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th, .stApp [data-baseweb="select"] div,
.stApp [data-baseweb="tag"] span, .vl { font-family: Montserrat, system-ui, sans-serif !important; }
.stApp { background: linear-gradient(160deg, #f3f5ff 0%, #e4eafd 45%, #d3ddfb 100%) fixed; color: #101828; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1400px; }
[data-testid="stSidebar"] > div:first-child { background: rgba(255,255,255,0.62); backdrop-filter: blur(18px);
  border-right: 1px solid rgba(255,255,255,0.9); }
[data-testid="stSidebar"] label p { font-size: 12px !important; font-weight: 500 !important; color: #5b6478 !important; }
/* Glass cards = Streamlit bordered containers */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
  background: rgba(255,255,255,0.74); backdrop-filter: blur(14px); border: 1px solid rgba(255,255,255,0.95) !important;
  border-radius: 24px !important; box-shadow: 0 10px 30px rgba(47,91,234,0.08); }
.stButton button, .stFormSubmitButton button { border-radius: 14px; font-weight: 600; }
/* ---- One interaction language: lift / brighten on hover, squish on press ---- */
.vl [data-tap], .stButton button, .stFormSubmitButton button, .vl a.nav {
  transition: transform .16s cubic-bezier(.3,.7,.4,1.5), box-shadow .16s ease, filter .16s ease, background-color .16s ease; }
.vl [data-tap]:active, .stButton button:active, .stFormSubmitButton button:active, .vl a.nav:active { transform: scale(.96); }
.stButton button:hover, .stFormSubmitButton button:hover { transform: translateY(-1px); }
.vl .card[data-tap]:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(47,91,234,.16); }
.vl .row[data-tap]:hover { background: rgba(47,91,234,.05); }
.vl .bar[data-tap] { transform-origin: left center; }
.vl .bar[data-tap]:hover { filter: brightness(1.08) saturate(1.2); transform: scaleY(1.4); }
.vl .chip[data-tap]:hover { transform: translateY(-1px); box-shadow: 0 6px 14px rgba(47,91,234,.14); }
.vl .word[data-tap]:hover { transform: scale(1.08); }
.vl .tile { transition: transform .22s cubic-bezier(.3,.7,.4,1.6); }
.vl [data-tap]:hover .tile, .vl a.nav:hover .tile { transform: rotate(-8deg) scale(1.08); }
.vl a.nav:hover { background: rgba(255,255,255,.8); }
.vl a { text-decoration: none; }
/* Responsive grid tables: become stacked cards on phones */
.vl .gt-head, .vl .gt-row { display: grid; grid-template-columns: var(--cols); gap: 10px; align-items: center; }
.vl .gt-head { padding: 8px 10px; font-size: 12px; font-weight: 500; color: #5b6478; border-bottom: 1px solid rgba(16,24,40,.08); }
.vl .gt-row { padding: 11px 10px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,.05); font-size: 13px; line-height: 1.45; }
.vl .r { text-align: right; }
@media (max-width: 760px) {
  .vl .gt-head { display: none; }
  .vl .gt-row { display: flex; flex-wrap: wrap; gap: 4px 14px; }
  .vl .gt-row > span { flex: 0 1 auto; text-align: left !important; }
  .vl .gt-row > span.main { flex: 1 1 100%; font-weight: 700; }
  .vl .gt-row > span[data-label]:not(.main)::before { content: attr(data-label) " · "; color: #5b6478; font-weight: 500; }
  .vl .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
  .vl .kpi-card { flex-direction: column; align-items: flex-start !important; }
  .vl h1 { font-size: 30px !important; }
}
</style>"""

CARD = ("border-radius: 24px; background: rgba(255,255,255,0.74); border: 1px solid rgba(255,255,255,0.95); "
        "box-shadow: 0 10px 30px rgba(47,91,234,0.08)")


def esc(v) -> str:
    return html.escape(str(v))


def svg(name: str, size: int = 20, width: float = 2.5) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def tint(color: str, a: float) -> str:
    return f"rgba({RGB.get(color, '47,91,234')},{a})"


def tile(icon: str, color: str, size: int = 44, radius: int = 14, isz: int = 22, strong: bool = False) -> str:
    t = 0.32 if strong else 0.2
    return (f'<span class="tile" style="flex: 0 0 {size}px; width: {size}px; height: {size}px; border-radius: {radius}px; '
            f'display: inline-flex; align-items: center; justify-content: center; color: {color}; '
            f'background: linear-gradient(150deg, #ffffff 0%, {tint(color, t)} 100%); border: 1px solid rgba(255,255,255,0.95); '
            f'box-shadow: inset 0 1px 0 #ffffff, inset 0 -5px 10px {tint(color, .18)}, 0 8px 18px {tint(color, t)}">'
            f'{svg(icon, isz)}</span>')


def wrap(inner: str) -> str:
    """Every HTML block goes through here so the .vl scoped styles apply."""
    return f'<div class="vl" style="font-family: {FONT}; color: {INK}">{inner}</div>'


def signed(n: float, suffix: str = "%", digits: int = 0) -> str:
    v = round(n * 100, digits) if suffix == "%" else n
    return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):g}{suffix}"


def ink(n: float) -> str:
    return UP if n > 0 else DOWN if n < 0 else FLAT


# ------------------------------------------------------------------ navigation
def logo() -> str:
    return wrap(f"""<div style="display: flex; align-items: center; gap: 12px; margin: 4px 0 10px">
      <span class="tile" style="flex: 0 0 42px; height: 42px; border-radius: 13px; display: flex; align-items: center; justify-content: center; color: #ffffff; background: linear-gradient(135deg, {BLUE} 0%, #8cc8fb 100%); box-shadow: 0 8px 20px rgba(47,91,234,0.3)">{svg('pulse', 22)}</span>
      <div><div style="font-size: 18px; font-weight: 800; letter-spacing: -0.02em">VN Listen</div><div style="font-size: 11px; font-weight: 500; color: {INK3}">Listening &amp; research</div></div></div>""")


def nav(active: str, params: dict[str, str], alerts: int = 0) -> str:
    items = []
    for key, label, icon, color in MODULES:
        on = key == active
        href = "?" + urlencode({**params, "module": key})
        badge = (f'<span style="margin-left: auto; min-width: 24px; height: 22px; padding: 0 7px; border-radius: 11px; '
                 f'background: #e5484d; color: #ffffff; font-size: 12px; font-weight: 700; display: inline-flex; '
                 f'align-items: center; justify-content: center">{alerts}</span>') if key == "alerts" and alerts else ""
        items.append(
            f'<a class="nav" href="{esc(href)}" target="_self" style="display: flex; align-items: center; gap: 12px; '
            f'min-height: 52px; padding: 0 10px; border-radius: 16px; color: {INK if on else INK2}; '
            f'background: {"#ffffff" if on else "transparent"}; font-size: 14px; font-weight: {700 if on else 500}; '
            f'box-shadow: {"0 10px 24px " + tint(color, .16) if on else "none"}">'
            f'{tile(icon, color, 36, 12, 20, strong=on)}<span style="flex: 1">{label}</span>{badge}</a>')
    return wrap(f'<nav aria-label="Modules" style="display: flex; flex-direction: column; gap: 6px; margin: 6px 0 14px">'
                f'<div style="font-size: 12px; font-weight: 500; color: {INK3}">Module</div>{"".join(items)}</nav>')


def status_card(text: str, sub: str) -> str:
    return wrap(f'<div style="margin-top: 14px; padding: 14px; border-radius: 16px; background: rgba(47,91,234,0.07); '
                f'font-size: 12px; line-height: 1.6; color: {INK2}"><div style="font-weight: 600; color: {INK}">{esc(text)}</div>{esc(sub)}</div>')


def header(crumb: str, title: str, icon: str, color: str) -> str:
    return wrap(f"""<header style="display: flex; align-items: center; gap: 16px; margin-bottom: 8px">
      {tile(icon, color, 56, 18, 28)}
      <div style="min-width: 0"><div style="font-size: 13px; font-weight: 500; color: {INK3}; line-height: 1.5">{esc(crumb)}</div>
      <h1 style="margin: 2px 0 0; padding: 0; font-size: 40px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1">{esc(title)}</h1></div>
    </header>""")


# ------------------------------------------------------------------ KPI
def kpis(hero: dict, cards: list[dict]) -> str:
    """hero: label, value, pill, pill_good, note · cards: label, value, note, note_ink, icon, color."""
    pill_bg, pill_ink = ("#dcfae6", UP) if hero.get("pill_good", True) else ("#fde2e2", DOWN)
    pill = (f'<span style="height: 26px; padding: 0 10px; border-radius: 13px; background: {pill_bg}; color: {pill_ink}; '
            f'font-size: 12px; font-weight: 700; display: inline-flex; align-items: center">{esc(hero["pill"])}</span>') if hero.get("pill") else ""
    hero_html = f"""<div class="card" data-tap style="flex: 1 1 300px; min-height: 188px; min-width: 0; border-radius: 24px; padding: 24px 26px; background: linear-gradient(135deg, {BLUE} 0%, #4f86f7 55%, #8cc8fb 100%); color: #ffffff; box-shadow: 0 16px 36px rgba(47,91,234,0.32); display: flex; flex-direction: column; justify-content: center; gap: 8px; position: relative; overflow: hidden">
      <div style="font-size: 14px; font-weight: 500; opacity: .92">{esc(hero['label'])}</div>
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px"><span style="font-size: 44px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1">{esc(hero['value'])}</span>{pill}</div>
      <div style="font-size: 12px; font-weight: 500; opacity: .92">{esc(hero.get('note', ''))}</div>
      <svg viewBox="0 0 200 40" style="position: absolute; right: 0; bottom: 8px; width: 50%; height: 44px" aria-hidden="true"><path d="M0 34 C 25 34, 30 22, 55 26 S 90 12, 110 20 S 150 4, 200 8" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="2.5" stroke-linecap="round"></path></svg></div>"""
    cells = "".join(f"""<div class="card kpi-card" data-tap style="{CARD}; border-radius: 22px; padding: 18px 20px; display: flex; align-items: center; gap: 14px; min-width: 0">
        {tile(c['icon'], c['color'], 46, 15, 22)}
        <div style="flex: 1; min-width: 0"><div style="font-size: 13px; font-weight: 500; color: {INK3}; line-height: 1.35">{esc(c['label'])}</div>
        <div style="font-size: 12px; font-weight: {700 if c.get('note_ink', FLAT) != FLAT else 500}; color: {c.get('note_ink', FLAT)}; line-height: 1.35; margin-top: 4px">{esc(c.get('note', ''))}</div></div>
        <div style="font-size: 28px; font-weight: 700; letter-spacing: -0.03em; white-space: nowrap">{esc(c['value'])}</div></div>""" for c in cards)
    return wrap(f"""<section aria-label="Key metrics" style="display: flex; flex-wrap: wrap; gap: 16px; align-items: stretch; margin: 6px 0 18px">{hero_html}
      <div class="kpi-grid" style="flex: 2 1 560px; min-width: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 16px">{cells}</div></section>""")


# ------------------------------------------------------------------ blocks
def title(text: str, sub: str = "") -> str:
    s = f'<h2 style="margin: 0; padding: 0; font-size: 18px; font-weight: 600; line-height: 1.3">{esc(text)}</h2>'
    if sub:
        s += f'<div style="font-size: 12px; font-weight: 500; color: {INK3}; line-height: 1.5; margin-top: 4px">{sub}</div>'
    return wrap(f'<div style="margin-bottom: 10px">{s}</div>')


def hbars(rows: list[dict], label_w: int = 110, value_w: int = 52, gradient: bool = False) -> str:
    """rows: label, value (str), ratio (0..1), color, title."""
    out = []
    for r in rows:
        fill = f"linear-gradient(90deg, {r['color']}, {r.get('color2', '#8cc8fb')})" if gradient else r["color"]
        out.append(f"""<div class="row" data-tap title="{esc(r.get('title', r['label']))}" style="display: grid; grid-template-columns: {label_w}px minmax(0, 1fr) {value_w}px; align-items: center; gap: 12px; padding: 4px 6px; margin: 0 -6px; border-radius: 10px">
          <span style="font-size: 13px; font-weight: 500; color: {INK2}; line-height: 1.3">{esc(r['label'])}</span>
          <span style="height: 12px; border-radius: 6px; background: rgba(47,91,234,0.07)"><span class="bar" data-tap style="display: block; height: 12px; width: {max(2, round(r['ratio'] * 100))}%; border-radius: 6px; background: {fill}"></span></span>
          <span style="font-size: 13px; font-weight: 700; text-align: right; white-space: nowrap">{esc(r['value'])}</span></div>""")
    return wrap(f'<div style="display: flex; flex-direction: column; gap: 6px">{"".join(out) or empty("No data in this period.")}</div>')


def grid(cols: list[tuple[str, str, str]], rows: list[list[str]], main_col: int = 1) -> str:
    """cols: (header, css width, align 'l'|'r'). rows: pre-rendered HTML cells (escape before passing)."""
    tpl = " ".join(c[1] for c in cols)
    head = "".join(f'<span class="{"r" if c[2] == "r" else ""}">{esc(c[0])}</span>' for c in cols)
    body = []
    for r in rows:
        cells = "".join(
            f'<span data-label="{esc(cols[i][0])}" class="{"main " if i == main_col else ""}{"r" if cols[i][2] == "r" else ""}">{cell}</span>'
            for i, cell in enumerate(r))
        body.append(f'<div class="gt-row row" data-tap style="--cols: {tpl}">{cells}</div>')
    return wrap(f'<div role="table"><div class="gt-head" style="--cols: {tpl}">{head}</div>{"".join(body) or empty("No data in this period.")}</div>')


def pill(text: str, bg: str, color: str) -> str:
    return (f'<span style="display: inline-block; padding: 3px 9px; border-radius: 11px; background: {bg}; color: {color}; '
            f'font-size: 11px; font-weight: 700; white-space: nowrap">{esc(text)}</span>')


def empty(text: str) -> str:
    return f'<div style="padding: 18px; border-radius: 14px; background: rgba(47,91,234,0.05); color: {INK3}; font-size: 13px">{esc(text)}</div>'


def facts(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="card" data-tap style="padding: 12px 14px; border-radius: 16px; background: rgba(47,91,234,0.06)">'
                    f'<div style="font-size: 11px; font-weight: 500; color: {INK3}">{esc(k)}</div>'
                    f'<div style="font-size: 18px; font-weight: 700; margin-top: 4px; line-height: 1.25">{esc(v)}</div></div>' for k, v in items)
    return wrap(f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 8px 0 14px">{cells}</div>')


CLOUD_VIVID = {"pos": [GREEN, ORANGE, "#b7791f"], "neg": ["#d92d32"], "neu": [INK2]}
CLOUD_MUTED = {"pos": ["#3f7d66", "#a2593a", "#8a6d32"], "neg": ["#a2484b"], "neu": ["#6b7385"]}


def keyword_cloud(kw: pd.DataFrame) -> str:
    if kw.empty:
        return wrap(empty("No keywords yet for this selection."))
    top = int(kw["mentions"].max())
    words, pi = [], 0
    for r in kw.sort_values("mentions", ascending=False).itertuples():
        ratio = r.mentions / top
        tier = 0 if ratio >= .6 else 1 if ratio >= .35 else 2 if ratio >= .2 else 3
        kind = "pos" if r.nsr > .2 else "neg" if r.nsr < -.2 else "neu"
        pal = (CLOUD_VIVID if tier <= 1 else CLOUD_MUTED)[kind]
        color = pal[pi % len(pal)] if kind == "pos" else pal[0]
        pi += kind == "pos"
        words.append(f'<span class="word" data-tap title="{esc(r.keyword)} · {r.mentions} posts" style="font-size: '
                     f'{[40, 28, 20, 15][tier]}px; font-weight: {[800, 700, 600, 400][tier]}; color: {color}">{esc(r.keyword)}</span>')
    ordered: list[str] = []
    for i, w in enumerate(words):
        ordered.insert(0, w) if i % 2 == 0 else ordered.append(w)
    legend = (f'<div style="display: flex; flex-wrap: wrap; gap: 12px; padding-top: 12px; border-top: 1px solid rgba(16,24,40,.06); '
              f'font-size: 11px; font-weight: 500; color: {INK3}"><span><b style="color:{GREEN}">●</b><b style="color:{ORANGE}">●</b>'
              f'<b style="color:#b7791f">●</b> Positive</span><span><b style="color:{INK3}">●</b> Neutral</span>'
              f'<span><b style="color:#d92d32">●</b> Negative</span><span>Bigger &amp; bolder = more mentions · muted = fewer</span></div>')
    return wrap(f"""<figure style="margin: 0; padding: 22px; border-radius: 20px; background: #ffffff; border: 1px solid rgba(47,91,234,0.12); min-height: 440px; display: flex; flex-direction: column; gap: 14px">
      <figcaption style="font-size: 14px; font-weight: 600">Keyword cloud</figcaption>
      <div style="flex: 1; display: flex; flex-wrap: wrap; align-items: center; align-content: space-evenly; justify-content: space-evenly; gap: 10px 20px; line-height: 1.1; text-align: center">{"".join(ordered)}</div>{legend}</figure>""")


def dark_card(head: str, body_html: str) -> str:
    return wrap(f"""<section class="card" data-tap style="border-radius: 24px; padding: 22px 24px; background: linear-gradient(160deg, {INK} 0%, #1f2a4a 100%); color: #ffffff; box-shadow: 0 16px 36px rgba(16,24,40,0.25)">
      <div style="margin-bottom: 10px"><span style="padding: 4px 10px; border-radius: 12px; background: rgba(255,255,255,0.12); font-size: 11px; font-weight: 700">{esc(head)}</span></div>
      <div style="font-size: 13px; line-height: 1.7; color: #e3e8f4">{body_html}</div></section>""")


def alert_card(level: str, when: str, rule: str, title_text: str, detail: str) -> str:
    if level == "High":
        bg, border, shadow, fg, muted, bbg, bink = ("linear-gradient(135deg, #e5484d 0%, #f07a6a 100%)", "transparent",
                                                     "0 14px 30px rgba(229,72,77,0.28)", "#ffffff", "rgba(255,255,255,.9)",
                                                     "rgba(255,255,255,.22)", "#ffffff")
    else:
        bg, border, shadow, fg, muted, bbg, bink = ("rgba(255,255,255,0.74)", "rgba(255,255,255,0.95)", "0 10px 30px rgba(47,91,234,0.08)",
                                                     INK, INK3, "#fdead7", "#93370d")
    return wrap(f"""<article class="card" data-tap style="border-radius: 20px; padding: 16px 18px; margin-bottom: 12px; background: {bg}; border: 1px solid {border}; box-shadow: {shadow}; color: {fg}">
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 8px"><span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; background: {bbg}; color: {bink}; font-size: 11px; font-weight: 700">{svg('warn', 12, 2.6)} {esc(level)}</span><span style="font-size: 12px; font-weight: 500; color: {muted}">{esc(when)} · {esc(rule)}</span></div>
      <div style="font-size: 15px; font-weight: 600; line-height: 1.4">{esc(title_text)}</div>
      <div style="font-size: 13px; line-height: 1.5; color: {muted}; margin-top: 6px; white-space: pre-line">{esc(detail)}</div></article>""")


def md_lite(text: str) -> str:
    """Tiny Markdown → HTML for generated insights (### headings, - bullets, 1. items, **bold**)."""
    import re  # noqa: PLC0415

    out, in_ul, in_ol = [], False, False

    def close():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
        if in_ol:
            out.append("</ol>")
        in_ul = in_ol = False

    for raw in text.splitlines():
        line = esc(raw.strip())
        line = re.sub(r"\*\*(.+?)\*\*", r'<b style="color:#ffffff;font-weight:600">\1</b>', line)
        if not line:
            close()
        elif line.startswith("### "):
            close()
            out.append(f'<div style="font-size:15px;font-weight:600;color:#ffffff;margin:10px 0 6px">{line[4:]}</div>')
        elif line.startswith("- "):
            if not in_ul:
                close(); out.append('<ul style="margin:0 0 8px;padding-left:18px">'); in_ul = True  # noqa: E702
            out.append(f"<li>{line[2:]}</li>")
        elif re.match(r"^\d+\. ", line):
            if not in_ol:
                close(); out.append('<ol style="margin:0 0 8px;padding-left:18px">'); in_ol = True  # noqa: E702
            item = re.sub(r"^\d+\. ", "", line)
            out.append(f"<li>{item}</li>")
        else:
            close()
            out.append(f"<p style='margin:0 0 8px'>{line}</p>")
    close()
    return "".join(out)
