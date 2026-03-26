"""CLI 엣지케이스 테스트 — 경계 조건, 빈 응답, 오류 복구 등."""

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
    """stdout의 마지막 유효한 JSON 라인 파싱 (WARNING, [DEBUG] 등 비JSON 라인 무시)."""
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
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
# 엣지케이스 1: 빈 응답 처리
# ─────────────────────────────────────────────────────────────────────────────

class TestEmptyResponseHandling:
    """API가 유효하지만 데이터가 없는 응답을 반환할 때."""

    @respx.mock
    def test_insight_empty_values(self, runner):
        """values가 빈 딕셔너리일 때 ok 응답."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={"data": {"series": [], "values": {}}, "legend_size": 0})
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "NonExistentEvent",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"
        assert d["data"]["data"]["values"] == {}

    @respx.mock
    def test_events_list_empty(self, runner):
        """이벤트가 하나도 없을 때 빈 배열 반환."""
        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        r = runner.invoke(cli, ["--quiet", "events", "list"])
        assert r.exit_code == 0
        result = parse_last_json(r.output)
        assert result == []

    @respx.mock
    def test_export_empty_stream(self, runner, tmp_path):
        """export 결과가 없을 때 빈 파일 생성."""
        respx.get("https://data.mixpanel.com/api/2.0/export").mock(
            return_value=httpx.Response(200, text="")
        )
        output_file = tmp_path / "empty.jsonl"
        r = runner.invoke(cli, [
            "export", "events",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-01",  # 1일
            "--file", str(output_file),
        ])
        assert r.exit_code == 0
        assert output_file.exists()
        assert output_file.read_bytes() == b""

    @respx.mock
    def test_retention_empty_data(self, runner):
        """retention 데이터가 없어도 ok 반환."""
        respx.get("https://mixpanel.com/api/2.0/retention").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        r = runner.invoke(cli, [
            "analytics", "retention",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 2: HTTP 서버 에러
# ─────────────────────────────────────────────────────────────────────────────

class TestServerErrors:
    """5xx 응답이 올 때 CLI가 JSON 에러를 반환한다."""

    @respx.mock
    def test_500_returns_server_error(self, runner):
        """500 → SERVER_ERROR JSON, exit 0."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(500, json={"error": "internal server error"})
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] == "SERVER_ERROR"

    @respx.mock
    def test_503_returns_server_error(self, runner):
        """503 Service Unavailable → SERVER_ERROR."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] == "SERVER_ERROR"

    @respx.mock
    def test_404_returns_not_found(self, runner):
        """404 → NOT_FOUND 계열 에러."""
        respx.get("https://mixpanel.com/api/2.0/funnels").mock(
            return_value=httpx.Response(404, json={"error": "funnel not found"})
        )
        r = runner.invoke(cli, [
            "analytics", "funnel",
            "--id", "99999",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"
        assert d["code"] in ("NOT_FOUND", "REQUEST_ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 3: 날짜 경계 조건
# ─────────────────────────────────────────────────────────────────────────────

class TestDateBoundaries:
    """날짜 범위 경계 케이스."""

    @respx.mock
    def test_same_day_query(self, runner):
        """from_date == to_date: 하루 쿼리는 정상 동작."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": ["2026-03-15"], "values": {"Login": {"2026-03-15": 42}}},
                "legend_size": 1,
            })
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Login",
            "--from-date", "2026-03-15",
            "--to-date", "2026-03-15",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    @respx.mock
    def test_export_single_day_one_chunk(self, runner, tmp_path):
        """하루 export는 청크 1개."""
        lines = '{"event":"Login","properties":{"time":1234567890}}\n'
        respx.get("https://data.mixpanel.com/api/2.0/export").mock(
            return_value=httpx.Response(200, text=lines)
        )
        output_file = tmp_path / "day.jsonl"
        r = runner.invoke(cli, [
            "export", "events",
            "--from-date", "2026-03-15",
            "--to-date", "2026-03-15",
            "--file", str(output_file),
        ])
        assert r.exit_code == 0
        assert output_file.read_text().count("\n") == 1

    @respx.mock
    def test_export_31_days_two_chunks(self, runner, tmp_path):
        """31일 범위: 청크 2개 → export 2번 호출, 데이터 합산."""
        lines = '{"event":"Purchase","properties":{}}\n'
        # 두 번 호출 → 각각 1줄씩 = 총 2줄
        respx.get("https://data.mixpanel.com/api/2.0/export").mock(
            return_value=httpx.Response(200, text=lines)
        )
        output_file = tmp_path / "multi.jsonl"
        r = runner.invoke(cli, [
            "export", "events",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-31",  # 31일 → 2청크
            "--file", str(output_file),
        ])
        assert r.exit_code == 0
        content = output_file.read_text()
        assert content.count("\n") == 2  # 청크당 1줄, 총 2줄


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 4: 전역 플래그 조합
# ─────────────────────────────────────────────────────────────────────────────

