# P6-T2 필수 검증 매트릭스 V-01~V-18

- 실행 일시: 2026-11-07, Windows 11 Pro, Python 3.12.10
- 전체 실행: `uv run --offline pytest -q -p no:cacheprovider --junitxml=…` → **1375 passed, 2 skipped** (P6-T1 이후 추가 19개)
- 판정: 표의 테스트를 JUnit 결과에서 모아 셌다. "방법 일치"는 00_PROMPT §11 P6-T2의 방법을 그대로 따르는 테스트가 있는지를 뜻한다. 그런 테스트가 없던 V-04·05·07·08·09·16·17·18은 `tests/test_p6_matrix.py`에 새로 만들었다.

| V | 검증 항목 | 근거 테스트 | 수 | 결과 | 방법 일치 |
|---|---|---|---|---|---|
| V-01 | 기존 Codex 설치 명령 | `tests/golden/test_golden_legacy.py`(기준선 24개 스냅숏과 비교), `tests/test_cli.py`, `test_codex_plan_equals_legacy_plan` | 62 | PASS | 예 |
| V-02 | 기존 스킬 정상 설치(이름·해시) | `test_restricted_catalog_is_exactly_the_legacy_skills`, `test_layered_files_equal_the_original_for_legacy_skills`, `test_restricted_new_path_installs_only_the_legacy_skills`, `tests/test_skills.py` | 78 | PASS | 예 |
| V-03 | 기존 프로필 유지 | `tests/profiles/test_profile_resolver.py`(TC-PRF-01 v1 = 기준선), `test_new_profile_resolution_snapshot` | 60 | PASS | 예 |
| V-04 | 반복 설치 시 중복 없음 | **`test_v04_three_installs_in_a_row_leave_the_same_tree`**(새 경로 3회), 골든 `python__rerun-x3`(기존 경로 3회), 재실행 테스트 2개 | 4 | PASS | 예(신규) |
| V-05 | 기존 사용자 설정 보존 | **`test_v05_*` 3개**(AGENTS.md CRLF, CLAUDE.md 한글, config.toml, .mcp.json, settings.json → install both --hooks → uninstall), 기존 보존 테스트, `tests/writers/test_manifest.py` | 23 | PASS | 예(신규) |
| V-06 | Claude 파일 위치 | `test_files_land_in_documented_places`, `test_claude_install_writes_only_claude_files` | 2 | PASS | 예 |
| V-07 | Codex·Claude 무충돌 | **`test_v07_codex_files_keep_their_hash_through_the_whole_order`**(codex → claude → both → uninstall claude), 기존 2개 | 3 | PASS | 예(신규) |
| V-08 | dry-run·plan 무변경 | **`test_v08_every_dry_run_leaves_workspace_and_home_alone`**(plan, install/update/uninstall/restore --dry-run, user 범위 --dry-run, capture 기본값; 작업 공간 + HOME + 키트 `user/`), 기존 plan·dry-run 테스트, capture 테스트 | 30 | PASS | 예(신규) |
| V-09 | `--offline` 네트워크 미사용 | **`test_v09_new_path_runs_with_the_network_blocked`**(socket·npx/uv/pip 차단 fixture에서 plan/install/verify/update/uninstall), 골든 in-process(차단 fixture), `tests/cli/test_network.py` | 49 | PASS | 예(신규: 새 경로) |
| V-10 | 허용되지 않은 MCP 자동 실행 없음 | `test_mcp_outside_allowlist_is_rejected`, `tests/catalog/test_mcp_catalog.py`(기본 비활성·opt-in), `tests/test_audit.py`, `test_v05_a_user_server_outside_the_allowlist_blocks_but_stays_as_written` | 78 | PASS | 예 |
| V-11 | 설치 실패 시 보존·복구 | `test_both_rolls_back_when_a_write_fails`(쓰기 예외 주입), `test_restore_*`, `tests/test_failure_recovery.py` | 7 | PASS | 예 |
| V-12 | 요구사항-테스트 연결 | `tests/hitl/test_trace.py`(TC-HTL-09~12) | 42 | PASS | 예 |
| V-13 | 반례 생성·검토 흐름 | `tests/hitl/test_counterexamples.py`(TC-HTL-14) | 48 | PASS | 예 |
| V-14 | 미승인 Task 자동 진행 없음 | `test_start_waits_for_an_approved_dependency`(TC-HTL-03), `test_only_one_task_in_progress` | 2 | PASS | 예 |
| V-15 | 세션 재시작 후 상태 복원 | `tests/hitl/test_recover.py`(TC-HTL-16~18) | 55 | PASS | 예 |
| V-16 | Windows·Linux 경로 | **`test_v16_*` 3개**(공백·한글 경로, CRLF 원본 바이트 보존, `kit/`·`shared/`·`run_kit.py`의 텍스트 입출력에 `encoding=`이 있는지 AST 검사와 그 검사기의 자체 검사), 한글·공백 git 하위 폴더 | 4 | PASS (Windows) | 예(신규). Linux는 P6-T4 |
| V-17 | 비밀값 비노출 | **`test_v17_*` 6개**(env·config에 심은 토큰, `--verbose`·`--json`·`--report-json`·로그·`.kit/work` 파일, 사용자가 입력한 값이 그대로 출력되는 HITL 명령), `test_new_path_masks_stdout_log_and_json`, `tests/test_security.py` | 16 | PASS | 예(신규) |
| V-18 | 전역 설정 무변경 | **`test_v18_*` 3개**(project 범위 install --hooks/verify/update/doctor/task/req/trace/recover/uninstall 동안 임시 HOME 트리 해시가 같음), 기존 2개 | 5 | PASS | 예(신규) |

