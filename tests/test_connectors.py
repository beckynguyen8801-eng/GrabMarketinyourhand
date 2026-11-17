from datetime import UTC, datetime

from vnlisten.connectors.csv_import import read_csv
from vnlisten.connectors.google_news import parse_rss
from vnlisten.connectors.tiki import parse_listing
from vnlisten.connectors.youtube import parse_comments, parse_videos
from vnlisten.domain.models import SourceType, TrackingQuery

Q = TrackingQuery("sữa giả", "sua_bot")

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Phát hiện lô sữa giả Similac - VnExpress</title><link>https://news.google.com/a</link>
<guid>g1</guid><pubDate>Tue, 17 Nov 2026 03:00:00 GMT</pubDate>
<description>&lt;a href="x"&gt;Phát hiện lô sữa giả&lt;/a&gt;</description><source url="https://vnexpress.net">VnExpress</source></item>
<item><title>Tin cũ</title><link>https://news.google.com/b</link><guid>g2</guid>
<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_parse_google_news_filters_old_items():
    items = parse_rss(RSS, Q, since=datetime(2026, 11, 10, tzinfo=UTC))
    assert len(items) == 1
    m = items[0]
    assert m.source is SourceType.GOOGLE_NEWS
    assert m.author == "VnExpress"
    assert m.content == "Phát hiện lô sữa giả"
    assert m.category == "sua_bot"


def test_parse_tiki_listing():
    payload = {"data": [{"id": 1, "name": "Sữa Similac 5G", "brand_name": "Abbott", "price": 550000,
                         "quantity_sold": {"text": "Đã bán 2k", "value": 2034}, "rating_average": 4.8,
                         "review_count": 321, "url_path": "sua-similac-p1.html"},
                        {"id": 2, "name": "Không có số bán", "price": None, "quantity_sold": None}]}
    snaps = parse_listing(payload, Q, datetime(2026, 11, 17, tzinfo=UTC))
    assert snaps[0].sold_count == 2034 and snaps[0].brand == "Abbott"
    assert snaps[1].sold_count == 0 and snaps[1].price == 0


