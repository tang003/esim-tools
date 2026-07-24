from pydantic import BaseModel, Field


class SendMfaRequest(BaseModel):
    sessionId: str = Field(min_length=12)
    channel: str = Field(default="TEXT", pattern="^(TEXT|EMAIL)$")


class SendMfaResponse(BaseModel):
    ok: bool = True
    ref: str
    message: str


class VerifyMfaRequest(BaseModel):
    sessionId: str = Field(min_length=12)
    ref: str = Field(min_length=4, max_length=128)
    code: str = Field(min_length=4, max_length=10)

