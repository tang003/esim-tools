from pydantic import BaseModel, Field


class SessionRequest(BaseModel):
    sessionId: str = Field(min_length=12)


class DownloadTokenRequest(SessionRequest):
    ssn: str | None = Field(default=None, min_length=4, max_length=64)
    itemId: str | None = Field(default=None, min_length=1, max_length=24)


class EsimItem(BaseModel):
    itemId: str
    ssn: str | None = None
    ssnMasked: str


class FetchEsimResponse(BaseModel):
    ok: bool = True
    status: str
    items: list[EsimItem]
    lpaString: str | None = None
    phoneNumber: str | None = None
    memberName: str | None = None
    memberId: str | None = None
    phoneNumberMasked: str | None = None
    memberNameMasked: str | None = None
    memberIdMasked: str | None = None
    simStatus: str | None = None
    esimCount: int | None = None


class DownloadTokenResponse(BaseModel):
    ok: bool = True
    lpaString: str
    ssn: str | None = None
    ssnMasked: str


class ReserveNewEsimResponse(DownloadTokenResponse):
    deliveryStatus: str | None = None
    reservationEndDate: str | None = None
