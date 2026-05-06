# Changelog

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
