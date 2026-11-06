# 01 기존 저장소 분석 (P1-T2, P1-T5)

- 기준: `main` @ `98add1edee13401cd1e79f9ad69ffee7b272d971`, 2026-11-05
- 근거 표기: `[확인됨: 근거]` / `[가정]` / `[미확인]`
- 관련 문서: 테스트 기준선 `baseline/test-baseline.md`, 설치 스냅샷 `baseline/install-snapshots/`, 호환성 `02_COMPATIBILITY_MATRIX.md`, 전역 설정 `baseline/global-inventory.md`, 사용자 목록 `08_USER_SOURCES.md`

## 0. 지시서 §3 사전 관찰과 실제의 차이

| 지시서 §3 | 실제 | 근거 |
|---|---|---|
| 스킬 8개 | **11개**(`algorithm-options`, `counterexample-hunter`, `design-review` 추가) | [확인됨: `profiles/core.json:5-17`, 커밋 `1d2fc5f`] |
| `benchmark`, `implementation-review`에 `agents/openai.yaml` 있음 | **없음**. 커밋 `1d2fc5f`에서 삭제됨(`allow_implicit_invocation: false`면 모델의 스킬 목록에서 빠져 키워드 호출이 안 되므로). 테스트가 "없음"을 강제 | [확인됨: `git show 1d2fc5f`, `tests/test_skills.py:122,148`, `docs/superpowers/specs/2026-10-31-stress-and-options-design.md:14`] |
| core `required_skills` 4개 | 같음 | [확인됨: `profiles/core.json:18-23`] |
| 테스트 24개 파일 안팎 | 24개 파일, 339개 테스트(1개 SKIPPED) | [확인됨: `baseline/raw/pytest.txt`] |
| REQ-COMPAT-002 "기존 8개 스킬" | 11개로 읽어야 한다 → **요구사항 문구 정정 필요(검토자 결정 사항 Q1)** | 위 |
| REQ-CE-001 `counterexample-generator`, REQ-ALGO-001 Algorithm Decision Reviewer를 **신규**로 가정 | 기존 `counterexample-hunter`(무작위 소입력 + 브루트포스 오라클 대조)와 `algorithm-options`(구현 전 후보 2~3개 비교, 사용자 선택 대기)가 이미 상당 부분을 덮는다 | [확인됨: 각 `SKILL.md` frontmatter] → 원문 §7.4 "기존 스킬로 덮을 수 있으면 새 스킬을 만들지 않는다"에 따라 **확장으로 처리하는 것이 1차 의견** |
| 상태 파일 | `.kit/state.json`(`{"version":1,"profile":…,"files":{rel: sha256}}`). 원문 D-06의 `install-manifest.json`은 아직 없음 | [확인됨: `kit/fsops.py:11,53-57`] |

## 1. 그대로 유지할 기능

| 기능 | 근거 | 보장 테스트 |
|---|---|---|
| 관리 구간 병합(생성/추가/갱신/무변경/충돌, CRLF 정규화, 마커 인수화) | `kit/agentsmd.py:41-64` | `test_agentsmd.py` 16개 |
| 해시 기반 소유 판정(state 기록 해시와 비교, 사용자 수정 시 CONFLICT, 기록 없으면 같은 내용만 채택) | `kit/plan.py:73-96` | `test_plan.py`, `test_idempotency.py::test_lost_state_is_adopted` |
| 대상 밖 쓰기 거부(`safe_path`: `..`, 절대 경로, 심볼릭 링크 탈출) | `kit/fsops.py:18-24` | `test_fsops.py` 3개(심볼릭 링크 1개는 이 PC에서 SKIPPED), `test_security.py::test_no_writes_outside_target` |
| 원자적 쓰기, 실패해도 state 저장, `.kit-tmp` 정리 | `kit/register.py:15-40` | `test_register.py` |
| 백업 `.kit/backups/<stamp>/` | `kit/fsops.py:60-65` | `test_register.py::test_apply_backs_up_before_update`, 스냅샷 `core__existing-agents-md` |
| 종료 코드 0/1/2/64/65, 예상치 못한 예외는 BLOCKED | `kit/model.py:7-11`, `kit/app.py:105-112` | `test_model.py`, `test_blocked_on_error.py`, 스냅샷 전체 |
| MCP 허용 목록 + 버전 고정 + stdio(`npx`/`uvx`만) + 감사(원격 URL, 금지 키, 비밀 env 이름) | `kit/mcpconfig.py:38-51`, `kit/audit.py` | `test_mcpconfig.py`, `test_audit.py` 16개 |
| 로그 마스킹 | `kit/logs.py:10-26` | `test_security.py` |
| 셸 전용 모드 | `bootstrap.sh:57-166`, `bootstrap.ps1` | `test_entrypoints.py::test_fallback_*` |
| 11개 스킬 내용 | `.agents/skills/` | `test_skills.py` 30개 |
| `full` = 보고 전용(도구 설치 안 함), `report_only`는 상속되지 않음 | `kit/profiles.py:98-103`, `profiles/full.json` | `test_profiles.py::test_full_profile_is_report_only`, `::test_report_only_is_not_inherited` |

