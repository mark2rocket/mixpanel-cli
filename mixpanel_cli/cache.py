"""이벤트 목록 로컬 캐시 — TTL 1시간."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_CACHE_DIR = Path.home() / ".mixpanel" / "cache"
_TTL = 3600  # 1시간


def _cache_path(project_id: str) -> Path:
    return _CACHE_DIR / f"events_{project_id}.json"


def get_cached_events(project_id: str) -> list[str] | None:
    """캐시에서 이벤트 목록 반환. 만료됐거나 없으면 None."""
    path = _cache_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("cached_at", 0) > _TTL:
            return None
        return data["events"]
    except Exception:
        return None


def set_cached_events(project_id: str, events: list[str]) -> None:
    """이벤트 목록을 캐시 파일에 저장."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(project_id).write_text(
        json.dumps({"cached_at": time.time(), "events": events})
    )


def invalidate_cache(project_id: str) -> None:
    """캐시 파일 삭제."""
    path = _cache_path(project_id)
    if path.exists():
        path.unlink()
