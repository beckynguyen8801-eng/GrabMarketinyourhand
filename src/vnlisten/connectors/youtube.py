"""YouTube Data API v3 – miễn phí 10.000 units/ngày.

Chi phí quota: search.list = 100 units (đắt!), videos.list & commentThreads.list = 1 unit.
=> ~80 lượt search/ngày. Vì vậy connector này chỉ nên chạy ở tier DAILY.
Comment là nơi có sentiment thật của các mẹ => lấy cả comment top.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..domain.models import Engagement, Mention, SourceType, TrackingQuery
from .http import PoliteClient

log = logging.getLogger(__name__)
API = "https://www.googleapis.com/youtube/v3"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_videos(payload: dict, query: TrackingQuery) -> list[Mention]:
    mentions = []
    for item in payload.get("items", []):
        snip, stats = item["snippet"], item.get("statistics", {})
        mentions.append(
            Mention(
                source=SourceType.YOUTUBE,
                external_id=f"video:{item['id']}",
                url=f"https://www.youtube.com/watch?v={item['id']}",
                title=snip.get("title", ""),
                content=snip.get("description", "")[:2000],
                author=snip.get("channelTitle", ""),
                published_at=_dt(snip["publishedAt"]),
                engagement=Engagement(
                    likes=int(stats.get("likeCount", 0)),
                    comments=int(stats.get("commentCount", 0)),
                    views=int(stats.get("viewCount", 0)),
                ),
                keyword=query.keyword,
                category=query.category,
                industry=query.industry,
            )
        )
    return mentions


def parse_comments(payload: dict, video_id: str, query: TrackingQuery) -> list[Mention]:
    mentions = []
    for item in payload.get("items", []):
        top = item["snippet"]["topLevelComment"]
        snip = top["snippet"]
        mentions.append(
            Mention(
                source=SourceType.YOUTUBE,
                external_id=f"comment:{top['id']}",
                url=f"https://www.youtube.com/watch?v={video_id}&lc={top['id']}",
                title="",
                content=snip.get("textOriginal", ""),
                author=snip.get("authorDisplayName", ""),
                published_at=_dt(snip["publishedAt"]),
                engagement=Engagement(
                    likes=int(snip.get("likeCount", 0)),
                    comments=int(item["snippet"].get("totalReplyCount", 0)),
                ),
                keyword=query.keyword,
                category=query.category,
                industry=query.industry,
            )
        )
    return mentions


class YouTubeConnector:
    source = SourceType.YOUTUBE

    def __init__(self, api_key: str, max_videos: int = 10, comments_per_video: int = 20,
                 client: PoliteClient | None = None):
        self._key = api_key
        self._max_videos = max_videos
        self._comments = comments_per_video
        self._client = client or PoliteClient(min_interval=0.3)

    def fetch(self, query: TrackingQuery, since: datetime) -> list[Mention]:
        search = self._client.get(f"{API}/search", params={
            "key": self._key, "part": "id", "type": "video", "q": query.keyword,
            "regionCode": "VN", "relevanceLanguage": "vi", "order": "relevance",
            "maxResults": self._max_videos,
            "publishedAfter": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }).json()
        ids = [i["id"]["videoId"] for i in search.get("items", [])]
        if not ids:
            return []

        details = self._client.get(f"{API}/videos", params={
            "key": self._key, "part": "snippet,statistics", "id": ",".join(ids),
        }).json()
        mentions = parse_videos(details, query)

        for vid in ids:
            try:
                payload = self._client.get(f"{API}/commentThreads", params={
                    "key": self._key, "part": "snippet", "videoId": vid,
                    "order": "relevance", "maxResults": self._comments, "textFormat": "plainText",
                }).json()
            except Exception as exc:  # video tắt comment => 403, bỏ qua
                log.debug("Bỏ qua comment video %s: %s", vid, exc)
                continue
            mentions += parse_comments(payload, vid, query)
        return mentions
