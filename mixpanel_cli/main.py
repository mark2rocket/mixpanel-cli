"""mixpanel-cli 진입점."""

import click
from mixpanel_cli.commands import config, project, analytics, events, export


class AppContext:
    def __init__(self):
        self.profile = "default"
        self.project_id = None
        self.region = None
        self.pretty = False
        self.quiet = False
        self.no_color = False
        self.debug = False
        self.timeout = 30
        self.fmt = "json"


pass_ctx = click.make_pass_decorator(AppContext, ensure=True)


@click.group()
@click.option("--profile", default="default", show_default=True, help="사용할 프로파일명")
@click.option("--project-id", default=None, help="프로젝트 ID 오버라이드")
@click.option("--region", type=click.Choice(["us", "eu", "in"]), default=None, help="리전 오버라이드")
@click.option("--pretty", is_flag=True, default=False, help="JSON pretty print")
@click.option("--quiet", is_flag=True, default=False, help="data 값만 출력")
@click.option("--no-color", is_flag=True, default=False, help="컬러 출력 비활성화")
@click.option("--debug", is_flag=True, default=False, help="요청/응답 디버그 출력")
@click.option("--timeout", default=30, show_default=True, type=int, help="HTTP 타임아웃 (초)")
@click.version_option("0.1.0", prog_name="mixpanel-cli")
@click.pass_context
def cli(ctx, profile, project_id, region, pretty, quiet, no_color, debug, timeout):
    """Mixpanel CLI — 에이전트 친화적 분석 도구."""
    ctx.ensure_object(AppContext)
    obj = ctx.obj
    obj.profile = profile
    obj.project_id = project_id
    obj.region = region
    obj.pretty = pretty
    obj.quiet = quiet
    obj.no_color = no_color
    obj.debug = debug
    obj.timeout = timeout


cli.add_command(config.config_group, name="config")
cli.add_command(project.project_group, name="project")
cli.add_command(analytics.analytics_group, name="analytics")
cli.add_command(events.events_group, name="events")
cli.add_command(export.export_group, name="export")


if __name__ == "__main__":
    cli()
