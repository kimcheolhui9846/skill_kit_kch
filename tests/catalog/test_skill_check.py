"""P4-T2 static skill checks (REQ-AGENT-002, REQ-ARCH-001). TC-SKL-*."""

from __future__ import annotations

import io
import json

import pytest

from kit import catalog, commands
from kit.model import EXIT_BLOCKED, EXIT_READY
from kit.skill_check import check, parse_frontmatter
from tests.catalog.kit_fixture import write

DESC = "Does a thing. Use when X. Do NOT use for Y."


def skill(name="demo", description=DESC, extra="", body="# Demo\n"):
    text = f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n{body}"
    return [("SKILL.md", text.encode("utf-8"))]


def errors(files, agent="codex", name="demo", kit_rules=True):
    return check(name, files, agent, kit_rules).errors


def warnings(files, agent="codex", name="demo", kit_rules=True):
    return check(name, files, agent, kit_rules).warnings


# ---------------------------------------------------------------- the real skills


KNOWN_WARNINGS = {"emil-design-eng": ["SKILL.md is longer than 500 lines"]}  # upstream, 677 lines


@pytest.mark.parametrize("agent", ["codex", "claude"])
@pytest.mark.parametrize("policy", ["restricted", "standard"])
def test_every_catalog_skill_is_clean(kit_root, agent, policy):
    source = catalog.source_for(kit_root, agent, policy)
    checked = 0
    for name, entry in source.entries.items():
        if entry.available(agent, policy):
            continue
        report = source.check(name)
        assert report.errors == [], name
        assert report.warnings == KNOWN_WARNINGS.get(name, []), name
        checked += 1
    # standard: +7 research pack (U-40), +task-approval (P5-T2), +launch-compliance-check
    assert checked == {"restricted": 11, "standard": 35}[policy]


# ---------------------------------------------------------------- spec rules (both agents)


@pytest.mark.parametrize(
    "name,folder,ok",
    [
        ("demo", "demo", True),
        ("a" * 64, "a" * 64, True),
        ("a" * 65, "a" * 65, False),
        ("Demo", "Demo", False),
        ("-demo", "-demo", False),
        ("demo-", "demo-", False),
        ("de--mo", "de--mo", False),
        ("de_mo", "de_mo", False),
        ("demo", "other", False),
    ],
)
@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_name_rules(name, folder, ok, agent):
    assert (errors(skill(name=name), agent, folder) == []) is ok


def test_description_rules():
    assert "description is missing" in errors(skill(description=""))
    long_ok = "x" * 1024
    assert errors(skill(description=long_ok), kit_rules=False) == []
    assert "description is longer than 1024 characters" in errors(
        skill(description=long_ok + "x"), kit_rules=False
    )


def test_optional_fields():
    assert errors(skill(extra="compatibility: " + "c" * 500 + "\n"), kit_rules=False) == []
    assert any(
        "compatibility" in e for e in errors(skill(extra="compatibility: " + "c" * 501 + "\n"))
    )
    assert any("metadata" in e for e in errors(skill(extra="metadata: flat\n")))
    nested = 'metadata:\n  author: me\n  version: "1.0"\n'
    assert errors(skill(extra=nested)) == []
    assert parse_frontmatter("---\n" + nested + "---\n")["metadata"] == {
        "author": "me",
        "version": "1.0",
    }


@pytest.mark.parametrize(
    "text,match",
    [
        ("\n---\nname: demo\n---\n", "first line"),
        ("---\nname: demo\n", "not closed"),
        ("---\nname: demo\nname: demo\n---\n", "duplicate key"),
        ("---\n  indented: x\n---\n", "without a parent"),
        ("---\nno colon here\n---\n", "bad frontmatter line"),
    ],
)
def test_frontmatter_errors(text, match):
    assert any(match in e for e in errors([("SKILL.md", text.encode())]))


def test_kit_rules_apply_only_to_kit_skills():
    plain = skill(description="Does a thing. Use when X.")
    assert any("Do NOT use" in e for e in errors(plain))
    assert errors(plain, kit_rules=False) == []
    long = skill(description="x" * 401 + " Do NOT use for Y.")
    assert any("kit rule" in e for e in errors(long))
    assert errors(long, kit_rules=False) == []


def test_long_skill_md_is_a_warning():
    assert any("500 lines" in w for w in warnings(skill(body="line\n" * 600)))


# ---------------------------------------------------------------- links


