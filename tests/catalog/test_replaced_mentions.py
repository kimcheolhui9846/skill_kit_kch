"""Follow-up A (2026-11-08): installed kit skills never point at a skill that is not there.

On the standard policy test-driven-development and verification-before-completion take the
place of tdd-automator and submission-validator. The kit's own skills (task-router,
codebase-explorer, counterexample-hunter, design-review) named the old skills, and three linked
`../tdd-automator/references/languages.md`, which the standard install does not have. The
installer now rewrites those mentions to the replacement, in the kit's own Markdown only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from kit import catalog
from tests.catalog.test_sources import run
from tests.conftest import KIT_ROOT

PROFILES = sorted(p.stem for p in (KIT_ROOT / "profiles").glob("*.json"))
ROOTS = (".agents/skills", ".claude/skills")
PLAIN_WORDS = {"accessibility", "prototype"}


def mentions(text, name):
    return re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text) is not None


def kit_skill_texts(root: Path):
    """(skill, file, text) for the Markdown of the kit's own skills installed under root."""
    entries = catalog.load(KIT_ROOT)
    for skill_md in sorted(root.glob("*/SKILL.md")):
        name = skill_md.parent.name
        if name in entries and entries[name].origin != "kit":
            continue
        for path in sorted(skill_md.parent.rglob("*.md")):
            yield name, path, path.read_text(encoding="utf-8")


@pytest.mark.parametrize("policy", ["standard", "restricted"])
@pytest.mark.parametrize("profile", PROFILES)
def test_no_installed_kit_skill_names_a_skill_that_is_not_installed(
    kit_root, workspace, profile, policy
):
    code, out = run(
        kit_root,
        workspace,
        "install",
        "--agent",
        "both",
        "--profile",
        profile,
        "--policy",
        policy,
        "--offline",
        "--no-mcp",
    )
    assert code == 0, out
    # opt-in pack skills (2026-11-08) named with plain English words; kit prose that says
    # "prototype" or "accessibility" does not refer to them
    every = set(catalog.load_all(KIT_ROOT)) - PLAIN_WORDS
    for rel in ROOTS:
        root = workspace / rel
        installed = {p.parent.name for p in root.glob("*/SKILL.md")}
        assert installed, rel
        bad = [
            (skill, path.relative_to(root).as_posix(), other)
            for skill, path, text in kit_skill_texts(root)
            for other in sorted(every - installed)
            if mentions(text, other)
        ]
        assert bad == [], (rel, bad)
        for skill, path, text in kit_skill_texts(root):
            for link in re.findall(r"\.\./([\w-]+)/([\w./-]+\.md)", text):
                assert (root / link[0] / link[1]).is_file(), (skill, path.name, link)


def test_standard_task_router_names_the_replacements(kit_root, workspace):
    code, out = run(kit_root, workspace, "install", "--agent", "claude", "--offline", "--no-mcp")
    assert code == 0, out
    text = (workspace / ".claude/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    assert "`test-driven-development`" in text
    assert "`verification-before-completion`" in text
    assert "tdd-automator" not in text and "submission-validator" not in text
    hunter = (workspace / ".claude/skills/counterexample-hunter/SKILL.md").read_text("utf-8")
    assert "../test-driven-development/references/languages.md" in hunter
    assert (workspace / ".claude/skills/test-driven-development/references/languages.md").is_file()
    assert "tdd-automator -> test-driven-development" in out  # the report still says so


@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_the_rename_map_follows_the_catalog(agent):
    assert catalog.source_for(KIT_ROOT, agent, "restricted").renames == {}
    standard = catalog.source_for(KIT_ROOT, agent, "standard").renames
    assert standard["tdd-automator"] == "test-driven-development"
    assert standard["submission-validator"] == "verification-before-completion"


def test_only_unavailable_skills_are_renamed():
    def entry(name, policies, replaces=()):
        return catalog.SkillEntry(name, None, ["claude"], list(policies), replaces=list(replaces))

    entries = {
        "old": entry("old", ["restricted"]),
        "new": entry("new", ["standard"], replaces=["old", "kept"]),
        "kept": entry("kept", ["restricted", "standard"]),  # still installed: keep its name
        "gone": entry("gone", ["restricted"]),  # nothing replaces it: no rename
    }
    assert catalog.renames(entries, "claude", "standard") == {"old": "new"}
    assert catalog.renames(entries, "claude", "restricted") == {}


def test_vendored_skills_are_never_rewritten():
    source = catalog.source_for(KIT_ROOT, "claude", "standard")
    source.renames = {"the": "ZZZ"}  # a word every skill uses: only kit skills may change
    changed = set()
    for name, entry in source.entries.items():
        if entry.available("claude", "standard"):
            continue
        plain = catalog.skill_files(KIT_ROOT, entry, "claude", "standard")
        if entry.origin == "kit":
            if source(name) != plain:
                changed.add(name)
        else:
            assert source(name) == plain, name
    assert "task-router" in changed  # the probe itself works


def test_rename_mentions_whole_words_and_markdown_only():
    mapping = {"tdd-automator": "test-driven-development"}
    files = [
        ("SKILL.md", b"use `tdd-automator`; see ../tdd-automator/x.md; tdd-automator."),
        (
            "notes.md",
            "my-tdd-automator, tdd-automator-v2, tdd-automators, 한글 tdd-automator".encode(),
        ),
        ("run.py", b"# tdd-automator"),
    ]
    out = dict(catalog.rename_mentions(files, mapping))
    assert out["SKILL.md"] == (
        b"use `test-driven-development`; see ../test-driven-development/x.md; "
        b"test-driven-development."
    )
    assert out["notes.md"].decode() == (
        "my-tdd-automator, tdd-automator-v2, tdd-automators, 한글 test-driven-development"
    )
    assert out["run.py"] == b"# tdd-automator"
    assert catalog.rename_mentions(files, {}) == files


def test_the_mirror_keeps_the_old_names():
    """The legacy path copies .agents/skills unchanged (golden tests); only installs differ."""
    text = (KIT_ROOT / ".agents/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    assert "`tdd-automator`" in text
