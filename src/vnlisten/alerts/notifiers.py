from __future__ import annotations

import logging

import httpx

from ..domain.models import Alert, Severity

log = logging.getLogger(__name__)


def _format(alert: Alert) -> str:
    icon = "🔴" if alert.severity is Severity.HIGH else "🟠"
    return f"{icon} {alert.title}\n{alert.detail}"


class ConsoleNotifier:
    def send(self, alert: Alert) -> None:
        print(_format(alert))  # noqa: T201


class TelegramNotifier:
    """Bot Telegram – free. Tạo bot qua @BotFather, lấy chat_id qua @userinfobot."""

    def __init__(self, token: str, chat_id: str):
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id

    def send(self, alert: Alert) -> None:
        try:
            httpx.post(self._url, json={"chat_id": self._chat_id, "text": _format(alert)}, timeout=10)
        except httpx.HTTPError as exc:
            log.error("Gửi Telegram thất bại: %s", exc)
