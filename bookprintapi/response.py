"""BookPrintAPI SDK — Response Parser

master_대비_변경사항.md § 1.2 / § 7.1 / § 8.1 의 응답 shape 변경 반영:
- 6필드 실패 응답 (errorCode / fieldErrors 추가)
- 주문 목록 응답 평탄화 (data: [...], pagination 최상위)
- PageMeta 통합 (data.pageMeta)
"""

from __future__ import annotations
from typing import Any

from .exceptions import FieldError


class ResponseParser:
    """API 응답 파싱 유틸리티"""

    def __init__(self, body: dict | None):
        self._body = body or {}

    @property
    def raw(self) -> dict:
        return self._body

    @property
    def success(self) -> bool:
        return bool(self._body.get("success"))

    def get_data(self) -> Any:
        return self._body.get("data", self._body)

    def get_dict(self) -> dict:
        d = self.get_data()
        return d if isinstance(d, dict) else {}

    def get_list(self) -> list:
        d = self.get_data()
        # 평탄화 응답: data: [...]
        if isinstance(d, list):
            return d
        # 구버전 호환: data: {orders|items|books|...: [...]}
        if isinstance(d, dict):
            for key in ("orders", "items", "books", "templates", "photos"):
                v = d.get(key)
                if isinstance(v, list):
                    return v
        return []

    def get_pagination(self) -> dict:
        """pagination 메타. 평탄화 후 최상위에 위치, 구버전은 data.pagination."""
        top = self._body.get("pagination")
        if isinstance(top, dict):
            return top
        d = self.get_data()
        if isinstance(d, dict):
            inner = d.get("pagination")
            if isinstance(inner, dict):
                return inner
        return {}

    def get_message(self) -> str:
        return self._body.get("message", "")

    # --- 신규: 6필드 응답 shape ---

    def get_error_code(self) -> str | None:
        return self._body.get("errorCode") or self._body.get("error_code")

    def get_errors(self) -> list[str]:
        v = self._body.get("errors")
        return list(v) if isinstance(v, list) else []

    def get_field_errors(self) -> list[FieldError]:
        v = self._body.get("fieldErrors") or self._body.get("field_errors") or []
        return [FieldError.from_dict(fe) if isinstance(fe, dict) else fe for fe in v]

    def get_field_error(self, field: str) -> FieldError | None:
        for fe in self.get_field_errors():
            if fe.field == field:
                return fe
        return None

    def get_page_meta(self) -> dict:
        """data.pageMeta 객체 (책 생성·내지·표지·finalize·PDF 응답)"""
        d = self.get_dict()
        meta = d.get("pageMeta")
        return meta if isinstance(meta, dict) else {}

    def to_flat_list_response(self) -> dict:
        """list 응답을 신·구 envelope 둘 다에서 동일한 형태로 평탄화.

        BookPrintAPI v1 (commit 6fbf346, 2026-05-11) 이후 list 응답이
        ``{ data: [...], pagination: {...} }`` 평탄 envelope으로 통일됨.
        본 헬퍼는 옛 ``{ data: { books|orders|items|...: [...], pagination } }``
        형태도 동일하게 평탄화해서 반환 — 사용자 코드는 envelope 통일 전후
        모두에서 같은 접근 패턴 (``response["data"]``, ``response["pagination"]``) 사용 가능.

        Returns:
            ``{ success, data: list, pagination: dict, message }`` 형태의 dict.
            ``totalCount`` (구 photos 응답) 도 자동으로 ``pagination.total`` 로 흡수.
        """
        out: dict[str, Any] = {
            "success": self.success,
            "data": self.get_list(),
            "message": self.get_message(),
        }
        pagination = self.get_pagination()
        # 구 photos 응답의 totalCount 흡수
        d = self.get_data()
        if isinstance(d, dict) and "totalCount" in d and "total" not in pagination:
            pagination = {**pagination, "total": d["totalCount"]}
        if pagination:
            out["pagination"] = pagination
        return out
