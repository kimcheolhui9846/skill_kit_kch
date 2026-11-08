"""P3-T4 ClaudeAdapter (REQ-AGENT-001/002/003, REQ-SAFE-009). TC-ADP-04/05, TC-SRC-01 (MCP part)."""

from __future__ import annotations

import json

import pytest

from kit.adapters import registry
from kit.adapters.claude import ClaudeAdapter
from kit.adapters.codex import CodexAdapter
from kit.audit import audit_mcp_json
from kit.fsops import State
from kit.model import CONFLICT, FAIL, PASS, Outcome, UsageError
from kit.profiles import Profile, load_profile
from kit.register import apply_changes
from tests.conftest import TOML_PASS, tree_digest

SEQ_PTR = "/mcpServers/sequential-thinking"


def _install(adapter, kit_root, workspace, profile_name="python", state=None):
    state = state if state is not None else State.load(workspace)
    profile = load_profile(kit_root, profile_name)
    changes = adapter.plan(workspace, kit_root, profile, state, bool(profile.mcp))
    apply_changes(workspace, changes, state, "s", profile_name)
    return profile, changes, state


def _verify(adapter, kit_root, workspace, profile, changes):
    return adapter.verify(workspace, kit_root, profile, changes, True, True, bool(profile.mcp))


def test_registry_has_claude():
    assert isinstance(registry.get("claude"), ClaudeAdapter)
    assert registry.names() == ["claude", "codex"]


def test_files_land_in_documented_places(kit_root, workspace, isolated_home):
    profile, changes, _ = _install(ClaudeAdapter(), kit_root, workspace)
    files = set(tree_digest(workspace))
    assert "CLAUDE.md" in files and ".mcp.json" in files
    skills = {f for f in files if f.startswith(".claude/skills/")}
    assert len(skills) == 26
    assert {f.split("/")[2] for f in skills} == set(profile.skills)
    assert not any(f.startswith((".agents/", ".codex/")) or f == "AGENTS.md" for f in files)
    assert not (workspace / ".claude/settings.local.json").exists()
    assert not any(isolated_home.rglob("*"))  # never ~/.claude
    text = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.startswith("<!-- hackathon-kit:begin -->")
    body = (kit_root / "AGENTS.md").read_text(encoding="utf-8").strip()
    assert body in text
    mcp = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp == {
        "mcpServers": {
            "sequential-thinking": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2026.8.31"],
            }
        }
    }
    items = _verify(ClaudeAdapter(), kit_root, workspace, profile, changes)
    assert {i.verified for i in items} == {PASS}
    assert audit_mcp_json(workspace, kit_root).verified == PASS


def test_existing_claude_md_and_mcp_json_preserved(kit_root, workspace):
    (workspace / "CLAUDE.md").write_text("# My notes\n\nkeep me\n", encoding="utf-8")
    user_mcp = {"mcpServers": {"mine": {"command": "my-tool"}}, "other": True}
    (workspace / ".mcp.json").write_text(json.dumps(user_mcp, indent=4) + "\n", encoding="utf-8")
    profile, changes, _ = _install(ClaudeAdapter(), kit_root, workspace)
    outcomes = {c.rel: c.outcome for c in changes}
    assert outcomes["CLAUDE.md"] == Outcome.APPEND
    assert outcomes[".mcp.json"] == Outcome.UPDATE
    assert (
        (workspace / "CLAUDE.md").read_text(encoding="utf-8").startswith("# My notes\n\nkeep me\n")
    )
    assert (workspace / ".kit/backups/s/CLAUDE.md").read_text(encoding="utf-8") == (
        "# My notes\n\nkeep me\n"
    )
    mcp = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp["mcpServers"]["mine"] == {"command": "my-tool"} and mcp["other"] is True
    assert list(mcp["mcpServers"]) == ["mine", "sequential-thinking"]


def test_rerun_is_idempotent(kit_root, workspace):
    _install(ClaudeAdapter(), kit_root, workspace)
    before = tree_digest(workspace, exclude=(".kit/",))
    profile = load_profile(kit_root, "python")
    again = ClaudeAdapter().plan(workspace, kit_root, profile, State.load(workspace), True)
    assert {c.outcome for c in again} == {Outcome.UNCHANGED}
    _install(ClaudeAdapter(), kit_root, workspace)
    assert tree_digest(workspace, exclude=(".kit/",)) == before


