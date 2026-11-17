"""SQLite repository – 0 đồng, 1 file, đủ cho 1 user tới vài triệu mention.
Khi lớn hơn: viết PostgresRepository implement cùng các Protocol trong domain/ports.py.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ..domain.models import (
    Alert, Engagement, KeywordSuggestion, Mention, ProductSnapshot, Sentiment, Severity, SourceType,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    uid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    url TEXT, title TEXT, content TEXT, author TEXT,
    published_at TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
    keyword TEXT, category TEXT,
    brands TEXT, products TEXT, risk_terms TEXT,
    sentiment TEXT, sentiment_score REAL
);
CREATE INDEX IF NOT EXISTS ix_mentions_published ON mentions(published_at);

CREATE TABLE IF NOT EXISTS product_snapshots (
    source TEXT, product_id TEXT, name TEXT, brand TEXT, category TEXT,
    price INTEGER, sold_count INTEGER, rating REAL, review_count INTEGER, url TEXT,
    captured_at TEXT,
    PRIMARY KEY (source, product_id, captured_at)
);

CREATE TABLE IF NOT EXISTS alerts (
    key TEXT PRIMARY KEY, rule TEXT, severity TEXT, title TEXT, detail TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, text TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    industry TEXT, keyword TEXT, created_at TEXT, PRIMARY KEY (industry, keyword)
);

CREATE TABLE IF NOT EXISTS keyword_suggestions (
    industry TEXT, seed TEXT, suggestion TEXT, rank INTEGER, captured_at TEXT,
    PRIMARY KEY (industry, seed, suggestion, captured_at)
);
"""

# Cột thêm ở các phiên bản sau – tự ALTER TABLE cho DB cũ (không mất dữ liệu)
MIGRATIONS: dict[str, dict[str, str]] = {
    "mentions": {"industry": "TEXT DEFAULT ''", "activities": "TEXT DEFAULT '[]'", "hashtags": "TEXT DEFAULT '[]'",
                 "community_id": "TEXT DEFAULT ''", "community_name": "TEXT DEFAULT ''",
                 "community_type": "TEXT DEFAULT ''", "community_url": "TEXT DEFAULT ''",
                 "visibility": "TEXT DEFAULT 'unknown'"},
    "product_snapshots": {"industry": "TEXT DEFAULT ''"},
    "alerts": {"industry": "TEXT DEFAULT ''"},
    "insights": {"industry": "TEXT DEFAULT ''"},
}

MENTION_COLUMNS = (
    "uid", "source", "external_id", "url", "title", "content", "author", "published_at", "collected_at",
    "likes", "comments", "shares", "views", "keyword", "category", "brands", "products", "risk_terms",
    "sentiment", "sentiment_score", "industry", "activities", "hashtags",
    "community_id", "community_name", "community_type", "community_url", "visibility",
)


def _iso(dt: datetime) -> str:
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(UTC).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _industry_filter(industry: str | None) -> tuple[str, tuple]:
    return (" AND industry = ?", (industry,)) if industry else ("", ())


