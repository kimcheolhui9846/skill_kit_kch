"""Follow-up 3 (2026-11-08, REQ-COMPAT-004, REQ-SAFE-003): install over an earlier install.

Before the fix, `install` replaced the earlier record (a v2 manifest entry, or the adopted v1
state) with the new plan's, so items the new plan dropped stayed on disk and fell out of the
record: the report said 17/17 while 19 skill folders were there, and a later uninstall left
them silently. install now uses update's rule: unchanged dropped items are removed (backed up,
inside the same transaction), edited ones are left and reported as CONFLICT.
"""

from __future__ import annotations

import json

import pytest

from kit import transaction
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY
from tests.conftest import tree_digest

MANIFEST = ".kit/state/install-manifest.json"
NOT_KIT = (".kit/",)
V1_ONLY = ("tdd-automator", "submission-validator")  # replaced on standard (P4-T4)


def skill_dirs(ws, root=".agents/skills"):
    base = ws / root
    return sorted(p.name for p in base.iterdir()) if base.is_dir() else []


def owned_files(ws):
    data = json.loads((ws / MANIFEST).read_text(encoding="utf-8"))
    return {f["path"] for e in data["installs"] for f in e["files"]}


def on_disk(ws):
    return set(tree_digest(ws, exclude=NOT_KIT))


def assert_everything_is_recorded(ws, *keep):
    """Every file the kit left under the skill folders is in the manifest."""
    for path in on_disk(ws):
        if path.startswith((".agents/skills/", ".claude/skills/")) and path not in keep:
            assert path in owned_files(ws), path


def test_v1_then_standard_install_leaves_no_v1_files(run_kit, workspace):
    run_kit("--offline")  # v1 (legacy path): 11 skills
    assert set(V1_ONLY) <= set(skill_dirs(workspace))
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_READY, out
    assert "Skills 17/17" in out
    assert len(skill_dirs(workspace)) == 17
    assert not set(V1_ONLY) & set(skill_dirs(workspace))
    assert not (workspace / ".agents/skills/systematic-debugging/examples/example.md").exists()
    assert "removed (no longer in the profile):" in out
    assert_everything_is_recorded(workspace)
    code, out = run_kit("uninstall", "--agent", "codex")
    assert code == EXIT_READY, out
    assert skill_dirs(workspace) == []


def test_the_plan_shows_the_removals_and_writes_nothing(run_kit, workspace):
    run_kit("--offline")
    before = tree_digest(workspace, exclude=())
    code, out = run_kit("plan", "--agent", "codex", "--offline")
    assert code == EXIT_READY, out
    assert "[codex] No longer in the profile:" in out
    assert "REMOVE    .agents/skills/tdd-automator/SKILL.md" in out
    code, out = run_kit("install", "--agent", "codex", "--offline", "--dry-run")
    assert "REMOVE    .agents/skills/submission-validator/SKILL.md" in out
    assert tree_digest(workspace, exclude=()) == before


def test_restricted_core_over_v1_removes_nothing(run_kit, workspace):
    run_kit("--offline")
    v1 = tree_digest(workspace, exclude=NOT_KIT)
    code, out = run_kit("install", "--agent", "codex", "--policy", "restricted", "--offline")
    assert code == EXIT_READY, out
    assert "No longer in the profile" not in out and "removed (no longer" not in out
    after = tree_digest(workspace, exclude=NOT_KIT)
    assert {k: v for k, v in after.items() if k.startswith(".agents/")} == {
        k: v for k, v in v1.items() if k.startswith(".agents/")
    }


@pytest.mark.parametrize("agent, root", [("codex", ".agents/skills"), ("claude", ".claude/skills")])
def test_a_smaller_profile_removes_what_it_dropped(run_kit, workspace, agent, root):
    run_kit("install", "--agent", agent, "--profile", "core,workflow", "--offline")
    wide = set(skill_dirs(workspace, root))
    code, out = run_kit("install", "--agent", agent, "--offline")
    assert code == EXIT_READY, out
    narrow = set(skill_dirs(workspace, root))
    assert len(wide) == 23 and len(narrow) == 17 and narrow < wide
    assert_everything_is_recorded(workspace)


