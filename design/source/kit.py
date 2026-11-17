"""Shared design kit for the VN Listen canvas: CSS (incl. haptic-feel interactions), icons, building blocks.

Every interactive thing carries `data-tap` (or is a native control) so the same hover / press feedback and the
same haptic tick apply everywhere: buttons, links, chips, cards, chart bars, heat-map cells, table rows, dots.
"""
from __future__ import annotations

import json

FONT = "Montserrat, system-ui, sans-serif"
BG = "linear-gradient(160deg, #f3f5ff 0%, #e4eafd 45%, #d3ddfb 100%)"
INK, INK2, INK3 = "#101828", "#3b4459", "#5b6478"
UP, DOWN, FLAT = "#067647", "#c01c28", "#5b6478"
# Module / accent palette (MKT-friendly): blue · pink · orange · amber · green · violet
BLUE, PINK, ORANGE, AMBER, GREEN, VIOLET = "#2f5bea", "#d6336c", "#e8590c", "#c27c00", "#0e9f6e", "#6250d6"
RGB = {BLUE: "47,91,234", PINK: "214,51,108", ORANGE: "232,89,12", AMBER: "245,159,0", GREEN: "14,159,110",
       VIOLET: "98,80,214"}

CARD = ("border-radius: 24px; background: rgba(255,255,255,0.74); border: 1px solid rgba(255,255,255,0.95); "
        "box-shadow: 0 10px 30px rgba(47,91,234,0.08)")

CSS = """body{margin:0;font-family:Montserrat,system-ui,sans-serif;color:#101828;background:#e4eafd}
*{box-sizing:border-box}
a{color:#1f43c4}a:hover{color:#142c86}
/* ---- One interaction language for everything clickable (+ haptic tick from the page script) ---- */
button,a,select,input,label,[data-tap]{-webkit-tap-highlight-color:transparent}
button,a.btn,[data-tap]{cursor:pointer;transition:transform .16s cubic-bezier(.3,.7,.4,1.5),box-shadow .16s ease,filter .16s ease,background-color .16s ease}
button:hover,a.btn:hover{transform:translateY(-1px)}
button:active,a.btn:active,[data-tap]:active{transform:scale(.96)}
.card[data-tap]:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(47,91,234,.16)}
.card[data-tap]:active{transform:translateY(-1px) scale(.985)}
.bar{transform-origin:left center}
.bar[data-tap]:hover{filter:brightness(1.08) saturate(1.2);transform:scaleY(1.4)}
.vbar[data-tap]:hover{filter:brightness(1.1) saturate(1.2)}
.row[data-tap]:hover{background:rgba(47,91,234,.05)}
.row[data-tap]:active{transform:scale(.99)}
.cell[data-tap]:hover{transform:scale(1.08);box-shadow:0 6px 14px rgba(16,24,40,.18)}
.dot[data-tap]:hover{transform:scale(1.2)}
.chip[data-tap]:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(47,91,234,.14)}
.word[data-tap]:hover{transform:scale(1.08)}
.tile{transition:transform .22s cubic-bezier(.3,.7,.4,1.6),box-shadow .22s ease}
[data-tap]:hover .tile,a:hover .tile{transform:rotate(-8deg) scale(1.08)}
[data-tap]:active .tile,a:active .tile{transform:scale(.9)}
.hscroll{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.hscroll::-webkit-scrollbar{display:none}"""

# Haptic tick: pages register ONE listener; components (sidebar / bars) rely on it.
HAPTIC_JS = """  componentDidMount() {
    // Haptic tick for every control, chart bar, card, row… (Android Chrome; other devices get the visual press)
    this._tap = (e) => {
      const t = e.target && e.target.closest ? e.target.closest('button,a,select,input,label,[data-tap]') : null;
      if (!t) return;
      try { if (navigator.vibrate) navigator.vibrate(t.matches('button,a') ? 10 : 6); } catch (err) { /* unsupported */ }
    };
    document.addEventListener('pointerdown', this._tap, { passive: true });
  }
  componentWillUnmount() {
    document.removeEventListener('pointerdown', this._tap);
  }
"""

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
    "search": '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="3"></rect><path d="M8 3v4M16 3v4M3.5 10h17"></path>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"></path>',
    "chevron": '<path d="m6 9 6 6 6-6"></path>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 19V7.5A1.5 1.5 0 0 1 5.5 6H10"></path>',
    "download": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"></path>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.6-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5L20 16M20 20v-4h-4"></path>',
    "trend": '<path d="M3 17 9 11l4 4 8-8M15 7h6v6"></path>',
    "shield": '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"></path><path d="m9 12 2 2 4-4"></path>',
}


