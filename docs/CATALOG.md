# 카탈로그

<!-- devtools/make_catalog_doc.py가 만든다. 손으로 고치지 않는다. -->

키트가 설치할 수 있는 스킬, MCP 서버, 플러그인, 수동 도구의 목록이다. 다시 만들려면 `uv run python devtools/make_catalog_doc.py`를 실행한다(네트워크 없음).

## 1. 스킬 (`catalog/skills.json`)

82개. 출처 `kit`은 이 저장소의 스킬이고, `source:`는 `third_party/`에 고정 커밋으로 들여온 외부 스킬이다(라이선스는 `THIRD_PARTY_NOTICES.md`, 해시는 `sources.lock.json`).

| 스킬 | 출처 | 에이전트 | 팩 | 정책 |
|---|---|---|---|---|
| `accessibility` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `add-skill-source` | kit | codex, claude | - | standard |
| `agents-sdk` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `algorithm-optimizer` | kit | codex, claude | core | restricted, standard |
| `algorithm-options` | kit | codex, claude | core | restricted, standard |
| `animate` | source:emilkowalski-skills | codex, claude | motion | standard |
| `animate-expo` | source:emilkowalski-skills | codex, claude | motion | standard |
| `animation-performance` | source:emilkowalski-skills | codex, claude | motion | standard |
| `animation-vocabulary` | source:emilkowalski-skills | codex, claude | motion | standard |
| `api-design` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `apple-design` | source:emilkowalski-skills | codex, claude | motion | standard |
| `architecture-decision-records` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `ask-sonner` | source:emilkowalski-skills | codex, claude | motion | standard |
| `benchmark` | kit | codex, claude | core | restricted, standard |
| `brainstorming` | source:superpowers-workflow | codex, claude | workflow | standard |
| `break-ui` | source:emilkowalski-skills | codex, claude | motion | standard |
| `choreograph` | source:emilkowalski-skills | codex, claude | motion | standard |
| `cloudflare-app-bootstrap` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `cloudflare-one-migrations` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `codebase-explorer` | kit | codex, claude | core | restricted, standard |
| `counterexample-hunter` | kit | codex, claude | core | restricted, standard |
| `data-quality-validator` | kit | codex, claude | core | standard |
| `database-migrations` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `design-review` | kit | codex, claude | core | restricted, standard |
| `domain-modeling` | source:mattpocock-skills | codex, claude | planning-extras | standard |
| `durable-objects` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `emil-design-eng` | source:emil-design-eng | codex, claude | web, fullstack | standard |
| `error-handling` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `executing-plans` | source:superpowers-workflow | codex, claude | workflow | standard |
| `experimental-design` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `exploratory-data-analysis` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `find-animation-opportunities` | source:emilkowalski-skills | codex, claude | motion | standard |
| `finishing-a-development-branch` | source:superpowers-workflow | codex, claude | workflow | standard |
| `frameworks-on-cloudflare` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `frontend-design` | source:anthropics-frontend-design | codex, claude | web, fullstack | standard |
| `handoff` | source:mattpocock-skills | codex, claude | planning-extras | standard |
| `implementation-review` | kit | codex, claude | core | restricted, standard |
| `improve-animations` | source:emilkowalski-skills | codex, claude | motion | standard |
| `k2` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `karpathy-guidelines` | source:karpathy-guidelines | codex, claude | core | standard |
| `launch-compliance-check` | kit | codex, claude | web, fullstack, launch | standard |
| `mobile-native` | source:emilkowalski-skills | codex, claude | motion | standard |
| `pick-ui-library` | source:emilkowalski-skills | codex, claude | motion | standard |
| `ponytail` | source:dietrichgebert-ponytail | codex, claude | lean | standard |
| `ponytail-audit` | source:dietrichgebert-ponytail | codex, claude | lean | standard |
| `ponytail-debt` | source:dietrichgebert-ponytail | codex, claude | lean | standard |
| `ponytail-gain` | source:dietrichgebert-ponytail | codex, claude | lean | standard |
| `ponytail-review` | source:dietrichgebert-ponytail | codex, claude | lean | standard |
| `prototype` | source:emilkowalski-skills | codex, claude | motion | standard |
| `python-testing` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `pytorch-lightning` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `receiving-code-review` | source:superpowers-core | codex, claude | core | standard |
| `regex-vs-llm-structured-text` | source:affaan-m-ecc | codex, claude | eng-patterns | standard |
| `remove-animations` | source:emilkowalski-skills | codex, claude | motion | standard |
| `requesting-code-review` | source:superpowers-core | codex, claude | core | standard |
| `review-animations` | source:emilkowalski-skills | codex, claude | motion | standard |
| `sandbox-migrate-to-next` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `sandbox-next` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `sandbox-stable` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `scientific-critical-thinking` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `scikit-learn` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `session-recovery` | kit | codex, claude | core | standard |
| `statistical-analysis` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `statistical-power` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `subagent-driven-development` | source:superpowers-workflow | codex, claude | workflow | standard |
| `submission-validator` | kit | codex, claude | core | restricted |
| `systematic-debugging` | kit | codex, claude | core | restricted |
| `systematic-debugging` | source:superpowers-core | codex, claude | core | standard |
| `task-approval` | kit | codex, claude | core | standard |
| `task-router` | kit | codex, claude | core | restricted, standard |
| `tdd-automator` | kit | codex, claude | core | restricted |
| `test-driven-development` | source:superpowers-core | codex, claude | core | standard |
| `to-spec` | source:mattpocock-skills | codex, claude | planning-extras | standard |
| `using-git-worktrees` | source:superpowers-workflow | codex, claude | workflow | standard |
| `verification-before-completion` | source:superpowers-core | codex, claude | core | standard |
| `web-design-guidelines` | kit | codex, claude | web, fullstack | standard |
| `workers-best-practices` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `workers-development` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `workers-profiling` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `wrangler` | source:cloudflare-skills | codex, claude | cloudflare | standard |
| `write-swift` | source:emilkowalski-skills | codex, claude | motion | standard |
| `writing-plans` | source:superpowers-workflow | codex, claude | workflow | standard |

