"""books.create() 의 page_count 파라미터 동작 검증.

PDF_UPLOAD / MIX_COVER_TEMPLATE 시 필수, TEMPLATE 시 선택.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bookprintapi.books import BooksClient


class _FakeClient:
    """HTTP 호출을 가로채서 payload 만 캡쳐."""

    def __init__(self) -> None:
        self.last_payload: dict | None = None
        self.last_path: str | None = None

    def post(self, path: str, *, payload: dict) -> dict:
        self.last_path = path
        self.last_payload = payload
        return {"success": True, "data": {"bookUid": "B-1", "pageMeta": {}}}


def test_template_mode_without_page_count():
    fake = _FakeClient()
    BooksClient(fake).create(book_spec_uid="SQUAREBOOK_HC", title="t")
    assert fake.last_path == "/books"
    assert fake.last_payload == {
        "bookSpecUid": "SQUAREBOOK_HC",
        "creationType": "TEMPLATE",
        "title": "t",
    }
    assert "pageCount" not in fake.last_payload


def test_template_mode_with_page_count_is_passed_through():
    """TEMPLATE 에서도 page_count 전달 시 페이로드에 포함 (서버가 무시함)."""
    fake = _FakeClient()
    BooksClient(fake).create(book_spec_uid="SQUAREBOOK_HC", page_count=24)
    assert fake.last_payload["pageCount"] == 24


def test_pdf_upload_mode_requires_page_count():
    with pytest.raises(ValueError, match="page_count"):
        BooksClient(_FakeClient()).create(
            book_spec_uid="SQUAREBOOK_HC", creation_type="PDF_UPLOAD"
        )


def test_pdf_upload_mode_rejects_zero_page_count():
    with pytest.raises(ValueError, match="page_count"):
        BooksClient(_FakeClient()).create(
            book_spec_uid="SQUAREBOOK_HC", creation_type="PDF_UPLOAD", page_count=0
        )


def test_pdf_upload_mode_rejects_negative_page_count():
    with pytest.raises(ValueError, match="page_count"):
        BooksClient(_FakeClient()).create(
            book_spec_uid="SQUAREBOOK_HC", creation_type="PDF_UPLOAD", page_count=-1
        )


def test_pdf_upload_mode_with_valid_page_count():
    fake = _FakeClient()
    BooksClient(fake).create(
        book_spec_uid="SQUAREBOOK_HC", creation_type="PDF_UPLOAD", page_count=24
    )
    assert fake.last_payload == {
        "bookSpecUid": "SQUAREBOOK_HC",
        "creationType": "PDF_UPLOAD",
        "pageCount": 24,
    }


def test_mix_cover_template_requires_page_count():
    with pytest.raises(ValueError, match="page_count"):
        BooksClient(_FakeClient()).create(
            book_spec_uid="SQUAREBOOK_HC", creation_type="MIX_COVER_TEMPLATE"
        )


def test_mix_cover_template_with_valid_page_count():
    fake = _FakeClient()
    BooksClient(fake).create(
        book_spec_uid="SQUAREBOOK_HC",
        creation_type="MIX_COVER_TEMPLATE",
        page_count=12,
        external_ref="ext-1",
    )
    assert fake.last_payload == {
        "bookSpecUid": "SQUAREBOOK_HC",
        "creationType": "MIX_COVER_TEMPLATE",
        "externalRef": "ext-1",
        "pageCount": 12,
    }
