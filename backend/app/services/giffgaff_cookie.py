import re
from html import unescape
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.giffgaff_client import WEB_UA


def merge_cookie_header(original_cookie: str, set_cookie_values: list[str]) -> str:
    jar: dict[str, str] = {}
    for part in original_cookie.split(";"):
        if "=" in part:
            key, value = part.strip().split("=", 1)
            jar[key] = value
    for set_cookie in set_cookie_values:
        pair = set_cookie.split(";", 1)[0]
        if "=" in pair:
            key, value = pair.strip().split("=", 1)
            jar[key] = value
    return "; ".join(f"{key}={value}" for key, value in jar.items())


class GiffgaffCookieService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def warm_session(self, cookie: str) -> str:
        url = f"{self.settings.giffgaff_web_base}/dashboard"
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    "Cookie": cookie,
                    "User-Agent": WEB_UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": f"{self.settings.giffgaff_id_base}/auth/login/challenge?redirect=%2Fdashboard",
                },
            )
        set_cookie = response.headers.get_list("set-cookie")
        return merge_cookie_header(cookie, set_cookie) if set_cookie else cookie

    async def verify_cookie(self, cookie: str) -> dict[str, Any]:
        warmed_cookie = await self.warm_session(cookie)
        html = await self._fetch_home(warmed_cookie)
        member_id = self._extract_member_id(html)
        token = await self._extract_access_token(warmed_cookie)
        if not member_id and not token:
            raise AppError("COOKIE_INVALID", "Cookie 无效或已过期，请重新登录 giffgaff 后复制", 401)
        return {
            "cookie": warmed_cookie,
            "memberId": member_id,
            "accessToken": token,
            "valid": bool(token),
        }

    async def fetch_csrf(self, cookie: str) -> str | None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(
                f"{self.settings.giffgaff_id_base}/auth/csrf",
                headers={
                    "Accept": "application/json",
                    "Cookie": cookie,
                    "User-Agent": "giffgaff/1332 CFNetwork/1568.300.101 Darwin/24.2.0",
                },
            )
        if response.status_code >= 400:
            return None
        return response.json().get("token")

    async def _fetch_home(self, cookie: str) -> str:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(
                f"{self.settings.giffgaff_web_base}/",
                headers={"Cookie": cookie, "User-Agent": WEB_UA},
            )
        if response.status_code >= 400:
            raise AppError("COOKIE_INVALID", "Cookie 无效或已过期，请重新登录 giffgaff 后复制", 401)
        return response.text

    async def _extract_access_token(self, cookie: str) -> str | None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(
                f"{self.settings.giffgaff_web_base}/auth/user-status",
                headers={
                    "Cookie": cookie,
                    "User-Agent": WEB_UA,
                    "Accept": "application/json",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": f"{self.settings.giffgaff_web_base}/dashboard",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                },
            )
        if response.status_code >= 400:
            return None
        data = response.json()
        token = data.get("accessToken") or data.get("token") or response.headers.get("x-access-token")
        return token if isinstance(token, str) and len(token) > 50 else None

    def _extract_member_id(self, html: str) -> str | None:
        patterns = [
            r'<meta[^>]+name=["\']member-id["\'][^>]+content=["\']([^"\']+)["\']',
            r'data-gg-member=["\']([^"\']+)["\']',
            r'memberId["\s:]+(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return unescape(match.group(1))
        return None


giffgaff_cookie_service = GiffgaffCookieService()
