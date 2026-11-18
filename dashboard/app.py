"""Dashboard – run: vnlisten dashboard  (or: streamlit run dashboard/app.py -- --db data/demo.db)

app.py only: read filters (industry, module, date range, search, sources) -> build ViewContext -> call the view.
Each module is one file in views/ (SRP). New module = one view + one line in MODULES.
UI language is English; data and search input are Vietnamese.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import design
from ui import SOURCE_LABELS, ViewContext
from views import alerts, communities, listening, research

from vnlisten.analytics import keywords, metrics
from vnlisten.container import Settings
from vnlisten.storage.sqlite_repo import SqliteRepository
from vnlisten.taxonomy import IndustryRegistry

# Same 4 modules as the approved design (icon + colour live in design.MODULES)
MODULES = {"listening": listening.render, "communities": communities.render,
           "research": research.render, "alerts": alerts.render}

st.set_page_config(page_title="VN Listen", page_icon="📊", layout="wide")
st.markdown(design.CSS, unsafe_allow_html=True)

# ---- Cloud mode (Streamlit Community Cloud): settings come from st.secrets, DB comes from the repo's `data` branch
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str | int | float):
            os.environ.setdefault(_k, str(_v))
except Exception:  # noqa: BLE001 – no secrets file locally
    pass
os.environ.setdefault("VNLISTEN_INDUSTRIES_DIR", str(Path(__file__).resolve().parents[1] / "config" / "industries"))
REMOTE_REPO = os.environ.get("VNLISTEN_REMOTE_REPO", "")


class NoRemoteData(Exception):
    """Raised (not returned) so Streamlit does NOT cache the 'no data yet' answer."""


@st.cache_data(ttl=600, show_spinner="Loading latest data…")
def remote_db() -> str:
    """Download the newest DB (refreshed every 10 min). Only successful downloads are cached."""
    from vnlisten.remote_db import download_db  # noqa: PLC0415

    dest = Path(tempfile.gettempdir()) / f"vnlisten-{datetime.now(UTC):%Y%m%d%H%M%S}.db"
    if not download_db(REMOTE_REPO, dest, os.environ.get("GITHUB_TOKEN", "")):
        raise NoRemoteData
    return str(dest)


def _db_path() -> Path:
    if REMOTE_REPO:
        try:
            return Path(remote_db())
        except NoRemoteData:
            st.info("No data yet. Run the **Collect data** workflow once in GitHub → Actions (see DEPLOY.md). "
                    "If it has already finished, check that GITHUB_TOKEN in the app secrets can read this repo.")
            st.stop()
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return Path(args.db) if args.db else Settings.from_env().db_path


DB_PATH = _db_path()


@st.cache_resource
def registry() -> IndustryRegistry:
    return IndustryRegistry.from_dir(Settings.from_env().industries_dir)


@st.cache_resource
def _repo_for(path: str) -> SqliteRepository:
    return SqliteRepository(path)


def repo() -> SqliteRepository:
    return _repo_for(str(DB_PATH))


@st.cache_data(ttl=300)
def load_frame(industry: str, since: datetime, until: datetime, db: str = "") -> pd.DataFrame:
    return metrics.to_frame(repo().load_mentions(since, until, industry))


# ================= Sidebar =================
# State lives in the URL (?module=&industry=&q=&from=&to=) so the module menu links keep it when switching.
reg = registry()
today = date.today()
qp = st.query_params


def _date(v: str | None, default: date) -> date:
    try:
        return date.fromisoformat(v) if v else default
    except ValueError:
        return default


module = qp.get("module", "listening") if qp.get("module") in MODULES else "listening"
with st.sidebar:
    st.markdown(design.logo(), unsafe_allow_html=True)
    ids = reg.ids()
    industry = st.selectbox("Industry", ids, index=ids.index(qp["industry"]) if qp.get("industry") in ids else 0,
                            format_func=lambda i: reg.get(i).name)
    tax = reg.get(industry)
    nav_slot = st.empty()  # filled once the alert count is known
    query = st.text_input("Search", value=qp.get("q", ""), placeholder="e.g. sữa công thức, Enfa A2, bv Bạch Mai",
                          help="Any word or phrase – Vietnamese, with or without accents.")
    picked = st.date_input("Date range", value=(_date(qp.get("from"), today - timedelta(days=6)), _date(qp.get("to"), today)),
                           max_value=today, format="DD/MM/YYYY", help="Any period, e.g. 01/10/2026 – 31/10/2026")
    if isinstance(picked, tuple):  # while picking, Streamlit returns a 1-item tuple
        start, end = (picked[0], picked[-1]) if picked else (today, today)
    else:
        start = end = picked

state = {"industry": industry, "q": query, "from": start.isoformat(), "to": end.isoformat()}
st.query_params.update({"module": module, **{k: v for k, v in state.items() if v}})
if not query and "q" in st.query_params:
    del st.query_params["q"]

span = timedelta(days=(end - start).days + 1)
until = datetime.combine(end, time.max, tzinfo=UTC)
since = datetime.combine(start, time.min, tzinfo=UTC)
raw = load_frame(industry, since - span, until, str(DB_PATH))   # current + previous period of equal length
alerts_24h = [a for a in repo().recent_alerts(100, industry) if a.created_at > datetime.now(UTC) - timedelta(days=1)]
nav_slot.markdown(design.nav(module, {k: v for k, v in state.items() if v}, len(alerts_24h)), unsafe_allow_html=True)

with st.sidebar:
    all_sources = sorted(raw["source"].unique()) if not raw.empty else []
    sources = st.multiselect("Sources", all_sources, default=all_sources,
                             format_func=lambda s: SOURCE_LABELS.get(s, s))
    if query and REMOTE_REPO:  # cloud dashboard is read-only
        st.caption(f"To collect “{query}” daily, add it to `config/watchlist.yaml` on GitHub.")
    elif query:
        tracked = {kw for _, kw in repo().watchlist(industry)}
        if query.strip() in tracked:
            st.caption(f"“{query}” is tracked daily.")
        elif st.button(f"+ Track “{query}” daily", width="stretch"):
            repo().add_watch(industry, query)
            st.toast(f"“{query}” will be collected in the next daily run.")
    if st.button("Refresh data", width="stretch"):
        st.cache_data.clear()
    newest = raw["published_at"].max() if not raw.empty else None
    st.markdown(design.status_card(f"Data up to {newest:%H:%M · %d/%m}" if newest is not None else "No data yet",
                                   "Crisis keywords every 2 hours · everything else daily"), unsafe_allow_html=True)

# ================= Content =================
if "demo" in DB_PATH.name:
    st.info("You are viewing **demo data** – not real market data.", icon="🧪")
if raw.empty:
    st.markdown(design.header(f"{tax.name}", "No data yet", "pulse", design.BLUE), unsafe_allow_html=True)
    st.info(f"No data for **{tax.name}** in this period. Pick a longer date range, or wait for the next scheduled run.")
    st.stop()

by_source = raw[raw["source"].isin(sources)]
df_all = keywords.search(by_source, query, tax)
if query and df_all.empty:
    st.warning(f"No posts match “{query}” in this period. Try another spelling or a longer date range.")
    st.stop()

ctx = ViewContext(
    tax=tax, repo=repo(), now=datetime.now(UTC), start=start, end=end, query=query, df_all=df_all,
    cur=df_all[df_all["published_at"] >= pd.Timestamp(since)],
    prev=df_all[df_all["published_at"] < pd.Timestamp(since)],
    base_cur=by_source[by_source["published_at"] >= pd.Timestamp(since)],
)
MODULES[module](ctx)
