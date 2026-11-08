# 02 호환성 매트릭스 (P1-T4)

- 확인일: 2026-11-05. 로컬 도구: codex-cli 0.166.0, Claude Code 2.1.318
- 확인 수준: `VERIFIED-DOC`(공식 문서에 명시) / `VERIFIED-RUN`(실행해 확인) / `UNVERIFIED`
- 출처 약어
  - **CX-SK** https://learn.chatgpt.com/docs/build-skills (developers.openai.com/codex/skills에서 308 리디렉션)
  - **CX-AG** https://learn.chatgpt.com/docs/agent-configuration/agents-md
  - **CX-MCP** https://learn.chatgpt.com/docs/extend/mcp?surface=cli
  - **CX-CFG** https://learn.chatgpt.com/docs/config-file/config-advanced
  - **CX-HK** https://learn.chatgpt.com/docs/hooks
  - **CX-PL** https://developers.openai.com/plugins/build/plugins
  - **CC-SK** https://code.claude.com/docs/en/skills
  - **CC-MEM** https://code.claude.com/docs/en/memory
  - **CC-SET** https://code.claude.com/docs/en/settings
  - **CC-MCP** https://code.claude.com/docs/en/mcp
  - **CC-HK** https://code.claude.com/docs/en/hooks
  - **CC-SUB** https://code.claude.com/docs/en/sub-agents
  - **CC-PL** https://code.claude.com/docs/en/plugins-reference (매니페스트 참조)
- 문서를 다시 확인할 때는 위 URL을 같은 질문으로 다시 읽고 이 표의 "확인일"을 바꾼다.

## 1. 프로젝트 범위

