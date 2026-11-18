"""Composition root – nơi DUY NHẤT biết class cụ thể nào được dùng.
Đổi SQLite -> Postgres, Lexicon -> PhoBERT, thêm nguồn TikTok... chỉ sửa file này.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .alerts.notifiers import ConsoleNotifier, TelegramNotifier
from .alerts.rules import CrisisKeywordRule, NegativeSpikeRule
from .connectors.google_news import GoogleNewsConnector
from .connectors.google_suggest import GoogleSuggestConnector
from .connectors.web_search import GoogleCseBackend, SearxngBackend, WebSearchConnector
from .connectors.tiki import TikiConnector
from .connectors.youtube import YouTubeConnector
from .domain.models import SourceType, Tier
from .domain.ports import MentionSource, Notifier
from .insights.generators import InsightGenerator, OllamaInsight, RuleBasedInsight
from .pipeline.pipeline import EnrichmentPipeline
from .pipeline.router import build_router
from .services import AlertService, CollectionService, InsightService, KeywordResearchService, MarketplaceService
from .storage.sqlite_repo import SqliteRepository
from .taxonomy import IndustryRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    db_path: Path
    industries_dir: Path
    youtube_api_key: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""
    ollama_url: str = ""
    ollama_model: str = "qwen2.5:7b"
    searxng_url: str = ""
    google_cse_key: str = ""
    google_cse_cx: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        _load_dotenv(PROJECT_ROOT / ".env")
        env = os.environ.get

        def path(key: str, default: str) -> Path:
            p = Path(env(key) or default)
            return p if p.is_absolute() else PROJECT_ROOT / p

        return cls(
            db_path=path("VNLISTEN_DB", "data/vnlisten.db"),
            industries_dir=path("VNLISTEN_INDUSTRIES_DIR", "config/industries"),
            youtube_api_key=env("YOUTUBE_API_KEY", ""),
            telegram_token=env("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=env("TELEGRAM_CHAT_ID", ""),
            ollama_url=env("OLLAMA_URL", ""),
            ollama_model=env("OLLAMA_MODEL", "qwen2.5:7b"),
            searxng_url=env("SEARXNG_URL", ""),
            google_cse_key=env("GOOGLE_CSE_KEY", ""),
            google_cse_cx=env("GOOGLE_CSE_CX", ""),
        )


@dataclass
class App:
    settings: Settings
    registry: IndustryRegistry
    repo: SqliteRepository
    collection: CollectionService
    marketplace: MarketplaceService
    keywords: KeywordResearchService
    alerts: AlertService
    insights: InsightService
    sources_by_tier: dict[Tier, list[MentionSource]] = field(default_factory=dict)
    web_search: MentionSource | None = None


def build_app(settings: Settings | None = None) -> App:
    settings = settings or Settings.from_env()
    registry = IndustryRegistry.from_dir(settings.industries_dir)
    repo = SqliteRepository(settings.db_path)

    # Router chọn đúng taxonomy + từ điển sentiment + hoạt động MKT theo ngành của mention
    pipeline = EnrichmentPipeline([build_router(registry)])

    google_news = GoogleNewsConnector()
    daily_sources: list[MentionSource] = [google_news]
    if settings.youtube_api_key:
        daily_sources.append(YouTubeConnector(settings.youtube_api_key))
    sources_by_tier = {Tier.HOURLY: [google_news], Tier.DAILY: daily_sources}

    notifiers: list[Notifier] = [ConsoleNotifier()]
    if settings.telegram_token and settings.telegram_chat_id:
        notifiers.append(TelegramNotifier(settings.telegram_token, settings.telegram_chat_id))

    generator: InsightGenerator = (
        OllamaInsight(settings.ollama_url, settings.ollama_model) if settings.ollama_url else RuleBasedInsight()
    )
    rules = {
        t.industry: [CrisisKeywordRule(t.brand_name), NegativeSpikeRule(t.brand_name)] for t in registry.all()
    }

    return App(
        settings=settings,
        registry=registry,
        repo=repo,
        collection=CollectionService(pipeline, repo),
        marketplace=MarketplaceService([TikiConnector()], repo),
        keywords=KeywordResearchService(GoogleSuggestConnector(), repo),
        alerts=AlertService(rules, notifiers, repo, repo),
        insights=InsightService(generator, registry, repo, repo, repo),
        sources_by_tier=sources_by_tier,
        web_search=_web_search(settings),
    )


def _web_search(settings: Settings) -> MentionSource | None:
    """SearXNG (tự host, free) ưu tiên; Google CSE nếu có key; không có gì thì tắt nguồn này."""
    if settings.searxng_url:
        # Facebook / TikTok / Threads (bỏ Instagram: kết quả chủ yếu là trang profile, tốn quota thời gian)
        return WebSearchConnector(SearxngBackend(settings.searxng_url),
                                  (SourceType.FACEBOOK, SourceType.TIKTOK, SourceType.THREADS))
    if settings.google_cse_key and settings.google_cse_cx:
        return WebSearchConnector(GoogleCseBackend(settings.google_cse_key, settings.google_cse_cx))
    return None
