from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.giffgaff_client import giffgaff_client
from app.services.session_store import session_store
from app.utils.mask import mask_middle, mask_name


GET_MEMBER_PROFILE = """query getMemberProfileAndSim {
  memberProfile {
    id
    memberName
    __typename
  }
  sim {
    phoneNumber
    status
    __typename
  }
}"""

GET_ESIMS = """query getESims($deliveryStatus: ESimDeliveryStatus!) {
  eSims(deliveryStatus: $deliveryStatus) {
    ssn
    __typename
  }
}"""

GET_DOWNLOAD_TOKEN = """query eSimDownloadToken($ssn: String!) {
  eSimDownloadToken(ssn: $ssn) {
    id
    host
    matchingId
    lpaString
    __typename
  }
}"""

RESERVE_ESIM = """mutation reserveESim($input: ESimReservationInput!) {
  reserveESim(input: $input) {
    id
    memberId
    reservationEndDate
    status
    esim {
      ssn
      activationCode
      deliveryStatus
      __typename
    }
    __typename
  }
}"""


class GiffgaffEsimService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def get_member_profile(self, session_id: str) -> dict[str, Any]:
        session = await session_store.get(session_id)
        data = await self._graphql(
            session,
            query=GET_MEMBER_PROFILE,
            operation_name="getMemberProfileAndSim",
        )
        member = data.get("memberProfile") or {}
        sim = data.get("sim") or {}
        await session_store.update(
            session_id,
            {
                "memberId": member.get("id"),
                "memberName": member.get("memberName"),
                "phoneNumber": sim.get("phoneNumber"),
                "simStatus": sim.get("status"),
            },
        )
        return {
            "memberId": member.get("id"),
            "memberName": member.get("memberName"),
            "phoneNumber": sim.get("phoneNumber"),
            "memberNameMasked": mask_name(member.get("memberName")),
            "phoneNumberMasked": mask_middle(sim.get("phoneNumber"), 3, 4),
            "simStatus": sim.get("status"),
        }

    async def fetch_existing(self, session_id: str) -> dict[str, Any]:
        session = await session_store.get(session_id)
        data = await self._graphql(
            session,
            query=GET_ESIMS,
            variables={"deliveryStatus": "DOWNLOADABLE"},
            operation_name="getESims",
        )
        esims = data.get("eSims") or []
        if not esims:
            raise AppError("NO_DOWNLOADABLE_ESIM", "未发现可下载的 eSIM", 404)

        candidates = [item.get("ssn") for item in esims if item.get("ssn")]
        await session_store.update(session_id, {"candidateSsns": candidates})
        current = await session_store.get(session_id)
        items = [
            {"itemId": str(index), "ssn": ssn, "ssnMasked": mask_middle(ssn)}
            for index, ssn in enumerate(candidates)
        ]

        if len(candidates) == 1:
            lpa = await self.get_lpa(session_id, candidates[0])
            return {
                "status": "READY",
                "items": items,
                "lpaString": lpa["lpaString"],
                "phoneNumber": current.get("phoneNumber"),
                "memberName": current.get("memberName"),
                "memberId": current.get("memberId"),
                "phoneNumberMasked": mask_middle(current.get("phoneNumber"), 3, 4),
                "memberNameMasked": mask_name(current.get("memberName")),
                "memberIdMasked": mask_middle(current.get("memberId"), 2, 2),
                "simStatus": current.get("simStatus"),
                "esimCount": len(candidates),
            }

        return {
            "status": "NEED_SELECTION",
            "items": items,
            "lpaString": None,
            "phoneNumber": current.get("phoneNumber"),
            "memberName": current.get("memberName"),
            "memberId": current.get("memberId"),
            "phoneNumberMasked": mask_middle(current.get("phoneNumber"), 3, 4),
            "memberNameMasked": mask_name(current.get("memberName")),
            "memberIdMasked": mask_middle(current.get("memberId"), 2, 2),
            "simStatus": current.get("simStatus"),
            "esimCount": len(candidates),
        }

    async def get_lpa_by_selection(
        self,
        session_id: str,
        *,
        ssn: str | None = None,
        item_id: str | None = None,
    ) -> dict[str, str]:
        session = await session_store.get(session_id)
        resolved_ssn = ssn
        if not resolved_ssn and item_id is not None:
            candidates = session.get("candidateSsns") or []
            try:
                resolved_ssn = candidates[int(item_id)]
            except (ValueError, IndexError):
                raise AppError("SSN_NOT_FOUND", "选择的 eSIM 不存在", 404)
        if not resolved_ssn:
            raise AppError("SSN_REQUIRED", "请选择要获取的 eSIM", 400)
        return await self.get_lpa(session_id, resolved_ssn)

    async def get_lpa(self, session_id: str, ssn: str) -> dict[str, str]:
        session = await session_store.get(session_id)
        data = await self._graphql(
            session,
            query=GET_DOWNLOAD_TOKEN,
            variables={"ssn": ssn},
            operation_name="eSimDownloadToken",
        )
        token = data.get("eSimDownloadToken") or {}
        lpa = token.get("lpaString")
        if not lpa:
            raise AppError("LPA_FETCH_FAILED", "未获取到 eSIM 下载信息，请稍后重试", 502)
        return {"lpaString": lpa, "ssn": ssn, "ssnMasked": mask_middle(ssn)}

    async def reserve_new_esim(self, session_id: str) -> dict[str, str]:
        session = await session_store.get(session_id)
        if not session.get("mfaSignature"):
            raise AppError("MFA_REQUIRED", "申请新的 eSIM 需要先完成验证码确认", 401)

        member_id = session.get("memberId")
        if not member_id:
            profile = await self.get_member_profile(session_id)
            current = await session_store.get(session_id)
            member_id = current.get("memberId") or profile.get("memberId")
        if not member_id:
            raise AppError("MEMBER_ID_MISSING", "未获取到会员 ID，无法申请新的 eSIM", 400)

        data = await self._graphql(
            session,
            query=RESERVE_ESIM,
            variables={"input": {"memberId": member_id, "userIntent": "SWITCH"}},
            operation_name="reserveESim",
        )
        reservation = data.get("reserveESim") or {}
        esim = reservation.get("esim") or {}
        ssn = esim.get("ssn")
        if not ssn:
            raise AppError("RESERVE_ESIM_FAILED", "申请新的 eSIM 失败，请稍后重试", 502)

        await session_store.update(
            session_id,
            {
                "candidateSsns": [ssn],
                "lastReservedSsn": ssn,
                "lastActivationCode": esim.get("activationCode"),
                "lastReservationEndDate": reservation.get("reservationEndDate"),
            },
        )
        lpa = await self.get_lpa(session_id, ssn)
        return {
            **lpa,
            "deliveryStatus": esim.get("deliveryStatus") or reservation.get("status") or "",
            "reservationEndDate": reservation.get("reservationEndDate") or "",
        }

    async def _graphql(
        self,
        session: dict[str, Any],
        *,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str,
    ) -> dict[str, Any]:
        access_token = session.get("accessToken")
        if not access_token:
            raise AppError("COOKIE_INCOMPLETE", "Cookie 已验证，但缺少可查询 eSIM 的访问令牌", 401)

        headers = giffgaff_client.app_headers(access_token)
        if session.get("mfaSignature"):
            headers["X-MFA-Signature"] = session["mfaSignature"]
            headers["x-mfa-signature"] = session["mfaSignature"]

        response = await giffgaff_client.request_json(
            "POST",
            f"{self.settings.giffgaff_public_api_base}/gateway/graphql",
            headers=headers,
            json_body={
                "query": query,
                "variables": variables or {},
                "operationName": operation_name,
            },
        )

        if response.get("errors"):
            message = str(response["errors"][0].get("message") or response["errors"][0])
            lowered = message.lower()
            if "unauthorized" in lowered or "invalid_token" in lowered:
                raise AppError("MFA_REQUIRED", "giffgaff 要求二次验证", 401)
            if "ssn" in lowered and "not" in lowered:
                raise AppError("SSN_NOT_FOUND", "选择的 eSIM 不存在", 404)
            if "500" in lowered or "internal" in lowered:
                raise AppError("GIFFGAFF_UPSTREAM_ERROR", "giffgaff 上游服务暂时不可用", 502)
            raise AppError("GIFFGAFF_GRAPHQL_ERROR", message, 422)

        return response.get("data") or {}


giffgaff_esim_service = GiffgaffEsimService()
