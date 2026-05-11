"""ResponseParser.to_flat_list_response 의 신·구 envelope 호환성 검증.

photobook-api commit 6fbf346 (2026-05-11) 전후 둘 다에서 동일 결과를 반환하는지 보증.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bookprintapi.response import ResponseParser


# =============================================================================
# 평탄화 신 envelope ({ data: [...], pagination: {...} })
# =============================================================================


def test_new_envelope_books_list():
    raw = {
        "success": True,
        "message": "성공",
        "data": [{"bookUid": "b1"}, {"bookUid": "b2"}],
        "pagination": {"total": 2, "limit": 20, "offset": 0, "hasNext": False},
    }
    out = ResponseParser(raw).to_flat_list_response()
    assert out["success"] is True
    assert out["data"] == [{"bookUid": "b1"}, {"bookUid": "b2"}]
    assert out["pagination"] == {"total": 2, "limit": 20, "offset": 0, "hasNext": False}
    assert out["message"] == "성공"


def test_new_envelope_no_pagination():
    """페이지네이션 없는 list (예: template-categories)."""
    raw = {"success": True, "data": [{"key": "a"}, {"key": "b"}]}
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == [{"key": "a"}, {"key": "b"}]
    assert "pagination" not in out


# =============================================================================
# 구 envelope ({ data: { books|orders|items|...: [...], pagination } })
# =============================================================================


def test_old_envelope_books_nested():
    raw = {
        "success": True,
        "data": {
            "books": [{"bookUid": "b1"}, {"bookUid": "b2"}],
            "pagination": {"total": 2, "limit": 20, "offset": 0, "hasNext": False},
        },
    }
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == [{"bookUid": "b1"}, {"bookUid": "b2"}]
    assert out["pagination"]["total"] == 2


def test_old_envelope_items_nested():
    """data 안의 키가 items 인 경우 (contacts, spec-profiles 등)."""
    raw = {
        "success": True,
        "data": {
            "items": [{"id": 1}, {"id": 2}],
            "pagination": {"total": 2, "limit": 10, "offset": 0, "hasNext": False},
        },
    }
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == [{"id": 1}, {"id": 2}]
    assert out["pagination"]["total"] == 2


def test_old_envelope_photos_totalcount_absorbed():
    """photos 구버전: data.totalCount → pagination.total 로 흡수."""
    raw = {
        "success": True,
        "data": {
            "photos": [{"fileName": "a.jpg"}, {"fileName": "b.jpg"}],
            "totalCount": 2,
        },
    }
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == [{"fileName": "a.jpg"}, {"fileName": "b.jpg"}]
    assert out["pagination"]["total"] == 2


# =============================================================================
# 엣지 케이스
# =============================================================================


def test_empty_data_list():
    raw = {"success": True, "data": [], "pagination": {"total": 0, "limit": 20, "offset": 0, "hasNext": False}}
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == []
    assert out["pagination"]["total"] == 0


def test_missing_data_returns_empty_list():
    """data 자체가 없는 비정상 응답도 비파괴적으로 처리."""
    raw = {"success": True}
    out = ResponseParser(raw).to_flat_list_response()
    assert out["data"] == []
