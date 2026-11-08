# ADR-012: 테스트 실행 근거 형식과 요구사항 연결
- 상태: 승인(2026-11-05)
- 관련: D-12
- 날짜: 2026-11-05

## 배경
HITL 보고 표(§5.6)를 자동으로 만들려면 언어에 무관한 실행 근거가 필요하다.

## 선택지
1. JUnit XML을 실행 근거로 쓰고, 요구사항과 테스트의 연결은 `.kit/work/trace.json`(요구사항 → 테스트 locator)에 둔다. 태그 스캔은 보조로 쓴다.
2. 테스트 이름의 `[REQ-…]` 태그만 쓴다(언어마다 달라 깨지기 쉽다).

## 결정
**선택지 1.**
- JUnit XML은 `xml.etree.ElementTree`(표준 라이브러리)로 파싱한다.
- 실행하지 않은 테스트는 `NOT RUN`이다.
- JUnit XML에 없는 locator는 PASS로 표시하지 않는다(R-01).

## 근거
pytest, jest/vitest, go 모두 JUnit 리포터가 있다.

## 결과와 위험
- 위험: JUnit 방언마다 `skipped`·`error` 처리가 다르다 → fixture 3종(pytest, vitest, go-junit-report)으로 테스트한다.

## 되돌리는 방법
리포트 생성 모듈만 바꾸면 된다.

## 구현(P5-T4, 2026-11-07)
- `kit report tests --junit FILE... [--out FILE]`(`kit/junit.py`, `kit/evidence.py`, `kit/evidence_cli.py`).
- 태그 스캔은 하지 않는다. 연결은 `kit trace link`로만 한다(검토자 결정 2026-11-07, P5-T3).
- 짝짓기는 정규화 후 정확 일치(검토자 결정 2026-11-07). 이름만 같은 다른 파일의 테스트는 짝짓지 않으므로 잘못된 PASS가 나오지 않는다. 짝이 없는 추적 테스트는 NOT RUN, 짝이 없는 testcase는 "추적되지 않은 테스트"로 따로 보인다.
- fixture: pytest 출력은 실제로 생성했다. vitest와 go-junit-report는 이 PC에 없어 공개된 형식대로 작성했다(실제 도구 출력으로 다시 확인하는 것은 남은 일).
