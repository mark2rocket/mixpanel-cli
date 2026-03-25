"""events 명령 단위 테스트."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from mixpanel_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def env_auth(monkeypatch):
    monkeypatch.setenv("MIXPANEL_USERNAME", "test@123456.mixpanel.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "test-secret")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "123456")


@respx.mock
def test_events_list_ok(runner):
    event_names = ["Sign Up", "Login", "Purchase"]
    respx.get("https://mixpanel.com/api/2.0/events/names").mock(
        return_value=httpx.Response(200, json=event_names)
    )
    result = runner.invoke(cli, ["events", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["data"], list)


@respx.mock
def test_events_list_quiet(runner):
    event_names = ["A", "B", "C"]
    respx.get("https://mixpanel.com/api/2.0/events/names").mock(
        return_value=httpx.Response(200, json=event_names)
    )
    result = runner.invoke(cli, ["--quiet", "events", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert isinstance(parsed, list)


@respx.mock
def test_events_get_ok(runner):
    respx.get("https://mixpanel.com/api/2.0/events/properties").mock(
        return_value=httpx.Response(200, json={"event": "Sign Up", "properties": []})
    )
    result = runner.invoke(cli, ["events", "get", "--name", "Sign Up"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "ok"


@respx.mock
def test_events_properties_ok(runner):
    respx.get("https://mixpanel.com/api/2.0/events/properties").mock(
        return_value=httpx.Response(200, json=[{"name": "$email", "type": "string"}])
    )
    result = runner.invoke(cli, ["events", "properties", "--event", "Sign Up"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "ok"