def test_codex_files_untouched_by_claude_install(kit_root, workspace):
    _install(CodexAdapter(), kit_root, workspace)
    codex_files = {
        k: v
        for k, v in tree_digest(workspace).items()
        if k == "AGENTS.md" or k.startswith((".agents/", ".codex/"))
    }
    _install(ClaudeAdapter(), kit_root, workspace)
    after = tree_digest(workspace)
    assert {k: after[k] for k in codex_files} == codex_files
    profile = load_profile(kit_root, "python")
    replan = CodexAdapter().plan(workspace, kit_root, profile, State.load(workspace), True)
    assert {c.outcome for c in replan} == {Outcome.UNCHANGED}
    items = CodexAdapter().verify(workspace, kit_root, profile, replan, True, True, True)
    # Python 3.9/3.10: the TOML checks say "... needs Python 3.11+" (UNVERIFIED by design)
    assert {i.verified for i in items if "3.11+" not in i.detail} == {PASS}
    assert {i.verified for i in items if "3.11+" in i.detail} <= {TOML_PASS}


def test_mcp_outside_allowlist_is_rejected(kit_root, workspace):
    profile = Profile("x", "x", skills=[], mcp=["fetch"])
    with pytest.raises(UsageError, match="fetch"):
        ClaudeAdapter().plan(workspace, kit_root, profile, State(), True)


def test_user_server_with_kit_name_is_conflict(kit_root, workspace):
    user = {"mcpServers": {"sequential-thinking": {"command": "uvx", "args": ["mine"]}}}
    (workspace / ".mcp.json").write_text(json.dumps(user), encoding="utf-8")
    profile, changes, _ = _install(ClaudeAdapter(), kit_root, workspace)
    mcp_change = next(c for c in changes if c.rel == ".mcp.json")
    assert mcp_change.outcome == Outcome.CONFLICT
    assert json.loads((workspace / ".mcp.json").read_text(encoding="utf-8")) == user
    item = next(
        i
        for i in _verify(ClaudeAdapter(), kit_root, workspace, profile, changes)
        if i.name == "mcp-config"
    )
    assert item.verified == CONFLICT


def test_user_edit_of_kit_key_is_conflict_on_update(kit_root, workspace):
    _install(ClaudeAdapter(), kit_root, workspace)
    path = workspace / ".mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["mcpServers"]["sequential-thinking"]["args"].append("--mine")
    path.write_text(json.dumps(doc), encoding="utf-8")
    profile = load_profile(kit_root, "python")
    replan = ClaudeAdapter().plan(workspace, kit_root, profile, State.load(workspace), True)
    mcp_change = next(c for c in replan if c.rel == ".mcp.json")
    assert mcp_change.outcome == Outcome.CONFLICT and mcp_change.data is None
    item = next(
        i
        for i in ClaudeAdapter().verify(workspace, kit_root, profile, replan, True, True, True)
        if i.name == "mcp-config"
    )
    assert item.verified == CONFLICT  # the kit does not overwrite the user's edit


@pytest.mark.parametrize(
    "server,problem",
    [
        ({"type": "http", "url": "https://example.com/mcp"}, "remote"),
        ({"type": "sse", "url": "http://x"}, "remote"),
        ({"type": "http", "command": "npx", "args": []}, "transport 'http' is remote"),
        ({"command": "npx", "args": [], "headers": {"A": "b"}}, "headers"),
        ({"command": "npx", "args": [], "env": {"GITHUB_TOKEN": "x"}}, "secret-like env"),
        ({"command": "curl", "args": []}, "not allowed"),
    ],
)
def test_json_audit_applies_toml_rules(kit_root, workspace, server, problem):
    doc = {"mcpServers": {"sequential-thinking": server}}
    (workspace / ".mcp.json").write_text(json.dumps(doc), encoding="utf-8")
    item = audit_mcp_json(workspace, kit_root)
    assert item.verified == FAIL and problem in item.detail


def test_json_audit_flags_unlisted_server(kit_root, workspace):
    doc = {"mcpServers": {"other": {"command": "npx", "args": []}}}
    (workspace / ".mcp.json").write_text(json.dumps(doc), encoding="utf-8")
    assert "not in mcp/allowlist.json" in audit_mcp_json(workspace, kit_root).detail


def test_manual_checks_mention_skills_and_mcp(workspace):
    assert not any("/mcp" in s for s in ClaudeAdapter().manual_checks(workspace))
    (workspace / ".mcp.json").write_text("{}", encoding="utf-8")
    steps = ClaudeAdapter().manual_checks(workspace)
    assert any("/skills" in s for s in steps) and any("/mcp" in s for s in steps)
