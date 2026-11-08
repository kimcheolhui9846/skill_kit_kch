# Skill Kit v2 최종 검증 보고서

- 작성: P7-T2, 2026-11-08. 같은 날 후속 1~4를 반영해 갱신했다.
- 형식: `00_PROMPT.md` §16
- 근거 원문: `docs/v2/regression/` (단계별 기록과 `raw/` 출력)

이 보고서의 실행 결과는 모두 실행 기록에서 가져왔다. 실행 기록이 없는 항목은 NOT RUN으로 적었다(R-01, REQ-TEST-002).

## 1. 요약

### 구현 범위
- **에이전트:** Codex와 Claude Code를 Adapter로 지원한다. `--agent codex|claude|both`로 고른다. 사용자 범위(`--scope user`)도 지원한다.
- **설치 CLI:**
  - 명령: `plan`, `install`, `verify`, `doctor`, `update`, `uninstall`, `restore`, `profiles`, `source`, `capture`.
  - 동작: 오프라인 실행, 백업과 복구, 소유 기록에 따른 제거를 지원한다.
  - 보고: 텍스트 보고서와 JSON 보고서를 낸다.
  - 이미 설치된 곳에 다시 `install`하면 이전 설치에서 빠진 항목을 정리한다(후속 3).
- **카탈로그:**
  - 스킬 38개(공통·에이전트별 층), MCP와 플러그인 카탈로그(허용 목록, 버전 고정, 기본 비활성).
  - 외부 출처는 `sources.lock.json`에 해시로 고정한다.
  - `source add`로 GitHub 주소에서 스킬을 받는다. 계획을 보여 준 뒤 승인을 받고, 원자적으로 반영한다.
- **프로필과 정책:**
  - v1 프로필 5개는 그대로 두고, 새 프로필 3개와 팩 4개(`hitl`, `workflow`, `research`, `launch`)를 더했다.
  - 정책은 `restricted`(v1 해커톤 규칙 그대로)와 `standard` 두 축이다. 공통 원칙 10개와 중간 승인 조건 9개(후속 1)는 원문 한 곳에서 관리한다.
- **HITL:**
  - Task 상태 기계(`kit task`)가 승인 전 진행을 막는다.
  - 근거 기반 테스트 보고(`kit report tests`, JUnit), 요구사항-테스트 추적(`kit req`/`kit trace`), 반례 기록(`kit ce`), 세션 복구(`kit recover`)를 제공한다.
  - 승인 훅(L2)은 opt-in이다.
- **검증 스킬:** 반례, 알고리즘 검토, 데이터 품질, 출시 전 점검(`launch-compliance-check`, 후속 4).
- **하위 호환:** 서브커맨드가 없는 기존 호출은 v1과 같은 결과를 낸다. 골든 기준선 24개로 확인했다.

### 제외 범위 (구현하지 않음)
- **원격(HTTP) MCP:** 기본 거부 그대로이고, opt-in 경로도 만들지 않았다.
- **`docs/EXTENDING.md`:** 06_TEST_PLAN의 DOC-001 행에 적었지만 만들지 않았다. Adapter를 추가하는 방법은 `docs/ARCHITECTURE.md`에 있다.
- **`launch-compliance-check`의 한국 법령 인용 확인:** 원문 확인은 하지 못했다. 스킬은 만들었고, 인용은 `UNVERIFIED`로 두었다(7절).

### 전체 판정: **PARTIAL**
- **자동 테스트:** 1790 passed, 2 skipped, 0 failed. P1 기준선 테스트 339개는 하나도 빠지거나 결과가 바뀌지 않았다.
- **REQ 84개**(원문 71 + 보강 10 + 이후 결정 3): 자동 테스트 PASS 81개, 문서로만 확인 3개. 미구현이나 부분 구현은 없다.
- **PARTIAL인 이유:** 사람이 확인해야 할 항목이 NOT RUN으로 남아 있다.
  - 에이전트 안에서의 로드 확인(M-01, M-02)
  - user 범위 실제 적용(M-06)
  - PowerShell 7, macOS, 실제 Linux 기기
  - 한국 법령 인용 원문 확인
  - 검토자 결정 대기 3건(8절)

## 2. 실행 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 Pro 10.0.26200 (한국어, cp949 콘솔) |
| Python | 3.12.10 (이 PC). Linux에서 3.9.25, 3.11.16, 3.14.4를 실행했다(P6-T4, WSL2 Ubuntu 26.04) |
| 도구 | uv 0.10.9, ruff 0.17.3, shellcheck 0.11.0, git 2.54.0.windows.1, Windows PowerShell 5.1.26100.9711 |
| 에이전트 CLI | codex-cli 0.166.0, Claude Code 2.1.319. 버전 확인만 했고, 훅 실험(M-05)은 격리된 설정 폴더에서 2026-11-07에 했다 |
| 실행 일시 | 최종 전체 실행 2026-11-08 14:55~14:59 (+0900) |
| 커밋 | `feat/v2-multi-agent` / HEAD `67921d46c5813e13d6eea6d7f8c25876577beaec`. P5-T2b 이후의 변경은 아직 커밋하지 않은 작업 트리에서 실행했다 |

