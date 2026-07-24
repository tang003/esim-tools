import re

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.giffgaff_client import APP_UA, WEB_UA
from app.services.giffgaff_cookie import giffgaff_cookie_service
from app.services.session_store import session_store


class GiffgaffMfaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_challenge(self, session_id: str, channel: str) -> str:
        session = await session_store.get(session_id)
        cookie = session.get("cookie")
        if not cookie:
            raise AppError("SESSION_INVALID", "会话缺少 Cookie，请重新验证", 401)

        csrf = session.get("csrfToken") or await giffgaff_cookie_service.fetch_csrf(cookie)
        await session_store.update(session_id, {"csrfToken": csrf})
        xsrf = self._extract_xsrf(cookie)
        method = "text" if channel == "TEXT" else "email"

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.giffgaff_id_base}/auth/v3/mfa/challenge",
                json={"method": method},
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": WEB_UA,
                    "Origin": self.settings.giffgaff_id_base,
                    "Referer": f"{self.settings.giffgaff_id_base}/auth/login/challenge",
                    "Device": "web",
                    "Cookie": cookie,
                    **({"x-csrf-token": csrf} if csrf else {}),
                    **({"x-xsrf-token": xsrf} if xsrf else {}),
                },
            )

        if response.status_code >= 400:
            ref = await self._send_challenge_v4(session, channel)
        else:
            ref = response.json().get("ref")

        if not ref:
            raise AppError("MFA_SEND_FAILED", "验证码发送失败，请稍后重试", 502)

        await session_store.update(session_id, {"mfaRef": ref})
        return ref

    async def validate_code(self, session_id: str, ref: str, code: str) -> None:
        session = await session_store.get(session_id)
        access_token = session.get("accessToken")
        cookie = session.get("cookie")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": APP_UA,
            **({"Authorization": f"Bearer {access_token}"} if access_token else {}),
            **({"Cookie": cookie} if cookie and not access_token else {}),
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.giffgaff_id_base}/v4/mfa/validation",
                json={"ref": ref, "code": code},
                headers=headers,
            )

        if response.status_code == 400:
            body = response.text
            if re.search(r"expired|invalid.*ref|ref.*invalid|not.?found", body, re.I):
                raise AppError("MFA_REF_EXPIRED", "验证码已过期，请重新发送", 410)
            raise AppError("MFA_CODE_INVALID", "验证码不正确，请重新输入", 400)
        if response.status_code >= 400:
            raise AppError("MFA_VERIFY_FAILED", "验证码验证失败，请稍后重试", response.status_code)

        signature = response.json().get("signature")
        if not signature:
            raise AppError("MFA_SIGNATURE_MISSING", "未获取到验证签名，请重新验证", 502)
        await session_store.update(session_id, {"mfaSignature": signature, "mfaRef": ref})

    async def _send_challenge_v4(self, session: dict, channel: str) -> str | None:
        access_token = session.get("accessToken")
        if not access_token:
            return None
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.giffgaff_id_base}/v4/mfa/challenge/me",
                json={"source": "esim", "preferredChannels": [channel]},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": APP_UA,
                    "Authorization": f"Bearer {access_token}",
                    **({"Cookie": session.get("cookie")} if session.get("cookie") else {}),
                },
            )
        if response.status_code >= 400:
            return None
        return response.json().get("ref")

    def _extract_xsrf(self, cookie: str) -> str | None:
        match = re.search(r"XSRF-TOKEN=([^;]+)", cookie)
        return match.group(1) if match else None


giffgaff_mfa_service = GiffgaffMfaService()

