# 보안

이 검사들은 위험을 줄이는 장치이며 완전한 보안 경계가 아니다. 1부는 v2(명령이 있는 호출), 2부는 v1 설치기(명령 없는 호출)다.

# 1부. v2

## 1. 쓰는 곳

- **project 범위(기본):** 대상 작업 공간 안에만 쓴다. 모든 쓰기 경로는 `safe_path`를 거친다. `..`, 절대 경로, 대상 안의 링크를 따라 밖으로 나가는 경로는 거부한다. 설치 기록(`.kit/state/`)을 처음 읽을 때도 같은 검사를 한다(P6-T3).
- **링크:** 키트는 심볼릭 링크를 만들지 않는다. 스킬은 복사해서 둔다.
- **user 범위(`--scope user`):** `~/.codex`, `~/.claude`에 쓴다.
  - `--dry-run`이 아니면 항상 확인을 받는다. 터미널이 없으면 `--yes`가 있어야 한다.
  - 쓰기 전 원본은 `~/.kit-backups/`에 남는다.
  - `~/.claude.json`(계정과 신뢰 상태)은 쓰지 않는다.
- **전역 설정:** project 범위 명령은 `~/.codex`, `~/.claude`, 셸 프로필, 전역 npm/pip을 바꾸지 않는다. 테스트는 임시 HOME으로 이를 확인한다(V-18).
- **기존 파일:** 키트 구간과 키트 소유 키만 고친다. 사용자가 고친 키트 파일은 `CONFLICT`로 두고 쓰지 않는다. 바꾸기 전 원본은 `.kit/backups/<시각>/`에 남는다.
- **실패:** 한 번의 실행이 쓴 파일은 하나라도 실패하면 모두 되돌린다(`--agent both` 포함).

## 2. 네트워크

`--offline`이면 네트워크를 전혀 쓰지 않는다. 그렇지 않을 때 네트워크를 쓰는 일은 아래뿐이다. 모두 먼저 터미널에서 묻는다. 터미널이 없으면 `--yes`가 있어야 한다.

| 동작 | 언제 | 접속 |
|---|---|---|
| 도구 설치(`uv tool install`, `pip install --user`) | 프로필 도구가 없을 때 | 패키지 저장소 |
| MCP 연결 확인(`npx -y <패키지>@<버전>`) | MCP가 있는 프로필이나 `--mcp` | npm 레지스트리 |
| 플러그인 설치(`claude`/`codex` CLI) | `--plugin` | 플러그인 저장소 |
| `kit source add`, `update`, `check --online` | 사람이 명령할 때 | `api.github.com`, `codeload.github.com`(읽기 전용) |

- MCP 서버가 시작된 뒤 보내는 데이터는 서버마다 다르다. `docs/CATALOG.md` 3절의 "네트워크" 열에 적었다. 이 정보는 카탈로그 작성 때 확인한 것이고, 서버 코드를 감사한 것이 아니다.
- 키트는 원격 MCP(`url`, `http(s)://` 엔드포인트)를 등록하지 않는다.

## 3. MCP와 설정 감사

- 등록할 수 있는 서버는 `catalog/mcp.json`에 버전이 고정된 것뿐이다. 프로필 기본(`sequential-thinking`) 말고는 모두 기본으로 꺼져 있다. `--mcp NAME`으로만 켠다.
- 버전이 고정되지 않은 서버(`fetch`, `git`, `filesystem`)는 목록에만 있고 켤 수 없다.
- 감사는 `.codex/config.toml`과 `.mcp.json`에 같은 규칙을 적용한다(P6-T3).
  - 허용 목록 밖 서버, 금지 키(`url`, `bearer_token_env_var` 등), 허용 명령(`npx`, `uvx`) 밖의 명령, 원격 엔드포인트는 FAIL이다.
  - `_API_KEY`·`_TOKEN`·`_SECRET`으로 끝나는 env에 **값**을 직접 쓰면 FAIL이다. 환경 변수 이름을 참조하는 것(`env_vars`, `"${NAME}"`)만 허용한다.
