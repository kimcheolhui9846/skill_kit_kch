"""P3-T5 profile v2 resolver. TC-PRF-01 (COMPAT-003, PROF-004), TC-PRF-03 (PROF-002),
TC-PRF-04 (PROF-003), show output (PROF-005; CLI wiring is TC-CLI-10 in P3-T6)."""

from __future__ import annotations

import json
import shutil

import pytest

from kit import profile_resolver as pr
from kit.model import UsageError
from kit.profiles import ProfileError, available_profiles, load_profile

V1 = ["core", "data", "full", "python", "web"]
V2 = ["ai-research", "fullstack", "hackathon"]  # P4-T6
SKILLS = {"a", "b", "c", "d", "e", "x"}


@pytest.fixture
def fake_kit(tmp_path, kit_root):
    """A kit root with only the files the resolver reads."""
    root = tmp_path / "kit"
    (root / "profiles/packs").mkdir(parents=True)
    (root / "mcp").mkdir()
    shutil.copy(kit_root / "mcp/allowlist.json", root / "mcp/allowlist.json")
    return root


def write(root, name, kind="profile", **data):
    folder = root / ("profiles/packs" if kind == "pack" else "profiles")
    body = {"schema": 2, **({"kind": "pack"} if kind == "pack" else {}), **data}
    (folder / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def res(root, spec, **kw):
    return pr.resolve(root, spec, skills=SKILLS, **kw)


# ---------------------------------------------------------------- TC-PRF-01 v1 == baseline


def test_v1_profiles_are_the_five_known():
    assert available_profiles(pr.Path(__file__).parents[2]) == V1


@pytest.mark.parametrize("name", V1)
@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_v1_resolution_equals_legacy_loader(kit_root, name, agent):
    legacy = load_profile(kit_root, name)
    view = pr.resolve(kit_root, name).for_agent(agent)
    assert view.profile == legacy
    assert view.skipped == [] and view.policy is None


def test_v1_normalisation_shape(kit_root):
    node = pr.load_node(kit_root, "python")
    assert node.schema == 1 and node.kind == "profile"
    assert node.extends == ["core"] and node.packs == [] and node.policy is None
    assert node.mcp == {"shared": ["sequential-thinking"]}
    assert node.skills == {"shared": []}
    assert node.agents == ["claude", "codex"]


def test_full_keeps_report_only_and_it_is_not_inherited(fake_kit, kit_root):
    for name in V1:
        shutil.copy(kit_root / f"profiles/{name}.json", fake_kit / f"profiles/{name}.json")
    write(fake_kit, "child", extends=["full"])
    assert pr.resolve(kit_root, "full").report_only is True
    assert pr.resolve(kit_root, "data").report_only is False
    known = load_core_skills()
    assert pr.resolve(fake_kit, "child", skills=known).report_only is False
    assert pr.resolve(fake_kit, "full,core", skills=known).report_only is True


def test_hitl_pack_and_default_combination(kit_root):
    resolved = pr.resolve(kit_root, "core,hitl")
    assert resolved.order == ["core", "hitl"] and resolved.nodes["hitl"].kind == "pack"
    assert resolved.for_agent("claude").profile.skills == load_profile(kit_root, "core").skills


# ---------------------------------------------------------------- TC-PRF-03 order, cycles, scalars


def test_multi_extends_order_is_left_depth_first_first_position(fake_kit):
    write(fake_kit, "base", skills={"shared": ["a", "b"]})
    write(fake_kit, "left", extends="base", skills={"shared": ["c"]})
    write(fake_kit, "right", extends=["base"], skills={"shared": ["b", "d"]})
    write(fake_kit, "top", extends=["left", "right"], skills={"shared": ["a", "e"]})
    resolved = res(fake_kit, "top")
    assert resolved.order == ["base", "left", "right", "top"]
    assert resolved.for_agent("codex").profile.skills == ["a", "b", "c", "d", "e"]


def test_combination_order_and_dedup(fake_kit):
    write(fake_kit, "p", skills={"shared": ["b", "a"]})
    write(fake_kit, "q", extends="p", skills={"shared": ["c", "a"]})
    write(fake_kit, "k", kind="pack", skills={"shared": ["d", "b"]})
    resolved = res(fake_kit, "q, k ,q")
    assert resolved.names == ["q", "k"] and resolved.label == "q,k"
    assert resolved.order == ["p", "q", "k"]
    assert resolved.for_agent("claude").profile.skills == ["b", "a", "c", "d"]
    assert resolved.description == "q + k"


def test_packs_field_is_visited_after_extends(fake_kit):
    write(fake_kit, "p", skills={"shared": ["a"]})
    write(fake_kit, "k", kind="pack", skills={"shared": ["b"]})
    write(fake_kit, "top", extends=["p"], packs=["k"], skills={"shared": ["c"]})
    assert res(fake_kit, "top").order == ["p", "k", "top"]


@pytest.mark.parametrize(
    "files,spec,match",
    [
        ({"a1": {"extends": ["a1"]}}, "a1", "cycle: a1 -> a1"),
        ({"a1": {"extends": ["b1"]}, "b1": {"extends": "a1"}}, "a1", "cycle: a1 -> b1 -> a1"),
        ({"a1": {"extends": ["nope"]}}, "a1", "unknown profile or pack 'nope'"),
        ({}, "core,missing", "unknown profile or pack"),
        ({"a1": {"skills": {"shared": ["zzz"]}}}, "a1", "unknown skill 'zzz'"),
        ({"a1": {"required_skills": {"codex": ["zzz"]}}}, "a1", "unknown skill 'zzz'"),
        ({"a1": {"mcp": {"claude": ["fetch"]}}}, "a1", "unknown MCP server 'fetch'"),
        ({"a1": {"packs": ["b1"]}, "b1": {}}, "a1", "'b1' in packs is not a pack"),
        ({}, "a1,,b1", "invalid --profile"),
        ({}, "", "invalid --profile"),
        ({}, "../profiles/core", "invalid profile name"),
        ({}, "Core", "invalid profile name"),
    ],
)
def test_reference_errors_are_usage_errors(fake_kit, files, spec, match):
    shutil.copy(pr.Path(__file__).parents[2] / "profiles/core.json", fake_kit / "profiles")
    for name, data in files.items():
        write(fake_kit, name, **data)
    with pytest.raises(UsageError, match=match):
        pr.resolve(fake_kit, spec, skills=SKILLS | {"task-router"} | load_core_skills())


def load_core_skills():
    path = pr.Path(__file__).parents[2] / "profiles/core.json"
    return set(json.loads(path.read_text(encoding="utf-8"))["skills"])


def test_diamond_is_not_a_cycle(fake_kit):
    write(fake_kit, "base")
    write(fake_kit, "l", extends="base")
    write(fake_kit, "r", extends="base")
    write(fake_kit, "top", extends=["l", "r"])
    assert res(fake_kit, "top").order == ["base", "l", "r", "top"]


def test_scalar_conflict_needs_override(fake_kit):
    write(fake_kit, "s", policy="standard")
    write(fake_kit, "r", policy="restricted")
    write(fake_kit, "n")
    with pytest.raises(UsageError, match="conflicting policy: s sets 'standard', r sets"):
        res(fake_kit, "s,r")
    assert res(fake_kit, "s,r", policy_override="restricted").policy == "restricted"
    assert res(fake_kit, "s,n").policy == "standard"
    assert res(fake_kit, "n").policy is None
    with pytest.raises(UsageError, match="--policy must be"):
        res(fake_kit, "n", policy_override="loose")


def test_child_policy_conflicting_with_parent_is_an_error(fake_kit):
    write(fake_kit, "parent", policy="restricted")
    write(fake_kit, "child", extends="parent", policy="standard")
    with pytest.raises(UsageError, match="conflicting policy"):
        res(fake_kit, "child")


# ---------------------------------------------------------------- TC-PRF-04 agent sections


def test_shared_codex_claude_sections(fake_kit):
    write(
        fake_kit,
        "p",
        skills={"shared": ["a"], "codex": ["b"], "claude": ["c"]},
        required_skills={"shared": ["a"], "claude": ["c"]},
        mcp={"codex": ["sequential-thinking"]},
        plugins={"claude": ["some-plugin"]},
    )
    codex = res(fake_kit, "p").for_agent("codex")
    claude = res(fake_kit, "p").for_agent("claude")
    assert codex.profile.skills == ["a", "b"] and claude.profile.skills == ["a", "c"]
    assert codex.profile.required_skills == ["a"] and claude.profile.required_skills == ["a", "c"]
    assert codex.profile.mcp == ["sequential-thinking"] and claude.profile.mcp == []
    assert codex.plugins == [] and claude.plugins == ["some-plugin"]


def test_profile_not_for_agent_is_skipped_and_reported(fake_kit):
    write(fake_kit, "both", skills={"shared": ["a"]})
    write(fake_kit, "conly", kind="pack", agents=["codex"], skills={"shared": ["b"]})
    resolved = res(fake_kit, "both,conly")
    assert resolved.for_agent("codex").profile.skills == ["a", "b"]
    claude = resolved.for_agent("claude")
    assert claude.profile.skills == ["a"] and claude.skipped == ["conly"]
    assert "Skipped (not for claude): conly" in pr.render_show(resolved, ["claude"])
    with pytest.raises(UsageError, match="unknown agent 'gemini'"):
        resolved.for_agent("gemini")


# ---------------------------------------------------------------- malformed files (BLOCKED)


@pytest.mark.parametrize(
    "kind,data,match",
    [
        ("profile", {"schema": 3}, "unsupported schema 3"),
        ("profile", {"schema": 2, "colour": 1}, "unknown field"),
        ("profile", {"schema": 2, "name": "other"}, "name field says"),
        ("profile", {"schema": 2, "agents": ["gemini"]}, "unknown agent"),
        ("profile", {"schema": 2, "policy": "loose"}, "policy must be"),
        ("profile", {"schema": 2, "skills": ["a"]}, "skills must map"),
        ("profile", {"schema": 2, "skills": {"gemini": []}}, "unknown section"),
        ("profile", {"schema": 2, "plugins": {"shared": []}}, "unknown section"),
        ("profile", {"schema": 2, "kind": "pack"}, "declares kind 'pack'"),
        ("pack", {"schema": 2}, "declares kind 'profile'"),
        ("pack", {"schema": 2, "kind": "pack", "extends": ["x"]}, "cannot use extends"),
        ("profile", {"kind": "pack"}, "kind needs schema 2"),
        ("profile", {"skills": "a"}, "skills must be a list"),
        ("profile", {"schema": 2, "tools": [{"name": "t", "kind": "zip"}]}, "unknown kind"),
        ("profile", {"schema": 2, "checks": [{}]}, "every check needs a name"),
    ],
)
def test_malformed_files_are_profile_errors(fake_kit, kind, data, match):
    folder = fake_kit / ("profiles/packs" if kind == "pack" else "profiles")
    (folder / "bad.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProfileError, match=match):
        res(fake_kit, "bad")


def test_name_in_both_places_is_ambiguous(fake_kit):
    write(fake_kit, "dup")
    write(fake_kit, "dup", kind="pack")
    with pytest.raises(ProfileError, match="both a profile and a pack"):
        res(fake_kit, "dup")


def test_invalid_json_is_profile_error(fake_kit):
    (fake_kit / "profiles/bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(ProfileError, match="not valid JSON"):
        res(fake_kit, "bad")


# ---------------------------------------------------------------- show / list


def test_show_matches_resolution(kit_root):
    resolved = pr.resolve(kit_root, "python,hitl")
    text = pr.render_show(resolved, ["claude"])
    profile = resolved.for_agent("claude").profile
    assert text.startswith("Profile: python,hitl\n")
    assert "Order: core -> python -> hitl\n" in text
    assert f"  Skills ({len(profile.skills)}): {', '.join(profile.skills)}\n" in text
    assert "  MCP: sequential-thinking\n" in text and "[codex]" not in text


def test_list_entries(kit_root):
    entries = pr.list_entries(kit_root)
    profiles = sorted(V1 + V2)
    assert entries[: len(profiles)] == [(n, "profile") for n in profiles]
    assert ("hitl", "pack") in entries


def test_resolver_is_read_only(kit_root, tmp_path):
    from tests.conftest import tree_digest

    before = tree_digest(kit_root / "profiles")
    pr.render_show(pr.resolve(kit_root, "full,hitl"))
    assert tree_digest(kit_root / "profiles") == before
