import pytest

from vnlisten.domain.models import Sentiment
from vnlisten.pipeline.activity import ActivityClassifier
from vnlisten.pipeline.entity_matcher import EntityMatcher
from vnlisten.pipeline.pipeline import EnrichmentPipeline
from vnlisten.pipeline.router import build_router
from vnlisten.pipeline.sentiment import LexiconSentimentAnalyzer
from vnlisten.pipeline.text import normalize_for_match, strip_accents

from .conftest import make_mention


def test_strip_accents_handles_d():
    assert strip_accents("Đường sữa đặc") == "Duong sua dac"
    assert normalize_for_match("Sữa Bột NAN-Optipro!!") == "sua bot nan optipro"


@pytest.fixture
def matcher(taxonomy):
    return EntityMatcher(taxonomy)


def test_match_product_implies_brand(matcher):
    m = matcher.enrich(make_mention("Bé nhà em uống similac thấy ổn"))
    assert m.products == ["abbott_similac"]
    assert m.brands == ["abbott"]
    assert m.category == "sua_bot"


def test_match_without_accents(matcher):
    m = matcher.enrich(make_mention("ta bobby voi bim huggies cai nao tot hon"))
    assert set(m.brands) == {"bobby", "huggies"}


def test_ambiguous_short_word_not_matched(matcher):
    # "nạn", "khó khăn" bỏ dấu -> chứa "nan" nhưng KHÔNG được match Nestlé
    m = matcher.enrich(make_mention("Tai nạn giao thông, hoàn cảnh khó khăn"))
    assert m.brands == []


def test_risk_terms_longest_only(matcher):
    m = matcher.enrich(make_mention("Bóc phốt shop bán bỉm moony hàng giả"))
    assert set(m.risk_terms) == {"bóc phốt", "hàng giả"}


def test_negated_risk_term_ignored(matcher):
    m = matcher.enrich(make_mention("Uống enfamil a+ bé ngủ ngon, không bị táo bón"))
    assert m.risk_terms == []


@pytest.mark.parametrize(("text", "expected"), [
    ("Sữa này tốt lắm, bé tăng cân đều, rất hài lòng", Sentiment.POSITIVE),
    ("Bé uống bị táo bón, thất vọng quá", Sentiment.NEGATIVE),
    ("Bé uống không bị táo bón, ngủ ngon", Sentiment.POSITIVE),
    ("Sữa này không tốt chút nào", Sentiment.NEGATIVE),
    ("Các mẹ cho hỏi mua sữa ở đâu?", Sentiment.NEUTRAL),
    ("Phát hiện sữa giả bán tràn lan", Sentiment.NEGATIVE),
])
def test_lexicon_sentiment(text, expected, taxonomy):
    analyzer = LexiconSentimentAnalyzer(taxonomy.positive_terms, taxonomy.negative_terms)
    assert analyzer.enrich(make_mention(text)).sentiment is expected


@pytest.mark.parametrize(("text", "expected"), [
    ("Uống thuốc này không hiệu quả gì cả", Sentiment.NEGATIVE),   # cụm dài thắng "hiệu quả"
    ("Thuốc hạ sốt nhanh, hiệu quả", Sentiment.POSITIVE),
    ("Bị sốc phản vệ phải nhập viện", Sentiment.NEGATIVE),
])
def test_health_sentiment(text, expected, health):
    analyzer = LexiconSentimentAnalyzer(health.positive_terms, health.negative_terms)
    assert analyzer.enrich(make_mention(text)).sentiment is expected


def test_pipeline_dedupes_and_drops_irrelevant(taxonomy):
    pipe = EnrichmentPipeline([EntityMatcher(taxonomy),
                               LexiconSentimentAnalyzer(taxonomy.positive_terms, taxonomy.negative_terms)])
    relevant = make_mention("bỉm merries thấm hút tốt", ext="a")
    out = pipe.run([relevant, make_mention("bỉm merries thấm hút tốt", ext="a"), make_mention("thời tiết đẹp", ext="b")])
    assert len(out) == 1
    assert out[0].brands == ["merries"]
    assert out[0].sentiment is Sentiment.POSITIVE


