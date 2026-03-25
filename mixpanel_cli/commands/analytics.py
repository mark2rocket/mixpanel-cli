"""analytics 명령 그룹."""

import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error
from mixpanel_cli.types import DATE


@click.group("analytics")
def analytics_group():
    """Mixpanel 분석 쿼리."""
    pass


@analytics_group.command("insight")
@click.option("--event", required=True, help="이벤트 이름")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--unit", type=click.Choice(["day", "week", "month"]), default="day", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "table"]), default="json", show_default=True)
@click.pass_context
def analytics_insight(ctx, event, from_date, to_date, unit, fmt):
    """Insights 쿼리 — 이벤트 카운트 시계열."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_insight(event=event, from_date=from_date, to_date=to_date, unit=unit)
        response = CLIResponse.ok(data=data, meta={"event": event, "from_date": from_date, "to_date": to_date, "unit": unit})
        print_response(response, pretty=pretty, quiet=quiet, fmt=fmt)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@analytics_group.command("funnel")
@click.option("--id", "funnel_id", required=True, help="펀넬 ID")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "table"]), default="json", show_default=True)
@click.pass_context
def analytics_funnel(ctx, funnel_id, from_date, to_date, fmt):
    """Funnel 분석."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_funnel(funnel_id=funnel_id, from_date=from_date, to_date=to_date)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet, fmt=fmt)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@analytics_group.command("retention")
@click.option("--event", required=True, help="Born 이벤트 이름")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--unit", type=click.Choice(["day", "week"]), default="day", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "table"]), default="json", show_default=True)
@click.pass_context
def analytics_retention(ctx, event, from_date, to_date, unit, fmt):
    """Retention 분석."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_retention(event=event, from_date=from_date, to_date=to_date, unit=unit)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet, fmt=fmt)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@analytics_group.command("flow")
@click.option("--event", required=True, help="기준 이벤트 이름")
@click.option("--from-date", "from_date", required=True, type=DATE, help="시작 날짜 (YYYY-MM-DD)")
@click.option("--to-date", "to_date", required=True, type=DATE, help="종료 날짜 (YYYY-MM-DD)")
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "table"]), default="json", show_default=True)
@click.pass_context
def analytics_flow(ctx, event, from_date, to_date, fmt):
    """Flow 분석 — 이벤트 전후 사용자 흐름."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_flow(event=event, from_date=from_date, to_date=to_date)
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet, fmt=fmt)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
