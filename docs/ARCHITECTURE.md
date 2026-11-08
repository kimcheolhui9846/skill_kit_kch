# 아키텍처

이 문서는 두 부분이다. 1부는 v2(명령이 있는 호출, Codex와 Claude Code)이고, 2부는 그대로 남아 있는 v1 설치기(명령 없는 호출)다. 설계의 근거는 `docs/v2/04_DESIGN.md`와 `docs/v2/adr/`에 있다.

# 1부. v2

## 1. 진입과 분기

```text
bootstrap.sh / bootstrap.ps1 / python run_kit.py
        -> kit.app.run(argv)
             argv[0]이 명령 이름(install, plan, verify, task, ...) -> kit.commands.run   (v2)
             그 밖의 모든 입력(빈 입력, --옵션)                  -> v1 설치기(2부)    (ADR-002)
```

- 이 규칙 덕분에 v1 사용법은 바뀌지 않는다. v1 파서에는 위치 인수가 없었으므로, 첫 토큰이 단어인 입력은 원래 오류(64)였다.
- `kit.app.main`은 예상하지 못한 예외를 BLOCKED(2)로 바꾼다. 대상 밖으로 쓰려는 경로(`PathEscapeError`)는 안전 거부로 따로 알린다.

## 2. 설치 계열의 흐름

```text
commands.run
  -> 프로필 해석 (profile_resolver: 프로필 + 팩, extends, 순환 거부)
  -> 정책 적용 (catalog: 스킬 카탈로그, standard/restricted, 대체 스킬, 오버레이 층)
  -> Adapter별 plan (adapters/codex.py, claude.py, user.py): 쓰기 없는 계획
  -> 확인 (네트워크 또는 user 범위면 터미널에서 묻거나 --yes)
  -> transaction.apply_all: 백업 -> 원자적 쓰기 -> 실패하면 이번 실행이 쓴 것을 모두 되돌림
  -> manifest: 에이전트별 소유 기록 (.kit/state/install-manifest.json)
  -> Adapter별 verify + audit (TOML과 JSON 같은 규칙) -> 보고서
```

- `--agent both`는 두 Adapter의 계획을 합쳐 한 트랜잭션으로 쓴다. 한쪽이 실패하면 둘 다 되돌린다.
- `update`와 `uninstall`은 `lifecycle.py`가 계획한다. 소유 기록의 해시와 지금 내용이 같은 것만 바꾸거나 지운다.

## 3. Adapter

| Adapter | 정책 파일 | 스킬 | MCP | 그 밖 |
|---|---|---|---|---|
| `codex` (project) | `AGENTS.md` 구간 | `.agents/skills/` | `.codex/config.toml` 구간 | 훅 `.codex/hooks.json` |
| `claude` (project) | `CLAUDE.md` 구간 | `.claude/skills/` | `.mcp.json`의 키트 소유 키 | 훅·플러그인 `.claude/settings.json`, 서브에이전트 `.claude/agents/` |
| `user` (`--scope user`) | `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` 구간(이 PC에서 capture한 지침) | `~/.codex/skills/`, `~/.claude/skills/` | `~/.codex/config.toml` 구간. Claude는 `claude mcp add` 명령 출력 | OMX(Codex) |

- Adapter는 "어디에 무엇을"만 안다. 쓰기, 백업, 되돌리기는 공통 실행기(`transaction.py`, `register.py`)가 맡는다. 그래서 에이전트를 추가해도 실행기는 바뀌지 않는다.
- 설정 파일 쓰기는 `writers/`의 세 방식뿐이다: `markdown_block`(마커 구간), `toml_block`(마커 구간), `json_keys`(JSON 포인터로 고른 키만).

**새 에이전트 추가:**
1. `kit/adapters/`에 Adapter를 만들고 `registry.py`에 등록한다.
2. `catalog/*.json`의 `agents`에 이름을 더한다.
3. 위 표와 `docs/v2/02_COMPATIBILITY_MATRIX.md`에 열을 더한다. 경로는 공식 문서로 확인한다.
4. `tests/adapters/`와 골든 테스트를 더한다.

## 4. 데이터