## 3. 실행한 명령과 원문 결과 요약

| 명령 | 결과 요약(원문) | 일시 |
|---|---|---|
| `uv run --offline pytest -q -p no:cacheprovider --junitxml=docs/v2/regression/raw/f4-junit.xml` | `1790 passed, 2 skipped in 260.59s (0:04:20)`, exit 0 (`raw/f4-pytest.txt`) | 2026-11-08 14:59 |
| `uv run --offline ruff check .` | `All checks passed!` | 2026-11-08 15:00 |
| `uv run --offline ruff format --check .` | `172 files already formatted` | 2026-11-08 15:00 |
| `shellcheck` (git이 추적하는 `.sh` 4개) | 출력 없음, 모두 exit 0 | 2026-11-08 12:44 (그 뒤 `.sh` 변경 없음) |
| `uv run python devtools/req_coverage.py docs/v2/regression/raw/f4-junit.xml` | `PASS 81, 문서 3` (`regression/P7-T2-req-coverage.md`) | 2026-11-08 15:00 |
| 기준선 비교(P1 `baseline/raw/pytest-junit.xml` 대 `f4-junit.xml`, `classname::name` 단위) | 기준선 339개, 사라진 것 0, 결과가 바뀐 것 0, 새 실패 0 | 2026-11-08 15:00 |
| `uv run python devtools/run_doc_commands.py` | `95 commands, 0 unexpected` (`regression/P7-T1-doc-commands.md`, 후속 3에서 마이그레이션 절차를 바꾼 뒤 다시 실행) | 2026-11-08 14:23 |
| 후속 1~3 전체 실행 | `1670 passed` / `1740 passed` / `1754 passed`, 모두 2 skipped (`raw/f1~f3-pytest.txt`) | 2026-11-08 |
| P7-T2 첫 전체 실행 | `1669 passed, 2 skipped` (`raw/p7t2-pytest.txt`) | 2026-11-08 12:43 |
| Linux 전체 테스트(WSL2, Python 3.11.16 / 3.9.25) | `1407 passed, 23 skipped` / `1397 passed, 33 skipped` (`raw/p6t4-*-linux*`) | 2026-11-07 (P6-T4) |
| 승인 훅 실제 동작(M-05) | Claude 2.1.319와 Codex 0.166.0에서 "승인" 입력 → `by: human-hook` 기록, 승인 파일 쓰기 차단 (ADR-011) | 2026-11-07 |
| 출처 확인(WebFetch) | W3C WCAG 2.2(2024-12-12 Recommendation)의 1.1.1·1.4.3·2.1.1·2.4.7, EUR-Lex 2002/58/EC 통합본(2009-12-19)의 제5조 제3항 읽음. law.go.kr 3회, KLRI 1회는 본문을 받지 못함 | 2026-11-08 |

## 4. 요구사항 커버리지 (§4의 모든 REQ)

- 표는 `devtools/req_coverage.py`가 `raw/f4-junit.xml`에서 만들었다(`regression/P7-T2-req-coverage.md`와 같다).
- REQ와 테스트의 대응은 그 스크립트의 `MAP`에 있다.
- `tests/test_req_coverage.py`가 두 가지를 확인한다.
  - 문서의 REQ가 모두 대응표에 있다.
  - 대응표의 모든 패턴이 실제 테스트를 가리킨다.
  - 이 테스트의 변이 4개는 모두 잡혔다.
- "실행 결과"의 괄호 안 숫자는 그 REQ에 연결된 테스트 케이스 수다. 매개변수화 케이스를 포함하고, 한 테스트가 여러 REQ에 연결될 수 있다.
- "문서"는 자동 테스트 없이 산출물로만 확인한 REQ다.

