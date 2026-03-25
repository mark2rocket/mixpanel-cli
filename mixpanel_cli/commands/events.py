"""events 명령 그룹."""

import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error


@click.group("events")
def events_group():
    """이벤트 목록 및 속성 조회."""
    pass


@events_group.command("list")
@click.option("--limit", default=255, show_default=True, type=int, help="최대 결과 수")
@click.option("--search", default=None, help="이벤트명 검색어")
@click.option("--page", default=1, show_default=True, type=int, help="페이지 번호")
@click.pass_context
def events_list(ctx, limit, search, page):
    """이벤트 목록 조회."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        names = client.get_event_names(limit=limit, search=search)
        # 간단한 클라이언트 사이드 페이지네이션
        page_size = 50
        start = (page - 1) * page_size
        page_data = names[start : start + page_size]
        response = CLIResponse.ok(
            data=page_data,
            meta={"total": len(names), "page": page, "page_size": page_size},
        )
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@events_group.command("get")
@click.option("--name", required=True, help="이벤트 이름")
@click.pass_context
def events_get(ctx, name):
    """특정 이벤트 상세 정보 조회."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_event_details(name)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@events_group.command("properties")
@click.option("--event", required=True, help="이벤트 이름")
@click.pass_context
def events_properties(ctx, event):
    """이벤트 속성(property) 목록 조회."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_event_properties(event)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
