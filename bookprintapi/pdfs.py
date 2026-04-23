"""BookPrintAPI SDK — PDF 업로드/교체/다운로드

대상: creation_type = "PDF_UPLOAD" 또는 "MIX_COVER_TEMPLATE" 책.
- POST /books/{bookUid}/pdf-cover      표지 PDF 신규 등록 (이미 있으면 409)
- PUT  /books/{bookUid}/pdf-cover      표지 PDF 교체 (없으면 404)
- GET  /books/{bookUid}/pdf-cover      표지 PDF 바이너리 다운로드
- POST /books/{bookUid}/pdf-contents   내지 PDF 신규 등록
- PUT  /books/{bookUid}/pdf-contents   내지 PDF 교체
- GET  /books/{bookUid}/pdf-contents   내지 PDF 바이너리 다운로드
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


class PdfsClient:
    """책 표지/내지 PDF 업로드 및 다운로드"""

    def __init__(self, client: Client):
        self._client = client

    # ─── 표지 PDF ─────────────────────────────────────────────
    def upload_cover(self, book_uid: str, file_path: str) -> dict | None:
        """표지 PDF 신규 등록. 이미 존재하면 409 (replace_cover 사용)."""
        return self._upload(book_uid, file_path, "pdf-cover", replace=False)

    def replace_cover(self, book_uid: str, file_path: str) -> dict | None:
        """표지 PDF 교체. 기존 파일이 없으면 404."""
        return self._upload(book_uid, file_path, "pdf-cover", replace=True)

    def download_cover(self, book_uid: str, dest_path: str | None = None) -> bytes | str:
        """표지 PDF 다운로드. dest_path 미지정 시 bytes 반환."""
        return self._client.download(f"/books/{book_uid}/pdf-cover", dest_path=dest_path)

    # ─── 내지 PDF ─────────────────────────────────────────────
    def upload_contents(self, book_uid: str, file_path: str) -> dict | None:
        """내지 PDF 신규 등록. 이미 존재하면 409 (replace_contents 사용)."""
        return self._upload(book_uid, file_path, "pdf-contents", replace=False)

    def replace_contents(self, book_uid: str, file_path: str) -> dict | None:
        """내지 PDF 교체. 기존 파일이 없으면 404."""
        return self._upload(book_uid, file_path, "pdf-contents", replace=True)

    def download_contents(self, book_uid: str, dest_path: str | None = None) -> bytes | str:
        """내지 PDF 다운로드. dest_path 미지정 시 bytes 반환."""
        return self._client.download(f"/books/{book_uid}/pdf-contents", dest_path=dest_path)

    # ─── 공통 ─────────────────────────────────────────────────
    def _upload(self, book_uid: str, file_path: str, kind: str, *, replace: bool) -> dict | None:
        path = f"/books/{book_uid}/{kind}"
        with open(file_path, "rb") as f:
            name = os.path.basename(file_path)
            files = [("file", (name, f, "application/pdf"))]
            if replace:
                return self._client.put_form(path, files=files)
            return self._client.post_form(path, files=files)
