"""models.py 단위 테스트."""

import pytest
from mixpanel_cli.models import CLIResponse, Profile, AskResponse


def test_cli_response_ok():
    r = CLIResponse.ok(data={"count": 42})
    assert r.status == "ok"
    assert r.data == {"count": 42}
    assert r.code is None


def test_cli_response_error():
    r = CLIResponse.error("AUTH_ERROR", "인증 실패")
    assert r.status == "error"
    assert r.code == "AUTH_ERROR"
    assert r.message == "인증 실패"
    assert r.data is None


def test_profile_defaults():
    p = Profile(name="test", service_account_username="u", project_id="123")
    assert p.region == "us"


def test_profile_region_validation():
    with pytest.raises(Exception):
        Profile(name="test", service_account_username="u", project_id="123", region="invalid")


def test_ask_response_inherits():
    r = AskResponse(status="ok", data={"count": 1}, summary="총 1건")
    assert r.summary == "총 1건"
    assert r.status == "ok"
