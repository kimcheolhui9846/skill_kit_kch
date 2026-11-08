# 전역 설정 목록 (보강 P1-T1, 읽기 전용)

- 조사일: 2026-11-05, 이 PC(Windows 11, 사용자 `00`)
- 방법: 파일 목록과 TOML/JSON **키 이름**만 읽었다. 값은 명령·인수·버전처럼 비밀이 아닌 것만 적었다. 인증 파일은 열지 않았다.
- 경로의 `~`는 사용자 홈 디렉터리다.

## 1. Codex (`~/.codex`, codex-cli 0.166.0)

### 1.1 정책 파일

| 파일 | 크기 | 비고 |
|---|---|---|
| `AGENTS.md` | 26,757 B | 공식 한도 `project_doc_max_bytes` 기본 32 KiB에 가깝다 [확인됨: learn.chatgpt.com/docs/agent-configuration/agents-md]. 백업 9개(`AGENTS.md.backup-*`)가 같은 폴더에 있다 |

`AGENTS.md`의 절 제목(머신·개인 정보 포함 여부 판단용):
User Workflow Preferences / Windows command execution / Integration Defaults / **Project Workspace Registry** / **Project: token-context-optimizer (`~\Desktop\…`)** / Cloud GPU Training Tool (runpod-hf-harness) / Global Harness Scope and Preservation / Agent Roles and Model Availability / Independent Cross-Check Provider Hierarchy / 핸드오프 및 교차 검토 운영 규칙(HANDOFF.md 템플릿 포함) / Mandatory Per-Task Workflow / Mandatory Task Review Result Template.
→ 굵게 표시한 절은 이 PC의 프로젝트 경로에 묶여 있어 이식할 때 분리하거나 템플릿화해야 한다 [가정: 내용 미열람, 제목 기준].

### 1.2 `config.toml` (6,776 B)

| 키 | 이식 판단(1차) |
|---|---|
| `model`, `model_provider`, `model_reasoning_effort`, `service_tier` | 이식 후보 |
| `developer_instructions` (문자열) | 내용 검토 필요 |
| `notify` (리스트) | 머신 경로 포함 가능 → 검토 |
| `windows.sandbox = "elevated"` | Windows 전용 → OS 조건부 |
| `desktop.*`, `tui.*`, `notice.*`, `hooks.state.*` | 앱 상태값 → 제외 |
| `features` = `goals, hooks, child_agents_md`(true), `js_repl`(false) | 이식 후보 |
| `marketplaces`: `openai-bundled`, `openai-primary-runtime` | 이식 후보(선언만) |
| `plugins`: browser, visualize, codex-app-tools, unified-computer-use, computer-use (`@openai-bundled`) / documents, pdf, spreadsheets, presentations, template-creator (`@openai-primary-runtime`) | 선언 이식 후보. computer-use 계열은 고위험 → 기본 비활성 |
| `mcp_servers.context7` | `npx -y @upstash/context7-mcp`, **버전 미고정** |
| `mcp_servers.playwright` | `~\.codex\tools\node-v24.18.0-win-x64\npx.cmd -y @playwright/mcp@latest …`, **머신 경로 + `@latest`**, `cwd` 설정 있음 |
| `mcp_servers.node_repl` | Codex 데스크톱 앱 설치 경로(`C:\Program Files\WindowsApps\OpenAI.Codex_…\node_repl.exe`), `env`/`env_vars` 있음 → **앱이 관리하는 항목, 제외** |
| `shell_environment_policy.set` | 값 검토 필요(비밀 가능성) |
| `projects` 12개 | 신뢰 경로 → **제외**(REQ-USER-004) |
| `apps` 1개(GitHub 커넥터 도구 승인 모드) | 커넥터 ID 포함 → **제외** |

### 1.3 스킬·에이전트·기타

| 위치 | 내용 | 출처 |
|---|---|---|
| `~/.codex/skills/` | `[OMX]` 접두 스킬 28개(ai-slop-cleaner, analyze, ask, autopilot, autoresearch, autoresearch-goal, best-practice-research, cancel, code-review, configure-notifications, deep-interview, design, doctor, hud, omx-setup, performance-goal, pipeline, plan, prometheus-strict, ralph, ralplan, skill, team, ultragoal, ultraqa, ultrawork, visual-ralph, wiki, worker — `superpowers` 제외 29개 디렉터리 중 28개가 OMX) | oh-my-codex [미확인: 설치 원본·버전. 전역 npm에 없음] |
| `~/.codex/skills/superpowers` | `~/.codex/superpowers/skills`로의 **심볼릭 링크** | `obra/superpowers` 커밋 `44c9b2d6e889982ac18c27d05a19fefe335194e1` [확인됨: `git rev-parse HEAD`] |
| `~/.codex/skills/.system/` | imagegen, openai-docs, review-agent, skill-creator, skill-installer | Codex 번들 → 제외 |
| `~/.codex/agents/*.toml` | 22개(+백업 2) | OMX로 보임 [가정] |
| `~/.codex/prompts/` | 37개 | OMX로 보임 [가정] |
| `~/.codex/rules/default.rules` | 1개 | 내용 검토 필요 |
| `~/.agents/skills/` | **비어 있음** | — |