@pytest.mark.parametrize(
    "body,files,problem",
    [
        ("[ref](references/a.md)", {"references/a.md"}, None),
        ("[ref](references/a.md#part)", {"references/a.md"}, None),
        ("[dir](references/)", {"references/a.md"}, None),
        ("[web](https://example.com/x) [mail](mailto:a@b.c) [top](#steps)", set(), None),
        ("```\n[not a link](missing.md)\n```", set(), None),
        ("`[code](missing.md)`", set(), None),
        ("[ref](references/missing.md)", set(), "broken link"),
        ("![img](assets/x.png)", set(), "broken link"),
        ("[up](../other/SKILL.md)", set(), "outside the skill"),
    ],
)
def test_relative_links(body, files, problem):
    found = errors(skill(body=body) + [(f, b"x") for f in files])
    if problem is None:
        assert found == []
    else:
        assert any(problem in e for e in found)


def test_links_inside_reference_files_are_relative_to_that_file():
    files = skill() + [("references/a.md", b"[b](b.md) [bad](c.md)"), ("references/b.md", b"")]
    assert errors(files) == ["references/a.md: broken link 'c.md'"]


# ---------------------------------------------------------------- per-agent fields


def test_claude_listing_cap_is_a_warning():
    files = skill(description="d" * 1000, extra="when_to_use: " + "w" * 600 + "\n")
    report = check("demo", files, "claude", kit_rules=False)
    assert report.errors == [] and any("1536" in w for w in report.warnings)
    assert check("demo", files, "codex", kit_rules=False).warnings == [
        "field 'when_to_use' is Claude Code only; move it to claude/skills/demo/"
    ]


def test_unknown_fields():
    files = skill(extra="colour: blue\n")
    assert warnings(files, "claude") == ["field 'colour' is ignored by Claude Code"]
    assert warnings(files, "codex") == ["field 'colour' is not a known skill field"]


def test_openai_yaml_is_codex_only():
    good = b"interface:\n  display_name: Demo\npolicy:\n  allow_implicit_invocation: false\n"
    files = skill() + [("agents/openai.yaml", good)]
    assert check("demo", files, "codex").warnings == []
    assert any("Codex-only" in w for w in warnings(files, "claude"))


def test_openai_yaml_checks():
    bad = b"interface:\n  title: x\npolicy:\n  allow_implicit_invocation: maybe\nextra: 1\n"
    report = check("demo", skill() + [("agents/openai.yaml", bad)], "codex")
    assert report.errors == ["agents/openai.yaml: allow_implicit_invocation must be true or false"]
    assert set(report.warnings) == {
        "agents/openai.yaml: unknown key 'interface.title'",
        "agents/openai.yaml: unknown key 'extra'",
    }


# ---------------------------------------------------------------- in the install flow


def run(kit, workspace, *argv):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out), out.getvalue()


def test_invalid_layer_blocks_install_before_writing(kit, workspace, capsys):
    write(
        kit,
        "codex/skills/tree-demo/agents/openai.yaml",
        "policy:\n  allow_implicit_invocation: maybe\n",
    )
    code, _ = run(
        kit, workspace, "install", "--agent", "both", "--profile", "core,demo", "--offline"
    )
    assert code == EXIT_BLOCKED
    assert "allow_implicit_invocation" in capsys.readouterr().err
    assert list(workspace.iterdir()) == []


def test_warnings_are_reported_per_agent(kit, workspace):
    write(
        kit,
        "shared/skills/tree-demo/SKILL.md",
        "---\nname: tree-demo\ndescription: Shared. Do NOT use for other work.\n"
        "disable-model-invocation: true\n---\n\n# x\n",
    )
    code, out = run(kit, workspace, "plan", "--agent", "both", "--profile", "core,demo")
    assert code == EXIT_READY
    assert (
        "Skill warning: tree-demo: field 'disable-model-invocation' is Claude Code only; "
        "move it to claude/skills/tree-demo/"
    ) in out
    assert out.count("Skill warning:") == 1  # nothing for claude


def test_verify_uses_official_rules_for_external_skills(kit, workspace):
    write(
        kit,
        "shared/skills/tree-demo/SKILL.md",
        "---\nname: tree-demo\ndescription: An external skill without the kit sentence.\n"
        "---\n\n# x\n",
    )
    data = json.loads((kit / "catalog/skills.json").read_text(encoding="utf-8"))
    for entry in data["skills"]:
        if entry["name"] == "tree-demo":
            entry["origin"] = "source:example"
    write(kit, "catalog/skills.json", json.dumps(data))
    code, out = run(
        kit, workspace, "install", "--agent", "claude", "--profile", "core,demo", "--offline"
    )
    assert code == EXIT_READY, out
    assert run(kit, workspace, "verify", "--agent", "claude", "--offline")[0] == EXIT_READY
