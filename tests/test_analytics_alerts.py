from datetime import timedelta

import pytest

from vnlisten.alerts.rules import CrisisKeywordRule, NegativeSpikeRule
from vnlisten.analytics import metrics
from vnlisten.domain.models import Sentiment as S

from .conftest import NOW, make_mention


def test_entity_metrics_sov_and_nsr():
    df = metrics.to_frame([
        make_mention("a", brands=["abbott"], sentiment=S.POSITIVE, likes=10),
        make_mention("b", brands=["abbott"], sentiment=S.NEGATIVE),
        make_mention("c", brands=["abbott", "nestle"], sentiment=S.POSITIVE),
        make_mention("d", brands=["nestle"], sentiment=S.NEUTRAL),
    ])
    out = metrics.entity_metrics(df).set_index("entity")
    assert out.loc["abbott", "mentions"] == 3
    assert out.loc["abbott", "sov"] == pytest.approx(3 / 5)
    assert out.loc["abbott", "nsr"] == pytest.approx((2 - 1) / 3)
    assert out.loc["nestle", "nsr"] == pytest.approx(1.0)


def test_buzz_growth():
    ms = [make_mention(str(i), hours_ago=10, brands=["bobby"]) for i in range(4)]
    ms += [make_mention(f"p{i}", hours_ago=30, brands=["bobby"]) for i in range(2)]
    g = metrics.buzz_growth(metrics.to_frame(ms), NOW, timedelta(days=1)).set_index("entity")
    assert g.loc["bobby", "growth"] == pytest.approx(1.0)


def test_rank_orders_by_score():
    df = metrics.to_frame([make_mention(str(i), brands=["a"], likes=100, sentiment=S.POSITIVE) for i in range(5)]
                          + [make_mention("x", brands=["b"], sentiment=S.NEGATIVE)])
    ranked = metrics.rank(metrics.entity_metrics(df))
    assert ranked["entity"].tolist() == ["a", "b"] and ranked["rank"].tolist() == [1, 2]


def test_timeline_fills_missing_days_with_zero():
    df = metrics.to_frame([make_mention("a", hours_ago=1, brands=["a"]),
                           make_mention("b", hours_ago=72, brands=["a"]),
                           make_mention("c", hours_ago=1, brands=["b"])])
    tl = metrics.timeline(df, "D")
    assert len(tl) == 4 * 2  # 4 ngày x 2 brand
    assert tl[tl["entity"] == "b"]["mentions"].sum() == 1


def test_crisis_rule_needs_volume():
    rule = CrisisKeywordRule(str, min_mentions=3, min_interactions=300)
    small = [make_mention("x", brands=["abbott"], risk=["sữa giả"], likes=5)]
    assert rule.evaluate(small, NOW) == []
    big = [make_mention(str(i), brands=["abbott"], risk=["sữa giả"], likes=5) for i in range(3)]
    alerts = rule.evaluate(big, NOW)
    assert len(alerts) == 1 and "sữa giả (3)" in alerts[0].detail


def test_negative_spike_rule():
    rule = NegativeSpikeRule(str, baseline_days=7, ratio=2.0, min_count=5)
    base = [make_mention(f"b{i}", hours_ago=24 + 20 * i, brands=["abbott"], sentiment=S.NEGATIVE) for i in range(7)]
    spike = [make_mention(f"s{i}", hours_ago=2, brands=["abbott"], sentiment=S.NEGATIVE) for i in range(6)]
    assert rule.evaluate(base, NOW) == []
    alerts = rule.evaluate(base + spike, NOW)
    assert len(alerts) == 1 and alerts[0].key.startswith("negative_spike:abbott")


def test_rank_communities_scores_relevance_intent_and_recommends(taxonomy):
    from vnlisten.analytics import communities, keywords

    def post(i, text, cid, vis="public", likes=10, brands=("abbott",), sentiment=S.NEUTRAL):
        m = make_mention(text, ext=f"{cid}-{i}", likes=likes, brands=list(brands), sentiment=sentiment)
        m.community_id, m.community_name, m.community_type, m.visibility = cid, cid, "fb_group", vis
        return m

    ms = []
    ms += [post(i, "Các mẹ cho hỏi sữa nào mát, bé bị táo bón", "fb_group:a") for i in range(6)]       # đúng chủ đề + hỏi mua
    ms += [post(i, "Khoe ảnh bé đi chơi cuối tuần", "fb_group:b", likes=500) for i in range(8)]        # đông nhưng lạc đề
    ms += [post(100, "táo bón quá", "fb_group:b", likes=500)]
    ms += [post(i, "Bé bị táo bón, sữa tệ quá", "fb_group:c", vis="private", sentiment=S.NEGATIVE) for i in range(6)]
    ms += [post(i, "nothing", "fb_group:d") for i in range(2)]                                         # < min_posts
    base = metrics.to_frame(ms)
    ranked = communities.rank_communities(base, keywords.search(base, "táo bón"), taxonomy, days=7,
                                          focus_brands={"abbott"})
    by_id = ranked.set_index("community_id")
    assert "fb_group:d" not in by_id.index
    assert by_id.loc["fb_group:a", "relevance"] == 1.0 and by_id.loc["fb_group:a", "intent"] == 1.0
    assert by_id.loc["fb_group:b", "relevance"] == pytest.approx(1 / 9)
    assert ranked.iloc[0]["community_id"] == "fb_group:a"
    assert by_id.loc["fb_group:c", "recommendation"].startswith("Crisis watch")
    assert by_id.loc["fb_group:a", "recommendation"].startswith("Buyers asking")
