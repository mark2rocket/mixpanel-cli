"""lexicon 명령 단위 테스트."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from mixpanel_cli.main import cli


def _parse_json(output: str) -> dict:
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    return json.loads(output.strip())


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def env_auth(monkeypatch):
    monkeypatch.setenv("MIXPANEL_USERNAME", "test@123456.mixpanel.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "test-secret")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "123456")


@respx.mock
def test_lexicon_list_ok(runner):
    events = [{"name": "Sign Up", "description": "사용자 가입", "status": "active"}]
    respx.get("https://mixpanel.com/api/app/projects/123456/schemas/events").mock(
        return_value=httpx.Response(200, json=events)
    )
    result = runner.invoke(cli, ["lexicon", "list"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["data"], list)


@respx.mock
def test_lexicon_edit_event_ok(runner):
    updated = {"name": "Sign Up", "description": "신규 설명", "status": "active"}
    respx.patch("https://mixpanel.com/api/app/projects/123456/schemas/events/Sign Up").mock(
        return_value=httpx.Response(200, json=updated)
    )
    result = runner.invoke(cli, [
        "lexicon", "edit-event",
        "--event", "Sign Up",
        "--description", "신규 설명",
    ])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_lexicon_edit_property_ok(runner):
    updated = {"name": "email", "description": "이메일 주소"}
    respx.patch(
        "https://mixpanel.com/api/app/projects/123456/schemas/events/Sign Up/properties/email"
    ).mock(return_value=httpx.Response(200, json=updated))
    result = runner.invoke(cli, [
        "lexicon", "edit-property",
        "--event", "Sign Up",
        "--property", "email",
        "--description", "이메일 주소",
    ])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_lexicon_list_auth_error(runner):
    respx.get("https://mixpanel.com/api/app/projects/123456/schemas/events").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    result = runner.invoke(cli, ["lexicon", "list"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AUTH_ERROR"
