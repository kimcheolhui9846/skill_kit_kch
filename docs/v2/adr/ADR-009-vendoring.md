# ADR-009: 외부 리소스를 저장소에 포함할지 참조할지
- 상태: 승인(2026-11-05)
- 관련: D-09, REQ-SRC-006/007, R-07, R-11
- 날짜: 2026-11-05

## 배경
사용자 목록 49개와 OMX는 라이선스가 섞여 있다. 대부분 MIT·Apache지만, 라이선스가 감지되지 않는 것이 4개, `other`가 2개, AGPL이 1개다(08_USER_SOURCES).

## 선택지
1. 작은 허용 라이선스 스킬의 텍스트만 원문·LICENSE와 함께 `third_party/<owner>-<repo>/`에 넣는다. 나머지는 버전을 고정해 참조만 한다.
2. 전부 참조만 한다(오프라인 설치가 불가능해진다).
3. 전부 넣는다(라이선스 위반 위험).

## 결정
**선택지 1.**
- 허용 라이선스 목록: MIT, Apache-2.0, BSD-2/3, ISC, 0BSD, CC-BY-4.0, Unlicense.
- 그 밖의 라이선스는 `sources.lock.json`에 `mode: reference`로 남기고, 설치할 때 안내만 출력한다.
- MCP 서버와 플러그인은 버전을 고정해 참조만 한다. 키트가 대신 내려받거나 실행하지 않는다.
- OMX(MIT)의 스킬·agents·prompts 텍스트는 vendored로 넣는다(REQ-USER-005).

## 근거
원문 권장안, 원문 §14.3, R-07.

## 결과와 위험
- 테스트 V-24: `mode: vendored`인 항목은 모두 허용 라이선스이고 LICENSE 파일이 있다.
- 위험: GitHub의 라이선스 감지가 틀릴 수 있다 → LICENSE 파일 본문도 대조한다(D-21).

## 되돌리는 방법
`third_party/`의 항목을 지우고 `mode: reference`로 바꾸면 된다.