## 2. 프로필별 설치 스킬

`kit plan --agent both --profile P --policy X --offline --json`이 실제로 설치하겠다고 한 스킬이다. 정책이 `restricted`이면 standard 전용 스킬이 빠지고, standard에서는 `tdd-automator`·`submission-validator` 대신 `test-driven-development`·`verification-before-completion`이 들어간다. restricted에서 standard 전용 팩(`workflow`, `research`)을 주면 거부하지 않고 그 스킬을 건너뛴다(계획의 `skipped_skills`에 `not in the restricted policy`로 나온다). `-`는 키트가 그 조합을 거부한다는 뜻이다.

| 프로필 | restricted | standard |
|---|---|---|
| `core` | 11 | 17 |
| `python` | 11 | 17 |
| `data` | 11 | 17 |
| `web` | 11 | 21 |
| `full` | 11 | 17 |
| `hackathon` | 11 | 17 |
| `fullstack` | 11 | 21 |
| `ai-research` | 11 | 24 |
| `core,workflow` | 11 | 23 |
| `core,research` | 11 | 24 |
| `core,eng-patterns` | 11 | 24 |
| `core,lean` | 11 | 22 |
| `core,cloudflare` | 11 | 30 |
| `core,motion` | 11 | 33 |
| `core,planning-extras` | 11 | 20 |

목록:

- `core` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `python` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `python` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `data` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `data` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `web` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `web` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, emil-design-eng, frontend-design, implementation-review, karpathy-guidelines, launch-compliance-check, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion, web-design-guidelines
- `full` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `full` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `hackathon` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `hackathon` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `fullstack` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `fullstack` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, emil-design-eng, frontend-design, implementation-review, karpathy-guidelines, launch-compliance-check, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion, web-design-guidelines
- `ai-research` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `ai-research` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, experimental-design, exploratory-data-analysis, implementation-review, karpathy-guidelines, pytorch-lightning, receiving-code-review, requesting-code-review, scientific-critical-thinking, scikit-learn, session-recovery, statistical-analysis, statistical-power, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `core,workflow` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,workflow` / standard: algorithm-optimizer, algorithm-options, benchmark, brainstorming, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, executing-plans, finishing-a-development-branch, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, subagent-driven-development, systematic-debugging, task-approval, task-router, test-driven-development, using-git-worktrees, verification-before-completion, writing-plans
- `core,research` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,research` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, experimental-design, exploratory-data-analysis, implementation-review, karpathy-guidelines, pytorch-lightning, receiving-code-review, requesting-code-review, scientific-critical-thinking, scikit-learn, session-recovery, statistical-analysis, statistical-power, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `core,eng-patterns` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,eng-patterns` / standard: accessibility, algorithm-optimizer, algorithm-options, api-design, architecture-decision-records, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, database-migrations, design-review, error-handling, implementation-review, karpathy-guidelines, python-testing, receiving-code-review, regex-vs-llm-structured-text, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `core,lean` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,lean` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, implementation-review, karpathy-guidelines, ponytail, ponytail-audit, ponytail-debt, ponytail-gain, ponytail-review, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion
- `core,cloudflare` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,cloudflare` / standard: agents-sdk, algorithm-optimizer, algorithm-options, benchmark, cloudflare-app-bootstrap, cloudflare-one-migrations, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, durable-objects, frameworks-on-cloudflare, implementation-review, k2, karpathy-guidelines, receiving-code-review, requesting-code-review, sandbox-migrate-to-next, sandbox-next, sandbox-stable, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion, workers-best-practices, workers-development, workers-profiling, wrangler
- `core,motion` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,motion` / standard: algorithm-optimizer, algorithm-options, animate, animate-expo, animation-performance, animation-vocabulary, apple-design, ask-sonner, benchmark, break-ui, choreograph, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, find-animation-opportunities, implementation-review, improve-animations, karpathy-guidelines, mobile-native, pick-ui-library, prototype, receiving-code-review, remove-animations, requesting-code-review, review-animations, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, verification-before-completion, write-swift
- `core,planning-extras` / restricted: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, design-review, implementation-review, submission-validator, systematic-debugging, task-router, tdd-automator
- `core,planning-extras` / standard: algorithm-optimizer, algorithm-options, benchmark, codebase-explorer, counterexample-hunter, data-quality-validator, design-review, domain-modeling, handoff, implementation-review, karpathy-guidelines, receiving-code-review, requesting-code-review, session-recovery, systematic-debugging, task-approval, task-router, test-driven-development, to-spec, verification-before-completion

