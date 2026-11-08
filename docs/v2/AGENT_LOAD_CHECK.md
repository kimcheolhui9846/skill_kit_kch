# 에이전트 로드 수동 점검표 (P6-T6)

키트의 `verify`는 파일이 제자리에 있는지만 확인한다. 에이전트가 그 파일을 실제로 읽었는지는 에이전트 안에서만 볼 수 있다. 그래서 보고서의 Load 칸은 항상 `UNVERIFIED`다(REQ-AGENT-005). 이 점검표는 그 칸을 검토자가 직접 채우기 위한 것이다.

- 모든 명령은 아래 "출처"의 공식 문서에서 2026-11-08에 확인했다. 문서에서 확인하지 못한 명령은 적지 않았다.
- 결과 칸은 비워 두었다. 검토자가 채우기 전까지 모든 항목은 최종 보고서에서 `UNVERIFIED`다.
- 이 점검표는 `docs/v2/06_TEST_PLAN.md` 4절의 M-01(Codex), M-02(Claude Code)를 대신한다. 승인 훅(M-05)은 2026-11-07에 이미 실제로 확인했다(ADR-011). 여기서는 훅이 로드되는지만 다시 본다.

## 0. 준비

**주의:**
- 이 점검은 검토자의 실제 Codex와 Claude Code 로그인으로 한다.
- 폴더를 신뢰하면 그 기록이 각 에이전트의 사용자 설정에 남는다. Codex는 `~/.codex/config.toml`, Claude Code는 `~/.claude.json`이다. 키트가 쓰는 것이 아니라 에이전트가 쓴다.
- 점검이 끝나면 각 에이전트에서 그 폴더의 신뢰를 지울 수 있다.

임시 작업 공간에 `both`로 설치한다. MCP는 `context7`(카탈로그의 기본 서버)만, 훅은 opt-in으로 넣는다.

```powershell
# Windows PowerShell 5.1 / 7
$KIT = '<KIT>'                                   # 키트를 받은 폴더
$WS  = Join-Path $env:TEMP ('kit-load-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory $WS | Out-Null
git -C $WS init -q                               # Codex는 저장소 루트까지 .agents/skills를 찾는다
python "$KIT\run_kit.py" install --agent both --mcp context7 --hooks --offline --target $WS
python "$KIT\run_kit.py" verify --agent both --offline --target $WS
Set-Location $WS
```

```bash
# Linux / macOS
KIT='<KIT>'; WS=$(mktemp -d); git -C "$WS" init -q
python3 "$KIT/run_kit.py" install --agent both --mcp context7 --hooks --offline --target "$WS"
python3 "$KIT/run_kit.py" verify --agent both --offline --target "$WS"
cd "$WS"
```

**기대 결과:** 두 명령 모두 `Status: READY`로 끝난다. `verify`의 Load 칸은 `UNVERIFIED`다.

**설치되는 것** (2026-11-08에 임시 폴더에 실제로 설치해 확인했다):

| 대상 | 파일 |
|---|---|
| Codex | `AGENTS.md`, `.agents/skills/`(스킬 17개), `.codex/config.toml`(`[mcp_servers.context7]`), `.codex/hooks.json`, `.codex/hooks/kit_approval.py` |
| Claude Code | `CLAUDE.md`, `.claude/skills/`(같은 17개), `.mcp.json`(`context7`), `.claude/settings.json`(`hooks`), `.claude/hooks/kit_approval.py`, `.claude/agents/counterexample-blackbox.md` |

**스킬 17개:** `algorithm-optimizer`, `algorithm-options`, `benchmark`, `codebase-explorer`, `counterexample-hunter`, `data-quality-validator`, `design-review`, `implementation-review`, `karpathy-guidelines`, `receiving-code-review`, `requesting-code-review`, `session-recovery`, `systematic-debugging`, `task-approval`, `task-router`, `test-driven-development`, `verification-before-completion`

**참고:**
- `context7` 서버는 에이전트가 시작할 때 `npx`로 패키지를 받는다. 이 단계는 키트가 아니라 에이전트가 네트워크를 쓴다.
- API 키는 설정 파일에 들어 있지 않다. 환경 변수 이름 `CONTEXT7_API_KEY`만 참조한다.

## 1. Codex

