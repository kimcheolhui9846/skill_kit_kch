# 06 테스트 계획 (P2-T6)

- 기준: `00_PROMPT.md` §4(요구사항), §12 P6-T2(V-01~V-18), `00_ADDENDUM.md`(REQ-SRC-006~009, REQ-SKILL-001, REQ-USER-001~005, V-19~V-24), ADR-001~021, `04_DESIGN.md`, `05_CLI_SPEC.md`
- 모든 테스트는 pytest로 돌리며 기본적으로 네트워크 없이 실행한다.
  - 네트워크·GitHub 접근은 fixture(tarball, JSON 응답)로 대신한다.
  - HOME은 `tmp_path`로 격리한다. 실제 `~/.codex`, `~/.claude`에 닿는 테스트는 없다(R-8).
- 실행 근거는 `pytest --junitxml`이다. 실행 기록이 없는 항목은 보고서에서 `NOT RUN`으로 표시한다(R-01, ADR-012).
- 이 PC에서 실행할 수 없는 환경은 수동 절차(§4)로 두고, 책임자는 검토자다: Linux, macOS, pwsh 7, Python 3.9, 에이전트 내부 확인.

## 1. 테스트 ID 규칙

- 형식: `TC-<영역>-<번호>`
- 영역: `GLD`(골든), `ADP`(Adapter), `WRT`(writer), `MAN`(매니페스트), `PRF`(프로필), `SRC`(소스), `USR`(user 범위·capture), `POL`(정책), `HTL`(HITL·추적·반례·세션), `SKL`(스킬 내용), `SEC`(보안), `CLI`, `XPL`(플랫폼)
- 파일 위치: `tests/<영역 폴더>/test_*.py`. 기존 `tests/test_*.py` 338개는 그대로 두고 매번 전체를 돌린다.
- V-xx는 원문·보강의 검증 매트릭스 ID이고, 하나의 V에 여러 TC가 연결될 수 있다.

## 2. 요구사항 → 테스트 연결

`자동` = pytest, `수동` = §4 절차, `문서` = 산출물 존재와 내용 검토.

### COMPAT

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| COMPAT-001 | 자동 | TC-GLD-01: 기준선 24개 스냅샷과 정규화 비교(트리, 관리 구간, 보고서, 종료 코드). TC-CLI-01: 서브커맨드 없는 호출이 `kit/cli.py` 경로로 가는지 | V-01 | P3-T1 |
| COMPAT-002 | 자동 | TC-GLD-02: `.agents/skills` 이름 집합 = 기준선 11개, 파일 해시가 같음. 기존 `test_skills.py` | V-02, V-22 | P3-T1 |
| COMPAT-003 | 자동 | TC-PRF-01: v1 프로필 5개를 해석한 결과 = 기준선. `full`은 report_only이고 상속되지 않음(기존 테스트 유지) | V-03 | P3-T5 |
| COMPAT-004 | 자동 | TC-MAN-01: v1 작업 공간(`.kit/state.json`)에 새 경로 install → 구간 1개, 사용자 내용 보존, 인수 기록. TC-MAN-02: 해시가 다른 파일은 CONFLICT | V-05 | P3-T2 |
| COMPAT-005 | 자동 | TC-CLI-02: 05_CLI_SPEC §6 표의 명령별 대표 시나리오와 종료 코드(기존 `test_model.py` 확장) | — | P3-T6 |
| COMPAT-006 | 자동 | 기존 `test_entrypoints.py::test_fallback_*` 유지. TC-CLI-03: 셸 모드에서 서브커맨드 입력 → 64 + 안내 문구(bash: Git Bash로 실행, ps1: PowerShell 5.1로 실행) | — | P3-T6 |
| COMPAT-007 | 자동 + 수동 | TC-SEC-01: `kit/` import가 표준 라이브러리만 쓰는지(AST 검사). ruff `target-version = "py39"`. 실제 3.9 실행은 수동 M-03 | — | P3 전반 |

### ARCH