| REQ | 구현 상태 | 테스트(파일) | 실행 결과 | 비고 |
|---|---|---|---|---|
| REQ-COMPAT-001 | 구현 | `golden/test_golden_legacy.py`, `test_cli.py`, `cli/test_commands.py`, `adapters/test_adapters.py` | PASS (63 passed) | 골든 기준선 24개 |
| REQ-COMPAT-002 | 구현 | `catalog/test_skill_tree.py`, `test_skills.py`, `catalog/test_sources.py` | PASS (79 passed) | v1 스킬은 8개가 아니라 11개(P1에서 확인) |
| REQ-COMPAT-003 | 구현 | `profiles/test_profile_resolver.py`, `test_profiles.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (39 passed) |  |
| REQ-COMPAT-004 | 구현 | `cli/test_install_cleanup.py`, `writers/test_manifest.py`, `cli/test_lifecycle.py`, `cli/test_commands.py` | PASS (20 passed) | v1 위 standard 직접 설치의 정리(후속 3, 2026-11-08). P7-T1에서 찾은 결함 수정 |
| REQ-COMPAT-005 | 구현 | `test_model.py`, `cli/test_commands.py`, `cli/test_entrypoints_v2.py`, `test_entrypoints.py` | PASS (28 passed) |  |
| REQ-COMPAT-006 | 구현 | `test_entrypoints.py`, `cli/test_entrypoints_v2.py` | PASS (20 passed) |  |
| REQ-COMPAT-007 | 구현 | `test_stdlib_only.py`, `test_p6_platform.py` | PASS (73 passed) | TC-SEC-01 AST 검사(후속 2). 3.9 실제 실행은 P6-T4(Linux 3.9.25) |
| REQ-ARCH-001 | 구현 | `catalog/test_skill_tree.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (4 passed) |  |
| REQ-ARCH-002 | 구현 | `catalog/test_mcp_catalog.py`, `catalog/test_plugin_install.py`, `catalog/test_skill_tree.py` | PASS (3 passed) |  |
| REQ-ARCH-003 | 구현 | `adapters/test_adapters.py`, `cli/test_commands.py` | PASS (2 passed) |  |
| REQ-ARCH-004 | 구현 | `adapters/test_adapters.py`, `profiles/test_profile_resolver.py` | PASS (2 passed) |  |
| REQ-AGENT-001 | 구현 | `cli/test_commands.py` | PASS (4 passed) |  |
| REQ-AGENT-002 | 구현 | `adapters/test_claude_adapter.py`, `cli/test_commands.py` | PASS (2 passed) | 위치 근거: 02_COMPATIBILITY_MATRIX.md |
| REQ-AGENT-003 | 구현 | `test_p6_matrix.py`, `adapters/test_claude_adapter.py`, `cli/test_commands.py`, `cli/test_lifecycle.py` | PASS (4 passed) |  |
| REQ-AGENT-004 | 구현 | `test_p6_agent_load_check.py` | PASS (4 passed) | 문서: 02_COMPATIBILITY_MATRIX.md(행마다 출처·확인 수준). 매트릭스 자체를 검사하는 테스트는 없음 |
| REQ-AGENT-005 | 구현 | `adapters/test_claude_adapter.py`, `test_p6_agent_load_check.py` | PASS (5 passed) | 실제 로드는 AGENT_LOAD_CHECK.md(검토자, NOT RUN) |
| REQ-INST-001 | 구현 | `cli/test_commands.py` | PASS (3 passed) |  |
| REQ-INST-002 | 구현 | `cli/test_commands.py`, `cli/test_network.py` | PASS (6 passed) |  |
| REQ-INST-003 | 구현 | `cli/test_commands.py`, `test_verify.py` | PASS (10 passed) |  |
| REQ-INST-004 | 구현 | `cli/test_commands.py` | PASS (2 passed) |  |
| REQ-INST-005 | 구현 | `cli/test_lifecycle.py` | PASS (4 passed) |  |
| REQ-INST-006 | 구현 | `cli/test_lifecycle.py` | PASS (6 passed) |  |
| REQ-INST-007 | 구현 | `cli/test_commands.py`, `cli/test_network.py`, `test_p6_matrix.py` | PASS (4 passed) |  |
| REQ-INST-008 | 구현 | `cli/test_lifecycle.py`, `cli/test_commands.py` | PASS (6 passed) |  |
| REQ-INST-009 | 구현 | `cli/test_commands.py`, `test_report.py`, `cli/test_network.py` | PASS (14 passed) |  |
| REQ-INST-010 | 구현 | `test_p6_matrix.py`, `test_p6_platform.py` | PASS (11 passed) | Linux는 P6-T4(WSL2). PowerShell 7·실제 Linux 기기는 NOT RUN |
| REQ-SAFE-001 | 구현 | `test_p6_matrix.py`, `adapters/test_claude_adapter.py`, `writers/test_json_keys.py`, `test_agentsmd.py` | PASS (24 passed) |  |
| REQ-SAFE-002 | 구현 | `test_register.py`, `cli/test_lifecycle.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-SAFE-003 | 구현 | `writers/test_json_keys.py`, `cli/test_lifecycle.py` | PASS (18 passed) |  |
| REQ-SAFE-004 | 구현 | `test_p6_matrix.py`, `test_idempotency.py`, `cli/test_commands.py`, `adapters/test_claude_adapter.py` | PASS (8 passed) |  |
| REQ-SAFE-005 | 구현 | `cli/test_commands.py`, `cli/test_lifecycle.py`, `test_failure_recovery.py`, `test_blocked_on_error.py` | PASS (18 passed) |  |
| REQ-SAFE-006 | 구현 | `cli/test_network.py`, `test_p6_matrix.py` | PASS (13 passed) |  |
| REQ-SAFE-007 | 구현 | `test_p6_matrix.py`, `test_security.py`, `cli/test_network.py` | PASS (19 passed) |  |
| REQ-SAFE-008 | 구현 | `test_p6_matrix.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-SAFE-009 | 구현 | `catalog/test_mcp_catalog.py`, `adapters/test_claude_adapter.py`, `cli/test_commands.py`, `test_audit.py` | PASS (30 passed) |  |
| REQ-SAFE-010 | 구현 | `test_p6_matrix.py`, `cli/test_commands.py`, `cli/test_lifecycle.py`, `userscope/test_user_install.py` | PASS (6 passed) |  |
| REQ-SAFE-011 | 구현 | `catalog/test_p4t9_credentials.py` | PASS (36 passed) | P4-T9 결정 |
| REQ-SAFE-012 | 구현 | `cli/test_p4t9_followups.py` | PASS (17 passed) | 2026-11-06 결정 |
| REQ-PROF-001 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (14 passed) |  |
| REQ-PROF-002 | 구현 | `profiles/test_profile_resolver.py` | PASS (19 passed) |  |
| REQ-PROF-003 | 구현 | `profiles/test_profile_resolver.py` | PASS (2 passed) |  |
| REQ-PROF-004 | 구현 | `profiles/test_profile_resolver.py`, `profiles/test_p4t6_profiles_policy.py` | PASS (17 passed) |  |
| REQ-PROF-005 | 구현 | `profiles/test_profile_resolver.py`, `cli/test_commands.py` | PASS (2 passed) | 보여 주는 목록은 정책 적용 전(11개). standard 실제 설치는 17개(검토자 결정 대기) |
| REQ-SRC-001 | 구현 | - | 문서 | 문서: 07_SOURCES_EVALUATION.md |
| REQ-SRC-002 | 구현 | `catalog/test_sources.py`, `test_p6_security.py` | PASS (19 passed) |  |
| REQ-SRC-003 | 구현 | `catalog/test_sources.py`, `test_skills.py` | PASS (4 passed) |  |
| REQ-SRC-004 | 구현 | `sources/test_source_add.py` | PASS (2 passed) | P4-T3 중간 승인 기록 |
| REQ-SRC-005 | 구현 | `catalog/test_sources.py`, `sources/test_source_add.py` | PASS (6 passed) | 비교표: 07_SOURCES_EVALUATION.md |
| REQ-SRC-006 | 구현 | - | 문서 | 문서: 08_USER_SOURCES.md |
| REQ-SRC-007 | 구현 | `catalog/test_sources.py`, `catalog/test_skill_tree.py` | PASS (3 passed) |  |
| REQ-SRC-008 | 구현 | - | 문서 | 문서: 07_SOURCES_EVALUATION.md |
| REQ-SRC-009 | 구현 | `sources/test_source_add.py` | PASS (81 passed) |  |
| REQ-POL-001 | 구현 | `profiles/test_p4t6_profiles_policy.py`, `profiles/test_p5t1_skill_guide.py` | PASS (23 passed) |  |
| REQ-POL-002 | 구현 | `profiles/test_p4t6_profiles_policy.py`, `cli/test_commands.py` | PASS (3 passed) |  |
| REQ-POL-003 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (1 passed) |  |
| REQ-POL-004 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (1 passed) |  |
| REQ-HITL-001 | 구현 | `hitl/test_tasks.py` | PASS (9 passed) |  |
| REQ-HITL-002 | 구현 | `hitl/test_tasks.py` | PASS (2 passed) |  |
| REQ-HITL-003 | 구현 | `hitl/test_tasks.py`, `test_p6_e2e.py` | PASS (10 passed) |  |
| REQ-HITL-004 | 구현 | `profiles/test_p4t6_profiles_policy.py` | PASS (3 passed) | §5.3 조건 9개를 standard 정책 Approval 절에 둠(후속 1, 2026-11-08) |
| REQ-HITL-005 | 구현 | `hitl/test_tasks.py` | PASS (10 passed) |  |
| REQ-HITL-006 | 구현 | `hitl/test_tasks.py`, `hitl/test_approval_hook.py` | PASS (83 passed) | L2 훅 실제 동작은 M-05 VERIFIED-RUN(2026-11-07) |
| REQ-TEST-001 | 구현 | `hitl/test_report_tests.py` | PASS (4 passed) |  |
| REQ-TEST-002 | 구현 | `hitl/test_report_tests.py`, `test_p6_e2e.py` | PASS (30 passed) |  |
| REQ-TRACE-001 | 구현 | `hitl/test_trace.py` | PASS (14 passed) |  |
| REQ-TRACE-002 | 구현 | `hitl/test_trace.py` | PASS (1 passed) |  |
| REQ-TRACE-003 | 구현 | `hitl/test_trace.py` | PASS (14 passed) |  |
| REQ-TRACE-004 | 구현 | `hitl/test_trace.py`, `test_p6_e2e.py` | PASS (17 passed) |  |
| REQ-TRACE-005 | 구현 | `hitl/test_report_tests.py` | PASS (7 passed) |  |
| REQ-CE-001 | 구현 | `hitl/test_counterexamples.py` | PASS (27 passed) |  |
| REQ-CE-002 | 구현 | `hitl/test_counterexamples.py` | PASS (4 passed) |  |
| REQ-ALGO-001 | 구현 | `catalog/test_p5t6_skills.py` | PASS (1 passed) |  |
| REQ-DATA-001 | 구현 | `catalog/test_p5t6_skills.py` | PASS (14 passed) |  |
| REQ-SESS-001 | 구현 | `hitl/test_recover.py`, `test_p6_e2e.py` | PASS (23 passed) |  |
| REQ-SESS-002 | 구현 | `hitl/test_recover.py` | PASS (11 passed) |  |
| REQ-SESS-003 | 구현 | `hitl/test_recover.py` | PASS (4 passed) |  |
| REQ-SKILL-001 | 구현 | `catalog/test_launch_compliance.py` | PASS (34 passed) | TC-SKL-05(후속 4). 한국 법령 인용은 원문 미확인이라 UNVERIFIED |
| REQ-USER-001 | 구현 | `userscope/test_capture.py` | PASS (10 passed) |  |
| REQ-USER-002 | 구현 | `userscope/test_user_install.py` | PASS (10 passed) | 실제 홈 적용(M-06)은 NOT RUN |
| REQ-USER-003 | 구현 | `userscope/test_capture.py`, `userscope/test_user_install.py` | PASS (4 passed) |  |
| REQ-USER-004 | 구현 | `userscope/test_capture.py` | PASS (10 passed) |  |
| REQ-USER-005 | 구현 | `userscope/test_user_install.py`, `catalog/test_sources.py` | PASS (4 passed) | 실제 Codex 로드는 AGENT_LOAD_CHECK.md |
| REQ-USER-008 | 구현 | `userscope/test_own_files.py` | PASS (10 passed, 1 skipped) | Q4 결정(2026-11-06) |
| REQ-DOC-001 | 구현 | `test_doc_commands.py`, `test_catalog_doc.py` | PASS (76 passed) | §12 문서 13종. 문서 명령 95개 실행 기록: P7-T1-doc-commands.md |

