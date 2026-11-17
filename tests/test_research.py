from datetime import timedelta

from vnlisten.analytics import metrics, research
from vnlisten.connectors.google_suggest import parse_suggestions
from vnlisten.domain.models import KeywordSuggestion

from .conftest import NOW, make_mention


def _df():
    return metrics.to_frame([
        make_mention("a", brands=["a"], activities=["livestream", "khuyen_mai"], likes=10, hashtags=["sale"]),
        make_mention("b", brands=["a"], activities=["su_kien_offline"], likes=5),
        make_mention("c", brands=["b"], activities=["su_kien_offline"], likes=50, hashtags=["sale"]),
        make_mention("d", brands=["b"]),
    ])


def test_activity_summary_and_channel_split():
    summary = research.activity_summary(_df()).set_index("activity")
    assert summary.loc["su_kien_offline", "mentions"] == 2
    assert summary.loc["su_kien_offline", "channel"] == "offline"
    assert summary.loc["su_kien_offline", "brands"] == 2

    split = research.channel_split(_df()).set_index("brand")
    assert split.loc["a", "online"] == 2 and split.loc["a", "offline"] == 1
    assert split.loc["b", "offline_share"] == 1.0


def test_top_hashtags_assigns_brand():
    tags = research.top_hashtags(_df())
    assert tags.iloc[0]["hashtag"] == "#sale"
    assert tags.iloc[0]["interactions"] == 60 and tags.iloc[0]["mentions"] == 2


def test_keyword_performance():
    df = metrics.to_frame([make_mention(str(i), keyword="sữa mát", hours_ago=2) for i in range(3)]
                          + [make_mention("p", keyword="sữa mát", hours_ago=30)])
    perf = research.keyword_performance(df, NOW, timedelta(days=1)).set_index("keyword")
    assert perf.loc["sữa mát", "current"] == 3 and perf.loc["sữa mát", "growth"] == 2.0


def test_trending_phrases_prefers_full_phrase():
    texts = ["uống men vi sinh mỗi ngày", "men vi sinh loại nào tốt", "review men vi sinh xịn",
             "giá men vi sinh rẻ"]
    df = metrics.to_frame([make_mention(t, hours_ago=2, ext=t) for t in texts]
                          + [make_mention("vitamin tổng hợp", hours_ago=40, ext="old")])
    trends = research.trending_phrases(df, NOW, timedelta(days=1))
    assert trends.iloc[0]["phrase"] == "men vi sinh"
    assert "men vi" not in trends["phrase"].tolist()


def test_suggestion_table_marks_new():
    old, new = NOW - timedelta(days=7), NOW
    history = [KeywordSuggestion("x", "sữa", "sữa mát", 1, old), KeywordSuggestion("x", "sữa", "sữa mát", 1, new),
               KeywordSuggestion("x", "sữa", "sữa a2", 2, new)]
    table = research.suggestion_table(history).set_index("suggestion")
    assert not table.loc["sữa mát", "is_new"] and table.loc["sữa a2", "is_new"]


def test_parse_google_suggest():
    assert parse_suggestions('["sữa", ["sữa mát", "sữa a2"]]') == ["sữa mát", "sữa a2"]
