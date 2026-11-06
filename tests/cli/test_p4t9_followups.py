"""Reviewer decisions of 2026-11-06 that followed P4-T9.

- P5-T1 8-1: a standard install that leaves out skills the policy names gets a warning.
- U-23: `--manual NAME` prints a guide from catalog/manual.json; the kit runs none of it.
- add-skill-source: the repo's own .claude/skills copy stays identical to shared/skills.
- the claude mcp add reference 'NAME=${NAME}' stays readable after masking.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import catalog, commands, mcp_catalog, policy_render
from kit.logs import mask
from kit.mcp_catalog import CatalogError
from kit.model import EXIT_READY, EXIT_USAGE
from tests.catalog.kit_fixture import write
from tests.conftest import KIT_ROOT, tree_digest

LEAVES_OUT = "the standard policy names skills this install leaves out"


def run(kit, workspace, *argv):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out), out.getvalue()


# ---------------------------------------------------------------- P5-T1 8-1


def test_a_pack_on_its_own_warns_that_the_policy_names_missing_skills(workspace):
    code, out = run(KIT_ROOT, workspace, "plan", "--agent", "both", "--profile", "hitl")
    assert code == EXIT_READY, out
    assert out.count(LEAVES_OUT) == 2  # once per agent
    assert "task-router" in out and "add --profile core" in out
    data = json.loads(
        run(KIT_ROOT, workspace, "plan", "--agent", "codex", "--profile", "hitl", "--json")[1]
    )
    assert any(LEAVES_OUT in w for w in data["agents"]["codex"]["warnings"])


@pytest.mark.parametrize("argv", [["--profile", "core,hitl"], ["--policy", "restricted"]])
def test_no_warning_when_the_skills_are_there_or_the_policy_has_no_guide(workspace, argv):
    code, out = run(KIT_ROOT, workspace, "plan", "--agent", "both", *argv)
    assert code == EXIT_READY, out
    assert LEAVES_OUT not in out


def test_only_a_policy_with_the_guide_names_skills():
    known = set(catalog.load(KIT_ROOT, "standard"))
    assert policy_render.guide_skills(KIT_ROOT, "restricted", known) == []
    assert "task-router" in policy_render.guide_skills(KIT_ROOT, "standard", known)


# ---------------------------------------------------------------- U-23 manual guides


def test_manual_guide_is_printed_and_nothing_else_happens(workspace):
    before = tree_digest(workspace, exclude=())
    argv = ("plan", "--agent", "claude", "--manual", "claude-code-router")
    code, out = run(KIT_ROOT, workspace, *argv)
    assert code == EXIT_READY, out
    assert "Manual guides (the kit runs none of this; you decide and run it):" in out
    assert "claude-code-router 3.1.3 (risk high, MIT)" in out
    assert "npm install -g @musistudio/claude-code-router@3.1.3" in out
    assert "undo:     ccr stop;" in out
    assert out.index("Manual guides") < out.index("DRY RUN")
    data = json.loads(run(KIT_ROOT, workspace, *argv, "--json")[1])
    (guide,) = data["manual_guides"]
    assert guide["name"] == "claude-code-router" and guide["risk"] == "high"
    assert tree_digest(workspace, exclude=()) == before


def test_install_with_a_manual_guide_runs_nothing(workspace, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    code, out = run(
        KIT_ROOT,
        workspace,
        "install",
        "--agent",
        "claude",
        "--manual",
        "claude-code-router",
        "--offline",
    )
    assert code == EXIT_READY, out
    assert "Manual guides" in out
    assert not any("ccr" in str(c) or "claude-code-router" in str(c) for c in calls)


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--agent", "codex", "--manual", "claude-code-router"], "not for codex"),
        (["--agent", "claude", "--manual", "nope"], "unknown manual guide 'nope'"),
        (
            ["--agent", "claude", "--manual", "claude-code-router", "--policy", "restricted"],
            "restricted",
        ),
        (["--agent", "claude", "--manual", ""], "need a name"),
    ],
)
def test_bad_manual_names_are_usage_errors(workspace, argv, message, capsys):
    before = tree_digest(workspace, exclude=())
    code, out = run(KIT_ROOT, workspace, "install", *argv)
    assert code == EXIT_USAGE
    assert message in out + capsys.readouterr().err
    assert tree_digest(workspace, exclude=()) == before  # refused before anything is written


def _manual(kit: Path, change) -> None:
    data = json.loads((kit / mcp_catalog.MANUAL_REL).read_text(encoding="utf-8"))
    change(data["tools"]["claude-code-router"])
    write(kit, mcp_catalog.MANUAL_REL, json.dumps(data))


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda e: e.pop("undo"), "missing undo"),
        (lambda e: e.update(steps=[]), "steps must be a non-empty list"),
        (lambda e: e.update(docs="http://x"), "docs must be an https://"),
        (lambda e: e.update(risk="extreme"), "risk must be one of"),
        (lambda e: e.update(credentials=[{"env": "x"}]), "UPPER_SNAKE"),
    ],
)
def test_bad_manual_catalog_is_refused(kit, change, message):
    _manual(kit, change)
    with pytest.raises(CatalogError, match=message):
        mcp_catalog.load_manual(kit)


# ---------------------------------------------------------------- add-skill-source copy


def test_repo_claude_copy_of_add_skill_source_matches_the_kit_skill():
    shared = KIT_ROOT / "shared/skills/add-skill-source"
    copy = KIT_ROOT / ".claude/skills/add-skill-source"
    files = sorted(p.relative_to(shared) for p in shared.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(copy) for p in copy.rglob("*") if p.is_file())
    for rel in files:
        assert (shared / rel).read_bytes() == (copy / rel).read_bytes(), rel


# ---------------------------------------------------------------- masking


def test_mask_keeps_environment_references_and_hides_values():
    ref = "claude mcp add -e 'CONTEXT7_API_KEY=${CONTEXT7_API_KEY}' -- npx"
    assert mask(ref) == ref
    assert mask("X_API_KEY=${X_API_KEY}") == "X_API_KEY=${X_API_KEY}"
    for value in ("X_API_KEY=${X}abc", "X_API_KEY=$X", "X_API_KEY=ctx7sk-123"):
        assert mask(value) == "X_API_KEY=***", value
