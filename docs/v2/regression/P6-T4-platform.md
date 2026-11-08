# P6-T4 플랫폼 검증

실행 일시: 2026-11-07. 원본 출력은 `raw/p6t4-*`에 있다.

## 결과 요약

| 환경 | 방법 | 결과 |
|---|---|---|
| Windows 11 Pro 10.0.26200, Python 3.12.10 | `uv run --offline pytest` 전체 | **1428 passed, 2 skipped** (`raw/p6t4-windows-*`) |
| Linux: WSL2 Ubuntu 26.04 LTS(커널 6.18), Python 3.11.16, `LANG=C.UTF-8` | 작업 트리를 WSL로 복사해 `.gitattributes`대로 LF로 다시 체크아웃(Linux clone과 같은 바이트), pytest만 설치(`--offline`, 키트는 표준 라이브러리만 씀) | **1407 passed, 23 skipped** (`raw/p6t4-*-linux.*`) |
| Linux, Python 3.9.25(uv가 받은 CPython, 검토자 승인 2026-11-07, WSL 안에서만) + pytest 8.4.2 | 같은 사본 | **1397 passed, 33 skipped** (`raw/p6t4-*-linux-39.*`) |
| Linux, 시스템 Python 3.14.4 | 같은 사본(아래 결함 2~3 수정 뒤, 결함 4와 3.9 테스트 보정 전 트리) | 1397 passed, 23 skipped |
| Linux CLI | `LANG=C LC_ALL=C`, 공백·한글 경로(`작업 폴더`), 임시 HOME에서 `plan`·`install`·`verify`·`task add`(한글 제목)·`task list`·`uninstall`·`bootstrap.sh --offline`(3.14), `install`·`verify`·`install --mcp context7`·`uninstall`(3.9, `python -I`) | 모두 0(READY/DONE), HOME에 파일 0개 |
| Windows PowerShell 5.1(5.1.26100.9711), 한국어 로캘 cp949 | 새 `powershell.exe -NoProfile`에서 콘솔을 cp949로 두고 `PYTHONUTF8`·`PYTHONIOENCODING` 없이 실행 | 모두 0. 결과는 `docs/v2/WINDOWS_MANUAL_CHECK.md`의 "에이전트 실행" 열 |
| PowerShell 7 | 이 PC에 `pwsh`가 없음 | **NOT RUN** → `WINDOWS_MANUAL_CHECK.md` 검토자 칸 |

건너뛴 테스트:
- Linux: 23개 모두 `tests/test_entrypoints.py`의 PowerShell 진입점 테스트(PowerShell 없음). Windows에서 건너뛰던 심볼릭 링크 테스트 2개는 Linux에서 **실행되어 통과**했다.
- Python 3.9: 위 23개, 그리고 tomllib(3.11+)가 필요한 10개(`tests/test_audit.py` 5, `tests/test_mcpconfig.py` 2, `tests/test_mcp_registration.py` 1, `tests/test_p6_platform.py` 2).
- Windows: 심볼릭 링크 2개(이 PC에서 만들 수 없음).

## 찾아 고친 결함

| # | 결함 | 찾은 곳 | 조치 |
|---|---|---|---|
| 1 | 같은 `sorted(paths)`가 플랫폼마다 다른 순서를 냈다. `WindowsPath`는 대소문자를 무시하고, `PosixPath`는 구분한다. 그래서 스킬 파일의 계획·출력·설치 순서가 달랐다(`SKILL.md`가 Windows에서는 `examples/` 뒤, Linux에서는 앞) | Linux 골든 `*__dry-run` 실패 | `fsops.path_order` 키(Windows 순서: 경로 조각 소문자, 그다음 원래 조각)를 `plan`·`catalog`·`capture`·`commands restore`·`sources`·`userscope`·`source_add`의 경로 정렬 12곳에 씀. Windows 순서와 골든은 그대로 |
| 2 | 골든 픽스처가 `write_text("…\n")`로 써서 Windows에서는 CRLF, Linux에서는 LF가 됐다. 기준선(Windows 기록) 해시가 Linux에서 맞지 않았다 | Linux 골든 `core__existing-agents-md`, `core__conflict-edited-block` | 테스트 수정: 픽스처가 기록 당시 바이트(CRLF)를 직접 씀 |
| 3 | 골든 in-process 테스트가 PC에 numpy·pandas가 있는지에 따라 결과가 달랐다(PRESENT/ADVICE) | Linux 골든 `data__dry-run`, `full__dry-run` | 테스트 수정: 그 테스트에서만 탐지 결과를 기록 당시 값으로 고정 |
| 4 | Python 3.9/3.10(tomllib 없음)에서 user 범위 설치가, 홈 `config.toml`에 **같은 값**으로 이미 있는 캡처 표(`[features] goals = true`)를 "다르게 설정됨"(CONFLICT)으로 보고 PARTIAL로 끝났다 | 실제 Python 3.9.25, `test_captured_table_set_the_same_way_is_left_out` | `adapters.user._same_table`: tomllib가 있으면 값으로 비교(기존과 같음). 없으면 빈 줄·주석을 뺀 줄이 같을 때 같다고 보고, 다르면 CONFLICT로 두되 이유를 "값 비교에는 Python 3.11+ (tomllib)가 필요"로 정확히 적는다. 같은 표를 하나 더 쓰면 잘못된 TOML이 되므로 CONFLICT 자체는 안전한 쪽이다 |
| 5 | 테스트 10개가 tomllib(3.11+)가 있다고 가정하고 PASS를 기대했다. 3.9/3.10에서는 TOML 감사·점검이 설계대로 UNVERIFIED다 | 실제 Python 3.9.25 | 테스트 수정: `tests/conftest.py`의 `HAS_TOMLLIB`·`TOML_PASS`를 쓰게 함. 골든 stdout 비교는 3.9/3.10에서 감사·`Status:`·`Items:` 줄만 빼고 나머지를 그대로 비교 |

