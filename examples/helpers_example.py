#!/usr/bin/env python3
"""BookPrintAPI Python SDK — Helpers 예제 (v0.3.0+)

⚠️  백엔드/CLI 실행 전제. SDK를 브라우저/프론트엔드에 번들하지 마세요.

다단계 플로우(`books.create → covers.create → contents.insert ×N → finalize`) 를
한 호출로 처리하는 ``client.helpers.*`` 사용 시나리오 데모.

사용법::

    python helpers_example.py template <coverTplUid> <contentTplUid> <photoPath>
    python helpers_example.py pdf <coverPdfPath> <contentsPdfPath>

환경변수::

    BOOKPRINT_API_KEY   API Key (필수)
    BOOKPRINT_BASE_URL  API 서버 URL (기본: https://api.sweetbook.com/v1)
"""

import io
import os
import sys
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from bookprintapi import (
    Client,
    ErrorCodes,
    HelperStage,
    SweetbookHelperError,
)


def cmd_template(args: list[str]) -> None:
    """createBookFromTemplate 시나리오.

    cover_template_uid + content_template_uid + photo_path 인자로 책 한 권 생성.
    동일 사진을 cover의 ``coverPhoto`` binding 과 contents 2페이지의
    ``mainPhoto`` binding 으로 사용. 마지막에 finalize 까지.
    """
    if len(args) < 3:
        print("사용법: helpers_example.py template <coverTplUid> <contentTplUid> <photoPath>")
        return

    cover_tpl, content_tpl, photo = args[0], args[1], args[2]
    if not os.path.exists(photo):
        print(f"파일 없음: {photo}")
        sys.exit(1)

    client = Client()
    try:
        result = client.helpers.create_book_from_template(
            book_spec_uid="PHOTOBOOK_A4_SC",
            cover_template_uid=cover_tpl,
            cover_params={"title": "Helpers 데모 책"},
            cover_binding_files={"coverPhoto": photo},
            contents=[
                {
                    "template_uid": content_tpl,
                    "params": {"text": "헬퍼 페이지 1"},
                    "binding_files": {"mainPhoto": photo},
                },
                {
                    "template_uid": content_tpl,
                    "params": {"text": "헬퍼 페이지 2"},
                    "binding_files": {"mainPhoto": photo},
                    "break_before": "page",
                },
            ],
            title="Helpers 데모 책",
        )
        print("=" * 50)
        print("  책 생성 완료")
        print("=" * 50)
        print(f"  bookUid     : {result.book_uid}")
        print(f"  cover page  : {result.cover_page_num}")
        print(f"  내지 페이지 : {len(result.content_pages)}")
        for i, p in enumerate(result.content_pages):
            print(f"    [{i}] pageNum={p.get('pageNum')}, side={p.get('pageSide')}")
        print(f"  finalized   : {result.finalized}")
        print(f"  pageCount   : {result.page_count}")

    except SweetbookHelperError as e:
        _handle_helper_error(client, e)


def cmd_pdf(args: list[str]) -> None:
    """uploadPdfAndOrder 시나리오.

    PDF_UPLOAD 모드 책 생성 + PDF 2종 업로드 + finalize + 견적 + 주문까지.

    주문은 fail_on_insufficient_credit=True 라 잔액 부족 시 ORDER_ESTIMATE 단계에서
    SweetbookHelperError(CREDIT_INSUFFICIENT) 발생, 실 주문 차단.

    배송지는 데모 더미 — 실제 사용 시 본인 정보로 교체.
    """
    if len(args) < 2:
        print("사용법: helpers_example.py pdf <coverPdfPath> <contentsPdfPath>")
        return

    cover_pdf, contents_pdf = args[0], args[1]
    for p in (cover_pdf, contents_pdf):
        if not os.path.exists(p):
            print(f"파일 없음: {p}")
            sys.exit(1)

    client = Client()
    try:
        result = client.helpers.upload_pdf_and_order(
            book_spec_uid="PHOTOBOOK_A4_SC",
            page_count=24,
            cover_pdf=cover_pdf,
            contents_pdf=contents_pdf,
            shipping={
                "recipientName": "홍길동",
                "recipientPhone": "010-1234-5678",
                "postalCode": "06100",
                "address1": "서울특별시 강남구 테헤란로 123",
                "address2": "4층",
            },
            quantity=1,
            order_external_ref="HELPERS-DEMO-001",
            fail_on_insufficient_credit=True,
        )
        print("=" * 50)
        print("  PDF 업로드 + 주문 완료")
        print("=" * 50)
        print(f"  bookUid  : {result.book_uid}")
        print(f"  orderUid : {result.order_uid}")
        print(f"  finalized: {result.finalized}")
        if result.estimate:
            ed = result.estimate.get("data", {}) or {}
            print(f"  결제금액 : {ed.get('paidCreditAmount', 0):,}원")

    except SweetbookHelperError as e:
        _handle_helper_error(client, e)


