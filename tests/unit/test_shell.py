"""shell REPL 단위 테스트."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from mixpanel_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def env_auth(monkeypatch):
    monkeypatch.setenv("MIXPANEL_USERNAME", "test@123456.mixpanel.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "test-secret")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "123456")


def test_shell_missing_prompt_toolkit(runner):
    """prompt-toolkit 미설치 시 안내 메시지 출력."""
    with patch.dict("sys.modules", {"prompt_toolkit": None,
                                     "prompt_toolkit.history": None,
                                     "prompt_toolkit.auto_suggest": None,
                                     "prompt_toolkit.completion": None}):
        result = runner.invoke(cli, ["shell", "start"])
    assert result.exit_code == 0
    assert "pip install mixpanel-cli[shell]" in result.output


def test_shell_exit_command(runner):
    """'exit' 입력 시 REPL 종료."""
    mock_session = MagicMock()
    mock_session.prompt.side_effect = ["exit"]

    mock_pt = MagicMock()
    mock_pt.PromptSession.return_value = mock_session
    mock_pt.history.FileHistory = MagicMock()
    mock_pt.auto_suggest.AutoSuggestFromHistory = MagicMock()
    mock_pt.completion.WordCompleter = MagicMock()

    with patch.dict("sys.modules", {
        "prompt_toolkit": mock_pt,
        "prompt_toolkit.history": mock_pt.history,
        "prompt_toolkit.auto_suggest": mock_pt.auto_suggest,
        "prompt_toolkit.completion": mock_pt.completion,
    }):
        result = runner.invoke(cli, ["shell", "start"])
    assert result.exit_code == 0


def test_shell_use_project_command(runner):
    """'use project <id>' 명령 처리."""
    mock_session = MagicMock()
    mock_session.prompt.side_effect = ["use project 999999", "exit"]

    mock_pt = MagicMock()
    mock_pt.PromptSession.return_value = mock_session
    mock_pt.history.FileHistory = MagicMock()
    mock_pt.auto_suggest.AutoSuggestFromHistory = MagicMock()
    mock_pt.completion.WordCompleter = MagicMock()

    with patch.dict("sys.modules", {
        "prompt_toolkit": mock_pt,
        "prompt_toolkit.history": mock_pt.history,
        "prompt_toolkit.auto_suggest": mock_pt.auto_suggest,
        "prompt_toolkit.completion": mock_pt.completion,
    }):
        result = runner.invoke(cli, ["shell", "start"])
    assert result.exit_code == 0
    assert "999999" in result.output
