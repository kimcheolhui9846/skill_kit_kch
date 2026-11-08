# Claude Code에서 쓰기

설치 공통 절차는 `INSTALL.md`에 있다. 여기에는 Claude Code에만 해당하는 내용을 적는다. 에이전트 안 명령은 공식 문서에서 확인한 것만 적었다(`docs/v2/AGENT_LOAD_CHECK.md`의 출처, 2026-11-08).

## 1. 설치되는 것 (project 범위)

```bash
kit install --agent claude
kit install --agent claude --mcp context7 --hooks
```

| 파일 | 내용 | 키트가 쓰는 범위 |
|---|---|---|
| `CLAUDE.md` | 작업 정책 | `<!-- hackathon-kit:begin -->` … `end` 구간만 |
| `.claude/skills/<이름>/` | 스킬(기본 17개) | 키트가 만든 파일만 |
| `.claude/agents/counterexample-blackbox.md` | 반례 검토의 블랙박스 단계용 서브에이전트(standard 정책) | 키트가 만든 파일만 |
| `.mcp.json` | MCP 서버(프로필이나 `--mcp`로 고른 것) | `mcpServers`의 키트 소유 키만 |
| `.claude/settings.json`, `.claude/hooks/kit_approval.py` | 승인 훅(`--hooks`만), 플러그인 선언(`--plugin`만) | 키트 소유 키만 |

- `CLAUDE.md`가 있으면 Claude Code는 `AGENTS.md`를 읽지 않는다(공식 문서 CC-MEM, 기본 설정). 그래서 `--agent both`는 두 파일에 같은 정책을 따로 쓴다.
- `.mcp.json`에는 API 키 값을 쓰지 않는다. `"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"`처럼 환경 변수를 참조한다.

## 2. 프로젝트 설정과 사용자 설정의 차이

| | project 범위(기본) | user 범위(`--scope user`) |
|---|---|---|
| 위치 | 작업 공간의 `CLAUDE.md`, `.claude/`, `.mcp.json` | `~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.claude/settings.json` |
| MCP | `.mcp.json`에 쓴다 | `~/.claude.json`은 계정과 신뢰 상태도 담고 있어서 키트가 쓰지 않는다. `claude mcp add --scope user …` 명령을 출력하므로 직접 실행한다 |
| 훅(`--hooks`) | 쓸 수 있다 | 쓰지 않는다(64) |
| 플러그인(`--plugin`) | 선언을 쓴다 | 쓰지 않는다(64). 사용자 플러그인은 `capture`한 설정에서 온다 |
| 확인 | 쓰기 전에 `plan`이나 `--dry-run` | 항상 묻는다. 터미널이 없으면 `--yes`가 필요하다 |

```bash
kit install --agent claude --scope user --dry-run
```

## 3. 로드 확인

| 확인 | 어디서 | 명령 |
|---|---|---|
| 지침(`CLAUDE.md`) | Claude Code | `/context all`의 **Memory files** |
| 스킬 | Claude Code | `/skills`, 또는 `/task-router` 같은 `/스킬이름` |
| MCP | 셸 / Claude Code | `claude mcp list`, `claude mcp get context7` / `/mcp` |
| 훅 | Claude Code | `/hooks` |
| 서브에이전트 | Claude Code | 대화에서 사용할 수 있는 서브에이전트를 묻는다(최신 `/agents`는 안내만 출력) |
| 플러그인 | 셸 / Claude Code | `claude plugin list` / `/plugin`의 Errors 탭 |

- 이 명령들은 이번 문서 작업에서 실행하지 않았다(**미검증**). 검토자 점검표는 `docs/v2/AGENT_LOAD_CHECK.md` 2절이다.
- **MCP 승인:** 프로젝트 `.mcp.json`의 서버는 대화형 세션에서 승인해야 쓰인다. 승인 전 `claude mcp list`에는 `Pending approval`로 나온다. 승인을 되돌리려면 `claude mcp reset-project-choices`를 실행한다.
- **메모리 확인 명령:** 메모리 문서는 이제 `/memory`가 아니라 `/context all`을 쓰라고 한다(2026-11-08 확인).

## 4. 플러그인: 선언과 수동 설치

```bash
kit install --agent claude --plugin security-guidance --dry-run
```

**`--plugin NAME`으로 켰을 때:**
1. `.claude/settings.json`에 마켓플레이스(`extraKnownMarketplaces`)와 `enabledPlugins` 선언을 쓴다. 플러그인 원본은 커밋 sha로 고정된다.
2. 네트워크를 허용하면(`--yes` 또는 확인) `claude` CLI로 이 PC에 설치한다. 이 단계는 `~/.claude/plugins/`와 `.claude/settings.local.json`에 쓴다.
3. `uninstall`이 같은 CLI로 되돌린다.

**제한:**
- 카탈로그의 유일한 플러그인 `security-guidance`는 위험도 high이고 기본으로 꺼져 있다. 이유는 `docs/CATALOG.md` 4절에 있다.
- 이번 문서 작업에서는 `--dry-run`만 실행했다. 실제 설치(`--yes`)는 **미검증**이다. P4-T5에서 격리된 설정 폴더로 확인한 기록이 `kit/plugin_install.py`에 있다.
- 선언만 두고 직접 설치하려면, 플러그인 문서의 `/plugin` 화면에서 그 마켓플레이스의 플러그인을 고른다. 이 화면 조작은 미검증이다.

## 5. 승인 훅 (opt-in)

```bash
kit install --agent claude --hooks
```

- `UserPromptSubmit` 훅: 사용자의 답이 승인 단어뿐이면(예: `승인`, `승인 T-1`) 제출된 Task를 `by: human-hook`으로 승인 기록한다.
- `PreToolUse` 훅: 에이전트가 승인 파일을 쓰거나 `kit task approve`를 실행하려 하면 막는다.
- 2026-11-07 Claude Code 2.1.319에서 실제로 확인했다(ADR-011, M-05). 폴더를 신뢰해야 프로젝트 훅이 로드된다.
- 같은 이벤트에 사용자 훅이 이미 있으면 `CONFLICT`이고, 훅 스크립트도 쓰지 않는다.
- 끄려면 `kit uninstall --agent claude`를 실행하거나, `.claude/settings.json`에서 키트가 넣은 훅 키를 지운다. 그러면 L1(상태 기계)만 남는다.
- 자세한 흐름은 `HITL_WORKFLOW.md`에 있다.