| REQ | 검증 | TC / 절차 | Phase |
|---|---|---|---|
| ARCH-001 | 자동 | TC-SKL-01: 카탈로그의 스킬마다 원본 위치가 하나이고 에이전트별 사본이 레포에 없음. 렌더 결과는 원본에서 생성 | P4-T1 |
| ARCH-002 | 자동 | TC-ADP-01: 카탈로그 `agents` 필드에 따라 codex 전용·claude 전용 항목이 다른 에이전트 plan에 나타나지 않음 | P4-T5 |
| ARCH-003 | 자동 | TC-ADP-02: 테스트 전용 `DummyAdapter`를 registry에만 등록하고 공통 코드는 바꾸지 않은 채 install/plan이 동작 | P3-T3 |
| ARCH-004 | 자동 | TC-ADP-03: `plan()` 호출 전후 대상 트리 해시가 같음. 쓰기 함수를 monkeypatch로 금지 | P3-T3 |

### AGENT

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| AGENT-001 | 자동 | TC-CLI-04: `--agent codex/claude/both`별 plan Action 집합. 잘못된 값이면 64 | — | P3-T6 |
| AGENT-002 | 자동 + 문서 | TC-ADP-04: Claude 파일 경로가 04_DESIGN 표 2.3과 02 매트릭스(CC-*)와 같은지 | V-06 | P3-T4 |
| AGENT-003 | 자동 | TC-ADP-05: codex → claude → both → uninstall claude 순서 뒤 codex 소유 파일 해시가 같음 | V-07 | P3-T4 |
| AGENT-004 | 문서 | `02_COMPATIBILITY_MATRIX.md` 갱신. 행마다 근거 ID와 확인 수준이 있는지 검사하는 TC-POL-05 | — | P6 |
| AGENT-005 | 자동 + 수동 | TC-CLI-05: 보고서의 Load 칸이 항상 `UNVERIFIED`이고 안내 문구가 있음. 실제 로드는 M-01, M-02 | — | P3-T6 |

### INST

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| INST-001 | 자동 | TC-ADP-06: 프로필×에이전트 조합 install → verify PASS(core,hitl × codex/claude/both) | — | P3 |
| INST-002 | 자동 | TC-CLI-06: plan 출력에 스킬·MCP·플러그인·도구·네트워크·Manual steps가 모두 표시됨 | V-08 | P3-T6 |
| INST-003 | 자동 | TC-ADP-07: 설치 뒤 파일을 하나 지우거나 고치면 verify FAIL(1) | — | P3 |
| INST-004 | 자동 | TC-CLI-07: doctor 실행 전후 트리와 HOME이 그대로이고, 프로필 추천이 출력됨 | — | P3-T6 |
| INST-005 | 자동 | TC-MAN-03: 키트 원본을 바꾼 뒤 update → 소유 파일만 갱신, 사용자가 고친 파일은 CONFLICT | — | P3-T2 |
| INST-006 | 자동 | TC-MAN-04: uninstall이 소유하고 해시가 같은 것만 지움. 사용자 파일·사용자 JSON 키는 남음 | — | P3-T2 |
| INST-007 | 자동 | TC-SEC-02: `socket.socket`·`urllib.request.urlopen`·`subprocess`(npx/uvx/uv/pip) 차단 fixture 아래에서 `--offline`이 성공 | V-09 | P3 |
| INST-008 | 자동 | TC-MAN-05: 충돌 탐지 → `restore --backup <stamp>` → 설치 전 트리와 같음 | V-11 | P3-T2 |
| INST-009 | 자동 | TC-CLI-08: 로그 파일 생성, `--report-json` 스키마 검증, `--json` stdout이 JSON 하나 | — | P3-T6 |
| INST-010 | 자동 + 수동 | TC-XPL-01: 공백·한글 경로, CRLF 원본, `open()`에 `encoding` 명시 여부(AST). Windows는 이 PC에서 실행. Linux는 M-04 | V-16 | P3·P6 |

