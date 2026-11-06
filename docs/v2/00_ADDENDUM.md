# 00_ADDENDUM.md — V2 지시서 보강 요구사항

> **원문:** `docs/v2/00_PROMPT.md` (바탕화면 `SKILL_KIT_V2_DEVELOPMENT_PROMPT.md`를 수정 없이 복사.
> SHA-256 `755e064ca9d86507ab3253187157bd27b90e95e7763bd9d3771758abde68d2d6`)
> **작성일:** 2026-11-05
> **승인:** 검토자 승인 2026-11-05 (대화에서 "승인")
> **우선순위:** 이 문서와 원문이 충돌하면 이 문서가 우선한다. 원문의 REQ 번호는 재사용하지 않는다.
> 설계 근거: `docs/superpowers/specs/2026-11-05-v2-addendum-design.md`

## 1. 목표 보강

원문 §2.2 목표에 다음을 더한다.

11. 사용자가 고른 오픈소스 스킬·MCP·플러그인 목록(`docs/v2/inputs/user-source-list.txt`)을
    우선 채택 대상으로 통합한다.
12. 웹 서비스 출시 전 법적·접근성 점검(`docs/v2/inputs/launch-checklist.txt`)을 공통 스킬로 제공한다.
13. 이 레포를 어느 PC에서 불러와도 사용자의 Codex·Claude Code **전역** 설정(정책 파일,
    설정, MCP, 플러그인, 스킬)을 재현할 수 있게 한다. 단 명시적 opt-in일 때만 전역에 쓴다.

## 2. 신규 요구사항

### SRC (보강)
- **REQ-SRC-006** 사용자 목록의 모든 항목을 원본 저장소 URL, 라이선스, 고정 커밋(또는 버전)으로
  확정한 표 `docs/v2/08_USER_SOURCES.md`를 만든다. 이름만으로 하나의 저장소로 확정할 수 없는
  항목은 추측하지 않고 `UNRESOLVED`로 두고 검토자에게 묻는다. 원본 목록은 1~29 다음에
  번호가 20부터 다시 시작해 39까지 이어지므로 실제 항목은 **49개**다(2026-11-05 정정, 처음에는
  39개로 잘못 셌다). 원문 순서대로 U-01~U-49 ID를 새로 매긴다.
- **REQ-SRC-007** 사용자 목록 항목이 레포 기존 스킬과 기능이 겹치면:
  - 새 경로(`--policy standard`, `--agent claude|both`)에는 사용자 목록 버전을 채택하고, 겹치는
    레포 스킬은 해당 경로의 설치 목록에서 빼거나 사용자 목록 버전에 없는 고유 부분만 합친다.
  - 기존 경로(서브커맨드 없는 호출 = `install --agent codex --policy restricted`)는 기존 11개
    스킬을 그대로 설치한다(REQ-COMPAT-002 유지).
  - 겹침 판정과 처리 결과를 `07_SOURCES_EVALUATION.md`에 쌍별로 기록한다.
- **REQ-SRC-008** 이 PC의 Codex 전역 스킬(`~/.codex/skills/` 아래 약 30개, omx 계열 포함)과
  Claude 전역 플러그인도 §14 평가 대상에 넣는다. 사용자 목록에 없는 항목은 우선 채택 대상이
  아니다(일반 §14 규칙 적용).
- 원문 R-07, §14.3(라이선스 확인, 원격 설치 스크립트 금지, 버전 고정)은 사용자 목록 항목에도
  그대로 적용한다. 사용자 목록에 있다는 이유로 이 규칙을 면제하지 않는다. 채택할 수 없으면
  이유를 적고 대안을 제시한다.
- **REQ-SRC-009 (2026-11-05 승인)** 검토자가 나중에 GitHub 저장소 주소를 주면 그 스킬·MCP·플러그인을
  레포에 반영하는 `kit source add|list|check|update|remove` 명령과 에이전트용 `add-skill-source` 스킬을 둔다.
  커밋 SHA 고정, 격리 내려받기(실행 금지), 라이선스 표(허용 라이선스만 vendored, 나머지 reference),
  보안·형식 검사, 겹침 판정(REQ-SRC-007과 같은 우선순위, restricted·미러 불변), plan → 승인 → 원자적 반영 →
  `sources.lock.json`·NOTICES 기록. 상세: `docs/superpowers/specs/2026-11-05-source-add-design.md`.

