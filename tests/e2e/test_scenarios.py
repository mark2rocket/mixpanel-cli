"""CLI 시나리오 테스트 — 실제 사용자 워크플로우를 end-to-end로 검증."""

import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from mixpanel_cli.main import cli


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def parse_last_json(output: str) -> dict:
    """stdout의 마지막 JSON 라인 파싱 (WARNING 등 비JSON 라인 무시)."""
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


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 1: 분석 워크플로우 (insight → funnel → retention)
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyticsWorkflow:
    """시나리오: 데이터 분석팀이 Sign Up 이벤트를 다각도로 분석한다."""

    @respx.mock
    def test_full_analysis_pipeline(self, runner):
        """insight → funnel → retention 순차 분석."""
        insight_data = {
            "data": {"series": ["2026-03-01"], "values": {"Sign Up": {"2026-03-01": 500}}},
            "legend_size": 1,
        }
        funnel_data = {
            "data": {
                "meta": {"dates": ["2026-03-01"]},
                "steps": [
                    {"count": 500, "goal": "Sign Up"},
                    {"count": 300, "goal": "Purchase"},
                ],
            }
        }
        retention_data = {
            "data": {"2026-03-01": {"counts": [500, 200, 150], "percentages": [100, 40, 30]}}
        }

        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json=insight_data)
        )
        respx.get("https://mixpanel.com/api/2.0/funnels").mock(
            return_value=httpx.Response(200, json=funnel_data)
        )
        respx.get("https://mixpanel.com/api/2.0/retention").mock(
            return_value=httpx.Response(200, json=retention_data)
        )

        # 1단계: insight
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"
        assert "values" in d["data"]["data"]

        # 2단계: funnel (--quiet로 파이프라인 시뮬레이션)
        r = runner.invoke(cli, [
            "--quiet",
            "analytics", "funnel",
            "--id", "99999",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert "steps" in d["data"]

        # 3단계: retention
        r = runner.invoke(cli, [
            "analytics", "retention",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
            "--unit", "week",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    @respx.mock
    def test_quiet_flag_returns_pure_data(self, runner):
        """--quiet는 data 값만 반환해야 한다 (파이프라인 파싱용)."""
        insight_data = {
            "data": {"series": [], "values": {"Login": {"2026-03-01": 99}}},
            "legend_size": 1,
        }
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json=insight_data)
        )
        r = runner.invoke(cli, [
            "--quiet",
            "analytics", "insight",
            "--event", "Login",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        # --quiet: status/meta 없이 data 값만
        assert "status" not in d
        assert "values" in d.get("data", d)

    @respx.mock
    def test_region_override(self, runner):
        """--region eu 시 EU 엔드포인트 사용."""
        respx.get("https://eu.mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": [], "values": {}}, "legend_size": 0
            })
        )
        r = runner.invoke(cli, [
            "--region", "eu",
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 2: 이벤트 탐색 및 Export 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

class TestEventExploreAndExport:
    """시나리오: 새 팀원이 어떤 이벤트가 있는지 탐색하고 raw 데이터를 추출한다."""

    @respx.mock
    def test_discover_events_then_export(self, runner, tmp_path):
        """이벤트 목록 → properties → export 파일 저장."""
        events_resp = {
            "results": ["Purchase", "Sign Up", "Login"],
        }
        props_resp = {
            "results": [
                {"name": "$browser", "count": 1000},
                {"name": "amount", "count": 500},
            ]
        }
        export_lines = (
            '{"event":"Purchase","properties":{"amount":29.99}}\n'
            '{"event":"Purchase","properties":{"amount":49.99}}\n'
        )

        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json=events_resp)
        )
        respx.get("https://mixpanel.com/api/2.0/events/properties").mock(
            return_value=httpx.Response(200, json=props_resp)
        )
        respx.get("https://data.mixpanel.com/api/2.0/export").mock(
            return_value=httpx.Response(200, text=export_lines)
        )

        # 1단계: 이벤트 목록
        r = runner.invoke(cli, ["--quiet", "events", "list"])
        assert r.exit_code == 0
        events = parse_last_json(r.output)
        assert "Purchase" in events

        # 2단계: 특정 이벤트의 properties 확인
        r = runner.invoke(cli, ["events", "properties", "--event", "Purchase"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

        # 3단계: raw 데이터 파일로 export (30일 범위 = 청크 1개)
        output_file = tmp_path / "events.jsonl"
        r = runner.invoke(cli, [
            "export", "events",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
            "--event-name", "Purchase",
            "--file", str(output_file),
        ])
        assert r.exit_code == 0
        assert output_file.exists()
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "Purchase"

    @respx.mock
    def test_events_search_filter(self, runner):
        """--search 필터로 이벤트 이름 검색."""
        # --search는 서버 사이드 필터링: mock이 이미 필터된 결과를 반환
        events_resp = {"results": ["Purchase", "Purchase Complete"]}
        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json=events_resp)
        )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--search", "Purchase"])
        assert r.exit_code == 0
        result = parse_last_json(r.output)
        assert all("Purchase" in e for e in result)
        assert "Login" not in result


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 3: 에러 복구 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """시나리오: 다양한 에러 상황에서 CLI가 올바른 JSON을 반환한다."""

    @respx.mock
    def test_auth_error_returns_json(self, runner):
        """401 응답 → AUTH_ERROR JSON."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0  # CLI는 항상 exit 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] == "AUTH_ERROR"

    @respx.mock
    def test_rate_limit_error(self, runner):
        """429 응답 → RATE_LIMIT JSON."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(429, json={"error": "rate limited"})
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] == "RATE_LIMIT"

    @respx.mock
    def test_missing_credentials_error(self, runner, monkeypatch):
        """인증 정보 없을 때 AUTH_ERROR."""
        monkeypatch.delenv("MIXPANEL_USERNAME", raising=False)
        monkeypatch.delenv("MIXPANEL_SECRET", raising=False)
        monkeypatch.delenv("MIXPANEL_PROJECT_ID", raising=False)

        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"

    @respx.mock
    def test_invalid_date_format(self, runner):
        """잘못된 날짜 형식 → CLI 레벨 에러 (exit 2)."""
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "03-01-2026",  # 잘못된 형식
            "--to-date", "2026-03-31",
        ])
        # Click parameter validation → exit 2
        assert r.exit_code == 2


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 4: AI ask 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

