"""exceptions.py 단위 테스트."""

import pytest
from mixpanel_cli.exceptions import (
    AuthError,
    PermissionError,
    NotFoundError,
    RateLimitError,
    QueryError,
    AINotInstalledError,
    ProfileNotFoundError,
    APIChangedError,
    HTTP_STATUS_TO_ERROR,
)


def test_auth_error_code():
    e = AuthError("인증 실패")
    assert e.code == "AUTH_ERROR"
    assert str(e) == "인증 실패"


def test_all_error_codes():
    assert AuthError.code == "AUTH_ERROR"
    assert PermissionError.code == "PERMISSION_ERROR"
    assert NotFoundError.code == "NOT_FOUND"
    assert RateLimitError.code == "RATE_LIMIT"
    assert QueryError.code == "QUERY_ERROR"
    assert AINotInstalledError.code == "AI_NOT_INSTALLED"
    assert ProfileNotFoundError.code == "PROFILE_NOT_FOUND"
    assert APIChangedError.code == "API_CHANGED"


def test_http_status_mapping():
    assert HTTP_STATUS_TO_ERROR[401] is AuthError
    assert HTTP_STATUS_TO_ERROR[403] is PermissionError
    assert HTTP_STATUS_TO_ERROR[404] is NotFoundError
    assert HTTP_STATUS_TO_ERROR[429] is RateLimitError
    assert HTTP_STATUS_TO_ERROR[400] is QueryError
