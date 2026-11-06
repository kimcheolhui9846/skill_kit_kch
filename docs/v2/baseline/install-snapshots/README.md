# P1-T3 설치 동작 스냅샷 (회귀 기준선)

- 생성: 2026-11-05, HEAD `98add1ed`, Windows 11 / Python 3.12.10
- 생성 스크립트: `snapshot.py` (이 폴더). 명령: `python -I docs/v2/baseline/install-snapshots/snapshot.py . docs/v2/baseline/install-snapshots`
- 각 경우는 새 임시 작업 공간에서 `python -I run_kit.py <인수>`(bootstrap이 넘기는 것과 같은 진입점)로 실행했다. HOME/USERPROFILE은 임시 디렉터리로 바꿨다.
- 결과 파일: `<경우>.json` = 실행별 `{args, exit, stdout, stderr}`, 최종 트리(경로 → SHA-256), `home_untouched`.
- 요약: `INDEX.md`

## 정규화 규칙

| 가변 값 | 치환 |
|---|---|
| 대상 작업 공간 경로 | `<TARGET>` |
| 키트 경로 | `<KIT>` |
| `YYYYmmdd-HHMMSS` 타임스탬프(백업 디렉터리 이름 포함) | `<STAMP>` |
| `.kit/logs/*` | 트리에서 제외(내용은 stdout 보고서를 마스킹한 사본) |

골든 테스트로 바꿀 때 추가로 정규화해야 하는 값 [확인됨: 보고서 원문]:
- `Environment:` 줄(OS, 아키텍처, Python 버전)과 `Tools:` 줄은 머신마다 다르다.
- `python`/`data`/`full`의 `tool:pytest`, `tool:ruff` 결과는 해당 명령이 PATH에 있는지에 따라 달라진다. 이 PC에서는 둘 다 있었다. 골든 테스트에서는 기존 `fast_preflight` 픽스처처럼 탐지를 고정해야 한다.

## 결과 요약

| 경우 | 종료 코드 | 트리 파일 수 | 관찰 |
|---|---|---|---|
| 5개 프로필 × 기본(`--offline`) | 모두 0 | core 28, 나머지 29 | `python/data/web/full`은 `.codex/config.toml` 1개가 더 생긴다 |
| 5개 프로필 × `--dry-run` | 모두 0 | 0 | 아무것도 쓰지 않음 |
| 5개 프로필 × `--verify-only`(빈 작업 공간) | 모두 2 | 0 | 설치되지 않았으니 BLOCKED. `.kit/logs/`만 씀 |
| 5개 프로필 × `--no-mcp` | 모두 0 | 28 | `.kit/state.json`을 빼면 core와 트리가 같음(확인 스크립트 결과 True) |
| `python` 3회 연속 | 0, 0, 0 | 29 | 멱등 |
| 기존 사용자 `AGENTS.md` | 0 | 29 | 구간 추가(APPEND), `.kit/backups/<STAMP>/AGENTS.md`에 백업 |
| 사용자가 고친 키트 구간 | 2 | 28 | `CONFLICT required AGENTS.md`, 파일은 그대로 둠 |
| 키트 폴더 자신을 대상으로 | 65 | 0 | |

모든 경우에서 HOME은 변경되지 않았다(`home_untouched: true`).

설치 트리는 `AGENTS.md` 1 + 스킬 파일 26(11개 스킬의 `SKILL.md` 11 + `examples/example.md` 11 + `references/languages.md` 4) + `.kit/state.json` 1 = 28이다.

## 실행하지 않은 것

| 항목 | 상태 | 이유 |
|---|---|---|
| `--offline` 없는 실행(도구 설치, `npx` MCP 핸드셰이크, `codex mcp list`) | NOT RUN (network, approval needed) | 네트워크 사용, 사용자 범위 도구 설치(`uv tool install`/`pip install --user`) |
| 셸 전용 모드(Python 없음) | NOT RUN | Python 없는 환경을 만들지 않았다. 기존 `tests/test_entrypoints.py`가 `KIT_PYTHON`으로 셸 모드를 테스트한다 [확인됨: 테스트 이름 `test_fallback_*`] |
| `bootstrap.ps1`/`bootstrap.sh` 경유 실행 | NOT RUN (이 스냅샷 범위) | 같은 `run_kit.py`로 넘기는 것을 `test_entrypoints.py::test_delegates_to_python`이 확인한다 |
| Linux에서 같은 스냅샷 | NOT RUN | Linux 환경 없음 |
