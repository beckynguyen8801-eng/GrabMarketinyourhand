"""Lọc bài không liên quan TRƯỚC khi lưu.

Bài lần chạy thật đầu tiên cho thấy công cụ tìm kiếm trả về cả bài tiếng nước ngoài và bài chỉ
"na ná" từ khoá. Quy tắc giữ bài:
  1. Viết bằng tiếng Việt (có đủ ký tự đặc trưng tiếng Việt), VÀ
  2. Nhắc brand / sản phẩm / chủ đề ngành (topic_terms), HOẶC chứa từ khoá rủi ro, HOẶC chứa đúng cụm từ khoá đã dùng để tìm.
"""
from __future__ import annotations

import re

from ..domain.models import Mention
from .text import normalize_for_match

# Chữ chỉ tiếng Việt mới có: ă â đ ê ô ơ ư + toàn bộ khối có dấu thanh (U+1EA0–U+1EF9).
# Cố ý KHÔNG tính á/é/ó… vì tiếng Pháp/Ba Lan/Tây Ban Nha cũng có.
_VI_CHARS = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯẠ-ỹ]")
_SYSTEM_KEYWORDS = {"", "demo", "csv-import", "browser-capture"}


def looks_vietnamese(text: str, min_hits: int = 3, min_ratio: float = 0.02) -> bool:
    letters = sum(ch.isalpha() for ch in text)
    if not letters:
        return False
    hits = len(_VI_CHARS.findall(text))
    return hits >= min_hits and hits / letters >= min_ratio


def keyword_hit(mention: Mention) -> bool:
    kw = normalize_for_match(mention.keyword or "")
    if mention.keyword in _SYSTEM_KEYWORDS or not kw:
        return False
    return re.search(rf"(?<![0-9a-z]){re.escape(kw)}(?![0-9a-z])", normalize_for_match(mention.text)) is not None


def is_relevant(mention: Mention) -> bool:
    if not looks_vietnamese(mention.text):
        return False
    return bool(mention.brands or mention.products or mention.topics or mention.risk_terms or keyword_hit(mention))