class SqliteRepository:
    """Implement MentionRepository, SnapshotRepository, AlertRepository, InsightRepository, KeywordRepository."""

    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        with self._conn:
            for table, columns in MIGRATIONS.items():
                existing = {r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")}
                for column, ddl in columns.items():
                    if column not in existing:
                        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            self._conn.execute("CREATE INDEX IF NOT EXISTS ix_mentions_industry ON mentions(industry, published_at)")

    # ---------------- Mentions ----------------
    def save_mentions(self, mentions: Sequence[Mention]) -> int:
        """Upsert: mention cũ được cập nhật engagement mới nhất. Trả về số mention MỚI."""
        before = self._count("mentions")
        now = _iso(datetime.now(UTC))
        placeholders = ",".join("?" * len(MENTION_COLUMNS))
        with self._conn:
            self._conn.executemany(
                f"""
                INSERT INTO mentions ({",".join(MENTION_COLUMNS)}) VALUES ({placeholders})
                ON CONFLICT(uid) DO UPDATE SET
                  likes=excluded.likes, comments=excluded.comments,
                  shares=excluded.shares, views=excluded.views,
                  community_name=CASE WHEN excluded.community_name != '' THEN excluded.community_name
                                      ELSE mentions.community_name END,
                  visibility=CASE WHEN excluded.visibility != 'unknown' THEN excluded.visibility
                                  ELSE mentions.visibility END
                """,
                [
                    (
                        m.uid, m.source.value, m.external_id, m.url, m.title, m.content, m.author,
                        _iso(m.published_at), now,
                        m.engagement.likes, m.engagement.comments, m.engagement.shares, m.engagement.views,
                        m.keyword, m.category,
                        json.dumps(m.brands), json.dumps(m.products), json.dumps(m.risk_terms, ensure_ascii=False),
                        m.sentiment.value, m.sentiment_score,
                        m.industry, json.dumps(m.activities), json.dumps(m.hashtags, ensure_ascii=False),
                        m.community_id, m.community_name, m.community_type, m.community_url, m.visibility,
                    )
                    for m in mentions
                ],
            )
        return self._count("mentions") - before

    def load_mentions(self, since: datetime, until: datetime | None = None,
                      industry: str | None = None) -> list[Mention]:
        until = until or datetime.now(UTC)
        where, params = _industry_filter(industry)
        rows = self._conn.execute(
            f"SELECT * FROM mentions WHERE published_at >= ? AND published_at <= ?{where} ORDER BY published_at",
            (_iso(since), _iso(until), *params),
        ).fetchall()
        return [self._row_to_mention(r) for r in rows]

    @staticmethod
    def _row_to_mention(r: sqlite3.Row) -> Mention:
        return Mention(
            source=SourceType(r["source"]), external_id=r["external_id"], url=r["url"] or "",
            title=r["title"] or "", content=r["content"] or "", author=r["author"] or "",
            published_at=_from_iso(r["published_at"]),
            engagement=Engagement(r["likes"], r["comments"], r["shares"], r["views"]),
            keyword=r["keyword"] or "", category=r["category"] or "", industry=r["industry"] or "",
            brands=json.loads(r["brands"] or "[]"), products=json.loads(r["products"] or "[]"),
            risk_terms=json.loads(r["risk_terms"] or "[]"),
            sentiment=Sentiment(r["sentiment"]), sentiment_score=r["sentiment_score"] or 0.0,
            activities=json.loads(r["activities"] or "[]"), hashtags=json.loads(r["hashtags"] or "[]"),
            community_id=r["community_id"] or "", community_name=r["community_name"] or "",
            community_type=r["community_type"] or "", community_url=r["community_url"] or "",
            visibility=r["visibility"] or "unknown",
        )

    # ---------------- Snapshots ----------------
    def save_snapshots(self, snapshots: Sequence[ProductSnapshot]) -> int:
        with self._conn:
            self._conn.executemany(
                """INSERT OR REPLACE INTO product_snapshots
                   (source, product_id, name, brand, category, price, sold_count, rating, review_count, url,
                    captured_at, industry) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (s.source.value, s.product_id, s.name, s.brand, s.category, s.price,
                     s.sold_count, s.rating, s.review_count, s.url, _iso(s.captured_at), s.industry)
                    for s in snapshots
                ],
            )
        return len(snapshots)

    def latest_snapshots(self, industry: str | None = None) -> list[ProductSnapshot]:
        where, params = _industry_filter(industry)
        rows = self._conn.execute(
            f"""
            SELECT p.* FROM product_snapshots p
            JOIN (SELECT source, product_id, MAX(captured_at) AS mx
                  FROM product_snapshots GROUP BY source, product_id) l
              ON p.source = l.source AND p.product_id = l.product_id AND p.captured_at = l.mx
            WHERE 1=1{where.replace("industry", "p.industry")}
            """,
            params,
        ).fetchall()
        return [
            ProductSnapshot(
                SourceType(r["source"]), r["product_id"], r["name"], r["brand"], r["category"],
                r["price"], r["sold_count"], r["rating"], r["review_count"], r["url"],
                _from_iso(r["captured_at"]), r["industry"] or "",
            )
            for r in rows
        ]

    # ---------------- Alerts ----------------
    def alert_exists(self, key: str) -> bool:
        return self._conn.execute("SELECT 1 FROM alerts WHERE key = ?", (key,)).fetchone() is not None

    def save_alert(self, alert: Alert) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO alerts (key, rule, severity, title, detail, created_at, industry) "
                "VALUES (?,?,?,?,?,?,?)",
                (alert.key, alert.rule, alert.severity.value, alert.title, alert.detail,
                 _iso(alert.created_at), alert.industry),
            )

    def recent_alerts(self, limit: int = 50, industry: str | None = None) -> list[Alert]:
        where, params = _industry_filter(industry)
        rows = self._conn.execute(
            f"SELECT * FROM alerts WHERE 1=1{where} ORDER BY created_at DESC LIMIT ?", (*params, limit)
        ).fetchall()
        return [
            Alert(r["rule"], Severity(r["severity"]), r["title"], r["detail"], r["key"],
                  _from_iso(r["created_at"]), r["industry"] or "")
            for r in rows
        ]

    # ---------------- Insights ----------------
    def save_insight(self, text: str, created_at: datetime, industry: str = "") -> None:
        with self._conn:
            self._conn.execute("INSERT INTO insights(created_at, text, industry) VALUES (?, ?, ?)",
                               (_iso(created_at), text, industry))

    def latest_insight(self, industry: str | None = None) -> tuple[datetime, str] | None:
        where, params = _industry_filter(industry)
        row = self._conn.execute(
            f"SELECT created_at, text FROM insights WHERE 1=1{where} ORDER BY id DESC LIMIT 1", params
        ).fetchone()
        return (_from_iso(row["created_at"]), row["text"]) if row else None

    # ---------------- Keyword research ----------------
    def save_suggestions(self, suggestions: Sequence[KeywordSuggestion]) -> int:
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO keyword_suggestions VALUES (?,?,?,?,?)",
                [(s.industry, s.seed, s.suggestion, s.rank, _iso(s.captured_at)) for s in suggestions],
            )
        return len(suggestions)

    def suggestion_history(self, industry: str) -> list[KeywordSuggestion]:
        rows = self._conn.execute(
            "SELECT * FROM keyword_suggestions WHERE industry = ? ORDER BY captured_at", (industry,)
        ).fetchall()
        return [KeywordSuggestion(r["industry"], r["seed"], r["suggestion"], r["rank"], _from_iso(r["captured_at"]))
                for r in rows]

    # ---------------- Watchlist (từ khoá người dùng tự thêm từ thanh search) ----------------
    def add_watch(self, industry: str, keyword: str) -> None:
        with self._conn:
            self._conn.execute("INSERT OR IGNORE INTO watchlist VALUES (?,?,?)",
                               (industry, keyword.strip(), _iso(datetime.now(UTC))))

    def remove_watch(self, industry: str, keyword: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM watchlist WHERE industry = ? AND keyword = ?", (industry, keyword))

    def watchlist(self, industry: str | None = None) -> list[tuple[str, str]]:
        where, params = _industry_filter(industry)
        rows = self._conn.execute(f"SELECT industry, keyword FROM watchlist WHERE 1=1{where} ORDER BY created_at",
                                  params).fetchall()
        return [(r["industry"], r["keyword"]) for r in rows]

    def _count(self, table: str) -> int:
        return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 – table nội bộ