PASS 81, 문서 3

## 5. 테스트 결과

| Test ID | Requirement | Scenario | Expected | Actual | Status |
|---|---|---|---|---|---|
| 골든(`tests/golden/`) | COMPAT-001 | 기존 호출 24가지(5개 프로필 × 기본/dry-run/verify-only/no-mcp, 3회 반복, 기존 AGENTS.md, 고친 구간, 키트 자신을 대상으로 지정) | 기준선과 같은 트리, 보고서, 종료 코드 | 49 passed | PASS |
| V-01~V-18 (`test_p6_matrix.py` 외) | 원문 검증 매트릭스 | P6-T2 표 | 18개 모두 근거 테스트 통과 | `test_p6_matrix.py` 19 passed. 나머지는 4절의 해당 REQ | PASS |
| P6-T3 보안(`test_p6_security.py`) | SAFE-003/007/009, SRC-002 | 링크를 통한 경로 탈출, 링크를 만들지 않음, 감사 규칙 일치, lock 해시 독립 재계산 | 대상 밖에 쓰지 않음, 거부 | 40 passed | PASS |
| P6-T4 플랫폼(`test_p6_platform.py`) | INST-010, COMPAT-007 | PowerShell 5.1용 ASCII, 골든 바이트, tomllib 유무 | 플랫폼마다 같은 결과 | 8 passed (Windows). Linux 기록은 3절 | PASS |
| P6-T5 E2E(`test_p6_e2e.py`) | HITL-003, TEST-002, TRACE-004, SESS-001 | 요구사항 3개, Task 2개, 실제 프로세스, 실제 pytest JUnit | 승인 전 진행 거부, HANDOFF 갱신, recover, impact | 7 passed | PASS |
| P6-T6 점검표(`test_p6_agent_load_check.py`) | AGENT-005 | 점검표의 스킬 목록, 파일, 출처가 실제 설치와 맞음 | 일치 | 4 passed | PASS |
| P7-T1 문서(`test_doc_commands.py`, `test_catalog_doc.py`) | DOC-001 | 문서의 명령이 모두 실행 기록에 있음, 카탈로그 문서가 최신임 | 일치 | 76 passed | PASS |
| P7-T2 커버리지(`test_req_coverage.py`) | TRACE-003 (이 개발 자체) | REQ 대응표가 완전하고 실제 테스트를 가리킴 | 일치 | 155 passed | PASS |
| 후속 1 TC-HTL-04 | HITL-004 | 중간 승인 조건 9개가 두 에이전트 정책의 Approval 절에 한 번씩 있음 | 일치, restricted에는 없음 | 1 passed (변이 4개 잡힘) | PASS |
| 후속 2 TC-SEC-01(`test_stdlib_only.py`) | COMPAT-007 | 런타임·설치 파이썬 파일 66개의 import | 표준 라이브러리와 키트만 | 69 passed (변이 5개 잡힘) | PASS |
| 후속 3(`test_install_cleanup.py` 외) | COMPAT-004, SAFE-002/003/005 | v1·v2 설치 위 재설치, 고친 파일, 롤백, restore, 일부만 소유한 파일, user 범위 | 빠진 항목만 정리, 고친 것은 CONFLICT | 13 + 1 passed (변이 5개 잡힘) | PASS |
| 후속 4 TC-SKL-05(`test_launch_compliance.py`) | SKILL-001 | 20개 항목(입력 목록 순서), 판정 4종, 출처 수준, 설치 범위 7가지, 기존 경로 | 일치 | 34 passed (변이 9개 잡힘) | PASS |
| 심볼릭 링크 2개 | SAFE-003, USER-008 | 링크를 통한 탈출, 목록의 링크 파일 | 거부, Note | 이 PC에서 링크를 만들 수 없음. Linux(P6-T4)에서는 실행되어 통과 | SKIPPED |
| 에이전트 안 로드(M-01, M-02) | AGENT-005, USER-005 | `/skills`, `/mcp`, `/plugin`, `/hooks` | `AGENT_LOAD_CHECK.md` 표대로 보임 | 실행 기록 없음 | NOT RUN |

