# BookPrintAPI Python SDK — Examples

이 폴더의 예제는 **모두 백엔드(서버) 프로세스에서 실행되는 것을 전제**합니다.

> ⚠️ **SDK를 브라우저/프론트엔드 앱에 직접 번들하지 마세요.**
> API Key가 클라이언트에 노출되면 무단 사용으로 이어질 수 있습니다.
> 권장 구조: `브라우저 → 파트너 백엔드(SDK 소유) → BookPrint API`

## 실행 전 준비

```bash
# 1. 의존성 설치
pip install bookprintapi python-dotenv

# 2. .env 작성
cp .env.example .env   # 없으면 직접 생성
# .env 내용:
#   BOOKPRINT_API_KEY=sk_live_xxx   또는   sk_test_xxx
#   BOOKPRINT_BASE_URL=https://api.sweetbook.com/v1
```

## 예제 목록

| 파일 | 역할 | 특징 |
|---|---|---|
| `server_pipeline.py` | **책 생성 → 주문 E2E 파이프라인** | 실서비스의 백그라운드 작업(Celery, RQ 등) 이식용 |
| `simple_books.py` | CLI — 책 목록/생성/확정/삭제 | 단일 도메인 학습용 |
| `simple_credits.py` | CLI — 충전금 잔액/거래내역/Sandbox 충전 | 단일 도메인 학습용 |
| `simple_orders.py` | CLI — 주문 견적/생성/조회/취소/배송지 변경 | 단일 도메인 학습용 |
| `webhook_receiver.py` | Flask 웹훅 수신 서버 | 서명 검증 + 이벤트 분기 |

## server_pipeline.py — 책 생성 파이프라인 시퀀스

```
 파트너 백엔드 (이 예제)                           BookPrint API
 ─────────────────                                  ─────────────

 [1] 충전금 확인        ───  GET /credits/balance   ───→
                       ←────────── balance ──────────────
 [2] 책 생성           ───  POST /books             ───→
                       ←────────── bookUid ──────────────
 [3] 표지 사진 업로드   ───  POST /books/{uid}/photos ──→
                       ←────────── fileName ─────────────
     표지 생성         ───  POST /books/{uid}/cover ───→
 [4] 간지 + 내지 loop  ───  POST /books/{uid}/contents ─→
                              (템플릿별 파라미터)
 [5] 빈내지 패딩        ───  POST /books/{uid}/contents ─→
                              (최소 페이지 충족까지)
 [6] 발행면             ───  POST /books/{uid}/contents ─→
 [7] 책 확정            ───  POST /books/{uid}/finalize ─→
                              (부족 시 빈내지 추가 후 재시도)
 [8] 가격 견적          ───  POST /orders/estimate ─────→
 [9] 주문 생성          ───  POST /orders ──────────────→
                       ←────────── orderUid ─────────────
[10] 주문 상태 확인     ───  GET /orders/{uid} ─────────→
```

### 실전 배치 구조 권장

```
 (큐/스케줄러)
 Celery, RQ, APScheduler, cron  ──→  server_pipeline.py 로직
                                        ↓
                                   BookPrint API
```

실서비스에서는 이 파이프라인을 **동기 HTTP 응답 안에서 실행하지 말고** 큐 태스크로 분리하세요.
페이지 수가 많은 책은 전체 흐름이 수 분 걸릴 수 있습니다.

## 웹훅 수신 (webhook_receiver.py)

주문/제작/배송 상태 변경은 **폴링이 아니라 웹훅**으로 수신하세요.
`verify_signature()`로 반드시 서명을 검증하고, 200 응답을 2초 이내 반환해야 재시도가 걸리지 않습니다.

이벤트 타입: `order.created`, `order.cancelled`, `production.{confirmed,started,completed}`, `shipping.{departed,delivered}`
