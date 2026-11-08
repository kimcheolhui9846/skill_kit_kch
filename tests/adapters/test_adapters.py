"""P3-T2: adapter extraction (REQ-ARCH-003/004, REQ-COMPAT-001). TC-ADP-02, TC-ADP-03."""

from __future__ import annotations

import pytest

from kit import agentsmd, mcpconfig
from kit.adapters import registry
from kit.adapters.base import BlockTarget
from kit.adapters.codex import CodexAdapter
from kit.fsops import State
from kit.model import PASS
from kit.plan import FileChange, plan_changes
from kit.profiles import load_profile
from kit.register import apply_changes
from kit.verify import verify_target
from kit.writers import markdown_block, toml_block
from tests.conftest import tree_digest


def _key(changes: list[FileChange]):
    return [(c.rel, c.owner, c.outcome, c.data, c.record, c.detail) for c in changes]


class DummyAdapter:
    """A made-up agent that only differs in paths: proves the shared code needs no edit."""

    name = "dummy"
    policy = BlockTarget("DUMMY.md", markdown_block.BEGIN, markdown_block.END)
    skill_root = ".dummy/skills"
    mcp_config = BlockTarget(".dummy/config.toml", toml_block.BEGIN, toml_block.END)

    def plan(self, target, kit_root, profile, state, include_mcp):
        return plan_changes(
            target, kit_root, profile, state, False, self.policy.rel, self.skill_root
        )

    def manual_checks(self, target):
        return []


def test_registry_returns_codex_and_rejects_unknown():
    assert isinstance(registry.get("codex"), CodexAdapter)
    assert "codex" in registry.names()
    with pytest.raises(KeyError, match="unknown agent 'nope'"):
        registry.get("nope")


@pytest.mark.parametrize("profile_name", ["core", "python", "full"])
def test_codex_plan_equals_legacy_plan(kit_root, workspace, profile_name):
    profile = load_profile(kit_root, profile_name)
    include_mcp = bool(profile.mcp)
    adapter_plan = CodexAdapter().plan(workspace, kit_root, profile, State(), include_mcp)
    legacy_plan = plan_changes(workspace, kit_root, profile, State(), include_mcp)
    assert _key(adapter_plan) == _key(legacy_plan)
    assert adapter_plan[0].rel == "AGENTS.md"
    assert all(c.rel.startswith(".agents/skills/") for c in adapter_plan[1:] if "skill:" in c.owner)


def test_plan_is_pure(kit_root, workspace, monkeypatch):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    before = tree_digest(workspace)

    def no_write(*args, **kwargs):
        raise AssertionError("plan() must not write")

    monkeypatch.setattr("kit.register._write_atomic", no_write)
    monkeypatch.setattr("pathlib.Path.write_bytes", no_write)
    monkeypatch.setattr("pathlib.Path.write_text", no_write)
    monkeypatch.setattr("pathlib.Path.mkdir", no_write)
    profile = load_profile(kit_root, "python")
    CodexAdapter().plan(workspace, kit_root, profile, State(), True)
    assert tree_digest(workspace) == before


def test_new_agent_needs_only_adapter_and_registry(kit_root, workspace):
    registry.register(DummyAdapter())
    try:
        adapter = registry.get("dummy")
        profile = load_profile(kit_root, "core")
        changes = adapter.plan(workspace, kit_root, profile, State(), False)
        assert changes[0].rel == "DUMMY.md"
        assert all(c.rel.startswith(".dummy/skills/") for c in changes[1:])
        apply_changes(workspace, changes, State(), "s", "core")
        items = verify_target(
            workspace,
            kit_root,
            profile,
            changes,
            check_writable=False,
            writable=True,
            policy_rel=adapter.policy.rel,
            skill_root=adapter.skill_root,
        )
        assert {i.verified for i in items} == {PASS}
        assert not (workspace / "AGENTS.md").exists()
        assert not (workspace / ".agents").exists()
    finally:
        registry.unregister("dummy")


def test_compat_shims_point_at_writers():
    assert agentsmd.merge is markdown_block.merge
    assert agentsmd.extract_block is markdown_block.extract_block
    assert (agentsmd.BEGIN, agentsmd.END) == (markdown_block.BEGIN, markdown_block.END)
    assert (mcpconfig.BEGIN, mcpconfig.END) == (toml_block.BEGIN, toml_block.END)
    assert mcpconfig.parse_toml is toml_block.parse_toml