| 기능 | Codex | 수준·출처 | Claude Code | 수준·출처 | 키트 설계 시사점 |
|---|---|---|---|---|---|
| 프로젝트 정책 파일 | `AGENTS.md`(그리고 `AGENTS.override.md`). 프로젝트 루트(Git 루트)부터 CWD까지 디렉터리마다 최대 1개 | VERIFIED-DOC CX-AG | `./CLAUDE.md` 또는 `./.claude/CLAUDE.md`, 개인용 `./CLAUDE.local.md`. **CLAUDE.md가 없으면 `AGENTS.md`를 대신 읽는다**(v2.1.277+) | VERIFIED-DOC CC-MEM | `--agent claude` 단독 설치에서 `CLAUDE.md`를 만들면 그 순간 Claude는 `AGENTS.md`를 읽지 않는다. `both` 설치에서는 `CLAUDE.md`가 `@AGENTS.md`를 import하거나 같은 원문을 렌더링해야 한다 |
| 정책 파일 import/계층 | import 문서화 없음. 루트→CWD로 이어 붙이고 가까운 것이 뒤에 온다. 합계 한도 `project_doc_max_bytes` 기본 32 KiB | VERIFIED-DOC CX-AG (import는 UNVERIFIED: 문서에 없음) | `@path` import, 상대 경로는 import하는 파일 기준, 최대 4단계. 코드 스팬·펜스 안은 무시. 작업 디렉터리 밖 import는 최초 1회 승인 대화상자. 파일 권장 크기 200줄 이하 | VERIFIED-DOC CC-MEM | D-04: 렌더링 방식이 두 에이전트 모두에서 확실하다. Claude 쪽은 `@AGENTS.md` import도 공식이므로 대안으로 유효하다(작업 디렉터리 안이라 승인 대화상자 없음) |
| 프로젝트 스킬 경로 | `.agents/skills/<name>/` — CWD부터 저장소 루트까지 각 디렉터리 | VERIFIED-DOC CX-SK, 로컬 0.165.0에서도 확인(`docs/ASSUMPTIONS.md`) | `.claude/skills/<name>/SKILL.md` — 시작 디렉터리부터 저장소 루트까지, 하위 디렉터리는 파일을 읽을 때 로드 | VERIFIED-DOC CC-SK | 두 위치가 다르다 → Adapter의 `skill_root()` |
| SKILL.md frontmatter | `name`, `description` 필수. 선택 폴더 `scripts/ references/ assets/ agents/`. 초기 스킬 목록 예산: 컨텍스트의 2% 또는 8,000자 | VERIFIED-DOC CX-SK | 모든 필드 선택(`description` 권장). `name` 기본값은 디렉터리 이름. `description`+`when_to_use` 합계 1,536자에서 잘림. 모르는 필드는 오류 없이 무시. 추가 필드: `disable-model-invocation`, `user-invocable`, `allowed-tools`, `context: fork`, `paths`, `hooks` 등. Claude Code 밖(Skills API 등)에서는 `name, description, license, compatibility, metadata, allowed-tools`만 허용 | VERIFIED-DOC CC-SK | 공통 원본은 `name`+`description`만 쓰면 양쪽 모두 유효하다. 현재 키트 검증(`kit/skills.py`)의 400자 상한은 두 에이전트 한도보다 엄격해서 그대로 써도 된다 |
| 에이전트 전용 스킬 메타데이터 | `agents/openai.yaml`: `interface.*`, `policy.allow_implicit_invocation`(기본 true), `dependencies.tools` | VERIFIED-DOC CX-SK | frontmatter 필드(`disable-model-invocation` 등). 별도 파일 없음 | VERIFIED-DOC CC-SK | overlay 구조(원문 D-01 권장안의 `overlays/{codex,claude}`)가 필요하다. 다만 현재 키트에는 `openai.yaml`이 **없다**(01_ANALYSIS §2 참고) |
| 상대 에이전트 경로 인식 | Codex 레포 마켓플레이스는 `.claude-plugin/marketplace.json`도 "legacy-compatible"로 읽는다. 스킬 경로로 `.claude/skills`는 문서에 없음 | VERIFIED-DOC CX-PL (스킬은 UNVERIFIED) | `.agents/skills`는 문서에 없음 | UNVERIFIED (CC-SK에 언급 없음) | `--agent both`에서 중복으로 보일 위험은 문서상 근거가 없다. **에이전트 안에서 `/skills`로 수동 확인 필요**(AGENT_LOAD_CHECK) |
| 프로젝트 MCP 파일·형식 | `.codex/config.toml`의 `[mcp_servers.<name>]`: stdio(`command` 필수, `args env env_vars cwd`), HTTP(`url`, `bearer_token_env_var`, `http_headers`), `startup_timeout_sec`(기본 10), `enabled` | VERIFIED-DOC CX-MCP | `.mcp.json`(프로젝트 루트) `{"mcpServers":{name:{command,args,env}|{type:"http",url}}}`. `type` 없으면 stdio. `${VAR}`, `${VAR:-default}` 확장 | VERIFIED-DOC CC-MCP | Claude는 JSON → D-05 JSON 키 소유 writer 필요. 기존 감사 규칙(원격 URL, 금지 키, 비밀 env 이름)을 JSON 형식으로 옮겨야 한다 |
| MCP 활성화 조건 | 프로젝트 `.codex/` 계층은 **신뢰한 프로젝트에서만** 로드 | VERIFIED-DOC CX-MCP, CX-CFG | 대화형 세션에서 `.mcp.json` 서버 사용 전 **승인 프롬프트**(`claude mcp reset-project-choices`로 초기화). `-p`·SDK에서는 묻지 않고 로드. 신뢰하지 않은 폴더에서는 커밋된 승인이 무시됨 | VERIFIED-DOC CC-MCP | 두 에이전트 모두 설치 직후에는 MCP가 비활성일 수 있다 → `UNVERIFIED`로 보고하고 수동 절차 안내(REQ-AGENT-005) |
| 플러그인 매니페스트 | 루트 `plugin.json`(이식형), OpenAI 전용은 `extensions.com.openai`. `.codex-plugin/plugin.json`은 호환 대체 | VERIFIED-DOC CX-PL | `.claude-plugin/plugin.json`(선택, `name`만 필수). 기본 레이아웃 `skills/ commands/ agents/ hooks/hooks.json .mcp.json` | VERIFIED-DOC CC-PL | 키트가 플러그인을 직접 만들지 않으면(D-10) 영향 작음 |
| 마켓플레이스·프로젝트 선언 | 레포 `.agents/plugins/marketplace.json`, 개인 `~/.agents/plugins/marketplace.json`. 활성화: `.codex/config.toml`의 `[plugins."name@market"] enabled = true`(신뢰 프로젝트만) | VERIFIED-DOC CX-PL | `.claude/settings.json`의 `enabledPlugins`, `extraKnownMarketplaces`. `extraKnownMarketplaces`는 폴더 신뢰 후에만 적용 | VERIFIED-DOC CC-SET (키 세부 형식은 settings-reference 미열람 → 값 형식 UNVERIFIED) | D-10 "선언만"이 두 에이전트 모두 공식 경로로 가능. Claude 쪽 값 형식은 Phase 2에서 settings-reference로 확인 |
| 훅 | 이벤트: SessionStart, PreModelRequest, PostModelRequest, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, UserPromptSubmit, SubagentStart, SubagentStop, Stop, Interrupt, SessionEnd. 위치: `~/.codex/hooks.json`, `config.toml [hooks]`, `<repo>/.codex/hooks.json`(신뢰 시). PreToolUse deny/exit 2로 차단, `apply_patch` 포함. "guardrail, not a complete enforcement boundary" | VERIFIED-DOC CX-HK, CX-CFG | 이벤트 30여 개(UserPromptSubmit, PreToolUse 등). 위치: user/project/local settings, 플러그인 `hooks/hooks.json`(최상위 `"hooks"` 래퍼 필수), 스킬·서브에이전트 frontmatter. PreToolUse exit 2 또는 `permissionDecision: deny`로 차단 | VERIFIED-DOC CC-HK, CC-PL | **원문 D-11의 전제가 바뀐다**: Codex에도 UserPromptSubmit/PreToolUse 훅이 있다. L2(승인 기록 훅 + 에이전트의 승인 파일 직접 쓰기 차단)를 두 에이전트 모두 opt-in으로 제공할 수 있다. UserPromptSubmit 입력에 프롬프트 원문이 들어오는지는 양쪽 모두 해당 절을 읽지 못해 UNVERIFIED → **2026-11-07 확인(VERIFIED-DOC): 양쪽 모두 `prompt` 필드**(P5-T2b) |
| 커스텀 명령 | `~/.codex/prompts/`(이 PC에 37개). 공식 문서에서 이번에 확인하지 않음 | UNVERIFIED | "Custom commands have been merged into skills." `.claude/commands/*.md`는 계속 동작, 같은 이름이면 스킬 우선 | VERIFIED-DOC CC-SK | 키트는 명령 대신 스킬만 제공한다 |
| 서브에이전트 | `~/.codex/agents/*.toml`(이 PC에 22개). 공식 문서 미확인 | UNVERIFIED | `.claude/agents/`, `~/.claude/agents/`의 Markdown+frontmatter(`name`, `description` 필수). 포크가 아닌 서브에이전트는 부모 대화를 보지 않는다. `omitClaudeMd: true`로 프로젝트 지침도 제외 가능 | VERIFIED-DOC CC-SUB | 원문 §10.5.1 블랙박스 반례 단계는 Claude에서 공식적으로 가능(대화 미상속). Codex는 UNVERIFIED → "별도 세션" 대체. **2026-11-07 확인(VERIFIED-DOC CC-SUB):** "starts with a fresh, isolated context window", `tools`는 허용 목록(생략하면 전부 상속, 아무것도 해석되지 않으면 실행 실패). P5-T5는 `tools: TodoWrite`만 둔 `.claude/agents/counterexample-blackbox.md`를 standard 설치에 넣는다. 실제 에이전트 안 로드는 UNVERIFIED(M-06) |
| 설정 우선순위 | CLI `-c` > 프로젝트 `.codex/config.toml`(루트→CWD, 가까운 것 우선, 신뢰 시) > 프로필 > 사용자 `~/.codex/config.toml`. 시스템 계층 위치는 문서에 명확하지 않음 | VERIFIED-DOC CX-CFG (시스템 계층 UNVERIFIED) | managed > CLI `--settings` > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. 리스트 키는 병합 | VERIFIED-DOC CC-SET | 키트가 쓰는 프로젝트 파일은 사용자 설정보다 우선한다 → 사용자 전역 설정을 의도치 않게 덮을 수 있음을 plan에 표시 |
| 로드 검증 방법 | TUI `/skills`, `/mcp`, `codex mcp list` | VERIFIED-DOC CX-SK, CX-MCP; `codex mcp list --json`은 기존 키트가 0.165.0에서 확인 | `/skills`, `/memory`, `/mcp`, `/status`(Setting sources), `claude mcp list`, `claude plugin validate` | VERIFIED-DOC CC-SK, CC-SET, CC-MCP, CC-PL | 비대화형 검증: Codex `codex mcp list --json`, Claude `claude mcp list`. 스킬 로드는 양쪽 모두 대화형에서만 → `Load UNVERIFIED` 유지. **2026-11-08 재확인(P6-T6):** Claude Code 메모리 문서는 이제 `/context all`의 Memory files로 확인하게 하고 `/memory`는 나오지 않는다. 최신 `/agents`는 목록 대신 안내만 출력한다. 검토자 절차는 `docs/v2/AGENT_LOAD_CHECK.md` |
| Windows 경로·제약 | 사용자 홈 `~/.codex`(`CODEX_HOME`으로 변경 가능) | VERIFIED-DOC CX-CFG | `~/.claude` = `%USERPROFILE%\.claude`(`CLAUDE_CONFIG_DIR`로 변경 가능). 플러그인 훅 경로는 대체로 슬래시 | VERIFIED-DOC CC-SET, CC-PL | 기존 키트는 심볼릭 링크를 만들지 않는다(유지). 이 PC는 심볼릭 링크 권한이 없다 [확인됨: test_fsops SKIPPED] |

