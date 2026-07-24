from fastapi import APIRouter

from app.utils.service_time import get_uk_service_time

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health() -> dict:
    return {"ok": True, "serviceTime": get_uk_service_time()}

