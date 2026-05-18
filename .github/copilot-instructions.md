# RICS BACS 플랫폼 — Copilot 헌법

## 프로젝트
폐쇄망 BACS(RICS MA3) UDP 헬스체크 모듈.
BACS 장비에 UDP 패킷을 전송하고 응답을 분석하여 장비 상태를 판단.

## UDP 프로토콜 (확정)
포트: 7788
요청 패킷 SE_MA_Connect_REQ (9바이트):
  01 10 | 05 00 | 00 00 | 12 | 00 00
응답 패킷 MA_SE_Connect_RPT (13바이트):
  01 01 | 0D 00 | 00 00 | 92 | 08 00 | [8바이트 alive]
판정: 응답 오면 ONLINE / 타임아웃이면 OFFLINE / 응답 형식 틀리면 OFFLINE

## 스택
Python 3.11+
asyncio (비동기 UDP 필수)
pytest + pytest-asyncio (테스트)

## NEVER
- 동기(sync) 방식 UDP 구현 금지. 전부 asyncio.
- Mock/Dummy 데이터 금지. 실제 패킷 구조만.
- 파일 전체 재작성 금지. 해당 부분만 수정.
- 추측으로 에러 수정 금지. 재현→가설→확인 순서.

## ALWAYS
- 새 기능 시작 전 플랜 모드 먼저.
- 구현 전 테스트 코드 먼저 작성 (TDD).
- 구현 + pytest 단위테스트 항상 같이.
- 한국어 주석 (핵심 로직).

## 상태 Enum
```python
class HealthStatus(str, Enum):
    ONLINE  = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
```

## 테스트 명령어
```bash
pytest tests/ -v
```

## ⛔ 미결 사항 — 확정 전 구현 금지
| 항목 | 상태 |
|------|------|
| 호출시험 프로토콜 (TCP) | ⛔ 별도 개발 단계에서 진행 |
| 지도 BACS 위치 좌표 | ⛔ 미확정 |
| 인증 방식 | ⛔ 미확정 |