폴더별 결과(`f4-junit.xml`):

| 폴더 | passed | skipped |
|---|---|---|
| 루트 `tests/test_*.py` | 721 | 1 |
| adapters | 23 | 0 |
| catalog | 271 | 0 |
| cli | 145 | 0 |
| golden | 49 | 0 |
| hitl | 307 | 0 |
| profiles | 104 | 0 |
| sources | 81 | 0 |
| userscope | 56 | 1 |
| writers | 33 | 0 |

- **통계:** PASS 1790 / FAIL 0 / SKIPPED 2 / NOT RUN: 수동 항목 9개(7절)

## 6. 기존 기능 회귀

- **기준선 대비 새 실패: 0개.**
  - P1-T1 기준선의 339개 테스트가 모두 그대로 있고, 결과도 같다(338 passed, 1 skipped).
  - 건너뛴 1개는 기준선과 같은 심볼릭 링크 테스트다.
- **골든 테스트:** 49개 모두 통과했다.
  - 기준선 비교(실제 진입점 `python -I run_kit.py`)와 보고서 전문 비교(프로세스 안 실행)를 합친 수다.
  - 골든 출력 파일(`tests/golden/inprocess/`, `baseline/`)은 처음 만든 뒤 한 번도 다시 만들지 않았다.
- **승인받은 의도적 변경 목록:** 기존 호출의 결과(트리, 관리 구간, 보고서, 종료 코드)를 바꾼 것은 없다. 아래 변경은 모두 v1에 없던 입력이나 새 경로에만 해당한다.