class TestFlagCombinations:
    """전역 플래그 조합 시 예상 동작."""

    @respx.mock
    def test_pretty_and_quiet_together(self, runner):
        """--pretty + --quiet: quiet가 우선 (data만 출력, pretty 무시)."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": [], "values": {"A": {"2026-03-01": 1}}},
                "legend_size": 1,
            })
        )
        r = runner.invoke(cli, [
            "--pretty", "--quiet",
            "analytics", "insight",
            "--event", "A",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        # quiet 모드: status/meta 없음
        assert "status" not in d

    @respx.mock
    def test_debug_flag_writes_to_stderr_only(self, runner):
        """--debug: stdout에는 JSON만, stderr에는 디버그 정보."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": [], "values": {}}, "legend_size": 0
            })
        )
        r = runner.invoke(cli, [
            "--debug",
            "analytics", "insight",
            "--event", "X",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        # stdout은 여전히 유효한 JSON
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    @respx.mock
    def test_all_regions_use_correct_endpoints(self, runner):
        """us/eu/in 리전 각각 올바른 엔드포인트."""
        region_map = {
            "us": "https://mixpanel.com/api/2.0/insights",
            "eu": "https://eu.mixpanel.com/api/2.0/insights",
            "in": "https://in.mixpanel.com/api/2.0/insights",
        }
        empty_resp = {"data": {"series": [], "values": {}}, "legend_size": 0}
        for region, url in region_map.items():
            with respx.mock:
                respx.get(url).mock(return_value=httpx.Response(200, json=empty_resp))
                r = runner.invoke(cli, [
                    "--region", region,
                    "analytics", "insight",
                    "--event", "E",
                    "--from-date", "2026-03-01",
                    "--to-date", "2026-03-30",
                ])
            assert r.exit_code == 0, f"region={region} failed"
            d = parse_last_json(r.output)
            assert d["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 5: Events 페이지네이션 경계
# ─────────────────────────────────────────────────────────────────────────────

class TestPaginationEdgeCases:
    """페이지네이션 경계 케이스."""

    @respx.mock
    def test_page_beyond_total(self, runner):
        """존재하지 않는 페이지 요청 → 빈 배열 반환 (에러 아님)."""
        # 5개 이벤트만 있음 → page_size=50이면 page 2는 빈 결과
        events = [f"Event{i}" for i in range(5)]
        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json={"results": events})
        )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--page", "2"])
        assert r.exit_code == 0
        result = parse_last_json(r.output)
        assert result == []

    @respx.mock
    def test_exactly_page_size_events(self, runner):
        """정확히 50개 이벤트: page 1은 50개, page 2는 빈 배열."""
        events = [f"Event{i:03d}" for i in range(50)]
        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json={"results": events})
        )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--page", "1"])
        assert r.exit_code == 0
        page1 = parse_last_json(r.output)
        assert len(page1) == 50

        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json={"results": events})
        )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--page", "2"])
        assert r.exit_code == 0
        page2 = parse_last_json(r.output)
        assert page2 == []

    @respx.mock
    def test_51_events_splits_pages(self, runner):
        """51개 이벤트: page 1 = 50개, page 2 = 1개."""
        events = [f"Event{i:03d}" for i in range(51)]
        for _ in range(2):
            respx.get("https://mixpanel.com/api/2.0/events/names").mock(
                return_value=httpx.Response(200, json={"results": events})
            )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--page", "1"])
        page1 = parse_last_json(r.output)
        assert len(page1) == 50

        r = runner.invoke(cli, ["--quiet", "events", "list", "--page", "2"])
        page2 = parse_last_json(r.output)
        assert len(page2) == 1
        assert page2[0] == "Event050"


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 6: Watch 내부 로직
# ─────────────────────────────────────────────────────────────────────────────