### SAFE

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| SAFE-001 | 자동 | TC-WRT-01: 사용자 내용이 있는 AGENTS.md/CLAUDE.md/config.toml/.mcp.json/settings.json fixture 보존 | V-05 | P3-T2 |
| SAFE-002 | 자동 | TC-MAN-06: 갱신·삭제 전에 백업이 존재(project, user 모두) | — | P3-T2 |
| SAFE-003 | 자동 | TC-WRT-02: JSON 포인터 소유(키 순서·들여쓰기 보존, 배열 원소 소유, 비소유 키 충돌 → CONFLICT) | — | P3-T2 |
| SAFE-004 | 자동 | TC-ADP-08: 새 경로 install 3회 연속 → 트리 해시 같음. 기존 경로는 TC-GLD rerun-x3 | V-04 | P3 |
| SAFE-005 | 자동 | TC-MAN-07: 쓰기 중 예외 주입 → 전체 롤백, 보고서에 PARTIAL/BLOCKED와 복구 명령. `both`는 두 에이전트 모두 롤백(05 §7) | V-11 | P3-T2 |
| SAFE-006 | 자동 | TC-CLI-09: 네트워크 Action이 plan에 `[network]`로 표시됨. 비대화형에서 `--yes`가 없으면 SKIPPED(ADR-014). INST-007의 TC-SEC-02 | V-09 | P3 |
| SAFE-007 | 자동 | TC-SEC-03: 가짜 토큰을 심은 env·설정으로 실행했을 때 로그·보고서·JSON 보고서에 값이 나오지 않음 | V-17 | P3 |
| SAFE-008 | 자동 | TC-SEC-04: **project 범위** 명령 실행 전후 임시 HOME 트리가 그대로. 기존 경로 도구 설치는 Q3 예외로 제외하고 문서화한다. user 범위는 USER-002 | V-18 | P3 |
| SAFE-009 | 자동 | TC-SRC-01: 허용 목록 밖 MCP 거부. 카탈로그의 고위험 플러그인은 `enabled_by_default:false`이고 `--plugin` 없이는 선언하지 않음 | V-10 | P4-T5 |
| SAFE-011 (P4-T9) | 자동 | TC-SEC-06: `credentials` 검증(필드·이름·URL·중복), 키가 필요한 항목은 기본으로 꺼짐·기본 팩 밖. 렌더러는 참조만 씀(`env_vars`, `${NAME}`, `-e 'NAME=${NAME}'`). 감사는 선언한 참조만 받고 값·다른 이름·미선언·다른 서버 선언은 FAIL. 가짜 키를 환경에 넣고 install·verify 했을 때 설정 파일·출력·로그에 값이 없음. 안내 절(set/not set, 필수 키 Next action, JSON `api_keys`), 마스킹 자리표시자 예외. `tests/catalog/test_p4t9_credentials.py` | V-17 | P4-T9 |
| SAFE-012 (2026-11-06 결정) | 자동 | TC-SEC-07: 큰 저장소의 폴더 단위 받기(고른 폴더와 위쪽 라이선스만, 서브모듈·경로 탈출·크기 불일치·합계 초과는 1, `--path` 없으면 1), frontmatter 라이선스 차이 Note. `--manual` 안내(출력·JSON, 아무것도 쓰거나 실행하지 않음, 잘못된 이름 64, 카탈로그 검증). 팩만 고른 standard 설치의 경고. `.claude/skills/add-skill-source`와 `shared/skills/add-skill-source`가 같음. 마스킹이 `${NAME}` 참조는 남기고 값은 가림. user 범위에서 context7은 참조만(`env_vars`, `-e 'NAME=${NAME}'`). `tests/cli/test_p4t9_followups.py`, `tests/sources/test_source_add.py`, `tests/userscope/test_user_install.py` | V-17 | P4-T9 |
| USER-008 (Q4, 2026-11-06) | 자동 | TC-USR-11: capture `codex.copy`가 적은 파일만 바이트 그대로 `user/codex/own/`에 복사, 목록에서 빠지면 REMOVE, 없거나 링크·UTF-8 아님은 Note, 비밀값이면 아무것도 안 씀. user 설치가 `~/.codex`에 쓰고 `verify`의 `own`이 PASS, 같은 내용은 소유하지 않음, 키트·OMX 스킬과 이름이 겹치면 64. 시험용 키트 사본은 실제 `user/` 스냅숏 대신 허용 목록만 씀. `tests/userscope/test_own_files.py` | — | P4-T9 |
| SAFE-010 | 자동 | TC-ADP-09: 모든 명령의 `--dry-run`(install/update/uninstall/restore/source add/capture 기본값) 전후 트리와 HOME 해시가 같음 | V-08 | P3·P4 |

### PROF

