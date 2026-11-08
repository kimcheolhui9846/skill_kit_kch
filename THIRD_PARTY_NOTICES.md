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

### Added 2026-11-08 (step 3): MCP servers and Claude Code plugins

All off by default; the kit writes a pinned entry only after `--mcp NAME` / `--plugin NAME` and runs none of them.

| Catalog entry | Repository | Commit | Version | License |
|---|---|---|---|---|
| mcp `codebase-memory` (`uvx codebase-memory-mcp==0.12.1`) | https://github.com/DeusData/codebase-memory-mcp | a7158ac2f48ca646b4527341b76f930f2aeff87e | 0.12.1 | MIT |
| mcp `markitdown` (`uvx markitdown-mcp==0.0.1a8`) | https://github.com/microsoft/markitdown | 21d9c1d01ecc12538dab19811fd247ef2f96ef60 | 0.0.1a8 | MIT |
| mcp `inspo` (`npx -y inspo-mcp@0.2.0`) | https://github.com/Nutlope/inspo | 022f80977c1e84d86284b17c928ab4b29f37f3ed | 0.2.0 | MIT |
| mcp `rea` (`npx -y rea-agents@6.8.0 mcp`) | https://github.com/morluto/rea | 160d821ac9a0310afcb8d1fc427862dd6508add5 | 6.8.0 | MIT |
| plugin `filetree` | https://github.com/data-goblin/claude-code-filetree | a3d36b1a56c0d982b307a58ef88fd3e857c977e6 | 0.8.2 | MIT |
| plugin `replay-theater` (`claude-code/mods/replay-theater`) | https://github.com/anthropics/claude-code-playground | 569c5283d9a0a7ee7938df85bb32e4f48cbb8c86 | 0.1.0 | Apache-2.0 |
| plugin `savvy-progress` (`plugins/savvy-progress`) | https://github.com/JohnnyVizz/claude-kit | c871c153ead54ad9547cc717d0f3e5a676c73986 | 1.2.1 | MIT |
| plugin `effortless` | https://github.com/HeyCubit/effortless | 7912a6ccdf0a562274a74f1f06f1306722c163db | 1.72.0 | MIT |

<!-- kit-source:begin k-dense-ai-scientific-agent-skills -->
### K-Dense-AI/scientific-agent-skills — experimental-design, exploratory-data-analysis, pytorch-lightning, scientific-critical-thinking, scikit-learn, statistical-analysis, statistical-power

- Repository: https://github.com/K-Dense-AI/scientific-agent-skills
- Commit: a25cf9ec00e2745d03f8704acf6f6919694ccd9a
- License: MIT, in `third_party/K-Dense-AI-scientific-agent-skills/LICENSE.md` (installed with the skill)
- Used verbatim: `skills/experimental-design`, `skills/exploratory-data-analysis`, `skills/pytorch-lightning`, `skills/scientific-critical-thinking`, `skills/scikit-learn`, `skills/statistical-analysis`, `skills/statistical-power`
- Added by `kit source add` (2026-11-06).
<!-- kit-source:end k-dense-ai-scientific-agent-skills -->

<!-- kit-source:begin emilkowalski-skills -->
### emilkowalski/skills — animate, animate-expo, animation-performance, animation-vocabulary, apple-design, ask-sonner, break-ui, choreograph, find-animation-opportunities, improve-animations, mobile-native, pick-ui-library, prototype, remove-animations, review-animations, write-swift

- Repository: https://github.com/emilkowalski/skills
- Commit: c8a79627b59d72d764d6ab6f2c87c09a48169833
- License: MIT, in `third_party/emilkowalski-skills/LICENSE` (installed with the skill)
- Used verbatim: `skills/animate`, `skills/animate-expo`, `skills/animation-performance`, `skills/animation-vocabulary`, `skills/apple-design`, `skills/ask-sonner`, `skills/break-ui`, `skills/choreograph`, `skills/find-animation-opportunities`, `skills/improve-animations`, `skills/mobile-native`, `skills/pick-ui-library`, `skills/prototype`, `skills/remove-animations`, `skills/review-animations`, `skills/write-swift`
- Added by `kit source add` (2026-11-08).
<!-- kit-source:end emilkowalski-skills -->

<!-- kit-source:begin mattpocock-skills -->
### mattpocock/skills — domain-modeling, to-spec, handoff

- Repository: https://github.com/mattpocock/skills
- Commit: 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- License: MIT, in `third_party/mattpocock-skills/LICENSE` (installed with the skill)
- Used verbatim: `skills/engineering/domain-modeling`, `skills/engineering/to-spec`, `skills/productivity/handoff`
- Added by `kit source add` (2026-11-08).
<!-- kit-source:end mattpocock-skills -->

<!-- kit-source:begin dietrichgebert-ponytail -->
### DietrichGebert/ponytail — ponytail, ponytail-audit, ponytail-debt, ponytail-gain, ponytail-review

- Repository: https://github.com/DietrichGebert/ponytail
- Commit: 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846
- License: MIT, in `third_party/DietrichGebert-ponytail/LICENSE` (installed with the skill)
- Used verbatim: `skills/ponytail`, `skills/ponytail-audit`, `skills/ponytail-debt`, `skills/ponytail-gain`, `skills/ponytail-review`
- Added by `kit source add` (2026-11-08).
<!-- kit-source:end dietrichgebert-ponytail -->

<!-- kit-source:begin affaan-m-ecc -->
### affaan-m/ECC — accessibility, api-design, architecture-decision-records, database-migrations, error-handling, python-testing, regex-vs-llm-structured-text

- Repository: https://github.com/affaan-m/ECC
- Commit: d2ef2680594f9a17526a6e1a2e18b3d242c5d17b
- License: MIT, in `third_party/affaan-m-ECC/LICENSE` (installed with the skill)
- Used verbatim: `skills/accessibility`, `skills/api-design`, `skills/architecture-decision-records`, `skills/database-migrations`, `skills/error-handling`, `skills/python-testing`, `skills/regex-vs-llm-structured-text`
- Added by `kit source add` (2026-11-08).
<!-- kit-source:end affaan-m-ecc -->

<!-- kit-source:begin cloudflare-skills -->
### cloudflare/skills — agents-sdk, cloudflare-app-bootstrap, cloudflare-one-migrations, durable-objects, frameworks-on-cloudflare, k2, sandbox-migrate-to-next, sandbox-next, sandbox-stable, workers-best-practices, workers-development, workers-profiling, wrangler

- Repository: https://github.com/cloudflare/skills
- Commit: 6eb6c781aa9b6438e0c7307bd102788a75fe1a6d
- License: Apache-2.0, in `third_party/cloudflare-skills/LICENSE` (installed with the skill)
- Used verbatim: `skills/agents-sdk`, `skills/cloudflare-app-bootstrap`, `skills/cloudflare-one-migrations`, `skills/durable-objects`, `skills/frameworks-on-cloudflare`, `skills/k2`, `skills/sandbox-migrate-to-next`, `skills/sandbox-next`, `skills/sandbox-stable`, `skills/workers-best-practices`, `skills/workers-development`, `skills/workers-profiling`, `skills/wrangler`
- Added by `kit source add` (2026-11-08).
<!-- kit-source:end cloudflare-skills -->