### SKILL
- **REQ-SKILL-001** 공통 스킬 `launch-compliance-check`를 만든다.
  - 입력 목록의 20개 항목(개인정보처리방침, 이용약관, 환불정책, 쿠키정책·동의 배너, 동의 항목,
    최소 수집, 외부 SDK 점검, 다크패턴, 숨은 요금, 가짜 후기, 근거 없는 주장, 대체 텍스트,
    색 대비, 키보드 접근성, 사업자 정보, 아동 정보, 수신거부 링크, 이미지·글꼴 이용권,
    개인정보 삭제 요청)을 점검 항목으로 하고, 항목별로 "확인 방법 / 증거 / 결과(PASS·FAIL·N/A·
    NEEDS_HUMAN)"를 보고하게 한다.
  - 법령·기준(예: 개인정보 보호법, 전자상거래법, 정보통신망법, WCAG 2.x 대비 기준) 인용은 공식
    출처로 확인한 것만 `VERIFIED-DOC`으로 쓰고 나머지는 `UNVERIFIED`로 표시한다. 스킬 본문에
    "법률 자문이 아니다"를 명시한다.
  - `web`, `fullstack` 프로필의 새 경로에 포함한다. 기존 `web` 프로필의 기존 경로 설치 내용은
    바꾸지 않는다(REQ-COMPAT-003).

### USER: 전역(사용자 범위) 설정
- **REQ-USER-001** 레포의 `user/codex/`, `user/claude/`에 이 PC의 전역 설정을 정리한 스냅샷을 둔다.
  - Codex: `AGENTS.md`, `config.toml`의 이식 가능한 부분(model, features, MCP, 플러그인·마켓플레이스
    선언), 스킬 목록과 출처.
  - Claude: `CLAUDE.md`, `settings.json`, 설치 플러그인·마켓플레이스 목록, 사용자 범위 MCP, 사용자 스킬.
  - 머신 고유 경로는 `${HOME}` 같은 템플릿 변수로 바꾼다. 외부 스킬 본문은 REQ-SRC 규칙에 따라
    채택된 것만 넣고, 나머지는 출처 참조로 둔다.
- **REQ-USER-002** 전역 적용은 `install --scope user`로만 한다.
  - 기본 범위는 `project`이고, `--scope user`는 `plan`으로 변경 내용(diff)을 먼저 보여 준 뒤 TTY
    확인 또는 `--yes`가 있어야 쓴다.
  - 쓰기 전에 `~/.kit-backups/<시각>/`에 백업한다. 키트 소유 구간(마커)과 소유 JSON/TOML 키만
    수정하고, 사용자가 고친 부분은 `CONFLICT`로 남긴다(REQ-SAFE-001/003과 같은 규칙).
  - `uninstall --scope user`, `restore --scope user`를 같은 매니페스트 방식으로 지원한다.
  - 원문 **REQ-SAFE-008**을 다음으로 바꾼다: "`--scope project`(기본) 실행은 전역 환경을 수정하지
    않는다. 전역 수정은 REQ-USER-002의 절차를 거친 `--scope user` 실행에서만 한다." V-18 테스트는
    project 범위에 그대로 적용한다.
  - 원문 R-06은 **개발 중의 에이전트 행동**에 대한 규칙으로 유지한다. 개발 중 테스트는 HOME을
    임시 디렉터리로 바꿔 실행하고 실제 `~/.codex`, `~/.claude`에 쓰지 않는다.
- **REQ-USER-003** `capture` 명령으로 현재 PC의 전역 설정을 `user/`로 다시 내보낸다. 기본은
  dry-run(변경 diff만 출력)이고 `--write`일 때만 레포 파일을 바꾼다. 정제 규칙은 REQ-USER-004.
- **REQ-USER-004** 다음은 레포에 절대 넣지 않는다.
  - 인증 파일: `~/.codex/auth.json`, `~/.claude/.credentials.json`, `.sandbox-secrets/` 등
  - 토큰·API 키 값(키 이름만 허용), 연결 앱·커넥터 ID, `projects.*` 신뢰 경로
  - 기록·상태: history, sessions, sqlite, cache, logs, file-history, paste-cache, backups
  - 테스트로 강제한다: `user/` 아래 모든 파일을 토큰 패턴(`sk-`, `ghp_`, `Bearer `, `*_TOKEN=`
    값 등)과 제외 목록으로 스캔해서 하나라도 나오면 실패.
- **REQ-USER-005** (Q6 결정) OMX(`Yeachan-Heo/oh-my-codex`, MIT)를 레포의 user 범위 구성 요소로
  포함한다. 대상은 이 PC의 `~/.codex/skills`에 있는 OMX 스킬 28개, `~/.codex/agents/*.toml`,
  `~/.codex/prompts/`다. 다른 PC에서도 `install --scope user` 한 번으로 설치되어 Codex에서 바로
  쓸 수 있어야 한다.
  - 라이선스 원문과 고정 커밋은 `sources.lock.json`과 `THIRD_PARTY_NOTICES.md`에 기록한다(원문 R-07, REQ-SRC-002/003).
  - 레포에 넣기 전에 내용을 검토한다. 머신 경로, 비밀값, 개인 정보가 있으면 REQ-USER-004에 따라 템플릿으로 바꾸거나 제외한다.
  - OMX가 자체 설치 도구(`omx-setup`, npm 빌드 등)에 의존하는 부분은 키트가 대신 실행하지 않는다. 키트는 필요한 명령을 출력하고 plan에 표시한다(원문 §14.3, §15).

