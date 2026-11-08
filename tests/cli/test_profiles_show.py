"""B-1: `kit profiles show` lists what install/plan would put in, after policy and catalog."""

from __future__ import annotations

import json

import pytest

from kit.adapters import registry
from kit.model import EXIT_PARTIAL, EXIT_READY, EXIT_USAGE
from tests.catalog.test_sources import run, skill_names
from tests.conftest import KIT_ROOT, tree_digest

PROFILES = sorted(p.stem for p in (KIT_ROOT / "profiles").glob("*.json"))
SPECS = PROFILES + ["fullstack,workflow"]


def shown(text, agent):
    """Skills, required, replaced and skipped lines of one agent block."""
    block = text.split(f"[{agent}]\n", 1)[1].split("\n\n", 1)[0]
    found = {"skills": None, "required": None, "replaced": [], "skipped": []}
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("Skills ("):
            count, names = line[len("Skills (") :].split("): ", 1)
            found["skills"] = [] if names == "-" else names.split(", ")
            assert int(count) == len(found["skills"])
        elif line.startswith("Required: "):
            names = line[len("Required: ") :]
            found["required"] = [] if names == "-" else names.split(", ")
        elif line.startswith("replaced: "):
            found["replaced"].append(line[len("replaced: ") :])
        elif line.startswith("skipped: "):
            found["skipped"].append(line[len("skipped: ") :])
    return found


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("policy", ["standard", "restricted"])
@pytest.mark.parametrize("spec", SPECS)
def test_show_lists_what_install_puts_in(kit_root, workspace, spec, policy, agent):
    argv = ("--agent", agent, "--policy", policy)
    code, text = run(kit_root, workspace, "profiles", "show", spec, *argv)
    assert code == EXIT_READY, text
    assert f"Policy: {policy}\n" in text
    listed = shown(text, agent)
    install = ("install", "--profile", spec, "--offline", "--no-mcp", "--json")
    code, out = run(kit_root, workspace, *install, *argv)
    assert code in (EXIT_READY, EXIT_PARTIAL), out
    installed = skill_names(workspace / registry.get(agent).skill_root)
    assert sorted(listed["skills"]) == installed
    data = json.loads(out)["agents"][agent]
    assert set(listed["required"]) <= set(listed["skills"])
    assert listed["replaced"] == data["replaced_skills"]
    assert listed["skipped"] == data["skipped_skills"]
    if policy == "restricted":
        assert listed["replaced"] == []


@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_replacements_only_on_standard(kit_root, workspace, agent):
    standard = run(kit_root, workspace, "profiles", "show", "core", "--agent", agent)[1]
    restricted = run(
        kit_root, workspace, "profiles", "show", "core", "--agent", agent, "--policy", "restricted"
    )[1]
    assert "  replaced: tdd-automator -> test-driven-development\n" in standard
    assert "  replaced: submission-validator -> verification-before-completion\n" in standard
    assert "replaced:" not in restricted
    assert "tdd-automator" in shown(restricted, agent)["skills"]
    assert "test-driven-development" in shown(standard, agent)["skills"]
    assert "test-driven-development" in shown(standard, agent)["required"]


def test_default_policy_is_the_install_default(kit_root, workspace):
    default = run(kit_root, workspace, "profiles", "show", "fullstack")[1]
    standard = run(kit_root, workspace, "profiles", "show", "fullstack", "--policy", "standard")
    assert standard == (EXIT_READY, default)
    plan = ("plan", "--agent", "claude", "--profile", "fullstack", "--offline", "--json")
    out = run(kit_root, workspace, *plan)[1]
    assert json.loads(out)["policy"] == "standard"
    assert "Policy: standard\n" in default
    assert "Policy: default" not in default
    assert "[codex]" in default and "[claude]" in default


@pytest.mark.parametrize(
    "argv",
    [
        ("profiles", "show", "core", "--policy", "bogus"),
        ("profiles", "list", "--policy", "standard"),
    ],
)
def test_bad_policy_is_usage_error(kit_root, workspace, argv):
    before = tree_digest(workspace, exclude=())
    assert run(kit_root, workspace, *argv)[0] == EXIT_USAGE
    assert tree_digest(workspace, exclude=()) == before


def test_show_writes_nothing(kit_root, workspace):
    before = tree_digest(kit_root / "profiles")
    code = run(kit_root, workspace, "profiles", "show", "full,workflow", "--policy", "restricted")
    assert code[0] == EXIT_READY
    assert not any(workspace.iterdir())
    assert tree_digest(kit_root / "profiles") == before
