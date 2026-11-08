"""Opt-in packs vendored with `kit source add` (2026-11-08): standard policy only, never default.

Each pack installs exactly its own skills on top of core; no profile and no restricted install
ever carries them; every vendored file still matches sources.lock.json.
"""

from __future__ import annotations

import json

import pytest

from kit import catalog, sources
from kit.model import EXIT_PARTIAL, EXIT_READY
from tests.catalog.test_sources import run, skill_names
from tests.conftest import KIT_ROOT

PACKS = {
    "eng-patterns": [
        "accessibility",
        "api-design",
        "architecture-decision-records",
        "database-migrations",
        "error-handling",
        "python-testing",
        "regex-vs-llm-structured-text",
    ],
    "lean": ["ponytail", "ponytail-audit", "ponytail-debt", "ponytail-gain", "ponytail-review"],
    "cloudflare": [
        "agents-sdk",
        "cloudflare-app-bootstrap",
        "cloudflare-one-migrations",
        "durable-objects",
        "frameworks-on-cloudflare",
        "k2",
        "sandbox-migrate-to-next",
        "sandbox-next",
        "sandbox-stable",
        "workers-best-practices",
        "workers-development",
        "workers-profiling",
        "wrangler",
    ],
    "motion": [
        "animate",
        "animate-expo",
        "animation-performance",
        "animation-vocabulary",
        "apple-design",
        "ask-sonner",
        "break-ui",
        "choreograph",
        "find-animation-opportunities",
        "improve-animations",
        "mobile-native",
        "pick-ui-library",
        "prototype",
        "remove-animations",
        "review-animations",
        "write-swift",
    ],
    "planning-extras": ["domain-modeling", "handoff", "to-spec"],
}
NEW = sorted({name for names in PACKS.values() for name in names})
ROOTS = (".agents/skills", ".claude/skills")
PROFILES = sorted(p.stem for p in (KIT_ROOT / "profiles").glob("*.json"))


def install(kit_root, workspace, profile, policy="standard"):
    workspace.mkdir(parents=True, exist_ok=True)
    argv = ["install", "--agent", "both", "--profile", profile, "--policy", policy]
    code, out = run(kit_root, workspace, *argv, "--offline", "--no-mcp")
    assert code in (EXIT_READY, EXIT_PARTIAL), out
    found = {root: skill_names(workspace / root) for root in ROOTS}
    assert found[ROOTS[0]] == found[ROOTS[1]]  # both agents get the same skills
    return found[ROOTS[0]]


def test_pack_files_exist_and_are_listed(kit_root, workspace):
    code, out = run(kit_root, workspace, "profiles", "list")
    assert code == EXIT_READY
    for pack in PACKS:
        data = json.loads((kit_root / f"profiles/packs/{pack}.json").read_text(encoding="utf-8"))
        assert data["kind"] == "pack" and data["name"] == pack
        assert "opt-in" in data["description"].lower()
        assert "standard" in data["description"]
        assert f"  {pack} " in out


def test_catalog_entries_are_standard_only_and_in_their_pack_only(kit_root):
    entries = catalog.load_all(kit_root)
    for pack, names in PACKS.items():
        for name in names:
            options = entries[name]
            assert len(options) == 1, name  # no same-name skill elsewhere in the kit
            entry = options[0]
            assert entry.policies == ["standard"], name
            assert entry.packs == [pack], name
            assert entry.origin.startswith("source:"), name


@pytest.mark.parametrize("pack", sorted(PACKS))
def test_pack_adds_exactly_its_skills_to_core(kit_root, tmp_path, pack):
    core = install(kit_root, tmp_path / "core", "core")
    both = install(kit_root, tmp_path / "pack", f"core,{pack}")
    assert sorted(set(both) - set(core)) == sorted(PACKS[pack])
    assert set(core) <= set(both)


@pytest.mark.parametrize("pack", sorted(PACKS))
def test_restricted_never_installs_the_pack(kit_root, workspace, pack):
    found = install(kit_root, workspace, f"core,{pack}", policy="restricted")
    assert not set(found) & set(NEW)


@pytest.mark.parametrize("policy", ["standard", "restricted"])
@pytest.mark.parametrize("profile", PROFILES)
def test_no_profile_installs_them(kit_root, workspace, profile, policy):
    found = install(kit_root, workspace, profile, policy=policy)
    assert not set(found) & set(NEW), profile


def test_default_install_has_none_of_them(kit_root, workspace):
    code, out = run(kit_root, workspace, "install", "--agent", "both", "--offline", "--no-mcp")
    assert code in (EXIT_READY, EXIT_PARTIAL), out
    for root in ROOTS:
        assert not set(skill_names(workspace / root)) & set(NEW)


def test_profiles_do_not_name_them(kit_root):
    for path in sorted((kit_root / "profiles").rglob("*.json")):
        if path.parent.name == "packs" and path.stem in PACKS:
            continue
        text = path.read_text(encoding="utf-8")
        for name in NEW:
            assert f'"{name}"' not in text, (path.name, name)


def test_vendored_files_match_the_lock(kit_root):
    assert sources.check(kit_root) == []
    lock = json.loads((kit_root / "sources.lock.json").read_text(encoding="utf-8"))
    by_pack = {}
    for entry in lock["sources"]:
        for pack in entry.get("packs", []):
            by_pack.setdefault(pack, []).append(entry)
    for pack in PACKS:
        entries = by_pack[pack]
        assert len(entries) == 1, pack
        entry = entries[0]
        assert entry["risk"] in ("low", "medium")
        assert entry["added_by"] == "source add"
        assert entry["integration"] == "vendored-verbatim"
        assert len(entry["commit"]) == 40
        for rel in entry["files"]:
            assert (kit_root / rel).is_file(), rel
