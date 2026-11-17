"""Nhận diện HOẠT ĐỘNG MKT trong bài viết (phục vụ module Research).

Mỗi bài có thể thuộc nhiều loại: 1 bài livestream có minigame + voucher.
Bộ từ khoá chung ở đây; ngành nào có từ đặc thù thì khai báo `activity_terms` trong YAML.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ..domain.models import Channel, Mention
from .text import normalize_for_match


@dataclass(frozen=True)
class ActivityType:
    id: str
    name: str
    short: str  # nhãn ngắn cho chart chật chỗ
    channel: Channel
    terms: tuple[str, ...]


BASE_ACTIVITIES: tuple[ActivityType, ...] = (
    ActivityType("khuyen_mai", "Promotion / discount", "Promotion", Channel.ONLINE, (
        "khuyến mãi", "giảm giá", "sale", "flash sale", "voucher", "mã giảm", "ưu đãi", "tặng kèm",
        "mua 1 tặng 1", "freeship", "deal", "combo",
    )),
    ActivityType("minigame", "Minigame / giveaway", "Minigame", Channel.ONLINE, (
        "minigame", "giveaway", "quay số", "trúng thưởng", "bốc thăm", "cuộc thi", "săn quà",
    )),
    # KHÔNG dùng "ad" (trên FB VN "ad ơi" = gọi admin).
    # KHÔNG dùng từ "review" trần: người dùng tự review/hỏi review là thảo luận tự nhiên, không phải hoạt động MKT.
    # Chỉ bắt dấu hiệu có tài trợ / booking.
    ActivityType("kol_review", "KOL / KOC booking", "KOL/KOC", Channel.ONLINE, (
        "kol", "koc", "unbox", "unboxing", "hợp tác cùng", "hợp tác với", "nhà tài trợ", "được tài trợ",
        "sponsored", "link mua ở bio", "link trong bio", "mã giảm giá của mình", "review chân thật",
        "chia sẻ từ chuyên gia", "bác sĩ chia sẻ", "dược sĩ chia sẻ",
    )),
    ActivityType("livestream", "Livestream selling", "Livestream", Channel.ONLINE, (
        "livestream", "live stream", "phiên live", "lên live", "mua trên live",
    )),
    ActivityType("ra_mat", "Product launch", "Launch", Channel.ONLINE, (
        "ra mắt", "sản phẩm mới", "launch", "phiên bản mới", "chính thức có mặt",
    )),
    ActivityType("branding", "Branding campaign / TVC", "Branding", Channel.ONLINE, (
        "tvc", "chiến dịch", "campaign", "đại sứ thương hiệu", "gương mặt đại diện", "viral",
        "phim ngắn", "mv",
    )),
    ActivityType("su_kien_offline", "Offline event / activation", "Event", Channel.OFFLINE, (
        "sự kiện", "hội thảo", "roadshow", "workshop", "triển lãm", "hội chợ", "pop up", "sampling",
        "dùng thử miễn phí", "tại siêu thị", "tại cửa hàng", "offline", "fan meeting",
    )),
    ActivityType("csr", "CSR / community", "CSR", Channel.OFFLINE, (
        # Không dùng "tài trợ" trần: "KOL được tài trợ" là booking, không phải CSR
        "từ thiện", "tài trợ chương trình", "tài trợ quỹ", "trao tặng", "chương trình cộng đồng", "học bổng",
        "vì cộng đồng",
    )),
)

ACTIVITY_INDEX: dict[str, ActivityType] = {a.id: a for a in BASE_ACTIVITIES}
_HASHTAG_RE = re.compile(r"#(\w{3,40})", re.UNICODE)


def activity_name(activity_id: str) -> str:
    a = ACTIVITY_INDEX.get(activity_id)
    return a.name if a else activity_id


def activity_short(activity_id: str) -> str:
    a = ACTIVITY_INDEX.get(activity_id)
    return a.short if a else activity_id


def activity_channel(activity_id: str) -> Channel:
    a = ACTIVITY_INDEX.get(activity_id)
    return a.channel if a else Channel.ONLINE


class ActivityClassifier:
    """Enricher: gắn `activities` + `hashtags` cho mention."""

    def __init__(self, extra_terms: Mapping[str, tuple[str, ...]] | None = None):
        extra_terms = extra_terms or {}
        self._patterns: list[tuple[str, re.Pattern[str]]] = []
        for activity in BASE_ACTIVITIES:
            terms = activity.terms + tuple(extra_terms.get(activity.id, ()))
            alternation = "|".join(re.escape(normalize_for_match(t)) for t in sorted(set(terms), key=len, reverse=True))
            self._patterns.append((activity.id, re.compile(rf"(?<![0-9a-z])(?:{alternation})(?![0-9a-z])")))

    def enrich(self, mention: Mention) -> Mention:
        text = normalize_for_match(mention.text)
        mention.activities = [aid for aid, pattern in self._patterns if pattern.search(text)]
        mention.hashtags = list(dict.fromkeys(tag.lower() for tag in _HASHTAG_RE.findall(mention.text)))
        return mention
