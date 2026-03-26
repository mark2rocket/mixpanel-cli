"""커스텀 예외 계층."""


class MixpanelCLIError(Exception):
    code: str = "UNKNOWN_ERROR"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class AuthError(MixpanelCLIError):
    code = "AUTH_ERROR"


class PermissionError(MixpanelCLIError):
    code = "PERMISSION_ERROR"


class NotFoundError(MixpanelCLIError):
    code = "NOT_FOUND"


class RateLimitError(MixpanelCLIError):
    code = "RATE_LIMIT"


class QueryError(MixpanelCLIError):
    code = "QUERY_ERROR"


class AIParseError(MixpanelCLIError):
    code = "AI_PARSE_ERROR"


class AINotInstalledError(MixpanelCLIError):
    code = "AI_NOT_INSTALLED"


class ProfileNotFoundError(MixpanelCLIError):
    code = "PROFILE_NOT_FOUND"


class APIChangedError(MixpanelCLIError):
    code = "API_CHANGED"


class ServerError(MixpanelCLIError):
    code = "SERVER_ERROR"


HTTP_STATUS_TO_ERROR: dict[int, type[MixpanelCLIError]] = {
    400: QueryError,
    401: AuthError,
    403: PermissionError,
    404: NotFoundError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}