## Python 3.9 근거

- 실제 실행: CPython 3.9.25(Linux)에서 전체 테스트 1397개 통과. `python -I run_kit.py`로 설치·검증·제거 CLI 정상.
- 정적 검사(`ast.parse(feature_version=(3, 9))`와 3.10+ API 이름 검사, `kit/`·`run_kit.py`·`tests/` 124개 파일): 걸린 것은 `SPEC_FIELDS | {...}`(집합 합치기, 오탐) 하나.
- Windows의 Python 3.9는 실행하지 않았다(NOT RUN). 3.9 실행은 Linux에서만 했다.
- 3.9/3.10에서 달라지는 점(설계대로): Codex `config.toml` 감사와 TOML 점검은 UNVERIFIED다(줄 단위 검사는 위반을 찾으면 FAIL). 이 경우 설치는 READY로 끝나지만 `Check security audit by hand` 안내가 나온다.

## cp949 (한국어 Windows) 점검 결과

- 키트 코드의 텍스트 입출력에는 모두 `encoding=`이 있다(P6-T2의 V-16 AST 검사). 그래서 Python의 기본 인코딩이 cp949여도 파일은 UTF-8로 읽고 쓴다.
- 콘솔 출력은 `main()`이 `errors="replace"`로 바꿔 둔다. cp949 콘솔에서 cp949에 없는 문자(—, 이모지)는 `?`로 보이지만 명령은 실패하지 않는다. 작업 파일(`tasks.json`)에는 원래 문자가 남는다.
- PowerShell 5.1은 BOM이 없는 `.ps1`을 cp949로 읽는다. `bootstrap.ps1`은 ASCII만 쓰고, `test_powershell_files_are_ascii_for_windows_powershell_5`가 이를 지킨다.

## 변이 점검

| 변이 | 결과 |
|---|---|
| `_same_table`에서 줄 비교를 뺌 | `test_captured_table_set_the_same_way_without_tomllib`, `test_without_tomllib_only_the_same_lines_count_as_the_same[same]`가 잡음 |
| `path_order`를 빼고 `sorted(paths)`로 되돌림 | Windows에서는 **살아남음**(Windows 순서가 원래 같음). Linux에서는 골든 dry-run 5개가 잡음(수정 전 실제 실패). `test_path_order_is_the_windows_order_on_every_system`은 키 자체를 어느 플랫폼에서나 검사한다 |

## 정리

- WSL에 받은 CPython 3.9.25는 실행 뒤 `uv python uninstall 3.9`로 지웠다. 3.9용 pytest 8.4.2 휠은 WSL의 uv 캐시에 남아 있다(`uv cache clean`으로 지울 수 있음).
- WSL의 작업 사본(`/root/kit-p6t4`)은 지웠다. Windows 쪽 전역 설정, `~/.codex`, `~/.claude`는 건드리지 않았다.
- `raw/`의 JUnit에 나오는 `ghp_BBBB…`는 테스트 매개변수(가짜 토큰, `test_mask_covers_shared_token_patterns`)이고 실제 비밀값이 아니다.

## 실행하지 못한 것

| 항목 | 상태 | 이유 |
|---|---|---|
| PowerShell 7 | NOT RUN | 이 PC에 없음. `WINDOWS_MANUAL_CHECK.md` |
| 설정을 바꾸지 않은 PowerShell 5.1의 리디렉션 인코딩(W-11) | NOT RUN | 에이전트 도구의 PowerShell은 기본값이 바뀌어 있음 |
| Windows에서 Python 3.9 | NOT RUN | 이 PC에 없음(3.9 실행은 Linux에서만) |
| 실제 Linux 기기(WSL 아님) | NOT RUN | WSL2 Ubuntu에서 실행함 |
| shellcheck | NOT RUN | WSL에 설치돼 있지 않음 |
