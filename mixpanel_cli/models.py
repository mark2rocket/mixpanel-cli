"""Pydantic v2 데이터 모델."""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Profile(BaseModel):
    name: str
    service_account_username: str
    project_id: str
    region: Literal["us", "eu", "in"] = "us"
    # secret은 OS keychain에 별도 저장 — 이 모델에 포함되지 않음


class CLIResponse(BaseModel):
    status: Literal["ok", "error"]
    data: Optional[Any] = None
    meta: Optional[dict[str, Any]] = None
    code: Optional[str] = None
    message: Optional[str] = None

    @classmethod
    def ok(cls, data: Any, meta: dict | None = None) -> "CLIResponse":
        return cls(status="ok", data=data, meta=meta or {})

    @classmethod
    def error(cls, code: str, message: str) -> "CLIResponse":
        return cls(status="error", code=code, message=message)


class AskResponse(CLIResponse):
    summary: Optional[str] = None
    query_used: Optional[dict[str, Any]] = None


class ProfilesFile(BaseModel):
    profiles: dict[str, Profile] = Field(default_factory=dict)
    default: str = "default"


class OAuthToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str
    client_id: str
    region: Literal["us", "eu", "in"] = "us"

    def is_expired(self) -> bool:
        """만료 5분 전부터 만료로 간주."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        return now >= (self.expires_at - timedelta(minutes=5))
