# 테스트 보고서

## 계획 1

실행일: 2026-10-28, 환경: Windows 11 AMD64, Python 3.12.10, codex-cli 0.165.0, shellcheck 0.11.0

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `158 passed, 1 skipped in 25.22s` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `50 files already formatted` |
| `shellcheck bootstrap.sh` | PASS | 출력 없음, 종료 코드 0 |
| PSScriptAnalyzer | 미실행 | `PSScriptAnalyzer not installed - not run` |
| one-liner (PowerShell, clean clone) | PASS | `git clone --depth 1 --branch feat/bootstrap-kit file:///D:/aaa/aaa kit` 후 `bootstrap.ps1 --target .` 첫 실행과 재실행 모두 `Status:       READY`, `exit=0` |
| one-liner (Git Bash) | PASS | `C:\Program Files\Git\bin\bash.exe`로 `bash kit/bootstrap.sh --target .` 실행, 기존 설치 상태와 빈 디렉터리 두 대상 모두 `Status:       READY`, exit 0 |
| Codex 스킬·AGENTS.md 로드 | PASS | 2026-10-29, codex-cli 0.165.0 + FactChat 프로필. `codex debug prompt-input`에 키트 정책과 암묵 스킬 4개가 들어감(명시 전용 2개는 설계대로 목록에 없음). TUI에서 `$task-router`로 요청 → 작업 공간에 `TASK_BRIEF.md` 생성 확인 |

## 건너뛴 테스트와 이유
- `tests/test_fsops.py:31` 심볼릭 링크 탈출 테스트: `symlinks not permitted on this system` (Windows에서 심볼릭 링크 권한 없음)

## 미검증
- 시험 환경(Cofa) 전체: docs/ASSUMPTIONS.md 참고
- 요청 시 전용 Skill 3개(`implementation-review`, `benchmark`, `design-review`)가 키워드나 `$이름`에만 반응하고 평소에는 끼어들지 않는지: 사용자의 대화형 확인 필요
- PSScriptAnalyzer가 설치되지 않아 `bootstrap.ps1` 정적 분석은 실행하지 못했다

# 계획 2 (프로필, MCP, 감사)

실행일: 2026-10-28, 환경: Windows 11 AMD64, Python 3.12.10

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `300 passed, 1 skipped in 36.21s` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `49 files already formatted` |
| `uv run python devtools/make_examples.py` | PASS | `docs/examples/{install,rerun,failure,offline,conflict}.log` 5개 생성. 네트워크 미사용, 로컬 경로는 `<target>`으로 치환 |
| 실제 npx로 sequential-thinking 핸드셰이크 | UNVERIFIED | `bootstrap.ps1 --profile python --target <빈 폴더>`로 사용자가 확인 |
| Codex `/mcp`에 sequential-thinking 표시 | PASS | 2026-10-29, codex-cli 0.165.0 + FactChat 프로필. 키트를 `--profile python --offline`으로 설치한 작업 공간을 Codex에서 신뢰한 뒤 `/mcp`에 표시됨(사용자 확인). Codex가 직접 `npx`로 서버를 띄움 |

## 예시 로그 판정

| 로그 | 기대 | 결과 |
|---|---|---|
| `install.log` | READY, 종료 코드 0 | 일치 |
| `rerun.log` | READY, CREATE 없음 | 일치 |
| `failure.log` | BLOCKED, 종료 코드 2 | 일치 |
| `offline.log` | `Network:      not used (--offline)`, MCP `SKIPPED` | 일치 |
| `conflict.log` | `skill:benchmark` CONFLICT, PARTIAL, 종료 코드 1 | 일치 |

## 미검증 (계획 2)

- 실제 `npx`로 한 MCP 핸드셰이크(위 표). 테스트는 로컬 가짜 서버만 쓴다.
- Codex에서의 MCP 표시: 신뢰하지 않은 작업 공간에서는 `codex mcp list`에 `sequential-thinking`이 나타나지 않는다(Codex가 신뢰된 프로젝트의 `.codex/config.toml`만 읽음). `-c projects.'<경로>'.trust_level="trusted"` 같은 일회성 설정으로는 신뢰가 바뀌지 않았다. 스킬과 AGENTS.md는 신뢰와 무관하게 읽혔다.
- 기존 건너뜀 1건은 Windows 심볼릭 링크 권한 때문이다(계획 1과 동일).

