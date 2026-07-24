from fastapi import APIRouter

from app.schemas.common import OkResponse
from app.schemas.mfa import SendMfaRequest, SendMfaResponse, VerifyMfaRequest
from app.services.giffgaff_mfa import giffgaff_mfa_service

router = APIRouter(prefix="/api/mfa", tags=["mfa"])


@router.post("/send", response_model=SendMfaResponse)
async def send_mfa(payload: SendMfaRequest) -> SendMfaResponse:
    ref = await giffgaff_mfa_service.send_challenge(payload.sessionId, payload.channel)
    return SendMfaResponse(ref=ref, message="验证码已发送")


@router.post("/verify", response_model=OkResponse)
async def verify_mfa(payload: VerifyMfaRequest) -> OkResponse:
    await giffgaff_mfa_service.validate_code(payload.sessionId, payload.ref, payload.code)
    return OkResponse()

