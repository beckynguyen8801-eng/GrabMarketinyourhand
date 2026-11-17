"""Builds every artboard of the VN Listen canvas (desktop + mobile) from one kit.

    python3 build.py <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from kit import (
    ACCENT_PROP, AMBER, BG, BLUE, CARD, DOWN, FLAT, FONT, GREEN, INK, INK2, INK3, ORANGE, PINK, UP, VIOLET, fmt_signed,
    h2, ic, look, page, signed_ink, svg, tile, tile_hole, tint,
)

OUT = Path(sys.argv[1])
MODULES = [  # key, label, short, href desktop, href mobile, icon, colour
    ("listening", "Social Listening", "Listening", "Main.dc.html", "M_Listening.dc.html", "listening", BLUE),
    ("communities", "Communities", "Communities", "Communities.dc.html", "M_Communities.dc.html", "users", PINK),
    ("research", "Marketing Research", "Research", "Research.dc.html", "M_Research.dc.html", "research", ORANGE),
    ("alerts", "Alerts", "Alerts", "Alerts.dc.html", "M_Alerts.dc.html", "bell", AMBER),
]
SOURCES = ["Facebook", "TikTok", "YouTube", "News", "Threads", "Instagram"]
PRESETS = ["7D", "30D", "This month", "YTD", "Custom"]


def write(name: str, html: str) -> None:
    (OUT / name).write_text(html, encoding="utf-8")


def nav_items(active: str, mobile: bool) -> list[dict]:
    items = []
    for key, label, short, href_d, href_m, icon, color in MODULES:
        on = key == active
        items.append({
            "label": short if mobile else label, "href": href_m if mobile else href_d, "on": on,
            "badge": "5" if key == "alerts" else "", **look(color, icon),
            "tint": tint(color, 0.32 if on else 0.16), "bg": "#ffffff" if on else "transparent",
            "ink": INK if on else INK2, "weight": 700 if on else 500,
            "shadow": f"0 10px 24px {tint(color, 0.16)}" if on else "none",
        })
    return items


def chip(text_hole: str, bg: str = "rgba(255,255,255,0.8)", ink: str = INK2, extra: str = "") -> str:
    return (f'<button type="button" class="chip" data-tap style="flex: 0 0 auto; height: 32px; padding: 0 12px; border-radius: 16px; '
            f'border: 1px solid rgba(47,91,234,0.14); background: {bg}; color: {ink}; font-family: {FONT}; '
            f'font-size: 12px; font-weight: 600; white-space: nowrap{extra}">{text_hole}</button>')


# ============================================================ COMPONENTS
def sidebar() -> None:
    body = f"""<aside style="width: 280px; min-height: 100%; padding: 28px 22px; display: flex; flex-direction: column; gap: 26px; background: rgba(255,255,255,0.62); border-right: 1px solid rgba(255,255,255,0.9); font-family: {FONT}; color: {INK}">
  <div style="display: flex; align-items: center; gap: 12px">
    <span class="tile" style="flex: 0 0 42px; height: 42px; border-radius: 13px; display: flex; align-items: center; justify-content: center; color: #ffffff; background: linear-gradient(135deg, {{{{accent}}}} 0%, #8cc8fb 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 8px 20px rgba(47,91,234,0.3)">{svg('pulse', 22)}</span>
    <div><div style="font-size: 18px; font-weight: 800; letter-spacing: -0.02em">VN Listen</div><div style="font-size: 11px; font-weight: 500; color: {INK3}">Listening &amp; research</div></div>
  </div>
  <label style="display: flex; flex-direction: column; gap: 8px; font-size: 12px; font-weight: 500; color: {INK3}">Industry
    <select style="height: 46px; border-radius: 14px; border: 1px solid rgba(47,91,234,0.18); background: rgba(255,255,255,0.9); padding: 0 12px; font-family: {FONT}; font-size: 14px; font-weight: 600; color: {INK}">
      <sc-for list="{{{{industries}}}}" as="ind" hint-placeholder-count="2"><sc-if value="{{{{ind.on}}}}" hint-placeholder-val="{{{{false}}}}"><option selected="selected">{{{{ind.label}}}}</option></sc-if><sc-if value="{{{{ind.off}}}}" hint-placeholder-val="{{{{true}}}}"><option>{{{{ind.label}}}}</option></sc-if></sc-for>
    </select>
  </label>
  <nav aria-label="Modules" style="display: flex; flex-direction: column; gap: 6px">
    <div style="font-size: 12px; font-weight: 500; color: {INK3}; margin-bottom: 2px">Module</div>
    <sc-for list="{{{{nav}}}}" as="n" hint-placeholder-count="4">
      <a href="{{{{n.href}}}}" class="btn" style="display: flex; align-items: center; gap: 12px; min-height: 52px; padding: 0 10px; border-radius: 16px; background: {{{{n.bg}}}}; color: {{{{n.ink}}}}; text-decoration: none; font-size: 14px; font-weight: {{{{n.weight}}}}; box-shadow: {{{{n.shadow}}}}">
        {tile_hole('n', 36, 12, 20)}
        <span style="flex: 1; line-height: 1.3">{{{{n.label}}}}</span>
        <sc-if value="{{{{n.badge}}}}" hint-placeholder-val="{{{{false}}}}"><span style="min-width: 24px; height: 22px; padding: 0 7px; border-radius: 11px; background: #e5484d; color: #ffffff; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center">{{{{n.badge}}}}</span></sc-if>
      </a>
    </sc-for>
  </nav>
  <div style="display: flex; flex-direction: column; gap: 10px">
    <label for="q" style="font-size: 12px; font-weight: 500; color: {INK3}">Search</label>
    <div style="display: flex; align-items: center; gap: 8px; height: 48px; padding: 0 14px; border-radius: 14px; background: #ffffff; border: 1.5px solid {{{{accent}}}}; box-shadow: 0 6px 18px rgba(47,91,234,0.12); color: {INK3}">
      {svg('search', 18, 2)}
      <input id="q" type="search" value="{{{{query}}}}" placeholder="Search any keyword…" style="flex: 1; min-width: 0; border: 0; outline: none; background: transparent; font-family: {FONT}; font-size: 14px; font-weight: 500; color: {INK}">
    </div>
    <div style="font-size: 11px; line-height: 1.5; color: {INK3}">Type anything in Vietnamese – a product, a hospital, a symptom. Accents optional.</div>
    <div style="display: flex; flex-wrap: wrap; gap: 6px"><sc-for list="{{{{recent}}}}" as="r" hint-placeholder-count="3">{chip('{{r}}')}</sc-for></div>
    <button type="button" style="height: 42px; border-radius: 12px; border: 0; background: rgba(47,91,234,0.1); color: #1f43c4; font-family: {FONT}; font-size: 13px; font-weight: 600">+ Track this keyword daily</button>
  </div>
  <fieldset style="border: 0; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px">
    <legend style="font-size: 12px; font-weight: 500; color: {INK3}; padding: 0; margin-bottom: 10px">Date range</legend>
    <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px">
      <label style="display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 500; color: {INK3}">From<input type="text" value="{{{{dateFrom}}}}" style="height: 42px; width: 100%; border-radius: 12px; border: 1px solid rgba(47,91,234,0.18); background: #ffffff; padding: 0 10px; font-family: {FONT}; font-size: 13px; font-weight: 600; color: {INK}"></label>
      <label style="display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 500; color: {INK3}">To<input type="text" value="{{{{dateTo}}}}" style="height: 42px; width: 100%; border-radius: 12px; border: 1px solid rgba(47,91,234,0.18); background: #ffffff; padding: 0 10px; font-family: {FONT}; font-size: 13px; font-weight: 600; color: {INK}"></label>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 6px"><sc-for list="{{{{presets}}}}" as="p" hint-placeholder-count="5">{chip('{{p.label}}', '{{p.bg}}', '{{p.ink}}')}</sc-for></div>
  </fieldset>
  <fieldset style="border: 0; margin: 0; padding: 0">
    <legend style="font-size: 12px; font-weight: 500; color: {INK3}; padding: 0; margin-bottom: 10px">Sources</legend>
    <div style="display: flex; flex-wrap: wrap; gap: 6px"><sc-for list="{{{{sources}}}}" as="s" hint-placeholder-count="6"><label class="chip" data-tap style="display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 11px; border-radius: 16px; background: rgba(255,255,255,0.85); border: 1px solid rgba(47,91,234,0.14); font-size: 12px; font-weight: 500; color: {INK2}"><input type="checkbox" checked="checked" style="margin: 0; accent-color: {{{{accent}}}}"> {{{{s}}}}</label></sc-for></div>
  </fieldset>
  <div style="margin-top: auto; padding: 14px; border-radius: 16px; background: rgba(47,91,234,0.07); font-size: 12px; line-height: 1.6; color: {INK2}"><div style="font-weight: 600; color: {INK}">Last scan 14:07 · 17/11</div>Crisis keywords hourly · everything else daily</div>
</aside>"""
    logic = """  renderVals() {
    const accent = this.props.accent ?? '#2f5bea';
    const active = this.props.active ?? 'listening';
    const industry = this.props.industry ?? 'Mother & Baby';
    const NAV = %s;
    return {
      accent, query: this.props.query ?? 'sữa công thức',
      dateFrom: this.props.dateFrom ?? '01/10/2026', dateTo: this.props.dateTo ?? '31/10/2026',
      industries: ['Mother & Baby', 'Healthcare'].map((label) => ({ label, on: label === industry, off: label !== industry })),
      nav: NAV[active] || NAV.listening,
      recent: ['Enfa A2', 'bv Bạch Mai', 'táo bón'],
      presets: %s.map((label) => ({ label, bg: label === 'Custom' ? accent : 'rgba(255,255,255,0.85)', ink: label === 'Custom' ? '#ffffff' : '#3b4459' })),
      sources: %s,
    };
  }
""" % (json.dumps({k[0]: nav_items(k[0], False) for k in MODULES}, ensure_ascii=False), json.dumps(PRESETS),
       json.dumps(SOURCES))
    props = {"active": {"editor": "enum", "options": [m[0] for m in MODULES], "default": "listening"},
             "industry": {"editor": "enum", "options": ["Mother & Baby", "Healthcare"], "default": "Mother & Baby"},
             "query": {"editor": "text", "default": "sữa công thức"},
             "dateFrom": {"editor": "text", "default": "01/10/2026"}, "dateTo": {"editor": "text", "default": "31/10/2026"},
             **ACCENT_PROP, "$preview": {"width": 280, "height": 1260}}
    write("Sidebar.dc.html", component("VN Listen – Sidebar", body, logic, props))


def component(title: str, body: str, logic: str, props: dict) -> str:
    """Child component: no haptic listener (the importing page owns it), small helmet."""
    props_json = json.dumps(props, ensure_ascii=False).replace("&", "&amp;").replace("'", "&#39;")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
<style>
body{{margin:0}}
</style>
</helmet>
{body}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{props_json}'>
class Component extends DCLogic {{
{logic}}}
</script>
</body>
</html>
"""


