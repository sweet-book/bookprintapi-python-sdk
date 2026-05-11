# Changelog

## 0.4.0 (2026-05-11)

### Added — list 응답 envelope 통일 호환 레이어

photobook-api commit `6fbf346` (2026-05-11) 의 list 응답 envelope 평탄화에 SDK 가 호환 레이어로 흡수. 사용자 코드 마이그레이션 불필요.

- **`ResponseParser.to_flat_list_response()`** 신규 — 신·구 envelope 둘 다에서 동일한 `{ success, data: list, pagination, message }` shape 반환
- 모든 list 메서드 (sync 5 + async 3 = 8건) 가 SDK 내부에서 평탄화 적용:
  - `client.books.list()` / `client.orders.list()` / `client.templates.list()`
  - `client.photos.list(book_uid)` / `client.book_specs.list()`
  - `client.credits.get_transactions()`
  - `AsyncClient.books.list()` / `AsyncClient.orders.list()` / `AsyncClient.credits.get_transactions()`
- 구 photos 응답의 `data.totalCount` → `pagination.total` 로 자동 흡수

### 변경된 envelope 명세

**Before** (구):
```json
{ "success": true, "data": { "books": [...], "pagination": {...} } }
```

**After** (신, commit 6fbf346 이후):
```json
{
  "success": true,
  "data": [...],
  "pagination": { "total": 120, "limit": 20, "offset": 0, "hasNext": true }
}
```

SDK 사용자는 두 envelope 모두에서 `result["data"]` 가 항상 배열, `result["pagination"]` 이 항상 최상위 — 동일한 코드로 두 시점 모두 호환.

### Tests
- `tests/test_response_envelope.py` 7건 추가 (신·구 envelope, totalCount 흡수, 엣지 케이스)
- `pytest` 23/23 통과

### Migration
v0.3.x → v0.4.0: 추가 호환 only. 기존 list 메서드 시그니처/리턴 dict 의 외부 shape 그대로 (`{ success, data, pagination, message }`).

이슈: https://github.com/sweet-book/bookprintapi-python-sdk/issues/2

## 0.3.0 (2026-05-07)

### Added — SDK 헬퍼 (다단계 플로우 한 호출)

설계 문서 `11_sdk_helpers_design.md` v0.1 구현. R011-S01 (16p 책에 35+ API 호출) / C08 (다단계 실패 컨텍스트) 대응.

- **`client.helpers.create_book_from_template(...)`**: TEMPLATE 모드 책 한 권을 `books.create → covers.create → contents.insert(N) → books.finalize` 한 호출로 처리. 반환 `BookBuildResult` (book_uid, content_pages, finalized, page_count)
- **`client.helpers.upload_pdf_and_order(...)`**: PDF_UPLOAD 모드 책 + PDF 2종 + finalize + 견적 + 주문까지 한 호출. 반환 `PdfOrderBuildResult` (book_uid, order_uid, finalized, estimate, order). `fail_on_insufficient_credit` 옵션으로 estimate `creditSufficient=false` 시 주문 전 차단

#### 새 예외: `SweetbookHelperError`
- `stage`: `HelperStage` 상수 — `BOOK_CREATE` / `COVER_CREATE` / `CONTENT_INSERT` / `BOOK_FINALIZE` / `PDF_UPLOAD_COVER` / `PDF_UPLOAD_CONTENTS` / `ORDER_ESTIMATE` / `ORDER_CREATE` / `VALIDATION`
- `code`: `HelperErrorCodes.SDK_HLPR_*` 임시 코드 (C03 확정 시 표준 errorCode 로 매핑 예정)
- `book_uid`: `BOOK_CREATE` 성공 후부터 채워짐. 파트너가 `client.books.delete(e.book_uid)` 로 명시적 cleanup 가능
- `partial`: 단계별 부분 성공 정보 (`bookCreated` / `coverCreated` / `contentsInserted[]` / `finalized` 등)
- `cause`: 원 `ApiError` 예외 보존
- `content_index`: `CONTENT_INSERT` 실패 시 어느 페이지인지 (0-based)
- `user_message()`: cause 가 `ApiError` 면 그쪽으로 위임, 아니면 자체 메시지

#### 정책 (설계 §4)
- 자동 재시도 / 자동 롤백 안 함 — 파트너가 `partial` / `book_uid` 보고 판단
- 호출 전 클라이언트측 검증: `book_spec_uid` 비어있지 않음, `contents` ≥ 1, `shipping.recipientName` 등

### Tests
- `tests/test_helpers.py` 16건 추가 (happy path / validation / 단계별 실패 / partial 컨텍스트 / user_message 위임). `pytest` 16/16 통과

### Notes
- Pythonic 한 개별 kwargs 시그니처 채택 (설계 §7-5). Node/Java 는 자체 언어 컨벤션에 맞춰 별도 시그니처
- helpers 가 신설되었지만 기존 sub-client (`client.books.create` 등) 동작은 그대로 보존. 하위 호환

## 0.2.2 (2026-05-06)

### Fixed
- `covers.create` / `contents.insert` 의 multipart 파일 part 이름 회귀 정정.
  서버는 **템플릿이 정의한 binding 이름**(예: `coverPhoto`, `mainPhoto`)을 multipart part name 으로
  요구합니다. 0.2.1 까지의 SDK는 모든 파일을 `files` (Covers) / `rowPhotos` (Contents) 단일
  필드명으로 보내 서버가 `필수 이미지 파라미터 'X' 가 제공되지 않았습니다` 로 거부했습니다.

