"""P4-T1 skill tree: shared base + per-policy overlay + per-agent layer (D-01, ADR-001)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from kit import catalog, commands
from kit.catalog import CatalogError
from kit.model import EXIT_BLOCKED, EXIT_READY
from kit.plan import iter_skill_files
from tests.catalog.kit_fixture import write
from tests.conftest import tree_digest

LEGACY = sorted(
    [
        "algorithm-optimizer",
        "algorithm-options",
        "benchmark",
        "codebase-explorer",
        "counterexample-hunter",
        "design-review",
        "implementation-review",
        "submission-validator",
        "systematic-debugging",
        "task-router",
        "tdd-automator",
    ]
)
V22 = Path(__file__).with_name("v22_agents_skills.json")


def install(kit, workspace, *extra):
    out = io.StringIO()
    argv = ["install", "--profile", "core,demo", "--offline", *extra]
    return commands.run(argv, workspace, kit, out), out.getvalue()


# ---------------------------------------------------------------- the real catalog


REPLACED_IN_STANDARD = ["submission-validator", "systematic-debugging", "tdd-automator"]


def test_restricted_catalog_is_exactly_the_legacy_skills(kit_root):
    """V-22 / 04_DESIGN 3.6: only the 11 original skills serve the restricted policy."""
    entries = catalog.load(kit_root, "restricted")
    restricted = sorted(n for n, e in entries.items() if "restricted" in e.policies)
    assert restricted == LEGACY
    for name in restricted:
        entry = entries[name]
        assert entry.location == f".agents/skills/{name}" and entry.origin == "kit"
        assert entry.agents == ["codex", "claude"]
        expected = ["restricted"] if name in REPLACED_IN_STANDARD else ["restricted", "standard"]
        assert entry.policies == expected
    for options in catalog.load_all(kit_root).values():
        for entry in options:
            if "restricted" in entry.policies:
                assert entry.location.startswith(".agents/skills/")


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("policy", ["restricted", "standard"])
def test_layered_files_equal_the_original_for_legacy_skills(kit_root, agent, policy):
    """No agent layers exist yet, so every agent gets the original bytes ("mirror" check)."""
    source = catalog.source_for(kit_root, agent, policy)
    kept = LEGACY if policy == "restricted" else sorted(set(LEGACY) - set(REPLACED_IN_STANDARD))
    for name in kept:
        original = [(r.split("/", 3)[3], d) for r, d in iter_skill_files(kit_root, name)]
        assert source(name) == original


def test_agents_skills_unchanged_v22(kit_root):
    """V-22: .agents/skills holds the 11 original skills, byte for byte."""
    expected = json.loads(V22.read_text(encoding="utf-8"))
    actual = {
        p.relative_to(kit_root / ".agents/skills").as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted((kit_root / ".agents/skills").rglob("*"))
        if p.is_file()
    }
    assert actual == expected


# ---------------------------------------------------------------- the tree


def test_shared_and_agent_layers(kit):
    entries = catalog.load(kit)
    codex = dict(catalog.skill_files(kit, entries["tree-demo"], "codex", "standard"))
    claude = dict(catalog.skill_files(kit, entries["tree-demo"], "claude", "standard"))
    assert set(codex) == {"SKILL.md", "references/notes.md", "agents/openai.yaml"}
    assert set(claude) == {"SKILL.md", "references/notes.md"}  # .append is not a file
    assert codex["references/notes.md"] == b"shared notes\n"
    assert claude["references/notes.md"] == b"claude notes\n"  # replaced
    assert claude["SKILL.md"] == codex["SKILL.md"] + b"Claude-only line.\n"  # appended


def test_overlay_only_for_its_policy(kit):
    entry = catalog.load(kit)["benchmark"]
    standard = dict(catalog.skill_files(kit, entry, "claude", "standard"))["SKILL.md"]
    restricted = dict(catalog.skill_files(kit, entry, "claude", "restricted"))["SKILL.md"]
    assert standard.endswith(b"Standard overlay line.\n")
    assert restricted == (kit / ".agents/skills/benchmark/SKILL.md").read_bytes()


def test_install_puts_each_layer_where_it_belongs(kit, workspace):
    code, out = install(kit, workspace, "--agent", "both")
    assert code == EXIT_READY, out
    assert (workspace / ".agents/skills/tree-demo/agents/openai.yaml").is_file()
    assert not (workspace / ".claude/skills/tree-demo/agents").exists()
    claude_skill = (workspace / ".claude/skills/tree-demo/SKILL.md").read_text(encoding="utf-8")
    assert claude_skill.endswith("Claude-only line.\n")
    assert "Claude-only" not in (workspace / ".agents/skills/tree-demo/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert (workspace / ".agents/skills/codex-only/SKILL.md").is_file()
    assert not (workspace / ".claude/skills/codex-only").exists()
    assert "skipped skills: codex-only (not for claude)" in out
    assert "Skills 17/17 verified in .agents/skills/" in out  # 15 standard core + 2 demo
    assert "Skills 16/16 verified in .claude/skills/" in out  # 15 core + tree-demo
    assert not any(p.name.endswith(".append") for p in workspace.rglob("*"))


def test_layered_install_is_idempotent_verifiable_and_removable(kit, workspace):
    install(kit, workspace, "--agent", "both")
    before = tree_digest(workspace, exclude=(".kit/",))
    assert install(kit, workspace, "--agent", "both")[0] == EXIT_READY
    assert tree_digest(workspace, exclude=(".kit/",)) == before
    out = io.StringIO()
    assert commands.run(["verify", "--agent", "both", "--offline"], workspace, kit, out) == 0
    out = io.StringIO()
    assert commands.run(["uninstall", "--agent", "both"], workspace, kit, out) == EXIT_READY
    assert tree_digest(workspace, exclude=(".kit/",)) == {}


def test_editing_an_agent_layer_changes_only_that_agent(kit, workspace):
    install(kit, workspace, "--agent", "both")
    codex_before = tree_digest(workspace / ".agents")
    write(kit, "claude/skills/tree-demo/SKILL.md.append", "Claude-only line, v2.\n")
    out = io.StringIO()
    code = commands.run(["update", "--agent", "both", "--offline"], workspace, kit, out)
    assert code == EXIT_READY, out.getvalue()
    assert tree_digest(workspace / ".agents") == codex_before
    text = (workspace / ".claude/skills/tree-demo/SKILL.md").read_text(encoding="utf-8")
    assert text.endswith("Claude-only line, v2.\n")


def test_policy_filter_skips_and_reports(kit, workspace):
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    for entry in data["skills"]:
        if entry["name"] == "tree-demo":
            entry["policies"] = ["standard"]
    write(kit, "catalog/skills.json", json.dumps(data))
    code, out = install(kit, workspace, "--agent", "claude", "--policy", "restricted")
    assert code == EXIT_READY, out
    assert "skipped skills: tree-demo (not in the restricted policy)" in out
    assert not (workspace / ".claude/skills/tree-demo").exists()


def test_legacy_path_ignores_the_tree(kit, workspace, kit_root):
    """No subcommand: .agents/skills copy as before, even with layers present."""
    from kit.app import run

    out = io.StringIO()
    assert run(["--offline"], cwd=workspace, kit_root=kit, out=out) == EXIT_READY
    names = sorted(p.name for p in (workspace / ".agents/skills").iterdir())
    assert names == LEGACY


# ---------------------------------------------------------------- catalog errors


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda d: d["skills"].append(dict(d["skills"][0])), "listed twice"),
        (lambda d: d["skills"][0].update(location="nope/x"), "does not exist"),
        (lambda d: d["skills"][0].update(location="../outside"), "outside the kit"),
        (lambda d: d["skills"][0].update(agents=["gemini"]), "unknown agent"),
        (lambda d: d["skills"][0].update(policies=["loose"]), "unknown policie"),
        (lambda d: d["skills"][0].update(colour=1), "unknown field"),
        (lambda d: d["skills"][0].update(overlay_policies=["standard"]), "without overlay"),
        (lambda d: d["skills"].append({"name": "ghost", "location": None}), "no location"),
        (lambda d: d.update(schema=2), "schema 1"),
    ],
)
def test_catalog_errors(kit, change, match):
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    change(data)
    write(kit, "catalog/skills.json", json.dumps(data))
    with pytest.raises(CatalogError, match=match):
        catalog.load(kit)


def test_append_without_base_is_an_error(kit, workspace):
    write(kit, "codex/skills/tree-demo/missing.md.append", "x")
    entry = catalog.load(kit)["tree-demo"]
    with pytest.raises(CatalogError, match="nothing below to append to"):
        catalog.skill_files(kit, entry, "codex", "standard")
    code, _ = install(kit, workspace, "--agent", "codex")
    assert code == EXIT_BLOCKED
    assert not (workspace / ".agents").exists()


def test_profile_with_skill_missing_from_catalog_is_64(kit, workspace):
    write(
        kit,
        "profiles/packs/bad.json",
        json.dumps({"schema": 2, "kind": "pack", "skills": {"shared": ["zzz"]}}),
    )
    out = io.StringIO()
    argv = ["install", "--agent", "codex", "--profile", "core,bad"]
    assert commands.run(argv, workspace, kit, out) == 64
