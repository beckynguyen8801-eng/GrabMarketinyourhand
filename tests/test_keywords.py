from collections import defaultdict

import pytest

from vnlisten.analytics import keywords, metrics
from vnlisten.domain.models import Sentiment as S
from vnlisten.pipeline.entity_matcher import EntityMatcher
from vnlisten.pipeline.text import normalize_for_match

from .conftest import make_mention


def _df(health):
    m = EntityMatcher(health)
    texts = [
        ("Khám ở bv bạch mai bác sĩ tận tâm, không phải chờ lâu", S.POSITIVE),
        ("Đưa mẹ vào bệnh viện bạch mai chờ cả ngày, quá tải", S.NEGATIVE),
        ("Viện phí bạch mai hợp lý, bác sĩ tận tâm", S.POSITIVE),
        ("Chợ Rẫy quá tải quá", S.NEGATIVE),
    ]
    out = []
    for i, (t, sent) in enumerate(texts):
        x = m.enrich(make_mention(t, ext=str(i), sentiment=sent))
        out.append(x)
    return metrics.to_frame(out)


def test_entity_keywords_known_tier_and_negation(health):
    kw = keywords.entity_keywords(_df(health), health, brand_id="bv_bach_mai", min_count=1).set_index("keyword")
    assert kw.loc["bác sĩ tận tâm", "mentions"] == 2 and kw.loc["bác sĩ tận tâm", "type"] == "Known"
    assert "chờ lâu" not in kw.index          # "không phải chờ lâu" là khen, không phải chê
    assert "không phải chờ" in kw.index
    assert kw.loc["quá tải", "nsr"] == -1.0
    assert not any("bach" in normalize_for_match(k) or "mai" == k for k in kw.index)  # không lấy tên brand


def test_single_syllable_terms_need_exact_accents(taxonomy):
    m = EntityMatcher(taxonomy)
    df = metrics.to_frame([m.enrich(make_mention(f"Mẹ cho bé uống similac {i}", ext=str(i))) for i in range(3)])
    kw = keywords.entity_keywords(df, taxonomy, product_id="abbott_similac", min_count=1)
    assert "mê" not in kw["keyword"].tolist()


def test_search_matches_text_and_entities(health):
    df = _df(health)
    assert len(keywords.search(df, "qua tai", health)) == 2           # không dấu vẫn tìm được
    assert len(keywords.search(df, "BV Bạch Mai", health)) == 3        # khớp alias brand
    assert len(keywords.search(df, "", health)) == 4
    assert keywords.search(df, "abc xyz", health).empty


@pytest.mark.parametrize(("text", "brand"), [
    ("Mới khám ở bv 108 xong", "bv_108"),
    ("Đi sinh ở Từ Dũ đông lắm", "bv_tu_du"),
    ("Sang Singapore khám ở Mount Elizabeth", "mount_elizabeth"),
    ("Chữa ung thư ở Charité Berlin", "charite"),
    ("Vinmec Times City khám nhanh", "vinmec"),
])
def test_hospital_aliases(health, text, brand):
    assert brand in EntityMatcher(health).enrich(make_mention(text)).brands


@pytest.mark.parametrize("text", [
    "Nhà em ở đường Hùng Vương",          # tên đường, không phải BV Hùng Vương
    "Chúc cả nhà an khang thịnh vượng",
    "Bé được 108 ngày tuổi",
    "Chị Hồng Ngọc mới sinh em bé",        # tên người
    "Một kết quả hoàn mỹ",
])
def test_common_words_are_not_hospitals(health, text):
    assert EntityMatcher(health).enrich(make_mention(text)).brands == []


def test_no_alias_shared_between_brands(registry):
    for tax in registry.all():
        owners = defaultdict(set)
        for b in tax.brands.values():
            for a in (*b.aliases, b.name):
                owners[normalize_for_match(a)].add(b.id)
        clashes = {a: ids for a, ids in owners.items() if len(ids) > 1}
        assert not clashes, f"{tax.industry}: alias trùng giữa brand {clashes}"


def test_every_brand_has_a_category(registry):
    health = registry.get("y_te_suc_khoe")
    assert all(health.category_of_brand(b) for b in health.brands)


def test_free_text_lookup_resolves_product_brand_or_text(taxonomy):
    m = EntityMatcher(taxonomy)
    df = metrics.to_frame([m.enrich(make_mention(t, ext=str(i))) for i, t in enumerate([
        "Bé uống enfa a+ tăng cân đều", "Enfamil A+ hơi táo bón", "Enfagrow giá cao", "Sữa hạt óc chó cho bé ngon"])])
    by_product = keywords.free_text_keywords(df, taxonomy, "enfa", "enfa a+", min_count=1)
    assert by_product.mode == "product" and by_product.product_id == "enfa_a_plus" and by_product.posts == 2
    by_brand = keywords.free_text_keywords(df, taxonomy, "ENFA", "", min_count=1)
    assert by_brand.mode == "brand" and by_brand.brand_id == "enfa" and by_brand.posts == 3
    by_text = keywords.free_text_keywords(df, taxonomy, "", "sua hat oc cho", min_count=1)
    assert by_text.mode == "text" and by_text.posts == 1