## 2. 수정이 필요한 기능

| 기능 | 이유 | 근거 |
|---|---|---|
| `profiles.py`의 `extends`(문자열만), 리스트 4종만 병합 | REQ-PROF-002/003(다중 상속, 팩, 에이전트별 항목) | `kit/profiles.py:16,57-59` |
| `plan.iter_skill_files`, `verify._verify_skill`이 `.agents/skills`를 하드코딩 | Adapter의 `skill_root()`로 빼야 Claude(`.claude/skills`)를 지원 | `kit/plan.py:25,27`, `kit/verify.py:76` |
| `plan_changes`가 항상 `AGENTS.md`를 계획 | Claude 단독 설치에서 정책 대상이 다름 | `kit/plan.py:102` |
| `audit_target`이 `.codex/config.toml`만 읽음 | Claude `.mcp.json` 감사 필요(원문 P3-T4) | `kit/audit.py:107-108` |
| `skills.validate_skill`이 description에 `"Do NOT use"`를 요구하고 400자 상한 | **키트 내부 작성 규칙**이다. 사용자 목록의 외부 스킬(REQ-SRC-007로 새 경로에 들어갈 것)은 대부분 이 규칙을 지키지 않는다 → 외부 스킬용 검증(공식 제약만: 이름 일치, 필수 필드, 길이 한도)을 따로 둬야 한다 | `kit/skills.py:7,48-49` |
| `tools.py`의 도구 설치가 `uv tool install` → `pip install --user` | **사용자 범위(전역) 설치다.** 원문 R-06("전역 npm/pip 설치는 승인 후")과 REQ-SAFE-008("전역 환경 수정 안 함")이 기존 동작과 문자 그대로 충돌한다. 기존 경로 동작은 유지하되, 새 경로에서는 plan에 "user-scope install"로 표시하고 확인을 받는 것이 1차 의견 | `kit/tools.py:59-66` |
| 셸 전용 모드가 `.agents/skills/*`를 **프로필과 무관하게 전부** 복사 | v2에서 미러(`.agents/skills`)에 새 스킬을 넣으면 기존(restricted) 경로 셸 모드 설치 결과가 바뀐다 → REQ-COMPAT-002/006 위반 위험(R-3) | `bootstrap.sh:131`, `bootstrap.ps1:152-156` |

## 3. 확장 가능한 모듈

| 모듈 | 확장 방식 |
|---|---|
| `agentsmd.merge` (마커가 인수) | 그대로 `writers/markdown_block`로 재사용: `CLAUDE.md`, 사용자 범위 `~/.codex/AGENTS.md`·`~/.claude/CLAUDE.md`(REQ-USER-002) |
| `mcpconfig` TOML 구간 | Codex 프로젝트·사용자 범위 공용. Claude는 JSON 키 소유 writer 신규(원문 D-05) |
| `audit.audit_config(data, allowlist)` | 입력이 이미 dict라 JSON(`.mcp.json`)의 `mcpServers`를 같은 형태로 바꿔 넣으면 재사용 가능 [가정: 키 이름 차이 `mcp_servers`↔`mcpServers`, `url`/`type` 처리만 다름] |
| `plan.FileChange` / `register.apply_changes` | 원문 Action 모델의 출발점. `owner`가 이미 있다. `agent`, `network`, `risk` 필드 추가 |
| `fsops.State` | `version: 1` 필드가 있어 v2 스키마(설치 매니페스트)로 올릴 수 있다. 기존 파일을 읽는 마이그레이션 필요 |
| `report.render` | 에이전트별 줄 추가(원문 P2-T5 예시) |

