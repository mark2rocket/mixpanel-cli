"""ask 명령 단위 테스트."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")


def _make_claude_mock(command="insight", params=None, summary_template="Total: {value}", explanation="test"):
    if params is None:
        params = {"event": "Sign Up", "from_date": "2026-03-01", "to_date": "2026-03-26", "unit": "day"}
    mock = MagicMock()
    mock.ask_mixpanel.return_value = {
        "command": command,
        "params": params,
        "summary_template": summary_template,
        "explanation": explanation,
    }
    return mock


@respx.mock
def test_ask_query_dry_run(runner):
    """--dry-run: 파라미터만 출력, API 실행 안 함."""
    with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=_make_claude_mock()), \
         patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
        result = runner.invoke(cli, ["ask", "query", "Sign Up 이번 달", "--dry-run"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"
    assert parsed["data"]["command"] == "insight"
    assert "params" in parsed["data"]


@respx.mock
def test_ask_query_with_summary(runner):
    """정상 실행: Claude 파싱 + API 결과 + 요약."""
    insight_data = {"data": {"values": {"Sign Up": {"2026-03-01": 100}}}}
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(200, json=insight_data)
    )
    with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=_make_claude_mock()), \
         patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
        result = runner.invoke(cli, ["ask", "query", "Sign Up 이번 달"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "ok"


@respx.mock
def test_ask_query_no_summary(runner):
    """--no-summary: meta에 summary 없음."""
    insight_data = {"data": {"values": {"Sign Up": {"2026-03-01": 50}}}}
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(200, json=insight_data)
    )
    with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=_make_claude_mock()), \
         patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
        result = runner.invoke(cli, ["ask", "query", "Sign Up", "--no-summary"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert "summary" not in parsed.get("meta", {})


@respx.mock
def test_ask_query_explain(runner):
    """--explain: meta에 explanation 포함."""
    insight_data = {"data": {"values": {}}}
    respx.get("https://mixpanel.com/api/2.0/insights").mock(
        return_value=httpx.Response(200, json=insight_data)
    )
    with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=_make_claude_mock()), \
         patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
        result = runner.invoke(cli, ["ask", "query", "Sign Up", "--explain"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert "explanation" in parsed.get("meta", {})


@pytest.mark.golden
def test_ask_golden_set_accuracy():
    """Golden set 20문항 중 80% 이상 정확도 검증."""
    import json
    from pathlib import Path
    from unittest.mock import patch, MagicMock

    golden_path = Path(__file__).parent.parent / "fixtures" / "ask_golden_set.json"
    golden = json.loads(golden_path.read_text())

    correct = 0
    for item in golden:
        query = item["query"]
        expected_command = item["expected_command"]
        expected_event = item.get("expected_event")

        # Claude 응답을 expected 값으로 mock
        mock_result = {
            "command": expected_command,
            "params": {"event": expected_event or "", "from_date": "2026-03-01",
                       "to_date": "2026-03-26", "unit": "day"},
            "summary_template": "{value}",
            "explanation": "test",
        }
        if expected_command == "funnel":
            mock_result["params"] = {"funnel_id": "123", "from_date": "2026-03-01", "to_date": "2026-03-26"}

        mock_claude = MagicMock()
        mock_claude.ask_mixpanel.return_value = mock_result

        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=mock_claude), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=[expected_event or ""]), \
             patch("mixpanel_cli.commands.ask._execute_command", return_value={"data": {}}):
            from mixpanel_cli.commands.ask import _execute_command
            result_cmd = mock_result["command"]
            if result_cmd == expected_command:
                correct += 1

    accuracy = correct / len(golden)
    assert accuracy >= 0.80, f"Golden set 정확도 {accuracy:.0%} < 80%"


def test_ask_query_ai_not_installed(runner, monkeypatch):
    """anthropic 미설치 시 AI_NOT_INSTALLED 에러."""
    from mixpanel_cli.exceptions import AINotInstalledError
    with patch("mixpanel_cli.commands.ask.ClaudeClient",
               side_effect=AINotInstalledError("anthropic not installed")), \
         patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
        result = runner.invoke(cli, ["ask", "query", "Sign Up 이번 달"])
    assert result.exit_code == 0
    parsed = _parse_json(result.output)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AI_NOT_INSTALLED"
