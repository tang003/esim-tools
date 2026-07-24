import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError


APP_UA = "giffgaff/1332 CFNetwork/1568.300.101 Darwin/24.2.0"
WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class GiffgaffClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def app_headers(self, access_token: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": APP_UA,
            "Origin": self.settings.giffgaff_public_api_base,
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "x-gg-app-device-manufacturer": "Apple",
            "x-gg-app-os": "iOS",
            "x-gg-app-version": "17.46.11",
            "x-gg-app-build-number": "1332",
            "x-gg-app-os-version": "18.2",
            "apollographql-client-name": "iOS 18.2",
            "apollographql-client-version": "17.46.11 1332",
            "x-gg-app-bundle-version": "v0",
            "x-gg-app-device-model": "iPhone SE",
            "x-gg-app-device-id": "iPhone12,8",
            "x-request-id": str(uuid.uuid4()),
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
        timeout: float = 30.0,
    ) -> Any:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            try:
                response = await client.request(method, url, headers=headers, json=json_body)
            except httpx.HTTPError as exc:
                raise AppError("GIFFGAFF_NETWORK_ERROR", "连接 giffgaff 失败，请稍后重试", 502) from exc

        if response.status_code in {401, 403}:
            raise AppError("MFA_REQUIRED", "giffgaff 要求二次验证", 401)

        if response.status_code >= 500:
            raise AppError("GIFFGAFF_UPSTREAM_ERROR", "giffgaff 上游服务暂时不可用", 502)

        if response.status_code >= 400:
            raise AppError("GIFFGAFF_REQUEST_FAILED", "giffgaff 请求失败，请检查登录状态", response.status_code)

        try:
            return response.json()
        except ValueError as exc:
            raise AppError("GIFFGAFF_BAD_RESPONSE", "giffgaff 返回格式异常", 502) from exc


giffgaff_client = GiffgaffClient()

