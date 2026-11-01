import re

import pytest

from kit.skills import MAX_DESCRIPTION, parse_frontmatter, validate_skill

CORE = ["task-router", "tdd-automator", "algorithm-optimizer", "submission-validator"]
WITH_LANGUAGES = ["tdd-automator", "algorithm-optimizer", "submission-validator"]


def _skill(root, name, frontmatter):
    folder = root / name
    folder.mkdir()
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Body\n", encoding="utf-8")
    return folder


def test_parse_frontmatter_strips_quotes():
    text = '---\nname: x\ndescription: "a: b"\n---\nbody'
    assert parse_frontmatter(text) == {"name": "x", "description": "a: b"}


def test_parse_requires_opening_marker():
    with pytest.raises(ValueError, match="opening"):
        parse_frontmatter("name: x\n")


def test_parse_requires_closing_marker():
    with pytest.raises(ValueError, match="closing"):
        parse_frontmatter("---\nname: x\n")


def test_validate_reports_name_mismatch(tmp_path):
    folder = _skill(tmp_path, "real", 'name: other\ndescription: "Use when x. Do NOT use y."')
    assert any("does not match" in e for e in validate_skill(folder))


def test_validate_requires_do_not_use(tmp_path):
    folder = _skill(tmp_path, "s", 'name: s\ndescription: "Use when x."')
    assert any("Do NOT use" in e for e in validate_skill(folder))


def test_validate_limits_description(tmp_path):
    long = "Use when " + "x" * MAX_DESCRIPTION + " Do NOT use y."
    folder = _skill(tmp_path, "s", f'name: s\ndescription: "{long}"')
    assert any("too long" in e for e in validate_skill(folder))


def test_validate_missing_skill_md(tmp_path):
    (tmp_path / "empty").mkdir()
    assert validate_skill(tmp_path / "empty") == ["empty: SKILL.md missing"]


@pytest.mark.parametrize("name", CORE)
def test_core_skill_is_valid(kit_root, name):
    assert validate_skill(kit_root / ".agents" / "skills" / name) == []


@pytest.mark.parametrize("name", CORE)
def test_core_skill_description_is_one_quoted_line(kit_root, name):
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("description:"))
    assert line.startswith('description: "') and line.endswith('"')
    assert line.count('"') == 2


@pytest.mark.parametrize("name", CORE)
def test_core_skill_has_example(kit_root, name):
    assert list((kit_root / ".agents" / "skills" / name / "examples").glob("*.md"))


@pytest.mark.parametrize("name", WITH_LANGUAGES)
def test_language_reference_exists(kit_root, name):
    assert (kit_root / ".agents" / "skills" / name / "references" / "languages.md").is_file()


def test_agents_md_policy(kit_root):
    text = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    for heading in (
        "## Understand the task",
        "## Build",
        "## Validate",
        "## Optimize",
        "## Restrictions",
    ):
        assert heading in text
    assert "task-router" in text
    assert "hackathon-kit:begin" not in text


EXTRA = [
    "systematic-debugging",
    "codebase-explorer",
    "counterexample-hunter",
    "algorithm-options",
]
ON_REQUEST = ["implementation-review", "benchmark", "design-review"]
ALL = CORE + ON_REQUEST + EXTRA


@pytest.mark.parametrize("name", ALL)
def test_every_skill_is_valid(kit_root, name):
    assert validate_skill(kit_root / ".agents" / "skills" / name) == []


def test_skill_set_matches_folders(kit_root):
    folders = sorted(p.name for p in (kit_root / ".agents" / "skills").iterdir() if p.is_dir())
    assert folders == sorted(ALL)


def test_total_description_budget(kit_root):
    total = 0
    for name in ALL:
        text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        total += len(parse_frontmatter(text)["description"])
    assert total <= 3000, total


