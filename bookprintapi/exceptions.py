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


class HelperStage:
    """SweetbookHelperError.stage 값 — 11_sdk_helpers_design.md § 3.2

    헬퍼가 다단계 호출 중 어느 단계에서 실패했는지 식별. 문자열 상수.
    """

    # 입력 검증 (호출 전)
    VALIDATION = "VALIDATION"

    # createBookFromTemplate 단계
    BOOK_CREATE = "BOOK_CREATE"
    COVER_CREATE = "COVER_CREATE"
    CONTENT_INSERT = "CONTENT_INSERT"  # contentIndex 와 함께 사용
    BOOK_FINALIZE = "BOOK_FINALIZE"

    # uploadPdfAndOrder 단계
    PDF_UPLOAD_COVER = "PDF_UPLOAD_COVER"
    PDF_UPLOAD_CONTENTS = "PDF_UPLOAD_CONTENTS"
    ORDER_ESTIMATE = "ORDER_ESTIMATE"
    ORDER_CREATE = "ORDER_CREATE"


class HelperErrorCodes:
    """헬퍼 임시 errorCode (11_sdk_helpers_design.md § 3.4)

    C03 에러코드 체계 확정 시 본 코드들을 표준 errorCode 로 매핑할 예정.
    """

    BOOK_CREATE_FAILED = "SDK_HLPR_BOOK_CREATE_FAILED"
    COVER_CREATE_FAILED = "SDK_HLPR_COVER_CREATE_FAILED"
    CONTENT_INSERT_FAILED = "SDK_HLPR_CONTENT_INSERT_FAILED"
    PDF_UPLOAD_FAILED = "SDK_HLPR_PDF_UPLOAD_FAILED"
    FINALIZE_FAILED = "SDK_HLPR_FINALIZE_FAILED"
    CREDIT_INSUFFICIENT = "SDK_HLPR_CREDIT_INSUFFICIENT"
    ORDER_ESTIMATE_FAILED = "SDK_HLPR_ORDER_ESTIMATE_FAILED"
    ORDER_CREATE_FAILED = "SDK_HLPR_ORDER_CREATE_FAILED"
    VALIDATION = "SDK_HLPR_VALIDATION"


class SweetbookHelperError(Exception):
    """헬퍼 다단계 호출 중 발생한 실패 — 11_sdk_helpers_design.md § 3

    Attributes:
        stage: HelperStage 상수 — 어느 단계에서 실패했는지
        code: HelperErrorCodes 상수 — SDK 헬퍼 임시 errorCode
        book_uid: BOOK_CREATE 성공 후 단계부터 채워짐. 파트너가 cleanup 결정에 사용
        order_uid: uploadPdfAndOrder 의 ORDER_CREATE 성공 후만 채워짐
        partial: 단계별 부분 성공 정보 dict
        cause: 원 예외 (대부분 ApiError, 가끔 ValueError 등)
        content_index: stage=CONTENT_INSERT 일 때 어느 페이지인지 (0-based)
    """

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        code: str,
        book_uid: str | None = None,
        order_uid: str | None = None,
        partial: dict | None = None,
        cause: Exception | None = None,
        content_index: int | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.code = code
        self.book_uid = book_uid
        self.order_uid = order_uid
        self.partial: dict = partial or {}
        self.cause = cause
        self.content_index = content_index

    def __str__(self) -> str:
        parts = [f"[{self.stage}]"]
        if self.content_index is not None:
            parts[-1] = f"[{self.stage}#{self.content_index}]"
        parts.append(self.message)
        if self.code:
            parts.append(f"({self.code})")
        if self.book_uid:
            parts.append(f"bookUid={self.book_uid}")
        return " ".join(parts)

    def user_message(self) -> str:
        """사용자 표시용. cause 가 ApiError 면 그쪽 user_message 위임."""
        if isinstance(self.cause, ApiError):
            return self.cause.user_message()
        return self.message