| REQ | 검증 | TC / 절차 | Phase |
|---|---|---|---|
| PROF-001 | 자동 | TC-PRF-02: `fullstack`, `ai-research`, `hackathon`이 로드되고 hitl 팩을 포함. 해석·설치 스킬 스냅샷(정책 2종), 기존 경로는 v1 5개만 봄. `tests/profiles/test_p4t6_profiles_policy.py` | P4-T6 |
| PROF-002 | 자동 | TC-PRF-03: 다중 상속 순서(왼쪽부터 깊이 우선, 처음 위치 유지), `core,hitl` 조합, 순환 참조와 없는 참조 → 64, 스칼라 충돌 → 64 | P3-T5 |
| PROF-003 | 자동 | TC-PRF-04: shared/codex/claude 항목 분리. `agents`에 없는 에이전트는 건너뛰고 보고 | P3-T5 |
| PROF-004 | 자동 | TC-PRF-01(v1 정규화) | P3-T5 |
| PROF-005 | 자동 | TC-CLI-10: `profiles show core,hitl --agent claude` 출력이 해석 결과와 같음 | P3-T6 |

### SRC

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| SRC-001 | 문서 | `07_SOURCES_EVALUATION.md`: 9개 기준 표, 묶음별 비교 | — | P4-T3 |
| SRC-002 | 자동 | TC-SRC-02: `sources.lock.json` 스키마 검증, `source check` 해시 일치·불일치 | V-23 | P4-T4 |
| SRC-003 | 자동 | TC-SRC-03: vendored 항목마다 LICENSE 파일이 있고 `THIRD_PARTY_NOTICES.md`에 항목이 있으며 lock과 1:1 | V-24 | P4-T4 |
| SRC-004 | 자동 + 절차 | TC-SRC-04: `source add`가 `--yes` 없이 plan만 출력하고 쓰지 않음. P4-T3 중간 승인 기록 | — | P4 |
| SRC-005 | 문서 + 자동 | 07의 겹침 표. TC-SRC-05: 카탈로그 한 팩 안에 `replaces` 관계인 두 스킬이 동시에 설치되지 않음 | — | P4-T3 |
| SRC-006 | 문서 | `08_USER_SOURCES.md` 49개 + OMX, UNRESOLVED 0 | — | P1(완료) |
| SRC-007 | 자동 | TC-SRC-06: standard 경로에는 사용자 목록 버전, restricted 경로에는 기존 11개만 | V-22 | P4 |
| SRC-008 | 문서 | 07에 Codex 전역 스킬과 Claude 전역 플러그인 평가 행 | — | P4-T3 |
| SRC-009 (P4-T8 반영: `tests/sources/test_source_add.py`, `tests/test_security.py`의 감지기·네트워크 모듈 검사) | 자동 | TC-SRC-07: URL 해석 3형식과 오류(64). TC-SRC-08: tar 경로 탈출·링크·크기 차단. TC-SRC-09: 라이선스 표 4종. TC-SRC-10: 스캐너(비밀값, `curl\|bash`, 보이지 않는 유니코드). TC-SRC-11: 겹침(이름 충돌, 유사도). TC-SRC-12: apply 중간 실패 → 롤백. TC-SRC-13: add→check→update→remove 왕복. TC-SRC-14: 같은 주소 재추가 → 변경 없음 | V-23, V-24 | P4-T8 |

### POL

| REQ | 검증 | TC / 절차 | Phase |
|---|---|---|---|
| POL-001 | 자동 | TC-POL-01: 10개 원칙이 AGENTS.md와 CLAUDE.md 렌더 결과에 모두 들어가고 원문 모듈이 하나임(ADR-004). `claude` 단독 설치에서도 들어감. `tests/profiles/test_p4t6_profiles_policy.py` | P4-T6 |
| POL-002 | 자동 | TC-POL-02: restricted 렌더 결과 = 기존 AGENTS.md 구간 바이트(골든). `tests/profiles/test_p4t6_profiles_policy.py` | P4-T6 |
| POL-003 | 자동 | TC-POL-03: standard 정책 문구에 "승인 전제" 조건(GitHub·외부 도구·MCP)이 있음. `tests/profiles/test_p4t6_profiles_policy.py` | P4-T6 |
| POL-004 | 자동 | TC-POL-04: 경량 경로 조항(`light-path.md`)이 렌더 결과에 있음. `tests/profiles/test_p4t6_profiles_policy.py` | P4-T6 |
| POL-001 (P5-T1) | 자동 | TC-POL-05: 스킬 안내 절(`skills.md`)이 두 에이전트에 한 번씩, restricted에는 없음. 적힌 이름이 모두 카탈로그 스킬이고, 모든 프로필의 standard 설치가 그 스킬을 모두 설치함(프로필 8개 × 에이전트 2개). standard 정책 4 KiB 미만. `tests/profiles/test_p5t1_skill_guide.py` | P5-T1 |

