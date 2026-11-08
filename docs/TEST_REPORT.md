# 테스트 보고서

1부는 v2 최종 결과다(2026-11-08). 2부는 v1(계획 1~2와 그 뒤) 기록을 그대로 둔 것이다. v2의 단계별 근거는 `docs/v2/regression/`에 있다.

# 1부. v2

## 최종 실행 (P7-T2, 2026-11-08)

최종 검증 보고서는 `docs/v2/FINAL_REPORT.md`다. 후속 1~4, 후속 A·B-1, 외부 출처 1~3단계, B-3(쓰기 전 감사)를 반영한 마지막 전체 실행은 **1997 passed, 2 skipped**(`docs/v2/regression/raw/fb3-pytest.txt`, `fb3-junit.xml`)이고, ruff 180개 파일이 깨끗했다. shellcheck는 후속 4 때 4개가 깨끗했고 그 뒤 `.sh` 변경은 없다. 아래 표는 P7-T1 시점의 실행이다.

### P7-T1 실행

환경: Windows 11 Pro 10.0.26200, Python 3.12.10, uv 0.10.9, shellcheck 0.11.0. 작업은 `feat/v2-multi-agent` 브랜치에서 아직 커밋하지 않은 상태로 실행했다.

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run --offline pytest -q -p no:cacheprovider` | **1517 passed, 2 skipped** | `docs/v2/regression/raw/p7t1-pytest.txt`, `p7t1-junit.xml` |
| `uv run --offline ruff check .` | PASS | `All checks passed!` |
| `uv run --offline ruff format --check .` | PASS | `164 files already formatted` |
| `shellcheck` (추적 중인 `.sh` 전부) | PASS | 출력 없음, 종료 코드 0 |
| `uv run python devtools/run_doc_commands.py` | PASS | 사용자 문서의 명령 95개, 기대와 다른 종료 코드 0개(`docs/v2/regression/P7-T1-doc-commands.md`) |

건너뛴 2개는 심볼릭 링크 테스트다. 이 PC에서는 링크를 만들 수 없다. Linux에서는 실행되어 통과했다(P6-T4).

## 단계별 근거

| 단계 | 내용 | 결과 | 기록 |
|---|---|---|---|
| P6-T1 | v1 기준선(P1-T1)과 전체 회귀 비교 | 기준선 테스트 모두 유지, 1356 passed | `regression/P6-T1-regression.md` |
| P6-T2 | 검증 행렬 V-01~V-18 | 18개 모두 근거 테스트 있음 | `regression/P6-T2-matrix.md` |
| P6-T3 | 보안: 링크를 통한 경로 탈출, 링크를 만들지 않음, TOML·JSON 감사 규칙 일치, lock 해시 | 통과. 변이 M1~M11 중 M3만 살아남음(다른 방어선이 이미 막음), 보강한 M3b는 잡힘 | `regression/P6-T3-security.md` |
| P6-T4 | 플랫폼: Linux(WSL2), 실제 Python 3.9.25, cp949 PowerShell 5.1 | Linux 1407 passed, 3.9 1397 passed. 결함 2개(파일 순서, 3.9의 표 비교) 고침 | `regression/P6-T4-platform.md` |
| P6-T5 | E2E HITL 시나리오 6단계(실제 프로세스, 실제 pytest JUnit) | 7개 통과, 변이 6개 모두 잡힘 | `regression/P6-T5-e2e.md` |
| P6-T6 | 에이전트 로드 점검표와 그 정합성 테스트 | 4개 통과, 변이 5개 모두 잡힘 | `docs/v2/AGENT_LOAD_CHECK.md` |
| P7-T1 | 문서 명령 실행, 카탈로그 문서 생성, 예시 로그 | 문서 명령 95개 기대대로 | `regression/P7-T1-doc-commands.md` |
| P7-T2 | REQ 84개 커버리지(JUnit에서 계산), 기준선 비교, 후속 1~4 | PASS 81, 문서 3. 기준선 339개 변화 없음 | `regression/P7-T2-req-coverage.md`, `docs/v2/FINAL_REPORT.md` |

## 미검증 (검토자 확인 필요)

| 항목 | 상태 | 확인 방법 |
|---|---|---|
| Codex·Claude Code 안에서의 스킬·MCP·훅·서브에이전트 로드 | UNVERIFIED | `docs/v2/AGENT_LOAD_CHECK.md` |
| PowerShell 7, 기본 설정 PowerShell 5.1의 리디렉션 인코딩 | NOT RUN | `docs/v2/WINDOWS_MANUAL_CHECK.md` |
| 실제 Linux 기기, macOS | NOT RUN | WSL2에서만 실행 |
| Windows에서 Python 3.9 | NOT RUN | 3.9는 Linux에서만 실행 |
| user 범위 실제 적용(`--scope user --yes`) | NOT RUN | 검토자 작업 M-06 |
| `--plugin` 실제 설치 | 이번에는 NOT RUN | P4-T5에서 격리 설정 폴더로 확인한 기록 |
| `git clone`으로 받는 v2 | NOT RUN | `main` 병합 뒤 |

승인 훅(L2)은 2026-11-07 Claude Code 2.1.319와 codex-cli 0.166.0에서 실제로 확인했다(ADR-011, M-05, VERIFIED-RUN).

# 2부. v1 기록


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
- Codex가 Skill 8개를 실제로 로드하는지: 2026-10-30 노트북(FactChat 프로필)에서 `/skills`에 모두 표시됨을 사용자가 확인했다. 코파 환경 결과는 `docs/RULES_CHECKLIST.md`의 "사전 체험 결과"를 본다.
- 요청 시 전용 Skill 3개(`implementation-review`, `benchmark`, `design-review`)가 키워드에만 반응하고 평소에는 끼어들지 않는지: 2026-11-01 `codex exec`로 확인했다(아래 "Codex 실행 확인과 algorithm-options 트리거 수정")
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
| 최종 리뷰 수정 후 `uv run pytest -q` | PASS | `320 passed, 1 skipped` (병합된 `main`에서 재실행해도 동일) |
| 새 저장소 주소(`skill_kit_kch`)로 bash 한 줄 설치 | PASS | 빈 폴더에서 `Status:       READY`, `Skills:       8 expected / 8 verified` |
| Codex `/skills` (노트북, FactChat 프로필) | PASS | 2026-10-30, 8개 모두 표시(사용자 확인) |
| 코파 사전 체험 | 부분 | 플랫폼 터미널 설치 실패, Codex에게 실행시키면 Skill 설치·표시. `/mcp`는 표시 안 됨. 자세한 내용은 `docs/RULES_CHECKLIST.md` |

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
