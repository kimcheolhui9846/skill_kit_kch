"""P4-T4 sources.lock.json, third_party/ and the vendored skills (REQ-SRC-002/003/007).

TC-SRC-02 (lock schema, offline check), TC-SRC-03 (license + notices for every vendored
source), V-22 (restricted unchanged), V-23/V-24 (offline check, third_party coverage).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import catalog, commands, sources
from kit.model import EXIT_BLOCKED, EXIT_READY
from kit.skill_check import check
from kit.sources import LockError
from tests.catalog.kit_fixture import write

SP = "third_party/obra-superpowers"
CHAIN = [
    "brainstorming",
    "writing-plans",
    "executing-plans",
    "subagent-driven-development",
    "using-git-worktrees",
    "finishing-a-development-branch",
]


def run(kit, workspace, *argv):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out), out.getvalue()


def skill_names(root: Path):
    return sorted(p.parent.name for p in root.glob("*/SKILL.md"))


def tree(root: Path):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def edit_lock(kit, change):
    data = json.loads((kit / "sources.lock.json").read_text(encoding="utf-8"))
    change(data)
    write(kit, "sources.lock.json", json.dumps(data))


# ---------------------------------------------------------------- the real lock


def test_real_lock_matches_the_files(kit_root):
    """V-23 offline: every hash matches, every third_party file is locked, notices complete."""
    assert sources.check(kit_root) == []


def test_every_vendored_source_has_license_and_notice(kit_root):
    """TC-SRC-03 / V-24."""
    notices = (kit_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    lock = sources.load(kit_root)
    assert {s.id for s in lock.values()} >= {
        "superpowers-core",
        "superpowers-workflow",
        "anthropics-frontend-design",
        "emil-design-eng",
        "web-interface-guidelines",
        "karpathy-guidelines",
        "oh-my-codex",
    }
    for source in lock.values():
        if source.integration != "referenced":  # referenced: nothing copied (P4-T5 mcp/plugin)
            assert (kit_root / source.license_file).is_file(), source.id
        assert source.origin in notices and source.commit in notices, source.id
        assert source.license in ("MIT", "Apache-2.0"), source.id  # allowed licenses only
    folders = {p.name for p in (kit_root / "third_party").iterdir()}
    licensed = {s.license_file.split("/")[1] for s in lock.values() if s.license_file}
    assert folders <= licensed


def test_oh_my_codex_is_user_scope_and_codex_only(kit_root):
    omx = sources.load(kit_root)["oh-my-codex"]
    assert omx.scope == ["user"] and omx.agents == ["codex"]
    assert not any(e.origin == "source:oh-my-codex" for e in catalog.load(kit_root).values())


# ---------------------------------------------------------------- lock schema


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda d: d["sources"][1].update(commit="22f0b46"), "40-character"),
        (lambda d: d["sources"][1].update(origin="https://example.com/x/y"), "origin"),
        (lambda d: d["sources"][1].update(kind="tool"), "kind"),
        (lambda d: d["sources"][1].update(risk="none"), "risk"),
        (lambda d: d["sources"][1].update(integration="copied"), "integration"),
        (lambda d: d["sources"][1].update(content_sha256="0" * 64), "content_sha256"),
        (lambda d: d["sources"][1].update(license_file="LICENSE"), "license_file"),
        (lambda d: d["sources"][1].update(integration="referenced"), "carries no files"),
        (lambda d: d["sources"][1].pop("license"), "missing license"),
        (lambda d: d["sources"].append(dict(d["sources"][1])), "listed twice"),
        (lambda d: d["sources"][1].update(agents=["gemini"]), "unknown agents"),
        (lambda d: d.update(schema=2), "schema 1"),
    ],
)
def test_lock_schema_errors(kit, change, match):
    edit_lock(kit, change)
    with pytest.raises(LockError, match=match):
        sources.load(kit)


def test_bad_file_path_in_lock(kit):
    def change(d):
        entry = d["sources"][1]
        entry["files"]["../outside"] = "0" * 64
        entry["content_sha256"] = sources.digest(entry["files"])

    edit_lock(kit, change)
    with pytest.raises(LockError, match="bad path"):
        sources.load(kit)


# ---------------------------------------------------------------- offline check finds drift


def test_check_reports_changed_missing_and_unlocked_files(kit):
    (kit / SP / "skills/systematic-debugging/SKILL.md").write_bytes(b"changed\n")
    (kit / SP / "skills/writing-plans/SKILL.md").unlink()
    write(kit, "third_party/stray/file.md", "x")
    problems = sources.check(kit)
    assert (
        f"superpowers-core: {SP}/skills/systematic-debugging/SKILL.md "
        "differs from the lock (sha256)" in problems
    )
    assert f"superpowers-workflow: {SP}/skills/writing-plans/SKILL.md is missing" in problems
    assert "third_party/stray/file.md is not in sources.lock.json" in problems
    assert "third_party/stray/ has no license_file in sources.lock.json" in problems


def test_check_requires_notices(kit):
    write(kit, "THIRD_PARTY_NOTICES.md", "# nothing\n")
    problems = sources.check(kit)
    assert any("does not mention https://github.com/obra/superpowers" in p for p in problems)


def test_tampered_vendored_file_blocks_install_before_writing(kit, workspace):
    (kit / SP / "skills/receiving-code-review/SKILL.md").write_bytes(
        (kit / SP / "skills/receiving-code-review/SKILL.md").read_bytes() + b"\nextra\n"
    )
    code, _ = run(kit, workspace, "install", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED
    assert list(workspace.iterdir()) == []


def test_tampered_included_license_blocks_install(kit, workspace):
    (kit / SP / "LICENSE").write_bytes(b"not the license\n")
    code, _ = run(kit, workspace, "install", "--agent", "codex", "--offline")
    assert code == EXIT_BLOCKED
    assert list(workspace.iterdir()) == []


# ---------------------------------------------------------------- what each policy installs


def test_restricted_new_path_installs_only_the_legacy_skills(kit_root, workspace):
    code, out = run(
        kit_root, workspace, "install", "--agent", "both", "--policy", "restricted", "--offline"
    )
    assert code == EXIT_READY, out
    legacy = skill_names(kit_root / ".agents/skills")
    for root in (".agents/skills", ".claude/skills"):
        assert skill_names(workspace / root) == legacy
        for name in legacy:
            assert tree(workspace / root / name) == tree(kit_root / ".agents/skills" / name)
    assert "replaced skills" not in out


def test_standard_replaces_and_adds_vendored_skills(kit_root, workspace):
    code, out = run(kit_root, workspace, "install", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    assert skill_names(workspace / ".claude/skills") == sorted(
        [
            "algorithm-optimizer",
            "algorithm-options",
            "benchmark",
            "codebase-explorer",
            "counterexample-hunter",
            "design-review",
            "implementation-review",
            "task-router",
            "systematic-debugging",
            "test-driven-development",
            "verification-before-completion",
            "requesting-code-review",
            "receiving-code-review",
            "karpathy-guidelines",
        ]
    )
    assert (
        "replaced skills: tdd-automator -> test-driven-development, "
        "submission-validator -> verification-before-completion"
    ) in out
    data = json.loads(run(kit_root, workspace, "plan", "--agent", "claude", "--json")[1])
    assert data["agents"]["claude"]["replaced_skills"] == [
        "tdd-automator -> test-driven-development",
        "submission-validator -> verification-before-completion",
    ]


def test_installed_vendored_skill_is_upstream_bytes_plus_license(kit_root, workspace):
    run(kit_root, workspace, "install", "--agent", "codex", "--offline")
    installed = tree(workspace / ".agents/skills/systematic-debugging")
    upstream = tree(kit_root / SP / "skills/systematic-debugging")
    assert installed == {**upstream, "LICENSE": (kit_root / SP / "LICENSE").read_bytes()}
    karpathy = tree(workspace / ".agents/skills/karpathy-guidelines")
    assert b"No copyright line is given" in karpathy["LICENSE"]


def test_kit_additions_are_appended_with_their_reference(kit_root, workspace):
    run(kit_root, workspace, "install", "--agent", "claude", "--offline")
    root = workspace / ".claude/skills"
    upstream = (kit_root / SP / "skills/test-driven-development/SKILL.md").read_bytes()
    text = (root / "test-driven-development/SKILL.md").read_bytes()
    assert text.startswith(upstream) and b"## Kit additions: tests from a task statement" in text
    assert (root / "test-driven-development/references/languages.md").read_bytes() == (
        kit_root / ".agents/skills/tdd-automator/references/languages.md"
    ).read_bytes()
    vbc = (root / "verification-before-completion/SKILL.md").read_text(encoding="utf-8")
    assert "Requirement | Check | Evidence | Result" in vbc


def test_web_profile_gets_design_skills_on_standard_only(kit_root, workspace):
    code, out = run(
        kit_root, workspace, "install", "--agent", "codex", "--profile", "web", "--offline"
    )
    assert code == EXIT_READY, out
    root = workspace / ".agents/skills"
    for name in ("frontend-design", "emil-design-eng", "web-design-guidelines"):
        assert (root / name / "SKILL.md").is_file(), name
    assert (root / "frontend-design/LICENSE.txt").is_file()
    assert (root / "web-design-guidelines/references/command.md").read_bytes() == (
        kit_root / "third_party/vercel-labs-web-interface-guidelines/command.md"
    ).read_bytes()
    assert "Skill warning: emil-design-eng: SKILL.md is longer than 500 lines" not in out
    plan = run(kit_root, workspace, "plan", "--agent", "codex", "--profile", "web")[1]
    assert "Skill warning: emil-design-eng: SKILL.md is longer than 500 lines" in plan


# ---------------------------------------------------------------- the workflow pack


def test_workflow_pack_installs_the_chain_and_verifies(kit_root, workspace):
    argv = ["install", "--agent", "both", "--profile", "core,workflow", "--offline"]
    code, out = run(kit_root, workspace, *argv)
    assert code == EXIT_READY, out
    for root in (".agents/skills", ".claude/skills"):
        names = skill_names(workspace / root)
        assert set(CHAIN) <= set(names)
        # the cross-skill paths the scripts and links rely on exist side by side
        assert (workspace / root / "subagent-driven-development/scripts/task-brief").is_file()
        assert (workspace / root / "requesting-code-review/code-reviewer.md").is_file()
    assert run(kit_root, workspace, "verify", "--agent", "both", "--offline")[0] == EXIT_READY


def test_workflow_pack_is_skipped_on_restricted(kit_root, workspace):
    argv = ["plan", "--agent", "codex", "--profile", "core,workflow", "--policy", "restricted"]
    code, out = run(kit_root, workspace, *argv)
    assert code == EXIT_READY
    assert "brainstorming (not in the restricted policy)" in out


def test_requires_blocks_a_missing_companion(kit, workspace, capsys):
    pack = json.loads((kit / "profiles/packs/workflow.json").read_text(encoding="utf-8"))
    pack["skills"]["shared"] = ["executing-plans"]
    write(kit, "profiles/packs/workflow.json", json.dumps(pack))
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    for entry in data["skills"]:
        if entry["name"] in ("requesting-code-review", "subagent-driven-development"):
            entry["packs"] = []
    write(kit, "catalog/skills.json", json.dumps(data))
    code, _ = run(
        kit, workspace, "install", "--agent", "codex", "--profile", "core,workflow", "--offline"
    )
    assert code == EXIT_BLOCKED
    err = capsys.readouterr().err
    assert "needs subagent-driven-development, requesting-code-review installed with it" in err
    assert list(workspace.iterdir()) == []


# ---------------------------------------------------------------- sibling links (checker)


SIB = "---\nname: a\ndescription: A.\n---\n\n[x](../b/x.md)\n"


def test_sibling_link_needs_a_companion():
    files = [("SKILL.md", SIB.encode())]
    assert check("a", files, "codex", kit_rules=False).errors == [
        "SKILL.md: link '../b/x.md' points outside the skill"
    ]
    ok = check("a", files, "codex", False, lambda other, path: (other, path) == ("b", "x.md"))
    assert ok.errors == []
    wrong = check("a", files, "codex", False, lambda other, path: False)
    assert wrong.errors != []


def test_verify_checks_sibling_links_on_disk(kit_root, workspace):
    run(
        kit_root,
        workspace,
        "install",
        "--agent",
        "codex",
        "--profile",
        "core,workflow",
        "--offline",
    )
    (workspace / ".agents/skills/requesting-code-review/code-reviewer.md").unlink()
    code, out = run(kit_root, workspace, "verify", "--agent", "codex", "--offline")
    assert code != EXIT_READY
    assert "code-reviewer.md" in out


# ---------------------------------------------------------------- catalog rules added in P4-T4


@pytest.mark.parametrize(
    "change,match",
    [
        (
            lambda d: d["skills"].append(
                {"name": "benchmark", "location": ".agents/skills/benchmark"}
            ),
            "listed twice for the same policy",
        ),
        (lambda d: d["skills"][0].update(include={"x.md": "nope.md"}), "does not exist"),
        (lambda d: d["skills"][0].update(include={"../x.md": "AGENTS.md"}), "bad include path"),
        (lambda d: d["skills"][0].update(include={"x.md": "../AGENTS.md"}), "outside the kit"),
        (lambda d: d["skills"][0].update(requires=["ghost"]), "unknown skill 'ghost'"),
        (lambda d: d["skills"][0].update(replaces=["ghost"]), "unknown skill 'ghost'"),
    ],
)
def test_catalog_p4t4_errors(kit, change, match):
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    change(data)
    write(kit, "catalog/skills.json", json.dumps(data))
    with pytest.raises(catalog.CatalogError, match=match):
        catalog.load(kit)


def test_include_may_not_overwrite_a_base_file(kit):
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    for entry in data["skills"]:
        if entry["name"] == "benchmark":
            entry["include"] = {"SKILL.md": "AGENTS.md"}
    write(kit, "catalog/skills.json", json.dumps(data))
    entry = catalog.load(kit)["benchmark"]
    with pytest.raises(catalog.CatalogError, match="already a file"):
        catalog.skill_files(kit, entry, "codex", "restricted")


def test_same_name_resolves_per_policy(kit_root):
    assert catalog.load(kit_root, "restricted")["systematic-debugging"].location == (
        ".agents/skills/systematic-debugging"
    )
    assert catalog.load(kit_root, "standard")["systematic-debugging"].location == (
        f"{SP}/skills/systematic-debugging"
    )
