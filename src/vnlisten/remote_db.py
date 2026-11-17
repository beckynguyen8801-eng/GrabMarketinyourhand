"""Đọc database từ nhánh `data` của repo GitHub – dùng cho chế độ chạy miễn phí trên cloud:

    GitHub Actions (cron) chạy collector  ->  force-push data/vnlisten.db lên nhánh `data` (1 commit, không phình repo)
    Streamlit Community Cloud              ->  tải file đó về (read-only) để hiển thị dashboard

Repo private => cần token chỉ-đọc (fine-grained PAT, quyền Contents: Read-only, chỉ cho repo này).
"""
from __future__ import annotations

from pathlib import Path

import httpx

API = "https://api.github.com/repos/{repo}/contents/{path}"


def download_db(repo: str, dest: Path, token: str = "", branch: str = "data", path: str = "vnlisten.db",
                client: httpx.Client | None = None) -> bool:
    """Tải DB về `dest`. Trả False nếu nhánh/file chưa tồn tại (collector chưa chạy lần nào)."""
    headers = {"Accept": "application/vnd.github.raw+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    own_client = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    try:
        resp = client.get(API.format(repo=repo, path=path), params={"ref": branch}, headers=headers)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(dest)  # thay file nguyên khối – không bao giờ để DB dở dang
        return True
    finally:
        if own_client:
            client.close()