## 2-1. 검토자 결정 기록 (2026-11-05, Phase 1 질문에 대한 답)

| # | 결정 | 반영 |
|---|---|---|
| Q1 | 승인 | **REQ-COMPAT-002**를 "기존 **11개** 스킬이 기존 위치(`.agents/skills/<name>/`)에 같은 내용으로 설치된다"로 고친다. 원문 §3.2, §7.4 표의 "기존 8개"도 11개로 읽는다 |
| Q2 | GitHub에서 이름 그대로 찾을 것 | `08_USER_SOURCES.md` 2차본으로 UNRESOLVED를 0개로 만들었다 |
| Q3 | 예외로 명시 | **REQ-SAFE-008 예외**: 기존 경로(서브커맨드 없는 호출)에서 `python` 계열 프로필이 하는 도구 설치(`uv tool install` → `pip install --user`, `kit/tools.py:59-66`)는 v1과 같은 동작으로 유지한다. 원문 R-06은 개발 에이전트가 직접 실행하는 전역 설치에 적용하고, 키트 기존 경로의 이 동작에는 적용하지 않는다. 새 경로에서는 같은 설치를 plan에 "user-scope install [network]"로 표시하고 D-14의 확인 절차를 거친다 |
| Q4 | 동의 | 원문 **D-03**: 관리 구간 마커는 `hackathon-kit`을 그대로 쓴다. 새 파일(`CLAUDE.md`, user 범위 파일)에도 같은 마커를 쓰고 `migrate` 명령은 만들지 않는다 |
| Q5 | Codex `/skills`에 보임 | Codex 0.166.0이 `~/.codex/skills`를 읽는다 → `VERIFIED-RUN`(검토자가 Codex 안에서 확인, 2026-11-05). user 범위 Codex 스킬 설치 경로는 **`~/.codex/skills`**(이 PC에서 확인됨)로 하고, 문서상 경로 `~/.agents/skills`는 대안으로 둔다 |
| Q6 | 레포에 포함하고 명령으로 불러와 실행되게 | REQ-USER-005 |
| Q7 | 동의 | 원문 REQ-CE-001은 신규 `counterexample-generator` 대신 기존 `counterexample-hunter`를 확장해 처리한다. REQ-ALGO-001은 신규 `algorithm-decision-reviewer` 대신 기존 `algorithm-options`를 확장해 처리한다. 확장은 새 경로(standard)용 overlay로 하고, restricted 경로의 11개 스킬 내용은 바꾸지 않는다(REQ-COMPAT-002) |

## 3. Phase 반영

| 원문 위치 | 보강 |
|---|---|
| P1-T1 | 추가 산출물 `docs/v2/baseline/global-inventory.md`: 이 PC 전역 설정의 파일 목록, 섹션·키 이름, 스킬·플러그인·MCP 목록. **읽기 전용, 비밀값은 이름만.** |
| P1-T4 | 호환성 매트릭스에 행 추가: 사용자 범위 정책 파일, 사용자 범위 스킬 경로, 사용자 범위 MCP·플러그인 설정, 사용자/프로젝트 우선순위. |
| P1-T5 | `08_USER_SOURCES.md` 1차본(항목별 후보 저장소, `UNRESOLVED` 목록)과 겹침 1차 의견을 03_PLAN에 포함. |
| P2-T1 | ADR 추가: D-18 사용자 범위 설치 설계(REQ-USER-002), D-19 capture 정제 규칙(REQ-USER-004), D-20 사용자 목록 우선 규칙과 경로 분리(REQ-SRC-007), D-21 외부 소스 추가 파이프라인(REQ-SRC-009). |
| P4-T3 | 평가 대상에 사용자 목록 전체와 REQ-SRC-008 항목을 포함. |
| P4-T7 (신규) | 사용자 범위 설치·제거·복구와 `capture` 구현, OMX 포함(REQ-USER-005). 등급 C. |
| P4-T8 (신규) | `kit source` 명령과 `add-skill-source` 스킬(REQ-SRC-009). P4-T4 뒤. 등급 B. |
| P5 | `launch-compliance-check` 스킬 추가(P5-T6과 같은 단계에서). |
| P6-T2 | 검증 매트릭스 추가: V-19 `--scope user` dry-run 무변경(HOME 임시), V-20 `user/` 비밀값 스캔, V-21 capture → install 왕복 시 정제 후 내용 일치, V-22 restricted 경로에 사용자 목록 스킬이 들어가지 않음, V-23 오프라인 fixture로 source add→check→update→remove 왕복, V-24 라이선스 없는 저장소는 vendored로 들어가지 않음. |

## 4. 입력 파일

| 파일 | 원본 |
|---|---|
| `docs/v2/inputs/user-source-list.txt` | 바탕화면 `skill들 모음.txt` |
| `docs/v2/inputs/launch-checklist.txt` | 바탕화면 `개발 시 주의사항.txt` |
