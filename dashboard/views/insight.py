"""Insights & recommendations – shared by both modules."""
from __future__ import annotations

import streamlit as st
from ui import ViewContext, section


def render(ctx: ViewContext) -> None:
    latest = ctx.repo.latest_insight(ctx.tax.industry)
    with section("Insights & recommended actions"):
        if not latest:
            st.info(f"No insights yet. Run `vnlisten insight --industry {ctx.tax.industry}`.")
            return
        st.caption(f"Generated {latest[0].astimezone():%d/%m/%Y %H:%M} for the last 7 days · "
                   f"refresh with `vnlisten insight --industry {ctx.tax.industry}`")
        st.markdown(latest[1])
