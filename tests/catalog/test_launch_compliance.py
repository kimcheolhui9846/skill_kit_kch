"""TC-SKL-05 (REQ-SKILL-001, follow-up 4): the launch-compliance-check skill.

The 20 items are the user's list (docs/v2/inputs/launch-checklist.txt) in its order; each has
how to check, evidence, FAIL signs and a rule id. Verdicts are PASS / FAIL / N/A / NEEDS_HUMAN.
Every rule id resolves to a source row whose level is VERIFIED-DOC (with an official URL and a
check date) or UNVERIFIED. The skill says it is not legal advice. It installs on the standard
policy of web, fullstack and the launch pack only; restricted and the legacy path never see it.
"""

from __future__ import annotations

import re

import pytest

from kit import catalog
from tests.catalog.test_sources import run
from tests.conftest import KIT_ROOT

SKILL = KIT_ROOT / "shared/skills/launch-compliance-check"
INPUT = KIT_ROOT / "docs/v2/inputs/launch-checklist.txt"
VERDICTS = ("PASS", "FAIL", "N/A", "NEEDS_HUMAN")
OFFICIAL = ("https://www.w3.org/", "https://eur-lex.europa.eu/", "https://www.law.go.kr")


def read(rel):
    return (SKILL / rel).read_text(encoding="utf-8")


def input_items():
    items = []
    for line in INPUT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(\d+)\.\s*(.+?)\s*$", line)
        if m:
            items.append((int(m.group(1)), m.group(2)))
    return items


def checklist_items():
    text = read("references/checklist.md")
    found = re.findall(r"^## (\d+)\. (.+?) \(([^)]+)\)$", text, re.M)
    bodies = re.split(r"^## \d+\. .*$", text, flags=re.M)[1:]
    return [(int(n), ko, body) for (n, ko, _), body in zip(found, bodies)]


def sources():
    rows = {}
    for line in read("references/sources.md").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and re.fullmatch(r"S-\d+", cells[0]):
            rows[cells[0]] = cells
    return rows


def test_the_twenty_items_are_the_users_list_in_order():
    wanted = input_items()
    assert len(wanted) == 20
    got = [(n, ko) for n, ko, _ in checklist_items()]
    assert got == wanted


@pytest.mark.parametrize("number", range(1, 21))
def test_each_item_says_how_what_and_which_rule(number):
    body = next(b for n, _, b in checklist_items() if n == number)
    for part in ("- How to check:", "- Evidence:", "- FAIL signs:", "- Rule:"):
        assert part in body, (number, part)
    ids = re.findall(r"S-\d+", body.split("- Rule:")[1])
    assert ids and all(i in sources() for i in ids), (number, ids)


def test_verdicts_report_and_disclaimer():
    text = read("SKILL.md")
    assert "**This is not legal advice.**" in text
    assert "This is not legal advice." in read("references/sources.md")
    for verdict in VERDICTS:
        assert f"`{verdict}`" in text, verdict
    assert "No evidence, no PASS." in text
    for column in ("How checked", "Evidence", "Verdict", "Rule (level)"):
        assert column in text
    assert "All 20 rows appear" in text


def test_every_source_has_a_level_and_verified_ones_have_url_and_date():
    rows = sources()
    assert rows
    for sid, (_, rule, items, url, checked, level) in rows.items():
        assert level in ("VERIFIED-DOC", "UNVERIFIED"), sid
        assert rule and items, sid
        if level == "VERIFIED-DOC":
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked), sid
            assert url.startswith(OFFICIAL), sid
        else:
            assert checked == "-", sid  # nothing claims a check that did not happen
    used = {i for _, _, body in checklist_items() for i in re.findall(r"S-\d+", body)}
    assert set(rows) == used  # no source without an item, no item rule without a source


def test_korean_statutes_are_not_claimed_as_verified():
    """2026-11-08: law.go.kr text could not be read; nothing Korean is VERIFIED-DOC."""
    for sid, row in sources().items():
        if "법" in row[1]:
            assert row[5] == "UNVERIFIED", sid


@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_the_skill_passes_the_static_checks(agent):
    source = catalog.source_for(KIT_ROOT, agent, "standard")
    report = source.check("launch-compliance-check")
    assert report.errors == [] and report.warnings == []


@pytest.mark.parametrize(
    "profile, policy, present",
    [
        ("web", "standard", True),
        ("fullstack", "standard", True),
        ("core,launch", "standard", True),
        ("core", "standard", False),
        ("python", "standard", False),
        ("web", "restricted", False),
        ("fullstack", "restricted", False),
    ],
)
def test_install_scope(kit_root, workspace, profile, policy, present):
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
    )
    assert code == 0, out
    for root in (".agents/skills", ".claude/skills"):
        installed = (workspace / root / "launch-compliance-check/references/sources.md").is_file()
        assert installed is present, (root, profile, policy)


def test_the_legacy_web_install_is_unchanged(run_kit, workspace):
    code, out = run_kit("--profile", "web", "--offline")
    assert code == 0, out
    assert not (workspace / ".agents/skills/launch-compliance-check").exists()
    assert not (KIT_ROOT / ".agents/skills/launch-compliance-check").exists()  # the mirror
