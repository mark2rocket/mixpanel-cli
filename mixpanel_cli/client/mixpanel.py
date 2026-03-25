"""Mixpanel API 클라이언트."""

import sys
from datetime import date, timedelta
from typing import Generator

from mixpanel_cli.client.base import BaseClient
from mixpanel_cli.constants import DEFAULT_EXPORT_CHUNK_DAYS, REGION_URLS


class MixpanelClient:
    def __init__(
        self,
        auth_header: str,
        project_id: str,
        region: str = "us",
        timeout: int = 30,
        debug: bool = False,
    ):
        urls = REGION_URLS.get(region, REGION_URLS["us"])
        self.project_id = project_id
        self.region = region
        self._api = BaseClient(urls["api"], auth_header, timeout, debug)
        self._data = BaseClient(urls["data"], auth_header, timeout, debug)

    # ── Project ──────────────────────────────────────────────────────────────

    def get_projects(self) -> list[dict]:
        result = self._api.get("/api/2.0/projects")
        return result if isinstance(result, list) else result.get("results", [result])

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_insight(
        self,
        event: str,
        from_date: str,
        to_date: str,
        unit: str = "day",
        **kwargs,
    ) -> dict:
        params = {
            "project_id": self.project_id,
            "event": f'["{event}"]',
            "from_date": from_date,
            "to_date": to_date,
            "unit": unit,
            **kwargs,
        }
        return self._api.get("/api/2.0/insights", params=params)

    def get_funnel(self, funnel_id: str, from_date: str, to_date: str, **kwargs) -> dict:
        params = {
            "project_id": self.project_id,
            "funnel_id": funnel_id,
            "from_date": from_date,
            "to_date": to_date,
            **kwargs,
        }
        return self._api.get("/api/2.0/funnels", params=params)

    def get_retention(
        self,
        event: str,
        from_date: str,
        to_date: str,
        unit: str = "day",
        **kwargs,
    ) -> dict:
        params = {
            "project_id": self.project_id,
            "born_event": event,
            "from_date": from_date,
            "to_date": to_date,
            "unit": unit,
            **kwargs,
        }
        return self._api.get("/api/2.0/retention", params=params)

    def get_flow(self, event: str, from_date: str, to_date: str, **kwargs) -> dict:
        params = {
            "project_id": self.project_id,
            "event": event,
            "from_date": from_date,
            "to_date": to_date,
            **kwargs,
        }
        return self._api.get("/api/2.0/flows", params=params)

    # ── Events ────────────────────────────────────────────────────────────────

    def get_event_names(self, limit: int = 255, search: str | None = None) -> list[str]:
        params: dict = {"project_id": self.project_id, "limit": limit, "type": "general"}
        if search:
            params["search"] = search
        result = self._api.get("/api/2.0/events/names", params=params)
        if isinstance(result, list):
            return result
        return result.get("results", [])

    def get_event_details(self, event_name: str) -> dict:
        params = {"project_id": self.project_id, "event": event_name}
        return self._api.get("/api/2.0/events/properties", params=params)

    def get_event_properties(self, event_name: str) -> list[dict]:
        params = {"project_id": self.project_id, "event": event_name, "type": "general"}
        result = self._api.get("/api/2.0/events/properties", params=params)
        if isinstance(result, list):
            return result
        return result.get("results", [])

    # ── Export ────────────────────────────────────────────────────────────────

    def export_events(
        self,
        from_date: str,
        to_date: str,
        event_name: str | None = None,
    ) -> Generator[bytes, None, None]:
        """날짜 범위를 30일 단위 청킹 후 스트리밍 JSONL."""
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        chunk_start = start

        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=DEFAULT_EXPORT_CHUNK_DAYS - 1), end)
            params: dict = {
                "project_id": self.project_id,
                "from_date": chunk_start.isoformat(),
                "to_date": chunk_end.isoformat(),
            }
            if event_name:
                params["event"] = f'["{event_name}"]'

            print(
                f"[export] {chunk_start} ~ {chunk_end} ...",
                file=sys.stderr,
            )

            yield from self._data.stream_get("/api/2.0/export", params=params)

            chunk_start = chunk_end + timedelta(days=1)
