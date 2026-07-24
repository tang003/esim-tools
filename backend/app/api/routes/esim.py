from fastapi import APIRouter

from app.schemas.esim import (
    DownloadTokenRequest,
    DownloadTokenResponse,
    FetchEsimResponse,
    ReserveNewEsimResponse,
    SessionRequest,
)
from app.services.giffgaff_esim import giffgaff_esim_service

router = APIRouter(prefix="/api/esim", tags=["esim"])


@router.post("/fetch", response_model=FetchEsimResponse)
async def fetch_esim(payload: SessionRequest) -> FetchEsimResponse:
    result = await giffgaff_esim_service.fetch_existing(payload.sessionId)
    return FetchEsimResponse(ok=True, **result)


@router.post("/download-token", response_model=DownloadTokenResponse)
async def download_token(payload: DownloadTokenRequest) -> DownloadTokenResponse:
    result = await giffgaff_esim_service.get_lpa_by_selection(
        payload.sessionId,
        ssn=payload.ssn,
        item_id=payload.itemId,
    )
    return DownloadTokenResponse(ok=True, **result)


@router.post("/reserve-new", response_model=ReserveNewEsimResponse)
async def reserve_new(payload: SessionRequest) -> ReserveNewEsimResponse:
    result = await giffgaff_esim_service.reserve_new_esim(payload.sessionId)
    return ReserveNewEsimResponse(ok=True, **result)
