"""HTTP client dùng chung: timeout, retry, giãn cách request để không bị chặn."""
from __future__ import annotations

import logging
import random
import time

import httpx

log = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


class PoliteClient:
    """Wrapper quanh httpx: mỗi request cách nhau min_interval giây (+ jitter), retry khi 429/5xx."""

    def __init__(self, min_interval: float = 2.0, retries: int = 3, timeout: float = 20.0):
        self._client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)
        self._min_interval = min_interval
        self._retries = retries
        self._last_call = 0.0

    def get(self, url: str, **kwargs) -> httpx.Response:
        for attempt in range(1, self._retries + 1):
            self._throttle()
            try:
                resp = self._client.get(url, **kwargs)
            except httpx.TransportError as exc:
                log.warning("GET %s lỗi mạng (%s), thử lại %d/%d", url, exc, attempt, self._retries)
            else:
                if resp.status_code not in (429, 500, 502, 503, 504):
                    resp.raise_for_status()
                    return resp
                log.warning("GET %s -> %s, thử lại %d/%d", url, resp.status_code, attempt, self._retries)
            time.sleep(2**attempt)
        raise RuntimeError(f"GET {url} thất bại sau {self._retries} lần")

    def _throttle(self) -> None:
        wait = self._min_interval + random.uniform(0, 0.5) - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
