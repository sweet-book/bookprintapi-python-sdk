"""BookPrintAPI SDK — Order 상태값 카탈로그

master_대비_변경사항.md § 7 기준. 주문 응답의 `orderStatus` / `itemStatus`는
문자열 enum으로 통일됨. 숫자 코드는 관리자 응답의 `orderStatusCode` /
`itemStatusCode`에서만 노출.
"""

from __future__ import annotations


class OrderStatus:
    """주문 상태 문자열 enum (string enum)"""

    PAID_AWAITING_CONTENT = "PAID_AWAITING_CONTENT"   # 15
    PAID = "PAID"                                     # 20
    PDF_READY = "PDF_READY"                           # 25 (Item)
    CONFIRMED = "CONFIRMED"                           # 30
    IN_PRODUCTION = "IN_PRODUCTION"                   # 40
    COMPLETED = "COMPLETED"                           # 45 (Item)
    PRODUCTION_COMPLETE = "PRODUCTION_COMPLETE"       # 50 (Order)
    SHIPPED = "SHIPPED"                               # 60
    DELIVERED = "DELIVERED"                           # 70 (Order)
    CANCELLED = "CANCELLED"                           # 80
    CANCELLED_REFUND = "CANCELLED_REFUND"             # 81 (Order)
    ERROR = "ERROR"                                   # 90


# 문자열 → 숫자 코드 매핑 (관리자/디버깅 용도)
ORDER_STATUS_CODE: dict[str, int] = {
    OrderStatus.PAID_AWAITING_CONTENT: 15,
    OrderStatus.PAID: 20,
    OrderStatus.PDF_READY: 25,
    OrderStatus.CONFIRMED: 30,
    OrderStatus.IN_PRODUCTION: 40,
    OrderStatus.COMPLETED: 45,
    OrderStatus.PRODUCTION_COMPLETE: 50,
    OrderStatus.SHIPPED: 60,
    OrderStatus.DELIVERED: 70,
    OrderStatus.CANCELLED: 80,
    OrderStatus.CANCELLED_REFUND: 81,
    OrderStatus.ERROR: 90,
}

# 숫자 코드 → 문자열 enum (역방향, 호환성 유지용)
ORDER_STATUS_FROM_CODE: dict[int, str] = {v: k for k, v in ORDER_STATUS_CODE.items()}
