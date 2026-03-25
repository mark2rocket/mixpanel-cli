"""공통 HTTP 클라이언트 — 인증, retry, timeout."""

import time
from typing import Any, Generator

import httpx

from mixpanel_cli.constants import DEFAULT_TIMEOUT
from mixpanel_cli.exceptions import (
    HTTP_STATUS_TO_ERROR,
    MixpanelCLIError,
    RateLimitError,
)


class BaseClient:
    def __init__(
        self,
        base_url: str,
        auth_header: str,
        timeout: int = DEFAULT_TIMEOUT,
        debug: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.timeout = timeout
        self.debug = debug

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict:
        if self.debug:
            import sys
            masked = response.request.headers.get("authorization", "")
            if masked:
                masked = masked[:10] + "***"
            print(
                f"[DEBUG] {response.request.method} {response.request.url} → {response.status_code}",
                file=sys.stderr,
            )
        if response.status_code in HTTP_STATUS_TO_ERROR:
            exc_cls = HTTP_STATUS_TO_ERROR[response.status_code]
            try:
                detail = response.json().get("error", response.text[:200])
            except Exception:
                detail = response.text[:200]
            raise exc_cls(f"HTTP {response.status_code}: {detail}")
        response.raise_for_status()
        return response.json()

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        backoff = 1
        for attempt in range(4):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params, headers=self._headers())
            if response.status_code == 429 and attempt < 3:
                time.sleep(backoff)
                backoff *= 2
                continue
            return self._handle_response(response)
        raise RateLimitError("Rate limit 초과. 잠시 후 다시 시도하세요.")

    def post(self, path: str, json_data: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        backoff = 1
        for attempt in range(4):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=json_data, headers=self._headers())
            if response.status_code == 429 and attempt < 3:
                time.sleep(backoff)
                backoff *= 2
                continue
            return self._handle_response(response)
        raise RateLimitError("Rate limit 초과. 잠시 후 다시 시도하세요.")

    def patch(self, path: str, json_data: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.patch(url, json=json_data, headers=self._headers())
        return self._handle_response(response)

    def delete(self, path: str) -> dict | None:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(url, headers=self._headers())
        if response.status_code == 204:
            return None
        return self._handle_response(response)

    def stream_get(self, path: str, params: dict | None = None) -> Generator[bytes, None, None]:
        """스트리밍 GET — export에 사용."""
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("GET", url, params=params, headers=self._headers()) as response:
                if response.status_code in HTTP_STATUS_TO_ERROR:
                    exc_cls = HTTP_STATUS_TO_ERROR[response.status_code]
                    raise exc_cls(f"HTTP {response.status_code}")
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    yield chunk