**중요한 불일치:** 공식 문서가 밝힌 사용자 스킬 경로는 `$HOME/.agents/skills`이고 `~/.codex/skills`는 문서에 나오지 않는다 [확인됨: learn.chatgpt.com/docs/build-skills, 2026-11-05]. 이 PC의 스킬은 모두 `~/.codex/skills`에 있다. 0.166.0이 이 경로를 아직 읽는지는 `UNVERIFIED`다(Codex 안에서 `/skills`로 확인 필요). 간접 근거로 `docs/TEST_REPORT.md:89`에 0.166.0 실행에서 superpowers 전역 스킬이 로드됐다는 기록이 있다(superpowers는 이 PC에서 `~/.codex/skills`에만 있다). 키트의 user 범위 설치는 문서 경로(`~/.agents/skills`)를 기본으로 한다.

### 1.4 제외(레포에 절대 넣지 않음)

`auth.json`, `cap_sid`, `.sandbox-secrets/`, `installation_id`, `*.sqlite*`, `history.jsonl`, `session_index.jsonl`, `sessions/`, `archived_sessions/`, `attachments/`, `logs`, `cache/`, `.tmp/`, `tmp/`, `worktrees/`, `.codex-global-state.json*`, `sandbox.*.log`, `models_cache.json`, `mention_usage.*`, `dictation-history/`, `transcription-history.jsonl`, `computer-use/`, `factchat-temporary*`, `AGENTS.md.backup-*`, `HANDOFF.md`(작업 상태).

## 2. Claude Code (`~/.claude`, 2.1.318)

### 2.1 정책 파일

| 파일 | 크기 | 절 |
|---|---|---|
| `CLAUDE.md` | 2,694 B | 모든 프로젝트에 적용되는 규칙 / 커밋 저자는 사용자 단독이다 / git 신원 / 커밋·푸시 / 클라우드 GPU 학습: runpod-hf-harness(로컬 경로 `~\runpod-hf-harness` 포함 → 템플릿화 필요) |

### 2.2 `settings.json` (3,441 B) 키

`attribution{commit,pr}`, `model`, `enabledPlugins{superpowers@superpowers-marketplace}`, `extraKnownMarketplaces{superpowers-marketplace}`, `modelSettings{claude-opus-5-5}`, `autoUpdatesChannel`, `tui`, `theme`, `agentPushNotifEnabled`, `autoMode{environment}`.
→ `autoMode.environment` 값은 내용 검토 필요(경로·환경 서술 가능). 나머지는 이식 후보.

### 2.3 플러그인·마켓플레이스

| 항목 | 값 |
|---|---|
| 설치 플러그인 | `superpowers@superpowers-marketplace` 6.2.0, 커밋 `44c9b2d6…`(Codex 쪽과 같은 커밋) |
| 알려진 마켓플레이스 | `claude-plugins-official`(github `anthropics/claude-plugins-official`), `superpowers-marketplace`(github `obra/superpowers-marketplace`) |

### 2.4 사용자 범위 MCP (`~/.claude.json`의 `mcpServers`)

| 이름 | 형태 | 비고 |
|---|---|---|
| `playwright` | stdio, `npx @playwright/mcp@latest`, `env` 있음 | **버전 미고정** |
| `context7` | **http**, `url` + `headers` | 헤더에 API 키가 있을 가능성이 높음 → 값은 절대 이식하지 않고 `${CONTEXT7_API_KEY}` 같은 환경 변수 참조로 바꿔야 함 [가정: 헤더 값 미열람] |

`~/.claude.json`은 계정 정보와 프로젝트별 신뢰 상태도 담고 있다 [확인됨: code.claude.com/docs/en/settings]. 파일 통째로는 이식하지 않고 `mcpServers`만 추출한다.

### 2.5 스킬·기타

| 위치 | 내용 |
|---|---|
| `~/.claude/skills/synced/` | claude.ai에서 동기화된 스킬 1개(UUID 폴더). claude.ai가 관리 → 제외 |
| `~/.claude/projects/*/memory/` | 프로젝트별 자동 메모리 → 제외(대화 기록 성격) |
| 바탕화면 `프롬포트 설정/claude code/` | `global-settings.json`, `mcp-servers.json`, `project-settings.json`, `memory/` 6개 — 참고만(검토자 결정) |

### 2.6 제외

`.credentials.json`, `history.jsonl`, `sessions/`, `session-env/`, `shell-snapshots/`, `file-history/`, `paste-cache/`, `backups/`, `cache/`, `ide/`, `downloads/`, `chrome/`, `state/`, `.last-*`, `baze-settings.json`(용도 미확인), `projects/`.

## 3. 키트 설계에 주는 시사점

1. **두 에이전트가 같은 MCP(context7, playwright)를 각자 다른 형식으로 갖고 있다.** 공통 카탈로그 1개 → Codex TOML / Claude JSON 렌더링이 자연스럽다(REQ-ARCH-002와 일치).
2. **버전 미고정(`@latest`)과 머신 경로가 섞여 있다.** capture 단계에서 고정 버전과 `${HOME}` 템플릿으로 바꿔야 하고, 원문 §14.3(버전 고정)에 따라 미고정 상태로는 카탈로그에 넣지 않는다.
3. **superpowers가 양쪽에 같은 커밋으로 있다.** 사용자 목록(U-39 superpowers)과도 겹친다 → 한 출처로 관리.
4. **OMX(oh-my-codex)는 사용자 목록에 없다.** REQ-SRC-008에 따라 일반 평가 대상이며 출처 확인이 먼저다.
5. **Codex 사용자 스킬 경로 불일치**(1.3) → user 범위 설치 경로를 정하기 전에 Codex 안에서 `/skills`로 확인해야 한다.