def svg(name: str, size: int = 20, width: float = 2.5) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def icon_switch(var: str, size: int = 20) -> str:
    """Icon chosen by data: var.ic = 'heart' -> renders only that icon (one sc-if per icon)."""
    return "".join(f'<sc-if value="{{{{{var}.ic_{k}}}}}" hint-placeholder-val="{{{{false}}}}">{svg(k, size)}</sc-if>'
                   for k in ICONS)


def ic(name: str) -> dict:
    return {f"ic_{name}": True}


def tile_style(color: str, size: int = 44, radius: int = 14, strong: bool = False) -> str:
    rgb = RGB.get(color, "47,91,234")
    t = 0.3 if strong else 0.2
    return (f"flex: 0 0 {size}px; width: {size}px; height: {size}px; border-radius: {radius}px; display: flex; "
            f"align-items: center; justify-content: center; color: {color}; "
            f"background: linear-gradient(150deg, #ffffff 0%, rgba({rgb},{t}) 100%); "
            f"border: 1px solid rgba(255,255,255,0.95); box-shadow: inset 0 1px 0 #ffffff, "
            f"inset 0 -5px 10px rgba({rgb},0.18), 0 8px 18px rgba({rgb},{t})")


def tile(icon: str, color: str, size: int = 44, radius: int = 14, isz: int = 22) -> str:
    return f'<span class="tile" style="{tile_style(color, size, radius)}">{svg(icon, isz)}</span>'


def tile_hole(var: str, size: int = 44, radius: int = 14, isz: int = 22) -> str:
    """Tile whose colours come from data: var.color, var.tint, var.inner."""
    return (f'<span class="tile" style="flex: 0 0 {size}px; width: {size}px; height: {size}px; border-radius: {radius}px; '
            f'display: flex; align-items: center; justify-content: center; color: {{{{{var}.color}}}}; '
            f'background: linear-gradient(150deg, #ffffff 0%, {{{{{var}.tint}}}} 100%); border: 1px solid rgba(255,255,255,0.95); '
            f'box-shadow: inset 0 1px 0 #ffffff, inset 0 -5px 10px {{{{{var}.inner}}}}, 0 8px 18px {{{{{var}.tint}}}}">'
            f'{icon_switch(var, isz)}</span>')


def tint(color: str, a: float = 0.2) -> str:
    return f"rgba({RGB.get(color, '47,91,234')},{a})"


def look(color: str, icon: str) -> dict:
    return {"color": color, "tint": tint(color, 0.2), "inner": tint(color, 0.16), **ic(icon)}


def h2(title: str, sub: str = "", size: int = 18) -> str:
    s = f'<h2 style="margin: 0; font-size: {size}px; font-weight: 600; line-height: 1.3">{title}</h2>'
    if sub:
        s += f'<div style="font-size: 12px; font-weight: 500; color: {INK3}; line-height: 1.5; margin-top: 4px">{sub}</div>'
    return f"<div>{s}</div>"


def page(title: str, body: str, data: dict, props: dict, extra_methods: str = "", haptics: bool = True) -> str:
    """Whole .dc.html file. `data` is precomputed JSON; `accent` stays a live tweak."""
    payload = json.dumps(data, ensure_ascii=False, indent=1)
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
{CSS}
</style>
</helmet>
{body}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{props_json}'>
class Component extends DCLogic {{
{HAPTIC_JS if haptics else ''}{extra_methods}  renderVals() {{
    // Illustrative data (fictional brands / communities). Edit freely.
    const D = {payload};
    return {{ ...D, accent: this.props.accent ?? '#2f5bea' }};
  }}
}}
</script>
</body>
</html>
"""


ACCENT_PROP = {"accent": {"editor": "color", "default": "#2f5bea", "options": ["#2f5bea", "#6250d6", "#0e9f6e", "#e8590c"]}}


def fmt_signed(n: float, suffix: str = "%") -> str:
    return ("+" if n > 0 else "−" if n < 0 else "") + f"{abs(n):g}{suffix}"


def signed_ink(n: float) -> str:
    return UP if n > 0 else DOWN if n < 0 else FLAT
