"""Mixpanel OAuth 2.0 PKCE 플로우."""

import hashlib
import http.server
import json
import os
import secrets
import socket
import threading
import webbrowser
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from mixpanel_cli.constants import MIXPANEL_DOMAIN_BY_REGION
from mixpanel_cli.models import OAuthToken

_DEFAULT_SCOPES = (
    "projects analysis events insights segmentation retention "
    "data:read funnels flows data_definitions dashboard_reports bookmarks"
)
_CLIENT_CACHE_DIR = Path(os.path.expanduser("~/.mixpanel"))


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def generate_pkce() -> tuple[str, str]:
    """(code_verifier, code_challenge) 생성.

    code_verifier: 64바이트 URL-safe base64 (86자, padding 제거)
    code_challenge: BASE64URL(SHA256(ASCII(code_verifier)))
    """
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# Dynamic Client Registration
# ---------------------------------------------------------------------------

def _client_cache_path(region: str) -> Path:
    return _CLIENT_CACHE_DIR / f"oauth_client_{region}.json"


def register_client(redirect_uri: str, region: str = "us") -> str:
    """동적 클라이언트 등록 → client_id 반환.

    redirect_uri별로 캐시 — 동일 URI면 재등록 없이 반환.
    """
    cache_path = _client_cache_path(region)
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            if data.get("redirect_uri") == redirect_uri and "client_id" in data:
                return data["client_id"]
        except Exception:
            pass

    domain = MIXPANEL_DOMAIN_BY_REGION.get(region, "mixpanel.com")
    url = f"https://{domain}/oauth/mcp/register/"
    payload = {
        "client_name": "mixpanel-cli",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "redirect_uris": [redirect_uri],
    }

    response = httpx.post(url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    client_id = data["client_id"]

    _CLIENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"client_id": client_id, "redirect_uri": redirect_uri}))
    cache_path.chmod(0o600)
    return client_id


# ---------------------------------------------------------------------------
# Local callback server
# ---------------------------------------------------------------------------

def find_free_port(start: int = 7777) -> int:
    """start 포트부터 순서대로 사용 가능한 포트 반환."""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("사용 가능한 포트를 찾을 수 없습니다 (7777-7796).")


def start_callback_server(port: int) -> dict:
    """로컬 HTTP 서버로 OAuth 콜백 수신 → {code, state} 반환."""
    result: dict = {}
    server_ready = threading.Event()
    server_done = threading.Event()

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            result["code"] = params.get("code", [""])[0]
            result["state"] = params.get("state", [""])[0]
            result["error"] = params.get("error", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if result.get("error"):
                body = f"<h2>로그인 실패: {result['error']}</h2><p>이 창을 닫아주세요.</p>"
            else:
                body = "<h2>로그인 성공!</h2><p>이 창을 닫고 터미널로 돌아오세요.</p>"
            self.wfile.write(body.encode())
            server_done.set()

        def log_message(self, *args):  # noqa: D102
            pass  # 서버 로그 억제

    httpd = http.server.HTTPServer(("127.0.0.1", port), _Handler)

    def _serve():
        server_ready.set()
        httpd.handle_request()  # 1회 요청만 처리

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    server_ready.wait(timeout=3)
    server_done.wait(timeout=120)  # 2분 타임아웃
    httpd.server_close()

    if result.get("error"):
        from mixpanel_cli.exceptions import AuthError
        raise AuthError(f"OAuth 인증 실패: {result['error']}")
    if not result.get("code"):
        from mixpanel_cli.exceptions import AuthError
        raise AuthError("OAuth 콜백에서 코드를 받지 못했습니다.")
    return result


# ---------------------------------------------------------------------------
# Token exchange & refresh
# ---------------------------------------------------------------------------

def exchange_code(
    code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
    region: str = "us",
) -> OAuthToken:
    """Authorization code → OAuthToken."""
    domain = MIXPANEL_DOMAIN_BY_REGION.get(region, "mixpanel.com")
    url = f"https://{domain}/oauth/token/"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    response = httpx.post(url, data=data, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return _parse_token_response(payload, client_id, region)


def refresh_token_request(
    token: OAuthToken,
    client_id: str,
    region: str = "us",
) -> OAuthToken:
    """refresh_token으로 새 OAuthToken 발급."""
    domain = MIXPANEL_DOMAIN_BY_REGION.get(region, "mixpanel.com")
    url = f"https://{domain}/oauth/token/"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
        "client_id": client_id,
    }
    response = httpx.post(url, data=data, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return _parse_token_response(payload, client_id, region)


def _parse_token_response(payload: dict, client_id: str, region: str = "us") -> OAuthToken:
    expires_in = payload.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return OAuthToken(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token", ""),
        expires_at=expires_at,
        scope=payload.get("scope", _DEFAULT_SCOPES),
        client_id=client_id,
        region=region,
    )


# ---------------------------------------------------------------------------
# Full login flow
# ---------------------------------------------------------------------------

def run_login_flow(region: str = "us", scopes: str = _DEFAULT_SCOPES) -> OAuthToken:
    """브라우저 기반 PKCE 로그인 플로우 실행 → OAuthToken 반환."""
    port = find_free_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    client_id = register_client(redirect_uri=redirect_uri, region=region)
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(16)

    domain = MIXPANEL_DOMAIN_BY_REGION.get(region, "mixpanel.com")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://{domain}/oauth/authorize?" + urlencode(params)

    import click
    click.echo(f"브라우저에서 Mixpanel 로그인 페이지를 엽니다...")
    click.echo(f"자동으로 열리지 않으면 아래 URL을 복사해서 브라우저에 붙여넣으세요:\n{auth_url}")

    opened = webbrowser.open(auth_url)
    if not opened:
        click.echo(f"\n위 URL을 브라우저에서 열고 로그인 후 돌아오세요.")

    click.echo(f"로컬 포트 {port}에서 콜백 대기 중...")
    callback_result = start_callback_server(port)

    if callback_result.get("state") != state:
        from mixpanel_cli.exceptions import AuthError
        raise AuthError("OAuth state 불일치 — CSRF 공격 가능성")

    return exchange_code(
        code=callback_result["code"],
        code_verifier=code_verifier,
        client_id=client_id,
        redirect_uri=redirect_uri,
        region=region,
    )
