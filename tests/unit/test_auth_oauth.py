"""OAuth 인증 단위 테스트."""

import hashlib
import json
import tempfile
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from mixpanel_cli.auth.oauth import generate_pkce, find_free_port
from mixpanel_cli.models import OAuthToken


# ---------------------------------------------------------------------------
# PKCE 테스트
# ---------------------------------------------------------------------------

def test_generate_pkce_lengths():
    verifier, challenge = generate_pkce()
    # verifier: 64바이트 → urlsafe_b64encode → 86자 (padding 제거)
    assert 43 <= len(verifier) <= 128
    assert len(challenge) > 0
    assert verifier != challenge


def test_generate_pkce_challenge_is_sha256():
    verifier, challenge = generate_pkce()
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
    assert challenge == expected_challenge


def test_generate_pkce_unique():
    v1, c1 = generate_pkce()
    v2, c2 = generate_pkce()
    assert v1 != v2
    assert c1 != c2


# ---------------------------------------------------------------------------
# 동적 클라이언트 등록 테스트
# ---------------------------------------------------------------------------

@respx.mock
def test_register_client_fresh(tmp_path, monkeypatch):
    """캐시 없을 때 API 호출해서 client_id 반환."""
    monkeypatch.setattr(
        "mixpanel_cli.auth.oauth._CLIENT_CACHE_DIR", tmp_path
    )

    respx.post("https://mixpanel.com/oauth/mcp/register/").mock(
        return_value=Response(200, json={"client_id": "test-client-123"})
    )

    from mixpanel_cli.auth.oauth import register_client
    client_id = register_client(redirect_uri="http://127.0.0.1:7777/callback", region="us")
    assert client_id == "test-client-123"

    # 캐시 파일 생성 확인
    cache_file = tmp_path / "oauth_client_us.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text())["client_id"] == "test-client-123"


def test_register_client_cached(tmp_path, monkeypatch):
    """캐시 있을 때 API 호출 없이 반환."""
    monkeypatch.setattr(
        "mixpanel_cli.auth.oauth._CLIENT_CACHE_DIR", tmp_path
    )

    cache_file = tmp_path / "oauth_client_us.json"
    cache_file.write_text(json.dumps({"client_id": "cached-client-456", "redirect_uri": "http://127.0.0.1:7777/callback"}))

    from mixpanel_cli.auth.oauth import register_client
    with respx.mock:
        # API 호출이 없어야 함 (mock에 route 없으므로 호출 시 에러)
        client_id = register_client(redirect_uri="http://127.0.0.1:7777/callback", region="us")

    assert client_id == "cached-client-456"


# ---------------------------------------------------------------------------
# OAuthToken 테스트
# ---------------------------------------------------------------------------

def test_oauth_token_not_expired():
    token = OAuthToken(
        access_token="tok",
        refresh_token="ref",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scope="projects",
        client_id="client-1",
    )
    assert not token.is_expired()


def test_oauth_token_expired():
    token = OAuthToken(
        access_token="tok",
        refresh_token="ref",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        scope="projects",
        client_id="client-1",
    )
    assert token.is_expired()


def test_oauth_token_expires_within_5_min():
    """5분 이내 만료 예정도 만료로 간주."""
    token = OAuthToken(
        access_token="tok",
        refresh_token="ref",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=3),
        scope="projects",
        client_id="client-1",
    )
    assert token.is_expired()


# ---------------------------------------------------------------------------
# AuthContext OAuth 우선순위 테스트
# ---------------------------------------------------------------------------

def _make_valid_token() -> OAuthToken:
    return OAuthToken(
        access_token="oauth-access-token",
        refresh_token="oauth-refresh-token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scope="projects analysis",
        client_id="client-id",
        region="us",
    )


def test_auth_context_oauth_bearer_header(monkeypatch):
    """OAuth 토큰 있을 때 Bearer 헤더 반환."""
    token = _make_valid_token()

    monkeypatch.setattr(
        "mixpanel_cli.auth.keychain.get_oauth_token",
        lambda profile_name: token,
    )
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "3497776")

    from mixpanel_cli.auth.profile import AuthContext
    ctx = AuthContext(profile_name="default")

    assert ctx.use_oauth is True
    assert ctx.auth_header == f"Bearer {token.access_token}"


def test_auth_context_service_account_fallback(monkeypatch):
    """OAuth 토큰 없을 때 Basic 헤더 반환."""
    monkeypatch.setattr(
        "mixpanel_cli.auth.keychain.get_oauth_token",
        lambda profile_name: None,
    )

    monkeypatch.setenv("MIXPANEL_USERNAME", "user@example.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "secret123")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "12345")

    from mixpanel_cli.auth.profile import AuthContext
    ctx = AuthContext(profile_name="default")

    assert ctx.use_oauth is False
    assert ctx.auth_header.startswith("Basic ")


# ---------------------------------------------------------------------------
# find_free_port 테스트
# ---------------------------------------------------------------------------

def test_find_free_port():
    port = find_free_port(start=8888)
    assert 8888 <= port <= 8908
