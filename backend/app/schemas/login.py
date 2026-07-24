from pydantic import BaseModel, Field


class AccountLoginRequest(BaseModel):
    memberName: str = Field(min_length=2, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AccountLoginResponse(BaseModel):
    ok: bool = True
    status: str
    sessionId: str
    message: str
    memberName: str | None = None
    phoneNumber: str | None = None
    memberId: str | None = None
    maskedAccount: str | None = None
    phoneNumberMasked: str | None = None


class AccountLoginMfaRequest(BaseModel):
    sessionId: str = Field(min_length=12)
    code: str = Field(min_length=4, max_length=10)
    rememberBrowser: bool = False


class AccountLoginChallengeRequest(BaseModel):
    sessionId: str = Field(min_length=12)
    channel: str = Field(pattern="^(TEXT|EMAIL)$")


class AccountLoginChallengeResponse(BaseModel):
    ok: bool = True
    message: str
    channel: str
