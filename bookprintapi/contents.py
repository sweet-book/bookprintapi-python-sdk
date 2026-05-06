"""BookPrintAPI SDK — Contents"""

from __future__ import annotations

import json
import mimetypes
import os
import warnings
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .client import Client


class ContentsClient:
    """책 내지(본문) 페이지 삽입/삭제"""

    def __init__(self, client: Client):
        self._client = client

    def insert(self, book_uid: str, *, template_uid: str,
               parameters: dict[str, Any] | None = None,
               binding_files: dict[str, str] | None = None,
               files: list[str] | None = None,
               break_before: Literal["page", "spread", "column"] | None = None) -> dict:
        """내지 페이지 삽입

        multipart 파일 part 이름은 **템플릿이 정의한 binding 이름**과 일치해야 합니다.
        예를 들어 템플릿이 ``mainPhoto``, ``subPhoto`` binding을 요구하면
        ``binding_files={"mainPhoto": p1, "subPhoto": p2}`` 로 전달합니다.

        Args:
            book_uid: 책 UID
            template_uid: 내지 템플릿 UID
            parameters: 템플릿 파라미터 (텍스트, 사진 fileName 참조 등)
            binding_files: binding 이름 → 파일 경로 매핑 (권장)
            files: [DEPRECATED] 모든 파일을 ``rowPhotos`` 단일 필드명으로 전송 — 서버가 거부합니다.
                대신 ``binding_files`` 를 사용하세요. 0.2.2 이전 코드 호환을 위해 보존.
            break_before: 페이지 나눔 ("page": 새 페이지, "spread": 새 스프레드)
        """
        multipart: list = [
            ("templateUid", (None, template_uid)),
            ("parameters", (None, json.dumps(parameters or {}, ensure_ascii=False))),
        ]

        params = {}
        if break_before:
            params["breakBefore"] = break_before

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
                    "contents.insert(files=...) 는 deprecated 입니다. "
                    "multipart 파일 part 이름은 템플릿 binding 이름과 일치해야 하므로 "
                    "binding_files={'mainPhoto': '...'} 형태로 전달하세요.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                for path in files:
                    f = open(path, "rb")
                    opened.append(f)
                    name = os.path.basename(path)
                    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
                    multipart.append(("rowPhotos", (name, f, mime)))

            return self._client.post_form(
                f"/books/{book_uid}/contents", files=multipart, params=params,
            )
        finally:
            for f in opened:
                f.close()

    def clear(self, book_uid: str) -> dict:
        """모든 내지 페이지 삭제 (표지는 유지)"""
        return self._client.delete(f"/books/{book_uid}/contents")
