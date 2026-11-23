from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class BootstrapLogin(BaseModel):
    owner_token: str = Field(min_length=24, max_length=512)


class ApprovalCreate(BaseModel):
    action_type: Literal["memory.add", "memory.update", "memory.delete"]
    target_id: str | None = None
    payload: dict = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=1000)


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]


class BrowserNavigate(BaseModel):
    url: HttpUrl
