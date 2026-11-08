"""Multi-line frontmatter values (follow-up S-1, 2026-11-08): block scalars and plain
continuation lines, in both parsers (kit.skill_check and kit.skills). Expected values follow the
YAML 1.2 rules for these cases (checked against a YAML library while writing, not at run time:
the kit has no YAML dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

import pytest

from kit import skill_check, skills


def both(body: str) -> List[dict]:
    text = "---\n" + body + "---\n# Body\n"
    return [skill_check.parse_frontmatter(text), skills.parse_frontmatter(text)]


@pytest.mark.parametrize(
    "body,expected",
    [
        # folded: line breaks become spaces, a blank line a newline; clip keeps one newline
        ("description: >\n  one\n  two\n\n  three\nname: x\n", "one two\nthree\n"),
        ("description: >-\n  one\n  two\nname: x\n", "one two"),
        ("description: >+\n  one\n  two\n\n\nname: x\n", "one two\n\n\n"),
        # more-indented lines are not folded
        ("description: >\n  a\n    indented\n  b\n\n  c\n", "a\n  indented\nb\nc\n"),
        ("description: >\n\n  lead\n  b\n", "\nlead b\n"),
        # literal: line breaks stay
        ("description: |\n  one\n  two\n\n  three\nname: x\n", "one\ntwo\n\nthree\n"),
        ("description: |-\n  one\n    more\n  two\nname: x\n", "one\n  more\ntwo"),
        ("description: |+\n  lit\n\nname: x\n", "lit\n\n"),
        ("description: |\n  # not a comment\n  x\n", "# not a comment\nx\n"),
        # header comment, explicit indentation, comment line after the block
        ("description: > # a comment\n  a\n  b\n", "a b\n"),
        ("description: >2\n    two extra\n  base\n", "  two extra\nbase\n"),
        ("description: >-\n  a\n  b\n# comment\nname: x\n", "a b"),
        # plain value over several lines
        (
            "description: Use on any coding task\n  continues here\n  and here.\nname: x\n",
            "Use on any coding task continues here and here.",
        ),
        ("description: first\n\n  after blank\nname: x\n", "first\nafter blank"),
        (
            "description:\n  value on the next line\n  more\nname: x\n",
            "value on the next line more",
        ),
        ('description: "quoted start\n  end"\nname: x\n', "quoted start end"),
        ("description: url http://x.y/z\n  more\n", "url http://x.y/z more"),
    ],
)
def test_multi_line_values(body, expected):
    for meta in both(body):
        assert meta["description"] == expected
        if "name: x" in body:
            assert meta["name"] == "x"


def test_one_level_maps_and_lists_still_work():
    meta = skill_check.parse_frontmatter(
        "---\nname: x\nmetadata:\n  author: me\n  version: '1'\ntags:\n  - a\n  - b\n"
        "description: >\n  folded\n  text\n---\n"
    )
    assert meta["metadata"] == {"author": "me", "version": "1"}
    assert meta["tags"] == ["a", "b"]
    assert meta["description"] == "folded text\n"


@pytest.mark.parametrize(
    "body",
    [
        "description: |\n    four\n  two\n",  # less indented than the block, not a key
        "no colon here\n",
        "  indented: x\n",
    ],
)
def test_other_shapes_still_raise(body):
    with pytest.raises(ValueError):
        skill_check.parse_frontmatter("---\n" + body + "---\n")


def test_skills_parser_still_rejects_lists():
    with pytest.raises(ValueError, match="bad frontmatter line"):
        skills.parse_frontmatter("---\nname: x\ntriggers:\n  - one\n---\n")


def _skill(description_lines: str, name: str = "demo") -> List[tuple]:
    text = f"---\nname: {name}\ndescription: >-\n{description_lines}---\n\n# {name}\n"
    return [("SKILL.md", text.encode("utf-8"))]


def test_checker_accepts_a_folded_description():
    files = _skill("  Does a thing.\n  Use when X. Do NOT use for Y.\n")
    for agent in ("codex", "claude"):
        assert skill_check.check("demo", files, agent).errors == []


def test_kit_rules_still_apply_to_kit_skills_only():
    long = "".join(f"  {'word ' * 10}\n" for _ in range(10))  # about 500 characters
    files = _skill(long + "  Do NOT use for Y.\n")
    assert any("kit rule" in e for e in skill_check.check("demo", files, "codex").errors)
    assert skill_check.check("demo", files, "codex", kit_rules=False).errors == []
    no_rule = _skill("  Does a thing.\n  Use when X.\n")
    assert any("Do NOT use" in e for e in skill_check.check("demo", no_rule, "codex").errors)
    assert skill_check.check("demo", no_rule, "codex", kit_rules=False).errors == []


# ---------------------------------------------------------------- no skill changes meaning

Old = Dict[str, Union[str, Dict[str, str], List[str]]]


def _old_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def old_skill_check_parse(text: str) -> Old:
    """kit.skill_check.parse_frontmatter before S-1, kept verbatim as the reference."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with '---' on the first line")
    data: Old = {}
    current = None
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            if current is None:
                raise ValueError(f"indented line without a parent key: {line!r}")
            item = line.strip()
            if item.startswith("- "):
                value = data[current] if isinstance(data[current], list) else []
                value.append(_old_scalar(item[2:]))
                data[current] = value
            else:
                key, sep, value = item.partition(":")
                if not sep:
                    raise ValueError(f"bad frontmatter line: {line!r}")
                mapping = data[current] if isinstance(data[current], dict) else {}
                mapping[key.strip()] = _old_scalar(value)
                data[current] = mapping
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        key = key.strip()
        if key in data:
            raise ValueError(f"duplicate key '{key}'")
        data[key] = _old_scalar(value)
        current = key
    raise ValueError("frontmatter is not closed with '---'")


def old_skills_parse(text: str) -> Dict[str, str]:
    """kit.skills.parse_frontmatter before S-1, kept verbatim as the reference."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    data: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        data[key.strip()] = _old_scalar(value)
    raise ValueError("missing closing '---'")


def _all_skill_files(kit_root: Path) -> List[Path]:
    found = []
    for folder in ("third_party", "shared/skills", ".agents/skills"):
        found += sorted((kit_root / folder).rglob("SKILL.md"))
    return found


def test_no_existing_skill_changes_meaning(kit_root):
    """Every SKILL.md the kit carries parses to the same name and description as before."""
    paths = _all_skill_files(kit_root)
    assert len(paths) > 50
    compared = 0
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for old, new in (
            (old_skill_check_parse, skill_check.parse_frontmatter),
            (old_skills_parse, skills.parse_frontmatter),
        ):
            try:
                before = old(text)
            except ValueError:
                continue  # the old parser refused it; nothing could rely on its meaning
            after = new(text)
            where = path.relative_to(kit_root).as_posix()
            assert after.get("name") == before.get("name"), where
            assert after.get("description") == before.get("description"), where
            assert after == before, where
            compared += 1
    # nearly all were readable before; the 5 ponytail SKILL.md files (lean pack, 2026-11-08)
    # use '>' blocks that both old parsers refused
    assert compared >= 2 * len(paths) - 5 - 2 * 5