## 2. 사용자 범위 (보강 REQ-USER)

| 기능 | Codex | 수준·출처 | Claude Code | 수준·출처 | 시사점 |
|---|---|---|---|---|---|
| 사용자 정책 파일 | `~/.codex/AGENTS.md`(또는 `AGENTS.override.md`, 비어 있지 않은 첫 파일만) | VERIFIED-DOC CX-AG | `~/.claude/CLAUDE.md`. 프로젝트에 AGENTS.md만 있어도 함께 로드됨 | VERIFIED-DOC CC-MEM | 관리 구간 마커로 병합 가능(기존 `agentsmd.merge` 재사용) |
| 사용자 스킬 경로 | `$HOME/.agents/skills`. **`~/.codex/skills`는 문서에 없음** | VERIFIED-DOC CX-SK / `~/.codex/skills` **VERIFIED-RUN**(2026-11-05 검토자가 Codex 0.166.0 `/skills`에서 OMX·superpowers 스킬이 보이는 것을 확인. 문서화되지 않은 호환 동작이므로 버전이 바뀌면 다시 확인). 이전 간접 근거: `docs/TEST_REPORT.md:89`(2026-11-01, 0.166.0 `codex exec`)에 "사용자 전역 Skill(superpowers)도 함께 로드됐다"고 기록됨. 이 PC에서 superpowers는 `~/.codex/skills`에만 있으므로 0.166.0이 이 경로를 아직 읽는 것으로 보이나, 문서화되지 않은 호환 동작일 수 있음 | `~/.claude/skills/<name>/` | VERIFIED-DOC CC-SK | 이 PC는 `~/.codex/skills`에만 스킬이 있다(global-inventory §1.3). 설치 경로 결정 전 `/skills` 수동 확인 필요 |
| 사용자 MCP | `~/.codex/config.toml [mcp_servers]` | VERIFIED-DOC CX-MCP | `~/.claude.json`의 `mcpServers`(user/local 범위). 이 파일은 계정·신뢰 상태도 담음 | VERIFIED-DOC CC-MCP, CC-SET | Claude 사용자 MCP는 `~/.claude.json`을 직접 고치기보다 `claude mcp add --scope user` 명령을 **출력해서 사람이 실행**하게 하는 편이 안전하다(원문 §15 "필요한 사용자 범위 작업은 명령을 출력") |
| 사용자 플러그인 | `~/.codex/config.toml [plugins."x@m"]`, `[marketplaces.*]` | VERIFIED-DOC CX-PL (marketplaces 키 형식은 로컬 파일로만 확인) | `~/.claude/settings.json`의 `enabledPlugins`, `extraKnownMarketplaces` | VERIFIED-DOC CC-SET | 선언은 설정 키로 가능하나 실제 설치(캐시 다운로드)는 에이전트가 한다 → D-10과 같은 "선언 + 안내". [확인됨 2026-11-06, 격리 홈: Claude Code 2.1.319·codex-cli 0.166.0 모두 CLI로 sha 고정 설치·제거 가능 → P4-T5에서 `--plugin` + 네트워크 게이트로 설치까지 한다, 04_DESIGN §3.6] |
| 사용자 훅 | `~/.codex/hooks.json` 또는 `config.toml [hooks]`(신뢰 불필요) | VERIFIED-DOC CX-CFG | `~/.claude/settings.json`의 `hooks` | VERIFIED-DOC CC-HK | 훅은 셸 명령 실행 → user 범위에서도 기본 비활성, opt-in |

