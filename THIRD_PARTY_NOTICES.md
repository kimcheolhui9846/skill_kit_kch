# Third-party notices

This file stays in the kit repository. The installer does not copy it into workspaces.

## obra/superpowers

- Repository: https://github.com/obra/superpowers
- Commit: 2ce8aa15d05bd57213e6f746f953aafb7ded7a8b
- Used:
  - `skills/systematic-debugging/SKILL.md` -> `.agents/skills/systematic-debugging/`, shortened and adapted for Codex and the exam rules (supporting files and references to other superpowers skills removed).
  - `skills/verification-before-completion/SKILL.md` -> its rules only, folded into `.agents/skills/submission-validator/SKILL.md` (fresh evidence only; checks that did not run are `NOT RUN`, never `PASS`).

```text
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Vendored sources (v2, `sources.lock.json`)

The files below are kept byte for byte under `third_party/<owner>-<repo>/` at the pinned commit.
`sources.lock.json` holds the sha256 of every file. On the new path (`--policy standard`) the
installer copies the skill folders into workspaces together with the license file named here,
so each installed copy carries its notice. Decisions: `docs/v2/07_SOURCES_EVALUATION.md`.

### obra/superpowers (v7.0.2)

- Repository: https://github.com/obra/superpowers
- Commit: 22f0b463e7a5e579904dd6211a520321035526f7
- License: MIT, Copyright (c) 2025 Jesse Vincent (text above; also `third_party/obra-superpowers/LICENSE`)
- Used verbatim: `skills/{systematic-debugging, test-driven-development, verification-before-completion, requesting-code-review, receiving-code-review}` (core, standard policy) and `skills/{brainstorming, writing-plans, executing-plans, subagent-driven-development, using-git-worktrees, finishing-a-development-branch}` (opt-in `workflow` pack). The kit appends its own section to `test-driven-development` and `verification-before-completion` SKILL.md at install time (`shared/skills/overlays/`).

### anthropics/skills — frontend-design

- Repository: https://github.com/anthropics/skills
- Commit: ca45fc496a3436251f191354091d557da31c15b5
- License: Apache License 2.0, in `third_party/anthropics-skills/skills/frontend-design/LICENSE.txt` (installed with the skill)
- Used verbatim: `skills/frontend-design/`

### emilkowalski/skills — emil-design-eng

- Repository: https://github.com/emilkowalski/skills
- Commit: c8a79627b59d72d764d6ab6f2c87c09a48169833
- License: MIT, Copyright (c) 2026 Emil Kowalski (`third_party/emilkowalski-skills/LICENSE`)
- Used verbatim: `skills/emil-design-eng/SKILL.md`

### vercel-labs/web-interface-guidelines

- Repository: https://github.com/vercel-labs/web-interface-guidelines
- Commit: 434b7f91364665f2f733b310ec54809bf8f37937
- License: MIT, Copyright (c) 2025 Vercel Labs (`third_party/vercel-labs-web-interface-guidelines/LICENSE`)
- Used verbatim: `command.md`, installed as `references/command.md` of the kit's own `web-design-guidelines` skill

### multica-ai/andrej-karpathy-skills — karpathy-guidelines

- Repository: https://github.com/multica-ai/andrej-karpathy-skills
- Commit: 2c606141936f1eeef17fa3043a72095b4765b9c2
- License: MIT as stated in the upstream README and SKILL.md frontmatter. The repository has no LICENSE file and no copyright line; see `third_party/multica-ai-andrej-karpathy-skills/LICENSE-NOTE.md` (written by the kit).
- Used verbatim: `skills/karpathy-guidelines/SKILL.md`

### Yeachan-Heo/oh-my-codex (v0.21.46)

- Repository: https://github.com/Yeachan-Heo/oh-my-codex
- Commit: f7830d0ae1b5c39cb2a86937dabfc1bdd9b7f237
- License: MIT, Copyright (c) 2026 Yeachan-Heo (`third_party/Yeachan-Heo-oh-my-codex/LICENSE`)
- Also: `user/codex/own/` holds this PC's copies of OMX files that upstream removed in commit
  b6b9141eb678 (2026-08-12): skill `prometheus-strict` and prompts `prometheus-strict-metis`,
  `prometheus-strict-momus`, `prometheus-strict-oracle`, `scholastic`, `sisyphus-lite`. Same MIT
  license; kept as the user's own (reviewer decision 2026-11-06).
- Used verbatim: `skills/`, `prompts/` (Markdown only), for the user-scope install (`install --scope user`, P4-T7). The npm package is not installed by the kit.

## Referenced, not copied (v2, `sources.lock.json`)

Nothing from these repositories is in this kit. The catalogs name them pinned to a version or
commit, and an agent fetches them only after the user opts in.

### microsoft/playwright-mcp (v0.0.84)

- Repository: https://github.com/microsoft/playwright-mcp
- Commit: be26c080edfae7c761db1e757c4aff9f6453b4d7
- License: Apache-2.0
- Used as: `catalog/mcp.json` server `playwright`, run as `npx -y @playwright/mcp@0.0.84` after `--mcp playwright`.

### upstash/context7 — @upstash/context7-mcp (4.5.1)

- Repository: https://github.com/upstash/context7
- Commit: 5e4df8d22231d5ccd5f3e24a7c08ca7643f9fffb
- License: MIT
- Used as: `catalog/mcp.json` server `context7`, run as `npx -y @upstash/context7-mcp@4.5.1` after `--mcp context7`. Optional key `CONTEXT7_API_KEY` is passed by name only.

### anthropics/claude-plugins-official — security-guidance

- Repository: https://github.com/anthropics/claude-plugins-official
- Commit: ff920a4094a341f282d5dee00daef2c3b8339c72
- License: Apache-2.0
- Used as: `catalog/plugins.json` plugin `security-guidance`, declared in `.claude/settings.json` (source pinned to the commit above) after `--plugin security-guidance`. Claude Code installs it when the user runs `/plugin install`.

<!-- kit-source:begin k-dense-ai-scientific-agent-skills -->
### K-Dense-AI/scientific-agent-skills — experimental-design, exploratory-data-analysis, pytorch-lightning, scientific-critical-thinking, scikit-learn, statistical-analysis, statistical-power

- Repository: https://github.com/K-Dense-AI/scientific-agent-skills
- Commit: a25cf9ec00e2745d03f8704acf6f6919694ccd9a
- License: MIT, in `third_party/K-Dense-AI-scientific-agent-skills/LICENSE.md` (installed with the skill)
- Used verbatim: `skills/experimental-design`, `skills/exploratory-data-analysis`, `skills/pytorch-lightning`, `skills/scientific-critical-thinking`, `skills/scikit-learn`, `skills/statistical-analysis`, `skills/statistical-power`
- Added by `kit source add` (2026-11-06).
<!-- kit-source:end k-dense-ai-scientific-agent-skills -->
