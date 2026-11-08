# P6-T1 전체 회귀 (P1-T1 기준선과 비교)

- 실행 일시: 2026-11-07 (로컬)
- 브랜치 / HEAD: `feat/v2-multi-agent` / `67921d46c5813e13d6eea6d7f8c25876577beaec`. P5-T2b~P5-T7 변경은 커밋하지 않은 채로 실행했다.
- 환경: Windows 11 Pro 10.0.26200, Python 3.12.10, uv 0.10.9, shellcheck 0.11.0 (기준선과 같음)
- 원문 출력: `docs/v2/regression/raw/` (`uv-sync.txt`, `pytest.txt`, `pytest-junit.xml`, `ruff_check.txt`, `ruff_format_check.txt`, `shellcheck.txt`)

## 실행 명령과 결과

| 명령 | 결과 | 종료 코드 |
|---|---|---|
| `uv sync --offline` | `Resolved 14 packages` / `Audited 7 packages` | 0 |
| `uv run --offline pytest -q -rs -p no:cacheprovider --junitxml=…` | `1356 passed, 2 skipped in 249.00s` | 0 |
| `uv run --offline ruff check .` | `All checks passed!` | 0 |
| `uv run --offline ruff format --check .` | `155 files already formatted` | 0 |
| `shellcheck` (저장소의 `.sh` 4개) | 출력 없음 | 모두 0 |

## 기준선과 비교 (JUnit testcase 단위)

| 항목 | 기준선 P1-T1 | 지금 |
|---|---|---|
| 테스트 수 | 339 | 1358 (신규 1019) |
| passed / skipped / failed | 338 / 1 / 0 | 1356 / 2 / 0 |
| 기준선 테스트 중 사라진 것 | — | **0** |
| 기준선 테스트 중 결과가 바뀐 것 | — | **0** |
| 새로 실패한 테스트 | — | **0** |

- 비교 방법: 두 JUnit XML의 `classname::name`을 키로 결과(passed/failed/error/skipped)를 맞대었다.
- 폴더별 테스트 수: 루트 341, adapters 23, catalog 235, cli 132, golden 49, hitl 307, profiles 103, sources 81, userscope 54, writers 33.
- 골든 테스트(`tests/golden/`, 기존 Codex 경로의 렌더링 결과) 49개가 모두 통과했다.

### 건너뛴 테스트

| 테스트 | 이유(원문) | 기준선 |
|---|---|---|
| `tests/test_fsops.py:31` | `symlinks not permitted on this system` | 같음 |
| `tests/userscope/test_own_files.py:90` | `this system cannot create symlinks` | 신규(P4-T7). 같은 이유 |

## 바꾼 것: ruff 대상에서 `third_party/` 제외

- 첫 실행에서 `ruff check .`은 5건, `ruff format --check .`은 25개 파일이 걸렸다.
- 걸린 파일은 모두 `third_party/K-Dense-AI-scientific-agent-skills/`였다. 이 폴더는 고정 커밋에서 그대로 복사해 `sources.lock.json`에 내용 해시가 기록된 외부 코드다.
- 외부 코드를 고치면 해시 검사가 깨지고 원본과도 달라진다. 그래서 `pyproject.toml`의 `extend-exclude`에 `third_party`를 더했다(`docs`, `.agents`도 이미 같은 이유로 빠져 있다).
- 키트 코드(`kit/`, `tests/`, `shared/`, 루트 스크립트)는 제외 전에도 깨끗했다.
- 기준선 때는 `third_party/`가 없었다(P4-T8 이후 추가).

## 실행하지 못한 것

| 항목 | 상태 | 이유 | 확인 방법 |
|---|---|---|---|
| Python 3.9 실행 | NOT RUN | 로컬에 없음. 내려받기는 네트워크 동작이라 승인 필요(P6-T4) | `uv python install 3.9` 후 `uv run -p 3.9 pytest -q` |
| Linux, PowerShell 7 | NOT RUN | 환경 없음(P6-T4에서 다룸) | P6-T4 |
| 심볼릭 링크 테스트 2개 | SKIPPED | 위 표 | 개발자 모드를 켠 뒤 재실행 |
