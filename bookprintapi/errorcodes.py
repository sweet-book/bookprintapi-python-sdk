"""BookPrintAPI SDK — errorCode / constraint 카탈로그

서버의 master_대비_변경사항.md § 2 카탈로그와 1:1 정합. 응답의 `errorCode`
필드를 분기할 때 문자열 리터럴 대신 본 모듈 상수를 사용 권장.
"""

from __future__ import annotations


class ErrorCodes:
    """24종 errorCode 카탈로그 (Generic 8 + Specific 16)"""

    # --- Generic (HTTP 상태 자동 주입) ---
    VALIDATION_FAILED = "ERR_VALIDATION_FAILED"          # 400
    MALFORMED_REQUEST = "ERR_MALFORMED_REQUEST"          # 400
    UNAUTHORIZED = "ERR_UNAUTHORIZED"                    # 401
    FORBIDDEN = "ERR_FORBIDDEN"                          # 403
    NOT_FOUND = "ERR_NOT_FOUND"                          # 404
    CONFLICT = "ERR_CONFLICT"                            # 409
    TOO_MANY_REQUESTS = "ERR_TOO_MANY_REQUESTS"          # 429
    INTERNAL_ERROR = "ERR_INTERNAL_ERROR"                # 500

    # --- Specific: 페이지 / 책 제약 ---
    INSUFFICIENT_PAGES = "ERR_INSUFFICIENT_PAGES"                # 400
    PAGECOUNT_INVALID = "ERR_PAGECOUNT_INVALID"                  # 400
    FINALIZE_PREREQ_UNMET = "ERR_FINALIZE_PREREQ_UNMET"          # 400
    CREATION_TYPE_UNSUPPORTED = "ERR_CREATION_TYPE_UNSUPPORTED"  # 400

    # --- Specific: 템플릿 ---
    TEMPLATE_BINDING_MISSING = "ERR_TEMPLATE_BINDING_MISSING"    # 400
    TEMPLATE_PARAM_REQUIRED = "ERR_TEMPLATE_PARAM_REQUIRED"      # 400

    # --- Specific: 주문 ---
    ORDER_TRANSITION_INVALID = "ERR_ORDER_TRANSITION_INVALID"    # 400
    INSUFFICIENT_CREDIT = "ERR_INSUFFICIENT_CREDIT"              # 402

    # --- Specific: 환경 / Sandbox ---
    ENV_MISMATCH = "ERR_ENV_MISMATCH"                            # 403
    SANDBOX_UNSUPPORTED = "ERR_SANDBOX_UNSUPPORTED"              # 501

    # --- Specific: 멱등성 ---
    IDEMPOTENCY_KEY_MISMATCH = "ERR_IDEMPOTENCY_KEY_MISMATCH"    # 422

    # --- Specific: PDF 취득/생성 (C02) ---
    PDF_NOT_UPLOADED = "ERR_PDF_NOT_UPLOADED"                    # 404
    PDF_NOT_GENERATED = "ERR_PDF_NOT_GENERATED"                  # 409
    PDF_PENDING = "ERR_PDF_PENDING"                              # 409
    PDF_GENERATION_FAILED = "ERR_PDF_GENERATION_FAILED"          # 422
    PDF_FILE_MISSING = "ERR_PDF_FILE_MISSING"                    # 500


class ConstraintTypes:
    """fieldErrors[].constraint 열거값"""

    MIN = "min"
    MAX = "max"
    INCREMENT = "increment"
    ENUM = "enum"
    PATTERN = "pattern"
    REQUIRED = "required"
