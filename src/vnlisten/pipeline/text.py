"""Chuẩn hoá text tiếng Việt."""
from __future__ import annotations

import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_NON_WORD_RE = re.compile(r"[^0-9a-z+]+")


def strip_html(value: str) -> str:
    return html.unescape(_TAG_RE.sub(" ", value or "")).strip()


def strip_accents(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_for_match(value: str) -> str:
    """'Sữa Bột NAN-Optipro!!' -> 'sua bot nan optipro'. Dùng để match alias (người dùng hay gõ không dấu)."""
    lowered = strip_accents(value.lower())
    return _NON_WORD_RE.sub(" ", lowered).strip()


NEGATORS_NO_ACCENT = {"khong", "ko", "k", "chang", "cha", "chua", "hong", "hok"}


def is_negated_no_accent(normalized_text: str, start: int, window: int = 3) -> bool:
    """Có từ phủ định trong `window` từ ngay trước vị trí start? (text đã bỏ dấu)"""
    return any(tok in NEGATORS_NO_ACCENT for tok in normalized_text[:start].split()[-window:])


def normalize_keep_accents(value: str) -> str:
    """Giữ dấu, chỉ lowercase + gộp khoảng trắng. Dùng cho sentiment (dấu mang nghĩa)."""
    value = unicodedata.normalize("NFC", value.lower())
    return re.sub(r"\s+", " ", value).strip()
