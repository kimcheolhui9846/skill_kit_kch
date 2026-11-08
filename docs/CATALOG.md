# 카탈로그

<!-- devtools/make_catalog_doc.py가 만든다. 손으로 고치지 않는다. -->

키트가 설치할 수 있는 스킬, MCP 서버, 플러그인, 수동 도구의 목록이다. 다시 만들려면 `uv run python devtools/make_catalog_doc.py`를 실행한다(네트워크 없음).

## 1. 스킬 (`catalog/skills.json`)

38개. 출처 `kit`은 이 저장소의 스킬이고, `source:`는 `third_party/`에 고정 커밋으로 들여온 외부 스킬이다(라이선스는 `THIRD_PARTY_NOTICES.md`, 해시는 `sources.lock.json`).

| 스킬 | 출처 | 에이전트 | 팩 | 정책 |
|---|---|---|---|---|
| `add-skill-source` | kit | codex, claude | - | standard |
| `algorithm-optimizer` | kit | codex, claude | core | restricted, standard |
| `algorithm-options` | kit | codex, claude | core | restricted, standard |
| `benchmark` | kit | codex, claude | core | restricted, standard |
| `brainstorming` | source:superpowers-workflow | codex, claude | workflow | standard |
| `codebase-explorer` | kit | codex, claude | core | restricted, standard |
| `counterexample-hunter` | kit | codex, claude | core | restricted, standard |
| `data-quality-validator` | kit | codex, claude | core | standard |
| `design-review` | kit | codex, claude | core | restricted, standard |
| `emil-design-eng` | source:emil-design-eng | codex, claude | web, fullstack | standard |
| `executing-plans` | source:superpowers-workflow | codex, claude | workflow | standard |
| `experimental-design` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `exploratory-data-analysis` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `finishing-a-development-branch` | source:superpowers-workflow | codex, claude | workflow | standard |
| `frontend-design` | source:anthropics-frontend-design | codex, claude | web, fullstack | standard |
| `implementation-review` | kit | codex, claude | core | restricted, standard |
| `karpathy-guidelines` | source:karpathy-guidelines | codex, claude | core | standard |
| `launch-compliance-check` | kit | codex, claude | web, fullstack, launch | standard |
| `pytorch-lightning` | source:k-dense-ai-scientific-agent-skills | codex, claude | research | standard |
| `receiving-code-review` | source:superpowers-core | codex, claude | core | standard |
| `requesting-code-review` | source:superpowers-core | codex, claude | core | standard |
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
| `using-git-worktrees` | source:superpowers-workflow | codex, claude | workflow | standard |
| `verification-before-completion` | source:superpowers-core | codex, claude | core | standard |
| `web-design-guidelines` | kit | codex, claude | web, fullstack | standard |
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

## 4. 플러그인 (`catalog/plugins.json`)

모두 기본으로 꺼져 있다. `--plugin NAME`으로 켜면 선언을 쓰고, 네트워크를 허용하면 에이전트 CLI로 이 PC에 설치한다.

| 플러그인 | 에이전트 | 정책 | 위험도 | 라이선스 | 꺼진 이유 |
|---|---|---|---|---|---|
| `security-guidance` | claude | standard | high | Apache-2.0 | its hooks create ~/.claude/security/agent-sdk-venv and pip-install the Agent SDK at session start, and send git diffs to the Anthropic API on stop (ANTHROPIC_API_KEY or your Claude Code sign-in). Opt in with --plugin security-guidance |

## 5. 수동 도구 (`catalog/manual.json`)

키트는 실행하지 않는다. `--manual NAME`은 절차와 위험만 출력한다.

| 도구 | 에이전트 | 정책 | 위험도 | 요약 |
|---|---|---|---|---|
| `claude-code-router` | claude | standard | high | local gateway that sends Claude Code requests to other model providers (07_SOURCES_EVALUATION U-23) |
