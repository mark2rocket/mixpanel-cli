"""config 명령 그룹."""

import click

from mixpanel_cli.auth.keychain import delete_secret, set_secret
from mixpanel_cli.auth.profile import (
    delete_profile,
    get_profile,
    list_profiles,
    save_profile,
    update_profile_field,
)
from mixpanel_cli.exceptions import MixpanelCLIError, ProfileNotFoundError
from mixpanel_cli.models import CLIResponse, Profile
from mixpanel_cli.output.formatter import print_response, print_error


@click.group("config")
def config_group():
    """인증 프로파일 관리."""
    pass


@config_group.command("init")
@click.option("--profile", default="default", show_default=True, help="프로파일명")
@click.option("--region", type=click.Choice(["us", "eu", "in"]), default="us", show_default=True)
@click.pass_context
def config_init(ctx, profile, region):
    """프로파일 초기화 (대화형)."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False

    click.echo(f"[config init] 프로파일 '{profile}' 설정", err=True)
    username = click.prompt("Service Account Username")
    secret = click.prompt("Service Account Secret", hide_input=True)
    project_id = click.prompt("Project ID")
    region_choice = click.prompt(
        "Region", default=region, type=click.Choice(["us", "eu", "in"])
    )

    p = Profile(
        name=profile,
        service_account_username=username,
        project_id=project_id,
        region=region_choice,
    )
    try:
        save_profile(p)
        set_secret(profile, secret)
        response = CLIResponse.ok(
            data={"profile": profile, "project_id": project_id, "region": region_choice},
            meta={"message": "프로파일 저장 완료"},
        )
        print_response(response, pretty=pretty)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@config_group.command("list")
@click.pass_context
def config_list(ctx):
    """프로파일 목록 출력."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    try:
        profiles = list_profiles()
        response = CLIResponse.ok(data=profiles)
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@config_group.command("show")
@click.option("--profile", default=None, help="프로파일명 (기본: 전역 --profile)")
@click.pass_context
def config_show(ctx, profile):
    """특정 프로파일 정보 출력."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    quiet = getattr(obj, "quiet", False) if obj else False
    name = profile or (getattr(obj, "profile", "default") if obj else "default")
    try:
        p = get_profile(name)
        response = CLIResponse.ok(
            data={
                "name": p.name,
                "username": p.service_account_username,
                "project_id": p.project_id,
                "region": p.region,
            }
        )
        print_response(response, pretty=pretty, quiet=quiet)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)


@config_group.command("set")
@click.option("--profile", default=None, help="프로파일명 (기본: 전역 --profile)")
@click.option("--key", required=True, help="변경할 필드 (region, project_id, service_account_username)")
@click.option("--value", required=True, help="새 값")
@click.pass_context
def config_set(ctx, profile, key, value):
    """프로파일 단일 필드 변경."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    name = profile or (getattr(obj, "profile", "default") if obj else "default")
    try:
        update_profile_field(name, key, value)
        response = CLIResponse.ok(data={"profile": name, "key": key, "value": value})
        print_response(response, pretty=pretty)
    except (MixpanelCLIError, ValueError) as e:
        code = getattr(e, "code", "VALIDATION_ERROR")
        msg = getattr(e, "message", str(e))
        print_error(code, msg, pretty=pretty)


@config_group.command("delete")
@click.option("--profile", required=True, help="삭제할 프로파일명")
@click.pass_context
def config_delete(ctx, profile):
    """프로파일 삭제."""
    obj = ctx.obj
    pretty = getattr(obj, "pretty", False) if obj else False
    try:
        delete_profile(profile)
        delete_secret(profile)
        response = CLIResponse.ok(data={"deleted": profile})
        print_response(response, pretty=pretty)
    except MixpanelCLIError as e:
        print_error(e.code, e.message, pretty=pretty)