| ID | 확인 항목 | 명령(어디서) | 기대 결과 | 출처 | 결과(검토자) | 날짜·버전 |
|---|---|---|---|---|---|---|
| C-01 | 프로젝트 지침(`AGENTS.md`) 로드 | 셸, `$WS`에서: `codex --ask-for-approval never "Summarize the current instructions."` | 요약에 키트 정책이 나온다. 예: 복잡한 작업은 task-router로 시작, 실행하지 않은 테스트를 통과라고 하지 않음 | CX-AG | | |
| C-02 | 프로젝트 스킬 로드 | `codex` TUI에서 `/skills` | 위 17개가 보인다. 같은 이름이 두 번 나오지 않는다. `.claude/skills`의 사본이 따로 보이지 않는다(R-4: 문서에 근거가 없어 확인이 필요함) | CX-SK | | |
| C-03 | 스킬 호출 | TUI 입력창에 `$` 입력 | 목록에 `task-router` 등 키트 스킬이 나온다 | CX-SK | | |
| C-04 | 신뢰 전 MCP | 이 폴더를 신뢰하지 않은 상태로 TUI에서 `/mcp` | 프로젝트 `.codex/` 층은 신뢰한 프로젝트에서만 로드된다. 그래서 `context7`이 없다. 키트가 MCP 로드를 `UNVERIFIED`로 보고하는 이유다 | CX-MCP | | |
| C-05 | 신뢰 후 MCP | 폴더를 신뢰한 뒤 셸에서 `codex mcp list`, TUI에서 `/mcp` | `context7`이 목록에 있고, `/mcp`에서 활성 서버로 보인다 | CX-MCP | | |
| C-06 | 훅 로드 | TUI에서 `/hooks` | 프로젝트 훅 `UserPromptSubmit`, `PreToolUse`(`kit_approval.py`)가 보인다. 새 훅은 검토와 신뢰 전까지 실행되지 않는다(시작할 때 `/hooks`를 열라는 경고가 나올 수 있다) | CX-HK | | |
| C-07 | 사용자 범위 스킬 (M-06을 적용한 경우만) | `~/`에서 `codex`를 열고 `/skills` | `~/.codex/skills`에 둔 스킬(OMX 포함)이 보인다. 이 경로는 문서에 없는 호환 동작이다(02 매트릭스). Codex 버전을 함께 적는다 | CX-SK(사용자 경로는 `$HOME/.agents/skills`만 문서화) | | |

## 2. Claude Code

| ID | 확인 항목 | 명령(어디서) | 기대 결과 | 출처 | 결과(검토자) | 날짜·버전 |
|---|---|---|---|---|---|---|
| L-01 | 프로젝트 지침(`CLAUDE.md`) 로드 | `$WS`에서 `claude`를 열고 `/context all` | **Memory files** 목록에 `CLAUDE.md`가 있다. `AGENTS.md`는 없다. 문서상 `CLAUDE.md`가 있으면 `AGENTS.md`는 읽지 않는다(기본값 `claude-md-or-agents-md`). `both` 설치에서는 이것이 맞다 | CC-MEM | | |
| L-02 | 프로젝트 스킬 로드 | `/skills` | 위 17개가 보인다. 같은 이름이 두 번 나오지 않는다. `.agents/skills`의 사본이 따로 보이지 않는다(R-4) | CC-SK | | |
| L-03 | 스킬 호출 | 입력창에 `/task-router` 입력 | 스킬로 실행된다(`/` 메뉴에 나옴) | CC-SK | | |
| L-04 | 승인 전 MCP | 셸, `$WS`에서: `claude mcp list` 그리고 `claude mcp get context7` | `context7`이 `⏸ Pending approval (run claude to approve)` 상태다. `.mcp.json` 서버는 대화형 세션에서 승인해야 쓴다 | CC-MCP | | |
| L-05 | 승인 후 MCP | `claude`를 열고 승인 프롬프트에서 `context7` 승인 → `/mcp` | `context7`이 보이고 상태가 나온다. 승인을 되돌리려면 `claude mcp reset-project-choices` | CC-MCP | | |
| L-06 | 훅 로드 | `/hooks` | `UserPromptSubmit`, `PreToolUse`(matcher `Bash\|PowerShell\|Edit\|Write\|MultiEdit\|NotebookEdit`) 훅이 project settings 출처로 보인다. 선택하면 `kit_approval.py` 명령이 보인다 | CC-HK | | |
| L-07 | 서브에이전트 로드 | 대화에서 "사용할 수 있는 서브에이전트를 알려 줘"라고 묻는다 | `counterexample-blackbox`가 목록에 있다. 문서상 최신 `/agents`는 목록 대신 "Claude에게 묻거나 `.claude/agents/`를 직접 보라"는 안내만 출력한다(v2.1.197 이하는 마법사) | CC-SUB | | |
| L-08 | 플러그인 (선택, `--plugin`을 쓴 경우만) | 셸에서 `claude plugin list`, 대화에서 `/plugin`(**Errors** 탭) | 선언한 플러그인이 보이고 Errors 탭에 오류가 없다. 카탈로그의 유일한 플러그인 `security-guidance`는 위험도 high이고 기본으로 꺼져 있다. 그래서 이 점검에서는 설치하지 않는 것을 권한다 | CC-PL | | |
| L-09 | 사용자 범위 (M-06을 적용한 경우만) | 홈에서 `claude`를 열고 `/skills`, `/context all` | `~/.claude/skills`의 스킬과 `~/.claude/CLAUDE.md`가 보인다 | CC-SK, CC-MEM | | |

