# ADR-006: 대상 작업 공간의 상태 디렉터리
- 상태: 승인(2026-11-05)
- 관련: D-06
- 날짜: 2026-11-05

## 배경
v1은 `.kit/state.json`(`version 1`, `files {rel: sha256}`)과 `.kit/backups/<stamp>/`를 쓴다 [확인됨: `kit/fsops.py:11,53-65`]. 기준선 설치 트리에도 `.kit/state.json`이 있다. 키트는 `.gitignore`를 다루지 않는다(코드에서 참조 없음).

## 선택지
1. 원문안: `.kit/state/install-manifest.json`을 새로 두고 v1 state를 인수한다.
2. `.kit/state.json`을 v2 형식으로 올린다(기존 경로의 바이트 동일성이 깨진다).

## 결정
**선택지 1.**
- 기존 경로는 계속 `.kit/state.json`(v1)만 쓴다(골든 동일성).
- 새 경로는 다음을 쓴다:
  - `.kit/state/install-manifest.json`: 파일 해시, JSON 포인터, 에이전트, 정책, 프로필
  - `.kit/logs/`
  - `.kit/backups/`(기존)
  - `.kit/work/`: HITL 상태
- 새 경로는 v1 state를 만나면 읽어서 매니페스트로 인수하되, v1 파일은 지우지 않는다.
- `.gitignore`는 수정하지 않고 권장 항목만 출력한다.

## 근거
기준선 트리에 `.kit/state.json`이 포함된다 [확인됨: `install-snapshots/core__default.json`].

## 결과와 위험
- 위험: 같은 작업 공간을 기존 경로와 새 경로로 번갈아 설치하면 상태가 둘로 나뉜다 → 새 경로가 v1을 읽어 병합하고, 기존 경로는 매니페스트를 무시한다. 이 동작을 문서화한다.

## 되돌리는 방법
매니페스트 파일을 지우면 v1 상태만 남는다.
