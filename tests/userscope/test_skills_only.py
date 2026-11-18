"""`--scope user --skills-only` (2026-11-17): only the profile's skills go to the home folder.

For a home that already has its own AGENTS.md/CLAUDE.md, OMX and MCP setup: those stay as they
are, nothing of them is planned (no CONFLICT), and update/verify keep the choice.
"""

from __future__ import annotations

import json

import pytest

from kit.model import EXIT_READY, EXIT_USAGE
from tests.userscope.pc_fixture import put
from tests.userscope.test_user_install import home_files, snapshot, user

OWN_RULES = "# My own rules\n"
OMX_PROMPT = "my own OMX prompt, not the kit's copy\n"
SETTINGS = {"theme": "dark"}


def _home(kit, home):
    snapshot(kit, mcp_codex=["playwright"], mcp_claude=["playwright"])
    put(home, ".codex/AGENTS.md", OWN_RULES)
    put(home, ".claude/CLAUDE.md", OWN_RULES)
    put(home, ".codex/prompts/sisyphus-lite.md", OMX_PROMPT)  # an OMX file the kit would ship
    put(home, ".codex/config.toml", '[mcp_servers.context7]\ncommand = "npx"\n')
    put(home, ".claude/settings.json", json.dumps(SETTINGS))


def _untouched(home):
    assert (home / ".codex/AGENTS.md").read_text(encoding="utf-8") == OWN_RULES
    assert (home / ".claude/CLAUDE.md").read_text(encoding="utf-8") == OWN_RULES
    assert (home / ".codex/prompts/sisyphus-lite.md").read_text(encoding="utf-8") == OMX_PROMPT
    config = (home / ".codex/config.toml").read_text(encoding="utf-8")
    assert config == '[mcp_servers.context7]\ncommand = "npx"\n'
    assert json.loads((home / ".claude/settings.json").read_text(encoding="utf-8")) == SETTINGS


def test_skills_only_writes_skills_and_nothing_else(kit, home, workspace):
    _home(kit, home)
    before = set(home_files(home))
    code, out = user(kit, workspace, "install", "--agent", "both", "--skills-only", "--yes")
    assert code == EXIT_READY, out
    _untouched(home)
    added = set(home_files(home)) - before
    assert added, out
    skill_roots = (".codex/skills/", ".claude/skills/", ".kit-state/")  # + the kit manifest
    assert [rel for rel in added if not rel.startswith(skill_roots)] == []
    assert ".codex/skills/task-router/SKILL.md" in added
    assert ".claude/skills/grounded-answer/SKILL.md" in added
    assert not any(rel.startswith(".codex/skills/ralph/") for rel in added)  # no OMX
    assert "CONFLICT" not in out
    assert "to add by hand" not in out and "MCP off (--no-mcp)" in out


def test_rerun_and_update_keep_skills_only(kit, home, workspace):
    _home(kit, home)
    code, out = user(kit, workspace, "install", "--agent", "both", "--skills-only", "--yes")
    assert code == EXIT_READY, out
    code, out = user(kit, workspace, "plan", "--agent", "both", "--skills-only")
    assert code == EXIT_READY, out
    assert "0 create, 0 update, 0 append, 0 conflict" in out  # a re-run writes nothing
    code, out = user(kit, workspace, "update", "--agent", "both", "--yes")
    assert code == EXIT_READY, out
    _untouched(home)
    code, out = user(kit, workspace, "verify", "--agent", "both")
    assert code == EXIT_READY, out


@pytest.mark.parametrize("legacy_manifest", [False, True])
def test_switching_to_skills_only_preserves_full_install(kit, home, workspace, legacy_manifest):
    snapshot(kit, mcp_codex=["playwright"], mcp_claude=["playwright"])
    put(kit, "user/codex/own/skills/my-copy/SKILL.md", "captured private skill\n")
    external = put(home, ".codex/skills/my-external/SKILL.md", "external skill\n")
    paths = (
        ".codex/AGENTS.md",
        ".codex/config.toml",
        ".codex/skills/ralph/SKILL.md",
        ".codex/skills/my-copy/SKILL.md",
        ".claude/CLAUDE.md",
        ".claude/settings.json",
    )
    code, out = user(kit, workspace, "install", "--agent", "both", "--yes")
    assert code == EXIT_READY, out
    if legacy_manifest:
        manifest = home / ".kit-state/manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in data["installs"]:
            for item in entry["files"]:
                item.pop("owner", None)
        manifest.write_text(json.dumps(data), encoding="utf-8")
    expected = {rel: (home / rel).read_bytes() for rel in paths}
    assert b"[mcp_servers.playwright]" in expected[".codex/config.toml"]

    code, out = user(kit, workspace, "plan", "--agent", "both", "--skills-only")
    assert code == EXIT_READY, out
    assert "REMOVE" not in out, out
    for command, args in [
        ("install", ("--skills-only", "--yes")),
        ("verify", ()),
        ("update", ("--yes",)),
    ]:
        code, out = user(kit, workspace, command, "--agent", "both", *args)
        assert code == EXIT_READY, out
        assert {rel: (home / rel).read_bytes() for rel in paths} == expected

    code, out = user(kit, workspace, "uninstall", "--agent", "both", "--yes")
    assert code == EXIT_READY, out
    assert all(not (home / rel).exists() for rel in paths)
    assert external.read_text(encoding="utf-8") == "external skill\n"


def test_skills_only_needs_user_scope_and_no_mcp(kit, workspace, capsys):
    from tests.userscope.pc_fixture import kit_run

    code, _ = kit_run(kit, workspace, "install", "--agent", "codex", "--skills-only")
    assert code == EXIT_USAGE
    assert "--skills-only is for --scope user" in capsys.readouterr().err
    code, _ = user(kit, workspace, "plan", "--agent", "codex", "--skills-only", "--mcp", "x")
    assert code == EXIT_USAGE
    assert "--mcp and --skills-only" in capsys.readouterr().err
