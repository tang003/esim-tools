from fastapi import APIRouter

from app.schemas.common import OkResponse
from app.services.session_store import session_store

router = APIRouter(prefix="/api/session", tags=["session"])


@router.delete("/{session_id}", response_model=OkResponse)
async def clear_session(session_id: str) -> OkResponse:
    await session_store.delete(session_id)
    return OkResponse()
