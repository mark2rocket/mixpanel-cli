"""Claude API 클라이언트 단위 테스트."""

import json
import pytest
from unittest.mock import MagicMock, patch
from mixpanel_cli.exceptions import AINotInstalledError, RateLimitError


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_ask_mixpanel_returns_structured_dict():
    """ClaudeClient.ask_mixpanel이 올바른 dict 반환."""
    expected = {
        "command": "insight",
        "params": {"event": "Sign Up", "from_date": "2026-03-01", "to_date": "2026-03-26", "unit": "day"},
        "summary_template": "Sign Up occurred {value} times.",
        "explanation": "User asked about sign ups.",
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(expected))]

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        from importlib import reload
        import mixpanel_cli.client.claude as claude_mod
        reload(claude_mod)
        client = claude_mod.ClaudeClient()
        result = client.ask_mixpanel("Sign up 이번 달", ["Sign Up", "Purchase"], "2026-03-26")

    assert result["command"] == "insight"
    assert result["params"]["event"] == "Sign Up"
    assert "summary_template" in result


def test_ask_mixpanel_strips_json_fences():
    """markdown 코드 펜스가 있어도 파싱 성공."""
    payload = {"command": "flow", "params": {"event": "Login", "from_date": "2026-03-01", "to_date": "2026-03-26"}, "summary_template": "", "explanation": ""}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fenced)]

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        from importlib import reload
        import mixpanel_cli.client.claude as claude_mod
        reload(claude_mod)
        client = claude_mod.ClaudeClient()
        result = client.ask_mixpanel("login flow", ["Login"], "2026-03-26")

    assert result["command"] == "flow"


def test_ask_mixpanel_rate_limit_raises():
    """API 429 응답 시 RateLimitError 발생."""
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("rate_limit exceeded 429")

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        from importlib import reload
        import mixpanel_cli.client.claude as claude_mod
        reload(claude_mod)
        client = claude_mod.ClaudeClient()
        with pytest.raises(RateLimitError):
            client.ask_mixpanel("test", [], "2026-03-26")


def test_ai_not_installed_when_no_key(monkeypatch):
    """ANTHROPIC_API_KEY 없으면 AINotInstalledError 발생."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("keyring.get_password", return_value=None):
        from importlib import reload
        import mixpanel_cli.client.claude as claude_mod
        reload(claude_mod)
        with pytest.raises(AINotInstalledError):
            claude_mod.ClaudeClient()


def test_ai_not_installed_when_package_missing(monkeypatch):
    """anthropic 패키지 없으면 AINotInstalledError 발생."""
    with patch.dict("sys.modules", {"anthropic": None}):
        from importlib import reload
        import mixpanel_cli.client.claude as claude_mod
        reload(claude_mod)
        client = claude_mod.ClaudeClient.__new__(claude_mod.ClaudeClient)
        client.model = "test"
        client._api_key = "key"
        with pytest.raises(AINotInstalledError):
            client.ask_mixpanel("test", [], "2026-03-26")