| 변경 | 영향 | 근거 |
|---|---|---|
| 첫 인수가 서브커맨드면 새 경로로 간다 | v1에서는 위치 인수가 사용법 오류(64)였다. 지금은 새 명령으로 실행된다 | ADR-002 |
| 셸 전용 모드(Python 없음)에서 서브커맨드를 주면 64와 안내 문구 | v1에서도 64였다. 문구만 더했다 | ADR-013, 05_CLI_SPEC §8 |
| 상태 폴더 `.kit/`에 매니페스트와 `work/` 추가 | v1의 `.kit/state.json`은 그대로 읽고, 새 경로가 인수한다 | ADR-006 |
| ruff 대상에서 `third_party/` 제외 | 개발 도구 설정만 바뀌었다. 외부 코드는 해시로 고정되어 있어 고치지 않는다 | P6-T1 |
| v2 `install`이 이전 설치에서 빠진 항목을 정리 | 그대로인 것은 백업 뒤 지우고, 고친 것은 CONFLICT(1)로 보고한다. v1 위 standard 설치에서는 대체된 v1 스킬이 지워진다 | 후속 3 중간 승인(A안) |
| standard 정책에 중간 승인 조건 9개 | 이미 standard로 설치한 작업 공간은 정책 구간이 OUTDATED로 보이고 `update`로 갱신된다 | 후속 1 승인 |
| `web`·`fullstack`(standard)에 `launch-compliance-check` 추가 | 그 프로필의 설치 스킬이 하나 늘었다. 스냅숏 테스트 2개의 기대값을 바꿨다(트리거 3, 설계 승인 범위) | 후속 4 중간 승인 |

## 7. 미구현·미검증