# 추가 Skill 2개 (systematic-debugging, codebase-explorer)

실행일: 2026-10-30, 환경: Windows 11 AMD64, Python 3.12.10

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `312 passed, 1 skipped in 37.05s` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `50 files already formatted` |
| `uv run python devtools/make_examples.py` | PASS | `docs/examples/*.log` 5개 재생성. 변경은 `Skills: N expected / M verified` 줄(`install`·`rerun`·`failure`·`offline`은 8/8, `conflict.log`는 8/7)과 `rerun.log`에 추가된 PASS 두 줄(`optional skill:systematic-debugging`, `optional skill:codebase-explorer`)뿐 |
| `run_kit.py --profile core` 빈 폴더 설치 | PASS | `Status:       READY`, `exit=0`, `Skills:       8 expected / 8 verified`, `.agents/skills`에 8개 폴더, `THIRD_PARTY_NOTICES.md`는 대상에 없음 |

# 추가 Skill 3개 (counterexample-hunter, algorithm-options, design-review)와 요청 시 호출

실행일: 2026-10-31, 환경: Windows 11 AMD64, Python 3.12.10

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `337 passed, 1 skipped` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `50 files already formatted` |
| `uv run python devtools/make_examples.py` | PASS | `docs/examples/*.log` 5개 재생성. 변경은 `Skills: N expected / M verified` 줄과 `rerun.log`에 추가된 PASS 세 줄(`optional skill:counterexample-hunter`, `optional skill:algorithm-options`, `optional skill:design-review`)뿐 |
| `run_kit.py --profile core` 빈 폴더 설치 | PASS | `Status:       READY`, `exit=0`, `Skills:       11 expected / 11 verified`, `.agents/skills`에 11개 폴더 |
| `codex debug prompt-input` (codex-cli 0.166.0, 설치한 빈 폴더) | PASS | `<skills_instructions>` 목록에 키트 Skill 11개가 모두 들어감. 명시 전용이던 `implementation-review`, `benchmark`도 이제 목록에 있음 |

description 합계 상한을 2000자에서 3000자로 올렸다(`test_total_description_budget`). 현재 합계는 2791자다.

# Codex 실행 확인과 algorithm-options 트리거 수정

실행일: 2026-11-01, 환경: Windows 11 AMD64, codex-cli 0.166.0 (FactChat 프로필), `codex exec --json`. 경우마다 키트를 새로 설치한 작업 공간에서 실행하고, 실행 기록에서 읽은 `SKILL.md`로 Skill 사용을 판정했다. 이 PC의 사용자 전역 Skill(superpowers)과 전역 지침도 함께 로드됐다.

| 요청 | 기대 | 읽은 키트 Skill | 결과 |
|---|---|---|---|
| "main.py 설계 리뷰 해줘" | `design-review` | `design-review` | PASS |
| "응집도랑 결합도 좀 봐줘" | `design-review` | `design-review` | PASS |
| 평범한 수정 작업(대조군) | 요청 시 전용 Skill 없음 | `codebase-explorer`, `submission-validator` | PASS |
| "main.py 벤치마크 해줘" | `benchmark` | `benchmark` | PASS |
| "main.py 풀이 설명해줘" | `implementation-review` | `implementation-review` | PASS |
| 버그가 숨은 풀이 "더 검증해줘" | `counterexample-hunter` | `counterexample-hunter` 외 | PASS (반례 `[-1]` 발견, 회귀 테스트 추가) |
| 제한이 주어진 알고리즘 문제(수정 전) | `algorithm-options` | `algorithm-optimizer` 외 | FAIL |
| 같은 문제(수정 후, 2회) | `algorithm-options` | `algorithm-options` 외 | PASS (2회 모두 후보 3개 비교 후 선택 기록) |

수정: `algorithm-optimizer`는 "이미 동작하는 풀이가 느리거나 제한을 넘을 때"로 좁히고, `algorithm-options`는 "입력 크기나 시간 제한이 주어진 알고리즘 문제에서 핵심 로직 전"으로 넓혔다. task-router 표도 맞췄다. `uv run pytest -q`: `338 passed, 1 skipped`, `ruff check`·`ruff format --check` 통과.

미검증: `codex exec`는 사용자 답을 받을 수 없어 `algorithm-options`가 선택을 기다리는 동작은 확인하지 못했다. 이후 사용자가 대화형 Codex에서 동작을 확인했다(2026-11-01).