### Added
- `covers.create(..., binding_files={"coverPhoto": "photo.jpg"})` — binding 이름 → 파일 경로 매핑 (권장)
- `contents.insert(..., binding_files={"mainPhoto": p1, "subPhoto": p2})` — 동일 패턴
- 파일 확장자 → MIME 자동 추정 (`mimetypes.guess_type`), 기존 image/jpeg 하드코딩 제거

### Deprecated
- `covers.create(..., files=[...])` 와 `contents.insert(..., files=[...])` — 호환을 위해 보존하지만
  `DeprecationWarning` 출력. 다음 메이저 버전에서 제거 예정.

### Migration

```python
# Before (v0.2.1, 깨짐)
client.covers.create(book_uid, template_uid="...", files=["photo.jpg"])

# After (v0.2.2)
client.covers.create(
    book_uid,
    template_uid="...",
    binding_files={"coverPhoto": "photo.jpg"},  # binding 이름은 template 정의에 맞춰
)
```

### Notes
- Java SDK (bookprintapi-java-sdk) 와 Node SDK 0.2.2 도 같은 회귀 정정. 모두 v0.2.2 동일 동작.
- 발견 경위: Java SDK 통합 테스트가 sandbox 99 에서 3시나리오로 검증 → 서버는 binding 이름이 정답.
  Python SDK 도 sandbox 99 실호출로 같은 응답 확인 후 정정.

## 0.2.1 (2026-04-29)

마이그레이션 회귀테스트 후 examples 핫픽스. SDK 본체는 변동 없음 — Python SDK는 클라이언트 메서드가 raw dict를 그대로 반환하는 설계여서 v1 평탄화 응답을 SDK 본체에서 처리할 곳이 없음.

### Fixed
- `examples/simple_books.py` — 책 목록 조회 시 v1 평탄화 응답(`data: [...]` + 최상위 `pagination`)에서 항상 빈 리스트로 빠지던 회귀. dict/list 타입 분기로 신/구 응답 모두 호환
- `examples/simple_orders.py` — `--status PAID` 같은 문자열 enum 입력 시 `int()` 캐스팅으로 ValueError 발생하던 회귀. 숫자/문자열 자동 분기
- `examples/simple_orders.py` — 주문 목록 평탄화 응답 회귀 동일 수정. `STATUS_NAMES` 숫자키 매핑 → `OrderStatus`/`ORDER_STATUS_FROM_CODE` 활용한 `status_label()` 헬퍼로 교체

## 0.2.0 (2026-04-28)

서버 master 대비 develop 브랜치 변경사항(99번 v1 적용분) 반영.

### Added
- `errorcodes.ErrorCodes` — 24종 errorCode 카탈로그 상수 (Generic 8 + Specific 16)
- `errorcodes.ConstraintTypes` — fieldErrors[].constraint 열거값
- `order_status.OrderStatus` — 주문 상태 문자열 enum 12종 (`PAID`, `PDF_READY`, ...)
- `ORDER_STATUS_CODE` / `ORDER_STATUS_FROM_CODE` — 숫자 ↔ 문자열 매핑 dict
- `exceptions.FieldError` — `field` / `message` / `current_value` / `required_value` / `constraint` 5필드 객체
- `ApiError.field_errors` — 신규 속성 (FieldError 리스트)
- `ApiError.field_error(name)` — 헬퍼
- `ApiError.user_message()` — `errors[0]` 또는 `message` 폴백
- `ApiError.data` — 일부 errorCode(`ERR_INSUFFICIENT_CREDIT` 등)에서 진단 객체
- `ResponseParser.success` / `get_error_code()` / `get_errors()` / `get_field_errors()` / `get_field_error(name)` / `get_page_meta()` 신규 메서드
- `TemplatesClient.get_schema(template_uid)` — `GET /templates/{uid}/schema` (JSON Schema draft-07)

### Changed
- `ApiError.from_response()` — `errorCode` (camelCase) 우선 파싱, snake_case fallback 유지. `fieldErrors[]` 구조화 파싱
- `ResponseParser.get_pagination()` — 평탄화 응답에서 최상위 `pagination` 우선 읽음, 구버전은 `data.pagination` fallback
- `ResponseParser.get_list()` — 평탄화 응답(`data: [...]`) 우선, 구버전 `data: {orders|items|...}` 자동 흡수
- `OrdersClient.list(status=...)` — 문자열 enum도 허용 (기존 숫자도 호환)
- `BooksClient.get()` — docstring에 `pageMeta` 응답 포함 명시

### Migration Notes (v0.1 → v0.2)
- 코드 분기는 `error_code` 문자열 비교 대신 `bookprintapi.ErrorCodes.*` 상수 권장
- 주문 상태 분기는 `order["orderStatus"] == OrderStatus.PAID` 형태로
- 사용자 표시 메시지는 `error.user_message()` 또는 `error.details[0]`
- `ApiError.field_errors` 로 폼 UI 하이라이트 자동화 가능

### Compatibility
- 응답 shape 6필드 고정(`success` / `errorCode` / `message` / `data` / `errors[]` / `fieldErrors[]`)
- 성공 응답은 변경 없음
- 구버전 `error_code` snake_case 응답도 fallback 처리