def mobile_topbar() -> None:
    body = f"""<header style="width: 390px; padding: 14px 16px 12px; display: flex; flex-direction: column; gap: 12px; background: rgba(255,255,255,0.7); border-bottom: 1px solid rgba(255,255,255,0.95); font-family: {FONT}; color: {INK}">
  <div style="display: flex; align-items: center; gap: 10px">
    <span class="tile" style="flex: 0 0 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #ffffff; background: linear-gradient(135deg, {{{{accent}}}} 0%, #8cc8fb 100%); box-shadow: 0 6px 16px rgba(47,91,234,0.3)">{svg('pulse', 20)}</span>
    <div style="flex: 1; min-width: 0">
      <div style="font-size: 11px; font-weight: 500; color: {INK3}">{{{{section}}}}</div>
      <div style="font-size: 20px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.2">{{{{title}}}}</div>
    </div>
    <label style="position: relative; display: inline-flex; align-items: center">
      <span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Industry</span>
      <select style="height: 38px; max-width: 150px; border-radius: 19px; border: 1px solid rgba(47,91,234,0.18); background: #ffffff; padding: 0 12px; font-family: {FONT}; font-size: 12px; font-weight: 700; color: {INK}">
        <sc-for list="{{{{industries}}}}" as="ind" hint-placeholder-count="2"><sc-if value="{{{{ind.on}}}}" hint-placeholder-val="{{{{false}}}}"><option selected="selected">{{{{ind.label}}}}</option></sc-if><sc-if value="{{{{ind.off}}}}" hint-placeholder-val="{{{{true}}}}"><option>{{{{ind.label}}}}</option></sc-if></sc-for>
      </select>
    </label>
  </div>
  <div style="display: flex; align-items: center; gap: 8px; height: 46px; padding: 0 14px; border-radius: 14px; background: #ffffff; border: 1.5px solid {{{{accent}}}}; box-shadow: 0 6px 18px rgba(47,91,234,0.12); color: {INK3}">
    {svg('search', 18, 2)}
    <input type="search" value="{{{{query}}}}" placeholder="Search any keyword…" aria-label="Search" style="flex: 1; min-width: 0; border: 0; outline: none; background: transparent; font-family: {FONT}; font-size: 15px; font-weight: 500; color: {INK}">
    <button type="button" aria-label="Track this keyword daily" style="flex: 0 0 auto; height: 30px; padding: 0 10px; border: 0; border-radius: 10px; background: rgba(47,91,234,0.1); color: #1f43c4; font-family: {FONT}; font-size: 12px; font-weight: 700">+ Track</button>
  </div>
  <div class="hscroll">
    <button type="button" class="chip" data-tap style="flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border-radius: 17px; border: 0; background: {{{{accent}}}}; color: #ffffff; font-family: {FONT}; font-size: 12px; font-weight: 700; white-space: nowrap">{svg('calendar', 15, 2.2)} {{{{dateRange}}}}</button>
    <sc-for list="{{{{presets}}}}" as="p" hint-placeholder-count="4">{chip('{{p}}').replace('height: 32px', 'height: 34px')}</sc-for>
    <sc-for list="{{{{sources}}}}" as="s" hint-placeholder-count="6"><label class="chip" data-tap style="flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 11px; border-radius: 17px; background: rgba(255,255,255,0.85); border: 1px solid rgba(47,91,234,0.14); font-size: 12px; font-weight: 500; color: {INK2}; white-space: nowrap"><input type="checkbox" checked="checked" style="margin: 0; accent-color: {{{{accent}}}}"> {{{{s}}}}</label></sc-for>
  </div>
</header>"""
    logic = """  renderVals() {
    const industry = this.props.industry ?? 'Mother & Baby';
    return {
      accent: this.props.accent ?? '#2f5bea',
      section: this.props.section ?? 'Social Listening', title: this.props.title ?? 'Overview',
      query: this.props.query ?? 'sữa công thức', dateRange: this.props.dateRange ?? '01/10 – 31/10/2026',
      industries: ['Mother & Baby', 'Healthcare'].map((label) => ({ label, on: label === industry, off: label !== industry })),
      presets: ['7D', '30D', 'This month', 'YTD'],
      sources: %s,
    };
  }
""" % json.dumps(SOURCES)
    props = {"section": {"editor": "text", "default": "Social Listening"}, "title": {"editor": "text", "default": "Overview"},
             "industry": {"editor": "enum", "options": ["Mother & Baby", "Healthcare"], "default": "Mother & Baby"},
             "query": {"editor": "text", "default": "sữa công thức"}, "dateRange": {"editor": "text", "default": "01/10 – 31/10/2026"},
             **ACCENT_PROP, "$preview": {"width": 390, "height": 186}}
    write("MobileTopBar.dc.html", component("VN Listen – Mobile top bar", body, logic, props))


def mobile_tabbar() -> None:
    body = f"""<nav aria-label="Modules" style="width: 390px; padding: 8px 10px 22px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; background: rgba(255,255,255,0.88); border-top: 1px solid rgba(255,255,255,0.95); box-shadow: 0 -10px 30px rgba(47,91,234,0.10); font-family: {FONT}">
  <sc-for list="{{{{nav}}}}" as="n" hint-placeholder-count="4">
    <a href="{{{{n.href}}}}" class="btn" style="position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 6px 2px; border-radius: 14px; text-decoration: none; color: {{{{n.ink}}}}; font-size: 11px; font-weight: {{{{n.weight}}}}">
      {tile_hole('n', 40, 13, 21)}
      <span style="line-height: 1.2; text-align: center">{{{{n.label}}}}</span>
      <sc-if value="{{{{n.badge}}}}" hint-placeholder-val="{{{{false}}}}"><span style="position: absolute; top: 2px; right: 14px; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: #e5484d; color: #ffffff; font-size: 10px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; border: 2px solid #ffffff">{{{{n.badge}}}}</span></sc-if>
    </a>
  </sc-for>
</nav>"""
    logic = """  renderVals() {
    const NAV = %s;
    return { nav: NAV[this.props.active ?? 'listening'] || NAV.listening };
  }
""" % json.dumps({k[0]: nav_items(k[0], True) for k in MODULES}, ensure_ascii=False)
    props = {"active": {"editor": "enum", "options": [m[0] for m in MODULES], "default": "listening"},
             "$preview": {"width": 390, "height": 92}}
    write("MobileTabBar.dc.html", component("VN Listen – Mobile tab bar", body, logic, props))


# ============================================================ SHARED SECTIONS
def frame_desktop(active: str, industry: str, query: str, d_from: str, d_to: str, main: str) -> str:
    return f"""<div style="display: flex; flex-wrap: wrap; min-height: 100vh; background: {BG}; font-family: {FONT}; color: {INK}">
  <div style="flex: 0 1 280px; max-width: 100%; display: flex">
    <dc-import name="Sidebar" active="{active}" industry="{industry.replace('&', '&amp;')}" query="{query}" date-from="{d_from}" date-to="{d_to}" accent="{{{{accent}}}}" hint-size="280px,1260px"></dc-import>
  </div>
  <main style="flex: 999 1 560px; min-width: 0; padding: 36px 40px 56px; display: flex; flex-direction: column; gap: 24px">
{main}
  </main>
</div>"""


def frame_mobile(active: str, section: str, title: str, industry: str, query: str, date_range: str, main: str) -> str:
    return f"""<div style="width: 390px; min-height: 844px; display: flex; flex-direction: column; background: {BG}; font-family: {FONT}; color: {INK}">
  <dc-import name="MobileTopBar" section="{section}" title="{title}" industry="{industry.replace('&', '&amp;')}" query="{query}" date-range="{date_range}" accent="{{{{accent}}}}" hint-size="390px,186px"></dc-import>
  <main style="flex: 1; padding: 16px 16px 24px; display: flex; flex-direction: column; gap: 16px">
{main}
  </main>
  <div style="position: sticky; bottom: 0">
    <dc-import name="MobileTabBar" active="{active}" hint-size="390px,92px"></dc-import>
  </div>
</div>"""


def header_desktop(crumb: str, title: str, icon: str, color: str, right: str = "") -> str:
    return f"""<header style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px">
  <div style="display: flex; align-items: center; gap: 16px; min-width: 0">
    {tile(icon, color, 56, 18, 28)}
    <div style="min-width: 0"><div style="font-size: 13px; font-weight: 500; color: {INK3}; line-height: 1.5">{crumb}</div>
    <h1 style="margin: 2px 0 0; font-size: 40px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1">{title}</h1></div>
  </div>
  {right}
</header>"""


def kpis(mobile: bool) -> str:
    """Hero gradient card + 4 KPI cards. Data: hero{{label,value,pill,note}}, kpis[]."""
    hero = f"""<div class="card" data-tap style="{'' if mobile else 'flex: 1 1 300px; min-height: 188px; '}min-width: 0; border-radius: 24px; padding: {'20px' if mobile else '24px 26px'}; background: linear-gradient(135deg, {{{{accent}}}} 0%, #4f86f7 55%, #8cc8fb 100%); color: #ffffff; box-shadow: 0 16px 36px rgba(47,91,234,0.32); display: flex; flex-direction: column; justify-content: center; gap: 8px; position: relative; overflow: hidden">
      <div style="font-size: 14px; font-weight: 500; opacity: 0.92">{{{{hero.label}}}}</div>
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px"><span style="font-size: {'38' if mobile else '44'}px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1">{{{{hero.value}}}}</span><span style="height: 26px; padding: 0 10px; border-radius: 13px; background: #dcfae6; color: {UP}; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center">{{{{hero.pill}}}}</span></div>
      <div style="font-size: 12px; font-weight: 500; opacity: 0.92">{{{{hero.note}}}}</div>
      <svg viewBox="0 0 200 40" style="position: absolute; right: 0; bottom: 8px; width: 50%; height: 44px" aria-hidden="true"><path d="M0 34 C 25 34, 30 22, 55 26 S 90 12, 110 20 S 150 4, 200 8" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="2.5" stroke-linecap="round"></path></svg>
    </div>"""
    if mobile:
        card = f"""<div class="card" data-tap style="{CARD}; border-radius: 20px; padding: 14px; display: flex; flex-direction: column; gap: 8px; min-width: 0">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">{tile_hole('k', 36, 12, 19)}<span style="font-size: 22px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; text-align: right">{{{{k.value}}}}</span></div>
        <div style="font-size: 12px; font-weight: 500; color: {INK3}; line-height: 1.35">{{{{k.label}}}}</div>
        <div style="font-size: 11px; font-weight: {{{{k.noteWeight}}}}; color: {{{{k.noteInk}}}}; line-height: 1.35">{{{{k.note}}}}</div>
      </div>"""
        return f"""<section aria-label="Key metrics" style="display: flex; flex-direction: column; gap: 12px">
    {hero}
    <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px"><sc-for list="{{{{kpis}}}}" as="k" hint-placeholder-count="4">{card}</sc-for></div>
  </section>"""
    card = f"""<div class="card" data-tap style="{CARD}; border-radius: 22px; padding: 18px 20px; display: flex; align-items: center; gap: 14px; min-width: 0">
        {tile_hole('k', 46, 15, 22)}
        <div style="flex: 1; min-width: 0"><div style="font-size: 13px; font-weight: 500; color: {INK3}; line-height: 1.35">{{{{k.label}}}}</div><div style="font-size: 12px; font-weight: {{{{k.noteWeight}}}}; color: {{{{k.noteInk}}}}; line-height: 1.35; margin-top: 4px">{{{{k.note}}}}</div></div>
        <div style="font-size: 28px; font-weight: 700; letter-spacing: -0.03em; white-space: nowrap">{{{{k.value}}}}</div>
      </div>"""
    return f"""<section aria-label="Key metrics" style="display: flex; flex-wrap: wrap; gap: 16px; align-items: stretch">
    {hero}
    <div style="flex: 2 1 560px; min-width: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 16px"><sc-for list="{{{{kpis}}}}" as="k" hint-placeholder-count="4">{card}</sc-for></div>
  </section>"""


def hbars(var: str, label_w: int, value_w: int = 48, height: int = 12, gradient: bool = False) -> str:
    fill = "linear-gradient(90deg, {{b.color}}, {{b.color2}})" if gradient else "{{b.color}}"
    return f"""<sc-for list="{{{{{var}}}}}" as="b" hint-placeholder-count="6">
        <div class="row" data-tap title="{{{{b.title}}}}" style="display: grid; grid-template-columns: {label_w}px minmax(0, 1fr) {value_w}px; align-items: center; gap: 12px; padding: 4px 6px; margin: 0 -6px; border-radius: 10px">
          <span style="font-size: 13px; font-weight: 500; color: {INK2}; line-height: 1.3">{{{{b.label}}}}</span>
          <span style="height: {height}px; border-radius: {height // 2}px; background: rgba(47,91,234,0.07)"><span class="bar" data-tap style="display: block; height: {height}px; width: {{{{b.width}}}}; border-radius: {height // 2}px; background: {fill}"></span></span>
          <span style="font-size: 13px; font-weight: 700; text-align: right; white-space: nowrap">{{{{b.value}}}}</span>
        </div>
      </sc-for>"""


