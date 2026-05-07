"""bookprintapi.helpers 단위 테스트.

실제 HTTP 호출 없이 sub-client 를 mock 으로 대체하여 헬퍼 로직만 검증.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# SDK 패키지를 sys.path 에 추가 (tests 폴더에서 직접 실행)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bookprintapi.exceptions import (
    ApiError,
    HelperErrorCodes,
    HelperStage,
    SweetbookHelperError,
)
from bookprintapi.helpers import BookBuildResult, HelpersClient, PdfOrderBuildResult


def _build_mock_client(*, with_pdfs: bool = False):
    """sub-client 가 모두 MagicMock 인 가짜 Client. 헬퍼만 실제 인스턴스."""
    client = MagicMock(name="Client")
    client.books = MagicMock(name="BooksClient")
    client.covers = MagicMock(name="CoversClient")
    client.contents = MagicMock(name="ContentsClient")
    client.orders = MagicMock(name="OrdersClient")
    if with_pdfs:
        client.pdfs = MagicMock(name="PdfsClient")
    return client


# =============================================================================
# create_book_from_template
# =============================================================================


class TestCreateBookFromTemplate:
    def test_happy_path_finalize(self):
        client = _build_mock_client()
        client.books.create.return_value = {"data": {"bookUid": "bk_test"}}
        client.covers.create.return_value = {"data": {"pageNum": 1}}
        client.contents.insert.side_effect = [
            {"data": {"pageNum": 2, "pageSide": "left"}},
            {"data": {"pageNum": 3, "pageSide": "right"}},
        ]
        client.books.finalize.return_value = {
            "data": {"pageMeta": {"currentPageCount": 4}}
        }

        helpers = HelpersClient(client)
        result = helpers.create_book_from_template(
            book_spec_uid="PHOTOBOOK_A4_SC",
            cover_template_uid="cv1",
            cover_params={"title": "T"},
            contents=[
                {"template_uid": "p1", "params": {}},
                {"template_uid": "p2", "params": {}, "break_before": "page"},
            ],
            title="My Book",
        )

        assert isinstance(result, BookBuildResult)
        assert result.book_uid == "bk_test"
        assert result.cover_page_num == 1
        assert len(result.content_pages) == 2
        assert result.content_pages[0]["pageSide"] == "left"
        assert result.finalized is True
        assert result.page_count == 4

        client.books.create.assert_called_once_with(
            book_spec_uid="PHOTOBOOK_A4_SC",
            title="My Book",
            creation_type="TEMPLATE",
            external_ref=None,
        )
        kwargs = client.contents.insert.call_args_list[1].kwargs
        assert kwargs["break_before"] == "page"

    def test_skip_finalize(self):
        client = _build_mock_client()
        client.books.create.return_value = {"data": {"bookUid": "bk_skip"}}
        client.covers.create.return_value = {"data": {}}
        client.contents.insert.return_value = {"data": {"pageNum": 2, "pageSide": "left"}}

        result = HelpersClient(client).create_book_from_template(
            book_spec_uid="X",
            cover_template_uid="cv",
            contents=[{"template_uid": "p", "params": {}}],
            skip_finalize=True,
        )
        assert result.finalized is False
        client.books.finalize.assert_not_called()

    def test_validation_empty_contents(self):
        client = _build_mock_client()
        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).create_book_from_template(
                book_spec_uid="X",
                cover_template_uid="cv",
                contents=[],
            )
        assert exc.value.stage == HelperStage.VALIDATION
        assert exc.value.code == HelperErrorCodes.VALIDATION
        client.books.create.assert_not_called()

    def test_validation_missing_book_spec(self):
        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(_build_mock_client()).create_book_from_template(
                book_spec_uid="",
                cover_template_uid="cv",
                contents=[{"template_uid": "p", "params": {}}],
            )
        assert exc.value.stage == HelperStage.VALIDATION

    def test_book_create_failure(self):
        client = _build_mock_client()
        client.books.create.side_effect = ApiError(
            "Bad Request", status_code=400, error_code="ERR_VALIDATION_FAILED"
        )

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).create_book_from_template(
                book_spec_uid="X",
                cover_template_uid="cv",
                contents=[{"template_uid": "p", "params": {}}],
            )
        e = exc.value
        assert e.stage == HelperStage.BOOK_CREATE
        assert e.code == HelperErrorCodes.BOOK_CREATE_FAILED
        assert e.book_uid is None
        assert e.partial == {
            "bookCreated": False,
            "coverCreated": False,
            "contentsInserted": [],
            "finalized": False,
        }
        assert isinstance(e.cause, ApiError)
        client.covers.create.assert_not_called()

    def test_cover_failure_keeps_book_uid(self):
        client = _build_mock_client()
        client.books.create.return_value = {"data": {"bookUid": "bk_x"}}
        client.covers.create.side_effect = ApiError(
            "Bad", status_code=400, error_code="ERR_TEMPLATE_BINDING_MISSING"
        )

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).create_book_from_template(
                book_spec_uid="X",
                cover_template_uid="cv",
                contents=[{"template_uid": "p", "params": {}}],
            )
        e = exc.value
        assert e.stage == HelperStage.COVER_CREATE
        assert e.book_uid == "bk_x"
        assert e.partial["bookCreated"] is True
        assert e.partial["coverCreated"] is False
        client.contents.insert.assert_not_called()

    def test_content_failure_includes_index(self):
        client = _build_mock_client()
        client.books.create.return_value = {"data": {"bookUid": "bk_y"}}
        client.covers.create.return_value = {"data": {}}
        client.contents.insert.side_effect = [
            {"data": {"pageNum": 2, "pageSide": "left"}},
            ApiError("Bad", status_code=400),
        ]

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).create_book_from_template(
                book_spec_uid="X",
                cover_template_uid="cv",
                contents=[
                    {"template_uid": "p1", "params": {}},
                    {"template_uid": "p2", "params": {}},
                ],
            )
        e = exc.value
        assert e.stage == HelperStage.CONTENT_INSERT
        assert e.content_index == 1
        assert e.book_uid == "bk_y"
        assert len(e.partial["contentsInserted"]) == 1

    def test_finalize_failure(self):
        client = _build_mock_client()
        client.books.create.return_value = {"data": {"bookUid": "bk_z"}}
        client.covers.create.return_value = {"data": {}}
        client.contents.insert.return_value = {"data": {"pageNum": 2}}
        client.books.finalize.side_effect = ApiError(
            "Bad", status_code=400, error_code="ERR_FINALIZE_PREREQ_UNMET"
        )

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).create_book_from_template(
                book_spec_uid="X",
                cover_template_uid="cv",
                contents=[{"template_uid": "p", "params": {}}],
            )
        e = exc.value
        assert e.stage == HelperStage.BOOK_FINALIZE
        assert e.code == HelperErrorCodes.FINALIZE_FAILED
        assert e.partial["finalized"] is False
        assert e.partial["coverCreated"] is True


# =============================================================================
# upload_pdf_and_order
# =============================================================================


class TestUploadPdfAndOrder:
    SHIPPING = {
        "recipientName": "홍길동",
        "recipientPhone": "010-1234-5678",
        "postalCode": "06100",
        "address1": "서울시 강남구",
    }

    def test_happy_path(self):
        client = _build_mock_client(with_pdfs=True)
        client.books.create.return_value = {"data": {"bookUid": "bk_pdf"}}
        client.pdfs.upload_cover.return_value = {"data": {"size": 100}}
        client.pdfs.upload_contents.return_value = {"data": {"size": 200}}
        client.books.finalize.return_value = {"data": {}}
        client.orders.estimate.return_value = {
            "data": {"creditSufficient": True, "paidCreditAmount": 12000}
        }
        client.orders.create.return_value = {"data": {"orderUid": "or_test"}}

        result = HelpersClient(client).upload_pdf_and_order(
            book_spec_uid="PHOTOBOOK_A4_SC",
            page_count=24,
            cover_pdf="/tmp/cover.pdf",
            contents_pdf="/tmp/contents.pdf",
            shipping=self.SHIPPING,
        )

        assert isinstance(result, PdfOrderBuildResult)
        assert result.book_uid == "bk_pdf"
        assert result.order_uid == "or_test"
        assert result.finalized is True
        assert result.estimate is not None
        client.books.create.assert_called_once()
        assert client.books.create.call_args.kwargs["creation_type"] == "PDF_UPLOAD"

    def test_insufficient_credit_raises(self):
        client = _build_mock_client(with_pdfs=True)
        client.books.create.return_value = {"data": {"bookUid": "bk_ic"}}
        client.pdfs.upload_cover.return_value = {"data": {}}
        client.pdfs.upload_contents.return_value = {"data": {}}
        client.books.finalize.return_value = {"data": {}}
        client.orders.estimate.return_value = {
            "data": {"creditSufficient": False, "paidCreditAmount": 50000, "creditBalance": 1000}
        }

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).upload_pdf_and_order(
                book_spec_uid="X",
                page_count=24,
                cover_pdf="/tmp/c.pdf",
                contents_pdf="/tmp/i.pdf",
                shipping=self.SHIPPING,
            )
        e = exc.value
        assert e.stage == HelperStage.ORDER_ESTIMATE
        assert e.code == HelperErrorCodes.CREDIT_INSUFFICIENT
        assert e.book_uid == "bk_ic"
        client.orders.create.assert_not_called()

    def test_skip_estimate_proceeds_directly(self):
        client = _build_mock_client(with_pdfs=True)
        client.books.create.return_value = {"data": {"bookUid": "bk_se"}}
        client.pdfs.upload_cover.return_value = {"data": {}}
        client.pdfs.upload_contents.return_value = {"data": {}}
        client.books.finalize.return_value = {"data": {}}
        client.orders.create.return_value = {"data": {"orderUid": "or_se"}}

        result = HelpersClient(client).upload_pdf_and_order(
            book_spec_uid="X",
            page_count=24,
            cover_pdf="/tmp/c.pdf",
            contents_pdf="/tmp/i.pdf",
            shipping=self.SHIPPING,
            skip_estimate=True,
        )
        assert result.estimate is None
        client.orders.estimate.assert_not_called()
        client.orders.create.assert_called_once()

    def test_pdf_cover_upload_failure(self):
        client = _build_mock_client(with_pdfs=True)
        client.books.create.return_value = {"data": {"bookUid": "bk_pf"}}
        client.pdfs.upload_cover.side_effect = ApiError(
            "Bad", status_code=400, error_code="ERR_PDF_FILE_MISSING"
        )

        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(client).upload_pdf_and_order(
                book_spec_uid="X",
                page_count=24,
                cover_pdf="/tmp/c.pdf",
                contents_pdf="/tmp/i.pdf",
                shipping=self.SHIPPING,
            )
        e = exc.value
        assert e.stage == HelperStage.PDF_UPLOAD_COVER
        assert e.code == HelperErrorCodes.PDF_UPLOAD_FAILED
        assert e.partial["bookCreated"] is True
        assert e.partial["coverPdfUploaded"] is False
        client.pdfs.upload_contents.assert_not_called()

    def test_validation_missing_recipient(self):
        with pytest.raises(SweetbookHelperError) as exc:
            HelpersClient(_build_mock_client(with_pdfs=True)).upload_pdf_and_order(
                book_spec_uid="X",
                page_count=24,
                cover_pdf="/tmp/c.pdf",
                contents_pdf="/tmp/i.pdf",
                shipping={"address1": "서울"},
            )
        assert exc.value.stage == HelperStage.VALIDATION


# =============================================================================
# 예외 표시 / user_message
# =============================================================================


def test_helper_error_str_includes_stage_and_book_uid():
    e = SweetbookHelperError(
        "fail",
        stage=HelperStage.CONTENT_INSERT,
        code=HelperErrorCodes.CONTENT_INSERT_FAILED,
        book_uid="bk_xyz",
        content_index=3,
    )
    s = str(e)
    assert "CONTENT_INSERT#3" in s
    assert "bk_xyz" in s


def test_helper_error_user_message_delegates_to_api_error():
    api = ApiError("Bad", status_code=400, details=["사용자에게 보여줄 한글 메시지"])
    e = SweetbookHelperError("fail",
        stage=HelperStage.BOOK_CREATE,
        code=HelperErrorCodes.BOOK_CREATE_FAILED,
        cause=api)
    assert e.user_message() == "사용자에게 보여줄 한글 메시지"


def test_helper_error_user_message_fallback_when_no_cause():
    e = SweetbookHelperError("fallback msg",
        stage=HelperStage.VALIDATION,
        code=HelperErrorCodes.VALIDATION)
    assert e.user_message() == "fallback msg"