### HITL · TEST · TRACE · CE · ALGO · DATA · SESS

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| HITL-001 | 자동 | TC-HTL-01: task add로 Subtask와 depends_on 기록 | — | P5-T1 |
| HITL-002 | 자동 | TC-HTL-02: Subtask 완료가 승인을 요구하지 않음 | — | P5-T1 |
| HITL-003 | 자동 | TC-HTL-03: 선행 Task가 미승인일 때 `task start` → 2 | V-14 | P5-T1 |
| HITL-004 | 자동 + 문서 | TC-HTL-04: 정책 렌더에 중간 승인 조건(A.3) 목록이 있음 | — | P5 |
| HITL-005 | 자동 | TC-HTL-05: 보고서 템플릿이 §5.6 섹션을 모두 포함 | — | P5-T2 |
| HITL-006 | 자동 + 수동 | TC-HTL-06: approve의 `by` 3종 기록. 비대화형 human-cli 거부. 훅이 승인 파일 쓰기를 막을 때 exit 2(Claude 형식, Codex 형식). 실제 에이전트 연동은 M-05 | — | P5 |
| TEST-001 | 자동 | TC-HTL-07: `report tests` 표에 원문 열이 모두 있음 | — | P5-T3 |
| TEST-002 | 자동 | TC-HTL-08: JUnit fixture 3종(pytest, vitest, go-junit-report). 없는 locator → NOT RUN, skipped/error 처리 | — | P5-T3 |
| TRACE-001 | 자동 | TC-HTL-09: REQ ID 중복 거부 | V-12 | P5-T3 |
| TRACE-002 | 자동 | TC-HTL-10: requirements가 없는 테스트 경고 | V-12 | P5-T3 |
| TRACE-003 | 자동 | TC-HTL-11: `trace check`가 테스트 없는 REQ를 보고 → 1 | V-12 | P5-T3 |
| TRACE-004 | 자동 | TC-HTL-12: `req impact` 결과가 revision이 바뀐 REQ의 테스트 목록 | V-12 | P5-T3 |
| TRACE-005 | 자동 | TC-HTL-13: 보고서가 "구현 정확성"과 "테스트 설계 타당성"을 다른 절로 나눔 | — | P5-T3 |
| CE-001 | 자동 + 스킬 검토 | TC-HTL-14: counterexamples 상태 전이(PROPOSED → ACCEPTED/REJECTED/NEEDS_SPEC → CONVERTED). TC-SKL-02: `counterexample-hunter` standard overlay에 블랙박스 단계·NEEDS_SPEC·기록 형식이 있고, restricted 원본은 바뀌지 않음(Q7) | V-13 | P5-T5 |
| CE-002 | 자동 | TC-HTL-15: C 등급 Task는 반례 기록이 없으면 submit 거부 | — | P5-T5 |
| ALGO-001 | 스킬 검토 | TC-SKL-03: `algorithm-options` standard overlay에 8개 검토 항목이 있고 restricted 원본은 바뀌지 않음(Q7) | — | P5-T6 |
| DATA-001 | 스킬 검토 | TC-SKL-04: `data-quality-validator`의 frontmatter·필수 항목 8개, "무조건 삭제 금지" 조항 | — | P5-T6 |
| SESS-001 | 자동 | TC-HTL-16: recover fixture에서 7개 항목 복원 | V-15 | P5-T7 |
| SESS-002 | 자동 | TC-HTL-17: HANDOFF.md에는 승인 상태만 있고 WIP는 `.kit/work/wip/`에 분리 | — | P5-T7 |
| SESS-003 | 자동 | TC-HTL-18: 키트 소유가 아닌 `HANDOFF.md`가 있으면 건드리지 않음. 상태 파일은 `.kit/` 아래에만 | — | P5-T7 |

### SKILL · USER · DOC (보강)