## 4. Codex에 종속된 부분

| 종류 | 위치 |
|---|---|
| 경로 | `.agents/skills`(`kit/plan.py:25,27`, `kit/verify.py:76`, `bootstrap.sh:131`, `bootstrap.ps1:152-153`), `.codex/config.toml`(`kit/mcpconfig.py:14`) |
| 정책 파일 | `AGENTS.md`(`kit/plan.py:56-58`, `kit/verify.py:51-67`) |
| 외부 명령 | `codex mcp list --json`(`kit/mcpcheck.py:111-123`), preflight 도구 목록의 `codex`(`kit/preflight.py:13`) |
| 보고서 문구 | `"Codex load:   UNVERIFIED (open Codex and run /skills)"`(`kit/report.py:94`, `bootstrap.sh:151`), 다음 행동 `"Open Codex in … run /skills"`, `"Trust … in Codex … /mcp"`(`kit/report.py:45-49`), `TRUST_NOTE`(`kit/mcpconfig.py:15`) |
| 정책 내용 | 루트 `AGENTS.md`의 Restrictions(시험용: Claude Code 사용 금지 등) |
| 스킬 내용 | `implementation-review`의 "written-answer phase of the exam" 문구, 여러 스킬의 `TASK_BRIEF.md` 의존(해커톤 워크플로) [확인됨: grep 결과] |
| 테스트 | `test_mcpcheck.py`(codex 목록), `test_report.py::test_next_actions_ready_points_to_skills_check`, `test_skills.py::test_agents_md_policy` 등 문자열 단언 |

## 5. Claude Code 지원을 위해 추가할 부분

(모두 `02_COMPATIBILITY_MATRIX.md`에서 `VERIFIED-DOC`인 항목만)
1. `.claude/skills/<name>/` 배치(공통 원본에서 렌더링).
2. `CLAUDE.md` 관리 구간. **Claude는 `CLAUDE.md`가 없으면 `AGENTS.md`를 읽고, 있으면 읽지 않는다** → `both` 설치 시 `CLAUDE.md`에 `@AGENTS.md` import 한 줄을 넣거나 같은 원문을 렌더링.
3. `.mcp.json`의 `mcpServers` 키 소유 병합과 JSON 감사.
4. (선택, opt-in) `.claude/settings.json`의 `enabledPlugins`/`extraKnownMarketplaces` 선언.
5. (선택, opt-in) L2 승인 훅. Codex에도 UserPromptSubmit/PreToolUse 훅이 있다는 점이 문서로 확인되어 원문 D-11의 "Claude 전용" 전제를 다시 검토해야 한다.
6. 수동 확인 절차: `/skills`, `/memory`, `/mcp`, `/status`, `claude mcp list`.
7. 사용자 범위(보강 REQ-USER): `~/.claude/CLAUDE.md` 구간, `~/.claude/skills/`, `~/.claude/settings.json` 소유 키. 사용자 MCP는 `~/.claude.json`이 계정·신뢰 상태까지 담으므로 직접 쓰지 않고 `claude mcp add --scope user …` 명령을 출력하는 방식을 1차 의견으로 한다.

## 6. 테스트가 보장하는 동작과 보장하지 않는 동작

**보장함** [확인됨: `baseline/raw/pytest.txt`, 테스트 이름]: 병합 규칙 전부, 해시 소유 판정, 경로 탈출 거부, 원자적 쓰기, 멱등성(2회), dry-run 무변경, verify-only가 로그만 씀, 종료 코드, 프로필 상속·순환 거부, MCP 허용 목록·감사(TOML, 3.11+/미만), 마스킹, 네트워크 모듈 import 금지(`test_kit_core_imports_no_network_modules`), push·`| sh` 금지 문자열(`test_kit_code_has_no_push_or_pipe_to_shell`), 셸 전용 모드, 스킬 정적 규칙과 설명 예산.