def test_health_alias_avoids_common_phrase(health):
    m = EntityMatcher(health).enrich(make_mention("Chúc cả nhà an khang thịnh vượng"))
    assert m.brands == []
    m = EntityMatcher(health).enrich(make_mention("Mua panadol extra ở nhà thuốc an khang"))
    assert set(m.brands) == {"panadol", "an_khang"} and m.category == "thuoc_otc"


def test_router_detects_industry(registry):
    router = build_router(registry)
    health_post = router.enrich(make_mention("Máy đo huyết áp omron đo chính xác"))
    baby_post = router.enrich(make_mention("Bỉm bobby thấm hút tốt"))
    assert health_post.industry == "y_te_suc_khoe" and health_post.sentiment is Sentiment.POSITIVE
    assert baby_post.industry == "me_va_be" and baby_post.brands == ["bobby"]


def test_router_respects_given_industry(registry):
    m = build_router(registry).enrich(make_mention("Bỉm bobby thấm hút tốt", industry="y_te_suc_khoe"))
    assert m.industry == "y_te_suc_khoe" and m.brands == []  # không ép brand ngành khác


def test_activity_classifier_and_hashtags():
    m = ActivityClassifier({"su_kien_offline": ("ngày hội sức khoẻ",)}).enrich(make_mention(
        "Ngày hội sức khoẻ cuối tuần, livestream tặng voucher #KhoeMoiNgay #khoemoingay"))
    assert set(m.activities) == {"su_kien_offline", "livestream", "khuyen_mai"}
    assert m.hashtags == ["khoemoingay"]


def test_organic_review_is_not_kol_activity():
    clf = ActivityClassifier()
    assert clf.enrich(make_mention("Mẹ nào dùng rồi cho xin review với")).activities == []
    assert clf.enrich(make_mention("Review chân thật sau 1 tháng, hợp tác cùng brand")).activities == ["kol_review"]
    assert clf.enrich(make_mention("Ad ơi cho em hỏi giá với")).activities == []
    assert clf.enrich(make_mention("Video này được tài trợ bởi nhãn hàng")).activities == ["kol_review"]


@pytest.mark.parametrize(("text", "expected"), [
    ("Bé nhà mình uống similac bị táo bón, các mẹ cho hỏi nên đổi sữa nào?", True),
    ("62 puste domy i działki zostały przekazane do Centrum Rozwoju", False),       # Ba Lan
    ("Juice that helps soothe the stomach and supports digestion", False),          # tiếng Anh
    ("Le médecin a prescrit un traitement à l'hôpital", False),                     # tiếng Pháp
])
def test_looks_vietnamese(text, expected):
    from vnlisten.pipeline.relevance import looks_vietnamese
    assert looks_vietnamese(text) is expected


def test_relevance_filter_drops_off_topic_and_foreign(registry):
    from vnlisten.domain.models import TrackingQuery  # noqa: F401
    pipe = EnrichmentPipeline([build_router(registry)])
    on_brand = make_mention("Khám ở bv bạch mai bác sĩ rất tận tâm", ext="1", industry="y_te_suc_khoe")
    on_keyword = make_mention("Nên chọn bệnh viện tư nào để sinh con ở Hà Nội?", ext="2", industry="y_te_suc_khoe",
                              keyword="bệnh viện tư")
    off_topic = make_mention("Hai bác sĩ Việt chạy đua thời gian cứu hành khách trên chuyến bay", ext="3",
                             industry="y_te_suc_khoe", keyword="bệnh viện tư")
    foreign = make_mention("Bach Mai hospital opens a new wing in Hanoi", ext="4", industry="y_te_suc_khoe")
    kept = {m.external_id for m in pipe.run([on_brand, on_keyword, off_topic, foreign])}
    assert kept == {"1", "2"}


def test_tracking_queries_use_vietnamese_alias(health):
    from vnlisten.domain.models import Tier
    words = {q.keyword for q in health.tracking_queries(Tier.DAILY)}
    assert "bệnh viện 108" in words and "Military Central Hospital 108" not in words
