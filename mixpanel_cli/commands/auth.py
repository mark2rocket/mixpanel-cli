"""OAuth 인증 명령 그룹."""

import click

from mixpanel_cli.output.formatter import print_response
from mixpanel_cli.models import CLIResponse


@click.group("auth")
def auth_group():
    """Mixpanel OAuth 인증 관리."""


@auth_group.command("login")
@click.option("--region", type=click.Choice(["us", "eu", "in"]), default="us", show_default=True, help="Mixpanel 리전")
@click.option("--profile", default="default", show_default=True, help="저장할 프로파일명")
@click.option("--pretty", is_flag=True, default=False)
@click.option("--quiet", is_flag=True, default=False)
def login(region, profile, pretty, quiet):
    """브라우저 OAuth 로그인 후 토큰을 keychain에 저장."""
    try:
        from mixpanel_cli.auth.oauth import run_login_flow
        from mixpanel_cli.auth.keychain import set_oauth_token

        token = run_login_flow(region=region)
        set_oauth_token(profile, token)

        response = CLIResponse.ok(data={
            "message": "로그인 성공",
            "profile": profile,
            "scope": token.scope,
            "expires_at": token.expires_at.isoformat(),
        })
    except Exception as e:
        from mixpanel_cli.exceptions import MixpanelCLIError
        if isinstance(e, MixpanelCLIError):
            response = CLIResponse.error(code=e.code, message=str(e))
        else:
            response = CLIResponse.error(code="AUTH_ERROR", message=str(e))

    print_response(response, pretty=pretty, quiet=quiet)


@auth_group.command("logout")
@click.option("--profile", default="default", show_default=True, help="프로파일명")
@click.option("--pretty", is_flag=True, default=False)
@click.option("--quiet", is_flag=True, default=False)
def logout(profile, pretty, quiet):
    """저장된 OAuth 토큰 삭제."""
    from mixpanel_cli.auth.keychain import delete_oauth_token
    delete_oauth_token(profile)
    response = CLIResponse.ok(data={"message": f"프로파일 '{profile}' OAuth 토큰 삭제 완료"})
    print_response(response, pretty=pretty, quiet=quiet)


@auth_group.command("status")
@click.option("--profile", default="default", show_default=True, help="프로파일명")
@click.option("--pretty", is_flag=True, default=False)
@click.option("--quiet", is_flag=True, default=False)
def status(profile, pretty, quiet):
    """현재 인증 상태 확인."""
    from mixpanel_cli.auth.keychain import get_oauth_token
    from mixpanel_cli.auth.profile import load_profiles

    oauth_token = get_oauth_token(profile)
    if oauth_token is not None:
        response = CLIResponse.ok(data={
            "auth_type": "oauth",
            "profile": profile,
            "expired": oauth_token.is_expired(),
            "expires_at": oauth_token.expires_at.isoformat(),
            "scope": oauth_token.scope,
        })
    else:
        pf = load_profiles()
        p = pf.profiles.get(profile)
        if p:
            response = CLIResponse.ok(data={
                "auth_type": "service_account",
                "profile": profile,
                "username": p.service_account_username,
                "project_id": p.project_id,
                "region": p.region,
            })
        else:
            response = CLIResponse.ok(data={
                "auth_type": "none",
                "profile": profile,
                "message": "인증 정보 없음. `mixpanel auth login` 또는 `mixpanel config init` 실행 필요.",
            })

    print_response(response, pretty=pretty, quiet=quiet)
