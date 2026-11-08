"""P5-T3 requirement-test tracing (00_PROMPT 10.3, ADR-012, REQ-TRACE-001~004, V-12).

TC-HTL-09 duplicate REQ id refused, TC-HTL-10 a test without requirements is reported,
TC-HTL-11 `trace check` reports untested requirements with exit 1, TC-HTL-12 `req impact`
lists the tests of a revised requirement.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import commands, trace
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import KIT_ROOT

BRIEF = """# Task Brief
Type: data

## Goal
Parse CSV files.

## Evaluation
- hidden tests

## Requirements
- REQ-001 (must): an empty file gives an empty list
- REQ-002 (should): quoted commas stay in one field
- REQ-003: rows with a missing column are reported

## Plan
- REQ-999 (must): not a requirement, wrong section
"""


def kit(ws: Path, *argv):
    out = io.StringIO()
    code = commands.run([*argv, "--target", str(ws)], ws, KIT_ROOT, out)
    return code, out.getvalue()


def data(ws: Path) -> dict:
    return json.loads((ws / trace.TRACE_REL).read_text(encoding="utf-8"))


def write(ws: Path, doc) -> None:
    p = ws / trace.TRACE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")


def req(ws: Path, req_id: str, priority: str = "must", text: str = "something"):
    code, out = kit(ws, "req", "add", req_id, "--text", text, "--priority", priority)
    assert code == EXIT_READY, out


def link(ws: Path, test_id: str, *reqs: str, case: str = "normal", locator: str = None):
    argv = ["trace", "link", test_id, "--case", case]
    argv += ["--locator", locator or f"tests/test_x.py::test_{test_id.lower()}"]
    for r in reqs:
        argv += ["--req", r]
    code, out = kit(ws, *argv)
    assert code == EXIT_READY, out
    return out


def check(ws: Path):
    code, out = kit(ws, "trace", "check", "--json")
    return code, [(f["kind"], f["subject"]) for f in json.loads(out)["findings"]]


# ---------------------------------------------------------------- requirements


def test_add_and_list(workspace):
    req(workspace, "REQ-001", text="  an empty file gives an empty list ")
    req(workspace, "REQ-002", "should")
    (r1, r2) = data(workspace)["requirements"]
    assert r1 == {
        "id": "REQ-001",
        "text": "an empty file gives an empty list",
        "source": "",
        "priority": "must",
        "revision": 1,
        "status": "not-started",
    }
    assert r2["priority"] == "should"
    code, out = kit(workspace, "req", "list")
    assert code == EXIT_READY and "REQ-001      must   r1   0 test(s)" in out


def test_a_duplicate_id_is_refused(workspace, capsys):
    """TC-HTL-09 / REQ-TRACE-001."""
    req(workspace, "REQ-001")
    before = (workspace / trace.TRACE_REL).read_bytes()
    code, out = kit(workspace, "req", "add", "REQ-001", "--text", "again")
    assert code == EXIT_BLOCKED and "REQ-001 already exists" in out
    assert (workspace / trace.TRACE_REL).read_bytes() == before
    doc = data(workspace)
    doc["requirements"].append(dict(doc["requirements"][0]))
    write(workspace, doc)
    assert kit(workspace, "trace", "check")[0] == EXIT_TARGET
    assert "REQ-001 is listed twice" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv, message",
    [
        (["req", "add", "R1", "--text", "x"], "look like REQ-001"),
        (["req", "add", "REQ-1", "--text", "  "], "--text needs"),
        (["req", "add", "REQ-1", "--text", "x", "--priority", "high"], "--priority must be"),
        (["req", "edit", "REQ-001"], "needs --text, --priority or --status"),
        (["req", "edit", "REQ-001", "--status", "done"], "--status must be"),
        (["req"], "req needs an action"),
        (["trace"], "trace needs an action"),
        (["trace", "link", "TC-1", "--locator", "a::b"], "--req is needed"),
        (["trace", "link", "TC-1", "--req", "REQ-001"], "needs --locator"),
        (
            ["trace", "link", "TC-1", "--req", "REQ-001", "--locator", "a", "--case", "edge"],
            "--case must be",
        ),
        (["trace", "link", "TC 1", "--req", "REQ-001", "--locator", "a"], "test id"),
        (
            ["trace", "link", "TC-1", "--req", "REQ-001", "--locator", "a", "--kind", "e2e"],
            "--kind must be",
        ),
    ],
)
def test_bad_arguments_are_usage_errors(workspace, capsys, argv, message):
    req(workspace, "REQ-001")
    if argv[:2] in (["req"], ["trace"]):
        out = io.StringIO()
        code = commands.run(argv, workspace, KIT_ROOT, out)
    else:
        code, _ = kit(workspace, *argv)
    assert code == EXIT_USAGE
    assert message in capsys.readouterr().err


def test_edit_raises_the_revision_only_for_text_or_priority(workspace):
    req(workspace, "REQ-001", text="a")
    kit(workspace, "req", "edit", "REQ-001", "--status", "partial")
    assert data(workspace)["requirements"][0]["revision"] == 1
    kit(workspace, "req", "edit", "REQ-001", "--text", "a")
    assert data(workspace)["requirements"][0]["revision"] == 1
    kit(workspace, "req", "edit", "REQ-001", "--priority", "should")
    kit(workspace, "req", "edit", "REQ-001", "--text", "b")
    r = data(workspace)["requirements"][0]
    assert (r["revision"], r["priority"], r["text"], r["status"]) == (3, "should", "b", "partial")
    code, out = kit(workspace, "req", "edit", "REQ-404", "--text", "x")
    assert code == EXIT_BLOCKED and "no requirement REQ-404" in out


# ---------------------------------------------------------------- TASK_BRIEF.md


def test_sync_reads_the_requirements_section(workspace):
    (workspace / "TASK_BRIEF.md").write_text(BRIEF, encoding="utf-8")
    code, out = kit(workspace, "req", "sync")
    assert code == EXIT_READY and "3 added, 0 revised, 0 unchanged" in out
    reqs = {r["id"]: r for r in data(workspace)["requirements"]}
    assert set(reqs) == {"REQ-001", "REQ-002", "REQ-003"}  # REQ-999 is outside the section
    assert reqs["REQ-002"]["priority"] == "should"
    assert reqs["REQ-003"]["priority"] == "must"  # no priority: must
    assert reqs["REQ-001"]["source"] == "TASK_BRIEF.md#REQ-001"
    assert reqs["REQ-001"]["text"] == "an empty file gives an empty list"


def test_sync_revises_changed_lines_and_names_the_tests_to_review(workspace):
    brief = workspace / "TASK_BRIEF.md"
    brief.write_text(BRIEF, encoding="utf-8")
    kit(workspace, "req", "sync")
    req(workspace, "REQ-100")  # added by hand: not reported as gone from the brief
    link(workspace, "TC-001", "REQ-001", case="boundary")
    brief.write_text(
        BRIEF.replace("an empty file gives an empty list", "an empty file gives []").replace(
            "- REQ-003: rows with a missing column are reported\n", ""
        ),
        encoding="utf-8",
    )
    code, out = kit(workspace, "req", "sync")
    assert code == EXIT_READY and "0 added, 1 revised, 1 unchanged" in out
    assert "Review:       TC-001 tests/test_x.py::test_tc-001 (saw r1)" in out
    assert "Warning:      no longer in TASK_BRIEF.md (kept): REQ-003\n" in out
    assert {r["id"] for r in data(workspace)["requirements"]} >= {"REQ-003"}
    assert kit(workspace, "req", "sync")[1].count("unchanged") == 1  # nothing new


@pytest.mark.parametrize(
    "brief, message",
    [
        (None, "TASK_BRIEF.md does not exist"),
        ("# Task Brief\n## Goal\nx\n", "has no '## Requirements' lines"),
        ("## Requirements\n- REQ-001: a\n- REQ-001: b\n", "lists REQ-001 more than once"),
        ("## Requirements\n- REQ-001 (high): a\n", "priority 'high' is not one of"),
    ],
)
def test_sync_refuses_a_brief_it_cannot_use(workspace, brief, message):
    if brief is not None:
        (workspace / "TASK_BRIEF.md").write_text(brief, encoding="utf-8")
    code, out = kit(workspace, "req", "sync")
    assert code == EXIT_BLOCKED and message in out
    assert not (workspace / trace.TRACE_REL).exists()


def test_sync_stays_in_the_workspace(workspace):
    code, out = kit(workspace, "req", "sync", "--brief", "../TASK_BRIEF.md")
    assert code == EXIT_BLOCKED and "outside the workspace" in out


def test_brief_parsing_details():
    text = "## requirements\n* REQ-A1 (MUST):  spaced text  \n- not a req\n## Next\n- REQ-B: no\n"
    assert trace.parse_brief(text) == [("REQ-A1", "must", "spaced text")]


# ---------------------------------------------------------------- trace check


def test_untested_requirements_are_reported(workspace):
    """TC-HTL-11 / REQ-TRACE-003."""
    req(workspace, "REQ-001")
    req(workspace, "REQ-002", "could")
    code, found = check(workspace)
    assert code == EXIT_PARTIAL
    assert found == [("UNTESTED", "REQ-001"), ("UNTESTED", "REQ-002")]
    code, out = kit(workspace, "trace", "check")
    assert "UNTESTED         REQ-001      must: no test" in out and "Status:       GAPS" in out


def test_a_must_requirement_with_only_normal_tests_is_weak(workspace):
    req(workspace, "REQ-001")
    req(workspace, "REQ-002", "should")
    link(workspace, "TC-001", "REQ-001", "REQ-002")
    link(workspace, "TC-002", "REQ-001")
    assert check(workspace) == (EXIT_PARTIAL, [("WEAK", "REQ-001")])  # should is not checked
    link(workspace, "TC-003", "REQ-001", case="error")
    assert check(workspace) == (EXIT_READY, [])
    code, out = kit(workspace, "trace", "check")
    assert "no gaps found" in out and "2 requirement(s) (1 must), 3 test(s)" in out


@pytest.mark.parametrize("case", ["boundary", "error", "counterexample"])
def test_any_non_normal_case_is_enough(workspace, case):
    req(workspace, "REQ-001")
    link(workspace, "TC-001", "REQ-001", case=case)
    assert check(workspace) == (EXIT_READY, [])


def test_tests_pointing_nowhere_are_reported(workspace):
    """TC-HTL-10 and the unknown-requirement case."""
    req(workspace, "REQ-001")
    link(workspace, "TC-001", "REQ-001", case="boundary")
    doc = data(workspace)
    doc["tests"].append(dict(doc["tests"][0], id="TC-002", requirements=[]))
    doc["tests"].append(
        dict(doc["tests"][0], id="TC-003", requirements=[{"id": "REQ-404", "revision": 1}])
    )
    write(workspace, doc)
    assert check(workspace) == (
        EXIT_PARTIAL,
        [("UNKNOWN_REQ", "TC-003"), ("NO_REQUIREMENTS", "TC-002")],
    )
    code, out = kit(workspace, "trace", "link", "TC-004", "--req", "REQ-404", "--locator", "a")
    assert code == EXIT_BLOCKED and "no requirement REQ-404" in out


def test_impact_after_a_revision(workspace):
    """TC-HTL-12 / REQ-TRACE-004."""
    req(workspace, "REQ-001", text="v1")
    req(workspace, "REQ-002")
    link(workspace, "TC-001", "REQ-001", case="boundary")
    link(workspace, "TC-002", "REQ-001", "REQ-002", case="error")
    link(workspace, "TC-003", "REQ-002", case="error")
    code, out = kit(workspace, "req", "edit", "REQ-001", "--text", "v2")
    assert "Review:       TC-001" in out and "Review:       TC-002" in out
    code, out = kit(workspace, "req", "impact", "REQ-001", "--json")
    payload = json.loads(out)
    assert payload["tests"] == ["TC-001", "TC-002"] and payload["review"] == ["TC-001", "TC-002"]
    code, found = check(workspace)
    assert (code, found) == (EXIT_PARTIAL, [("STALE", "TC-001"), ("STALE", "TC-002")])
    code, out = kit(workspace, "trace", "link", "TC-001", "--req", "REQ-001")  # reviewed at r2
    assert code == EXIT_READY, out
    assert data(workspace)["tests"][0]["case"] == "boundary"
    code, out = kit(workspace, "req", "impact", "REQ-001")
    assert "ok     TC-001" in out and "REVIEW TC-002" in out
    assert check(workspace) == (EXIT_PARTIAL, [("STALE", "TC-002")])
    code, out = kit(workspace, "req", "impact", "REQ-404")
    assert code == EXIT_USAGE


def test_relinking_adds_requirements_and_keeps_the_rest(workspace):
    req(workspace, "REQ-001")
    req(workspace, "REQ-002")
    link(workspace, "TC-001", "REQ-001", case="error", locator="a.py::t")
    code, out = kit(
        workspace,
        "trace",
        "link",
        "TC-001",
        "--req",
        "REQ-002",
        "--kind",
        "integration",
        "--purpose",
        "both",
    )
    assert code == EXIT_READY and "Updated:      TC-001" in out
    t = data(workspace)["tests"][0]
    assert [x["id"] for x in t["requirements"]] == ["REQ-001", "REQ-002"]
    assert (t["locator"], t["case"], t["kind"], t["purpose"]) == (
        "a.py::t",
        "error",
        "integration",
        "both",
    )


# ---------------------------------------------------------------- the file


def test_missing_or_empty_file_means_nothing_traced(workspace):
    assert check(workspace) == (EXIT_READY, [])
    write(workspace, "  \n")
    assert check(workspace) == (EXIT_READY, [])
    code, out = kit(workspace, "req", "list")
    assert code == EXIT_READY and "(none; kit req add or kit req sync)" in out


@pytest.mark.parametrize(
    "doc, message",
    [
        ("{oops", "not valid JSON"),
        ({"schema": 2, "requirements": [], "tests": []}, "schema 1"),
        ({"schema": 1, "requirements": {}, "tests": []}, "must be lists"),
        (
            {
                "schema": 1,
                "requirements": [{"id": "REQ-1", "priority": "p", "revision": 1}],
                "tests": [],
            },
            "priority 'p'",
        ),
        (
            {
                "schema": 1,
                "requirements": [{"id": "REQ-1", "priority": "must", "revision": 0}],
                "tests": [],
            },
            "revision of 1 or more",
        ),
        (
            {"schema": 1, "requirements": [], "tests": [{"id": "T", "requirements": "REQ-1"}]},
            "list of {id, revision}",
        ),
        (
            {
                "schema": 1,
                "requirements": [],
                "tests": [{"id": "T", "requirements": [], "case": "weird"}],
            },
            "case 'weird'",
        ),
        (
            {
                "schema": 1,
                "requirements": [],
                "tests": [{"id": "T", "requirements": []}, {"id": "T", "requirements": []}],
            },
            "test T is listed twice",
        ),
    ],
)
def test_a_broken_file_is_a_target_problem(workspace, capsys, doc, message):
    write(workspace, doc)
    assert kit(workspace, "trace", "check")[0] == EXIT_TARGET
    assert message in capsys.readouterr().err


def test_the_task_flow_uses_trace_priorities(workspace):
    """P5-T2 submit reads must/should from the same file."""
    req(workspace, "REQ-001")
    req(workspace, "REQ-002", "should")
    task = {"requirements": ["REQ-001", "REQ-002", "REQ-009"]}
    from kit import tasks

    assert tasks.must_requirements(workspace, task) == ["REQ-001", "REQ-009"]


def test_standard_task_router_asks_for_requirement_ids(workspace, isolated_home):
    code, out = kit(workspace, "install", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    text = (workspace / ".claude/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    assert "## Kit additions: requirement IDs" in text and "kit req sync" in text
    original = (KIT_ROOT / ".agents/skills/task-router/SKILL.md").read_text(encoding="utf-8")
    renamed = original.replace("tdd-automator", "test-driven-development").replace(
        "submission-validator", "verification-before-completion"
    )  # standard names the replacements (follow-up A)
    assert text.startswith(renamed.rstrip("\n"))
    assert "kit req sync" not in original  # restricted keeps the original skill