def legend(items: list[tuple[str, str]], dot: str = "10px") -> str:
    return "".join(f'<span style="display: inline-flex; align-items: center; gap: 6px; white-space: nowrap"><span style="width: {dot}; height: {dot}; border-radius: 3px; background: {c}"></span>{t}</span>'
                   for t, c in items)


def section(inner: str, pad: str = "22px 24px", extra: str = "", radius: int = 24) -> str:
    return f'<section style="{CARD}; border-radius: {radius}px; padding: {pad}; min-width: 0; {extra}">\n{inner}\n</section>'


def row2(left: str, right: str, lw: str = "3 1 520px", rw: str = "2 1 320px") -> str:
    return f'<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: stretch"><div style="flex: {lw}; min-width: 0; display: flex">{left}</div><div style="flex: {rw}; min-width: 0; display: flex">{right}</div></div>'


def bar_rows(rows, max_value, color, label_key=0, value_fmt=str, color2=None):
    return [{"label": r[label_key], "value": value_fmt(r[1]), "width": f"{round(r[1] / max_value * 100)}%",
             "color": color if not callable(color) else color(r), "color2": color2 or "#8cc8fb",
             "title": f"{r[0]}: {value_fmt(r[1])}"} for r in rows]


# ============================================================ DATA (illustrative)
SOV = [("Lumi Milk", 21), ("Nutri Kid", 13), ("Happi Dry", 12), ("Mimo", 8), ("BabySoft", 8), ("Sunny Bottle", 6)]
KEYWORDS = [  # keyword, posts, nsr, type, example
    ("đạm A2", 62, 0.71, "Known", "Đổi sang Lumi A2 Gold 1 tháng, đạm A2 dễ tiêu hơn hẳn"),
    ("tăng cân", 48, 0.83, "Known", "Bé uống 2 tháng tăng cân đều, mẹ yên tâm"),
    ("sữa mát", 41, 0.66, "Known", "Sữa mát, bé đi ngoài đều, không nóng trong"),
    ("giá cao", 37, -0.78, "Known", "Sữa tốt nhưng giá cao quá, lon 800g gần 700k"),
    ("táo bón", 22, -0.64, "Known", "Tuần đầu bé hơi táo bón, các mẹ có bị không?"),
    ("dễ uống", 19, 0.9, "Known", "Vị nhạt dễ uống, bé không kén"),
    ("chính hãng", 17, 0.41, "Known", "Mua ở cửa hàng chính hãng có tem cào"),
    ("tiêu hoá", 16, 0.6, "Known", "Hệ tiêu hoá bé ổn hơn sau 2 tuần"),
    ("đổi sữa", 15, 0.05, "Known", "Có nên đổi sữa khi bé 1 tuổi không mọi người?"),
    ("lon 800g", 14, 0.12, "Discovered", "Lon 800g dùng khoảng 10 ngày cho bé 1 tuổi"),
    ("DHA", 13, 0.5, "Known", "Có DHA nên mình yên tâm"),
    ("HMO", 12, 0.58, "Known", "Có HMO tăng đề kháng"),
    ("6 tháng", 12, 0.4, "Discovered", "Bé 6 tháng uống được không ạ?"),
    ("khuyến mãi", 11, 0.1, "Known", "Đang khuyến mãi mua 2 tặng 1"),
    ("mua ở đâu", 10, 0.0, "Known", "Mua ở đâu chính hãng giá tốt?"),
    ("pha sữa", 9, 0.3, "Discovered", "Pha không bị vón, tan nhanh"),
    ("hàng giả", 9, -1.0, "Known", "Cẩn thận hàng giả trên sàn"),
    ("review", 9, 0.4, "Known", "Review thật sau 1 tháng"),
    ("bé lười ăn", 7, -0.2, "Discovered", "Bé lười ăn uống có cải thiện không?"),
    ("so sánh", 6, 0.0, "Known", "So sánh với Nutri Kid thì sao?"),
    ("ngủ ngon", 6, 0.9, "Known", "Bé ngủ ngon hơn"),
    ("vón cục", 5, -0.6, "Known", "Lon cuối bị vón cục"),
    ("giao hàng", 5, -0.3, "Known", "Giao hàng chậm 5 ngày"),
    ("nôn trớ", 4, -0.7, "Known", "Bé hay nôn trớ sau khi uống"),
]
RANKING = [("Lumi Milk", 0.92, "1,136", "21%", 20, 45), ("Nutri Kid", 0.90, "703", "13%", 67, 5),
           ("Happi Dry", 0.85, "649", "12%", 46, 115), ("BabySoft", 0.77, "433", "8%", 50, 22),
           ("Mimo", 0.74, "441", "8%", 17, -18)]
COMMUNITIES = [  # name, type, access, score, parts, tier, ppw, rel, intent, nsr, rec, x%, y%
    ("Hội mẹ bỉm sữa Hà Nội", "Facebook group", "public", 0.82, [0.24, 0.2, 0.2, 0.08, 0.1], "High potential", 56, 41, 38, 43, "Buyers asking questions – seed honest KOC reviews and answer threads", 72, 70),
    ("mebap.review", "TikTok account", "public", 0.76, [0.2, 0.25, 0.15, 0.06, 0.1], "High potential", 43, 33, 37, 58, "Core community – build a long-term presence with expert answers", 58, 86),
    ("Nuôi con bằng sữa công thức", "Facebook group", "public", 0.68, [0.18, 0.14, 0.22, 0.04, 0.1], "High potential", 41, 52, 36, 51, "Core community – host an AMA with a nutritionist", 86, 48),
    ("Review bỉm sữa chính hãng", "Facebook group", "public", 0.57, [0.12, 0.12, 0.16, 0.07, 0.1], "Worth testing", 31, 38, 44, -12, "Competitor stronghold – sponsor the admin or run a comparison review", 62, 36),
    ("nhabimsua", "TikTok account", "public", 0.55, [0.16, 0.22, 0.05, 0.02, 0.1], "Worth testing", 48, 12, 31, 30, "Big reach, broad topic – awareness content or minigame", 16, 78),
    ("Hội mẹ sinh tháng 6/2026", "Facebook group", "private", 0.46, [0.1, 0.08, 0.17, 0.08, 0.03], "Worth testing", 22, 40, 52, 20, "Request to join; observe 1–2 weeks before posting", 66, 18),
    ("webtretho.com", "Forum", "public", 0.38, [0.06, 0.04, 0.14, 0.04, 0.1], "Monitor", 9, 34, 29, -35, "Crisis watch – reply with facts and track daily", 46, 10),
    ("Ăn dặm & dinh dưỡng cho bé", "Facebook group", "public", 0.34, [0.08, 0.06, 0.06, 0.04, 0.1], "Monitor", 18, 9, 24, 62, "Keep monitoring – test with 1–2 helpful posts", 10, 28),
]
COMPONENTS = [("Activity", "25", "Posts per week", BLUE, "trend"), ("Engagement", "25", "Avg interactions per post", PINK, "heart"),
              ("Relevance", "25", "Share of on-topic posts", GREEN, "search"),
              ("Buying intent", "15", "Questions, reviews, price asks", ORANGE, "spark"),
              ("Openness", "10", "Public › unknown › private", AMBER, "users")]
TIERS = {"High potential": ("rgba(14,159,110,0.14)", "#05603a", GREEN), "Worth testing": ("rgba(232,89,12,0.14)", "#9a3c12", ORANGE),
         "Monitor": ("rgba(138,147,166,0.18)", INK2, "#8a93a6")}
HOSPITALS = [("Lotus International Hospital", "Private · VN", "TP.HCM", "General", "2,140", 38, "gói khám, sạch sẽ, viện phí"),
             ("Sông Hồng General Hospital", "Public · VN", "Hà Nội", "General – central level", "1,986", -12, "quá tải, chờ lâu, bác sĩ giỏi"),
             ("Bến Nghé Women & Children", "Public · VN", "TP.HCM", "Obstetrics & pediatrics", "1,402", 21, "sinh con, điều dưỡng, chu đáo"),
             ("Harbor Medical Centre", "Asia", "Singapore", "Oncology", "864", 44, "du lịch y tế, chi phí, visa"),
             ("Siam Care Hospital", "Asia", "Bangkok", "General", "611", 52, "khám tổng quát, phiên dịch"),
             ("Cửu Long Heart Institute", "Private · VN", "Cần Thơ", "Cardiology", "498", 30, "mổ tim, bảo hiểm"),
             ("Nordlicht University Clinic", "Europe", "Germany", "General – university", "233", 61, "chữa ung thư, chi phí")]
SEG = {"Public · VN": (BLUE, "#1f43c4"), "Private · VN": (GREEN, "#05603a"), "Asia": (ORANGE, "#9a3c12"), "Europe": (VIOLET, "#4a3aa7")}
ACTIVITIES = [("Promotion / discount", 412, "on"), ("Offline event", 366, "off"), ("Free check-up / CSR", 298, "off"),
              ("KOL / doctor content", 271, "on"), ("Branding / TVC", 214, "on"), ("Livestream", 160, "on"),
              ("Minigame", 104, "on"), ("Launch / new branch", 81, "on")]
HEAT_COLS = ["Promo", "Game", "KOL", "Live", "Launch", "Brand", "Event", "CSR"]
HEAT = [("Lotus International", [14, 4, 8, 3, 2, 6, 11, 5]), ("Sông Hồng General", [0, 0, 6, 0, 0, 2, 9, 12]),
        ("VitaCare", [10, 6, 7, 5, 1, 3, 2, 1]), ("PharmaGo", [12, 2, 3, 8, 4, 1, 6, 2]),
        ("Harbor Medical", [2, 0, 5, 0, 0, 4, 3, 0]), ("BeatCheck", [4, 1, 2, 3, 3, 0, 5, 0])]
TRENDS = [("men vi sinh", 8.5), ("khám tầm soát ung thư", 6.1), ("bảo hiểm sức khoẻ", 4.4), ("đi singapore khám", 3.8),
          ("giao thuốc 2h", 2.9), ("bác sĩ online", 2.2)]
SUGGEST = [("bệnh viện tư tốt nhất tphcm", False), ("bệnh viện tư có bảo hiểm y tế", True), ("bệnh viện tư sinh con", False),
           ("bệnh viện tư hà nội", False), ("bệnh viện tư khám ngoài giờ", True), ("bệnh viện tư giá khám", False)]
ALERTS = [("High", "09:12", "Risk keywords", "Lumi Milk · 12 posts mention “hàng giả”, “tiêu chảy” in 24h", "5,234 interactions · spreading on TikTok and 2 news sites"),
          ("High", "09:12", "Negative spike", "Lumi Milk · 15 negative posts in 24h (normal 2.3/day)", "6.5× the usual level"),
          ("Medium", "08:05", "Risk keywords", "Mimo · 5 posts mention “nổi mẩn”, “dị ứng”", "2,249 interactions · mostly in parenting groups"),
          ("Medium", "07:40", "Risk keywords", "BabySoft · 3 posts call out a shop selling fakes", "494 interactions"),
          ("Medium", "Yesterday", "Risk keywords", "Sunny Bottle · 3 posts about choking with the large teat", "283 interactions")]
