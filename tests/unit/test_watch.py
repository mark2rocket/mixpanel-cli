"""watch 명령 단위 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from mixpanel_cli.commands.watch import _sum_insight, _check_thresholds


def test_sum_insight_normal():
    data = {"data": {"values": {"Sign Up": {"2026-03-01": 100, "2026-03-02": 200}}}}
    assert _sum_insight(data) == 300.0


def test_sum_insight_empty():
    assert _sum_insight({}) == 0.0


def test_check_thresholds_drop_triggers(capsys):
    """하락 임계값 초과 시 stderr 출력."""
    _check_thresholds("Sign Up", 80, -25.0, 20.0, None, None)
    captured = capsys.readouterr()
    assert "[ALERT]" in captured.err
    assert "하락" in captured.err


def test_check_thresholds_rise_triggers(capsys):
    """상승 임계값 초과 시 stderr 출력."""
    _check_thresholds("Sign Up", 150, 60.0, None, 50.0, None)
    captured = capsys.readouterr()
    assert "[ALERT]" in captured.err
    assert "상승" in captured.err


def test_check_thresholds_no_alert(capsys):
    """임계값 미초과 시 출력 없음."""
    _check_thresholds("Sign Up", 100, -5.0, 20.0, 50.0, None)
    captured = capsys.readouterr()
    assert "[ALERT]" not in captured.err


def test_check_thresholds_webhook(capsys):
    """webhook URL이 있으면 POST 전송."""
    with patch("mixpanel_cli.commands.watch.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        _check_thresholds("Sign Up", 80, -30.0, 20.0, None, "https://example.com/webhook")
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["type"] == "drop"
        assert payload["event"] == "Sign Up"
