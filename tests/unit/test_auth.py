"""auth 레이어 단위 테스트."""

import json
import os
import pytest
from mixpanel_cli.auth.profile import (
    AuthContext,
    save_profile,
    get_profile,
    list_profiles,
    delete_profile,
    update_profile_field,
)
from mixpanel_cli.auth.keychain import set_secret, get_secret
from mixpanel_cli.exceptions import AuthError, ProfileNotFoundError
from mixpanel_cli.models import Profile


@pytest.fixture
def temp_profiles(tmp_path, monkeypatch):
    profiles_path = tmp_path / "profiles.json"
    monkeypatch.setattr("mixpanel_cli.auth.profile._profiles_path", lambda: profiles_path)
    return profiles_path


def test_save_and_get_profile(temp_profiles):
    p = Profile(name="test", service_account_username="u@123.mixpanel.com", project_id="123", region="us")
    save_profile(p)
    loaded = get_profile("test")
    assert loaded.name == "test"
    assert loaded.project_id == "123"


def test_list_profiles(temp_profiles):
    p1 = Profile(name="prod", service_account_username="u1", project_id="111")
    p2 = Profile(name="staging", service_account_username="u2", project_id="222")
    save_profile(p1)
    save_profile(p2)
    profiles = list_profiles()
    names = [p["name"] for p in profiles]
    assert "prod" in names
    assert "staging" in names


def test_get_profile_not_found(temp_profiles):
    with pytest.raises(ProfileNotFoundError):
        get_profile("nonexistent")


def test_delete_profile(temp_profiles):
    p = Profile(name="to-delete", service_account_username="u", project_id="999")
    save_profile(p)
    delete_profile("to-delete")
    with pytest.raises(ProfileNotFoundError):
        get_profile("to-delete")


def test_update_profile_field(temp_profiles):
    p = Profile(name="mypro", service_account_username="u", project_id="000", region="us")
    save_profile(p)
    update_profile_field("mypro", "region", "eu")
    loaded = get_profile("mypro")
    assert loaded.region == "eu"


def test_auth_context_env(monkeypatch, temp_profiles):
    monkeypatch.setenv("MIXPANEL_USERNAME", "env-user")
    monkeypatch.setenv("MIXPANEL_SECRET", "env-secret")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "env-pid")
    auth = AuthContext()
    assert auth.username == "env-user"
    assert auth.secret == "env-secret"
    assert auth.project_id == "env-pid"


def test_auth_context_no_creds_raises(monkeypatch, temp_profiles):
    monkeypatch.delenv("MIXPANEL_USERNAME", raising=False)
    monkeypatch.delenv("MIXPANEL_SECRET", raising=False)
    monkeypatch.delenv("MIXPANEL_PROJECT_ID", raising=False)
    with pytest.raises(AuthError):
        AuthContext()


def test_keychain_set_get(mock_keyring):
    set_secret("my-profile", "super-secret")
    result = get_secret("my-profile")
    assert result == "super-secret"


def test_keyring_runtime_error(monkeypatch):
    def fake_get(service, key):
        raise RuntimeError("no backend")
    monkeypatch.setattr("keyring.get_password", fake_get)
    with pytest.raises(AuthError) as exc_info:
        get_secret("any")
    assert "MIXPANEL_SECRET" in str(exc_info.value)