| 파일 | 내용 | 모듈 |
|---|---|---|
| `profiles/*.json`, `profiles/packs/*.json` | 프로필과 팩(스키마 2) | `profile_resolver.py` |
| `catalog/skills.json` | 스킬마다 위치, 출처, 에이전트, 팩, 정책 | `catalog.py` |
| `catalog/mcp.json`, `plugins.json`, `manual.json` | MCP 서버, 플러그인, 수동 도구(위험도, 기본 꺼짐 여부) | `mcp_catalog.py` |
| `sources.lock.json` | 외부 파일의 고정 커밋과 sha256 | `sources.py` |
| `user/` | 이 PC에서 capture한 개인 전역 설정 스냅숏 | `capture.py`, `userscope.py` |
| `<target>/.kit/state/install-manifest.json` | 에이전트별 소유 항목(파일, 구간, JSON 키)과 해시 | `manifest.py` |
| `<target>/.kit/work/*` | Task, 추적, 반례, 보고서, HANDOFF, WIP | `tasks.py`, `trace.py`, `counterexamples.py`, `recover.py` |

## 5. 모듈 (v2에서 더해진 것)

| 무리 | 모듈 |
|---|---|
| 명령 | `commands.py`(설치 계열과 분기), `task_cli.py`, `trace_cli.py`, `evidence_cli.py`, `ce_cli.py`, `recover_cli.py`, `source_cli.py` |
| 설치 | `adapters/`, `writers/`, `profile_resolver.py`, `catalog.py`, `policy_render.py`, `subagents.py`, `transaction.py`, `manifest.py`, `lifecycle.py`, `userscope.py`, `credentials.py` |
| MCP·플러그인 | `mcp_catalog.py`, `mcpjson.py`, `mcpconfig.py`, `audit.py`, `plugin_install.py` |
| 외부 스킬 | `sources.py`, `source_add.py`, `github_fetch.py`(키트의 유일한 네트워크 코드), `source_scan.py`, `skill_check.py` |
| 개인 설정 | `capture.py`, `secrets_scan.py` |
| HITL | `tasks.py`, `trace.py`, `junit.py`, `evidence.py`, `counterexamples.py`, `recover.py`, `approval_hooks.py`(훅 설치), `shared/hooks/kit_approval.py`(훅 본체) |

모두 Python 3.9 표준 라이브러리만 쓴다.

# 2부. v1 설치기 (명령 없는 호출)

아래는 v1 문서 그대로다. 이 경로의 결과는 v1과 바이트 단위로 같아야 하고, `tests/golden/`이 이를 확인한다.

## 왜 `kit/`인가

지시서는 `scripts/*.py`를 가정했지만 이 저장소는 `kit/` 패키지를 쓴다. import와 테스트가 단순해지기 때문이다. 대응은 1:1이다.

- `scripts/install.py` → `kit/tools.py`
- `scripts/audit.py` → `kit/audit.py`

`kit/`는 Python 표준 라이브러리만 쓴다(런타임 의존성 없음). 개발 의존성(pytest, ruff)은 `uv.lock`에 있다.

## 실행 흐름

```text
bootstrap.sh / bootstrap.ps1  ->  run_kit.py  ->  kit.app.run
```

셸 스크립트는 Python 3.9+를 찾아 `python -I run_kit.py <인수>`로 넘긴다. `run_kit.py`가 저장소 루트를 `sys.path`에 넣는다(`PYTHONPATH`를 쓰지 않는다). Python이 없으면 셸 전용 모드로 `AGENTS.md`와 Skill만 복사한다(프로필과 무관하게 도구·MCP 없음, 종료 코드 1).

`kit.app.run`의 순서:

1. 인수 파싱과 프로필 로드, 대상이 키트 폴더 자신이면 거부(종료 코드 65)
2. preflight (`preflight.py`): OS, 셸, 쓰기 가능 여부, 도구 버전
3. plan (`plan.py`): 파일별로 create / update / append / conflict / unchanged 결정. `--dry-run`이면 여기서 출력하고 종료
4. apply (`register.py`): 백업 후 원자적 쓰기, 상태 저장
5. tools (`tools.py`): 프로필 도구 확인과 설치
6. verify (`verify.py`, `mcpconfig.verify_config`): 대상의 실제 내용 검사
7. audit (`audit.py`): `.codex/config.toml`을 allowlist와 대조
8. web check (`webcheck.py`): `node-project` 도구가 있는 프로필만
9. MCP check (`mcpcheck.py`): stdio 핸드셰이크와 `codex mcp list --json`
10. report와 로그 (`report.py`, `logs.py`)

`--verify-only`는 apply와 설치를 건너뛴다. 예상치 못한 예외는 `kit.app.main`이 잡아 `BLOCKED`로 끝낸다.

## 모듈

| 모듈 | 역할 |
|---|---|
| `model.py` | 항목 결과(`ItemResult`), 판정 문자열, 종료 코드, 예외 |
| `cli.py` | 인수 → `Options`. 오류는 종료하지 않고 예외로 올린다 |
| `profiles.py` | `profiles/*.json` 로드, `extends` 상속, 검증 |
| `preflight.py` | OS·셸·도구(`git uv node npx codex python`) 탐지 |
| `fsops.py` | `safe_path`, SHA-256, `.kit/state.json`, 백업 |
| `agentsmd.py` | 보호 구간 렌더링·추출·병합(마커를 인수로 받는다) |
| `skills.py` | `SKILL.md` frontmatter 파싱과 검증 |
| `plan.py` | 변경 계획과 계획 출력 |
| `register.py` | 계획 적용(원자적 쓰기, 백업, 실패해도 상태 저장) |
| `verify.py` | AGENTS.md, Skill, 쓰기 가능 여부 검사 |
| `mcpconfig.py` | manifest·allowlist 로드, 설정 블록 렌더링, 병합 검사, 설정 검증 |
| `audit.py` | 설정을 allowlist와 대조 |
| `tools.py` | 도구 설치 계획과 실행(`uv tool install` → `pip install --user`) |
| `webcheck.py` | `package.json`, lockfile, `engines.node` 검사 |
| `mcpcheck.py` | MCP 서버 핸드셰이크, `codex mcp list --json` 조회 |
| `report.py` | 최종 상태 판정, 다음 행동, 보고서 출력 |
| `logs.py` | 비밀 마스킹과 `.kit/logs/` 기록 |
| `app.py` | 위 단계를 엮는 `run`과 `main` |

## 상태와 멱등성

- `<target>/.kit/state.json`에 키트가 쓴 파일의 경로와 해시, 프로필을 기록한다. 실행 시각은 넣지 않는다.
- 대상 해시가 새 내용과 같으면 건너뛴다(`unchanged`).
- 대상 해시가 기록 해시와 같고 새 내용과 다르면 백업 후 갱신한다(`update`).
- 대상 해시가 기록 해시와 다르면 사용자가 고친 것이므로 `CONFLICT`로 두고 쓰지 않는다.
- 기록이 없는데 같은 경로에 파일이 있으면, 내용이 같으면 채택하고 다르면 `CONFLICT`다.
- 수정 전 원본은 `.kit/backups/<YYYYmmdd-HHMMSS>/`에 남는다.

## 마커 두 쌍

| 파일 | 시작 | 끝 |
|---|---|---|
| `AGENTS.md` | `<!-- hackathon-kit:begin -->` | `<!-- hackathon-kit:end -->` |
| `.codex/config.toml` | `# hackathon-kit:begin` | `# hackathon-kit:end` |

키트는 구간 안만 고친다. 마커가 짝이 맞지 않거나 중복되면 `CONFLICT`다. `config.toml`에서 같은 이름의 서버가 구간 밖에 있어도 `CONFLICT`이며 파일은 그대로 둔다.

## 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | READY (dry-run 완료 포함) |
| 1 | PARTIAL |
| 2 | BLOCKED |
| 64 | 잘못된 인수 |
| 65 | 대상 디렉터리 없음 또는 키트 폴더 자신 |

필수 항목의 FAIL·CONFLICT는 `BLOCKED`, 선택 항목의 FAIL·CONFLICT는 `PARTIAL`이다. `UNVERIFIED`와 `SKIPPED`는 상태를 낮추지 않는다.