def test_switching_policy_by_install(run_kit, workspace):
    run_kit("install", "--agent", "both", "--offline")
    code, out = run_kit("install", "--agent", "both", "--policy", "restricted", "--offline")
    assert code == EXIT_READY, out
    assert len(skill_dirs(workspace)) == 11
    assert len(skill_dirs(workspace, ".claude/skills")) == 11
    assert_everything_is_recorded(workspace)


def test_an_edited_dropped_file_is_left_and_reported(run_kit, workspace):
    run_kit("install", "--agent", "codex", "--profile", "core,workflow", "--offline")
    mine = workspace / ".agents/skills/brainstorming/SKILL.md"
    mine.write_text("my notes\n", encoding="utf-8")
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_PARTIAL, out
    assert "CONFLICT   optional [codex] stale:.agents/skills/brainstorming/SKILL.md" in out
    assert mine.read_text(encoding="utf-8") == "my notes\n"
    assert not (workspace / ".agents/skills/brainstorming/visual-companion.md").exists()


def test_an_edited_v1_file_the_new_plan_drops_is_reported(run_kit, workspace):
    run_kit("--offline")
    mine = workspace / ".agents/skills/tdd-automator/SKILL.md"
    mine.write_text("my tdd notes\n", encoding="utf-8")
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_PARTIAL, out
    assert "stale:.agents/skills/tdd-automator/SKILL.md" in out
    assert "differs from what the kit wrote" in out
    assert mine.read_text(encoding="utf-8") == "my tdd notes\n"
    assert not (workspace / ".agents/skills/tdd-automator/examples/example.md").exists()


def test_removed_files_come_back_from_the_backup(run_kit, workspace):
    run_kit("--offline")
    v1 = tree_digest(workspace, exclude=NOT_KIT)
    run_kit("install", "--agent", "codex", "--offline")
    stamps = sorted(p.name for p in (workspace / ".kit/backups").iterdir())
    code, out = run_kit("restore", "--backup", stamps[-1])
    assert code == EXIT_READY, out
    after = tree_digest(workspace, exclude=NOT_KIT)
    for rel in (r for r in v1 if r.startswith(".agents/skills/tdd-automator/")):
        assert after[rel] == v1[rel]


def test_a_failure_during_cleanup_rolls_everything_back(run_kit, workspace, monkeypatch):
    run_kit("--offline")
    before = tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/"))
    real = transaction.backup_file

    def flaky(target, rel, stamp):
        if rel.startswith(".agents/skills/tdd-automator/"):
            raise RuntimeError("boom")
        return real(target, rel, stamp)

    monkeypatch.setattr(transaction, "backup_file", flaky)
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_BLOCKED and "rolled back" in out
    assert "removed (no longer" not in out
    assert tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/")) == before


def test_reinstalling_the_same_profile_removes_nothing(run_kit, workspace):
    run_kit("install", "--agent", "both", "--offline")
    before = tree_digest(workspace, exclude=NOT_KIT)
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert "removed (no longer" not in out
    assert tree_digest(workspace, exclude=NOT_KIT) == before


def test_the_other_agent_keeps_its_files(run_kit, workspace):
    run_kit("install", "--agent", "both", "--profile", "core,workflow", "--offline")
    claude = {k: v for k, v in tree_digest(workspace, exclude=NOT_KIT).items() if ".claude" in k}
    run_kit("install", "--agent", "codex", "--offline")
    after = {k: v for k, v in tree_digest(workspace, exclude=NOT_KIT).items() if ".claude" in k}
    assert after == claude
    assert len(skill_dirs(workspace)) == 17


def test_partly_owned_files_lose_only_the_kit_parts(run_kit, workspace):
    """python adds an MCP server; core does not. The user's own server and text stay.

    B-3 (2026-11-08): the user's server is one the audit allows (a catalog name the kit did not
    install); a server outside the allowlist now blocks before any write
    (tests/cli/test_audit_before_write.py), so the cleanup could not be seen with one."""
    mine = {"playwright": {"command": "npx", "args": ["-y", "my-playwright@1"]}}
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": mine}, indent=2) + "\n", encoding="utf-8"
    )
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_text('model = "mine"\n', encoding="utf-8")
    run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    assert "sequential-thinking" in (workspace / ".mcp.json").read_text(encoding="utf-8")
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    servers = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert servers == mine
    assert (workspace / ".codex/config.toml").read_text(encoding="utf-8") == 'model = "mine"\n'
