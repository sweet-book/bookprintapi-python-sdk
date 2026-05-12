"""BookPrintAPI SDK — Books"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class BooksClient:
    """책 생성/조회/확정/삭제"""

    def __init__(self, client: Client):
        self._client = client

    def list(self, *, status: str | None = None, limit: int = 20, offset: int = 0) -> dict:
        """책 목록 조회

        Args:
            status: "draft" | "finalized" (미지정 시 전체)
            limit: 결과 수 (1-100)
            offset: 페이지네이션 오프셋

        Returns:
            ``{ success, data: list[Book], pagination: {total, limit, offset, hasNext}, message }``
            (envelope 통일 전후 모두에서 동일한 shape 보장 — SDK 내부 평탄화)
        """
        from .response import ResponseParser
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        raw = self._client.get("/books", params=params)
        return ResponseParser(raw).to_flat_list_response()

    def create(self, *, book_spec_uid: str, title: str | None = None,
               creation_type: str = "TEMPLATE", external_ref: str | None = None,
               page_count: int | None = None) -> dict:
        """새 책 생성 (draft 상태)

        Args:
            book_spec_uid: 상품 규격 UID (예: "SQUAREBOOK_HC")
            title: 책 제목
            creation_type: "TEMPLATE" | "PDF_UPLOAD" | "MIX_COVER_TEMPLATE"
            external_ref: 외부 참조 ID (최대 100자)
            page_count: 내지 페이지수. ``creation_type`` 이
                ``PDF_UPLOAD`` 또는 ``MIX_COVER_TEMPLATE`` 일 때 **필수**.
                ``TEMPLATE`` 모드에서는 서버가 무시함.
        """
        if creation_type in ("PDF_UPLOAD", "MIX_COVER_TEMPLATE") and (
            page_count is None or page_count <= 0
        ):
            raise ValueError(
                f"creation_type={creation_type} 는 page_count(내지 페이지수, >0)가 필수입니다."
            )
        payload = {"bookSpecUid": book_spec_uid, "creationType": creation_type}
        if title:
            payload["title"] = title
        if external_ref:
            payload["externalRef"] = external_ref
        if page_count is not None:
            payload["pageCount"] = page_count
        return self._client.post("/books", payload=payload)

    def get(self, book_uid: str) -> dict:
        """책 상세 조회 (RESTful 단건)

        응답 `data`에 `pageMeta` 포함 — currentPageCount / pageMin / pageMax /
        pageIncrement / isValid. 권한: 본인 책 + 환경 일치 필요.
        """
        return self._client.get(f"/books/{book_uid}")

    def finalize(self, book_uid: str) -> dict:
        """책 확정 (draft → finalized). 확정 후에는 내용 수정 불가."""
        return self._client.post(f"/books/{book_uid}/finalization", payload={})

    def delete(self, book_uid: str) -> dict | None:
        """책 삭제 (draft 상태만 가능)"""
        return self._client.delete(f"/books/{book_uid}")
