"""P3-T7 update / uninstall / restore and install transactions.
REQ-INST-005/006/008, REQ-SAFE-002/005 (TC-INS-*, TC-SAF-*)."""

from __future__ import annotations

import json

import pytest

from kit import register
from kit.model import EXIT_BLOCKED, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import tree_digest

MANIFEST = ".kit/state/install-manifest.json"
NOT_KIT = (".kit/",)


def manifest(ws):
    return json.loads((ws / MANIFEST).read_text(encoding="utf-8"))


def backups(ws):
    return sorted(p.name for p in (ws / ".kit/backups").iterdir())


# ---------------------------------------------------------------- uninstall


def test_uninstall_returns_workspace_to_before(run_kit, workspace):
    (workspace / "CLAUDE.md").write_text("# mine\n\nkeep\n", encoding="utf-8")
    # B-3 (2026-11-08): a user server the audit allows (a catalog name the kit does not
    # install here); one outside the allowlist would now block the install before any write.
    mine = {"playwright": {"command": "npx", "args": ["-y", "my-playwright@1"]}}
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": mine}, indent=2) + "\n", encoding="utf-8"
    )
    (workspace / ".claude").mkdir()
    (workspace / ".claude/settings.json").write_text("{}", encoding="utf-8")
    before = tree_digest(workspace, exclude=NOT_KIT)
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    assert tree_digest(workspace, exclude=NOT_KIT) != before
    code, out = run_kit("uninstall", "--agent", "claude")
    assert code == EXIT_READY, out
    assert tree_digest(workspace, exclude=NOT_KIT) == before
    assert not (workspace / ".claude/skills").exists()  # kit-made empty dirs removed
    assert (workspace / ".claude/settings.json").is_file()  # user dir kept
    assert manifest(workspace)["installs"] == []


def test_uninstall_of_created_files_leaves_nothing(run_kit, workspace):
    run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    code, out = run_kit("uninstall", "--agent", "both")
    assert code == EXIT_READY, out
    assert tree_digest(workspace, exclude=NOT_KIT) == {}
    assert sorted(p.name for p in workspace.iterdir()) == [".kit"]


def test_codex_untouched_by_claude_install_and_uninstall(run_kit, workspace):
    run_kit("install", "--agent", "codex", "--profile", "python", "--offline")
    codex = tree_digest(workspace, exclude=NOT_KIT)
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    code, out = run_kit("uninstall", "--agent", "claude")
    assert code == EXIT_READY, out
    assert tree_digest(workspace, exclude=NOT_KIT) == codex
    assert [i["agent"] for i in manifest(workspace)["installs"]] == ["codex"]
    assert run_kit("verify", "--agent", "codex", "--offline")[0] == EXIT_READY


def test_user_modified_items_are_left_and_reported(run_kit, workspace):
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    skill = workspace / ".claude/skills/benchmark/SKILL.md"
    skill.write_text("my notes", encoding="utf-8")
    doc = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    doc["mcpServers"]["sequential-thinking"]["args"].append("--mine")
    (workspace / ".mcp.json").write_text(json.dumps(doc), encoding="utf-8")
    code, out = run_kit("uninstall", "--agent", "claude")
    assert code == EXIT_BLOCKED, out
    assert "CONFLICT   [claude] .claude/skills/benchmark/SKILL.md: changed" in out
    assert "/mcpServers/sequential-thinking: changed" in out
    assert skill.read_text(encoding="utf-8") == "my notes"
    assert json.loads((workspace / ".mcp.json").read_text(encoding="utf-8")) == doc
    assert not (workspace / "CLAUDE.md").exists()  # unchanged kit items still removed
    left = manifest(workspace)["installs"][0]
    assert [f["path"] for f in left["files"]] == [".claude/skills/benchmark/SKILL.md"]
    assert [k["pointer"] for k in left["json_keys"]] == ["/mcpServers/sequential-thinking"]
    assert left["blocks"] == []


def test_edited_kit_block_is_left(run_kit, workspace):
    run_kit("install", "--agent", "codex", "--offline")
    path = workspace / "AGENTS.md"
    path.write_text(path.read_text(encoding="utf-8").replace("## Build", "## Build!"), "utf-8")
    code, out = run_kit("uninstall", "--agent", "codex")
    assert code == EXIT_BLOCKED
    assert "AGENTS.md: kit block was edited, left in place" in out
    assert "## Build!" in path.read_text(encoding="utf-8")


def test_uninstall_dry_run_writes_nothing(run_kit, workspace):
    run_kit("install", "--agent", "both", "--offline")
    before = tree_digest(workspace, exclude=())
    code, out = run_kit("uninstall", "--agent", "both", "--dry-run")
    assert code == EXIT_READY
    assert "REMOVE    AGENTS.md  (only the kit block was left)" in out
    assert "REMOVE    .claude/skills/task-router/SKILL.md" in out
    assert tree_digest(workspace, exclude=()) == before


def test_uninstall_keeps_backups(run_kit, workspace):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    run_kit("install", "--agent", "codex", "--offline")
    first = backups(workspace)
    code, out = run_kit("uninstall", "--agent", "codex")
    assert code == EXIT_READY
    after = backups(workspace)
    assert set(first) < set(after) and len(after) == len(first) + 1
    saved = workspace / ".kit/backups" / after[-1] / ".agents/skills/task-router/SKILL.md"
    assert saved.is_file()  # removed kit files are backed up too


def test_uninstall_legacy_install(run_kit, workspace):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    run_kit("--profile", "python", "--offline")
    code, out = run_kit("uninstall", "--agent", "codex")
    assert code == EXIT_READY, out
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8") == "# mine\n"
    assert not (workspace / ".agents").exists() and not (workspace / ".codex").exists()


