"""Domain models – không phụ thuộc vào bất kỳ framework / IO nào."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class SourceType(StrEnum):
    GOOGLE_NEWS = "google_news"
    INSTAGRAM = "instagram"
    WEB = "web"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    THREADS = "threads"
    FORUM = "forum"
    TIKI = "tiki"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Tier(StrEnum):
    """Tần suất quét. HOURLY chỉ dành cho query nóng để tránh bị chặn / hết quota."""

    HOURLY = "hourly"
    DAILY = "daily"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"


class Module(StrEnum):
    SOCIAL_LISTENING = "listening"
    RESEARCH = "research"


class Channel(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class TrackingQuery:
    keyword: str
    category: str = ""
    tier: Tier = Tier.DAILY
    industry: str = ""


@dataclass
class Engagement:
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0

    @property
    def interactions(self) -> int:
        return self.likes + self.comments + self.shares


@dataclass
class Mention:
    """Một bài viết / video / comment / bài báo nhắc tới ngành hàng."""

    source: SourceType
    external_id: str
    url: str
    title: str
    content: str
    published_at: datetime
    author: str = ""
    engagement: Engagement = field(default_factory=Engagement)
    keyword: str = ""
    category: str = ""
    industry: str = ""
    # ---- Các field dưới đây do pipeline enrich ----
    brands: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    risk_terms: list[str] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    sentiment_score: float = 0.0
    activities: list[str] = field(default_factory=list)  # loại hoạt động MKT: khuyen_mai, su_kien_offline...
    hashtags: list[str] = field(default_factory=list)
    # ---- Community nơi bài xuất hiện (group FB, kênh TikTok, diễn đàn...) ----
    community_id: str = ""        # VD "fb_group:hoimebimsua"
    community_name: str = ""
    community_type: str = ""      # fb_group | fb_page | tiktok_account | ig_account | threads_account | youtube_channel | forum | news_site
    community_url: str = ""
    visibility: str = "unknown"   # public | private | unknown

    @property
    def uid(self) -> str:
        return hashlib.sha1(f"{self.source}:{self.external_id}".encode()).hexdigest()

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.content}".strip()


@dataclass
class ProductSnapshot:
    """Ảnh chụp 1 sản phẩm trên sàn TMĐT tại 1 thời điểm (giá, đã bán, rating)."""

    source: SourceType
    product_id: str
    name: str
    brand: str
    category: str
    price: int
    sold_count: int
    rating: float
    review_count: int
    url: str
    captured_at: datetime
    industry: str = ""


@dataclass
class Alert:
    rule: str
    severity: Severity
    title: str
    detail: str
    key: str  # dùng để chống gửi trùng cảnh báo
    created_at: datetime
    industry: str = ""


@dataclass
class KeywordSuggestion:
    """Gợi ý từ khoá từ Google Autocomplete – phản ánh những gì người dùng ĐANG tìm."""

    industry: str
    seed: str
    suggestion: str
    rank: int
    captured_at: datetime
