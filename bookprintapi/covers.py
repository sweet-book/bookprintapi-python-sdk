"""BookPrintAPI SDK — Covers"""

from __future__ import annotations

import json
import mimetypes
import os
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Client


class CoversClient:
    """책 표지 생성/조회/삭제"""

    def __init__(self, client: Client):
        self._client = client

    def create(self, book_uid: str, *, template_uid: str,
               parameters: dict[str, Any] | None = None,
               binding_files: dict[str, str] | None = None,
               files: list[str] | None = None) -> dict:
        """표지 생성/수정

        multipart 파일 part 이름은 **템플릿이 정의한 binding 이름**과 일치해야 합니다.
        예를 들어 템플릿이 ``coverPhoto`` binding을 요구하면
        ``binding_files={"coverPhoto": "photo.jpg"}`` 로 전달합니다.

        또는 사진을 미리 ``client.photos.upload(...)``로 업로드한 뒤
        ``parameters={"coverPhoto": "<업로드된 fileName>"}`` 으로 참조할 수도 있습니다.

        Args:
            book_uid: 책 UID
            template_uid: 표지 템플릿 UID
            parameters: 템플릿 파라미터 (제목, 사진 fileName 참조 등)
            binding_files: binding 이름 → 파일 경로 매핑 (권장)
            files: [DEPRECATED] 모든 파일을 ``files`` 단일 필드명으로 전송 — 서버가 거부합니다.
                대신 ``binding_files`` 를 사용하세요. 0.2.2 이전 코드 호환을 위해 보존.
        """
        multipart: list = [
            ("templateUid", (None, template_uid)),
            ("parameters", (None, json.dumps(parameters or {}, ensure_ascii=False))),
        ]

        opened: list = []
        try:
            if binding_files:
                for binding_name, path in binding_files.items():
                    f = open(path, "rb")
                    opened.append(f)
                    name = os.path.basename(path)
                    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
                    multipart.append((binding_name, (name, f, mime)))

            if files:
                warnings.warn(
                    "covers.create(files=...) 는 deprecated 입니다. "
                    "multipart 파일 part 이름은 템플릿 binding 이름과 일치해야 하므로 "
                    "binding_files={'coverPhoto': '...'} 형태로 전달하세요.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                for path in files:
                    f = open(path, "rb")
                    opened.append(f)
                    name = os.path.basename(path)
                    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
                    multipart.append(("files", (name, f, mime)))

            return self._client.post_form(f"/books/{book_uid}/cover", files=multipart)
        finally:
            for f in opened:
                f.close()

    def get(self, book_uid: str) -> dict:
        """표지 정보 조회"""
        return self._client.get(f"/books/{book_uid}/cover")

    def delete(self, book_uid: str) -> dict | None:
        """표지 삭제"""
        return self._client.delete(f"/books/{book_uid}/cover")
