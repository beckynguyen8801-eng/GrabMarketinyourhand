"""Sentiment tiếng Việt.

- LexiconSentimentAnalyzer: free, nhanh, chạy được ngay. Độ chính xác tầm 65-75%,
  đủ để bắt xu hướng & tiêu cực rõ ràng. Mở rộng bằng cách bổ sung từ điển.
- TransformerSentimentAnalyzer: dùng model PhoBERT trên HuggingFace, chạy local (free),
  chính xác hơn nhưng nặng. Cài: pip install -e ".[ml]".

Cả 2 đều implement Enricher => đổi qua lại không phải sửa pipeline (LSP/OCP).
"""
from __future__ import annotations

import re

from ..domain.models import Mention, Sentiment
from .text import normalize_keep_accents

# Từ điển CHUNG cho mọi ngành. Từ vựng đặc thù ngành nằm trong YAML (sentiment.positive/negative).
POSITIVE_TERMS = (
    "tốt", "rất tốt", "thích", "ưng", "ưng ý", "hài lòng", "đáng tiền", "recommend", "ok lắm",
    "hợp", "yên tâm", "chất lượng", "rẻ", "giá tốt", "khuyên dùng", "tuyệt vời", "xịn", "chính hãng",
    "nhiệt tình", "uy tín", "ổn áp", "mê", "đỉnh",
)
NEGATIVE_TERMS = (
    "tệ", "dở", "kém", "thất vọng", "không hợp", "đắt", "giá cao", "lừa đảo", "hàng giả", "hàng nhái",
    "thu hồi", "ngộ độc", "nhiễm khuẩn", "phốt", "bóc phốt", "tẩy chay", "đừng mua", "không nên mua",
    "chán", "bực", "mùi lạ", "hết hạn", "dị ứng", "tiền mất tật mang",
)
NEGATORS = {"không", "ko", "k", "chẳng", "chả", "chưa", "hông", "đâu có"}

# Từ rủi ro nặng: x2 trọng số
HEAVY_NEGATIVE = {"sữa giả", "thuốc giả", "hàng giả", "thu hồi", "ngộ độc", "nhiễm khuẩn", "lừa đảo",
                  "tẩy chay", "sốc phản vệ", "nhập viện"}


def _compile(terms: tuple[str, ...]) -> list[tuple[str, re.Pattern[str]]]:
    # \w trong Python hỗ trợ unicode => ranh giới từ đúng với tiếng Việt có dấu
    ordered = sorted(set(terms), key=len, reverse=True)
    return [(t, re.compile(rf"(?<!\w){re.escape(t)}(?!\w)")) for t in ordered]


class LexiconSentimentAnalyzer:
    def __init__(self, extra_positive: tuple[str, ...] = (), extra_negative: tuple[str, ...] = (),
                 threshold: float = 0.2, negation_window: int = 3):
        pos = [(t, p, 1) for t, p in _compile(POSITIVE_TERMS + tuple(extra_positive))]
        neg = [(t, p, -1) for t, p in _compile(NEGATIVE_TERMS + tuple(extra_negative))]
        # Duyệt cụm DÀI trước bất kể cực tính: "không hiệu quả" phải thắng "hiệu quả"
        self._terms = sorted(pos + neg, key=lambda x: len(x[0]), reverse=True)
        self._threshold = threshold
        self._window = negation_window

    def score(self, text: str) -> float:
        text = normalize_keep_accents(text)
        consumed: list[tuple[int, int]] = []  # tránh đếm "hăm" khi đã đếm "hăm tã"
        pos = neg = 0.0

        for term, pattern, polarity in self._terms:
            for match in pattern.finditer(text):
                start, end = match.span()
                if any(s < end and start < e for s, e in consumed):
                    continue
                consumed.append((start, end))
                weight = 2.0 if term in HEAVY_NEGATIVE else 1.0
                sign = -polarity if self._is_negated(text, start) else polarity
                if sign > 0:
                    pos += weight
                else:
                    neg += weight

        total = pos + neg
        return 0.0 if total == 0 else (pos - neg) / total

    def _is_negated(self, text: str, start: int) -> bool:
        before = text[:start].split()[-self._window :]
        joined = " ".join(before)
        return any(tok in NEGATORS for tok in before) or "đâu có" in joined

    def enrich(self, mention: Mention) -> Mention:
        score = self.score(mention.text)
        mention.sentiment_score = round(score, 3)
        if score >= self._threshold:
            mention.sentiment = Sentiment.POSITIVE
        elif score <= -self._threshold:
            mention.sentiment = Sentiment.NEGATIVE
        else:
            mention.sentiment = Sentiment.NEUTRAL
        return mention


class TransformerSentimentAnalyzer:
    """PhoBERT fine-tune sentiment (NEG/POS/NEU). Lazy-load để không bắt buộc cài torch."""

    _LABELS = {"NEG": Sentiment.NEGATIVE, "POS": Sentiment.POSITIVE, "NEU": Sentiment.NEUTRAL}

    def __init__(self, model_name: str = "wonrax/phobert-base-vietnamese-sentiment"):
        from transformers import pipeline  # noqa: PLC0415 – import nặng, chỉ khi cần

        self._clf = pipeline("sentiment-analysis", model=model_name)

    def enrich(self, mention: Mention) -> Mention:
        result = self._clf(mention.text[:1000], truncation=True)[0]
        label = self._LABELS.get(result["label"], Sentiment.NEUTRAL)
        mention.sentiment = label
        sign = {Sentiment.POSITIVE: 1, Sentiment.NEGATIVE: -1}.get(label, 0)
        mention.sentiment_score = round(sign * float(result["score"]), 3)
        return mention
