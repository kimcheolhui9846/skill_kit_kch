# 03 개발 계획 (P1-T5)

- 기준: `00_PROMPT.md`(원문) + `00_ADDENDUM.md`(보강), Phase 1 분석 결과(`01_ANALYSIS.md`)
- 진행 규칙은 원문 §5 그대로: Task 완료마다 보고하고 승인을 받는다. Phase 1 승인 후 로컬 브랜치 `feat/v2-multi-agent`를 만든다.

## 1. Phase/Task 조정

원문 §7~§12를 따르되 다음을 바꾸거나 더한다.

| 위치 | 조정 | 이유 |
|---|---|---|
| P3-T1 골든 | 정규화 대상에 `Environment:`·`Tools:` 줄과 `tool:pytest/ruff` 탐지 결과를 추가. 스냅샷 생성 스크립트(`baseline/install-snapshots/snapshot.py`)를 `devtools/`로 옮겨 재사용 | 머신 의존 값(`install-snapshots/README.md`) |
| P3-T4 ClaudeAdapter | `CLAUDE.md` 처리에 "AGENTS.md 대체 읽기" 규칙 반영(R-5) | CC-MEM |
| P4-T1 스킬 원본 | **미러 `.agents/skills`에는 기존 11개만** 둔다. 새 경로용 스킬(외부 채택분, `launch-compliance-check`)은 `shared/skills/`에만 | R-3 |
| P4-T2 스킬 검증 | 키트 작성 규칙 검증(기존)과 공식 제약 검증(외부 스킬용)을 분리 | R-7 |
| P4-T3 평가 | 대상: 사용자 목록 49개 + OMX(U-51) + 원문 §14.1 후보. UNRESOLVED는 2차본에서 0개 | REQ-SRC-006~008 |
| P4-T7 (신규) | user 범위 설치·제거·복구와 `capture` | REQ-USER-001~004 |
| P5-T5 반례 | 신규 `counterexample-generator`를 만들지 않고 기존 `counterexample-hunter`를 확장(블랙박스 단계, `NEEDS_SPEC`, 기록 형식 추가)하는 안을 먼저 검토 | 01_ANALYSIS §0 |
| P5-T6 알고리즘 | `algorithm-decision-reviewer` 대신 기존 `algorithm-options`를 확장하는 안을 먼저 검토. `data-quality-validator`는 신규 | 01_ANALYSIS §0 |
| P5 | `launch-compliance-check` 스킬 추가(REQ-SKILL-001) | 보강 |
| P5-T2 / P5-T2b (신규) | P5-T2는 L1(`kit task` 상태 기계·보고서 검사·승인 기록과 `task-approval` 스킬)만. L2 승인 훅(D-11, `human-hook`)은 P5-T2b로 나눈다 | 검토자 결정 2026-11-07 |

## 2. 결정 사항(ADR) 1차 의견

