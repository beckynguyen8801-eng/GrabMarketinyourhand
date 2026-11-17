"""Trích cụm từ (n-gram) từ text tiếng Việt – dùng chung cho trend & keyword theo sản phẩm.

Tiếng Việt: 1 âm tiết hiếm khi có nghĩa độc lập ("sữa", "bé") => dùng cụm 2-3 âm tiết.
"""
from __future__ import annotations

import re

import pandas as pd

# Stopword tối thiểu cho tiếng Việt mạng xã hội – mở rộng dần khi thấy cụm rác lọt vào kết quả
STOPWORDS = set("""
và là của có cho các những được với này thì mà nhé nha ạ ơi mình em anh chị bạn mọi người
không cũng đã đang sẽ rồi lắm quá rất hơn nào gì đâu ai khi nếu vì nên để từ trong ngoài trên dưới
một hai ba bé con mẹ ở tại đi về ra vào lại còn thấy làm dùng uống mua bị nhà hay như bao giờ
ạ à ừ thế vậy luôn nữa cả chỉ mới sau trước hỏi xin cho biết giữa bv tôi nó họ ta
""".split())
_TOKEN_RE = re.compile(r"[^\W\d_]+|\d+[a-z]*", re.UNICODE)


def phrases(text: str, n: int) -> set[str]:
    """Các n-gram (giữ dấu, lowercase) không bắt đầu/kết thúc bằng stopword. Set => đếm theo số bài."""
    tokens = [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1 or t.isdigit()]
    grams = set()
    for i in range(len(tokens) - n + 1):
        gram = tokens[i : i + n]
        if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
            continue
        grams.add(" ".join(gram))
    return grams


def drop_subphrases(counts: dict[str, int], ratio: float = 0.8) -> dict[str, int]:
    """Bỏ cụm con nếu cụm dài hơn chứa nó có tần suất tương đương: giữ "men vi sinh", bỏ "men vi"."""
    return {
        p: c for p, c in counts.items()
        if not any(p != longer and f" {p} " in f" {longer} " and lc >= ratio * c for longer, lc in counts.items())
    }


def diversify(df: pd.DataFrame, column: str, max_shared_tokens: int = 1) -> pd.DataFrame:
    """Giữ thứ tự, bỏ dòng có cụm trùng > max_shared_tokens từ với cụm đã chọn."""
    chosen: list[set[str]] = []
    keep_idx = []
    for idx, phrase in df[column].items():
        tokens = set(phrase.split())
        if any(len(tokens & c) > max_shared_tokens for c in chosen):
            continue
        chosen.append(tokens)
        keep_idx.append(idx)
    return df.loc[keep_idx].reset_index(drop=True)
