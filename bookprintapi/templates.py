"""BookPrintAPI SDK — Templates 조회"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class TemplatesClient:
    """템플릿 목록/상세 조회 (읽기 전용)

    생성/수정/삭제는 관리자 전용(admin:* 스코프)이라 일반 파트너 SDK에는 노출하지 않음.
    """

    def __init__(self, client: Client):
        self._client = client

    def list(
        self,
        *,
        scope: str | None = None,
        book_spec_uid: str | None = None,
        spec_profile_uid: str | None = None,
        template_kind: str | None = None,
        category: str | None = None,
        template_name: str | None = None,
        theme: str | None = None,
        sort: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """템플릿 목록 조회

        Args:
            scope: "public" | "private" | "all" (기본 "all")
            book_spec_uid: 특정 상품 스펙에 호환되는 템플릿만 필터
            spec_profile_uid: 상품 프로필 UID 필터
            template_kind: "cover" | "content" | "divider" | "publish"
            category: template_category.key 값
            template_name: 이름 부분 일치 검색
            theme: 테마 필터
            sort: 정렬 키
            limit: 1-100 (기본 50)
            offset: 페이지네이션 오프셋
        """
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if scope:
            params["scope"] = scope
        if book_spec_uid:
            params["bookSpecUid"] = book_spec_uid
        if spec_profile_uid:
            params["specProfileUid"] = spec_profile_uid
        if template_kind:
            params["templateKind"] = template_kind
        if category:
            params["category"] = category
        if template_name:
            params["templateName"] = template_name
        if theme:
            params["theme"] = theme
        if sort:
            params["sort"] = sort
        return self._client.get("/templates", params=params)

    def get(self, template_uid: str, *, account_uid: str | None = None) -> dict:
        """템플릿 상세 조회

        Args:
            template_uid: 템플릿 UID
            account_uid: 관리자 전용 - 특정 사용자의 템플릿 조회 시
        """
        params = {"AccountUid": account_uid} if account_uid else None
        return self._client.get(f"/templates/{template_uid}", params=params)

    def get_schema(self, template_uid: str) -> dict:
        """템플릿 파라미터 스키마 조회 (JSON Schema draft-07)

        AI 에이전트 / 페이로드 검증 / codegen 용도. 응답 `data`는 JSON Schema
        문서로, `properties` 각 항목의 `x-binding` 으로 binding 종류 식별.

        binding ↔ JSON Schema 매핑:
            text           → string
            file           → string + format=uri
            gallery        → array<string + format=uri>
            collageGallery → array<string + format=uri>
            rowGallery     → array<string + format=uri>

        `required` 명시되지 않은 키는 응답 시점에 자동으로 필수(true) 처리됨.

        Args:
            template_uid: 템플릿 UID
        """
        return self._client.get(f"/templates/{template_uid}/schema")
