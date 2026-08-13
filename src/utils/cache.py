"""LLM 응답 디스크 캐시 (JSON, TTL 기반).

같은 (채널, 프롬프트) 조합을 TTL 안에 다시 물어보면 API를 안 때리고 캐시를 돌려준다.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from src.config import CACHE_DIR, get_cache_ttl_hours


def _key(namespace: str, payload: str) -> str:
    return hashlib.sha256(f"{namespace}::{payload}".encode()).hexdigest()


class DiskCache:
    def __init__(self, cache_dir: Path | None = None, ttl_hours: float | None = None):
        self.dir = cache_dir or CACHE_DIR
        self.ttl_seconds = (ttl_hours if ttl_hours is not None else get_cache_ttl_hours()) * 3600
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, payload: str) -> Path:
        return self.dir / f"{_key(namespace, payload)}.json"

    def get(self, namespace: str, payload: str) -> dict | None:
        path = self._path(namespace, payload)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - entry["saved_at"] > self.ttl_seconds:
            path.unlink(missing_ok=True)
            return None
        return entry["value"]

    def set(self, namespace: str, payload: str, value: dict) -> None:
        path = self._path(namespace, payload)
        path.write_text(
            json.dumps({"saved_at": time.time(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )
