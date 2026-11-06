"""P4-T6 new profiles and the policy axis.

TC-PRF-02 (PROF-001), legacy profiles unchanged (COMPAT-003), TC-POL-01..04 (POL-001..004),
ADR-015 (hackathon + standard warns; hackathon + restricted renders the legacy rules).
"""

from __future__ import annotations

import io
import json
import re

import pytest

from kit import policy_render
from kit import profile_resolver as pr
from kit.adapters import registry
from kit.app import run
from kit.model import EXIT_READY, EXIT_USAGE, UsageError
from kit.plan import kit_policy_text
from kit.profiles import ProfileError, available_profiles, load_profile

V1 = ["core", "data", "full", "python", "web"]
CORE_REQUIRED = ["task-router", "tdd-automator", "algorithm-optimizer", "submission-validator"]
LEGACY_11 = sorted(load_profile(pr.Path(__file__).parents[2], "core").skills)
STANDARD_CORE = sorted(
    set(LEGACY_11) - {"tdd-automator", "submission-validator"}
    | {
        "test-driven-development",
        "verification-before-completion",
        "requesting-code-review",
        "receiving-code-review",
        "karpathy-guidelines",
    }
)
WEB_DESIGN = ["emil-design-eng", "frontend-design", "web-design-guidelines"]
# U-40 research pack (K-Dense-AI/scientific-agent-skills, reviewer approval 2026-11-06)
RESEARCH = [
    "experimental-design",
    "exploratory-data-analysis",
    "pytorch-lightning",
    "scientific-critical-thinking",
    "scikit-learn",
    "statistical-analysis",
    "statistical-power",
]

# resolution snapshot: order, tools, MCP, required skills (same for both agents)
SNAPSHOT = {
    "fullstack": (
        ["core", "python", "web", "hitl", "fullstack"],
        ["pytest", "ruff", "node-project"],
        ["sequential-thinking"],
        CORE_REQUIRED,
    ),
    "ai-research": (
        ["core", "python", "data", "hitl", "research", "ai-research"],
        ["pytest", "ruff", "numpy", "pandas"],
        ["sequential-thinking"],
        CORE_REQUIRED + ["benchmark", "algorithm-options"],
    ),
    "hackathon": (
        ["core", "hitl", "hackathon"],
        [],
        [],
        CORE_REQUIRED + ["benchmark"],
    ),
}
# skill folders installed per (profile, policy), after the catalog (packs, replaces, policies)
INSTALLED = {
    ("fullstack", "standard"): sorted(STANDARD_CORE + WEB_DESIGN),
    ("fullstack", "restricted"): LEGACY_11,
    ("ai-research", "standard"): sorted(STANDARD_CORE + RESEARCH),
    ("ai-research", "restricted"): LEGACY_11,
    ("hackathon", "standard"): STANDARD_CORE,
    ("hackathon", "restricted"): LEGACY_11,
}
HACKATHON_WARNING = "profile 'hackathon' is meant for --policy restricted"


def kit(workspace, *argv):
    out = io.StringIO()
    code = run(list(argv), cwd=workspace, out=out)
    return code, out.getvalue()


# ---------------------------------------------------------------- TC-PRF-02 new profiles


@pytest.mark.parametrize("name", sorted(SNAPSHOT))
@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_new_profile_resolution_snapshot(kit_root, name, agent):
    order, tools, mcp, required = SNAPSHOT[name]
    resolved = pr.resolve(kit_root, name)
    assert resolved.order == order and "hitl" in resolved.order
    assert resolved.nodes["hitl"].kind == "pack" and resolved.policy is None
    view = resolved.for_agent(agent)
    assert view.skipped == []
    assert [t["name"] for t in view.profile.tools] == tools
    assert view.profile.mcp == mcp
    assert view.profile.required_skills == required
    assert sorted(view.profile.skills) == LEGACY_11


@pytest.mark.parametrize("name,policy", sorted(INSTALLED))
def test_new_profile_installed_skills_snapshot(workspace, name, policy):
    code, out = kit(
        workspace, "plan", "--agent", "codex", "--profile", name, "--policy", policy, "--json"
    )
    assert code == EXIT_READY, out
    changes = json.loads(out)["agents"]["codex"]["changes"]
    found = {c["path"].split("/")[2] for c in changes if c["path"].startswith(".agents/skills/")}
    assert sorted(found) == INSTALLED[(name, policy)]


# ---------------------------------------------------------------- legacy profiles unchanged


def test_legacy_path_sees_only_the_v1_profiles(kit_root):
    assert available_profiles(kit_root) == V1
    for name in SNAPSHOT:
        with pytest.raises(UsageError, match="available: core, data, full, python, web"):
            load_profile(kit_root, name)


def test_legacy_invocation_rejects_a_v2_profile(workspace):
    code, out = kit(workspace, "--profile", "fullstack", "--dry-run")
    assert code == EXIT_USAGE


