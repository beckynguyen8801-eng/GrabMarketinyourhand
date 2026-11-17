"""Sinh dữ liệu GIẢ LẬP để xem dashboard khi chưa crawl. Ghi vào DB riêng (data/demo.db).

Text được sinh từ template rồi đi qua ĐÚNG pipeline thật (router -> match brand -> sentiment -> hoạt động MKT),
nên đây cũng là bài test end-to-end cho pipeline.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .container import App
from .domain.models import Engagement, KeywordSuggestion, Mention, ProductSnapshot, SourceType
from .pipeline.text import strip_accents
from .taxonomy import Taxonomy


@dataclass(frozen=True)
class Script:
    positive: tuple[str, ...]
    neutral: tuple[str, ...]
    negative: tuple[str, ...]
    crisis: str
    crisis_brand: str
    riser_brand: str
    trend: tuple[str, ...]  # các câu chứa cụm từ trend, chỉ xuất hiện 7 ngày gần nhất
    offline_event: str   # hoạt động offline đặc thù ngành
    # Template riêng cho entity KHÔNG có sản phẩm (bệnh viện...), theo tiền tố category: (pos, neu, neg)
    entity_templates: tuple[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...] = ()


SCRIPTS: dict[str, Script] = {
    "me_va_be": Script(
        positive=(
            "Con mình uống {p} được 2 tháng, bé tăng cân đều, đi ngoài đều, rất hài lòng",
            "Review {p}: mát, bé thích, giá tốt so với mấy loại khác. Khuyên dùng nha các mẹ",
            "Dùng {p} thấy ổn, bé ngủ ngon, không bị táo bón. Đáng tiền",
            "{p} chính hãng mua ở shop uy tín, bé hợp lắm mọi người ạ",
        ),
        neutral=(
            "Các mẹ cho em hỏi {p} với {q} thì loại nào phù hợp cho bé 6 tháng?",
            "Đang phân vân giữa {p} và {q}, mẹ nào dùng rồi cho xin kinh nghiệm",
        ),
        negative=(
            "Bé nhà mình dùng {p} bị táo bón cả tuần, thất vọng quá",
            "Dùng {p} bé bị nổi mẩn, dị ứng, các mẹ cân nhắc nhé",
            "{p} giá cao mà chất lượng kém, không nên mua",
            "Bóc phốt shop bán {p} hàng giả, các mẹ cẩn thận",
        ),
        crisis="Nghi vấn sữa giả {p} bán tràn lan trên mạng, nhiều bé bị tiêu chảy sau khi uống",
        crisis_brand="abbott", riser_brand="bobby",
        trend=(
            "Dạo này hội mẹ bỉm rần rần sữa đạm A2, {p} có dòng đạm A2 không các mẹ?",
            "Chuyển sang sữa đạm A2 có tốt hơn {p} không ạ?",
            "Bé uống {p} ổn rồi, có cần đổi sang sữa đạm A2 không?",
            "Sữa đạm A2 giá cao hơn {p} nhiều, mọi người thấy đáng không",
        ),
        offline_event="Hội thảo tiền sản cuối tuần cùng {b}: tư vấn dinh dưỡng thai kỳ, tặng mẫu thử {p} #{tag}",
    ),
    "y_te_suc_khoe": Script(
        positive=(
            "Dùng {p} được 1 tháng thấy hiệu quả, khoẻ hơn hẳn, rất hài lòng",
            "{p} chất lượng, giá tốt, nhà mình tin dùng lâu rồi. Khuyên dùng",
            "Mua {p} giao nhanh, dược sĩ tư vấn nhiệt tình, yên tâm",
            "{p} dễ uống, đỡ nhiều sau 2 ngày, ổn áp",
        ),
        neutral=(
            "Mọi người cho hỏi {p} với {q} cái nào tốt hơn?",
            "Đang phân vân giữa {p} và {q}, ai dùng rồi cho xin kinh nghiệm",
        ),
        negative=(
            "Uống {p} không hiệu quả, còn bị buồn nôn, chóng mặt",
            "{p} đắt mà không đỡ, thất vọng",
            "Bóc phốt chỗ bán {p} hàng giả, mọi người cẩn thận",
            "{p} tăng giá liên tục, chán thật sự",
        ),
        crisis="Cảnh báo thuốc giả {p} bán trên mạng, có người phải nhập viện sau khi dùng",
        crisis_brand="panadol", riser_brand="long_chau",
        trend=(
            "Trend men vi sinh đang hot, có nên uống {p} kèm men vi sinh không mọi người?",
            "Bác sĩ khuyên bổ sung men vi sinh song song với {p}",
            "Ai dùng men vi sinh lâu dài chưa, so với {p} thế nào?",
            "Men vi sinh loại nào tốt, đang dùng {p} rồi",
        ),
        offline_event="Ngày hội sức khoẻ: đo huyết áp miễn phí tại nhà thuốc cùng {b}, tặng kèm {p} #{tag}",
        entity_templates=(
            ("bv_", (
                "Khám ở {p} bác sĩ tận tâm, sạch sẽ, không phải chờ lâu",
                "Mổ ở {p} thành công, điều dưỡng dễ thương, chu đáo lắm",
                "Gói khám sức khoẻ tổng quát ở {p} chuyên nghiệp, đáng tiền",
            ), (
                "Mọi người cho hỏi khám tổng quát ở {p} hết bao nhiêu?",
                "Có ai từng sinh ở {p} chưa, cho mình xin kinh nghiệm",
                "Đặt lịch khám {p} online thế nào mọi người?",
            ), (
                "Đưa mẹ vào {p} chờ cả ngày, quá tải, nhân viên cáu gắt",
                "Viện phí ở {p} cao quá, cảm giác bị chặt chém",
                "Người nhà mình bị biến chứng sau mổ ở {p}, rất bức xúc",
            )),
        ),
    ),
}

CAMPAIGN_TEMPLATES = (
    "{b} đang flash sale 50% {p}, freeship toàn quốc #{tag}",
    "Minigame tháng này của {b}: chia sẻ bài viết để có cơ hội trúng thưởng {p} #{tag}",
    "Review chân thật {p} sau 1 tháng, hợp tác cùng {b} #{tag}",
    "Tối nay 8h livestream cùng {b}, mua trên live giảm thêm 10% cho {p}",
    "{b} chính thức ra mắt {p} phiên bản mới #{tag}",
    "TVC mới của {b} với gương mặt đại diện đang viral #{tag}",
    "Sự kiện dùng thử miễn phí {p} tại siêu thị cuối tuần này do {b} tổ chức #{tag}",
    "{b} trao tặng 1.000 phần quà trong chương trình cộng đồng #{tag}",
)
TAG_SUFFIX = ("yeuthuong", "khoemoingay", "2026", "camket", "donghanh", "tet")
SOURCE_WEIGHTS = {SourceType.FACEBOOK: 0.45, SourceType.TIKTOK: 0.25, SourceType.YOUTUBE: 0.12,
                  SourceType.GOOGLE_NEWS: 0.1, SourceType.THREADS: 0.08}
SUGGESTION_TAILS = ("có tốt không", "loại nào tốt", "giá bao nhiêu", "review", "cho người lớn", "chính hãng",
                    "mua ở đâu", "tphcm", "hà nội", "2026")


def seed_demo(app: App, days: int = 30, seed: int = 42) -> int:
    rng = random.Random(seed)
    now = datetime.now(UTC)
    raw: list[Mention] = []
    for tax in app.registry.all():
        raw += _industry_mentions(rng, tax, SCRIPTS[tax.industry], days, now)
        _seed_market_and_keywords(rng, app, tax, now)

    stats = app.collection.ingest(raw)
    app.alerts.run(now)
    app.insights.run_all(now)
    return stats.new


def _industry_mentions(rng: random.Random, tax: Taxonomy, script: Script, days: int, now: datetime) -> list[Mention]:
    products = list(tax.products.values())
    # Entity không có sản phẩm (bệnh viện) => coi chính nó là 1 "sản phẩm" để sinh bài
    products += [_BrandAsProduct(b.id, b.name, b.id, tax.category_of_brand(b.id), b.aliases)
                 for b in tax.brands.values() if not tax.products_of_brand(b.id) and tax.category_of_brand(b.id)]
    # Bệnh viện: nhiều entity nhưng mỗi cái ít bài hơn sản phẩm => giữ demo gọn
    popularity = {p.id: rng.uniform(0.05, 0.6) if isinstance(p, _BrandAsProduct) else rng.uniform(0.3, 3.0)
                  for p in products}
    positivity = {p.id: rng.uniform(0.35, 0.75) for p in products}
    brand_tag = {b: strip_accents(tax.brand_name(b)).lower().replace(" ", "").replace(".", "").split("(")[0]
                 + rng.choice(TAG_SUFFIX) for b in tax.brands}
    sources, weights = zip(*SOURCE_WEIGHTS.items(), strict=True)

    def mk(text: str, when: datetime, category: str, boost: float = 1.0, source: SourceType | None = None) -> Mention:
        src = source or rng.choices(sources, weights)[0]
        # Giả lập: bài được tìm thấy qua 1 từ khoá ngành con hoặc tên sản phẩm (giống collector thật)
        product_names = [p.name for p in tax.products.values() if p.category == category and p.name in text]
        keyword = product_names[0] if product_names else rng.choice(tax.categories[category].keywords)
        return _assign_community(rng, _mention(rng, src, text, when, category, tax.industry, keyword, boost))

    out: list[Mention] = []
    for day in range(days):
        for p in products:
            factor = 2.2 if (p.brand == script.riser_brand and day < 7) else 1.0
            when = lambda: now - timedelta(days=day, hours=rng.uniform(0, 24))  # noqa: E731
            for _ in range(rng.randint(0, int(4 * popularity[p.id] * factor) + 1)):
                other = rng.choice([o for o in products if o.category == p.category and o.id != p.id] or products)
                roll = rng.random()
                pos, neu, neg = _templates_for(script, p.category)
                pool = pos if roll < positivity[p.id] else neu if roll < positivity[p.id] + 0.2 else neg
                alias = rng.choice(p.aliases or (p.name,))
                out.append(mk(rng.choice(pool).format(p=alias, q=other.name), when(), p.category))
            # Bài hoạt động MKT do brand / KOL đăng (ít hơn nhưng tương tác cao)
            if rng.random() < 0.6 * popularity[p.id] / 3:
                tpl = rng.choice(CAMPAIGN_TEMPLATES + (script.offline_event,))
                text = tpl.format(b=tax.brand_name(p.brand), p=p.name, tag=brand_tag[p.brand])
                out.append(mk(text, when(), p.category, boost=2.5, source=rng.choice([SourceType.FACEBOOK, SourceType.TIKTOK])))
            if day < 7 and not isinstance(p, _BrandAsProduct) and rng.random() < 0.35:
                out.append(mk(rng.choice(script.trend).format(p=p.name), when(), p.category))

    crisis_product = next(p for p in products if p.brand == script.crisis_brand)
    for _ in range(12):  # khủng hoảng 24h gần nhất
        out.append(mk(script.crisis.format(p=crisis_product.name), now - timedelta(hours=rng.uniform(0, 20)),
                      crisis_product.category, boost=4,
                      source=rng.choice([SourceType.FACEBOOK, SourceType.TIKTOK, SourceType.GOOGLE_NEWS])))
    return out


@dataclass(frozen=True)
class _BrandAsProduct:
    id: str
    name: str
    brand: str
    category: str
    aliases: tuple[str, ...]


def _templates_for(script: Script, category: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    for prefix, pos, neu, neg in script.entity_templates:
        if category.startswith(prefix):
            return pos, neu, neg
    return script.positive, script.neutral, script.negative


def _seed_market_and_keywords(rng: random.Random, app: App, tax: Taxonomy, now: datetime) -> None:
    app.repo.save_snapshots([
        ProductSnapshot(SourceType.TIKI, f"demo-{p.id}", f"{p.name} (demo)", tax.brand_name(p.brand), p.category,
                        rng.randint(80, 900) * 1000, rng.randint(300, 9000), round(rng.uniform(4.2, 4.9), 1),
                        rng.randint(50, 3000), "https://tiki.vn", now, tax.industry)
        for p in tax.products.values() if not p.category.startswith("bv_")
    ])
    suggestions = []
    for seed in tax.research_seeds:
        tails = rng.sample(SUGGESTION_TAILS, 7)
        for captured, picked in ((now - timedelta(days=7), tails[:6]), (now, tails[1:7])):
            suggestions += [KeywordSuggestion(tax.industry, seed, f"{seed} {t}", i, captured)
                            for i, t in enumerate(picked, 1)]
    app.repo.save_suggestions(suggestions)


# Community GIẢ ĐỊNH cho demo: (slug, tên, visibility, độ "nóng" tương đối)
DEMO_GROUPS = {
    "me_va_be": [("hoimebimsuahn", "Hội mẹ bỉm sữa Hà Nội (demo)", "public", 3.0),
                 ("nuoiconsuacongthuc", "Nuôi con bằng sữa công thức (demo)", "public", 2.2),
                 ("reviewbimsua", "Review bỉm sữa chính hãng (demo)", "public", 1.6),
                 ("mesinhthang6", "Hội mẹ sinh tháng 6/2026 (demo)", "private", 1.2),
                 ("anvatchobe", "Ăn dặm & dinh dưỡng cho bé (demo)", "public", 0.8)],
    "y_te_suc_khoe": [("reviewbenhvienhcm", "Review bệnh viện & phòng khám HCM (demo)", "public", 2.6),
                      ("khamchuabenhsingapore", "Đi khám chữa bệnh ở Singapore (demo)", "public", 1.2),
                      ("nguoibenhtieuduong", "Cộng đồng người bệnh tiểu đường (demo)", "private", 1.4),
                      ("chamsocnguoigia", "Chăm sóc sức khoẻ người cao tuổi (demo)", "public", 1.8),
                      ("thucphamchucnangreview", "Review thực phẩm chức năng (demo)", "public", 2.0)],
}
DEMO_CREATORS = {"me_va_be": ["mebap.review", "bacsi.nhi.demo", "nhabimsua"],
                 "y_te_suc_khoe": ["duocsi.tuvan.demo", "bacsi.giadinh.demo", "songkhoe247"]}


def _assign_community(rng: random.Random, m: Mention) -> Mention:
    """Gắn bài demo vào 1 group FB / kênh TikTok qua URL – CommunityResolver sẽ tự nhận ra."""
    ext = m.external_id
    if m.source is SourceType.FACEBOOK and rng.random() < 0.75:
        groups = DEMO_GROUPS[m.industry]
        slug, name, vis, _ = rng.choices(groups, weights=[g[3] for g in groups])[0]
        m.url = f"https://www.facebook.com/groups/{slug}/posts/{ext}"
        m.community_name, m.visibility = name, vis
    elif m.source is SourceType.TIKTOK:
        m.url = f"https://www.tiktok.com/@{rng.choice(DEMO_CREATORS[m.industry])}/video/{ext}"
    return m


def _engagement(rng: random.Random, source: SourceType, boost: float = 1.0) -> Engagement:
    base = {SourceType.TIKTOK: 400, SourceType.FACEBOOK: 120, SourceType.YOUTUBE: 200}.get(source, 20)
    likes = int(rng.expovariate(1 / (base * boost)))
    return Engagement(likes=likes, comments=int(likes * rng.uniform(0.05, 0.3)),
                      shares=int(likes * rng.uniform(0, 0.1)),
                      views=likes * rng.randint(10, 60) if source in (SourceType.TIKTOK, SourceType.YOUTUBE) else 0)


def _mention(rng: random.Random, source: SourceType, text: str, published: datetime, category: str,
             industry: str, keyword: str, boost: float = 1.0) -> Mention:
    ext = f"demo-{rng.getrandbits(48):x}"
    return Mention(source=source, external_id=ext, url=f"https://example.com/{source}/{ext}",
                   title="" if source is not SourceType.GOOGLE_NEWS else text[:80], content=text,
                   author=f"user{rng.randint(1, 5000)}", published_at=published,
                   engagement=_engagement(rng, source, boost), keyword=keyword, category=category, industry=industry)