## P4-T2 추가 확인 (2026-11-06)

`kit/skill_check.py`가 쓰는 제약이다.

| 출처 | 확인한 내용 | 수준 |
|---|---|---|
| Agent Skills 명세 (agentskills.io/specification) | `name` 1~64자, `a-z 0-9 -`만, 앞뒤 하이픈과 `--` 금지, 폴더 이름과 같아야 함. `description` 1~1024자. `compatibility` 1~500자. `metadata`는 문자열 맵. 파일 참조는 스킬 루트 기준 상대 경로. SKILL.md 500줄 이하 권장 | VERIFIED-DOC |
| Claude Code (CC-SK) | `name`의 최대 길이는 문서에 없음(기본값은 폴더 이름). `<`, `>`, 제어 문자 등은 거부. `description`+`when_to_use` 1,536자에서 잘림. 모르는 필드는 오류 없이 무시. `compatibility` 500자 이하 | VERIFIED-DOC |
| Codex (CX-SK) | `name`, `description` 필수, 길이 제한은 문서에 없음. `agents/openai.yaml`: `interface.{display_name, short_description, icon_small, icon_large, brand_color, default_prompt}`, `policy.allow_implicit_invocation`(기본 true), `dependencies.tools` | VERIFIED-DOC |

- 공통 원본에는 명세 규칙(두 에이전트의 교집합)을 오류로 적용한다. 에이전트 전용 필드가 다른 에이전트로 가면 경고와 함께 해당 에이전트 층(`codex/skills/`, `claude/skills/`)으로 옮기라고 안내한다.