## 3. MCP 서버 (`catalog/mcp.json`)

기본으로 켜진 것만 프로필에 따라 등록된다. 꺼진 서버는 `--mcp NAME`으로 켠다. 버전이 고정되지 않은 서버는 목록에만 있고 켤 수 없다.

| 서버 | 버전 | 정책 | 위험도 | 기본 | 네트워크 | 꺼진 이유 |
|---|---|---|---|---|---|---|
| `sequential-thinking` | 2026.8.31 | restricted, standard | low | 켜짐 | npm registry download on first start; the server itself is not expected to use the network (not verified) | - |
| `playwright` | 0.0.84 | standard | medium | 꺼짐 | npm registry download on first start; the browser reaches any site the agent opens | opens a real browser and visits any URL the agent chooses; first start downloads the package and may need browser binaries. Opt in with --mcp playwright |
| `context7` | 4.5.1 | standard | medium | 꺼짐 | npm registry download on first start; context7.com API for every lookup | sends the library names and questions the agent looks up to context7.com. Opt in with --mcp context7; works without a key (lower rate limits) |
| `fetch` | 고정 없음(목록만) | standard | high | 꺼짐 | any URL | fetches arbitrary URLs: can send task data outside the workspace. Listed only (no pinned version) |
| `git` | 고정 없음(목록만) | standard | high | 꺼짐 | git remotes | exposes git operations including remote sync; the agents already run git through the shell with approval. Listed only (no pinned version) |
| `filesystem` | 고정 없음(목록만) | standard | medium | 꺼짐 | none | duplicates the agents' own file access and widens the reachable paths. Listed only (no pinned version) |
| `codebase-memory` | 0.12.1 | standard | medium | 꺼짐 | PyPI download on first start, then the native binary from github.com/DeusData/codebase-memory-mcp releases; the index itself stays local (not verified at runtime) | indexes the whole repository; on first start it downloads a native binary from the project's GitHub Releases and keeps a background daemon and cache under ~/.cache/codebase-memory-mcp. Never run its `install` subcommand (it edits agent configs). Opt in with --mcp codebase-memory |
| `markitdown` | 0.0.1a8 | standard | high | 꺼짐 | PyPI download on first start; any URL the agent asks it to convert | alpha release; its convert tool reads any file the agent names and fetches any http(s) URL, so task data can leave the workspace. Opt in with --mcp markitdown |
| `inspo` | 0.2.0 | standard | medium | 꺼짐 | npm registry download on first start; the catalogue from Vercel Blob storage; Together AI embeddings for semantic search (only with a key); get_design_system(live) fetches the public page it is asked about | first start downloads a ~14 MB design catalogue from Vercel Blob storage; semantic search sends your queries to Together AI when TOGETHER_API_KEY is set. Never run its `install` subcommand (it writes agent configs). Opt in with --mcp inspo |
| `rea` | 6.8.0 | standard | high | 꺼짐 | npm registry download on first start; whatever model providers and tools you configure in rea (not verified at runtime) | agent runtime with 42 npm dependencies; its `rea-agents setup` command installs into your home folder and must never be run for this entry (the project-scope stdio server is `rea-agents mcp`). Opt in with --mcp rea |
| `scrapling` | 고정 없음(목록만) | standard | high | 꺼짐 | any URL; browser downloads during `scrapling install` | web scraping (sends requests to any site); its MCP server needs the Python package (v0.5.1) and `scrapling install` to download browsers before it can start, which the kit does not do. Listed only (no runnable command) |

