"""export 명령 단위 테스트."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from mixpanel_cli.main import cli
from mixpanel_cli.client.mixpanel import MixpanelClient


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def env_auth(monkeypatch):
    monkeypatch.setenv("MIXPANEL_USERNAME", "test@123456.mixpanel.com")
    monkeypatch.setenv("MIXPANEL_SECRET", "test-secret")
    monkeypatch.setenv("MIXPANEL_PROJECT_ID", "123456")


@respx.mock
def test_export_events_to_file(runner, tmp_path):
    jsonl_data = b'{"event": "Sign Up", "time": 1000}\n{"event": "Sign Up", "time": 1001}\n'
    respx.get("https://data.mixpanel.com/api/2.0/export").mock(
        return_value=httpx.Response(200, content=jsonl_data)
    )
    output_file = tmp_path / "events.jsonl"
    result = runner.invoke(cli, [
        "export", "events",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-30",
        "--file", str(output_file),
    ])
    assert result.exit_code == 0
    assert output_file.exists()
    content = output_file.read_bytes()
    assert b"Sign Up" in content


@respx.mock
def test_export_events_stdout(runner):
    jsonl_data = b'{"event": "Purchase", "time": 2000}\n'
    respx.get("https://data.mixpanel.com/api/2.0/export").mock(
        return_value=httpx.Response(200, content=jsonl_data)
    )
    result = runner.invoke(cli, [
        "export", "events",
        "--from-date", "2026-03-01",
        "--to-date", "2026-03-30",
    ])
    assert result.exit_code == 0


def test_export_chunking():
    """30일 초과 시 청킹 검증."""
    from mixpanel_cli.client.mixpanel import MixpanelClient
    from unittest.mock import patch, MagicMock

    client = MixpanelClient(
        auth_header="Basic dXNlcjpzZWNyZXQ=",
        project_id="123456",
        region="us",
    )
    chunks_called = []

    def fake_stream_get(path, params=None):
        chunks_called.append(params.get("from_date"))
        yield b'{"event": "x"}\n'

    with patch.object(client._data, "stream_get", side_effect=fake_stream_get):
        list(client.export_events("2026-01-01", "2026-03-31"))

    # 31 + 28 + 31 = 90일 → 3개 청크
    assert len(chunks_called) == 3
    assert chunks_called[0] == "2026-01-01"
    assert chunks_called[1] == "2026-01-31"
    assert chunks_called[2] == "2026-03-02"
