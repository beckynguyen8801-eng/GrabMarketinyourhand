from datetime import timedelta

from vnlisten.alerts.rules import CrisisKeywordRule
from vnlisten.domain.models import SourceType, TrackingQuery
from vnlisten.pipeline.entity_matcher import EntityMatcher
from vnlisten.pipeline.pipeline import EnrichmentPipeline
from vnlisten.pipeline.sentiment import LexiconSentimentAnalyzer
from vnlisten.services import AlertService, CollectionService
from vnlisten.storage.sqlite_repo import SqliteRepository

from .conftest import NOW, make_mention


class FakeSource:
    source = SourceType.FACEBOOK

    def __init__(self, items):
        self.items = items

    def fetch(self, query, since):
        return self.items


class BrokenSource:
    source = SourceType.TIKTOK

    def fetch(self, query, since):
        raise RuntimeError("bị chặn")


class SpyNotifier:
    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)


def test_collect_isolates_errors_and_upserts(tmp_path, taxonomy):
    repo = SqliteRepository(tmp_path / "t.db")
    svc = CollectionService(EnrichmentPipeline([EntityMatcher(taxonomy),
                                                LexiconSentimentAnalyzer(taxonomy.positive_terms, taxonomy.negative_terms)]), repo)
    item = make_mention("Bỉm bobby bị tràn, thất vọng", ext="p1", likes=1)
    stats = svc.collect([BrokenSource(), FakeSource([item])], [TrackingQuery("bobby")], NOW - timedelta(days=1))
    assert stats.new == 1 and len(stats.errors) == 1

    item.engagement.likes = 99  # lần quét sau: engagement tăng -> update, không tạo bản mới
    assert svc.collect([FakeSource([item])], [TrackingQuery("bobby")], NOW - timedelta(days=1)).new == 0
    saved = repo.load_mentions(NOW - timedelta(days=1), NOW)
    assert saved[0].engagement.likes == 99 and saved[0].brands == ["bobby"]


def test_alert_service_dedupes(tmp_path):
    repo = SqliteRepository(tmp_path / "t.db")
    repo.save_mentions([make_mention(str(i), brands=["abbott"], risk=["thu hồi"], likes=200, industry="me_va_be")
                        for i in range(3)])
    repo.save_mentions([make_mention("h", brands=["abbott"], risk=["thu hồi"], likes=5, industry="y_te_suc_khoe")])
    spy = SpyNotifier()
    rules = {"me_va_be": [CrisisKeywordRule(str)], "y_te_suc_khoe": [CrisisKeywordRule(str)]}
    svc = AlertService(rules, [spy], repo, repo)
    fired = svc.run(NOW)
    assert len(fired) == 1 and fired[0].industry == "me_va_be"  # ngành Y tế chưa đủ ngưỡng
    assert repo.recent_alerts(industry="y_te_suc_khoe") == []
    assert svc.run(NOW) == []  # chạy lại trong ngày không spam
    assert len(spy.sent) == 1


def test_repo_migrates_old_schema_and_filters_industry(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    old = sqlite3.connect(db)  # schema v0.1: chưa có industry / activities / hashtags
    old.executescript("""CREATE TABLE mentions (uid TEXT PRIMARY KEY, source TEXT NOT NULL, external_id TEXT NOT NULL,
        url TEXT, title TEXT, content TEXT, author TEXT, published_at TEXT NOT NULL, collected_at TEXT NOT NULL,
        likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
        keyword TEXT, category TEXT, brands TEXT, products TEXT, risk_terms TEXT, sentiment TEXT, sentiment_score REAL);
        INSERT INTO mentions VALUES ('u1','facebook','e1','','','cũ','', '2026-11-17T10:00:00+00:00',
        '2026-11-17T10:00:00+00:00',0,0,0,0,'','','[]','[]','[]','neutral',0);""")
    old.close()

    repo = SqliteRepository(db)
    repo.save_mentions([make_mention("mới", industry="y_te_suc_khoe", activities=["livestream"], hashtags=["x"])])
    everything = repo.load_mentions(NOW - timedelta(days=1), NOW)
    health = repo.load_mentions(NOW - timedelta(days=1), NOW, industry="y_te_suc_khoe")
    assert len(everything) == 2
    assert len(health) == 1 and health[0].activities == ["livestream"] and health[0].hashtags == ["x"]


def test_build_app_wires_everything(tmp_path):
    import dataclasses

    from vnlisten.container import Settings, build_app

    s = dataclasses.replace(Settings.from_env(), db_path=tmp_path / "x.db", searxng_url="http://127.0.0.1:8888")
    app = build_app(s)
    assert set(app.registry.ids()) == {"me_va_be", "y_te_suc_khoe"}
    assert app.web_search is not None
