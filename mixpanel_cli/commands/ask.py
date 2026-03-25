"""ask 명령 — 자연어 쿼리를 Mixpanel API로 변환."""

from __future__ import annotations

import json
from datetime import date

import click

from mixpanel_cli.cache import get_cached_events, set_cached_events, invalidate_cache
from mixpanel_cli.client.claude import ClaudeClient
from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError, AINotInstalledError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error


@click.group("ask")
def ask_group():
    """자연어로 Mixpanel 데이터 조회 (AI 필요)."""
    pass


@ask_group.command("query")
@click.argument("query")
@click.option("--dry-run", is_flag=True, default=False, help="파라미터만 출력, API 실행 안 함")
@click.option("--explain", is_flag=True, default=False, help="쿼리 구성 이유 포함 출력")
@click.option("--no-summary", is_flag=True, default=False, help="자연어 요약 없이 raw 데이터만 반환")
@click.option("--refresh-cache", is_flag=True, default=False, help="이벤트 캐시 강제 갱신")
@click.pass_context
def ask_query(ctx, query, dry_run, explain, no_summary, refresh_cache):
    """자연어 쿼리로 Mixpanel 데이터 조회.

    예: mixpanel ask query "지난 주 Sign Up 이벤트 몇 건?"
    """
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False

    try:
        client, auth = make_client(obj)

        # 이벤트 목록 (캐시 우선)
        if refresh_cache:
            invalidate_cache(auth.project_id)

        events = get_cached_events(auth.project_id)
        if events is None:
            events = client.get_event_names()
            set_cached_events(auth.project_id, events)

        # Claude 1회 호출
        claude = ClaudeClient()
        today = date.today().isoformat()
        result = claude.ask_mixpanel(query=query, events=events, today=today)

        command = result.get("command", "insight")
        params = result.get("params", {})
        summary_template = result.get("summary_template", "")
        explanation = result.get("explanation", "")

        if dry_run:
            response = CLIResponse.ok(
                data={"command": command, "params": params},
                meta={"explanation": explanation} if explain else {},
            )
            print_response(response, pretty=pretty, quiet=quiet)
            return

        # Mixpanel API 실행
        api_data = _execute_command(client, command, params)

        meta: dict = {}
        if explain:
            meta["explanation"] = explanation
        if not no_summary and summary_template:
            meta["summary"] = summary_template.format(value=_extract_value(api_data))

        response = CLIResponse.ok(data=api_data, meta=meta)
        print_response(response, pretty=pretty, quiet=quiet)

    except AINotInstalledError as e:
        print_error(e.code, e.message, pretty=pretty)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
    except Exception as e:
        from mixpanel_cli.exceptions import QueryError
        print_error("QUERY_ERROR", str(e), pretty=pretty)


def _execute_command(client, command: str, params: dict):
    """command + params로 MixpanelClient 메서드 호출."""
    if command == "insight":
        return client.get_insight(
            event=params.get("event", ""),
            from_date=params.get("from_date", ""),
            to_date=params.get("to_date", ""),
            unit=params.get("unit", "day"),
        )
    elif command == "funnel":
        return client.get_funnel(
            funnel_id=params.get("funnel_id", ""),
            from_date=params.get("from_date", ""),
            to_date=params.get("to_date", ""),
        )
    elif command == "retention":
        return client.get_retention(
            event=params.get("event", ""),
            from_date=params.get("from_date", ""),
            to_date=params.get("to_date", ""),
            unit=params.get("unit", "day"),
        )
    elif command == "flow":
        return client.get_flow(
            event=params.get("event", ""),
            from_date=params.get("from_date", ""),
            to_date=params.get("to_date", ""),
        )
    else:
        from mixpanel_cli.exceptions import QueryError
        raise QueryError(f"알 수 없는 command: {command}")


def _extract_value(data) -> str:
    """API 응답에서 대표 숫자 추출 (요약 템플릿용)."""
    if isinstance(data, dict):
        values = data.get("data", {}).get("values", {})
        if values:
            for v in values.values():
                if isinstance(v, dict):
                    total = sum(v.values())
                    return str(total)
        counts = data.get("counts", [])
        if counts:
            return str(sum(counts))
    return "N/A"
