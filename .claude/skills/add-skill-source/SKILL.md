---
name: add-skill-source
description: "Use in the kit repository when the user gives a GitHub address and asks to add that skill, MCP or plugin to the kit ('이 스킬 추가', 'add this repo', '레포에 반영') - runs `kit source add` for a plan, explains it, and applies only after approval. Do NOT use to install a skill into a workspace (use kit install) or for repositories outside GitHub."
---

# Add a skill source

The kit adds outside skills only through `kit source` (ADR-021). The command pins the commit,
downloads into memory, checks license, secrets and format, and writes nothing until approved.
You explain its plan; you never copy files by hand.

## Steps

1. Ask for the address if none was given. Accepted: `owner/repo`,
   `https://github.com/owner/repo`, or `.../tree/<ref>/<path>`.
2. Get the plan:
   `python run_kit.py source add <address> [--path P]... [--pack K] --json`
   - Several skills found (exit 2): show the list and ask which (`--path`, repeatable) or `--all`.
   - Ask which pack should install it (`--pack web`, `--pack core`, ...) if the user did not say.
3. Summarise for the user, from the JSON only:
   - repository and pinned commit (first 12 characters), license and whether files are copied
     (`vendored-verbatim`) or only recorded (`referenced`);
   - files to create, scripts left out (`left_out`), and the pack;
   - `findings`: BLOCK stops the add; REVIEW needs the user's decision; WARN is information;
   - `overlap`: an existing skill that does the same job. Ask: replace it in the standard
     policy (`--replaces NAME`) or keep both (`--keep-both`).
4. Re-run with the user's choices and `--yes` only after the user says yes.
   - `--accept-risk` only when the user has read each REVIEW finding and agreed.
   - `--accept-license` only for license `other`, after the user has read the license text.
   - `--include PATH` only for a script the user has read and approved.
5. Run the tests (`uv run --offline pytest -q`) and `python run_kit.py source check`.
6. Report: source id, commit, files written, test result. Say the change is not committed.

Later: `source update <id>` takes a new commit (local edits are never overwritten),
`source remove <id>` takes a source out, `source list` shows them.

## Never

- Run, build or install anything from the downloaded repository.
- Change a license decision, a finding level, or a file under `third_party/` by hand.
- Change `.agents/skills/` or the restricted policy; new sources serve the standard policy only.
- Commit or push unless the user asks.