## 이번에 찾아 고친 결함

| 결함 | 영향 | 조치 |
|---|---|---|
| `kit task`·`req`/`trace`·`ce`·`report`의 `--json` 출력이 마스킹을 거치지 않았다(텍스트 출력만 마스킹) | Task 제목·요구사항 문장·반례 가정에 사용자가 넣은 토큰이 JSON으로 그대로 나왔다(V-17 위반). 실제 재현: `task list --json`에 `ghp_…` | `kit/logs.py`에 `mask_tree`(문자열 값마다 마스킹)를 두고 네 CLI의 JSON 출력에 적용 |
| 설치 JSON 보고서(`--json`, `--report-json`)와 `capture --json`이 JSON 문자열 전체를 마스킹했다 | 값에 `token=…`이 있으면 `NAME=\S+` 규칙이 닫는 따옴표까지 지워 JSON이 깨질 수 있다(P5-T7 `recover`에서 같은 원인을 실제로 확인) | 같은 `mask_tree`로 바꿈. 깨지는 것을 보여 주는 테스트 포함 |

## 기록해 둘 동작 (바꾸지 않음)

- 보안 감사는 쓰기 **뒤에** 결과 설정을 검사한다(기준선의 `test_remote_server_blocks_the_run`과 같음). 작업 공간에 허용 목록 밖 MCP 서버가 이미 있으면 종료 코드 2(BLOCKED)와 이유가 나오지만 키트 파일은 이미 써져 있다. 사용자의 서버는 지우거나 고치지 않는다. 키트가 그 서버를 실행하거나 켜지는 않으므로 V-10 위반은 아니다. 기존 경로와의 호환(V-01) 때문에 그대로 둔다.
- 허용 목록(`mcp/allowlist.json`)의 서버는 `sequential-thinking` 하나뿐이라, 사용자 MCP 서버가 있는 작업 공간에서는 설치가 항상 BLOCKED다.

- **개정 (2026-11-08, B-3):** 위 첫 줄의 순서는 새 경로에서 바뀌었다. `install`·`update`·`plan`·`--dry-run`은 쓰기 전에, 디스크의 설정에 계획한 내용을 겹친 결과를 감사한다. 허용 목록 밖 서버가 있으면 BLOCKED(2)로 끝나고 아무것도 쓰지 않는다(키트 파일, 백업, 상태, 로그 없음). V-05 테스트(`test_v05_a_user_server_outside_the_allowlist_blocks_but_stays_as_written`)는 이제 `CLAUDE.md`가 바이트 단위로 그대로인지 본다. 기존 경로는 그대로 쓰기 뒤에 감사한다. 테스트: `tests/cli/test_audit_before_write.py`.

## 변이 점검

- 마스킹을 끈 변이(`kit/logs.py`의 규칙 목록을 비움): 처음 만든 V-17은 **통과했다**. 키트가 env·설정 값을 애초에 출력하지 않아 마스킹 경로를 거치지 않았기 때문이다. 사용자 입력이 그대로 출력되는 경로를 더한 뒤에는 V-17 테스트 6개가 실패한다(변이 잡힘). 이 과정에서 위 첫 번째 결함이 드러났다.
- V-16 AST 검사기는 자체 테스트로 `open()`·`read_text()`·`write_text()`·`subprocess.run(text=True)`의 누락을 잡고 `rb` 모드와 `tarfile.open`은 넘기는 것을 확인한다.

## 실행하지 못한 것

| 항목 | 상태 | 이유 |
|---|---|---|
| V-16 Linux | P6-T4에서 실행 | WSL2 Ubuntu 26.04에서 전체 테스트 실행(`P6-T4-platform.md`) |
| 심볼릭 링크 테스트 2개 | SKIPPED | 이 PC에서 링크를 만들 수 없음 |
