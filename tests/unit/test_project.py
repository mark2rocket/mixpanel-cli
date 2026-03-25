"""project 명령 단위 테스트."""

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
def test_project_list_ok(runner):
    projects = [{"id": "123456", "name": "My App"}]
    respx.get("https://mixpanel.com/api/2.0/projects").mock(
        return_value=httpx.Response(200, json=projects)
    )
    result = runner.invoke(cli, ["project", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["data"], list)


@respx.mock
def test_project_info_ok(runner):
    projects = [{"id": "123456", "name": "My App", "token": "abc"}]
    respx.get("https://mixpanel.com/api/2.0/projects").mock(
        return_value=httpx.Response(200, json=projects)
    )
    result = runner.invoke(cli, ["project", "info"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_project_list_quiet(runner):
    projects = [{"id": "123456", "name": "My App"}]
    respx.get("https://mixpanel.com/api/2.0/projects").mock(
        return_value=httpx.Response(200, json=projects)
    )
    result = runner.invoke(cli, ["--quiet", "project", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert isinstance(parsed, list)


@respx.mock
def test_project_auth_error(runner):
    respx.get("https://mixpanel.com/api/2.0/projects").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    result = runner.invoke(cli, ["project", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AUTH_ERROR"
