# Changelog

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