def test_parse_youtube():
    videos = {"items": [{"id": "v1", "snippet": {"title": "Review sữa Meiji", "description": "d",
                                                  "channelTitle": "Mẹ Bắp", "publishedAt": "2026-11-16T10:00:00Z"},
                         "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "7"}}]}
    v = parse_videos(videos, Q)[0]
    assert v.engagement.views == 1000 and v.url.endswith("v=v1")
    comments = {"items": [{"snippet": {"totalReplyCount": 2, "topLevelComment": {"id": "c1", "snippet": {
        "textOriginal": "bé uống bị táo bón", "authorDisplayName": "A", "publishedAt": "2026-11-16T11:00:00Z",
        "likeCount": 3}}}}]}
    c = parse_comments(comments, "v1", Q)[0]
    assert c.external_id == "comment:c1" and c.engagement.comments == 2


def test_read_csv(tmp_path):
    f = tmp_path / "fb.csv"
    f.write_text("url,content,published_at,likes\nhttps://fb/1,Bỉm bobby tốt,17/11/2026 08:00,12\n,,2026-11-17,0\n",
                 encoding="utf-8")
    items = read_csv(f, SourceType.FACEBOOK)
    assert len(items) == 1
    assert items[0].engagement.likes == 12 and items[0].published_at.day == 17


# ---------------- Browser capture + community + web search ----------------
import json as _json
import threading
import urllib.request

import pytest

from vnlisten.connectors.browser_capture import capture_to_mentions, parse_count
from vnlisten.connectors.web_search import WebSearchConnector, parse_google_cse, parse_searxng
from vnlisten.pipeline.community import CommunityResolver, resolve_community


@pytest.mark.parametrize(("raw", "expected"), [
    ("1,2K", 1200), ("3,4 N", 3400), ("2.5M", 2_500_000), ("1.234", 1234), ("35 bình luận", 35), (12, 12), ("", 0),
    ("1,5 Tr", 1_500_000),
])
def test_parse_count(raw, expected):
    assert parse_count(raw) == expected


def test_capture_payload_to_mentions_hashes_author():
    ms = capture_to_mentions({
        "source": "facebook", "page_url": "https://www.facebook.com/groups/hoimebimsua",
        "community": {"name": "Hội mẹ bỉm sữa", "url": "https://www.facebook.com/groups/hoimebimsua",
                      "visibility": "public"},
        "items": [{"url": "https://www.facebook.com/groups/hoimebimsua/posts/1", "text": "Các mẹ cho hỏi sữa nào mát?",
                   "author": "Nguyễn Văn A", "likes": "1,2K", "comments": "35"},
                  {"text": "ok"}],  # quá ngắn -> bỏ
    })
    assert len(ms) == 1
    m = ms[0]
    assert m.engagement.likes == 1200 and m.community_name == "Hội mẹ bỉm sữa" and m.visibility == "public"
    assert "Nguyễn" not in m.author and len(m.author) == 12


def test_capture_rejects_unknown_source():
    with pytest.raises(ValueError):
        capture_to_mentions({"source": "myspace", "items": []})


@pytest.mark.parametrize(("url", "cid", "kind"), [
    ("https://www.facebook.com/groups/hoimebimsua/posts/123", "fb_group:hoimebimsua", "fb_group"),
    ("https://m.facebook.com/groups/12345/permalink/9", "fb_group:12345", "fb_group"),
    ("https://www.tiktok.com/@mebap.review/video/7311", "tiktok_account:mebap.review", "tiktok_account"),
    ("https://www.threads.net/@bacsi.nhi/post/abc", "threads_account:bacsi.nhi", "threads_account"),
    ("https://www.instagram.com/healthyvn/", "ig_account:healthyvn", "ig_account"),
    ("https://www.instagram.com/p/Cx1/", "", ""),
    ("https://www.webtretho.com/f/me-va-be/abc", "forum:webtretho.com", "forum"),
    ("https://vnexpress.net/abc", "", ""),
])
def test_resolve_community(url, cid, kind):
    got = resolve_community(url)
    assert got[0] == cid and got[1] == kind


def test_resolver_marks_pages_public_and_keeps_capture_name():
    from .conftest import make_mention
    m = make_mention("x", source=SourceType.TIKTOK)
    m.url = "https://www.tiktok.com/@mebap/video/1"
    assert CommunityResolver().enrich(m).visibility == "public"
    g = make_mention("y")
    g.url, g.community_name = "https://www.facebook.com/groups/abc/posts/1", "Hội mẹ ABC"
    g = CommunityResolver().enrich(g)
    assert g.community_name == "Hội mẹ ABC" and g.visibility == "unknown"  # group: không tự đoán public


def test_web_search_connector_builds_site_queries_and_parses():
    class Fake:
        def __init__(self):
            self.queries = []

        def search(self, q, days):
            self.queries.append(q)
            return parse_searxng({"results": [
                {"url": "https://www.facebook.com/groups/abc/posts/1", "title": "Sữa mát cho bé",
                 "content": "Các mẹ cho hỏi sữa công thức nào mát", "publishedDate": "2026-11-16T08:00:00"},
                {"url": "https://spam.example.com/x", "title": "spam", "content": "spam spam spam spam"},
            ]})
    fake = Fake()
    ms = WebSearchConnector(fake, (SourceType.FACEBOOK,)).fetch(TrackingQuery("sữa công thức", "sua_bot"),
                                                                 datetime(2026, 11, 10, tzinfo=UTC))
    assert fake.queries == ['site:facebook.com/groups "sữa công thức"']
    assert len(ms) == 1 and ms[0].source is SourceType.FACEBOOK and ms[0].visibility == "public"


def test_parse_google_cse_prefers_og_description():
    out = parse_google_cse({"items": [{"link": "https://tiktok.com/@a/video/1", "title": "t", "snippet": "short",
                                       "pagemap": {"metatags": [{"og:description": "full caption"}]}}]})
    assert out[0]["snippet"] == "full caption"


def test_ingest_server_end_to_end(tmp_path, registry):
    from http.server import ThreadingHTTPServer

    from vnlisten.ingest_server import make_handler
    from vnlisten.pipeline.pipeline import EnrichmentPipeline
    from vnlisten.pipeline.router import build_router
    from vnlisten.services import CollectionService
    from vnlisten.storage.sqlite_repo import SqliteRepository

    repo = SqliteRepository(tmp_path / "t.db")
    svc = CollectionService(EnrichmentPipeline([build_router(registry)]), repo)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(svc, token="secret"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/ingest"
    body = _json.dumps({"source": "facebook", "community": {"name": "Hội mẹ", "visibility": "public"},
                        "items": [{"url": "https://www.facebook.com/groups/hoime/posts/1",
                                   "text": "Bé nhà mình uống similac bị táo bón, các mẹ cho hỏi nên đổi sữa nào?"}]})

    def post(token):
        req = urllib.request.Request(url, data=body.encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-VNListen-Token": token})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, _json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, {}

    assert post("wrong")[0] == 401
    status, res = post("secret")
    server.shutdown()
    assert status == 200 and res["new"] == 1
    saved = repo.load_mentions(datetime(2020, 1, 1, tzinfo=UTC))[0]
    assert saved.industry == "me_va_be" and saved.brands == ["abbott"]
    assert saved.community_id == "fb_group:hoime" and saved.community_name == "Hội mẹ"
