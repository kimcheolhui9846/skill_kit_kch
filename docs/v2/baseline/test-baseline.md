# P1-T1 테스트 기준선

- 실행 일시: 2026-11-05 (로컬, KST)
- 브랜치 / HEAD: `main` / `98add1edee13401cd1e79f9ad69ffee7b272d971`
- 작업 트리: 실행 전 clean. 이후 변경은 `docs/v2/`, `docs/superpowers/specs/2026-11-05-v2-addendum-design.md` 추가뿐.
- 원문 출력: `docs/v2/baseline/raw/` (`uv-sync.txt`, `pytest.txt`, `pytest-junit.xml`, `ruff_check__.txt`, `ruff_format_--check__.txt`, `shellcheck.txt`)

## 환경

| 도구 | 버전 | 비고 |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 | 실제 Windows 실기 |
| Python | 3.12.10 (Microsoft Store 배포) | 3.9는 로컬에 없음(`uv python list`에서 download available) |
| uv | 0.10.9 | |
| node / npx | v24.18.0 / 11.16.0 | |
| Windows PowerShell | 5.1.26100.9711 | |
| pwsh (PowerShell 7) | 없음 | |
| shellcheck | 0.11.0 | |
| git | 2.54.0.windows.1 (Git Bash) | |
| codex CLI | codex-cli 0.166.0 | 상태 변경 명령은 실행하지 않음 |
| claude CLI | 2.1.318 (Claude Code) | 상태 변경 명령은 실행하지 않음 |

## 실행 명령과 결과

| 명령 | 원문 결과 요약 | 종료 코드 |
|---|---|---|
| `uv sync --offline` | `Resolved 14 packages in 0.82ms` / `Audited 7 packages in 1ms` | 0 |
| `uv run --offline pytest -q -rs --junitxml=…` | `338 passed, 1 skipped in 42.64s` | 0 |
| `uv run --offline ruff check .` | `All checks passed!` | 0 |
| `uv run --offline ruff format --check .` | `50 files already formatted` | 0 |
| `shellcheck bootstrap.sh` | (출력 없음) | 0 |

`uv sync` 대신 `--offline`을 붙였다. 잠금 파일이 이미 충족되어 결과는 같다고 본다 [가정: 온라인 `uv sync`는 네트워크 동작이라 실행하지 않음].

## 건너뛴 테스트

| 테스트 | 이유(원문) |
|---|---|
| `tests/test_fsops.py:31` | `symlinks not permitted on this system` (Windows에서 개발자 모드·관리자 권한 없음) |

## 마커 테스트

- `real_preflight` 5개, `real_mcp` 5개. 기본 실행에서 **제외되지 않고 함께 실행되었다** [확인됨: `pyproject.toml`에 `addopts`/`-m` 필터 없음, `--collect-only -m …` 결과 각 5/339].
- `real_preflight`: 이 PC의 실제 도구를 탐지한다(네트워크 없음).
- `real_mcp`: `tests/test_mcpcheck.py`에서 임시로 쓴 가짜 MCP 서버(`sys.executable`)에 핸드셰이크한다. 외부 네트워크와 npx를 쓰지 않는다 [확인됨: tests/test_mcpcheck.py:35-58].
- 결과적으로 **기본 실행은 외부 네트워크를 쓰지 않는다**. 실제 `npx` MCP 핸드셰이크와 실제 도구 설치는 테스트에 없다 → 해당 동작은 `NOT RUN (network, approval needed)`.

## 실행하지 못한 것

| 항목 | 상태 | 이유 | 확인 방법 |
|---|---|---|---|
| Python 3.9 실행 | NOT RUN | 로컬에 없음. 내려받기는 네트워크 동작이라 승인 필요 | `uv python install 3.9` 후 `uv run -p 3.9 pytest -q` |
| PowerShell 7(pwsh) | NOT RUN | 미설치 | 설치 후 `pwsh -File bootstrap.ps1 --dry-run --offline` |
| Linux 실행 | NOT RUN | Linux 환경 없음(WSL 미확인) | Linux에서 `uv run pytest -q` |
| 심볼릭 링크 테스트 | SKIPPED | 위 표 | 개발자 모드 켠 뒤 재실행 |