HOURS = [0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 2, 3, 6, 11, 18, 14, 9, 7, 5, 4]
RISKS = [("hàng giả", 12), ("tiêu chảy", 12), ("bóc phốt", 6), ("thu hồi", 3), ("dị ứng", 2)]
POSTS = [("09:03", "TikTok", "Nghi vấn hàng giả Lumi Milk bán tràn lan trên mạng, nhiều bé bị tiêu chảy sau khi uống", "3,114"),
         ("09:40", "News", "Phụ huynh phản ánh sữa Lumi Milk không rõ nguồn gốc trên sàn TMĐT", "1,420"),
         ("10:15", "Facebook", "Các mẹ check mã lô Lumi Milk trước khi cho con uống nhé, mình bị dính hàng giả", "688"),
         ("11:02", "Threads", "Có ai biết cách phân biệt Lumi Milk thật giả không?", "236")]


def kw_cloud() -> list[dict]:
    top = max(k[1] for k in KEYWORDS)
    vivid = {"pos": [GREEN, ORANGE, "#b7791f"], "neg": ["#d92d32"], "neu": [INK2]}
    muted = {"pos": ["#3f7d66", "#a2593a", "#8a6d32"], "neg": ["#a2484b"], "neu": ["#6b7385"]}
    words, pi = [], 0
    for kw, posts, nsr, *_ in sorted(KEYWORDS, key=lambda k: -k[1]):
        r = posts / top
        tier = 0 if r >= 0.6 else 1 if r >= 0.35 else 2 if r >= 0.2 else 3
        kind = "pos" if nsr > 0.2 else "neg" if nsr < -0.2 else "neu"
        pal = (vivid if tier <= 1 else muted)[kind]
        color = pal[pi % len(pal)] if kind == "pos" else pal[0]
        pi += kind == "pos"
        words.append({"kw": kw, "title": f"{kw} · {posts} posts · NSR {fmt_signed(round(nsr * 100))}", "color": color,
                      "size": ["40px", "28px", "20px", "15px"][tier], "msize": ["30px", "22px", "17px", "14px"][tier],
                      "weight": [800, 700, 600, 400][tier]})
    out = []
    for i, w in enumerate(words):
        out.insert(0, w) if i % 2 == 0 else out.append(w)
    return out


def kw_rows(n: int = 8) -> list[dict]:
    return [{"kw": k, "type": t, "posts": p, "share": f"{round(p / 214 * 100)}%", "nsr": fmt_signed(round(s * 100)),
             "nsrInk": signed_ink(s), "example": ex,
             "typeBg": "rgba(47,91,234,0.1)" if t == "Known" else "rgba(232,89,12,0.12)",
             "typeInk": "#1f43c4" if t == "Known" else "#9a3c12"} for k, p, s, t, ex in KEYWORDS[:n]]


def community_rows() -> list[dict]:
    rows = []
    for i, c in enumerate(COMMUNITIES):
        name, typ, acc, score, parts, tier, ppw, rel, intent, nsr, rec, x, y = c
        tb, ti, tc = TIERS[tier]
        rows.append({"rank": i + 1, "name": name, "type": typ, "access": acc, "score": f"{score:.2f}", "tier": tier,
                     "tierBg": tb, "tierInk": ti, "tierColor": tc, "ppw": ppw, "rel": f"{rel}%", "intent": f"{intent}%",
                     "nsr": fmt_signed(nsr), "nsrInk": signed_ink(nsr), "rec": rec,
                     "summary": f"{ppw} posts/week · {rel}% on-topic · {intent}% buying questions · NSR {fmt_signed(nsr)}",
                     "parts": [{"w": f"{round(p * 100)}%", "c": COMPONENTS[j][3]} for j, p in enumerate(parts)],
                     "accessBg": "rgba(14,159,110,0.14)" if acc == "public" else "rgba(245,159,0,0.22)",
                     "accessInk": "#05603a" if acc == "public" else "#7a4a00",
                     "x": f"{x}%", "y": f"{y}%", "dot": f"{26 + ppw // 8}px",
                     "medal": ["linear-gradient(150deg,#fff6d6,#f5b400)", "linear-gradient(150deg,#ffffff,#c9d1e3)",
                               "linear-gradient(150deg,#ffe8d9,#e8590c)"][i] if i < 3 else "",
                     "medalInk": ["#5c3d00", "#2c3445", "#ffffff"][i] if i < 3 else "",
                     "cardBg": "linear-gradient(150deg, #ffffff 0%, #ffe3ee 100%)" if i == 0 else "rgba(255,255,255,0.74)",
                     "recBg": "rgba(214,51,108,0.10)" if i == 0 else "rgba(47,91,234,0.06)"})
    return rows


def heat_scale(v: int) -> dict:
    if v == 0:
        return {"v": v, "bg": "rgba(255,255,255,0.75)", "ink": "#8a93a6"}
    if v <= 2:
        return {"v": v, "bg": "#dfe7fd", "ink": "#142c86"}
    if v <= 5:
        return {"v": v, "bg": "#a9bdf7", "ink": "#142c86"}
    if v <= 9:
        return {"v": v, "bg": "#6d8ef0", "ink": "#ffffff"}
    return {"v": v, "bg": BLUE, "ink": "#ffffff"}


