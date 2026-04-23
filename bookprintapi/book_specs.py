"""BookPrintAPI SDK — BookSpecs 조회 (읽기 전용)"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class BookSpecsClient:
    """상품 스펙(BookSpec) 목록/상세 조회

    생성/수정/삭제 및 custom_pricing은 관리자 전용(admin:* 스코프)이라
    일반 파트너 SDK에는 노출하지 않음. 필요 시 raw client.post/patch/delete 사용.
    """

    def __init__(self, client: Client):
        self._client = client

    def list(self, *, account_uid: str | None = None) -> dict | list:
        """BookSpec 목록 조회

        Args:
            account_uid: 관리자 전용 - 다른 사용자의 custom_pricing이 반영된 목록 조회
        """
        params = {"accountUid": account_uid} if account_uid else None
        return self._client.get("/book-specs", params=params)

    def get(self, book_spec_uid: str, *, account_uid: str | None = None) -> dict:
        """BookSpec 상세 조회

        Args:
            book_spec_uid: 상품 스펙 UID
            account_uid: 관리자 전용 - 다른 사용자의 custom_pricing 오버레이
        """
        params = {"accountUid": account_uid} if account_uid else None
        return self._client.get(f"/book-specs/{book_spec_uid}", params=params)