| ID | 원문 권장안 | 1차 의견 |
|---|---|---|
| D-01 | 원본을 `shared/skills/`로, `.agents/skills`는 생성 미러 | **동의, 단 미러는 기존 11개로 고정**(R-3). 기존 11개는 원본=미러가 되도록 하고 동기화 검사 테스트 추가 |
| D-02 | 기존 호출 = `install --agent codex --policy restricted`, 바이트 단위 동일 | 동의. 근거: `cli.py`는 위치 인수를 받지 않음 [확인됨: `kit/cli.py:36-65`] → 첫 토큰이 알려진 서브커맨드면 새 경로 |
| D-03 | 기존 마커 계속 인식, 바꾸려면 `migrate`로만 | **결정됨(Q4): 마커를 바꾸지 않는다**. 새 파일(`CLAUDE.md`, user 범위)에도 `hackathon-kit` 마커를 그대로 쓰면 마이그레이션 코드가 필요 없다. 이름이 어색한 비용만 있음 |
| D-04 | 정책 원문에서 렌더링 | 동의. 추가: `both`·`claude` 설치의 `CLAUDE.md` 구간 맨 위에 `@AGENTS.md`를 쓰는 안과 비교(문서상 둘 다 유효, CC-MEM) |
| D-05 | JSON 키 소유 + 값 해시 | 동의. 저장 시 키 순서 보존은 `json`의 dict 순서로 가능, 들여쓰기는 기존 파일에서 추정 [가정] |
| D-06 | `.kit/` 확장 | 동의. 기존 `.kit/state.json`(v1)을 읽어 `install-manifest`로 올리는 인수 절차 포함. user 범위는 `~/.kit-backups/`와 `~/.kit-state/`(가칭) |
| D-07 | 프로필 v2 스키마, `--profile a,b` | 동의 |
| D-08 | 기존 5개 프로필 설치 내용 불변, 새 스킬은 팩으로 | 동의 |
| D-09 | 작은 허용 라이선스 스킬 텍스트만 vendoring | 동의. AGPL(U-14) 등은 참조만 |
| D-10 | 플러그인은 선언·안내만 | 동의. Codex(`[plugins."x@m"]`)와 Claude(`enabledPlugins`) 모두 공식 선언 경로가 있다(02 매트릭스) |
| D-11 | L1 공통, L2는 Claude 전용 opt-in | **수정 제안: L2를 두 에이전트 모두 opt-in으로.** Codex에도 UserPromptSubmit·PreToolUse(apply_patch 포함) 훅이 문서화되어 있다(CX-HK). 단 Codex 문서 자체가 "complete enforcement boundary가 아니다"라고 함 |
| D-12 | JUnit XML + trace.json | 동의 |
| D-13 | bootstrap + 서브커맨드 | 동의 |
| D-14 | 새 경로 네트워크 확인, 비대화형은 `--yes` 없으면 SKIPPED | 동의 |
| D-15 | 정책 축 분리 | 동의 |
| D-16 | 이름 유지 | 동의(레포 이름은 이미 `skill_kit_kch`, 패키지 이름은 `hackathon-agent-kit` 유지) |
| D-17 | Windows 검증 | **이 PC가 실제 Windows 11이다.** Windows 항목은 `VERIFIED-RUN`이 가능하고, 반대로 **Linux가 NOT RUN**이다(WSL 여부 미확인). PowerShell 5.1은 있고 7은 없음 |
| D-18 (신규) | user 범위 설치 설계 | plan(diff) → TTY 확인/`--yes` → 백업 → 소유 구간·키만 수정. Claude 사용자 MCP는 명령 출력 방식 |
| D-19 (신규) | capture 정제 규칙 | 허용 목록 방식(이식할 키만 명시적으로 고름) > 차단 목록 방식. 새 키가 생겨도 자동으로 새지 않게 |
| D-20 (신규) | 사용자 목록 우선 규칙과 경로 분리 | REQ-SRC-007 그대로. 미러 고정(R-3)과 한 세트 |

## 3. 예상 위험

`01_ANALYSIS.md` §7 R-1~R-11 참고. 일정상 가장 큰 위험은 **P4-T3 외부 평가의 양**(49 + 28개)이다. 원문 §14.2의 9개 기준을 항목마다 채우면 Task 하나가 매우 커진다 → 원문 §14.3 "겹치면 하나만"을 먼저 적용해 묶음(디자인 MCP 5개, 컨텍스트 절약 도구 5개, 코드 인덱싱 4개, 오케스트레이터 4개 등)별로 비교하고, 묶음마다 승인받는 방식을 제안한다.

## 4. 검토자에게 묻는 질문 (2026-11-05 모두 답변됨 → `00_ADDENDUM.md` §2-1)

| # | 질문 | 1차 의견 |
|---|---|---|
| Q1 | REQ-COMPAT-002의 "기존 8개 스킬"을 "기존 11개 스킬"로 고쳐도 되는가? | 고친다 |
| Q2 | `08_USER_SOURCES.md`의 UNRESOLVED 11개(U-08, U-11, U-17, U-18, U-23, U-24, U-25, U-26, U-34, U-39, U-41)는 각각 무엇을 뜻하는가? 링크가 있으면 가장 정확하다 | — |
| Q3 | 기존 경로의 도구 설치(`uv tool install`/`pip install --user`)는 원문 R-06·REQ-SAFE-008의 예외로 명시해도 되는가? | 예외로 명시(동작 유지) |
| Q4 | 관리 구간 마커를 바꾸지 않는 안(D-03)에 동의하는가? | 동의 권장 |
| Q5 | Codex 안에서 `/skills`를 실행해 `~/.codex/skills`의 OMX·superpowers 스킬이 보이는지 확인해 줄 수 있는가? (user 범위 설치 경로 결정에 필요, R-9) | — |
| Q6 | OMX(oh-my-codex) 스킬 28개와 `~/.codex/agents`·`prompts`를 레포의 user 범위에 포함할 대상으로 보는가, 아니면 "OMX 설치 안내"만 남기면 되는가? | 안내만(OMX가 자체 설치·업데이트 도구를 가진 것으로 보임 [가정]) |
| Q7 | `counterexample-hunter`·`algorithm-options`를 확장하는 안(신규 스킬 대신)에 동의하는가? | 동의 권장 |