| REQ | 검증 | TC / 절차 | V | Phase |
|---|---|---|---|---|
| SKILL-001 | 자동 + 스킬 검토 | TC-SKL-05: `launch-compliance-check`가 20개 점검 항목을 모두 가짐(입력 파일 대조), 판정 4종(PASS/FAIL/N/A/NEEDS_HUMAN), 법령 인용마다 VERIFIED-DOC/UNVERIFIED 표기, "법률 자문 아님" 문구, `launch` 팩·standard 전용 | — | P5 |
| USER-001 | 자동 | TC-USR-01: `user/` 스냅샷이 `${HOME}` 템플릿만 쓰고 절대경로·사용자 이름이 없음 | V-20 | P4-T7 |
| USER-002 | 자동 | TC-USR-02: `install --scope user --dry-run` → 임시 HOME 무변경. TC-USR-03: 비대화형 + `--yes` 없음 → 64. TC-USR-04: 백업 → 소유 구간·키만 수정, 사용자 내용 보존, uninstall·restore. TC-USR-05: `~/.claude.json`은 쓰지 않고 Manual step만 출력. TC-USR-06: AGENTS.md 28 KiB 초과 경고 | V-19 | P4-T7 |
| USER-003 | 자동 | TC-USR-07: capture 기본 dry-run 무변경, `--write`로 `user/`에 씀 | V-21 | P4-T7 |
| USER-004 | 자동 | TC-USR-08: 가짜 토큰·auth 파일·`projects.*`·sqlite fixture로 capture → 아무것도 나오지 않음, 스캐너가 걸리면 1. TC-SEC-05: 레포 `user/`·`third_party/` 전체 비밀값 스캔(항상 실행). TC-USR-09: capture → install 왕복 내용 일치 | V-20, V-21 | P4-T7 |
| USER-005 (P4-T7 반영) | 자동 + 수동 | `tests/userscope/test_capture.py`(TC-USR-01, 07, 08, TC-SEC-05, 비밀값 패턴), `tests/userscope/test_user_install.py`(TC-USR-02~06, 09, 10, 충돌·인수 규칙). OMX는 실제로 29개 스킬·32개 prompts이며 agents/*.toml은 태그에 없어 설치하지 않는다. 이하 원래 문구: TC-USR-10: OMX 스킬 28개와 agents·prompts가 임시 HOME의 `~/.codex/`에 설치되고 sources.lock과 일치. OMX 자체 설치 흔적이 있으면 CONFLICT. 실제 Codex 로드는 M-01 | — | P4-T7 |
| DOC-001 | 문서 | §12 문서 목록 체크리스트(P7) + `EXTENDING.md` | — | P7 |

### 커버리지 요약

| 구분 | 수 |
|---|---|
| 원문 REQ | 71 |
| 보강 REQ(SRC-006~009, SKILL-001, USER-001~005) | 10 |
| 합계 | **81**, 연결되지 않은 REQ 0 |
| 자동 테스트가 없는(문서·수동만 있는) REQ | AGENT-004, SRC-001, SRC-006, SRC-008, DOC-001 — 모두 문서 산출물 요구사항 |

## 3. 검증 매트릭스 V-01~V-24

| V | 연결 TC |
|---|---|
| V-01 | TC-GLD-01, TC-CLI-01 |
| V-02 | TC-GLD-02 |
| V-03 | TC-PRF-01 |
| V-04 | TC-ADP-08, TC-GLD(rerun-x3) |
| V-05 | TC-WRT-01, TC-MAN-01 |
| V-06 | TC-ADP-04 |
| V-07 | TC-ADP-05 |
| V-08 | TC-ADP-09, TC-CLI-06 |
| V-09 | TC-SEC-02, TC-CLI-09 |
| V-10 | TC-SRC-01 |
| V-11 | TC-MAN-05, TC-MAN-07 |
| V-12 | TC-HTL-09~12 |
| V-13 | TC-HTL-14 |
| V-14 | TC-HTL-03 |
| V-15 | TC-HTL-16 |
| V-16 | TC-XPL-01, M-04 |
| V-17 | TC-SEC-03 |
| V-18 | TC-SEC-04 |
| V-19 | TC-USR-02 |
| V-20 | TC-USR-01, TC-SEC-05 |
| V-21 | TC-USR-07, TC-USR-09 |
| V-22 | TC-GLD-02, TC-SRC-06 |
| V-23 | TC-SRC-02, TC-SRC-13 |
| V-24 | TC-SRC-03, TC-SRC-09 |

## 4. 수동 검증 (책임자: 검토자)

| ID | 내용 | 절차 | 기록 위치 |
|---|---|---|---|
| M-01 | Codex 스킬·MCP 로드 | 설치한 대상에서 Codex를 열고 `/skills`, `/mcp` 확인. user 범위는 `~/.codex/skills`(OMX 포함) | `docs/v2/manual/M-01.md` |
| M-02 | Claude Code 스킬·MCP·플러그인 로드 | `/skills`, `/mcp`, `/plugin`. `both`에서 `.agents/skills` 중복이 보이는지(R-4) | M-02.md |
| M-03 | Python 3.9 | `uv python install 3.9` 후 전체 테스트(네트워크 승인 필요) | M-03.md |
| M-04 | Linux·macOS·pwsh 7 | `devtools/manual_verify.sh` / `.ps1` | M-04.md |
| M-05 | 승인 훅 실제 동작 | `--hooks` 설치 뒤 각 에이전트에서 "승인" 입력 → `by: human-hook` 기록. 에이전트에게 승인 파일 쓰기를 시키면 차단되는지 | M-05.md |
| M-06 | user 범위 첫 실제 적용 | 이 PC에서 `install --scope user --dry-run`의 diff를 검토한 뒤 직접 적용 → M-01·M-02 | M-06.md |

결과는 실행한 사람과 날짜를 적고 `VERIFIED-RUN`으로 표시한다. 하지 않은 항목은 최종 보고서에 `NOT RUN`으로 남긴다.

## 5. 기존 기능 → 새 위치 대응표 (Phase 2 완료 기준)

| 기존 기능 | 기존 위치 | v2에서 | 비고 |
|---|---|---|---|
| CLI 파싱(옵션만) | `kit/cli.py` | **그대로**(서브커맨드 없는 경로) | ADR-002 |
| 실행 흐름 | `kit/app.py` | 그대로. P3-T3 이후 내부만 CodexAdapter 호출로 바뀌고, 골든 동일 | R-1 |
| AGENTS.md 구간 병합 | `kit/agentsmd.py` | 로직을 `kit/writers/markdown_block.py`로 추출. 기존 모듈은 래퍼로 남김 | import 호환 |
| config.toml 구간·MCP 허용 목록 | `kit/mcpconfig.py` | `kit/writers/toml_block.py` 추출 + `catalog/mcp.json` 매핑. 기존 모듈은 래퍼 | |
| 파일 계획·해시 소유 | `kit/plan.py` | 그대로 + Adapter가 `FileChange` 재사용 | |
| 원자적 쓰기·백업·state | `kit/register.py`, `kit/fsops.py` | 그대로 + 공통 실행기·`kit/manifest.py`가 사용 | `.kit/state.json` 유지(ADR-006) |
| 프로필 로드 | `kit/profiles.py` | 그대로(v1) + v2 로더가 정규화해 사용 | ADR-007 |
| 스킬 검증 | `kit/skills.py` | 키트 작성 규칙은 그대로. 외부 스킬용 공식 제약 검증을 따로 추가 | R-7 |
| 검증 | `kit/verify.py` | 그대로 + Adapter.verify | |
| 감사 | `kit/audit.py` | 그대로 + `.mcp.json` 감사 추가 | |
| 로그 마스킹 | `kit/logs.py` | 그대로. 패턴은 `kit/secrets_scan.py`와 공유 | |
| 보고서 | `kit/report.py` | 그대로 + 에이전트별 줄 | 05 §5 |
| 도구 설치 | `kit/tools.py` | 그대로(기존 경로 예외 Q3). 새 경로는 `InstallTool` Action | ADR-014 |
| preflight·mcpcheck·webcheck | `kit/*.py` | 그대로 | |
| 기존 11개 스킬 | `.agents/skills/` | **그대로**(원본) | ADR-001 |
| 키트 레포 정책 | `AGENTS.md` | 그대로 | |
| 프로필 5개 | `profiles/*.json` | 그대로 | |
| MCP 목록 | `mcp/*.json` | 그대로(기존 경로가 읽음) + `catalog/mcp.json` | |
| 셸 전용 모드 | `bootstrap.sh`, `bootstrap.ps1` | 그대로 + 서브커맨드 거부 문구 | 05 §8 |
| 외부 고지 | `THIRD_PARTY_NOTICES.md` | 그대로 + `sources.lock.json`에 같은 내용 | |
| 예제 생성 | `devtools/make_examples.py` | 그대로 | |

옮기거나 삭제하는 파일은 없다. 추출(writers)은 기존 모듈을 래퍼로 남기는 방식이므로 기존 테스트의 import도 그대로 동작한다.