## 4. 플러그인 (`catalog/plugins.json`)

모두 기본으로 꺼져 있다. `--plugin NAME`으로 켜면 선언을 쓰고, 네트워크를 허용하면 에이전트 CLI로 이 PC에 설치한다.

| 플러그인 | 에이전트 | 정책 | 위험도 | 라이선스 | 꺼진 이유 |
|---|---|---|---|---|---|
| `security-guidance` | claude | standard | high | Apache-2.0 | its hooks create ~/.claude/security/agent-sdk-venv and pip-install the Agent SDK at session start, and send git diffs to the Anthropic API on stop (ANTHROPIC_API_KEY or your Claude Code sign-in). Opt in with --plugin security-guidance |
| `filetree` | claude | standard | medium | MIT | Claude Code mod (IDE-style file tree pane) that runs its own code in every session; v0.8.2 needs Claude Code 2.1.306 or later. Opt in with --plugin filetree |
| `replay-theater` | claude | standard | medium | Apache-2.0 | Claude Code mod with hooks (hooks/hooks.json, replay-theater.mjs) that steps through the last turn's edits; needs Claude Code 2.1.287 or later. Opt in with --plugin replay-theater |
| `savvy-progress` | claude | standard | medium | MIT | Claude Code mod (progress bar and agents panel) that runs its own code in every session. Opt in with --plugin savvy-progress |
| `effortless` | claude | standard | high | MIT | calls Haiku on every prompt (and for every compaction) on your Claude login; its in-app Update button copies a newer version over the pinned one, bypassing the pin; a key pasted into its setup guide is stored in plain text in ~/.config/jev/.env; it needs CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 in your user settings, which the kit does not set. Opt in with --plugin effortless |

## 5. 수동 도구 (`catalog/manual.json`)

키트는 실행하지 않는다. `--manual NAME`은 절차와 위험만 출력한다.

| 도구 | 에이전트 | 정책 | 위험도 | 요약 |
|---|---|---|---|---|
| `claude-code-router` | claude | standard | high | local gateway that sends Claude Code requests to other model providers (07_SOURCES_EVALUATION U-23) |
| `headroom` | codex, claude | standard | high | context-compression proxy that wraps a coding agent and relays its model requests (07_SOURCES_EVALUATION U-08). An anonymous telemetry beacon is ON by default |
| `rtk` | codex, claude | standard | high | shell hook that rewrites the agent's Bash commands to compress their output (07_SOURCES_EVALUATION U-20). Use the Apache-2.0-only rtk-oss edition |
| `graphify` | codex, claude | standard | high | code knowledge-graph CLI and skill; installs a PreToolUse hook (Claude Code) or instruction blocks (AGENTS.md for Codex) that steer the agent to the graph (07_SOURCES_EVALUATION U-07). PyPI name is graphifyy (two y) |
| `claude-mem` | codex, claude | standard | high | session memory: hooks capture tool activity, a local worker summarises it and later sessions recall it (07_SOURCES_EVALUATION U-42). Usage analytics are ON by default; the installer auto-installs Bun and uv |
| `openrig` | codex, claude | standard | high | tmux-based multi-agent rigs (07_SOURCES_EVALUATION U-10). No native Windows: macOS, Linux or WSL2 only. Its setup writes ~/.codex and ~/.claude |
| `ruflo` | codex, claude | standard | high | orchestration platform: MCP server, hooks, background daemon and swarms (07_SOURCES_EVALUATION U-44). Upstream examples use @latest; pin 3.72.2 yourself |
| `bureau-des-agents` | claude | standard | medium | local web 'office' UI that runs and shows Claude Code agents (07_SOURCES_EVALUATION U-45). Interface in French |
| `mobbin` | claude | standard | high | remote MCP (Streamable HTTP, OAuth) with Mobbin's app screens and flows (U-35). Remote servers never go into catalog/mcp.json (§15); you add it yourself |
| `nicelydone` | claude | standard | high | remote MCP (Streamable HTTP, OAuth 2.1 with dynamic client registration) with SaaS screens and flows (U-36). The command below is Claude Code's generic form: Nicelydone shows its own wording only after sign-in (UNVERIFIED) |
| `refero` | claude | standard | high | remote MCP (HTTP) with product screens and user flows (U-37). Use OAuth: the docs also show an Authorization header with a token, which would put a secret into the MCP config, so this guide leaves it out |
