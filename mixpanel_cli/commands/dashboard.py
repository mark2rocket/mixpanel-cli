"""dashboard 명령 그룹 (비공식 API)."""

import sys
import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error

_WARN = "[WARNING] dashboard commands use an undocumented API and may break without notice."


@click.group("dashboard")
def dashboard_group():
    """대시보드 관리 (비공식 API)."""
    pass


@dashboard_group.command("list")
@click.pass_context
def dashboard_list(ctx):
    """대시보드 목록 조회."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_dashboards()
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@dashboard_group.command("get")
@click.option("--id", "dashboard_id", required=True, help="대시보드 ID")
@click.pass_context
def dashboard_get(ctx, dashboard_id):
    """특정 대시보드 상세 조회."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_dashboard(dashboard_id)
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@dashboard_group.command("create")
@click.option("--title", required=True, help="대시보드 제목")
@click.pass_context
def dashboard_create(ctx, title):
    """새 대시보드 생성."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.create_dashboard(title=title)
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@dashboard_group.command("update")
@click.option("--id", "dashboard_id", required=True, help="대시보드 ID")
@click.option("--title", default=None, help="새 제목")
@click.pass_context
def dashboard_update(ctx, dashboard_id, title):
    """대시보드 수정."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    kwargs = {}
    if title:
        kwargs["title"] = title
    try:
        client, _ = make_client(obj)
        data = client.update_dashboard(dashboard_id, **kwargs)
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@dashboard_group.command("delete")
@click.option("--id", "dashboard_id", required=True, help="대시보드 ID")
@click.pass_context
def dashboard_delete(ctx, dashboard_id):
    """대시보드 삭제."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        client.delete_dashboard(dashboard_id)
        print_response(
            CLIResponse.ok(data={"deleted": dashboard_id}),
            pretty=pretty,
            quiet=quiet,
        )
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