| 항목 | 상태 | 이유 | 검토자 확인 방법 |
|---|---|---|---|
| `launch-compliance-check`의 한국 법령 인용 14개(S-01~S-14) | UNVERIFIED | law.go.kr 본문을 받지 못했다(스크립트 렌더링, 서비스 지연 안내, HTTP 500). 조문 번호와 내용은 확인하지 않은 후보다. 특히 S-09(전자상거래법 다크패턴 조항)는 조문 번호를 비워 두었다 | law.go.kr에서 조문과 시행일을 확인하고 `references/sources.md`의 수준과 날짜를 고친다(테스트가 날짜와 공식 URL을 요구한다) |
| Codex·Claude Code 안의 스킬·MCP·훅·서브에이전트 로드(M-01, M-02) | UNVERIFIED / NOT RUN | 에이전트 안에서만 볼 수 있다 | `docs/v2/AGENT_LOAD_CHECK.md` |
| 에이전트가 중간 승인 조건에서 실제로 멈추는지 | NOT RUN | 에이전트 안에서만 확인할 수 있다 | 위험한 요청(파일 삭제 등)을 주고 멈추는지 본다 |
| PowerShell 7 | NOT RUN | 이 PC에 `pwsh`가 없다 | `docs/v2/WINDOWS_MANUAL_CHECK.md` |
| 기본 설정 PowerShell 5.1의 리디렉션 인코딩 | NOT RUN | 에이전트가 실행한 셸은 설정이 다르다 | `WINDOWS_MANUAL_CHECK.md` |
| 실제 Linux 기기, macOS | NOT RUN | WSL2에서만 실행했다 | Linux·macOS에서 전체 테스트 |
| Python 3.9: Windows 실행, 그리고 후속 2~4 테스트 | NOT RUN | 3.9는 P6-T4에서 Linux(WSL)로만 실행했고, 그 뒤 지웠다. 후속 2의 3.9 판정 경로는 3.12에서 흉내 내어 확인했다 | `uv run -p 3.9 pytest -q` (3.9를 받으려면 네트워크 필요) |
| user 범위 실제 적용(`install --scope user --yes`, M-06) | NOT RUN | 실제 홈에 쓰는 동작이라 검토자가 한다. dry-run과 비대화형 거부(64)는 실행했다 | `install --scope user --dry-run`의 diff를 검토한 뒤 적용 |
| `--plugin` 실제 설치 | NOT RUN(이번) | 네트워크와 사용자 설정이 필요하다. P4-T5에서 격리된 설정 폴더로 확인한 기록이 있다 | `docs/guides/CLAUDE_CODE.md` |
| 실제 `npx` MCP 핸드셰이크 | NOT RUN(v2) | 네트워크 동작이다. 테스트는 가짜 서버만 쓴다 | `kit install --profile python`을 네트워크와 함께 실행 |
| `git clone`으로 받은 v2 | NOT RUN | `main`에 병합하기 전이다 | 병합한 뒤 README의 명령 |
| 2026-11-08 이전 키트로 v1 위에 standard를 설치한 작업 공간 | 자동 정리 불가 | 남은 v1 파일이 기록 밖에 있다 | `MIGRATION_V1_TO_V2.md` 3절대로 직접 지운다 |

## 8. 보안·호환성 주의사항

- **네트워크:**
  - 네트워크를 쓰는 동작은 `plan`에 `[network]`로 표시된다.
  - 비대화형 실행에서 `--yes`가 없으면 SKIPPED로 끝난다.
  - `--offline`이면 0회다. 소켓과 하위 프로세스를 막은 fixture로 확인했다(V-09).
- **승인 강제 수준(ADR-011):**
  - L0(정책 문구)과 L1(상태 기계)은 기본으로 켜진다.
  - L2(훅)는 opt-in(`--hooks`)이다.
  - L1은 셸 명령으로 우회할 수 있다. 승인 기록의 `by`(human-cli / human-hook / agent-recorded)로 나중에 가려낼 수 있을 뿐, 위조를 원천 차단하지는 못한다.
- **보안 감사는 쓰기 뒤에 한다(v1과 같음).**
  - 작업 공간에 허용 목록 밖 MCP 서버가 이미 있으면 BLOCKED(2)로 끝난다. 그때 키트 파일은 이미 써져 있다.
  - 사용자 서버는 고치지 않고, 키트가 실행하지도 않는다.
  - 이 순서를 유지할지는 검토자 결정을 기다린다(P6-T2).
- **재설치 정리(후속 3):**
  - 다른 프로필·정책으로 다시 `install`하면 이전 설치에서 빠진 키트 항목을 지운다. 지우기 전에 백업하므로 `kit restore --backup <시각>`으로 되돌릴 수 있다.
  - 사용자가 고친 항목은 지우지 않고 `stale:` CONFLICT로 남긴다. 에이전트가 그 낡은 스킬을 함께 읽을 수 있다.
- **비밀값:**
  - 설정 파일에는 환경 변수 이름만 쓴다.
  - 텍스트·JSON 출력과 로그는 값 단위로 마스킹한다(V-17).
  - `capture`는 auth·세션·sqlite·기록 파일을 가져오지 않는다.
