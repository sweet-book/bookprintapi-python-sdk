"""BookPrintAPI SDK — 다단계 플로우 헬퍼

11_sdk_helpers_design.md 기준 v0.1 구현.

- ``create_book_from_template`` : TEMPLATE 모드 책 생성 → 표지 → 내지 N → finalize
- ``upload_pdf_and_order``      : PDF_UPLOAD 모드 책 + PDF 2종 → finalize → 견적 → 주문

설계 §4.1 정책:
- 자동 재시도 안 함 (트랜스포트 레이어 재시도만 사용)
- 자동 롤백 안 함 — 실패 시 :class:`SweetbookHelperError` 의 ``book_uid`` / ``partial`` 노출.
  파트너가 ``client.books.delete(bookUid)`` 등으로 명시적 cleanup 판단

설계 §7-5 채택: 본 Python 구현은 dict ``options`` 대신 **개별 kwargs** 사용 (Pythonic).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Sequence

from .exceptions import (
    ApiError,
    HelperErrorCodes,
    HelperStage,
    SweetbookHelperError,
    ValidationError,
)

if TYPE_CHECKING:
    from .client import Client


# ---------------------------------------------------------------------------
# 결과 객체
# ---------------------------------------------------------------------------


class BookBuildResult:
    """``create_book_from_template`` 반환값 — 11_sdk_helpers_design.md § 2.1"""

    __slots__ = ("book_uid", "cover_page_num", "content_pages", "finalized", "page_count", "raw")

    def __init__(
        self,
        *,
        book_uid: str,
        cover_page_num: int | None = None,
        content_pages: list[dict] | None = None,
        finalized: bool = False,
        page_count: int | None = None,
        raw: dict | None = None,
    ):
        self.book_uid = book_uid
        self.cover_page_num = cover_page_num
        self.content_pages: list[dict] = content_pages or []
        self.finalized = finalized
        self.page_count = page_count
        self.raw = raw or {}

    def __repr__(self) -> str:
        return (
            f"BookBuildResult(book_uid={self.book_uid!r}, "
            f"contents={len(self.content_pages)}p, finalized={self.finalized})"
        )


class PdfOrderBuildResult:
    """``upload_pdf_and_order`` 반환값 — 11_sdk_helpers_design.md § 2.2"""

    __slots__ = (
        "book_uid",
        "cover_pdf",
        "contents_pdf",
        "finalized",
        "estimate",
        "order",
        "order_uid",
    )

    def __init__(
        self,
        *,
        book_uid: str,
        cover_pdf: dict,
        contents_pdf: dict,
        finalized: bool,
        estimate: dict | None,
        order: dict,
    ):
        self.book_uid = book_uid
        self.cover_pdf = cover_pdf
        self.contents_pdf = contents_pdf
        self.finalized = finalized
        self.estimate = estimate
        self.order = order
        self.order_uid: str | None = (order.get("data", {}) or {}).get("orderUid") or order.get("orderUid")

    def __repr__(self) -> str:
        return (
            f"PdfOrderBuildResult(book_uid={self.book_uid!r}, "
            f"order_uid={self.order_uid!r}, finalized={self.finalized})"
        )


# ---------------------------------------------------------------------------
# 헬퍼 클라이언트
# ---------------------------------------------------------------------------


class HelpersClient:
    """다단계 플로우 헬퍼 — ``Client.helpers`` 로 노출."""

    def __init__(self, client: "Client"):
        self._client = client

    # ====================================================================
    # createBookFromTemplate
    # ====================================================================

    def create_book_from_template(
        self,
        *,
        book_spec_uid: str,
        cover_template_uid: str,
        cover_params: dict[str, Any] | None = None,
        cover_binding_files: dict[str, str] | None = None,
        contents: Sequence[dict[str, Any]],
        title: str | None = None,
        external_ref: str | None = None,
        spec_profile_uid: str | None = None,
        skip_finalize: bool = False,
    ) -> BookBuildResult:
        """TEMPLATE 모드 책 한 권을 한 호출로 생성.

        내부 호출 순서 (성공 경로):
            1. ``books.create(book_spec_uid, title, creation_type="TEMPLATE", external_ref)``
            2. ``covers.create(book_uid, cover_template_uid, cover_params, cover_binding_files)``
            3. ``for c in contents: contents.insert(book_uid, c["template_uid"], c["params"], c["binding_files"], c["break_before"])``
            4. ``books.finalize(book_uid)`` (skip_finalize=True 면 건너뜀)

        Args:
            book_spec_uid: 상품 규격 (예: ``"PHOTOBOOK_A4_SC"``)
            cover_template_uid: 표지 템플릿 UID
            cover_params: 표지 텍스트/이미지 binding 매핑
            cover_binding_files: multipart 직접 첨부할 binding→경로. 사전 업로드 패턴이면 None
            contents: 내지 페이지 dict 시퀀스. 각 항목 키: ``template_uid``, ``params``,
                ``binding_files`` (선택), ``break_before`` (선택, "page"|"spread"|"column")
            title: 책 제목 (선택)
            external_ref: 외부 참조 ID (선택, 멱등 재시도 식별용)
            spec_profile_uid: 책 사양 프로파일 (선택)
            skip_finalize: True 면 finalize 안 함 (호출자가 추가 페이지 후 직접 finalize)

        Raises:
            SweetbookHelperError: 단계별 실패. ``stage`` / ``book_uid`` / ``partial`` 노출
            ValidationError: contents 비어있음 등 클라이언트측 검증 실패
        """
        # § 4.5 클라이언트측 입력 검증
        if not book_spec_uid:
            raise SweetbookHelperError(
                "book_spec_uid 는 필수입니다",
                stage=HelperStage.VALIDATION,
                code=HelperErrorCodes.VALIDATION,
            )
        if not cover_template_uid:
            raise SweetbookHelperError(
                "cover_template_uid 는 필수입니다",
                stage=HelperStage.VALIDATION,
                code=HelperErrorCodes.VALIDATION,
            )
        contents_list = list(contents or [])
        if not contents_list:
            raise SweetbookHelperError(
                "contents 는 최소 1개 이상이어야 합니다",
                stage=HelperStage.VALIDATION,
                code=HelperErrorCodes.VALIDATION,
            )

        partial: dict[str, Any] = {
            "bookCreated": False,
            "coverCreated": False,
            "contentsInserted": [],
            "finalized": False,
        }
        book_uid: str | None = None

        # 1. books.create
        try:
            book = self._client.books.create(
                book_spec_uid=book_spec_uid,
                title=title,
                creation_type="TEMPLATE",
                external_ref=external_ref,
            )
        except ApiError as e:
            raise SweetbookHelperError(
                "책 생성 실패",
                stage=HelperStage.BOOK_CREATE,
                code=HelperErrorCodes.BOOK_CREATE_FAILED,
                partial=partial,
                cause=e,
            ) from e

        data = book.get("data", book) if isinstance(book, dict) else {}
        book_uid = (data or {}).get("bookUid")
        if not book_uid:
            raise SweetbookHelperError(
                "books.create 응답에 bookUid 가 없습니다",
                stage=HelperStage.BOOK_CREATE,
                code=HelperErrorCodes.BOOK_CREATE_FAILED,
                partial=partial,
            )
        partial["bookCreated"] = True

        # 2. covers.create
        try:
            cover_resp = self._client.covers.create(
                book_uid,
                template_uid=cover_template_uid,
                parameters=cover_params or {},
                binding_files=cover_binding_files,
            )
        except ApiError as e:
            raise SweetbookHelperError(
                "표지 생성 실패",
                stage=HelperStage.COVER_CREATE,
                code=HelperErrorCodes.COVER_CREATE_FAILED,
                book_uid=book_uid,
                partial=partial,
                cause=e,
            ) from e
        partial["coverCreated"] = True
        cover_data = cover_resp.get("data", cover_resp) if isinstance(cover_resp, dict) else {}
        cover_page_num = (cover_data or {}).get("pageNum")

        # 3. contents.insert (반복)
        for idx, page in enumerate(contents_list):
            tpl = page.get("template_uid") or page.get("templateUid")
            if not tpl:
                raise SweetbookHelperError(
                    f"contents[{idx}].template_uid 누락",
                    stage=HelperStage.CONTENT_INSERT,
                    code=HelperErrorCodes.CONTENT_INSERT_FAILED,
                    book_uid=book_uid,
                    partial=partial,
                    content_index=idx,
                )
            try:
                resp = self._client.contents.insert(
                    book_uid,
                    template_uid=tpl,
                    parameters=page.get("params") or page.get("parameters") or {},
                    binding_files=page.get("binding_files") or page.get("bindingFiles"),
                    break_before=page.get("break_before") or page.get("breakBefore"),
                )
            except ApiError as e:
                raise SweetbookHelperError(
                    f"내지 페이지 #{idx} 삽입 실패",
                    stage=HelperStage.CONTENT_INSERT,
                    code=HelperErrorCodes.CONTENT_INSERT_FAILED,
                    book_uid=book_uid,
                    partial=partial,
                    cause=e,
                    content_index=idx,
                ) from e

            rd = resp.get("data", resp) if isinstance(resp, dict) else {}
            page_info = {
                "pageNum": rd.get("pageNum"),
                "pageSide": rd.get("pageSide"),
            }
            partial["contentsInserted"].append(page_info)

        # 4. books.finalize
        finalize_resp: dict | None = None
        if not skip_finalize:
            try:
                finalize_resp = self._client.books.finalize(book_uid)
            except ApiError as e:
                raise SweetbookHelperError(
                    "책 확정(finalize) 실패",
                    stage=HelperStage.BOOK_FINALIZE,
                    code=HelperErrorCodes.FINALIZE_FAILED,
                    book_uid=book_uid,
                    partial=partial,
                    cause=e,
                ) from e
            partial["finalized"] = True

        page_count: int | None = None
        if finalize_resp:
            fd = finalize_resp.get("data", finalize_resp) if isinstance(finalize_resp, dict) else {}
            page_meta = (fd or {}).get("pageMeta") or {}
            page_count = page_meta.get("currentPageCount") or fd.get("pageCount")

        return BookBuildResult(
            book_uid=book_uid,
            cover_page_num=cover_page_num,
            content_pages=partial["contentsInserted"],
            finalized=partial["finalized"],
            page_count=page_count,
            raw={"book": book, "cover": cover_resp, "finalize": finalize_resp},
        )

    # ====================================================================
    # uploadPdfAndOrder
    # ====================================================================

    def upload_pdf_and_order(
        self,
        *,
        book_spec_uid: str,
        page_count: int,
        cover_pdf: str,
        contents_pdf: str,
        shipping: dict[str, Any],
        quantity: int = 1,
        title: str | None = None,
        book_external_ref: str | None = None,
        order_external_ref: str | None = None,
        spec_profile_uid: str | None = None,
        fail_on_insufficient_credit: bool = True,
        skip_estimate: bool = False,
    ) -> PdfOrderBuildResult:
        """PDF_UPLOAD 모드 책 + PDF 2종 + finalize + 주문까지 한 호출로.

        내부 호출 순서:
            1. ``books.create(book_spec_uid, creation_type="PDF_UPLOAD", page_count, ...)``
            2. ``pdfs.upload_cover(book_uid, cover_pdf)``
            3. ``pdfs.upload_contents(book_uid, contents_pdf)``
            4. ``books.finalize(book_uid)``
            5. ``orders.estimate([{"bookUid", "quantity"}])`` (skip_estimate=False)
            6. ``orders.create(items, shipping, external_ref)``

        Args:
            cover_pdf / contents_pdf: PDF 파일 경로 (str). bytes/file-like 는 추후 지원
            shipping: ``{"recipientName", "recipientPhone", "postalCode", "address1", ...}``
            quantity: 주문 수량 (기본 1)
            book_external_ref / order_external_ref: 책/주문 멱등 식별자 (선택)
            fail_on_insufficient_credit: estimate 의 ``creditSufficient=false`` 일 때
                주문 생성 전 :class:`SweetbookHelperError` (CREDIT_INSUFFICIENT) 던질지
            skip_estimate: True 면 estimate 생략하고 바로 orders.create
        """
        # 클라이언트측 검증
        if not book_spec_uid:
            raise SweetbookHelperError("book_spec_uid 필수",
                stage=HelperStage.VALIDATION, code=HelperErrorCodes.VALIDATION)
        if not isinstance(page_count, int) or page_count < 1:
            raise SweetbookHelperError("page_count >= 1 필요",
                stage=HelperStage.VALIDATION, code=HelperErrorCodes.VALIDATION)
        if not cover_pdf or not contents_pdf:
            raise SweetbookHelperError("cover_pdf / contents_pdf 둘 다 필수",
                stage=HelperStage.VALIDATION, code=HelperErrorCodes.VALIDATION)
        if not shipping or not shipping.get("recipientName"):
            raise SweetbookHelperError("shipping.recipientName 비어있음",
                stage=HelperStage.VALIDATION, code=HelperErrorCodes.VALIDATION)

        partial: dict[str, Any] = {
            "bookCreated": False,
            "coverPdfUploaded": False,
            "contentsPdfUploaded": False,
            "finalized": False,
            "estimate": None,
        }

        # 1. books.create
        try:
            book = self._client.books.create(
                book_spec_uid=book_spec_uid,
                title=title,
                creation_type="PDF_UPLOAD",
                external_ref=book_external_ref,
            )
        except ApiError as e:
            raise SweetbookHelperError("책 생성 실패",
                stage=HelperStage.BOOK_CREATE,
                code=HelperErrorCodes.BOOK_CREATE_FAILED,
                partial=partial, cause=e) from e

        bdata = book.get("data", book) if isinstance(book, dict) else {}
        book_uid = (bdata or {}).get("bookUid")
        if not book_uid:
            raise SweetbookHelperError("books.create 응답에 bookUid 없음",
                stage=HelperStage.BOOK_CREATE,
                code=HelperErrorCodes.BOOK_CREATE_FAILED, partial=partial)
        partial["bookCreated"] = True

        # 2. pdfs.upload_cover
        try:
            cover_pdf_resp = self._client.pdfs.upload_cover(book_uid, cover_pdf)
        except ApiError as e:
            raise SweetbookHelperError("표지 PDF 업로드 실패",
                stage=HelperStage.PDF_UPLOAD_COVER,
                code=HelperErrorCodes.PDF_UPLOAD_FAILED,
                book_uid=book_uid, partial=partial, cause=e) from e
        partial["coverPdfUploaded"] = True

        # 3. pdfs.upload_contents
        try:
            contents_pdf_resp = self._client.pdfs.upload_contents(book_uid, contents_pdf)
        except ApiError as e:
            raise SweetbookHelperError("내지 PDF 업로드 실패",
                stage=HelperStage.PDF_UPLOAD_CONTENTS,
                code=HelperErrorCodes.PDF_UPLOAD_FAILED,
                book_uid=book_uid, partial=partial, cause=e) from e
        partial["contentsPdfUploaded"] = True

        # 4. books.finalize
        try:
            self._client.books.finalize(book_uid)
        except ApiError as e:
            raise SweetbookHelperError("책 확정(finalize) 실패",
                stage=HelperStage.BOOK_FINALIZE,
                code=HelperErrorCodes.FINALIZE_FAILED,
                book_uid=book_uid, partial=partial, cause=e) from e
        partial["finalized"] = True

        # 5. orders.estimate (선택)
        estimate_resp: dict | None = None
        if not skip_estimate:
            try:
                estimate_resp = self._client.orders.estimate(
                    [{"bookUid": book_uid, "quantity": quantity}]
                )
            except ApiError as e:
                raise SweetbookHelperError("견적 조회 실패",
                    stage=HelperStage.ORDER_ESTIMATE,
                    code=HelperErrorCodes.ORDER_ESTIMATE_FAILED,
                    book_uid=book_uid, partial=partial, cause=e) from e
            partial["estimate"] = estimate_resp

            if fail_on_insufficient_credit:
                ed = (estimate_resp or {}).get("data", estimate_resp) or {}
                if ed.get("creditSufficient") is False:
                    required = ed.get("paidCreditAmount", 0)
                    balance = ed.get("creditBalance", 0)
                    raise SweetbookHelperError(
                        f"충전금 부족: 필요 {required}, 잔액 {balance}",
                        stage=HelperStage.ORDER_ESTIMATE,
                        code=HelperErrorCodes.CREDIT_INSUFFICIENT,
                        book_uid=book_uid,
                        partial=partial,
                    )

        # 6. orders.create
        try:
            order_resp = self._client.orders.create(
                items=[{"bookUid": book_uid, "quantity": quantity}],
                shipping=shipping,
                external_ref=order_external_ref,
            )
        except ApiError as e:
            raise SweetbookHelperError("주문 생성 실패",
                stage=HelperStage.ORDER_CREATE,
                code=HelperErrorCodes.ORDER_CREATE_FAILED,
                book_uid=book_uid, partial=partial, cause=e) from e

        return PdfOrderBuildResult(
            book_uid=book_uid,
            cover_pdf=cover_pdf_resp if isinstance(cover_pdf_resp, dict) else {},
            contents_pdf=contents_pdf_resp if isinstance(contents_pdf_resp, dict) else {},
            finalized=True,
            estimate=estimate_resp,
            order=order_resp if isinstance(order_resp, dict) else {},
        )
