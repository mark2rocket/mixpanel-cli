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
