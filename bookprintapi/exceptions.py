"""BookPrintAPI SDK — Exceptions"""

from __future__ import annotations
from typing import Any


class FieldError:
    """fieldErrors[] 항목 — master_대비_변경사항.md § 1.3"""

    __slots__ = ("field", "message", "current_value", "required_value", "constraint")

    def __init__(
        self,
        field: str,
        message: str = "",
        *,
        current_value: Any = None,
        required_value: Any = None,
        constraint: str | None = None,
    ):
        self.field = field
        self.message = message
        self.current_value = current_value
        self.required_value = required_value
        self.constraint = constraint

    @classmethod
    def from_dict(cls, d: dict) -> "FieldError":
        return cls(
            field=d.get("field", ""),
            message=d.get("message", ""),
            current_value=d.get("currentValue"),
            required_value=d.get("requiredValue"),
            constraint=d.get("constraint"),
        )

    def to_dict(self) -> dict:
        out: dict[str, Any] = {"field": self.field, "message": self.message}
        if self.current_value is not None:
            out["currentValue"] = self.current_value
        if self.required_value is not None:
            out["requiredValue"] = self.required_value
        if self.constraint is not None:
            out["constraint"] = self.constraint
        return out

    def __repr__(self) -> str:
        return f"FieldError(field={self.field!r}, constraint={self.constraint!r})"


class ApiError(Exception):
    """API 요청 실패 — 6필드 응답 shape 대응

    master_대비_변경사항.md § 1.2 의 표준 shape:
        {success, errorCode, message, data, errors[], fieldErrors[]}

    Attributes:
        message: HTTP 상태 영어 라벨 (예: "Bad Request")
        status_code: HTTP 상태 코드
        error_code: ERR_* 식별자 (예: "ERR_INSUFFICIENT_PAGES")
        details: errors[] — 사용자 표시용 한글 메시지 배열
        field_errors: FieldError 리스트
        data: data 필드 (일반적으로 None, ERR_INSUFFICIENT_CREDIT 등 일부 케이스에서 진단 객체)
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        details: list | None = None,
        field_errors: list[FieldError] | None = None,
        data: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []
        self.field_errors: list[FieldError] = field_errors or []
        self.data = data

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.insert(0, f"[{self.status_code}]")
        if self.error_code:
            parts.append(f"({self.error_code})")
        return " ".join(parts)

    def field_error(self, name: str) -> FieldError | None:
        """field 이름으로 FieldError 찾기. 없으면 None."""
        for fe in self.field_errors:
            if fe.field == name:
                return fe
        return None

    def user_message(self) -> str:
        """사용자에게 표시할 한글 메시지 — errors[0] 또는 message fallback."""
        if self.details:
            return self.details[0]
        return self.message

    @classmethod
    def from_response(cls, response) -> "ApiError":
        try:
            body = response.json() or {}
        except Exception:
            return cls(
                message=f"HTTP {response.status_code}: {response.reason}",
                status_code=response.status_code,
            )

        # camelCase 우선, snake_case fallback (구버전 응답 호환)
        error_code = body.get("errorCode") or body.get("error_code")
        message = body.get("message", "") or response.reason
        errors = body.get("errors", []) or []

        raw_field_errors = body.get("fieldErrors", []) or body.get("field_errors", []) or []
        field_errors = [
            FieldError.from_dict(fe) if isinstance(fe, dict) else fe
            for fe in raw_field_errors
        ]

        return cls(
            message=message,
            status_code=response.status_code,
            error_code=error_code,
            details=errors,
            field_errors=field_errors,
            data=body.get("data"),
        )


class ValidationError(Exception):
    """요청 파라미터 검증 실패 (SDK 클라이언트 사이드)"""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field
