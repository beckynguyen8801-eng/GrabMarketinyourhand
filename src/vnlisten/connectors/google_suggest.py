"""Google Autocomplete – miễn phí, không cần key. Cho biết người dùng ĐANG gõ tìm gì quanh 1 seed keyword.

Mở rộng seed bằng cách ghép thêm ký tự a..z / câu hỏi ("có tốt không", "loại nào") để ra long-tail.
Không có search volume (cái đó cần Google Ads Keyword Planner) – dùng thứ hạng gợi ý làm proxy.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

from ..domain.models import KeywordSuggestion
from .http import PoliteClient

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
MODIFIERS = ("", "có tốt không", "loại nào tốt", "giá", "review", "cho bé", "cho người già")


def parse_suggestions(body: str) -> list[str]:
    data = json.loads(body)
    return [s for s in data[1] if isinstance(s, str)] if len(data) > 1 else []


class GoogleSuggestConnector:
    def __init__(self, client: PoliteClient | None = None, modifiers: tuple[str, ...] = MODIFIERS):
        self._client = client or PoliteClient(min_interval=1.0)
        self._modifiers = modifiers

    def suggest(self, seed: str, industry: str) -> list[KeywordSuggestion]:
        now = datetime.now(UTC)
        seen: dict[str, int] = {}
        for modifier in self._modifiers:
            q = f"{seed} {modifier}".strip()
            resp = self._client.get(SUGGEST_URL, params={"client": "firefox", "hl": "vi", "gl": "vn", "q": q})
            for rank, text in enumerate(parse_suggestions(resp.text), 1):
                seen.setdefault(text, rank)
        return [KeywordSuggestion(industry, seed, text, rank, now) for text, rank in seen.items()]
