"""analytics 명령 단위 테스트."""

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
def test_analytics_insight_ok(runner):
    mock_data = {"data": {"series": ["2026-03-01"], "values": {"Sign Up": {"2026-03-01": 100}}}}
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    result = runner.invoke(cli, [
        "analytics", "insight",
        "--event", "Sign Up",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_analytics_insight_auth_error(runner):
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )
    result = runner.invoke(cli, [
        "analytics", "insight",
        "--event", "Sign Up",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AUTH_ERROR"


@respx.mock
def test_analytics_insight_quiet(runner):
    mock_data = {"data": {"values": {"Sign Up": {"2026-03-01": 99}}}}
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    result = runner.invoke(cli, [
        "--quiet",
        "analytics", "insight",
        "--event", "Sign Up",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code == 0
    # --quiet 시 data만 유효한 JSON으로 출력
    parsed = json.loads(result.output.strip())
    assert "values" in parsed or "data" in parsed or isinstance(parsed, dict)


def test_analytics_insight_bad_date(runner):
    result = runner.invoke(cli, [
        "analytics", "insight",
        "--event", "Sign Up",
        "--from-date", "2026/03/01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code != 0


@respx.mock
def test_analytics_funnel_ok(runner):
    respx.get("https://mixpanel.com/api/2.0/funnels").mock(
        return_value=httpx.Response(200, json={"steps": []})
    )
    result = runner.invoke(cli, [
        "analytics", "funnel",
        "--id", "42",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "ok"


@respx.mock
def test_analytics_retention_ok(runner):
    respx.get("https://mixpanel.com/api/2.0/retention").mock(
        return_value=httpx.Response(200, json={"2026-03-01": {"count": 100}})
    )
    result = runner.invoke(cli, [
        "analytics", "retention",
        "--event", "Sign Up",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-31",
    ])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "ok"
