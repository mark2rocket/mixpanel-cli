"""formatter.py 단위 테스트."""

import json
import pytest
from click.testing import CliRunner
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error


def _capture(fn, *args, **kwargs) -> str:
    """stdout 캡처 헬퍼."""
    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def test_print_response_json():
    r = CLIResponse.ok(data={"count": 42})
    out = _capture(print_response, r)
    parsed = json.loads(out)
    assert parsed["status"] == "ok"
    assert parsed["data"]["count"] == 42


def test_print_response_quiet():
    r = CLIResponse.ok(data={"count": 42})
    out = _capture(print_response, r, quiet=True)
    parsed = json.loads(out.strip())
    assert parsed == {"count": 42}


def test_print_response_quiet_list():
    r = CLIResponse.ok(data=["a", "b", "c"])
    out = _capture(print_response, r, quiet=True)
    parsed = json.loads(out.strip())
    assert parsed == ["a", "b", "c"]


def test_print_response_pretty():
    r = CLIResponse.ok(data={"k": "v"})
    out = _capture(print_response, r, pretty=True)
    assert "\n" in out  # indented


def test_print_response_error_to_stdout():
    r = CLIResponse.error("AUTH_ERROR", "인증 실패")
    out = _capture(print_response, r)
    parsed = json.loads(out)
    assert parsed["status"] == "error"
    assert parsed["code"] == "AUTH_ERROR"


def test_print_error():
    out = _capture(print_error, "QUERY_ERROR", "잘못된 쿼리")
    parsed = json.loads(out)
    assert parsed["status"] == "error"
    assert parsed["code"] == "QUERY_ERROR"


def test_print_response_csv():
    r = CLIResponse.ok(data=[{"name": "Sign Up", "count": 100}])
    out = _capture(print_response, r, fmt="csv")
    assert "name" in out
    assert "Sign Up" in out