def test_uninstall_with_nothing_installed(run_kit):
    code, out = run_kit("uninstall", "--agent", "claude")
    assert code == EXIT_READY and "nothing installed by the kit" in out


# ---------------------------------------------------------------- update


def test_update_removes_what_the_profile_dropped(run_kit, workspace):
    run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    data = manifest(workspace)
    for entry in data["installs"]:
        entry["profiles"] = ["core"]  # as if the kit's profile had dropped the MCP server
    (workspace / MANIFEST).write_text(json.dumps(data), encoding="utf-8")
    code, out = run_kit("update", "--agent", "both", "--offline", "--dry-run")
    assert "REMOVE    .mcp.json  (only kit keys were left)" in out
    assert "UPDATE    .codex/config.toml" in out or "REMOVE    .codex/config.toml" in out
    code, out = run_kit("update", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert not (workspace / ".mcp.json").exists()
    assert not (workspace / ".codex/config.toml").exists()
    assert (workspace / ".claude/skills/task-router/SKILL.md").is_file()
    assert all(i["json_keys"] == [] for i in manifest(workspace)["installs"])


def test_update_brings_outdated_kit_files_to_this_version(run_kit, workspace):
    run_kit("install", "--agent", "claude", "--offline")
    path = workspace / ".claude/skills/benchmark/SKILL.md"
    current = path.read_bytes()
    old = b"old kit version\n"
    path.write_bytes(old)
    state = json.loads((workspace / ".kit/state.json").read_text(encoding="utf-8"))
    import hashlib

    state["files"][".claude/skills/benchmark/SKILL.md"] = hashlib.sha256(old).hexdigest()
    (workspace / ".kit/state.json").write_text(json.dumps(state), encoding="utf-8")
    code, out = run_kit("update", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    assert path.read_bytes() == current


def test_update_leaves_user_edits(run_kit, workspace):
    run_kit("install", "--agent", "claude", "--offline")
    path = workspace / ".claude/skills/task-router/SKILL.md"  # required skill
    path.write_text("mine", encoding="utf-8")
    code, out = run_kit("update", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED and "CONFLICT   required [claude] skill:task-router" in out
    assert path.read_text(encoding="utf-8") == "mine"


def test_update_without_install(run_kit):
    code, out = run_kit("update", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED and "no kit install for claude" in out


# ---------------------------------------------------------------- restore


def test_restore_puts_back_the_pre_install_file(run_kit, workspace):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    run_kit("install", "--agent", "codex", "--offline")
    stamp = backups(workspace)[0]
    before = tree_digest(workspace, exclude=())
    code, out = run_kit("restore", "--backup", stamp, "--dry-run")
    assert code == EXIT_READY and "RESTORE   AGENTS.md" in out
    assert tree_digest(workspace, exclude=()) == before
    code, out = run_kit("restore", "--backup", stamp)
    assert code == EXIT_READY, out
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8") == "# mine\n"
    newest = backups(workspace)[-1]
    assert newest != stamp and "Saved first:  .kit/backups/" in out
    assert "hackathon-kit:begin" in (workspace / ".kit/backups" / newest / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    code, out = run_kit("restore", "--backup", stamp)
    assert "Restored:     0 file(s); 1 already matched" in out


@pytest.mark.parametrize(
    "stamp,code", [("../../x", EXIT_USAGE), ("20990101-000000", EXIT_TARGET), ("latest", 64)]
)
def test_restore_bad_stamp(run_kit, stamp, code):
    assert run_kit("restore", "--backup", stamp)[0] == code


def test_restore_needs_backup_and_no_agent(run_kit):
    assert run_kit("restore")[0] == EXIT_USAGE
    assert run_kit("restore", "--backup", "20990101-000000", "--agent", "codex")[0] == EXIT_USAGE


# ---------------------------------------------------------------- transactions


@pytest.mark.parametrize("error", [OSError("disk full"), RuntimeError("bug"), KeyError("k")])
@pytest.mark.parametrize("fail_at", [1, 12, 30])
def test_exception_mid_install_rolls_back_then_converges(
    run_kit, workspace, monkeypatch, error, fail_at
):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    before = tree_digest(workspace, exclude=())
    real = register._write_atomic
    calls = {"n": 0}

    def flaky(path, data):
        calls["n"] += 1
        if calls["n"] == fail_at:
            raise error
        real(path, data)

    monkeypatch.setattr(register, "_write_atomic", flaky)
    code, out = run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "rolled back" in out
    after = tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/"))
    assert after == {k: v for k, v in before.items()}
    monkeypatch.setattr(register, "_write_atomic", real)
    code, out = run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    assert code == EXIT_READY, out


def test_exception_mid_uninstall_rolls_back(run_kit, workspace, monkeypatch):
    run_kit("install", "--agent", "claude", "--offline")
    before = tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/"))
    from kit import transaction

    real = transaction.backup_file
    calls = {"n": 0}

    def flaky(target, rel, stamp):
        calls["n"] += 1
        if calls["n"] == 5:
            raise RuntimeError("boom")
        return real(target, rel, stamp)

    monkeypatch.setattr(transaction, "backup_file", flaky)
    code, out = run_kit("uninstall", "--agent", "claude")
    assert code == EXIT_BLOCKED and "rolled back" in out
    assert tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/")) == before


@pytest.mark.parametrize("original", [b"# mine\n", b"# mine\r\n\r\nkeep\r\n", b"a\n\n\nb\n"])
def test_block_removal_gives_back_the_exact_bytes(run_kit, workspace, original):
    (workspace / "AGENTS.md").write_bytes(original)
    run_kit("install", "--agent", "codex", "--offline")
    run_kit("uninstall", "--agent", "codex")
    assert (workspace / "AGENTS.md").read_bytes() == original
