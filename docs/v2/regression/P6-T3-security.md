# P6-T3 보안 검증

- 실행 일시: 2026-11-07, Windows 11 Pro, Python 3.12.10
- 전체 실행: `uv run --offline pytest -q -p no:cacheprovider --junitxml=docs/v2/regression/raw/p6t3-junit.xml` → **1415 passed, 2 skipped (P6-T2 이후 +40)**
- 새 테스트: `tests/test_p6_security.py` 40개(아래 표의 굵은 이름)

## 검증 항목 (00_PROMPT §11 P6-T3)

| 항목 | 근거 테스트 | 결과 |
|---|---|---|
| `..` 경로 거부 | `test_safe_path_rejects_parent_traversal`, `test_report_outside_the_workspace_is_refused`(task submit `--report`), `test_sync_refuses_a_brief_it_cannot_use`(req sync `--brief`), report tests `--out`(`tests/hitl/test_report_tests.py`), source add `--path ../x`·아카이브 `top/../../evil`·lock `../outside`(`tests/sources/test_source_add.py`, `test_bad_file_path_in_lock`) | PASS |
| 절대 경로 거부 | `test_safe_path_rejects_absolute_outside`, 위 HITL 입력 테스트(작업 공간 밖 절대 경로), `_escapes`(`/`, `\`, `C:` 형태) | PASS |
| 링크를 통한 대상 밖 쓰기 거부 | **`test_safe_path_refuses_a_directory_link_that_leads_outside`**, **`test_a_link_inside_the_target_never_leads_a_write_outside` 10개**(`.kit`, `.kit/state`, `.kit/work`, `.agents`, `.claude`, `.codex`와 install codex/claude/both, `--hooks`, `--mcp`, task, recover, 기존 설치기), **`test_the_manifest_link_is_refused_before_anything_is_written`**, **`test_source_add_writes_cannot_follow_a_link_out_of_the_kit`**, **`test_capture_writes_cannot_follow_a_link_out_of_the_kit`**, 원격 저장소의 링크(`test_links_are_never_followed_and_block_inside_the_skill`, `test_sparse_fetch_blocks_a_link_inside_the_skill`) | PASS (결함 1 수정 후) |
| 링크를 만들지 않음, 복사로 배치 | **`test_kit_code_never_creates_a_link`**(`kit/`, `run_kit.py` AST 검사: `os.symlink`, `symlink_to`, `hardlink_to`, `os.link`, `CreateJunction`, `copytree(symlinks=True)`, `mklink`), **`test_the_link_checker_finds_every_form`**(검사기 자체 검사), **`test_installed_skills_are_copies_not_links` 3개**(both+hooks, 넓은 프로필, 기존 설치기: 설치된 경로 중 링크·정션 0) | PASS |
| 감사 규칙이 TOML·JSON 모두에 적용 | **`test_each_audit_rule_fails_in_toml_line_scan_and_json` 10개**(허용 목록 밖 이름, `url`, `bearer_token_env_var`, 허용되지 않은 명령, 명령 경로, 인수의 원격 주소, 비밀형 env 값, 비밀형 `env_vars` 이름, 선언한 이름에 값, 선언한 이름 옆의 미선언 이름 — 각각 전체 TOML 감사, 줄 단위 검사, `.mcp.json` 세 곳에서 FAIL), **`test_an_inline_server_table_is_audited_by_the_line_scan`**, **`test_json_only_remote_forms_fail` 3개**(`type: http`, `type: sse`, `headers`), **`test_allowed_servers_pass_everywhere` 3개**, **`test_every_installable_catalog_server_passes_its_own_audit` 2개**(tomllib, 줄 단위), 기존 `tests/test_audit.py` | PASS (결함 2·3·4 수정 후) |
| 외부 리소스 해시 = `sources.lock.json` | **`test_every_external_file_matches_the_lock_recomputed_independently`**(`kit.sources`를 쓰지 않고 hashlib으로 170개 파일과 `content_sha256` 12개를 다시 계산, `third_party/`의 모든 파일이 lock에 있음), **`test_a_changed_byte_is_found_by_the_lock_check`**(1비트 변경), 기존 `test_real_lock_matches_the_files`, `test_tampered_vendored_file_blocks_install_before_writing`, `test_tampered_included_license_blocks_install` | PASS |

링크는 Windows에서 디렉터리 정션(`_winapi.CreateJunction`, 관리자 권한 불필요)으로 만들었다. 이 PC는 심볼릭 링크를 만들 수 없어서 기존 심볼릭 링크 테스트 2개는 건너뛰지만, 정션도 `Path.resolve()`가 따라가는 재분석 지점이라 같은 경로를 검사한다. Linux에서는 같은 테스트가 `os.symlink`를 쓴다(NOT RUN, P6-T4).

## 찾아 고친 결함

| # | 결함 | 재현 | 조치 |
|---|---|---|---|
| 1 | 설치 매니페스트(`.kit/state/install-manifest.json`)를 `safe_path` 없이 썼다 | `.kit/state`를 작업 공간 밖을 가리키는 정션으로 두고 `install --agent codex` → READY, **작업 공간 밖에 `install-manifest.json`이 생김** | `commands._manifest_path`가 `safe_path`를 거친다. 매니페스트는 설치 명령에서 가장 먼저 읽으므로 아무것도 쓰기 전에 BLOCKED(2)로 멈춘다 |
| 2 | 줄 단위 검사(Python 3.9/3.10)가 명령 규칙을 보지 않았다 | `[mcp_servers.sequential-thinking] command = "bash"` → 전체 감사는 FAIL, 줄 단위 검사는 위반 없음(UNVERIFIED, 설치는 READY) | `command = "…"`를 허용 명령과 비교 |
| 3 | 줄 단위 검사가 `[mcp_servers]` 아래 인라인 서버를 보지 않았다 | `evil = { command = "npx" }` → 전체 감사 FAIL, 줄 단위 검사 위반 없음 | 인라인 서버 이름을 허용 목록과 비교 |
| 4 | 줄 단위 검사가 P4-T9 `declared_env` 예외를 몰랐다 | Python 3.9/3.10에서 `install --agent codex --mcp context7` → 키트가 쓴 `env_vars = ["CONTEXT7_API_KEY"]`를 비밀값으로 보고 BLOCKED | 전체 감사와 같은 예외(그 서버가 선언한 이름이 `env_vars` 줄이나 `NAME = "${NAME}"` 줄에 참조로만 있을 때) |

방어 보강(결함은 아님): `capture`(키트 `user/`에 씀)와 `source add`(키트 `third_party/` 등에 씀)의 쓰기도 `safe_path`를 거친다. `source add`의 경로 이름은 원격 저장소에서 오지만 이미 `_escapes`와 링크 거부로 막고 있었다. 이번 변경은 키트 폴더 안에 사람이 만든 링크가 있는 경우까지 막는다.

## 기록해 둘 동작 (바꾸지 않음)

- 작업 공간 밖 링크 때문에 거부되면 출력이 `error: unexpected PathEscapeError: refusing path outside target: <경로>`이고 종료 코드는 2(BLOCKED)다. 거부와 종료 코드는 맞지만 "unexpected"라는 말은 정확하지 않다. 문구 정리는 P7 문서화 때 함께 검토한다.
- `install`이 쓰는 파일(스킬·정책·MCP·훅)은 링크를 만나면 그 항목만 CONFLICT로 남고 나머지는 계속된다(종료 코드 1 또는 2). 키트 상태 파일(`.kit/…`)이 링크로 막히면 명령 전체가 BLOCKED다.
- `--report-json FILE`은 사용자가 고른 출력 파일이라 작업 공간 밖에도 쓴다(05_CLI_SPEC 공통 옵션 표). 이 옵션은 사용자가 경로를 직접 주므로 경로 탈출이 아니다.
- user 범위에는 감사가 없다(04_DESIGN user 범위 절, ADR-018: 홈 설정은 사용자 것). 키트가 홈에 쓰는 MCP 항목은 카탈로그에서만 온다.
- 줄 단위 검사는 주석 줄에 있는 URL·비밀형 이름도 FAIL로 본다(전체 감사는 무시). Python 3.9/3.10에서만 쓰는 보수적 경로라 그대로 둔다.
- P6-T2에 적은 "감사는 쓰기 뒤" 동작은 그대로다.
- **개정 (2026-11-08, B-3):** 새 경로에서는 위 줄이 더 이상 맞지 않는다. `install`·`update`는 쓰기 전에 계획한 결과(디스크 + 계획)를 감사하고, FAIL이면 아무것도 쓰지 않고 BLOCKED(2)로 끝난다. 쓰기 뒤 감사도 남아 있다. 감사 규칙 자체(이 문서의 표와 줄 단위 검사)는 바뀌지 않았다. 기존 경로는 그대로 쓰기 뒤에 감사한다.

## 변이 점검

`tests/test_p6_security.py`만 돌려 확인했다.

| 변이 | 결과 |
|---|---|
| M1 매니페스트 경로에서 `safe_path` 제거 | 잡힘 |
| M2 capture 쓰기에서 `safe_path` 제거 | 잡힘 |
| M3 source add `write`에서만 `safe_path` 제거 | **살아남음**: `_save`가 같은 경로를 먼저 검사해 동작이 같다(중복 방어). M3b(`_save`·`write`·`delete` 세 곳 모두 제거)는 잡힘 |
| M4 줄 단위 검사의 명령 규칙 제거 | 잡힘 |
| M5 줄 단위 검사의 인라인 서버 제거 | 잡힘 |
| M6 줄 단위 검사에서 선언 이름 예외를 없앰 | 잡힘 |
| M7 선언 이름이면 값이 있어도 통과 | 잡힘 |
| M8 `.mcp.json` 원격 transport 검사 제거 | 잡힘 |
| M9 lock 해시 비교 제거 | 잡힘 |
| M10 `safe_path`가 `resolve()` 대신 `normpath`(링크를 따라가지 않음) | 잡힘 |
| M11 전체 TOML 감사의 명령 규칙 제거 | 잡힘 |

## 실행하지 못한 것

| 항목 | 상태 | 이유 |
|---|---|---|
| Linux에서 심볼릭 링크로 같은 테스트 | NOT RUN | Linux 환경 없음(P6-T4) |
| 실제 Python 3.9/3.10에서 줄 단위 검사 | NOT RUN | 이 PC에 없음. `parse_toml`을 tomllib 없음으로 바꿔 같은 경로를 실행했다(P6-T4) |
| 심볼릭 링크 테스트 2개(`test_safe_path_rejects_symlink_escape`, `test_a_linked_listed_file_is_a_note`) | SKIPPED | 이 PC에서 심볼릭 링크를 만들 수 없음. 같은 경로를 정션으로 검사했다 |
