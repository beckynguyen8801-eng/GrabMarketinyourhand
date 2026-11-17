"""Dashboard – run: vnlisten dashboard  (or: streamlit run dashboard/app.py -- --db data/demo.db)

app.py only: read filters (industry, module, date range, search, sources) -> build ViewContext -> call the view.
Each module is one file in views/ (SRP). New module = one view + one line in MODULES.
UI language is English; data and search input are Vietnamese.
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from ui import SOURCE_LABELS, ViewContext, apply_theme
from views import listening, research

from vnlisten.analytics import keywords, metrics
from vnlisten.container import Settings
from vnlisten.domain.models import Module
from vnlisten.storage.sqlite_repo import SqliteRepository
from vnlisten.taxonomy import IndustryRegistry

MODULES = {
    Module.SOCIAL_LISTENING: ("Social Listening", listening.render),
    Module.RESEARCH: ("Marketing Research", research.render),
}

st.set_page_config(page_title="VN Listen", page_icon="📊", layout="wide")
apply_theme()


def _db_path() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return Path(args.db) if args.db else Settings.from_env().db_path


DB_PATH = _db_path()


@st.cache_resource
def registry() -> IndustryRegistry:
    return IndustryRegistry.from_dir(Settings.from_env().industries_dir)


@st.cache_resource
def repo() -> SqliteRepository:
    return SqliteRepository(DB_PATH)


@st.cache_data(ttl=300)
def load_frame(industry: str, since: datetime, until: datetime) -> pd.DataFrame:
    return metrics.to_frame(repo().load_mentions(since, until, industry))


# ================= Sidebar =================
reg = registry()
today = date.today()
with st.sidebar:
    st.markdown("<h2 style='margin:0 0 4px;font-weight:800'>VN Listen</h2>", unsafe_allow_html=True)
    st.caption("Social listening & marketing research")
    industry = st.selectbox("Industry", reg.ids(), format_func=lambda i: reg.get(i).name)
    tax = reg.get(industry)
    module = st.radio("Module", list(MODULES), format_func=lambda m: MODULES[m][0])
    st.divider()

    picked = st.date_input("Date range", value=(today - timedelta(days=6), today), max_value=today,
                           format="DD/MM/YYYY", help="Any period, e.g. 01/10/2026 – 31/10/2026")
    # While the user is still picking, Streamlit returns a 1-item tuple
    if isinstance(picked, tuple):
        start, end = (picked[0], picked[-1]) if picked else (today, today)
    else:
        start = end = picked

    query = st.text_input("Search", placeholder="e.g. sữa công thức, Enfa A+, bv Bạch Mai",
                          help="Any word or phrase – Vietnamese, with or without accents. "
                               "Matches post content and brand / product / hospital names.")

span = timedelta(days=(end - start).days + 1)
until = datetime.combine(end, time.max, tzinfo=UTC)
since = datetime.combine(start, time.min, tzinfo=UTC)
raw = load_frame(industry, since - span, until)   # current + previous period of equal length

with st.sidebar:
    all_sources = sorted(raw["source"].unique()) if not raw.empty else []
    sources = st.multiselect("Sources", all_sources, default=all_sources,
                             format_func=lambda s: SOURCE_LABELS.get(s, s))
    if query:
        tracked = {kw for _, kw in repo().watchlist(industry)}
        if query.strip() in tracked:
            st.caption(f"“{query}” is tracked daily.")
        elif st.button(f"Track “{query}” daily", width="stretch"):
            repo().add_watch(industry, query)
            st.toast(f"“{query}” will be collected in the next daily run.")
    if st.button("Refresh data", width="stretch"):
        st.cache_data.clear()
    st.caption(f"Database: `{DB_PATH.name}`")

# ================= Header =================
st.title(MODULES[module][0])
st.caption(f"{tax.name} · {start:%d/%m/%Y} – {end:%d/%m/%Y}" + (f" · search: “{query}”" if query else ""))
if "demo" in DB_PATH.name:
    st.info("You are viewing **demo data** – not real market data.", icon="🧪")
if raw.empty:
    st.info(f"No data for **{tax.name}** in this period. Run `vnlisten daily` to collect, "
            "or `vnlisten seed-demo` then `vnlisten --db data/demo.db dashboard` for a demo.")
    st.stop()

by_source = raw[raw["source"].isin(sources)]
df_all = keywords.search(by_source, query, tax)
if query and df_all.empty:
    st.warning(f"No posts match “{query}” in this period. Use **Track** in the sidebar to start collecting it.")
    st.stop()

ctx = ViewContext(
    tax=tax, repo=repo(), now=datetime.now(UTC), start=start, end=end, query=query, df_all=df_all,
    cur=df_all[df_all["published_at"] >= pd.Timestamp(since)],
    prev=df_all[df_all["published_at"] < pd.Timestamp(since)],
    base_cur=by_source[by_source["published_at"] >= pd.Timestamp(since)],
)
MODULES[module][1](ctx)