# ============================================================ PAGE BODIES
def listening(mobile: bool) -> tuple[str, dict]:
    sp = 16 if mobile else 20
    chart = f"""<svg viewBox="0 0 760 250" style="width: 100%; height: auto; display: block" role="img" aria-label="Weekly mentions for three brands; Lumi Milk peaks in week 4 at 640 mentions">
          <defs><linearGradient id="peak" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f5bea"></stop><stop offset="1" stop-color="#8cc8fb"></stop></linearGradient></defs>
          <g fill="rgba(47,91,234,0.08)">{''.join(f'<rect class="vbar" data-tap x="{52 + i * 108}" y="30" width="56" height="180" rx="14"><title>Week {i + 1}</title></rect>' for i in range(6) if i != 3)}</g>
          <rect class="vbar" data-tap x="376" y="30" width="56" height="180" rx="14" fill="url(#peak)" opacity="0.9"><title>Week 4 · peak</title></rect>
          <g font-size="{18 if mobile else 11}" fill="{INK3}" font-family="Montserrat, sans-serif" font-weight="600">{''.join(f'<text x="{80 + i * 108}" y="{240 if mobile else 234}" text-anchor="middle">W{i + 1}</text>' for i in range(6))}</g>
          <g fill="none" stroke-width="{4 if mobile else 2.5}" stroke-linecap="round">
            <path d="M80 160 C 130 160, 140 150, 188 146 S 250 150, 296 138 S 360 120, 404 124 S 470 140, 512 132 S 580 128, 620 120" stroke="{GREEN}"></path>
            <path d="M80 120 C 130 118, 140 112, 188 110 S 250 116, 296 112 S 360 104, 404 108 S 470 118, 512 116 S 580 122, 620 118" stroke="{ORANGE}"></path>
            <path d="M80 140 C 130 132, 140 104, 188 100 S 250 96, 296 80 S 360 48, 404 46 S 470 70, 512 78 S 580 74, 620 64" stroke="#2a78d6"></path>
          </g>
          <circle cx="404" cy="46" r="8" fill="#ffffff" stroke="#2a78d6" stroke-width="3"></circle>
          <g transform="translate(424 18)"><rect width="{150 if mobile else 112}" height="{50 if mobile else 42}" rx="12" fill="{INK}"></rect>
            <text x="14" y="{20 if mobile else 18}" font-size="{15 if mobile else 11}" fill="#c9d3ea" font-family="Montserrat, sans-serif" font-weight="500">Lumi Milk · W4</text>
            <text x="14" y="{41 if mobile else 34}" font-size="{18 if mobile else 13}" fill="#ffffff" font-family="Montserrat, sans-serif" font-weight="700">640 mentions</text></g>
        </svg>"""
    trend = section(f"""<div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px">
        {h2('Mentions over time')}
        <div style="display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; font-weight: 500; color: {INK2}">{legend([('Lumi Milk', '#2a78d6'), ('Nutri Kid', ORANGE), ('Happi Dry', GREEN)], '12px')}</div>
      </div>
      {chart}""", "18px" if mobile else "22px 24px", "width: 100%")
    sov = section(f"""<div style="display: flex; flex-direction: column; gap: 10px">{h2('Share of voice')}
      {hbars('sov', 96 if mobile else 104, 44, gradient=True)}</div>""", "18px" if mobile else "22px 24px", "width: 100%")

    form = f"""<form role="search" aria-label="Find keywords for a product" style="display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px; padding: {'14px' if mobile else '16px'}; border-radius: 18px; background: rgba(47,91,234,0.06)">
        <label style="flex: 1 1 {'100%' if mobile else '220px'}; display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 500; color: {INK3}">Brand
          <span style="display: flex; align-items: center; gap: 8px; height: 46px; padding: 0 14px; border-radius: 14px; background: #ffffff; border: 1px solid rgba(47,91,234,0.18); color: {INK3}">{svg('search', 16, 2)}<input type="text" value="lumi" placeholder="Type any brand, e.g. enfa" style="flex: 1; min-width: 0; border: 0; outline: none; background: transparent; font-family: {FONT}; font-size: 14px; font-weight: 600; color: {INK}"></span></label>
        <label style="flex: 1 1 {'100%' if mobile else '260px'}; display: flex; flex-direction: column; gap: 6px; font-size: 12px; font-weight: 500; color: {INK3}">Product
          <span style="display: flex; align-items: center; gap: 8px; height: 46px; padding: 0 14px; border-radius: 14px; background: #ffffff; border: 1.5px solid {{{{accent}}}}; box-shadow: 0 6px 18px rgba(47,91,234,0.12); color: {INK3}">{svg('search', 16, 2)}<input type="text" value="lumi a2 gold" placeholder="Type any product, e.g. enfa A2" style="flex: 1; min-width: 0; border: 0; outline: none; background: transparent; font-family: {FONT}; font-size: 14px; font-weight: 600; color: {INK}"></span></label>
        <button type="submit" style="flex: {'1 1 100%' if mobile else '0 0 auto'}; height: 46px; padding: 0 20px; border-radius: 14px; border: 0; background: {{{{accent}}}}; color: #ffffff; font-family: {FONT}; font-size: 14px; font-weight: 700; box-shadow: 0 8px 18px rgba(47,91,234,0.28)">Find keywords</button>
        <div style="flex: 1 1 100%; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 12px; font-weight: 500; color: {INK2}; line-height: 1.5">
          <span style="color: {INK3}">Matched:</span>
          <span class="chip" data-tap style="padding: 4px 10px; border-radius: 13px; background: #ffffff; font-weight: 700">Brand · Lumi Milk</span>
          <span class="chip" data-tap style="padding: 4px 10px; border-radius: 13px; background: #ffffff; font-weight: 700">Product · Lumi Milk A2 Gold</span>
          <span style="color: {INK3}; flex: 1 1 220px">Accents optional · empty Product = brand-wide · unknown words → text search</span>
        </div>
      </form>"""
    facts = f"""<div style="display: grid; grid-template-columns: repeat({'2' if mobile else 'auto-fit'}, minmax({'0' if mobile else '150px'}, 1fr)); gap: 10px">
        <sc-for list="{{{{facts}}}}" as="f" hint-placeholder-count="5"><div class="card" data-tap style="padding: 12px 14px; border-radius: 16px; background: rgba(47,91,234,0.06)"><div style="font-size: 11px; font-weight: 500; color: {INK3}">{{{{f.label}}}}</div><div style="font-size: {'16' if mobile else '18'}px; font-weight: 700; margin-top: 4px; line-height: 1.25">{{{{f.value}}}}</div></div></sc-for>
      </div>"""
    cloud = f"""<figure style="flex: 2 1 380px; min-width: 0; margin: 0; padding: {'16px' if mobile else '22px'}; border-radius: 20px; background: #ffffff; border: 1px solid rgba(47,91,234,0.12); display: flex; flex-direction: column; gap: 14px">
        <figcaption style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 6px"><span style="font-size: 14px; font-weight: 600">Keyword cloud</span><span style="font-size: 11px; font-weight: 500; color: {INK3}">Bigger &amp; bolder = mentioned more</span></figcaption>
        <div style="flex: 1; min-height: {'260' if mobile else '360'}px; display: flex; flex-wrap: wrap; align-items: center; align-content: space-evenly; justify-content: space-evenly; gap: 8px {'14' if mobile else '20'}px; line-height: 1.1; text-align: center">
          <sc-for list="{{{{cloud}}}}" as="w" hint-placeholder-count="24"><span class="word" data-tap title="{{{{w.title}}}}" style="font-size: {{{{w.{'msize' if mobile else 'size'}}}}}; font-weight: {{{{w.weight}}}}; color: {{{{w.color}}}}">{{{{w.kw}}}}</span></sc-for>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 12px; padding-top: 12px; border-top: 1px solid rgba(16,24,40,0.06); font-size: 11px; font-weight: 500; color: {INK3}; line-height: 1.4">
          <span style="display: inline-flex; align-items: center; gap: 6px"><span style="display: inline-flex; gap: 2px"><span style="width: 8px; height: 8px; border-radius: 4px; background: {GREEN}"></span><span style="width: 8px; height: 8px; border-radius: 4px; background: {ORANGE}"></span><span style="width: 8px; height: 8px; border-radius: 4px; background: #b7791f"></span></span>Positive</span>
          {legend([('Neutral', INK3), ('Negative', '#d92d32')], '8px')}<span>Muted = fewer mentions</span>
        </div>
      </figure>"""
    if mobile:
        kw_list = f"""<div style="display: flex; flex-direction: column; gap: 10px">
        <sc-for list="{{{{kwRows}}}}" as="r" hint-placeholder-count="8"><div class="row" data-tap style="padding: 12px 14px; border-radius: 16px; background: #ffffff; border: 1px solid rgba(47,91,234,0.10); display: flex; flex-direction: column; gap: 6px">
          <div style="display: flex; align-items: center; gap: 8px"><b style="font-size: 15px; font-weight: 700; flex: 1">{{{{r.kw}}}}</b><span style="padding: 3px 9px; border-radius: 11px; background: {{{{r.typeBg}}}}; color: {{{{r.typeInk}}}}; font-size: 11px; font-weight: 700">{{{{r.type}}}}</span></div>
          <div style="display: flex; gap: 14px; font-size: 12px; font-weight: 500; color: {INK3}"><span><b style="color: {INK}; font-weight: 700">{{{{r.posts}}}}</b> posts</span><span>{{{{r.share}}}} of posts</span><span>NSR <b style="font-weight: 700; color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</b></span></div>
          <div style="font-size: 12px; color: {INK2}; line-height: 1.5">“{{{{r.example}}}}”</div>
        </div></sc-for></div>"""
    else:
        kw_list = f"""<div style="flex: 3 1 520px; min-width: 0" role="table" aria-label="Keywords">
        <div role="row" style="display: grid; grid-template-columns: minmax(96px, 1.1fr) 92px 58px 64px 64px minmax(160px, 2.4fr); gap: 10px; padding: 8px 12px; font-size: 12px; font-weight: 500; color: {INK3}; border-bottom: 1px solid rgba(16,24,40,0.08)"><span role="columnheader">Keyword</span><span role="columnheader">Type</span><span role="columnheader" style="text-align: right">Posts</span><span role="columnheader" style="text-align: right">Share</span><span role="columnheader" style="text-align: right">NSR</span><span role="columnheader">Example post</span></div>
        <sc-for list="{{{{kwRows}}}}" as="r" hint-placeholder-count="8"><div role="row" class="row" data-tap style="display: grid; grid-template-columns: minmax(96px, 1.1fr) 92px 58px 64px 64px minmax(160px, 2.4fr); gap: 10px; align-items: center; padding: 11px 12px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px">
          <span role="cell" style="font-weight: 700">{{{{r.kw}}}}</span><span role="cell"><span style="padding: 3px 9px; border-radius: 11px; background: {{{{r.typeBg}}}}; color: {{{{r.typeInk}}}}; font-size: 11px; font-weight: 700">{{{{r.type}}}}</span></span>
          <span role="cell" style="text-align: right; font-weight: 700">{{{{r.posts}}}}</span><span role="cell" style="text-align: right">{{{{r.share}}}}</span><span role="cell" style="text-align: right; font-weight: 700; color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</span><span role="cell" style="color: {INK2}; line-height: 1.45">{{{{r.example}}}}</span>
        </div></sc-for></div>"""
    product = section(f"""<div style="display: flex; flex-direction: column; gap: 16px">
      {h2('Product keywords', 'Every keyword people use when they talk about the selected product. <b style="font-weight: 600; color: #3b4459">Known</b> = industry vocabulary · <b style="font-weight: 600; color: #3b4459">Discovered</b> = recurring new phrases.')}
      {form}
      {facts}
      <div style="display: flex; flex-wrap: wrap; gap: {sp}px; align-items: stretch">{cloud}{kw_list}</div>
    </div>""", "18px" if mobile else "24px")

    if mobile:
        ranking_list = f"""<sc-for list="{{{{ranking}}}}" as="r" hint-placeholder-count="5"><div class="row" data-tap style="display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 10px 6px; border-bottom: 1px solid rgba(16,24,40,0.05)">
          <b style="font-weight: 800; color: {INK3}">{{{{r.rank}}}}</b>
          <div style="min-width: 0"><div style="font-weight: 700; font-size: 14px">{{{{r.name}}}}</div><div style="display: flex; gap: 10px; font-size: 11px; font-weight: 500; color: {INK3}; margin-top: 3px"><span>{{{{r.mentions}}}} mentions</span><span>SOV {{{{r.sov}}}}</span><span>NSR <b style="color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</b></span></div><span style="display: block; height: 6px; margin-top: 6px; border-radius: 3px; background: rgba(47,91,234,0.08)"><span class="bar" data-tap style="display: block; height: 6px; width: {{{{r.scoreW}}}}; border-radius: 3px; background: {{{{accent}}}}"></span></span></div>
          <div style="text-align: right"><div style="font-size: 18px; font-weight: 700">{{{{r.score}}}}</div><div style="font-size: 11px; font-weight: 700; color: {{{{r.buzzInk}}}}">{{{{r.buzz}}}}</div></div>
        </div></sc-for>"""
    else:
        cols = "34px minmax(110px, 1.4fr) minmax(130px, 1.6fr) 84px 56px 64px 64px"
        ranking_list = f"""<div role="table" aria-label="Brand ranking"><div role="row" style="display: grid; grid-template-columns: {cols}; gap: 10px; padding: 8px 10px; font-size: 12px; font-weight: 500; color: {INK3}; border-bottom: 1px solid rgba(16,24,40,0.08)"><span>#</span><span>Brand</span><span>Score</span><span style="text-align: right">Mentions</span><span style="text-align: right">SOV</span><span style="text-align: right">NSR</span><span style="text-align: right">Buzz</span></div>
        <sc-for list="{{{{ranking}}}}" as="r" hint-placeholder-count="5"><div role="row" class="row" data-tap style="display: grid; grid-template-columns: {cols}; gap: 10px; align-items: center; padding: 12px 10px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px">
          <b style="font-weight: 700; color: {INK3}">{{{{r.rank}}}}</b><b style="font-weight: 700">{{{{r.name}}}}</b>
          <span style="display: flex; align-items: center; gap: 8px"><span style="flex: 1; height: 8px; border-radius: 4px; background: rgba(47,91,234,0.08)"><span class="bar" data-tap style="display: block; height: 8px; width: {{{{r.scoreW}}}}; border-radius: 4px; background: {{{{accent}}}}"></span></span><b style="font-weight: 700">{{{{r.score}}}}</b></span>
          <span style="text-align: right">{{{{r.mentions}}}}</span><span style="text-align: right">{{{{r.sov}}}}</span><b style="text-align: right; font-weight: 700; color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</b><b style="text-align: right; font-weight: 700; color: {{{{r.buzzInk}}}}">{{{{r.buzz}}}}</b>
        </div></sc-for></div>"""
    ranking = section(f"""<div style="display: flex; flex-direction: column; gap: 8px">{h2('Brand ranking', 'Score = 45% mentions · 35% interactions · 20% NSR')}{ranking_list}</div>""",
                      "18px" if mobile else "22px 24px", "width: 100%")
    insights = f"""<section class="card" data-tap style="width: 100%; border-radius: 24px; padding: {'18px' if mobile else '22px 24px'}; background: linear-gradient(160deg, {INK} 0%, #1f2a4a 100%); color: #ffffff; box-shadow: 0 16px 36px rgba(16,24,40,0.25)">
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 12px"><span style="padding: 4px 10px; border-radius: 12px; background: rgba(255,255,255,0.12); font-size: 11px; font-weight: 700">Auto summary</span><span style="font-size: 12px; font-weight: 500; color: #c9d3ea">Updated 06:23 today</span></div>
      <h2 style="margin: 0 0 10px; font-size: 18px; font-weight: 600">Insights &amp; actions</h2>
      <ul style="margin: 0 0 14px; padding-left: 18px; font-size: 13px; line-height: 1.7; color: #e3e8f4"><li><b style="font-weight: 600; color: #ffffff">Lumi Milk</b> leads with 21% SOV, but NSR fell 8 pts on a counterfeit rumour.</li><li><b style="font-weight: 600; color: #ffffff">“đạm A2”</b> is the fastest-rising keyword (×8.5).</li><li><b style="font-weight: 600; color: #ffffff">Happi Dry</b> buzz <b style="color: #7ee2b0">+115%</b>, driven by TikTok reviews.</li></ul>
      <div style="font-size: 12px; font-weight: 600; color: #c9d3ea; margin-bottom: 6px">Recommended</div>
      <ol style="margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.7; color: #e3e8f4"><li>Publish an authenticity guide within 24h.</li><li>Build content around “đạm A2” in the next 5 days.</li></ol>
    </section>"""
    if mobile:
        main = "\n".join([kpis(True), trend, sov, product, ranking, insights])
    else:
        actions = f"""<div style="display: flex; gap: 10px"><button type="button" style="display: inline-flex; align-items: center; gap: 8px; height: 46px; padding: 0 18px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.95); background: rgba(255,255,255,0.75); font-family: {FONT}; font-size: 14px; font-weight: 600; color: {INK}">{svg('download', 18, 2.2)} Export report</button><button type="button" style="display: inline-flex; align-items: center; gap: 8px; height: 46px; padding: 0 18px; border-radius: 14px; border: 0; background: {{{{accent}}}}; font-family: {FONT}; font-size: 14px; font-weight: 700; color: #ffffff; box-shadow: 0 10px 24px rgba(47,91,234,0.3)">{svg('refresh', 18, 2.2)} Run scan now</button></div>"""
        main = "\n".join([header_desktop("Mother &amp; Baby · 01/10/2026 – 31/10/2026 · search “sữa công thức”", "Social Listening", "listening", BLUE, actions),
                          kpis(False), row2(trend, sov), product, row2(ranking, insights)])
    data = {
        "hero": {"label": "Mentions", "value": "5,412", "pill": "▲ +18%", "note": "vs September"},
        "kpis": [{"label": "Interactions", "value": "1.24M", "note": "▲ +11% vs September", "noteInk": UP, "noteWeight": 700, **look(PINK, "heart")},
                 {"label": "Net sentiment (NSR)", "value": "+41%", "note": "▼ −6 pts", "noteInk": DOWN, "noteWeight": 700, **look(GREEN, "smile")},
                 {"label": "Negative posts", "value": "486", "note": "▲ +23% – watch", "noteInk": DOWN, "noteWeight": 700, **look(ORANGE, "warn")},
                 {"label": "Alerts", "value": "12", "note": "▲ 3 high severity", "noteInk": DOWN, "noteWeight": 700, **look(AMBER, "bell")}],
        "sov": [{**b, "color": "{{accent}}"} for b in bar_rows(SOV, 21, BLUE, value_fmt=lambda v: f"{v}%")],
        "facts": [{"label": "Category", "value": "Infant formula"}, {"label": "Posts", "value": "214"},
                  {"label": "Share of brand talk", "value": "38%"}, {"label": "NSR", "value": "+36%"}, {"label": "Top source", "value": "TikTok"}],
        "cloud": kw_cloud(), "kwRows": kw_rows(6 if mobile else 8),
        "ranking": [{"rank": i + 1, "name": n, "score": f"{s:.2f}", "scoreW": f"{round(s * 100)}%", "mentions": m, "sov": sv,
                     "nsr": fmt_signed(nsr), "nsrInk": signed_ink(nsr), "buzz": fmt_signed(bz), "buzzInk": signed_ink(bz)}
                    for i, (n, s, m, sv, nsr, bz) in enumerate(RANKING)],
    }
    for b in data["sov"]:
        b["color"] = BLUE
    return main, data