class TestAskWorkflow:
    """시나리오: AI 자연어 쿼리로 Mixpanel 데이터를 분석한다."""

    @pytest.fixture(autouse=True)
    def set_ai_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _make_claude_mock(self, command="insight"):
        mock = MagicMock()
        mock.ask_mixpanel.return_value = {
            "command": command,
            "params": {
                "event": "Sign Up",
                "from_date": "2026-03-01",
                "to_date": "2026-03-31",
                "unit": "day",
            },
            "summary_template": "총 {value}건",
            "explanation": "Sign Up 이벤트를 월간 insight로 조회했습니다.",
        }
        return mock

    @respx.mock
    def test_dry_run_no_api_call(self, runner):
        """--dry-run: API 실행 없이 파라미터만 반환."""
        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=self._make_claude_mock()), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
            r = runner.invoke(cli, ["ask", "query", "이번 달 Sign Up 몇 건?", "--dry-run"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"
        assert d["data"]["command"] == "insight"
        assert "params" in d["data"]

    @respx.mock
    def test_explain_includes_explanation(self, runner):
        """--explain: meta에 explanation 포함."""
        insight_data = {"data": {"values": {"Sign Up": {"2026-03-01": 100}}}}
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json=insight_data)
        )
        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=self._make_claude_mock()), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
            r = runner.invoke(cli, ["ask", "query", "Sign Up 분석", "--explain"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert "explanation" in d.get("meta", {})

    @respx.mock
    def test_no_summary_flag(self, runner):
        """--no-summary: meta에 summary 없음."""
        insight_data = {"data": {"values": {}}}
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json=insight_data)
        )
        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=self._make_claude_mock()), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Sign Up"]):
            r = runner.invoke(cli, ["ask", "query", "Sign Up", "--no-summary"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert "summary" not in d.get("meta", {})

    def test_ai_package_not_installed(self, runner):
        """anthropic 미설치 시 AI_NOT_INSTALLED 에러."""
        from mixpanel_cli.exceptions import AINotInstalledError
        with patch("mixpanel_cli.commands.ask.ClaudeClient",
                   side_effect=AINotInstalledError("not installed")), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=[]):
            r = runner.invoke(cli, ["ask", "query", "Sign Up 분석"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] == "AI_NOT_INSTALLED"


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 5: 전역 플래그 조합
# ─────────────────────────────────────────────────────────────────────────────

class TestGlobalFlags:
    """시나리오: 전역 플래그가 모든 서브커맨드에 올바르게 적용된다."""

    @respx.mock
    def test_pretty_flag_formats_json(self, runner):
        """--pretty: 들여쓰기된 JSON 출력."""
        insight_data = {"data": {"series": [], "values": {}}, "legend_size": 0}
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json=insight_data)
        )
        r = runner.invoke(cli, [
            "--pretty",
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        assert "\n" in r.output  # pretty print에는 줄바꿈 있음
        assert "  " in r.output  # 들여쓰기 있음

    @respx.mock
    def test_project_id_override(self, runner):
        """--project-id로 환경변수 프로젝트 ID 오버라이드."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={"data": {"values": {}}, "legend_size": 0})
        )
        r = runner.invoke(cli, [
            "--project-id", "999999",
            "analytics", "insight",
            "--event", "Login",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    def test_help_text_available(self, runner):
        """모든 주요 커맨드에 --help가 작동한다."""
        for cmd in [
            ["--help"],
            ["analytics", "--help"],
            ["events", "--help"],
            ["export", "--help"],
            ["config", "--help"],
            ["dashboard", "--help"],
            ["lexicon", "--help"],
            ["ask", "--help"],
        ]:
            r = runner.invoke(cli, cmd)
            assert r.exit_code == 0, f"--help failed for: {cmd}"
            assert "Usage:" in r.output


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 6: Dashboard + Lexicon (비공식 API)
# ─────────────────────────────────────────────────────────────────────────────

class TestUnofficialApiScenarios:
    """시나리오: 비공식 API 사용 시 경고가 표시되고 정상 동작한다."""

    @respx.mock
    def test_dashboard_workflow(self, runner):
        """대시보드 목록 조회 → 특정 대시보드 조회."""
        list_resp = {"status": "ok", "results": [{"id": 1, "title": "KPI Dashboard"}]}
        get_resp = {"status": "ok", "result": {"id": 1, "title": "KPI Dashboard", "reports": []}}

        respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks").mock(
            return_value=httpx.Response(200, json=list_resp)
        )
        respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks/1").mock(
            return_value=httpx.Response(200, json=get_resp)
        )

        # 목록 조회 (WARNING이 stderr에 출력됨)
        r = runner.invoke(cli, ["--quiet", "dashboard", "list"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert len(d) >= 1

        # 특정 대시보드
        r = runner.invoke(cli, ["--quiet", "dashboard", "get", "--id", "1"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        # get_resp 구조: {"status": "ok", "result": {"id": 1, ...}}
        assert d.get("result", d).get("id", d.get("id")) == 1

    @respx.mock
    def test_lexicon_list_workflow(self, runner):
        """Lexicon 이벤트 목록 조회."""
        lexicon_resp = {
            "status": "ok",
            "results": [
                {"name": "Sign Up", "description": "신규 가입", "status": "active"},
                {"name": "Purchase", "description": "구매 완료", "status": "active"},
            ],
        }
        respx.get("https://mixpanel.com/api/app/projects/123456/schemas/events").mock(
            return_value=httpx.Response(200, json=lexicon_resp)
        )
        r = runner.invoke(cli, ["--quiet", "lexicon", "list"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert isinstance(d, list)
        assert len(d) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 시나리오 7: Watch 임계값 로직
# ─────────────────────────────────────────────────────────────────────────────

class TestWatchThresholds:
    """시나리오: watch 명령의 임계값 로직이 올바르게 동작한다."""

    def test_drop_threshold_triggers_alert(self):
        """20% 이상 하락 시 stderr에 ALERT 출력."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("click.echo") as mock_echo:
            _check_thresholds(
                event="Sign Up",
                current=80.0,
                change_pct=-20.0,   # -20% == threshold → 트리거
                threshold_drop=20.0,
                threshold_rise=None,
                webhook=None,
            )
        assert mock_echo.called
        alert_msg = mock_echo.call_args[0][0]
        assert "ALERT" in alert_msg
        assert "하락" in alert_msg

    def test_rise_threshold_triggers_alert(self):
        """50% 이상 상승 시 stderr에 ALERT 출력."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("click.echo") as mock_echo:
            _check_thresholds(
                event="Sign Up",
                current=160.0,
                change_pct=60.0,    # 60% > 50% threshold → 트리거
                threshold_drop=None,
                threshold_rise=50.0,
                webhook=None,
            )
        assert mock_echo.called
        alert_msg = mock_echo.call_args[0][0]
        assert "ALERT" in alert_msg
        assert "상승" in alert_msg

    def test_no_threshold_no_alert(self):
        """변화가 임계값 미만이면 알림 없음."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("click.echo") as mock_echo:
            _check_thresholds(
                event="Sign Up",
                current=95.0,
                change_pct=-5.0,    # -5%, 20% 임계값 미만 → no alert
                threshold_drop=20.0,
                threshold_rise=50.0,
                webhook=None,
            )
        assert not mock_echo.called
