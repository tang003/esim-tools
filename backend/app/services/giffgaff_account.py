import base64
import hashlib
import json
import re
import secrets
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.giffgaff_cookie import giffgaff_cookie_service, merge_cookie_header
from app.services.giffgaff_esim import giffgaff_esim_service
from app.services.session_store import session_store
from app.utils.mask import mask_middle


WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
)
OAUTH_CLIENT_ID = "e72540d04bfd3651c2f12998d3919a54"
OAUTH_AUTH_HEADER = "Basic ZTcyNTQwZDA0YmZkMzY1MWMyZjEyOTk4ZDM5MTlhNTQ6MDBpVGdhall0OThJYXlpc29kQXdicGN6NmhSS3N0UXZBQS9DRklvd2x1ST0="
OAUTH_REDIRECT_URI = "giffgaff://auth/callback/"


class GiffgaffAccountService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def start_login(self, member_name: str, password: str) -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            csrf = await self._load_login_page(client)
            response = await self._post_login(client, csrf, member_name, password)
            cookie = self._cookie_header(client)

        if response.status_code == 200:
            return await self._create_verified_session(cookie)

        body = self._json_or_empty(response)
        if response.status_code == 401 and body.get("code") == "mfa.required":
            session_id = await session_store.create(
                {
                    "cookie": cookie,
                    "csrfToken": csrf,
                    "loginMemberName": member_name,
                    "loginPassword": password,
                    "loginPending": True,
                }
            )
            return {
                "status": "MFA_REQUIRED",
                "sessionId": session_id,
                "message": "需要输入 giffgaff 发出的邮箱或短信验证码",
                "memberName": member_name,
                "maskedAccount": mask_middle(member_name, 2, 2),
            }

        self._raise_login_error(response, body)

    async def send_login_challenge(self, session_id: str, channel: str) -> dict[str, Any]:
        session = await session_store.get(session_id)
        cookie = session.get("cookie")
        if not cookie:
            raise AppError("LOGIN_SESSION_EXPIRED", "登录会话已过期，请重新输入账号密码", 401)

        csrf = session.get("csrfToken") or await giffgaff_cookie_service.fetch_csrf(cookie)
        xsrf = self._extract_xsrf(cookie)
        method = "text" if channel == "TEXT" else "email"

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.giffgaff_id_base}/auth/v3/mfa/challenge",
                json={"method": method},
                headers={
                    "User-Agent": WEB_UA,
                    "Accept": "application/json",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Content-Type": "application/json",
                    "Origin": self.settings.giffgaff_id_base,
                    "Referer": f"{self.settings.giffgaff_id_base}/auth/login/challenge",
                    "Device": "web",
                    "Cookie": cookie,
                    **({"X-CSRF-TOKEN": csrf} if csrf else {}),
                    **({"X-XSRF-TOKEN": xsrf} if xsrf else {}),
                },
            )

        if response.status_code >= 400:
            raise AppError("LOGIN_MFA_SEND_FAILED", "验证码发送失败，请切换邮箱或短信后重试", response.status_code)

        set_cookie = response.headers.get_list("set-cookie")
        updated_cookie = merge_cookie_header(cookie, set_cookie) if set_cookie else cookie
        await session_store.update(
            session_id,
            {
                "cookie": updated_cookie,
                "csrfToken": csrf,
                "loginMfaChannel": channel,
                "loginMfaSent": True,
            },
        )
        return {
            "message": "验证码已发送，请查收后输入",
            "channel": channel,
        }

    async def finish_login(self, session_id: str, code: str, remember_browser: bool) -> dict[str, Any]:
        session = await session_store.get(session_id)
        member_name = session.get("loginMemberName")
        password = session.get("loginPassword")
        csrf = session.get("csrfToken")
        cookie = session.get("cookie")
        if not member_name or not password or not csrf or not cookie:
            raise AppError("LOGIN_SESSION_EXPIRED", "登录会话已过期，请重新输入账号密码", 401)

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            self._load_cookie_header(client, cookie)
            response = await self._post_login(
                client,
                csrf,
                member_name,
                password,
                mfa_code=code,
                remember_browser=remember_browser,
            )
            new_cookie = self._merge_response_cookies(cookie, client, response)

        if response.status_code == 200:
            result = await self._create_verified_session(new_cookie, existing_session_id=session_id)
            await session_store.update(session_id, {"loginPassword": "", "loginPending": False})
            return result

        body = self._json_or_empty(response)
        if response.status_code == 400:
            raise AppError("MFA_CODE_INVALID", "验证码不正确，请重新输入", 400)
        self._raise_login_error(response, body)

    async def _create_verified_session(
        self,
        cookie: str,
        *,
        existing_session_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            verified = await giffgaff_cookie_service.verify_cookie(cookie)
        except AppError:
            token_data = await self._exchange_cookie_for_token(cookie)
            verified = {
                "cookie": await giffgaff_cookie_service.warm_session(cookie),
                "memberId": None,
                "accessToken": token_data["access_token"],
                "refreshToken": token_data.get("refresh_token"),
                "valid": True,
            }
        if not verified.get("accessToken"):
            token_data = await self._exchange_cookie_for_token(verified.get("cookie") or cookie)
            verified["accessToken"] = token_data["access_token"]
            verified["refreshToken"] = token_data.get("refresh_token")
            verified["valid"] = True
        payload = {
            **verified,
            "loginPending": False,
            "loginPassword": "",
        }
        session_id = existing_session_id or await session_store.create(payload)
        if existing_session_id:
            await session_store.update(existing_session_id, payload)

        masked_account = mask_middle(verified.get("memberId"), 2, 2)
        member_name = None
        member_id = verified.get("memberId")
        phone_number = None
        phone_masked = None
        if verified.get("valid"):
            try:
                profile = await giffgaff_esim_service.get_member_profile(session_id)
                member_name = profile.get("memberName")
                member_id = profile.get("memberId") or member_id
                phone_number = profile.get("phoneNumber")
                masked_account = profile.get("memberNameMasked") or masked_account
                phone_masked = profile.get("phoneNumberMasked")
            except Exception:
                pass

        return {
            "status": "READY",
            "sessionId": session_id,
            "message": "账号登录成功",
            "memberName": member_name,
            "memberId": member_id,
            "phoneNumber": phone_number,
            "maskedAccount": masked_account,
            "phoneNumberMasked": phone_masked,
        }

    async def _exchange_cookie_for_token(self, cookie: str) -> dict[str, Any]:
        verifier = self._base64_url(secrets.token_bytes(32))
        challenge = self._base64_url(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)
        async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
            authorize = await client.get(
                f"{self.settings.giffgaff_id_base}/auth/oauth/authorize",
                params={
                    "client_id": OAUTH_CLIENT_ID,
                    "state": state,
                    "response_type": "code",
                    "scope": "read",
                    "code_challenge_method": "S256",
                    "code_challenge": challenge,
                    "redirect_uri": OAUTH_REDIRECT_URI,
                },
                headers={
                    "Cookie": cookie,
                    "User-Agent": WEB_UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": f"{self.settings.giffgaff_web_base}/dashboard",
                },
            )
            callback_url = authorize.headers.get("location") or ""
            if not callback_url.startswith("giffgaff://"):
                match = re.search(r"giffgaff://auth/callback/\?[^\"'\s<>]+", authorize.text)
                callback_url = match.group(0) if match else callback_url
            parsed = parse_qs(urlparse(callback_url).query)
            code = (parsed.get("code") or [""])[0]
            returned_state = (parsed.get("state") or [""])[0]
            if not code or returned_state != state:
                raise AppError("TOKEN_EXCHANGE_CODE_FAILED", "登录成功，但未能获取 giffgaff 授权码", 502)

            token = await client.post(
                f"{self.settings.giffgaff_id_base}/auth/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "state": state,
                    "redirect_uri": OAUTH_REDIRECT_URI,
                    "code_verifier": verifier,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Authorization": OAUTH_AUTH_HEADER,
                    "Accept": "application/json",
                    "User-Agent": "giffgaff/1360 CFNetwork/3860.400.51 Darwin/25.3.0",
                },
            )
        if token.status_code >= 400:
            raise AppError("TOKEN_EXCHANGE_FAILED", "登录成功，但换取 giffgaff 访问令牌失败", token.status_code)
        data = token.json()
        if not data.get("access_token"):
            raise AppError("TOKEN_MISSING", "登录成功，但 giffgaff 未返回访问令牌", 502)
        return data

    def _base64_url(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    async def _load_login_page(self, client: httpx.AsyncClient) -> str:
        response = await client.get(
            f"{self.settings.giffgaff_web_base}/auth/login",
            headers={
                "User-Agent": WEB_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
            },
        )
        if response.status_code >= 400:
            raise AppError("LOGIN_PAGE_FAILED", "无法打开 giffgaff 登录页，请稍后重试", 502)
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            response.text,
        )
        if not match:
            raise AppError("CSRF_MISSING", "未获取到登录安全令牌，请稍后重试", 502)
        data = json.loads(match.group(1))
        return data["props"]["pageProps"]["csrfToken"]["token"]

    async def _post_login(
        self,
        client: httpx.AsyncClient,
        csrf: str,
        member_name: str,
        password: str,
        *,
        mfa_code: str | None = None,
        remember_browser: bool | None = None,
    ) -> httpx.Response:
        body: dict[str, Any] = {"memberName": member_name.strip(), "password": password}
        if mfa_code is not None and remember_browser is not None:
            body["mfaCode"] = mfa_code
            body["rememberBrowser"] = remember_browser
        return await client.post(
            f"{self.settings.giffgaff_id_base}/auth/login",
            json=body,
            headers={
                "User-Agent": WEB_UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Content-Type": "application/json",
                "Origin": self.settings.giffgaff_web_base,
                "Referer": f"{self.settings.giffgaff_web_base}/auth/login",
                "X-CSRF-TOKEN": csrf,
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
        )

    def _cookie_header(self, client: httpx.AsyncClient) -> str:
        parts = []
        for cookie in client.cookies.jar:
            parts.append(f"{cookie.name}={cookie.value}")
        return "; ".join(parts)

    def _merge_response_cookies(
        self,
        original_cookie: str,
        client: httpx.AsyncClient,
        response: httpx.Response,
    ) -> str:
        values = response.headers.get_list("set-cookie")
        values.extend(f"{cookie.name}={cookie.value}" for cookie in client.cookies.jar)
        return merge_cookie_header(original_cookie, values)

    def _load_cookie_header(self, client: httpx.AsyncClient, cookie_header: str) -> None:
        for part in cookie_header.split(";"):
            if "=" not in part:
                continue
            key, value = part.strip().split("=", 1)
            client.cookies.set(key, value, domain=".giffgaff.com")

    def _extract_xsrf(self, cookie_header: str) -> str | None:
        match = re.search(r"XSRF-TOKEN=([^;]+)", cookie_header)
        return match.group(1) if match else None

    def _json_or_empty(self, response: httpx.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {}

    def _raise_login_error(self, response: httpx.Response, body: dict[str, Any]) -> None:
        if response.status_code == 403 and "Incapsula" in response.text:
            raise AppError(
                "GIFFGAFF_WAF_BLOCKED",
                "giffgaff 拦截了服务端账号登录请求，请稍后重试或改用 Cookie/OAuth 登录",
                403,
            )
        code = body.get("code") or body.get("error") or "LOGIN_FAILED"
        if code == "bad.credentials":
            raise AppError("BAD_CREDENTIALS", "账号或密码不正确，请检查后重试", 400)
        if code == "user.locked":
            raise AppError("USER_LOCKED", "账号已被锁定，请稍后或联系 giffgaff", 423)
        if code == "user.disabled":
            raise AppError("USER_DISABLED", "账号已被禁用，请联系 giffgaff", 403)
        if code == "credentials.expired":
            raise AppError("CREDENTIALS_EXPIRED", "密码已过期，请先在 giffgaff 官网更新密码", 400)
        raise AppError("LOGIN_FAILED", body.get("message") or "登录失败，请稍后重试", response.status_code)


giffgaff_account_service = GiffgaffAccountService()