def communities(mobile: bool) -> tuple[str, dict]:
    filters = f"""<div role="group" aria-label="Community type" class="{'hscroll' if mobile else ''}" style="display: flex; {'' if mobile else 'flex-wrap: wrap; '}gap: 6px; padding: 5px; border-radius: 16px; background: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.95)">
        <sc-for list="{{{{typeFilters}}}}" as="f" hint-placeholder-count="5"><button type="button" style="flex: 0 0 auto; height: 38px; padding: 0 14px; border: 0; border-radius: 12px; background: {{{{f.bg}}}}; color: {{{{f.ink}}}}; box-shadow: {{{{f.shadow}}}}; font-family: {FONT}; font-size: 13px; font-weight: 600; white-space: nowrap">{{{{f.label}}}}</button></sc-for>
      </div>"""
    comp_card = f"""<div class="card" data-tap style="{CARD}; border-radius: 20px; padding: {'12px' if mobile else '16px 18px'}; display: flex; align-items: center; gap: 12px; min-width: {'210px' if mobile else '0'}; {'flex: 0 0 auto' if mobile else ''}">
        {tile_hole('c', 42, 13, 20)}
        <div style="min-width: 0"><div style="display: flex; align-items: baseline; gap: 6px"><span style="font-size: 14px; font-weight: 700">{{{{c.label}}}}</span><span style="font-size: 12px; font-weight: 800; color: {{{{c.color}}}}">{{{{c.weight}}}}%</span></div><div style="font-size: 12px; font-weight: 500; color: {INK3}; line-height: 1.35; margin-top: 2px">{{{{c.hint}}}}</div></div>
      </div>"""
    comps = (f'<section aria-label="How the score works" class="hscroll" style="gap: 10px">' if mobile else
             '<section aria-label="How the score works" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px">') + \
        f'<sc-for list="{{{{components}}}}" as="c" hint-placeholder-count="5">{comp_card}</sc-for></section>'
    top_card = f"""<article class="card" data-tap style="border-radius: 24px; padding: {'18px' if mobile else '22px'}; background: {{{{t.cardBg}}}}; border: 1px solid rgba(255,255,255,0.95); box-shadow: 0 10px 30px rgba(47,91,234,0.08); display: flex; flex-direction: column; gap: 12px; min-width: 0">
        <div style="display: flex; align-items: center; gap: 12px">
          <span class="tile" style="flex: 0 0 44px; height: 44px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 800; color: {{{{t.medalInk}}}}; background: {{{{t.medal}}}}; box-shadow: inset 0 1px 0 rgba(255,255,255,.9), inset 0 -5px 10px rgba(16,24,40,.12), 0 8px 18px rgba(16,24,40,.12)">{{{{t.rank}}}}</span>
          <div style="min-width: 0"><div style="font-size: 12px; font-weight: 500; color: {INK3}">{{{{t.type}}}} · {{{{t.access}}}}</div><div style="font-size: 17px; font-weight: 700; line-height: 1.3">{{{{t.name}}}}</div></div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px"><span style="padding: 5px 11px; border-radius: 13px; font-size: 12px; font-weight: 700; background: {{{{t.tierBg}}}}; color: {{{{t.tierInk}}}}">{{{{t.tier}}}}</span><span style="font-size: 30px; font-weight: 700; letter-spacing: -0.03em">{{{{t.score}}}}</span></div>
        <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; gap: 2px; background: rgba(16,24,40,0.06)"><sc-for list="{{{{t.parts}}}}" as="p" hint-placeholder-count="5"><span class="bar" data-tap style="width: {{{{p.w}}}}; background: {{{{p.c}}}}"></span></sc-for></div>
        <div style="font-size: 12px; line-height: 1.6; color: {INK2}">{{{{t.summary}}}}</div>
        <div style="display: flex; gap: 10px; align-items: flex-start; padding: 12px; border-radius: 14px; background: {{{{t.recBg}}}}; color: {INK}">{svg('arrow', 18, 2.4).replace('aria-hidden', 'style="flex: 0 0 18px; margin-top: 1px" aria-hidden')}<span style="font-size: 13px; font-weight: 600; line-height: 1.45">{{{{t.rec}}}}</span></div>
      </article>"""
    top = (f'<section style="display: grid; grid-template-columns: {"minmax(0, 1fr)" if mobile else "repeat(auto-fit, minmax(300px, 1fr))"}; gap: 16px">'
           f'<sc-for list="{{{{top}}}}" as="t" hint-placeholder-count="3">{top_card}</sc-for></section>')
    quad_h = 300 if mobile else 330
    quadrant = section(f"""<div style="display: flex; flex-direction: column; gap: 12px">
      {h2('Relevance × reach', 'Top-right = on-topic and engaging → best place to be')}
      <div role="img" aria-label="Quadrant chart: communities 1 to 3 sit in the top-right" style="position: relative; height: {quad_h}px; border-radius: 18px; background: linear-gradient(135deg, rgba(14,159,110,0) 50%, rgba(14,159,110,0.12) 100%); border: 1px solid rgba(16,24,40,0.06); overflow: hidden">
        <span style="position: absolute; left: 50%; top: 0; bottom: 0; border-left: 1px dashed rgba(16,24,40,0.15)"></span>
        <span style="position: absolute; top: 50%; left: 0; right: 0; border-top: 1px dashed rgba(16,24,40,0.15)"></span>
        <span style="position: absolute; right: 10px; top: 10px; padding: 3px 8px; border-radius: 10px; background: rgba(255,255,255,0.8); font-size: 11px; font-weight: 700; color: {UP}">Go here</span>
        <span style="position: absolute; left: 10px; top: 10px; padding: 3px 8px; border-radius: 10px; background: rgba(255,255,255,0.8); font-size: 11px; font-weight: 600; color: {INK3}">Reach, off-topic</span>
        <span style="position: absolute; right: 10px; bottom: 10px; padding: 3px 8px; border-radius: 10px; background: rgba(255,255,255,0.8); font-size: 11px; font-weight: 600; color: {INK3}">Niche, on-topic</span>
        <sc-for list="{{{{rows}}}}" as="d" hint-placeholder-count="8"><span class="dot" data-tap title="{{{{d.name}}}} · score {{{{d.score}}}}" style="position: absolute; left: {{{{d.x}}}}; bottom: {{{{d.y}}}}; width: {{{{d.dot}}}}; height: {{{{d.dot}}}}; margin-left: -14px; margin-bottom: -14px; border-radius: 50%; background: {{{{d.tierColor}}}}; border: 2px solid #ffffff; box-shadow: 0 6px 14px rgba(16,24,40,0.2); color: #ffffff; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center">{{{{d.rank}}}}</span></sc-for>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 500; color: {INK3}"><span>On-topic share →</span><span>↑ Avg interactions / post</span></div>
      <ol style="margin: 0; padding: 0; list-style: none; display: grid; grid-template-columns: {'minmax(0, 1fr)' if mobile else 'repeat(2, minmax(0, 1fr))'}; gap: 6px 14px">
        <sc-for list="{{{{rows}}}}" as="d" hint-placeholder-count="8"><li class="row" data-tap style="display: flex; align-items: center; gap: 8px; padding: 4px; border-radius: 8px; font-size: 12px; font-weight: 500; color: {INK2}; line-height: 1.35"><span style="flex: 0 0 20px; height: 20px; border-radius: 10px; background: {{{{d.tierColor}}}}; color: #ffffff; font-size: 10px; font-weight: 800; display: flex; align-items: center; justify-content: center">{{{{d.rank}}}}</span>{{{{d.name}}}}</li></sc-for>
      </ol>
      <div style="display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; font-weight: 500; color: {INK2}">{legend([('High potential', GREEN), ('Worth testing', ORANGE), ('Monitor', '#8a93a6')], '10px')}</div>
    </div>""", "18px" if mobile else "22px 24px", "width: 100%")
    stack = '<span style="display: flex; flex: 1; height: 8px; border-radius: 4px; overflow: hidden; gap: 1px; background: rgba(16,24,40,0.06)"><sc-for list="{{r.parts}}" as="p" hint-placeholder-count="5"><span class="bar" data-tap style="width: {{p.w}}; background: {{p.c}}"></span></sc-for></span>'
    if mobile:
        table_body = f"""<sc-for list="{{{{rows}}}}" as="r" hint-placeholder-count="8"><div class="row" data-tap style="padding: 12px 6px; border-bottom: 1px solid rgba(16,24,40,0.05); display: flex; flex-direction: column; gap: 6px">
          <div style="display: flex; align-items: center; gap: 10px"><b style="flex: 0 0 22px; font-weight: 800; color: {INK3}">{{{{r.rank}}}}</b><div style="flex: 1; min-width: 0"><div style="font-weight: 700; font-size: 14px; line-height: 1.3">{{{{r.name}}}}</div><div style="font-size: 11px; font-weight: 500; color: {INK3}">{{{{r.type}}}}</div></div><span style="padding: 3px 9px; border-radius: 11px; font-size: 11px; font-weight: 700; background: {{{{r.accessBg}}}}; color: {{{{r.accessInk}}}}">{{{{r.access}}}}</span></div>
          <div style="display: flex; align-items: center; gap: 8px; padding-left: 32px">{stack}<b style="font-weight: 700">{{{{r.score}}}}</b></div>
          <div style="display: flex; flex-wrap: wrap; gap: 4px 12px; padding-left: 32px; font-size: 11px; font-weight: 500; color: {INK3}"><span>{{{{r.ppw}}}}/wk</span><span>{{{{r.rel}}}} on-topic</span><span>{{{{r.intent}}}} intent</span><span>NSR <b style="font-weight: 700; color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</b></span></div>
        </div></sc-for>"""
    else:
        cols = "34px minmax(170px, 2fr) 76px minmax(150px, 1.4fr) 72px 72px 82px 64px"
        table_body = f"""<div role="row" style="display: grid; grid-template-columns: {cols}; gap: 10px; padding: 8px 10px; font-size: 12px; font-weight: 500; color: {INK3}; border-bottom: 1px solid rgba(16,24,40,0.08)"><span>#</span><span>Community</span><span>Access</span><span>Score</span><span style="text-align: right">Posts/wk</span><span style="text-align: right">On-topic</span><span style="text-align: right">Intent</span><span style="text-align: right">NSR</span></div>
        <sc-for list="{{{{rows}}}}" as="r" hint-placeholder-count="8"><div role="row" class="row" data-tap style="display: grid; grid-template-columns: {cols}; gap: 10px; align-items: center; padding: 11px 10px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px">
          <b style="font-weight: 700; color: {INK3}">{{{{r.rank}}}}</b><span style="min-width: 0"><b style="display: block; font-weight: 700; line-height: 1.3">{{{{r.name}}}}</b><span style="font-size: 11px; font-weight: 500; color: {INK3}">{{{{r.type}}}}</span></span>
          <span><span style="padding: 3px 9px; border-radius: 11px; font-size: 11px; font-weight: 700; background: {{{{r.accessBg}}}}; color: {{{{r.accessInk}}}}">{{{{r.access}}}}</span></span>
          <span style="display: flex; align-items: center; gap: 8px">{stack}<b style="font-weight: 700">{{{{r.score}}}}</b></span>
          <span style="text-align: right">{{{{r.ppw}}}}</span><span style="text-align: right">{{{{r.rel}}}}</span><span style="text-align: right">{{{{r.intent}}}}</span><b style="text-align: right; font-weight: 700; color: {{{{r.nsrInk}}}}">{{{{r.nsr}}}}</b>
        </div></sc-for>"""
    table = section(f"""<div style="display: flex; flex-direction: column; gap: 8px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px">{h2('All communities')}<label class="chip" data-tap style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 12px; font-size: 13px; font-weight: 500; color: {INK2}"><input type="checkbox" style="width: 18px; height: 18px; margin: 0; accent-color: {PINK}"> Public only</label></div>
      <div role="table" aria-label="All communities">{table_body}</div></div>""", "18px" if mobile else "22px 24px", "width: 100%")
    if mobile:
        main = "\n".join([filters, comps, top, quadrant, table])
    else:
        comps_col = section(f"""<div style="display: flex; flex-direction: column; gap: 12px">{h2('How the score works', 'Five signals, weighted for marketing value')}
      <sc-for list="{{{{components}}}}" as="c" hint-placeholder-count="5">{comp_card.replace(CARD + '; ', 'background: rgba(47,91,234,0.04); ').replace('box-shadow: 0 10px 30px rgba(47,91,234,0.08)', 'box-shadow: none')}</sc-for></div>""",
                            "22px 24px", "width: 100%")
        main = "\n".join([header_desktop("Social Listening › Communities · Mother &amp; Baby · search “sữa công thức”", "Community Radar", "users", PINK, filters),
                          top, row2(comps_col, quadrant, "1 1 320px", "2 1 520px"), table])
    rows = community_rows()
    data = {"typeFilters": [{"label": l, "bg": PINK if i == 0 else "transparent", "ink": "#ffffff" if i == 0 else INK2,
                             "shadow": f"0 8px 18px {tint(PINK, 0.3)}" if i == 0 else "none"}
                            for i, l in enumerate(["All", "Facebook groups", "TikTok", "Instagram / Threads", "Forums"])],
            "components": [{"label": l, "weight": w, "hint": h, **look(c, i)} for l, w, h, c, i in COMPONENTS],
            "top": rows[:3], "rows": rows}
    return main, data


