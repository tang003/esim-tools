import json
import secrets
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.errors import AppError


class SessionStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"gg:session:{session_id}"

    async def create(self, payload: dict[str, Any]) -> str:
        session_id = secrets.token_urlsafe(24)
        await self.redis.setex(
            self._key(session_id),
            self.settings.session_ttl_seconds,
            json.dumps(payload),
        )
        return session_id

    async def get(self, session_id: str) -> dict[str, Any]:
        raw = await self.redis.get(self._key(session_id))
        if not raw:
            raise AppError("SESSION_EXPIRED", "会话已过期，请重新验证 Cookie", 401)
        await self.redis.expire(self._key(session_id), self.settings.session_ttl_seconds)
        return json.loads(raw)

    async def update(self, session_id: str, values: dict[str, Any]) -> dict[str, Any]:
        payload = await self.get(session_id)
        payload.update({key: value for key, value in values.items() if value is not None})
        await self.redis.setex(
            self._key(session_id),
            self.settings.session_ttl_seconds,
            json.dumps(payload),
        )
        return payload

    async def delete(self, session_id: str) -> None:
        await self.redis.delete(self._key(session_id))


session_store = SessionStore()

