"""Pydantic v2 데이터 모델."""

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
