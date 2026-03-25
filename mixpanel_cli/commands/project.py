"""project 명령 그룹."""

import click

from mixpanel_cli.commands._utils import make_client
from mixpanel_cli.exceptions import MixpanelCLIError
from mixpanel_cli.models import CLIResponse
from mixpanel_cli.output.formatter import print_response, print_error


@click.group("project")
def project_group():
    """프로젝트 정보 조회."""
    pass


@project_group.command("info")
@click.option("--project-id", default=None, help="프로젝트 ID (기본: 프로파일)")
@click.pass_context
def project_info(ctx, project_id):
    """프로젝트 정보 출력."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    if project_id and obj:
        obj.project_id = project_id
    try:
        client, auth = make_client(obj)
        projects = client.get_projects()
        # project_id에 해당하는 프로젝트만 필터
        match = next((p for p in projects if str(p.get("id")) == str(auth.project_id)), None)
        data = match or (projects[0] if projects else {})
        response = CLIResponse.ok(data=data)
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@project_group.command("list")
@click.pass_context
def project_list(ctx):
    """접근 가능한 프로젝트 목록 출력."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        client, _ = make_client(obj)
        projects = client.get_projects()
        response = CLIResponse.ok(data=projects)
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