@pytest.mark.parametrize("name", ON_REQUEST)
def test_on_request_policy(kit_root, name):
    folder = kit_root / ".agents" / "skills" / name
    assert not (folder / "agents" / "openai.yaml").exists()
    text = (folder / "SKILL.md").read_text(encoding="utf-8")
    description = parse_frontmatter(text)["description"]
    assert description.startswith(f"Use only when the user invokes ${name} or asks")
    assert "Do NOT use unasked" in description


def test_benchmark_language_reference(kit_root):
    assert (kit_root / ".agents/skills/benchmark/references/languages.md").is_file()


@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_has_example(kit_root, name):
    assert list((kit_root / ".agents" / "skills" / name / "examples").glob("*.md"))


@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_description_is_one_quoted_line(kit_root, name):
    text = (kit_root / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("description:"))
    assert line.startswith('description: "') and line.endswith('"')
    assert line.count('"') == 2


@pytest.mark.parametrize("name", EXTRA)
def test_extra_skill_is_implicit(kit_root, name):
    assert not (kit_root / ".agents" / "skills" / name / "agents" / "openai.yaml").exists()


def test_debugging_skill_credits_source(kit_root):
    text = (kit_root / ".agents/skills/systematic-debugging/SKILL.md").read_text(encoding="utf-8")
    assert "Adapted from obra/superpowers (MIT, Copyright (c) 2025 Jesse Vincent)" in text


def test_third_party_notices(kit_root):
    text = (kit_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "https://github.com/obra/superpowers" in text
    assert "2ce8aa15d05bd57213e6f746f953aafb7ded7a8b" in text
    assert "MIT License" in text
    assert "Copyright (c) 2025 Jesse Vincent" in text


def test_task_router_routes_new_skills(kit_root):
    text = (kit_root / ".agents/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "`codebase-explorer`",
        "`systematic-debugging`",
        "## Plan",
        "## Decision log",
        "## Repository",
    ):
        assert needle in text


def test_submission_validator_has_not_run(kit_root):
    text = (kit_root / ".agents/skills/submission-validator/SKILL.md").read_text(encoding="utf-8")
    assert "NOT RUN" in text
    assert "this validation pass" in text


@pytest.mark.parametrize("name", ALL)
def test_relative_links_resolve(kit_root, name):
    folder = kit_root / ".agents" / "skills" / name
    text = (folder / "SKILL.md").read_text(encoding="utf-8")
    for link in re.findall(r"`(\.\./[^`]+)`", text):
        assert (folder / link).is_file(), f"{name}: {link}"


def test_task_router_routes_stress_and_options(kit_root):
    text = (kit_root / ".agents/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    assert "`counterexample-hunter`" in text
    assert "`algorithm-options`" in text


def test_algorithm_options_waits_for_choice(kit_root):
    text = (kit_root / ".agents/skills/algorithm-options/SKILL.md").read_text(encoding="utf-8")
    assert "Stop and wait" in text
    assert "../algorithm-optimizer/SKILL.md" in text


def test_counterexample_hunter_keeps_failing_input(kit_root):
    text = (kit_root / ".agents/skills/counterexample-hunter/SKILL.md").read_text(encoding="utf-8")
    assert "brute" in text
    assert "seed" in text
    assert "regression test" in text


def test_design_review_is_read_only(kit_root):
    text = (kit_root / ".agents/skills/design-review/SKILL.md").read_text(encoding="utf-8")
    for needle in ("Cohesion", "Coupling", "Do not edit code", "| Location |"):
        assert needle in text
    assert list((kit_root / ".agents/skills/design-review/examples").glob("*.md"))


def test_algorithm_options_owns_stated_limits(kit_root):
    def description(name):
        text = (kit_root / ".agents/skills" / name / "SKILL.md").read_text(encoding="utf-8")
        return parse_frontmatter(text)["description"]

    assert description("algorithm-options").startswith(
        "Use before writing core logic for an algorithm problem with stated input sizes"
    )
    assert description("algorithm-optimizer").startswith("Use when a working solution is too slow")