## 3. 정리

```powershell
Set-Location $env:TEMP
python "$KIT\run_kit.py" uninstall --agent both --target $WS    # 키트가 쓴 파일만 지운다
Remove-Item -Recurse -Force $WS
```

- 폴더 신뢰와 MCP 승인 기록은 각 에이전트에 남는다. 필요하면 지운다.
- Claude Code의 MCP 승인은 `claude mcp reset-project-choices`로 지울 수 있다.

## 4. 판정

- 각 행이 기대 결과와 같으면 그 항목은 `VERIFIED-RUN`이다. 결과 칸에 에이전트 버전과 날짜를 적는다.
- 다르면 실제로 본 내용을 그대로 적는다. 그 항목은 결함 후보로 최종 보고서에 남긴다.
- 실행하지 않은 행은 `NOT RUN`이다. 최종 보고서에서 Load는 `UNVERIFIED`로 남는다.

| 에이전트 | 검토자 | 날짜 | 버전(`codex --version` / `claude --version`) | 판정 | 메모 |
|---|---|---|---|---|---|
| Codex | | | | | |
| Claude Code | | | | | |

## 출처 (확인일 2026-11-08, 확인 수준 VERIFIED-DOC)

| ID | URL | 근거 인용(짧게) |
|---|---|---|
| CX-AG | https://learn.chatgpt.com/docs/agent-configuration/agents-md | "Run `codex --ask-for-approval never "Summarize the current instructions."` from a repository root." |
| CX-SK | https://learn.chatgpt.com/docs/build-skills | "In Codex CLI or the IDE extension, run `/skills` or type `$` to mention a skill." / "Codex scans `.agents/skills` in every directory from your current working directory up to the repository root." |
| CX-MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | "In the `codex` TUI, use `/mcp` to see your active MCP servers." / "Run `codex mcp list` to see configured servers." / "`.codex/config.toml` (trusted projects only)" |
| CX-HK | https://learn.chatgpt.com/docs/hooks | "Use `/hooks` in the CLI to inspect hook sources" / "new or changed hooks are marked for review and skipped until trusted." |
| CC-MEM | https://code.claude.com/docs/en/memory | "To confirm the file loaded, run `/context all` in a session and check the list under **Memory files**." / AGENTS.md는 "only when you have no `CLAUDE.md` in your working directory or above it" |
| CC-SK | https://code.claude.com/docs/en/skills | "To see which skills synced, run `/skills`." / "you can invoke one directly with `/skill-name`" |
| CC-MCP | https://code.claude.com/docs/en/mcp | "`claude mcp list` shows a health status next to each server" / "`⏸ Pending approval (run claude to approve)`" / "run `claude mcp reset-project-choices`" |
| CC-HK | https://code.claude.com/docs/en/hooks | "Type `/hooks` in Claude Code to open a read-only browser for your configured hooks." |
| CC-SUB | https://code.claude.com/docs/en/sub-agents | "Running `/agents` prints a reminder to ask Claude or edit `.claude/agents/` and `~/.claude/agents/` directly." |
| CC-PL | https://code.claude.com/docs/en/plugins-reference | "`claude plugin list` and the `/plugin` interface then show the warning …" / "the `/plugin` **Errors** tab shows …" |

**02 매트릭스와 달라진 점 (2026-11-08):**
- Claude Code 메모리 확인 방법이 바뀌었다. 문서는 이제 `/memory`가 아니라 `/context all`의 **Memory files**를 쓰라고 한다. 메모리 문서에는 `/memory`가 나오지 않는다.
- Claude Code의 `/agents`는 최신 버전에서 목록을 보여 주지 않는다.
- Codex 플러그인 문서에는 설치된 플러그인을 나열하는 명령이 없다(`codex plugin marketplace list`는 마켓플레이스 목록이다). 키트 카탈로그에 Codex 플러그인이 없으므로 이 점검표에서는 다루지 않는다.
