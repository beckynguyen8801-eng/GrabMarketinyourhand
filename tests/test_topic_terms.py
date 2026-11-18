from datetime import datetime

import pandas as pd

from vnlisten.analytics.keywords import keywords_in, search
from vnlisten.domain.models import Mention
from vnlisten.pipeline.entity_matcher import EntityMatcher
from vnlisten.pipeline.relevance import is_relevant
from vnlisten.taxonomy import IndustryRegistry

REG = IndustryRegistry.from_dir("config/industries")


def _enrich(industry: str, text: str) -> Mention:
    m = Mention("facebook", "1", "https://x", "", text, datetime(2026, 11, 1))
    return EntityMatcher(REG.get(industry)).enrich(m)


def test_abbreviation_maps_to_topic_and_keeps_post():
    m = _enrich("me_va_be", "Mẹ nào cho con uống SCT mà bé đi poo mượt, êm bụng không ạ?")
    assert {"sữa công thức", "đi poo mượt", "êm bụng"} <= set(m.topics)
    assert is_relevant(m)


def test_single_accented_syllable_alone_does_not_keep_post():
    assert not is_relevant(_enrich("me_va_be", "Hôm nay trời mát quá các mẹ ơi, đi chơi thôi"))


def test_hospital_aliases_and_longest_match():
    assert _enrich("y_te_suc_khoe", "Khám ở BV Đa khoa Carmel rất ổn").brands == ["carmel"]
    hue = _enrich("y_te_suc_khoe", "Bệnh viện Đại học Y Dược Huế mổ thành công")
    assert hue.brands == ["bv_dhyd_hue"]
    talk = _enrich("y_te_suc_khoe", "Xem UMC Nursing CareTalk tối nay")
    assert talk.products == ["umc_caretalk"] and talk.brands == ["bv_dhyd_hcm"]


def test_variants_merge_in_keywords_and_search():
    tax = REG.get("me_va_be")
    df = pd.DataFrame({
        "title": ["", ""], "content": ["Bé uống sct thấy ổn", "Sữa công thức này tốt"],
        "sentiment": ["positive", "positive"], "interactions": [1, 2],
        "brands": [[], []], "products": [[], []],
    })
    kw = keywords_in(df, tax, min_count=1)
    assert kw.loc[kw["keyword"] == "sữa công thức", "mentions"].iloc[0] == 2
    assert len(search(df, "SCT", tax)) == 2
