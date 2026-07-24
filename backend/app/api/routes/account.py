from fastapi import APIRouter

from app.schemas.login import (
    AccountLoginChallengeRequest,
    AccountLoginChallengeResponse,
    AccountLoginMfaRequest,
    AccountLoginRequest,
    AccountLoginResponse,
)
from app.services.giffgaff_account import giffgaff_account_service

router = APIRouter(prefix="/api/account", tags=["account"])


@router.post("/login", response_model=AccountLoginResponse)
async def account_login(payload: AccountLoginRequest) -> AccountLoginResponse:
    result = await giffgaff_account_service.start_login(payload.memberName, payload.password)
    return AccountLoginResponse(ok=True, **result)


@router.post("/login/challenge", response_model=AccountLoginChallengeResponse)
async def account_login_challenge(payload: AccountLoginChallengeRequest) -> AccountLoginChallengeResponse:
    result = await giffgaff_account_service.send_login_challenge(payload.sessionId, payload.channel)
    return AccountLoginChallengeResponse(ok=True, **result)


@router.post("/login/mfa", response_model=AccountLoginResponse)
async def account_login_mfa(payload: AccountLoginMfaRequest) -> AccountLoginResponse:
    result = await giffgaff_account_service.finish_login(
        payload.sessionId,
        payload.code,
        payload.rememberBrowser,
    )
    return AccountLoginResponse(ok=True, **result)
