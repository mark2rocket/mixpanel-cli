"""config 명령 단위 테스트."""

import json
import pytest
from click.testing import CliRunner
from mixpanel_cli.main import cli


def _parse_json_output(output: str) -> dict:
    """stdout에서 마지막 JSON 라인 파싱 (prompt 텍스트 제외)."""
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    return json.loads(output.strip())


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_profile_path(tmp_path, monkeypatch):
    path = tmp_path / "profiles.json"
    monkeypatch.setattr("mixpanel_cli.auth.profile._profiles_path", lambda: path)
    return path


def test_config_init(runner, temp_profile_path):
    result = runner.invoke(cli, ["config", "init"], input="user@123.mixpanel.com\nsecret123\n123456\nus\n")
    assert result.exit_code == 0, result.output
    parsed = _parse_json_output(result.output)
    assert parsed["status"] == "ok"
    assert parsed["data"]["project_id"] == "123456"


def test_config_list_empty(runner, temp_profile_path):
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["data"], list)


def test_config_list_with_profile(runner, temp_profile_path):
    # 먼저 프로파일 생성
    runner.invoke(cli, ["config", "init"], input="u@1.mixpanel.com\nsecret\n111\nus\n")
    result = runner.invoke(cli, ["config", "list"])
    parsed = json.loads(result.output)
    assert len(parsed["data"]) >= 1


def test_config_show(runner, temp_profile_path):
    runner.invoke(cli, ["config", "init"], input="u@1.mixpanel.com\nsecret\n222\nus\n")
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"


def test_config_set_region(runner, temp_profile_path):
    runner.invoke(cli, ["config", "init"], input="u@1.mixpanel.com\nsecret\n333\nus\n")
    result = runner.invoke(cli, ["config", "set", "--key", "region", "--value", "eu"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "ok"
    assert parsed["data"]["value"] == "eu"


def test_config_delete(runner, temp_profile_path):
    runner.invoke(cli, ["config", "init", "--profile", "todelete"],
                  input="u@1.mixpanel.com\nsecret\n444\nus\n")
    result = runner.invoke(cli, ["config", "delete", "--profile", "todelete"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["data"]["deleted"] == "todelete"