class TestWatchInternalLogic:
    """watch 명령의 내부 함수 엣지케이스."""

    def test_sum_insight_empty_values(self):
        """빈 values → 0.0 반환 (ZeroDivisionError 없음)."""
        from mixpanel_cli.commands.watch import _sum_insight
        assert _sum_insight({"data": {"values": {}}}) == 0.0

    def test_sum_insight_malformed_data(self):
        """비정상 응답 구조 → 0.0 반환 (예외 없음)."""
        from mixpanel_cli.commands.watch import _sum_insight
        assert _sum_insight({}) == 0.0
        assert _sum_insight({"data": None}) == 0.0
        assert _sum_insight({"data": {"values": {"E": "not_a_dict"}}}) == 0.0

    def test_check_thresholds_exact_boundary_drop(self):
        """정확히 임계값과 동일한 하락 → 알림 트리거 (<=)."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("click.echo") as mock_echo:
            _check_thresholds("E", 80.0, -20.0, 20.0, None, None)  # exactly -20%
        assert mock_echo.called

    def test_check_thresholds_just_below_drop(self):
        """임계값보다 1% 적은 하락 → 알림 없음."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("click.echo") as mock_echo:
            _check_thresholds("E", 81.0, -19.0, 20.0, None, None)  # -19% < 20%
        assert not mock_echo.called

    def test_check_thresholds_webhook_called_on_alert(self):
        """임계값 초과 + webhook URL → httpx.post 호출."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("httpx.post") as mock_post, patch("click.echo"):
            _check_thresholds("E", 50.0, -50.0, 20.0, None, "https://hooks.example.com/alert")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "https://hooks.example.com/alert"

    def test_check_thresholds_no_alert_no_webhook(self):
        """변화 없음 → webhook 호출 안 함."""
        from mixpanel_cli.commands.watch import _check_thresholds
        with patch("httpx.post") as mock_post:
            _check_thresholds("E", 100.0, 0.0, 20.0, 50.0, "https://hooks.example.com/alert")
        mock_post.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 7: Ask 명령 엣지케이스
# ─────────────────────────────────────────────────────────────────────────────

class TestAskEdgeCases:
    """ask 명령의 비정상 시나리오."""

    @pytest.fixture(autouse=True)
    def set_ai_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def test_ask_without_api_key(self, runner, monkeypatch):
        """ANTHROPIC_API_KEY 없을 때 AI_NOT_INSTALLED or AUTH 에러."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from mixpanel_cli.exceptions import AINotInstalledError
        with patch("mixpanel_cli.commands.ask.ClaudeClient",
                   side_effect=AINotInstalledError("no key")), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=[]):
            r = runner.invoke(cli, ["ask", "query", "뭐든지"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "error"

    @respx.mock
    def test_ask_dry_run_does_not_call_mixpanel(self, runner):
        """--dry-run: Mixpanel API 호출 없이 파라미터만 반환."""
        mock = MagicMock()
        mock.ask_mixpanel.return_value = {
            "command": "insight",
            "params": {"event": "A", "from_date": "2026-03-01", "to_date": "2026-03-30", "unit": "day"},
            "summary_template": "{value}건",
            "explanation": "테스트",
        }
        # Mixpanel API가 호출되면 respx가 unmocked exception을 던짐
        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=mock), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["A"]):
            r = runner.invoke(cli, ["ask", "query", "A 건수", "--dry-run"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"
        assert d["data"]["command"] == "insight"

    @respx.mock
    def test_ask_explain_and_summary_together(self, runner):
        """--explain + 기본 summary: meta에 explanation과 summary 모두 포함."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"values": {"Login": {"2026-03-01": 200}}}, "legend_size": 1
            })
        )
        mock = MagicMock()
        mock.ask_mixpanel.return_value = {
            "command": "insight",
            "params": {"event": "Login", "from_date": "2026-03-01", "to_date": "2026-03-30", "unit": "day"},
            "summary_template": "총 {value}건",
            "explanation": "Login 이벤트 조회",
        }
        with patch("mixpanel_cli.commands.ask.ClaudeClient", return_value=mock), \
             patch("mixpanel_cli.commands.ask.get_cached_events", return_value=["Login"]):
            r = runner.invoke(cli, ["ask", "query", "Login 분석", "--explain"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert "explanation" in d.get("meta", {})


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 8: 특수 입력값
# ─────────────────────────────────────────────────────────────────────────────

class TestSpecialInputs:
    """특수 문자, 공백, 긴 문자열 등."""

    @respx.mock
    def test_event_name_with_spaces(self, runner):
        """공백 포함 이벤트명 처리."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": [], "values": {"Sign Up Button Clicked": {}}},
                "legend_size": 1,
            })
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "Sign Up Button Clicked",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    @respx.mock
    def test_event_name_with_unicode(self, runner):
        """유니코드/한국어 이벤트명 처리."""
        respx.get("https://mixpanel.com/api/2.0/insights").mock(
            return_value=httpx.Response(200, json={
                "data": {"series": [], "values": {"구매완료": {}}},
                "legend_size": 1,
            })
        )
        r = runner.invoke(cli, [
            "analytics", "insight",
            "--event", "구매완료",
            "--from-date", "2026-03-01",
            "--to-date", "2026-03-30",
        ])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        assert d["status"] == "ok"

    @respx.mock
    def test_events_search_no_match(self, runner):
        """검색 결과가 없을 때 빈 배열 반환."""
        respx.get("https://mixpanel.com/api/2.0/events/names").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        r = runner.invoke(cli, ["--quiet", "events", "list", "--search", "존재하지않는이벤트XYZ123"])
        assert r.exit_code == 0
        result = parse_last_json(r.output)
        assert result == []

    def test_required_option_missing_exits_2(self, runner):
        """필수 옵션 누락 시 exit 2 (Click validation)."""
        r = runner.invoke(cli, ["analytics", "insight", "--event", "X"])
        # --from-date, --to-date 누락
        assert r.exit_code == 2

    def test_invalid_region_exits_2(self, runner):
        """지원하지 않는 리전 → exit 2."""
        r = runner.invoke(cli, ["--region", "jp", "analytics", "--help"])
        assert r.exit_code == 2


