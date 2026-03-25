"""공통 테스트 픽스처."""

import json
import pytest
import respx
import httpx
from unittest.mock import MagicMock, patch


# ── Auth 픽스처 ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_keyring(monkeypatch):
    """keyring을 항상 mock으로 대체."""
    store = {}

    def fake_set(service, key, secret):
        store[f"{service}/{key}"] = secret

    def fake_get(service, key):
        return store.get(f"{service}/{key}", "test-secret")

    def fake_delete(service, key):
        store.pop(f"{service}/{key}", None)

    monkeypatch.setattr("keyring.set_password", fake_set)
    monkeypatch.setattr("keyring.get_password", fake_get)
    monkeypatch.setattr("keyring.delete_password", fake_delete)
    return store


@pytest.fixture
def mock_profiles_file(tmp_path, monkeypatch):
    """profiles.json을 임시 경로로 대체."""
    profiles_path = tmp_path / "profiles.json"
    monkeypatch.setattr(
        "mixpanel_cli.auth.profile.PROFILES_PATH_DEFAULT",
        str(profiles_path),
    )
    monkeypatch.setattr(
        "mixpanel_cli.constants.PROFILES_PATH_DEFAULT",
        str(profiles_path),
    )
    return profiles_path


@pytest.fixture
def auth_env(monkeypatch):
    """환경변수 인증 설정."""
    monkeypatch.setenv("MIXPANEL_USERNAME", "test@123456.mixpanel.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "test-secret-123")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "123456")
    monkeypatch.setenv("MIXPANEL_REGION", "us")


# ── HTTP 픽스처 ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_mixpanel_api():
    """Mixpanel API (mixpanel.com) mock."""
    with respx.mock(base_url="https://mixpanel.com", assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def mock_mixpanel_data():
    """Mixpanel Data API (data.mixpanel.com) mock."""
    with respx.mock(base_url="https://data.mixpanel.com", assert_all_called=False) as mock:
        yield mock


# ── 샘플 응답 픽스처 ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_insight_response():
    return {
        "data": {
            "series": ["2026-03-01", "2026-03-02"],
            "values": {"Sign Up": {"2026-03-01": 100, "2026-03-02": 120}},
        },
        "legend_size": 1,
    }


@pytest.fixture
def sample_event_names():
    return ["Sign Up", "Login", "Purchase", "View Item", "Add to Cart"]


@pytest.fixture
def sample_projects():
    return [{"id": "123456", "name": "My App", "token": "abc123"}]