- **전역 설정:** project 범위 명령은 HOME을 바꾸지 않는다(V-18). 전역을 바꾸는 것은 `--scope user`뿐이고, 백업과 확인을 거친다.
- **`launch-compliance-check`는 법률 자문이 아니다.** 판정은 증거 수집이고, 법적 판단은 NEEDS_HUMAN으로 남긴다. 한국 법령 인용은 모두 UNVERIFIED다.
- **`kit profiles show`:** 정책을 적용하기 전 목록(core 11개)을 보여 준다. standard로 실제 설치되는 목록(17개)과 다르다. 실제 목록은 `kit plan` 또는 `docs/CATALOG.md`로 본다(결정 대기).
- **`hitl` 팩:** 스킬을 직접 나열하지 않는다. `task-approval`, `session-recovery`는 standard 정책의 `core` 팩으로 들어온다(ADR-008과 다름, 결정 대기).
- **Python 3.9/3.10:** tomllib가 없어서 Codex `config.toml` 감사가 UNVERIFIED로 끝나고, 사람이 확인하라는 안내가 나온다.
- **Claude Code의 `.agents/skills`:** `--agent both`일 때 Claude Code가 `.agents/skills`도 읽는지는 에이전트 안에서 확인해야 한다(`AGENT_LOAD_CHECK.md`).

## 9. 질문 6개에 대한 답

1. **어떤 요구사항이 구현됐는가?**
   - REQ 84개 모두 구현했다.
   - 이 중 문서 산출물 REQ 3개(SRC-001, SRC-006, SRC-008)는 07, 08 문서로 충족했다.
   - P7-T2에서 찾은 빈 곳 4개(HITL-004, COMPAT-007의 테스트, COMPAT-004 결함, SKILL-001)는 후속 1~4로 채웠다.
2. **어떤 테스트가 해당 요구사항을 검증하는가?**
   - 4절 표의 "테스트(파일)" 열과 `devtools/req_coverage.py`의 `MAP`에 있다.
   - 테스트 이름 단위의 대응은 `06_TEST_PLAN.md` 2절과 P6-T2 매트릭스에 있다.
3. **테스트는 실제로 실행됐는가?**
   - 실행됐다. 2026-11-08 14:55에 1792개 케이스가 실행되었고, 근거는 `raw/f4-junit.xml`이다.
   - 4절의 결과는 모두 그 파일에서 셌다.
   - 수동 항목 9개는 실행 기록이 없어 NOT RUN이다.
4. **실패한 테스트는 무엇인가?**
   - 없다(0 failed).
   - 건너뛴 2개는 이 PC에서 심볼릭 링크를 만들 수 없어서다.
5. **테스트가 누락된 요구사항은 무엇인가?**
   - 자동 테스트가 없는 것은 문서 산출물 REQ 3개(SRC-001, SRC-006, SRC-008)뿐이다.
   - AGENT-004는 매트릭스 행 자체를 검사하는 테스트가 없다. 점검표 정합성 테스트와 문서로 확인한다.
   - 에이전트 안 동작(로드, 중간 승인에서 멈춤)은 자동 테스트로 확인할 수 없다.
6. **사람이 추가로 검토해야 하는 위험은 무엇인가?**
   - 한국 법령 인용 14개의 원문 확인.
   - 에이전트 안 로드 확인(M-01, M-02).
   - user 범위의 첫 실제 적용(M-06).
   - L1 승인 강제는 우회할 수 있다는 한계.
   - 감사를 쓰기 뒤에 하는 순서.
   - `profiles show`와 실제 설치의 차이, `hitl` 팩의 스킬 소속.
   - 재설치 정리가 대체된 v1 스킬을 지운다는 점(백업 있음).
   - P5-T2b 이후 변경이 아직 커밋되지 않았다는 점.

## 10. 후속 작업 제안

| 순서 | 작업 | 등급 | 이유 |
|---|---|---|---|
| 1 | 한국 법령 인용 14개 확인 → `sources.md`의 수준과 날짜 갱신 | S | 사람이 law.go.kr에서 확인하거나, 접근할 수 있는 환경에서 다시 조회 |
| 2 | 검토자 수동 확인: `AGENT_LOAD_CHECK.md`, `WINDOWS_MANUAL_CHECK.md`, M-06 | - | 7절의 NOT RUN 해소 |
| 3 | 결정 대기 항목 정리: `profiles show` 출력, `hitl` 팩 소속(ADR-008), 감사 순서 | S | 8절 |
| 4 | `docs/EXTENDING.md` (새 에이전트 Adapter 추가 안내) | L | 06_TEST_PLAN DOC-001 행 |
| 5 | 비밀값 감사 → 커밋(P5-T2b~후속 4) → PR → `main` 병합 뒤 `git clone` 설치 확인 | - | 7절. 커밋과 푸시는 요청이 있을 때만 한다 |