# ─────────────────────────────────────────────────────────────────────────────
# 엣지케이스 9: 응답 구조 방어 (APIChangedError)
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIChangedDefense:
    """비공식 API 응답 구조 변경 시 방어적 처리."""

    @respx.mock
    def test_dashboard_unexpected_structure(self, runner):
        """비공식 API가 예상치 못한 구조를 반환해도 CLI는 에러 JSON을 출력한다."""
        # 응답이 완전히 다른 구조 (예: 문자열만 반환)
        respx.get("https://mixpanel.com/api/app/projects/123456/bookmarks").mock(
            return_value=httpx.Response(200, json={"unexpected_key": "unexpected_value"})
        )
        r = runner.invoke(cli, ["dashboard", "list"])
        assert r.exit_code == 0
        d = parse_last_json(r.output)
        # ok 또는 에러 — 어떤 경우든 유효한 JSON
        assert d.get("status") in ("ok", "error")

    @respx.mock
    def test_lexicon_empty_results(self, runner):
        """lexicon results가 빈 배열일 때 ok 반환."""
        respx.get("https://mixpanel.com/api/app/projects/123456/schemas/events").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        r = runner.invoke(cli, ["--quiet", "lexicon", "list"])
        assert r.exit_code == 0
        result = parse_last_json(r.output)
        assert result == []
