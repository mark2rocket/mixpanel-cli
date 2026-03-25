"""dashboard 명령 단위 테스트."""

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
def test_dashboard_list_ok(runner):
    dashboards = [{"id": "d1", "title": "KPI Board"}]
    respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks").mock(
        return_value=httpx.Response(200, json=dashboards)
    )
    result = runner.invoke(cli, ["dashboard", "list"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["data"], list)


@respx.mock
def test_dashboard_get_ok(runner):
    dashboard = {"id": "d1", "title": "KPI Board", "items": []}
    respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks/d1").mock(
        return_value=httpx.Response(200, json=dashboard)
    )
    result = runner.invoke(cli, ["dashboard", "get", "--id", "d1"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"
    assert parsed["data"]["id"] == "d1"


@respx.mock
def test_dashboard_create_ok(runner):
    created = {"id": "d2", "title": "New Board"}
    respx.post("https://mixpanel.com/api/app/projects/123456/bookmarks").mock(
        return_value=httpx.Response(201, json=created)
    )
    result = runner.invoke(cli, ["dashboard", "create", "--title", "New Board"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_dashboard_delete_ok(runner):
    respx.delete("https://mixpanel.com/api/app/projects/123456/bookmarks/d1").mock(
        return_value=httpx.Response(204)
    )
    result = runner.invoke(cli, ["dashboard", "delete", "--id", "d1"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"
    assert parsed["data"]["deleted"] == "d1"


@respx.mock
def test_dashboard_auth_error(runner):
    respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    result = runner.invoke(cli, ["dashboard", "list"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AUTH_ERROR"
