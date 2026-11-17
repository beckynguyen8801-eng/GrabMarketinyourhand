"""Nhận diện COMMUNITY (group FB, page, kênh TikTok/IG/Threads/YouTube, diễn đàn, báo) từ URL của bài.

Không cần API: cấu trúc URL của các nền tảng đủ để biết bài thuộc nhóm/kênh nào.
Tên hiển thị lấy từ dữ liệu capture (extension) nếu có, không thì dùng slug trong URL.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from ..domain.models import Mention, SourceType

# (pattern trên host+path, type, nhóm regex chứa slug)
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:^|\.)facebook\.com/groups/([^/?#]+)"), "fb_group"),
    (re.compile(r"(?:^|\.)tiktok\.com/@([^/?#]+)"), "tiktok_account"),
    (re.compile(r"(?:^|\.)threads\.(?:net|com)/@([^/?#]+)"), "threads_account"),
    (re.compile(r"(?:^|\.)instagram\.com/(?!p/|reel/|explore/|stories/)([^/?#]+)"), "ig_account"),
    (re.compile(r"(?:^|\.)youtube\.com/(@[^/?#]+|channel/[^/?#]+)"), "youtube_channel"),
    (re.compile(r"(?:^|\.)facebook\.com/(?!groups/|watch|story\.php|permalink\.php|share)([^/?#]+)"), "fb_page"),
    (re.compile(r"(?:^|\.)(webtretho\.com|lamchame\.com|marrybaby\.vn|tinhte\.vn|voz\.vn)/"), "forum"),
)
_PUBLIC_BY_DEFAULT = {"fb_page", "tiktok_account", "threads_account", "youtube_channel", "forum", "news_site"}


def resolve_community(url: str) -> tuple[str, str, str, str]:
    """-> (community_id, type, slug/name, base_url). Rỗng nếu không nhận ra."""
    if not url:
        return "", "", "", ""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.").removeprefix("web.")
    target = f"{host}{parsed.path}"
    for pattern, kind in _RULES:
        m = pattern.search(target)
        if m:
            slug = unquote(m.group(1)).strip("/")
            if kind == "forum":
                return f"forum:{slug}", kind, slug, f"https://{slug}"
            base = f"https://{host}/{'groups/' if kind == 'fb_group' else ''}{slug}"
            return f"{kind}:{slug.lower()}", kind, slug, base
    return "", "", "", ""


class CommunityResolver:
    """Enricher: điền community_* nếu bài chưa có (bài từ extension thường đã có tên group)."""

    def enrich(self, mention: Mention) -> Mention:
        if not mention.community_id:
            cid, kind, slug, base = resolve_community(mention.url)
            if not cid and mention.source is SourceType.GOOGLE_NEWS and mention.author:
                cid, kind, slug, base = f"news_site:{mention.author.lower()}", "news_site", mention.author, ""
            if not cid and mention.source is SourceType.YOUTUBE and mention.author:
                cid, kind, slug, base = f"youtube_channel:{mention.author.lower()}", "youtube_channel", mention.author, ""
            mention.community_id, mention.community_type, mention.community_url = cid, kind, base
            mention.community_name = mention.community_name or slug
        if mention.visibility == "unknown" and mention.community_type in _PUBLIC_BY_DEFAULT:
            mention.visibility = "public"
        return mention
