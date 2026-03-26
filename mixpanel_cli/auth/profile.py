"""프로파일 CRUD 및 인증 해결."""

import json
import os
from pathlib import Path
from typing import Optional

from mixpanel_cli.constants import PROFILES_PATH_DEFAULT
from mixpanel_cli.exceptions import AuthError, ProfileNotFoundError
from mixpanel_cli.models import Profile, ProfilesFile


def _profiles_path() -> Path:
    return Path(os.path.expanduser(PROFILES_PATH_DEFAULT))


def load_profiles() -> ProfilesFile:
    path = _profiles_path()
    if not path.exists():
        return ProfilesFile()
    try:
        data = json.loads(path.read_text())
        return ProfilesFile.model_validate(data)
    except Exception:
        return ProfilesFile()


def save_profiles(pf: ProfilesFile) -> None:
    path = _profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pf.model_dump_json(indent=2))


def get_profile(name: str) -> Profile:
    pf = load_profiles()
    if name not in pf.profiles:
        raise ProfileNotFoundError(
            f"프로파일 '{name}'을 찾을 수 없습니다. `mixpanel config init --profile {name}` 실행 필요."
        )
    return pf.profiles[name]


def list_profiles() -> list[dict]:
    pf = load_profiles()
    return [
        {
            "name": name,
            "username": p.service_account_username,
            "project_id": p.project_id,
            "region": p.region,
            "is_default": name == pf.default,
        }
        for name, p in pf.profiles.items()
    ]


def save_profile(profile: Profile) -> None:
    pf = load_profiles()
    pf.profiles[profile.name] = profile
    if not pf.profiles or len(pf.profiles) == 1:
        pf.default = profile.name
    save_profiles(pf)


def delete_profile(name: str) -> None:
    pf = load_profiles()
    if name not in pf.profiles:
        raise ProfileNotFoundError(f"프로파일 '{name}'을 찾을 수 없습니다.")
    del pf.profiles[name]
    if pf.default == name and pf.profiles:
        pf.default = next(iter(pf.profiles))
    save_profiles(pf)


def update_profile_field(name: str, key: str, value: str) -> None:
    pf = load_profiles()
    if name not in pf.profiles:
        raise ProfileNotFoundError(f"프로파일 '{name}'을 찾을 수 없습니다.")
    profile_data = pf.profiles[name].model_dump()
    if key not in profile_data:
        raise ValueError(f"알 수 없는 필드: '{key}'. 사용 가능: {list(profile_data.keys())}")
    profile_data[key] = value
    pf.profiles[name] = Profile.model_validate(profile_data)
    save_profiles(pf)


class AuthContext:
    """인증 컨텍스트 — 우선순위에 따라 자격증명 해결."""

    def __init__(
        self,
        profile_name: str = "default",
        username: str | None = None,
        secret: str | None = None,
        project_id: str | None = None,
        region: str | None = None,
    ):
        self.use_oauth: bool = False
        self.access_token: str | None = None
        self._resolve(profile_name, username, secret, project_id, region)

    def _resolve(self, profile_name, cli_username, cli_secret, cli_project_id, cli_region):
        # 1순위: CLI 플래그
        if cli_username and cli_secret and cli_project_id:
            self.username = cli_username
            self.secret = cli_secret
            self.project_id = cli_project_id
            self.region = cli_region or "us"
            return

        # 2순위: 환경변수
        env_username = os.environ.get("MIXPANEL_USERNAME")
        env_secret = os.environ.get("MIXPANEL_SECRET")
        env_project_id = os.environ.get("MIXPANEL_PROJECT_ID")
        env_region = os.environ.get("MIXPANEL_REGION", "us")

        if env_username and env_secret and env_project_id:
            self.username = env_username
            self.secret = env_secret
            self.project_id = env_project_id
            self.region = cli_region or env_region
            return

        # 3순위: OAuth 토큰 (keychain)
        from mixpanel_cli.auth.keychain import get_oauth_token, set_oauth_token
        oauth_token = get_oauth_token(profile_name)
        if oauth_token is not None:
            if oauth_token.is_expired():
                # 자동 갱신 시도
                try:
                    from mixpanel_cli.auth.oauth import refresh_token_request
                    oauth_token = refresh_token_request(oauth_token, oauth_token.client_id, oauth_token.region)
                    set_oauth_token(profile_name, oauth_token)
                except Exception:
                    pass  # 갱신 실패 시 Service Account로 폴백
            if not oauth_token.is_expired():
                resolved_project_id = cli_project_id or os.environ.get("MIXPANEL_PROJECT_ID", "")
                if not resolved_project_id:
                    raise AuthError(
                        "OAuth 로그인 상태이지만 project_id가 없습니다. "
                        "--project-id 플래그 또는 MIXPANEL_PROJECT_ID 환경변수를 설정하세요."
                    )
                self.use_oauth = True
                self.access_token = oauth_token.access_token
                self.project_id = resolved_project_id
                self.region = cli_region or os.environ.get("MIXPANEL_REGION", oauth_token.region)
                # Service Account 필드는 빈값으로 (OAuth 모드에서 불필요)
                self.username = ""
                self.secret = ""
                return

        # 4순위: 프로파일 + keychain
        try:
            profile = get_profile(profile_name)
        except ProfileNotFoundError:
            raise AuthError(
                f"인증 정보를 찾을 수 없습니다. "
                f"`mixpanel config init` 또는 환경변수 MIXPANEL_USERNAME/MIXPANEL_SECRET/MIXPANEL_PROJECT_ID 설정 필요."
            )

        from mixpanel_cli.auth.keychain import get_secret
        secret = get_secret(profile_name)
        if secret is None:
            raise AuthError(
                f"프로파일 '{profile_name}'의 secret을 keychain에서 찾을 수 없습니다. "
                "환경변수 MIXPANEL_SECRET을 설정하거나 `mixpanel config init`을 재실행하세요."
            )
        self.username = profile.service_account_username
        self.secret = secret
        self.project_id = cli_project_id or profile.project_id
        self.region = cli_region or profile.region

    @property
    def auth_header(self) -> str:
        if self.use_oauth and self.access_token:
            return f"Bearer {self.access_token}"
        import base64
        token = base64.b64encode(f"{self.username}:{self.secret}".encode()).decode()
        return f"Basic {token}"