- Python 3.9~3.10(`tomllib` 없음)에서는 TOML을 줄 단위로 검사한다. 위반을 찾으면 FAIL, 못 찾으면 `UNVERIFIED`다.

## 4. 비밀값

- 키트는 API 키를 묻거나 저장하거나 출력하지 않는다. 설정 파일에는 환경 변수 이름만 쓴다. `kit install`이 어느 키를 어디서 받는지 안내한다(`API keys` 줄).
- 로그, 보고서, JSON 출력, 승인 근거, WIP 메모는 토큰 형태 문자열을 가린다(`*_TOKEN=`, `*_API_KEY=`, `Bearer`, `sk-…`, `ghp_…` 등). 테스트: V-17.
- `kit capture`는 비밀값 검사에 하나라도 걸리면 아무것도 쓰지 않는다. 출력에는 키 이름과 위치만 나온다.

## 5. 외부 스킬과 리소스

- `third_party/`의 파일은 고정 커밋에서 바이트 그대로 가져왔다. `sources.lock.json`에 파일마다 sha256이 있다. `kit source check`가 오프라인으로 다시 계산한다.
- `kit source add`는 다음을 거친다.
  - 라이선스: 없거나 copyleft면 복사하지 않고 참조만 한다.
  - 내용 검사: 비밀값, 바이너리, 링크, 경로 탈출은 BLOCK이다. 원격 스크립트 실행 한 줄, 숨은 유니코드, 프롬프트 인젝션 문구는 REVIEW이고 사람의 `--accept-risk`가 필요하다.
  - 스크립트 파일은 기본으로 빼고, `--include`로 하나씩 넣는다.
- 출처와 라이선스: `THIRD_PARTY_NOTICES.md`.

## 6. 승인 강제 수준 (L0/L1/L2)

| 수준 | 무엇 | 한계 |
|---|---|---|
| L0 | 정책 문구(`AGENTS.md`/`CLAUDE.md`): 승인 없이 다음 Task로 가지 않는다 | 에이전트가 따르지 않을 수 있다 |
| L1 | 상태 기계: 의존 Task가 승인되지 않으면 `task start` 거부. 터미널이 없으면 `human-cli` 승인 거부. 제출 뒤 보고서가 바뀌면 승인 거부 | 에이전트가 `--by agent-recorded`로 기록할 수 있다. 대신 그렇게 표시된다 |
| L2(opt-in, `--hooks`) | 훅: 사용자의 답이 승인 단어뿐일 때만 `human-hook`으로 기록한다. 에이전트가 승인 파일을 쓰거나 `task approve`를 실행하면 막는다. 훅이 있으면 `agent-recorded`도 거부한다 | 셸로 우회할 수 있다. Codex 훅은 공식 문서상 "guardrail, not a complete enforcement boundary"다 |

- 2026-11-07 Claude Code 2.1.319와 codex-cli 0.166.0에서 L2를 실제로 확인했다(ADR-011, M-05).
- 우회는 사후에 드러난다. 승인 기록의 `by` 필드와 보고서 sha256으로 확인한다.

## 7. 알려진 한계 (v2)

- `npx`는 최상위 패키지만 버전을 고정한다. 하위 의존성은 설치 시점에 달라질 수 있다.
- 감사는 설정 파일의 정적 검사다. 서버나 플러그인이 실제로 하는 일은 검사하지 않는다.
- 에이전트가 파일을 실제로 읽었는지(Load)는 에이전트 안에서만 확인할 수 있다(`docs/v2/AGENT_LOAD_CHECK.md`).
- 설치 위에 다른 프로필·정책으로 다시 `install`하면 이전 항목 중 사용자가 고친 것은 지우지 않고 `CONFLICT`로 남긴다. 에이전트가 그 낡은 스킬을 함께 읽을 수 있으니 보고서의 `stale:` 항목을 확인한다.

# 2부. v1 설치기 (명령 없는 호출)

이 검사들은 위험을 줄이는 장치이며 완전한 보안 경계가 아니다.

## 코드가 강제하는 것