def _handle_helper_error(client: Client, e: SweetbookHelperError) -> None:
    """SweetbookHelperError 분기 패턴 데모.

    11_sdk_helpers_design.md § 4.1 (자동 롤백 안 함) 정책. 파트너가 stage / cause /
    book_uid / partial 보고 명시적 cleanup 결정.
    """
    print("=" * 50)
    print(f"  헬퍼 실패 — stage={e.stage}")
    print("=" * 50)
    print(f"  code      : {e.code}")
    print(f"  bookUid   : {e.book_uid}")
    if e.content_index is not None:
        print(f"  contentIdx: {e.content_index}")
    print(f"  message   : {e.user_message()}")
    print(f"  partial   : {json.dumps(e.partial, ensure_ascii=False, default=str)}")
    if e.cause:
        print(f"  cause     : {e.cause}")
        if hasattr(e.cause, "error_code") and e.cause.error_code:
            print(f"  cause.code: {e.cause.error_code}")

    # stage 기반 분기 — 단계별 cleanup 정책
    if e.stage == HelperStage.VALIDATION:
        print("\n  → 클라이언트측 검증 실패 (호출 전 차단). 입력 값 확인 후 재시도.")

    elif e.stage == HelperStage.CONTENT_INSERT:
        print(f"\n  → 페이지 #{e.content_index} 삽입 실패. 책({e.book_uid})은 유지됨.")
        print("     사용자에게 해당 페이지 재입력 후 contents.insert 직접 호출 권장.")

    elif e.stage == HelperStage.BOOK_FINALIZE:
        # cause 가 INSUFFICIENT_PAGES / FINALIZE_PREREQ_UNMET 면 페이지 추가 안내
        if e.cause and getattr(e.cause, "error_code", None) in (
            ErrorCodes.INSUFFICIENT_PAGES, ErrorCodes.FINALIZE_PREREQ_UNMET,
        ):
            print(f"\n  → finalize 전제조건 미달. 책({e.book_uid})은 유지. 추가 페이지 후 finalize 재시도.")
        else:
            print(f"\n  → finalize 실패. 책({e.book_uid}) 상태 점검 후 재시도 또는 삭제.")

    elif e.stage in (HelperStage.PDF_UPLOAD_COVER, HelperStage.PDF_UPLOAD_CONTENTS):
        print(f"\n  → PDF 업로드 실패. 파일 규격(456×303mm 등) 확인 후 재시도.")

    elif e.stage == HelperStage.ORDER_ESTIMATE:
        if e.code == "SDK_HLPR_CREDIT_INSUFFICIENT":
            print(f"\n  → 충전금 부족 — 주문은 차단됨. 책({e.book_uid})은 finalize 까지 진행 완료.")
            print("     충전 후 직접 orders.create 호출 가능 (책 재생성 불필요).")
        else:
            print(f"\n  → 견적 조회 실패. 책({e.book_uid}) 유지. 재시도 또는 삭제.")

    else:
        # BOOK_CREATE / COVER_CREATE / ORDER_CREATE 등 — 책 폐기 권장
        if e.book_uid:
            print(f"\n  → 책 폐기 (books.delete({e.book_uid}))...")
            try:
                client.books.delete(e.book_uid)
                print("     OK — 정리 완료.")
            except Exception as cleanup_err:
                print(f"     cleanup 실패 (수동 처리 필요): {cleanup_err}")

    sys.exit(1)


COMMANDS = {
    "template": cmd_template,
    "pdf": cmd_pdf,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Commands:", ", ".join(COMMANDS.keys()))
        return
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"알 수 없는 명령: {cmd}")
        print("Commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)
    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
