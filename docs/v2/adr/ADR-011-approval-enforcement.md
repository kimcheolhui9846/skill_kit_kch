# ADR-011: 승인 강제 수준
- 상태: 승인(2026-11-05)
- 관련: D-11
- 날짜: 2026-11-05

## 배경
승인 강제 수준은 세 단계다.
- L0: 정책 문구
- L1: 상태 기계. `task start`가 선행 Task가 미승인이면 거부한다.
- L2: 훅. 사용자 프롬프트의 승인 표현을 기록하고, 에이전트가 승인 파일을 쓰지 못하게 막는다.

문서 근거:
- Claude: UserPromptSubmit·PreToolUse 훅, exit 2 차단(CC-HK)
- Codex: UserPromptSubmit·PreToolUse(apply_patch 포함) 훅. 다만 Codex 문서 스스로 "complete enforcement boundary가 아니다"라고 한다(CX-HK).

## 선택지
1. 원문안: L1을 공통으로 두고, L2는 Claude 전용 opt-in.
2. L1을 공통으로 두고, L2는 **두 에이전트 모두** opt-in.
3. L2를 기본으로 켠다.

## 결정
**선택지 2.**
- 같은 훅 스크립트(Python 표준 라이브러리)를 두 에이전트의 설정 형식에 맞춰 등록한다.
- Codex 쪽은 보고서와 문서에 "보조 수단이며 완전한 차단 경계가 아님"으로 표시한다.
- 승인 기록의 `by` 필드는 `human-hook`이다.

## 근거
두 에이전트 모두 공식 훅 규격이 있다(VERIFIED-DOC). Codex의 한계는 숨기지 않고 표시한다.

## 결과와 위험
- 테스트: 훅 스크립트 단위 테스트(승인 문구 판정, 승인 파일 쓰기를 막을 때의 exit code).
- 실제 에이전트와의 연동은 수동 체크리스트로 확인하고, 검토자가 확인한 뒤에 VERIFIED-RUN으로 표시한다.
- 위험: 셸 명령으로 우회할 수 있다 → L1 상태 기계와 `by` 구분으로 사후에 탐지한다.

## 구현(P5-T2b, 2026-11-07)
- 검토자 결정(2026-11-07): 승인은 프롬프트 전체가 승인 단어(선택적으로 Task ID)일 때만 기록한다. 훅이 켜진 작업 공간에서 `agent-recorded`는 거부한다. 설치는 project 범위만.
- 근거 확인(VERIFIED-DOC): 두 에이전트 모두 UserPromptSubmit 입력에 `prompt` 필드가 있고, PreToolUse는 exit 2(stderr가 이유)로 막는다. Codex는 `commandWindows`로 Windows 명령을 따로 준다. 프로젝트 훅은 두 에이전트 모두 폴더 신뢰 뒤에 로드되고, Codex는 `/hooks` 검토도 필요하다.
- PreToolUse는 exit 2가 아니라 JSON `hookSpecificOutput.permissionDecision: "deny"`(exit 0)로 막는다. 아래 M-05에서 Codex가 exit 2를 막지 않았기 때문이다.
- **M-05 실제 실행(2026-11-07, VERIFIED-RUN).** Claude Code 2.1.319, codex-cli 0.166.0, Windows 11. 격리한 `CLAUDE_CONFIG_DIR`·`CODEX_HOME`과 임시 작업 공간, 사용자 PC의 BAZE/FactChat 게이트웨이 설정을 썼다. Codex는 `--dangerously-bypass-hook-trust`로 훅 신뢰를 이번 실행에만 주었고, 차단 시험은 검토자 승인 아래 샌드박스를 끄고 사용자가 직접 실행했다.
  - 두 에이전트 모두: `승인 T-001` → `by: human-hook` 기록. 에이전트가 `task approve` 실행 → 차단. tasks.json 쓰기·삭제 → 차단, 파일 해시 불변. 대조군 `python --version`은 실행됨.
  - 발견 1: Codex는 exit 2를 "hook Failed"로 표시하고 도구를 실행했다(tasks.json이 실제로 지워짐). JSON deny로 바꾼 뒤 "hook PreToolUse Blocked"로 막혔다.
  - 발견 2: Codex가 프롬프트 하나에 UserPromptSubmit을 두 번 실행해, 두 번째 "not SUBMITTED" 안내가 에이전트를 헷갈리게 했다. 같은 프롬프트의 반복(10분 안)은 같은 성공 안내를 돌려주게 고쳤다.
  - 발견 3: 첫 차단 시험에서 L1(`agent-recorded` 거부)이 두 번째 방어선으로 승인 기록을 막았다.
  - Codex 프로젝트 훅은 실제 사용 시 `/hooks`에서 검토·신뢰해야 동작한다. `codex exec`의 기본 샌드박스 환경에서는 모든 셸 명령이 Codex 정책에 막혀 차단 시험을 판별할 수 없었다.

## 되돌리는 방법
훅 등록 키를 지우면 L1만 남는다.
