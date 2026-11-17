from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vnlisten.domain.models import Engagement, Mention, SourceType
from vnlisten.taxonomy import IndustryRegistry, load_taxonomy

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="session")
def taxonomy():
    return load_taxonomy(ROOT / "config/industries/me_va_be.yaml")


@pytest.fixture(scope="session")
def health():
    return load_taxonomy(ROOT / "config/industries/y_te_suc_khoe.yaml")


@pytest.fixture(scope="session")
def registry():
    return IndustryRegistry.from_dir(ROOT / "config/industries")


def make_mention(text="", hours_ago=1.0, ext=None, likes=0, brands=None, sentiment=None, risk=None,
                 source=SourceType.FACEBOOK, products=None, industry="", activities=None, hashtags=None,
                 keyword=""):
    m = Mention(source=source, external_id=ext or f"id-{text}-{hours_ago}", url="https://x", title="",
                content=text, published_at=NOW - timedelta(hours=hours_ago), engagement=Engagement(likes=likes),
                industry=industry, keyword=keyword)
    m.activities = activities or []
    m.hashtags = hashtags or []
    if brands is not None:
        m.brands = brands
    if products is not None:
        m.products = products
    if sentiment is not None:
        m.sentiment = sentiment
    if risk is not None:
        m.risk_terms = risk
    return m