**보장하지 않음**
| 동작 | 이유 |
|---|---|
| 실제 Codex가 스킬·MCP를 로드함 | 비대화형 확인 불가(설계상 `UNVERIFIED`). 이전 수동 기록은 `docs/TEST_REPORT.md:87-102` |
| 실제 `npx` 핸드셰이크, 실제 도구 설치 | `conftest.py`의 `fake_mcp`, `no_real_commands` 픽스처가 막음 |
| 전체 설치 결과의 바이트 단위 골든 비교 | 개별 동작만 테스트. 스냅샷(`baseline/install-snapshots/`)을 P3-T1에서 골든으로 전환 |
| HOME 무변경을 **모든 경로에서** | `isolated_home`은 격리만 하고 무변경을 단언하지 않음. 스냅샷 스크립트에서는 24개 경우 모두 HOME 무변경 확인 |
| Python 3.9 실행 | 로컬에 3.9 없음 → NOT RUN |
| Linux 실행 | 환경 없음 → NOT RUN |
| 심볼릭 링크 탈출 | 이 PC에서 SKIPPED |

## 7. 호환성 위험 등록부

| ID | 내용 | 영향 | 가능성 | 대응 |
|---|---|---|---|---|
| R-1 | Adapter 추출 중 기존 보고서 문구·파일 트리가 미세하게 바뀜 | 높음(REQ-COMPAT-001) | 중 | P3-T1 골든 테스트를 리팩터링 전에 만든다. 머신 의존 줄(`Environment:`, `Tools:`)은 정규화 |
| R-2 | 공통 원본(`shared/skills/`)으로 옮긴 뒤 `.agents/skills` 미러가 원본과 어긋남 | 높음 | 중 | 원문 D-01의 동기화 검사 테스트. 또는 현재 위치를 원본으로 유지하는 대안(D-01 1차 의견 참고) |
| R-3 | 셸 전용 모드가 미러의 **모든** 스킬을 복사 → 새 경로용 스킬이 restricted 셸 설치에 섞임 | 높음 | **높음**(구조상 확정) | 새 경로용 스킬을 `.agents/skills` 미러에 넣지 않는다. 미러는 기존 11개만 |
| R-4 | `both` 설치 시 Claude가 `.agents/skills`도 읽어 같은 스킬이 두 번 보일 수 있음 | 중(컨텍스트 낭비) | 미확인 | 문서상 근거 없음(UNVERIFIED). 수동 확인 체크리스트에 넣고, 확인 전에는 `both`에서 Claude 쪽 스킬만 `.claude/skills`에 둔다 |
| R-5 | `CLAUDE.md`를 만들면 Claude가 기존 `AGENTS.md`를 더는 읽지 않음 | 중 | 높음 | `@AGENTS.md` import 또는 같은 원문 렌더링(D-04) |
| R-6 | 기존 `tools.py`의 사용자 범위 설치가 원문 R-06·REQ-SAFE-008과 문자 그대로 충돌 | 중(정책 일관성) | 확정 | 기존 경로는 유지(REQ-COMPAT-001), 요구사항 문구를 "기존 경로의 도구 설치는 예외"로 정리할지 검토자 결정(Q3) |
| R-7 | 사용자 목록 외부 스킬이 키트 작성 규칙(`Do NOT use`, 400자) 검증에서 FAIL → 새 경로 설치가 BLOCKED | 중 | 높음 | 외부 스킬 전용 검증 규칙 분리(§2) |
| R-8 | user 범위 설치가 실제 `~/.codex`, `~/.claude`를 망가뜨림 | 높음 | 낮음~중 | 원문 수준의 백업·소유 구간·plan 확인 + 테스트는 HOME 격리(V-19) + 첫 실제 적용은 검토자가 직접 |
| R-9 | Codex의 사용자 스킬 경로가 문서(`~/.agents/skills`)와 이 PC의 실제(`~/.codex/skills`)가 다름 | 중 | 확정 | **해소(2026-11-05)**: 검토자가 `/skills`에서 확인 → `~/.codex/skills` 사용(00_ADDENDUM §2-1 Q5) |
| R-10 | `~/.codex/AGENTS.md`(26.7 KB)에 키트 구간을 추가하면 `project_doc_max_bytes` 32 KiB에 걸릴 수 있음 | 중(지침 잘림) | 중 | user 범위 plan에서 결과 크기를 계산해 경고 [가정: 사용자 AGENTS.md도 같은 한도에 포함되는지는 문서상 불명확] |
| R-11 | 외부 리소스의 라이선스(AGPL 등)와 원격 MCP | 중 | 확정(U-14 등) | §14 평가, 포함 금지·opt-in |
