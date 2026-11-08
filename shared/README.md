# Where the kit's skills come from

A skill is built like a tree: the shared trunk goes to every agent, and each agent's
branch adds or replaces files for that agent only (`kit/catalog.py`).

| Layer | Folder | Who gets it |
|---|---|---|
| 1. base | the catalog `location`: `.agents/skills/<name>/` (the 11 original skills), `shared/skills/<name>/` (new kit skills) or `third_party/<owner>-<repo>/…` (vendored) | every agent the catalog entry lists |
| 2. overlay | `shared/skills/overlays/<name>/` | only the policies in `overlay_policies` (e.g. standard) |
| 3. agent | `codex/skills/<name>/`, `claude/skills/<name>/` | only that agent |

Rules:
- A higher layer **adds** files and **replaces** a lower file with the same path.
- `<path>.append` is **appended** to `<path>` from the layers below, e.g.
  `claude/skills/tdd-automator/SKILL.md.append` adds Claude-only lines to the shared SKILL.md.
- An agent-only skill has no `location`; all its files live in `<agent>/skills/<name>/` and the
  catalog entry lists only that agent.
- Every skill is listed in `catalog/skills.json` (name, location, agents, policies, packs). A name
  may appear twice only for policies that do not overlap (restricted: the kit's own version,
  standard: the vendored one).
- `include` adds single kit files to the base layer (e.g. the upstream `LICENSE`).
- `replaces` swaps a skill the policy cannot have for this one; `packs` adds the skill whenever
  a profile or pack of that name is selected; `requires` lists skills that must be installed
  with it (their folders are linked as `../<name>/`).
- Files under `third_party/` are byte-for-byte upstream copies pinned in `sources.lock.json`.
  The installer re-checks their sha256 before every install. Do not edit them; put kit
  additions in `shared/skills/overlays/<name>/` instead.

Installed paths: Codex reads `.agents/skills/<name>/`, Claude Code reads `.claude/skills/<name>/`.

`.agents/skills/` holds exactly the 11 original skills and is what the legacy installer
(no subcommand, shell-only mode) copies. Do not add new skills there (ADR-001).
