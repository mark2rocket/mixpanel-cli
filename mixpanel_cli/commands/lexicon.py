"""lexicon 명령 그룹 (비공식 API)."""

import sys
import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error

_WARN = "[WARNING] lexicon commands use an undocumented API and may break without notice."


@click.group("lexicon")
def lexicon_group():
    """Lexicon 이벤트/프로퍼티 메타데이터 관리 (비공식 API)."""
    pass


@lexicon_group.command("list")
@click.pass_context
def lexicon_list(ctx):
    """Lexicon에 정의된 이벤트 목록 조회."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        data = client.get_lexicon_events()
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@lexicon_group.command("edit-event")
@click.option("--event", required=True, help="이벤트 이름")
@click.option("--description", default=None, help="이벤트 설명")
@click.option("--status", type=click.Choice(["active", "dropped", "hidden"]), default=None)
@click.pass_context
def lexicon_edit_event(ctx, event, description, status):
    """Lexicon 이벤트 메타데이터 수정."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    kwargs = {}
    if description is not None:
        kwargs["description"] = description
    if status is not None:
        kwargs["status"] = status
    try:
        client, _ = make_client(obj)
        data = client.update_lexicon_event(event, **kwargs)
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@lexicon_group.command("edit-property")
@click.option("--event", required=True, help="이벤트 이름")
@click.option("--property", "prop", required=True, help="프로퍼티 이름")
@click.option("--description", default=None, help="프로퍼티 설명")
@click.option("--hidden", is_flag=True, default=False, help="프로퍼티 숨김 처리")
@click.pass_context
def lexicon_edit_property(ctx, event, prop, description, hidden):
    """Lexicon 이벤트 프로퍼티 메타데이터 수정."""
    click.echo(_WARN, file=sys.stderr)
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    kwargs = {}
    if description is not None:
        kwargs["description"] = description
    if hidden:
        kwargs["hidden"] = True
    try:
        client, _ = make_client(obj)
        data = client.update_lexicon_property(event, prop, **kwargs)
        print_response(CLIResponse.ok(data=data), pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