- 모든 쓰기는 `safe_path`를 거친다. `resolve()` 후 대상 하위가 아니면(`..`, 절대 경로, 심볼릭 링크 탈출) 거부한다.
- 파일을 바꾸기 전에 원본을 `.kit/backups/<시각>/`에 복사한다. 쓰기는 `.kit-tmp` 임시 파일을 거친 원자적 교체다.
- 전역 설정을 쓰지 않는다. 쓰는 곳은 대상의 `AGENTS.md`, `.agents/skills/`, `.codex/config.toml`, `.kit/`뿐이다.
- MCP는 `mcp/manifest.json`에서 `enabled_by_default`가 참이고 `mcp/allowlist.json`의 `servers`에 있는 것만 등록한다. 지금은 `sequential-thinking` 하나다.
- 감사(`kit/audit.py`)는 `.codex/config.toml`에서 다음을 FAIL로 본다. allowlist에 없는 서버, 금지 키(`url`, `bearer_token_env_var`), 허용 목록(`npx`, `uvx`) 밖의 명령, `http://`·`https://` 원격 엔드포인트, `env`·`env_vars`의 `_API_KEY`·`_TOKEN`·`_SECRET`으로 끝나는 이름(대소문자 무시).
- 로컬 로그(`.kit/logs/`)는 `*_TOKEN=`, `*_API_KEY=` 같은 값, `Bearer` 값, `sk-…`, `ghp_…` 형태를 `***`로 가린다. 환경 변수 값은 기록하지 않는다.
- 저장소 스캔 테스트(`tests/test_security.py`)가 위험 패턴을 찾는다.
- `--offline`이면 도구 설치와 MCP 핸드셰이크를 하지 않는다. 네트워크 접근이 전혀 없다.

## 네트워크 동작과 시점

네트워크는 아래 경우에만 쓰며, 보고서의 `Network:` 줄에 표시한다. `--dry-run`은 설치하지 않고 서버를 시작하지 않는다(`--version` 점검은 실행한다). `--verify-only`는 설치하지 않지만 MCP 핸드셰이크(`npx -y`)는 `--offline`·`--no-mcp`가 아닌 한 실행하며, 이때 네트워크와 대상 밖의 npm 캐시를 쓴다.

| 동작 | 언제 |
|---|---|
| `uv tool install <pkg>==<ver>` | python 프로필, 도구가 PATH에 없고 `uv`가 있을 때 |
| `python -m pip install --user <pkg>==<ver>` | 위가 불가하거나 실패했을 때 |
| `npx -y <pkg>@<ver>` | MCP 핸드셰이크: python, data, web, full 프로필(`--offline`·`--no-mcp`가 아닐 때) |

`core`와 `web` 프로필은 도구를 설치하지 않는다. `data`는 numpy·pandas를 설치하지 않고 명령만 안내한다. `full`은 도구를 설치하지 않지만 `python`을 상속하므로 sequential-thinking 등록과 npx 핸드셰이크는 한다.

## 알려진 한계

- `npx`는 최상위 패키지만 버전을 고정한다. 하위 의존성은 범위 지정에 따라 해석되므로 설치 시점에 달라질 수 있다.
- `uv tool`과 `pip --user`는 대상 밖의 사용자 수준 도구 폴더에 설치한다. 대상 폴더 쓰기 제한은 이 설치에 적용되지 않는다.
- 서버가 stdin 종료를 무시하면 핸드셰이크 뒤에 프로세스가 남을 수 있다(`docs/COMPATIBILITY.md`).
- 감사는 `config.toml`의 정적 검사다. 서버 코드가 실제로 하는 일은 검사하지 않는다.
- manifest의 `sequential-thinking` 네트워크 송신과 파일 접근 항목은 "예상"이며 확인한 사실이 아니다. 라이선스는 2026.8.31에 대해 다시 확인하지 않았다.

## 비활성 MCP 서버

`mcp/manifest.json`에 후보로 기록만 하고 등록하지 않는다.

| 서버 | 사유 |
|---|---|
| `fetch` | fetches arbitrary URLs: can send task data outside the workspace |
| `git` | exposes git operations; remote sync and push are forbidden in the exam |
| `filesystem` | duplicates Codex's own file access and widens the reachable paths |