@pytest.mark.parametrize("name", V1)
def test_v1_profile_files_are_still_v1(kit_root, name):
    data = json.loads((kit_root / f"profiles/{name}.json").read_text(encoding="utf-8"))
    assert "schema" not in data


# ---------------------------------------------------------------- ADR-015 policy axis


def test_hackathon_restricted_renders_the_legacy_rules(workspace, kit_root):
    code, out = kit(
        workspace,
        "install",
        "--agent",
        "both",
        "--profile",
        "hackathon",
        "--policy",
        "restricted",
        "--offline",
    )
    assert code == EXIT_READY, out
    legacy = kit_policy_text(kit_root)
    assert "## Restrictions" in legacy
    for rel in ("AGENTS.md", "CLAUDE.md"):
        assert legacy in (workspace / rel).read_text(encoding="utf-8")
    assert "Warning:" not in out


def test_hackathon_standard_warns_in_text_and_json(workspace):
    code, out = kit(workspace, "plan", "--agent", "codex", "--profile", "hackathon")
    assert code == EXIT_READY and f"Warning:      {HACKATHON_WARNING}" in out
    code, out = kit(workspace, "plan", "--agent", "codex", "--profile", "hackathon", "--json")
    assert json.loads(out)["policy_warnings"][0].startswith(HACKATHON_WARNING)


def test_recommended_policy_is_never_forced(kit_root):
    resolved = pr.resolve(kit_root, "hackathon")
    assert resolved.policy is None
    assert resolved.policy_warnings("restricted") == []
    assert pr.resolve(kit_root, "fullstack").policy_warnings("standard") == []


def test_bad_recommended_policy_is_a_profile_error(kit):
    body = {"schema": 2, "name": "odd", "recommended_policy": "exam"}
    (kit / "profiles/odd.json").write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ProfileError, match="recommended_policy must be one of"):
        pr.load_node(kit, "odd")


# ---------------------------------------------------------------- TC-POL-01..04


PRINCIPLE = re.compile(r"^(\d+)\. ", re.M)


def standard(kit_root, agent):
    return policy_render.render(kit_root, "standard", registry.get(agent))


def test_ten_principles_in_agents_md_and_claude_md(workspace, kit_root):
    """TC-POL-01: both files, same text, from one module."""
    code, out = kit(workspace, "install", "--agent", "both", "--profile", "core", "--offline")
    assert code == EXIT_READY, out
    for rel, agent in (("AGENTS.md", "codex"), ("CLAUDE.md", "claude")):
        text = (workspace / rel).read_text(encoding="utf-8")
        assert standard(kit_root, agent) in text
        assert [int(n) for n in PRINCIPLE.findall(text)] == list(range(1, 11))
    codex = standard(kit_root, "codex").split("\n## Principles\n")[1].split("\n\n")[0]
    claude = standard(kit_root, "claude").split("\n## Principles\n")[1].split("\n\n")[0]
    assert codex == claude


def test_claude_alone_gets_the_principles(workspace):
    code, out = kit(workspace, "install", "--agent", "claude", "--profile", "core", "--offline")
    assert code == EXIT_READY, out
    assert not (workspace / "AGENTS.md").exists()
    text = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
    assert [int(n) for n in PRINCIPLE.findall(text)] == list(range(1, 11))


def test_each_rule_has_one_source(kit_root):
    """No line of a policy module is repeated in another module."""
    seen = {}
    for path in policy_render.module_paths(kit_root, "standard"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                assert line not in seen, f"{line!r} in {seen.get(line)} and {path.name}"
                seen[line] = path.name


def test_editing_one_module_changes_both_agents(kit):
    path = kit / "shared/policies/core.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nEdited once.\n", encoding="utf-8")
    for agent in ("codex", "claude"):
        assert "Edited once." in standard(kit, agent)


def test_standard_names_what_is_allowed_and_what_needs_approval(kit_root):
    """TC-POL-03."""
    text = standard(kit_root, "codex")
    allowed = next(ln for ln in text.splitlines() if ln.startswith("- Allowed:"))
    assert all(w in allowed for w in ("GitHub", "external tools", "MCP"))
    ask = next(ln for ln in text.splitlines() if ln.startswith("- Ask first:"))
    for word in ("push", "deploy", "outside service", "secrets", "global settings"):
        assert word in ask


def test_light_path_is_rendered(kit_root):
    """TC-POL-04."""
    for agent in ("codex", "claude"):
        text = standard(kit_root, agent)
        assert "\n## Light path\n" in text
        assert all(f"\n- {grade}: " in text for grade in ("L", "S", "C"))


def test_restricted_render_is_the_legacy_text_for_every_agent(kit_root):
    """TC-POL-02."""
    for agent in ("codex", "claude"):
        body = policy_render.render(kit_root, "restricted", registry.get(agent))
        assert body == kit_policy_text(kit_root)
