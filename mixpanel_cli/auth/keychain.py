"""OS keychain 연동 wrapper."""

from mixpanel_cli.constants import KEYRING_SERVICE
from mixpanel_cli.exceptions import AuthError


def set_secret(profile_name: str, secret: str) -> None:
    """keyring에 secret 저장."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, profile_name, secret)
    except RuntimeError as e:
        raise AuthError(
            "keyring unavailable. Set MIXPANEL_SECRET env var instead."
        ) from e
    except Exception as e:
        raise AuthError(f"keyring 저장 실패: {e}") from e


def get_secret(profile_name: str) -> str | None:
    """keyring에서 secret 조회. 없으면 None."""
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, profile_name)
    except RuntimeError as e:
        raise AuthError(
            "keyring unavailable. Set MIXPANEL_SECRET env var instead."
        ) from e
    except Exception:
        return None


def delete_secret(profile_name: str) -> None:
    """keyring에서 secret 삭제."""
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, profile_name)
    except Exception:
        pass


def set_oauth_token(profile_name: str, token: "OAuthToken") -> None:
    """OAuth 토큰을 keyring에 JSON으로 저장."""
    try:
        import keyring
        from mixpanel_cli.models import OAuthToken  # noqa: F401 (type check용)
        keyring.set_password(
            KEYRING_SERVICE,
            f"oauth:{profile_name}",
            token.model_dump_json(),
        )
    except RuntimeError as e:
        raise AuthError("keyring unavailable.") from e
    except Exception as e:
        raise AuthError(f"OAuth 토큰 keyring 저장 실패: {e}") from e


def get_oauth_token(profile_name: str) -> "OAuthToken | None":
    """keyring에서 OAuth 토큰 조회. 없으면 None."""
    try:
        import keyring
        raw = keyring.get_password(KEYRING_SERVICE, f"oauth:{profile_name}")
        if raw is None:
            return None
        from mixpanel_cli.models import OAuthToken
        return OAuthToken.model_validate_json(raw)
    except RuntimeError as e:
        raise AuthError("keyring unavailable.") from e
    except Exception:
        return None


def delete_oauth_token(profile_name: str) -> None:
    """keyring에서 OAuth 토큰 삭제."""
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, f"oauth:{profile_name}")
    except Exception:
        pass