def research(mobile: bool) -> tuple[str, dict]:
    tabs = f"""<div role="tablist" aria-label="Research sections" style="display: flex; gap: 4px; padding: 5px; border-radius: 16px; background: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.95)">
        {''.join(f'<button type="button" role="tab" aria-selected="{str(i == 0).lower()}" style="flex: 1 1 auto; height: 38px; padding: 0 16px; border: 0; border-radius: 12px; background: {"#ffffff" if i == 0 else "transparent"}; box-shadow: {"0 6px 16px rgba(232,89,12,0.16)" if i == 0 else "none"}; font-family: {FONT}; font-size: 13px; font-weight: {700 if i == 0 else 500}; color: {INK if i == 0 else INK2}">{t}</button>' for i, t in enumerate(["Campaigns", "Keywords", "Trends"]))}
      </div>"""
    segs = f"""<div role="group" aria-label="Hospital segment" class="{'hscroll' if mobile else ''}" style="display: flex; {'' if mobile else 'flex-wrap: wrap; '}gap: 6px"><sc-for list="{{{{segments}}}}" as="s" hint-placeholder-count="5"><button type="button" style="flex: 0 0 auto; height: 34px; padding: 0 14px; border-radius: 17px; border: 1px solid rgba(47,91,234,0.14); background: {{{{s.bg}}}}; color: {{{{s.ink}}}}; font-family: {FONT}; font-size: 12px; font-weight: 700; white-space: nowrap">{{{{s.label}}}} · {{{{s.count}}}}</button></sc-for></div>"""
    if mobile:
        hosp_list = f"""<sc-for list="{{{{hospitals}}}}" as="h" hint-placeholder-count="7"><div class="row" data-tap style="padding: 12px 6px; border-bottom: 1px solid rgba(16,24,40,0.05); display: flex; flex-direction: column; gap: 6px">
          <div style="display: flex; align-items: flex-start; gap: 8px"><b style="flex: 1; font-weight: 700; font-size: 14px; line-height: 1.3">{{{{h.name}}}}</b><span style="flex: 0 0 auto; padding: 3px 9px; border-radius: 11px; font-size: 11px; font-weight: 700; background: {{{{h.segBg}}}}; color: {{{{h.segInk}}}}">{{{{h.segment}}}}</span></div>
          <div style="font-size: 12px; font-weight: 500; color: {INK3}">{{{{h.location}}}} · {{{{h.specialty}}}}</div>
          <div style="display: flex; gap: 14px; font-size: 12px; font-weight: 500; color: {INK3}"><span><b style="color: {INK}; font-weight: 700">{{{{h.mentions}}}}</b> mentions</span><span>NSR <b style="font-weight: 700; color: {{{{h.nsrInk}}}}">{{{{h.nsr}}}}</b></span></div>
          <div style="font-size: 12px; color: {INK2}">{{{{h.keywords}}}}</div>
        </div></sc-for>"""
    else:
        cols = "minmax(180px, 1.8fr) 116px 96px minmax(140px, 1.4fr) 80px 64px minmax(160px, 1.6fr)"
        hosp_list = f"""<div role="row" style="display: grid; grid-template-columns: {cols}; gap: 10px; padding: 8px 10px; font-size: 12px; font-weight: 500; color: {INK3}; border-bottom: 1px solid rgba(16,24,40,0.08)"><span>Hospital</span><span>Segment</span><span>Location</span><span>Specialty</span><span style="text-align: right">Mentions</span><span style="text-align: right">NSR</span><span>Top keywords</span></div>
        <sc-for list="{{{{hospitals}}}}" as="h" hint-placeholder-count="7"><div role="row" class="row" data-tap style="display: grid; grid-template-columns: {cols}; gap: 10px; align-items: center; padding: 11px 10px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px; line-height: 1.4">
          <b style="font-weight: 700">{{{{h.name}}}}</b><span><span style="display: inline-block; padding: 3px 9px; border-radius: 11px; font-size: 11px; font-weight: 700; background: {{{{h.segBg}}}}; color: {{{{h.segInk}}}}; white-space: nowrap">{{{{h.segment}}}}</span></span>
          <span style="color: {INK2}">{{{{h.location}}}}</span><span style="color: {INK2}">{{{{h.specialty}}}}</span><b style="text-align: right; font-weight: 700">{{{{h.mentions}}}}</b><b style="text-align: right; font-weight: 700; color: {{{{h.nsrInk}}}}">{{{{h.nsr}}}}</b><span style="color: {INK2}">{{{{h.keywords}}}}</span>
        </div></sc-for>"""
    hospitals = section(f"""<div style="display: flex; flex-direction: column; gap: 14px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px">{h2('Hospitals in the conversation', 'Public &amp; private hospitals in Vietnam, Asia and Europe')}{segs}</div>
      <div role="table" aria-label="Hospitals">{hosp_list}</div></div>""", "18px" if mobile else "22px 24px")
    activity = section(f"""<div style="display: flex; flex-direction: column; gap: 10px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px">{h2('Activity types')}<div style="display: flex; gap: 12px; font-size: 12px; font-weight: 500; color: {INK2}">{legend([('Online', BLUE), ('Offline', ORANGE)])}</div></div>
      {hbars('activities', 132 if mobile else 150, 40)}</div>""", "18px" if mobile else "22px 24px", "width: 100%")
    cell_w = "minmax(34px, 1fr)" if mobile else "minmax(44px, 1fr)"
    heat = section(f"""<div style="display: flex; flex-direction: column; gap: 12px">
      <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 8px">{h2('Brand × activity')}<span style="font-size: 12px; font-weight: 500; color: {INK3}">{'Swipe →' if mobile else 'Posts'}</span></div>
      <div style="{'overflow-x: auto; margin: 0 -4px; padding: 0 4px' if mobile else ''}"><div style="min-width: {'520px' if mobile else '0'}; display: flex; flex-direction: column; gap: 4px">
        <div style="display: grid; grid-template-columns: {'112px' if mobile else '138px'} repeat(8, {cell_w}); gap: 4px; font-size: 11px; font-weight: 600; color: {INK3}"><span></span><sc-for list="{{{{heatCols}}}}" as="c" hint-placeholder-count="8"><span style="text-align: center">{{{{c}}}}</span></sc-for></div>
        <sc-for list="{{{{heatRows}}}}" as="r" hint-placeholder-count="6"><div style="display: grid; grid-template-columns: {'112px' if mobile else '138px'} repeat(8, {cell_w}); gap: 4px">
          <span style="display: flex; align-items: center; font-size: 12px; font-weight: 600; color: {INK2}; line-height: 1.25">{{{{r.name}}}}</span>
          <sc-for list="{{{{r.cells}}}}" as="cell" hint-placeholder-count="8"><span class="cell" data-tap style="height: 36px; border-radius: 10px; background: {{{{cell.bg}}}}; color: {{{{cell.ink}}}}; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700">{{{{cell.v}}}}</span></sc-for>
        </div></sc-for>
      </div></div></div>""", "18px" if mobile else "22px 24px", "width: 100%")
    trends = section(f"""<div style="display: flex; flex-direction: column; gap: 10px">{h2('Rising phrases', 'Lift vs the previous period of equal length')}{hbars('trends', 150 if mobile else 180, 48, gradient=True)}</div>""",
                     "18px" if mobile else "22px 24px", "width: 100%")
    suggest = section(f"""<div style="display: flex; flex-direction: column; gap: 10px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 10px">{h2('What people search for', 'Google Autocomplete rank · not search volume')}
        <label style="display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 500; color: {INK3}">Seed keyword<select style="height: 40px; border-radius: 12px; border: 1px solid rgba(47,91,234,0.18); background: #ffffff; padding: 0 10px; font-family: {FONT}; font-size: 13px; font-weight: 600; color: {INK}"><option selected="selected">bệnh viện tư</option><option>khám dịch vụ</option><option>đi singapore khám bệnh</option></select></label></div>
      <ol style="margin: 0; padding: 0; list-style: none"><sc-for list="{{{{suggest}}}}" as="s" hint-placeholder-count="6"><li class="row" data-tap style="display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 6px; border-radius: 10px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px">
        <b style="width: 18px; font-weight: 700; color: {INK3}">{{{{s.rank}}}}</b><span style="flex: 1; font-weight: 500; line-height: 1.35">{{{{s.text}}}}</span>
        <sc-if value="{{{{s.isNew}}}}" hint-placeholder-val="{{{{false}}}}"><span style="padding: 3px 9px; border-radius: 11px; background: #dcfae6; color: {UP}; font-size: 11px; font-weight: 700">▲ New</span></sc-if></li></sc-for></ol></div>""",
                      "18px" if mobile else "22px 24px", "width: 100%")
    if mobile:
        main = "\n".join([tabs, kpis(True), hospitals, activity, heat, trends, suggest])
    else:
        main = "\n".join([header_desktop("Healthcare · 01/01/2026 – 17/11/2026 · search “bệnh viện tư”", "Marketing Research", "research", ORANGE, tabs),
                          kpis(False), hospitals, row2(activity, heat, "2 1 360px", "3 1 560px"), row2(trends, suggest, "1 1 360px", "1 1 360px")])
    seg_data = []
    for i, (l, n) in enumerate([("All", 109), ("Public · VN", 35), ("Private · VN", 19), ("Asia", 23), ("Europe", 13)]):
        seg_data.append({"label": l, "count": n, "bg": ORANGE if i == 0 else "rgba(255,255,255,0.85)", "ink": "#ffffff" if i == 0 else INK2})
    data = {
        "hero": {"label": "Marketing activity posts", "value": "1,906", "pill": "▲ +16%", "note": "vs same period 2025"},
        "kpis": [{"label": "Brands & hospitals active", "value": "64 / 109", "note": "▲ +9 vs 2025", "noteInk": UP, "noteWeight": 700, **look(BLUE, "users")},
                 {"label": "Offline share", "value": "35%", "note": "Events, free check-ups", "noteInk": FLAT, "noteWeight": 500, **look(ORANGE, "pin")},
                 {"label": "Campaign hashtags", "value": "138", "note": "▲ +22 new this month", "noteInk": UP, "noteWeight": 700, **look(PINK, "hash")},
                 {"label": "New search suggestions", "value": "17", "note": "Google Autocomplete", "noteInk": FLAT, "noteWeight": 500, **look(GREEN, "spark")}],
        "segments": seg_data,
        "hospitals": [{"name": n, "segment": s, "location": loc, "specialty": sp, "mentions": m, "nsr": fmt_signed(nsr),
                       "nsrInk": signed_ink(nsr), "keywords": kw, "segBg": tint(SEG[s][0], 0.12), "segInk": SEG[s][1]}
                      for n, s, loc, sp, m, nsr, kw in HOSPITALS[: 5 if mobile else 7]],
        "activities": bar_rows(ACTIVITIES, 412, lambda r: BLUE if r[2] == "on" else ORANGE),
        "heatCols": HEAT_COLS, "heatRows": [{"name": n, "cells": [heat_scale(v) for v in vals]} for n, vals in HEAT],
        "trends": bar_rows(TRENDS, 8.5, ORANGE, value_fmt=lambda v: f"×{v}", color2="#ffc078"),
        "suggest": [{"rank": i + 1, "text": t, "isNew": n} for i, (t, n) in enumerate(SUGGEST)],
    }
    return main, data


