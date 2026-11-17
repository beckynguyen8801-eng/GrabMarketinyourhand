"""Local ingest server cho browser extension. Chỉ nghe 127.0.0.1 – không mở ra mạng ngoài.

    vnlisten serve            # http://127.0.0.1:8765
    GET  /health  -> {"ok": true}
    POST /ingest  -> {"received": n, "kept": k, "new": m}

Đặt VNLISTEN_INGEST_TOKEN trong .env để bắt extension gửi kèm header X-VNListen-Token.
"""
from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .connectors.browser_capture import capture_to_mentions
from .services import CollectionService

log = logging.getLogger(__name__)
MAX_BODY = 5 * 1024 * 1024


def make_handler(collection: CollectionService, token: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-VNListen-Token")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # noqa: N802 – CORS preflight
            self._send(204, {})

        def do_GET(self) -> None:  # noqa: N802
            self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/ingest":
                return self._send(404, {"error": "not found"})
            if token and self.headers.get("X-VNListen-Token") != token:
                return self._send(401, {"error": "bad token"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._send(413, {"error": "empty or too large"})
            try:
                payload = json.loads(self.rfile.read(length))
                mentions = capture_to_mentions(payload)
            except (ValueError, json.JSONDecodeError) as exc:
                return self._send(400, {"error": str(exc)})
            stats = collection.ingest(mentions)
            log.info("ingest %s: received=%d kept=%d new=%d", payload.get("source"), stats.fetched, stats.kept,
                     stats.new)
            return self._send(200, {"received": stats.fetched, "kept": stats.kept, "new": stats.new})

        def log_message(self, *args) -> None:  # tắt log mặc định ồn ào của http.server
            return

    return Handler


def serve(collection: CollectionService, port: int = 8765) -> None:
    token = os.environ.get("VNLISTEN_INGEST_TOKEN", "")
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(collection, token))
    log.info("Ingest server on http://127.0.0.1:%d (token %s). Ctrl+C to stop.", port, "on" if token else "off")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