def alerts(mobile: bool) -> tuple[str, dict]:
    alert_card = f"""<article class="card" data-tap style="border-radius: 20px; padding: 16px 18px; background: {{{{a.bg}}}}; border: 1px solid {{{{a.border}}}}; box-shadow: {{{{a.shadow}}}}; color: {{{{a.ink}}}}; display: flex; flex-direction: column; gap: 8px">
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px"><span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; background: {{{{a.badgeBg}}}}; color: {{{{a.badgeInk}}}}; font-size: 11px; font-weight: 700">{svg('warn', 12, 2.6)} {{{{a.level}}}}</span><span style="font-size: 12px; font-weight: 500; color: {{{{a.muted}}}}">{{{{a.time}}}} · {{{{a.rule}}}}</span></div>
        <div style="font-size: 15px; font-weight: 600; line-height: 1.4">{{{{a.title}}}}</div>
        <div style="font-size: 13px; line-height: 1.5; color: {{{{a.muted}}}}">{{{{a.detail}}}}</div>
      </article>"""
    alert_list = f'<div style="display: flex; flex-direction: column; gap: 12px; width: 100%"><sc-for list="{{{{alerts}}}}" as="a" hint-placeholder-count="5">{alert_card}</sc-for></div>'
    hours = section(f"""<div style="display: flex; flex-direction: column; gap: 14px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px">{h2('Lumi Milk · negative posts per hour')}<span style="font-size: 12px; font-weight: 600; color: {DOWN}">Peak 18 at 09:00 · normal 2.3 / day</span></div>
      <div style="display: flex; align-items: flex-end; gap: {3 if mobile else 5}px; height: {120 if mobile else 150}px"><sc-for list="{{{{hours}}}}" as="h" hint-placeholder-count="24"><span class="vbar" data-tap title="{{{{h.title}}}}" style="flex: 1; height: {{{{h.height}}}}; background: {{{{h.color}}}}; border-radius: {6 if mobile else 8}px"></span></sc-for></div>
      <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 500; color: {INK3}"><span>15:00</span><span>21:00</span><span>03:00</span><span>09:00</span><span>14:00</span></div></div>""",
                    "18px" if mobile else "22px 24px", "width: 100%")
    risks = section(f"""<div style="display: flex; flex-direction: column; gap: 10px">{h2('Risk keywords')}{hbars('risks', 90, 32)}</div>""", "18px" if mobile else "22px 24px", "width: 100%")
    playbook = section(f"""<div style="display: flex; flex-direction: column; gap: 12px">{h2('Response playbook')}
      <sc-for list="{{{{playbook}}}}" as="p" hint-placeholder-count="4"><label class="row" data-tap style="display: flex; gap: 10px; align-items: flex-start; padding: 6px; border-radius: 10px; font-size: 13px; font-weight: 500; line-height: 1.45"><input type="checkbox" checked="{{{{p.done}}}}" style="flex: 0 0 18px; width: 18px; height: 18px; margin: 1px 0 0; accent-color: {GREEN}"> {{{{p.text}}}}</label></sc-for></div>""",
                       "18px" if mobile else "22px 24px", "width: 100%")
    if mobile:
        posts_list = f"""<sc-for list="{{{{posts}}}}" as="p" hint-placeholder-count="4"><div class="row" data-tap style="padding: 12px 6px; border-bottom: 1px solid rgba(16,24,40,0.05); display: flex; flex-direction: column; gap: 6px">
          <div style="display: flex; gap: 10px; font-size: 12px; font-weight: 600; color: {INK3}"><span>{{{{p.time}}}}</span><span>{{{{p.source}}}}</span><span style="margin-left: auto; color: {INK}; font-weight: 700">{{{{p.interactions}}}} interactions</span></div>
          <div style="font-size: 13px; line-height: 1.5">{{{{p.text}}}}</div><button type="button" style="border: 0; padding: 0; background: none; font-family: {FONT}; color: #1f43c4; font-weight: 700; font-size: 12px; text-align: left">Open post</button></div></sc-for>"""
    else:
        cols = "62px 84px minmax(240px, 1fr) 96px 56px"
        posts_list = f"""<div role="row" style="display: grid; grid-template-columns: {cols}; gap: 10px; padding: 8px 10px; font-size: 12px; font-weight: 500; color: {INK3}; border-bottom: 1px solid rgba(16,24,40,0.08)"><span>Time</span><span>Source</span><span>Post</span><span style="text-align: right">Interactions</span><span></span></div>
        <sc-for list="{{{{posts}}}}" as="p" hint-placeholder-count="4"><div role="row" class="row" data-tap style="display: grid; grid-template-columns: {cols}; gap: 10px; align-items: center; padding: 11px 10px; border-radius: 12px; border-bottom: 1px solid rgba(16,24,40,0.05); font-size: 13px; line-height: 1.45"><span style="color: {INK3}">{{{{p.time}}}}</span><span style="font-weight: 600">{{{{p.source}}}}</span><span>{{{{p.text}}}}</span><b style="text-align: right; font-weight: 700">{{{{p.interactions}}}}</b><button type="button" style="border: 0; padding: 0; background: none; font-family: {FONT}; color: #1f43c4; font-weight: 700; font-size: 13px">Open</button></div></sc-for>"""
    posts = section(f"""<div style="display: flex; flex-direction: column; gap: 8px">{h2('Most-shared posts')}<div role="table" aria-label="Most-shared posts">{posts_list}</div></div>""",
                    "18px" if mobile else "22px 24px", "width: 100%")
    if mobile:
        main = "\n".join([alert_list, hours, risks, playbook, posts])
    else:
        detail = f'<div style="display: flex; flex-direction: column; gap: 20px; width: 100%">{hours}{row2(risks, playbook, "1 1 260px", "1 1 260px")}{posts}</div>'
        main = "\n".join([header_desktop("Mother &amp; Baby · last 24 hours", "Alerts &amp; crisis", "bell", AMBER),
                          row2(alert_list, detail, "2 1 340px", "3 1 560px")])
    high = {"bg": "linear-gradient(135deg, #e5484d 0%, #f07a6a 100%)", "border": "transparent", "shadow": "0 14px 30px rgba(229,72,77,0.28)",
            "ink": "#ffffff", "muted": "rgba(255,255,255,0.9)", "badgeBg": "rgba(255,255,255,0.22)", "badgeInk": "#ffffff"}
    med = {"bg": "rgba(255,255,255,0.74)", "border": "rgba(255,255,255,0.95)", "shadow": "0 10px 30px rgba(47,91,234,0.08)",
           "ink": INK, "muted": INK3, "badgeBg": "#fdead7", "badgeInk": "#93370d"}
    data = {
        "alerts": [{**(high if lv == "High" else med), "level": lv, "time": t, "rule": r, "title": ti, "detail": de}
                   for lv, t, r, ti, de in ALERTS],
        "hours": [{"height": f"{max(4, round(c / 18 * 100))}%", "title": f"{(15 + i) % 24:02d}:00 · {c} negative posts",
                   "color": "linear-gradient(180deg, #e5484d, #f59a8f)" if c >= 10 else "rgba(229,72,77,0.25)"} for i, c in enumerate(HOURS)],
        "risks": bar_rows(RISKS, 12, "#e5484d"),
        "playbook": [{"text": t, "done": d} for t, d in [("Verify the source and batch numbers", True), ("Publish an official statement (≤ 24h)", False),
                                                          ("Brief customer care &amp; fanpage admins".replace("&amp;", "&"), False), ("Share a genuine-vs-fake checking guide", False)]],
        "posts": [{"time": t, "source": s, "text": x, "interactions": n} for t, s, x, n in POSTS],
    }
    return main, data


# ============================================================ BUILD
def build() -> dict[str, tuple[int, int]]:
    sidebar()
    mobile_topbar()
    mobile_tabbar()
    sizes = {}
    pages = [
        ("Main", "M_Listening", "listening", listening, "Social Listening", "Overview", "Mother & Baby", "sữa công thức", ("01/10/2026", "31/10/2026"), "01/10 – 31/10/2026"),
        ("Communities", "M_Communities", "communities", communities, "Social Listening", "Community Radar", "Mother & Baby", "sữa công thức", ("01/10/2026", "31/10/2026"), "01/10 – 31/10/2026"),
        ("Research", "M_Research", "research", research, "Marketing Research", "Healthcare", "Healthcare", "bệnh viện tư", ("01/01/2026", "17/11/2026"), "01/01 – 17/11/2026"),
        ("Alerts", "M_Alerts", "alerts", alerts, "Alerts", "Crisis · last 24h", "Mother & Baby", "", ("16/11/2026", "17/11/2026"), "Last 24 hours"),
    ]
    for desk, mob, key, fn, section_name, mtitle, industry, query, (d1, d2), mrange in pages:
        main, data = fn(False)
        body = frame_desktop(key, industry, query, d1, d2, main)
        write(f"{desk}.dc.html", page(f"VN Listen – {desk}", body, data, {**ACCENT_PROP, "$preview": {"width": 1440, "height": 2000}}))
        main, data = fn(True)
        body = frame_mobile(key, section_name, mtitle, industry, query, mrange, main)
        write(f"{mob}.dc.html", page(f"VN Listen – {mob}", body, data, {**ACCENT_PROP, "$preview": {"width": 390, "height": 2400}}))
    return sizes


if __name__ == "__main__":
    build()
    print("built", sorted(p.name for p in OUT.glob("*.dc.html")))
