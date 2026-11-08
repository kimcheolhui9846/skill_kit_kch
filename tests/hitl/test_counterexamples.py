"""P5-T5 counterexample review (00_PROMPT 10.5, REQ-CE-001/002, Q7).

TC-HTL-14 record schema and state transitions (NEEDS_SPEC never reaches CONVERTED without the
reviewer's decision), TC-HTL-15 a C-grade task cannot be submitted without a record,
TC-SKL-02 the standard counterexample-hunter overlay has the black-box step, NEEDS_SPEC and the
record format while restricted keeps the original; the Claude black-box subagent is kit-owned.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import commands, subagents, tasks, trace
from kit import counterexamples as ce
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import KIT_ROOT

AGENT_REL = ".claude/agents/counterexample-blackbox.md"


def kit(ws: Path, *argv):
    out = io.StringIO()
    code = commands.run([*argv, "--target", str(ws)], ws, KIT_ROOT, out)
    return code, out.getvalue()


def items(ws: Path) -> dict:
    doc = json.loads((ws / ce.CE_REL).read_text(encoding="utf-8"))
    return {i["id"]: i for i in doc["items"]}


def add(ws: Path, cid: str = "CE-001", expected: str = "kept as two records", **over):
    fields = {
        "--function": "dedupe_records()",
        "--req": "REQ-001",
        "--category": "duplicate",
        "--origin": "black-box",
        "--assumption": "keys compare case-insensitively",
        "--input": "[{'id':'A1'},{'id':'a1'}]",
        "--would-catch": "an implementation that merges after lower()",
        "--expected": expected,
        "--rationale": "REQ-001: compare IDs as given",
    }
    fields.update(over)
    argv = ["ce", "add", cid]
    for k, v in fields.items():
        if v is not None:
            argv += [k, v]
    return kit(ws, *argv)


def ok(ws: Path, *argv):
    code, out = kit(ws, *argv)
    assert code == EXIT_READY, out
    return out


def linked_test(ws: Path, test_id: str = "TC-031", req: str = "REQ-001"):
    if trace.get_req(trace.load(ws), req) is None:
        ok(ws, "req", "add", req, "--text", "compare IDs as given")
    ok(
        ws,
        "trace",
        "link",
        test_id,
        "--req",
        req,
        "--locator",
        "tests/t.py::test_ce",
        "--case",
        "counterexample",
    )


# ---------------------------------------------------------------- records


def test_add_records_the_10_5_3_shape(workspace):
    code, out = add(workspace)
    assert code == EXIT_READY and "CE-001        PROPOSED    dedupe_records()" in out
    item = items(workspace)["CE-001"]
    assert {k: item[k] for k in item if k != "history"} == {
        "id": "CE-001",
        "target": "dedupe_records()",
        "requirements": ["REQ-001"],
        "assumption_challenged": "keys compare case-insensitively",
        "category": "duplicate",
        "origin": "black-box",
        "input": "[{'id':'A1'},{'id':'a1'}]",
        "expected": "kept as two records",
        "would_catch": "an implementation that merges after lower()",
        "rationale": "REQ-001: compare IDs as given",
        "status": "PROPOSED",
        "test_id": "",
        "result": "",
    }
    assert [h["to"] for h in item["history"]] == ["PROPOSED"]


@pytest.mark.parametrize(
    "cid, over, message",
    [
        ("CE 1", {}, "look like CE-001"),
        ("CE-002", {"--category": "weird"}, "--category must be one of"),
        ("CE-002", {"--origin": "grey-box"}, "--origin must be one of"),
        ("CE-002", {"--req": "R1"}, "REQ IDs like REQ-001"),
        ("CE-002", {"--would-catch": None}, "--would-catch is needed"),
        ("CE-002", {"--assumption": "  "}, "--assumption is needed"),
        ("CE-002", {"--function": None}, "--function is needed"),
        ("CE-002", {"--input": "x" * 2001}, "longer than 2000"),
    ],
)
def test_bad_records_are_usage_errors(workspace, capsys, cid, over, message):
    code, _ = add(workspace, cid, **over)
    assert code == EXIT_USAGE and message in capsys.readouterr().err
    assert not (workspace / ce.CE_REL).exists()


def test_duplicates_and_unknown_requirements_are_refused(workspace):
    add(workspace)
    code, out = add(workspace)
    assert code == EXIT_BLOCKED and "CE-001 already exists" in out
    ok(workspace, "req", "add", "REQ-001", "--text", "x")  # trace.json now lists requirements
    code, out = add(workspace, "CE-002", **{"--req": "REQ-404"})
    assert code == EXIT_BLOCKED and "no requirement REQ-404 in trace.json" in out
    assert set(items(workspace)) == {"CE-001"}


# ---------------------------------------------------------------- transitions (TC-HTL-14)


def test_accept_convert_and_result(workspace):
    add(workspace)
    ok(workspace, "ce", "accept", "CE-001")
    linked_test(workspace)
    ok(workspace, "ce", "convert", "CE-001", "--test", "TC-031")
    ok(workspace, "ce", "result", "CE-001", "--result", "FAIL -> fixed -> PASS (token=abc123456)")
    item = items(workspace)["CE-001"]
    assert (item["status"], item["test_id"]) == ("CONVERTED", "TC-031")
    assert item["result"] == "FAIL -> fixed -> PASS (token=***"
    assert [h["to"] for h in item["history"]] == ["PROPOSED", "ACCEPTED", "CONVERTED"]
    for action, extra in (("reject", ["--reason", "x"]), ("accept", [])):
        code, out = kit(workspace, "ce", action, "CE-001", *extra)
        assert code == EXIT_BLOCKED and "is CONVERTED; it cannot become" in out


def test_needs_spec_cannot_be_converted_without_the_reviewer(workspace):
    """TC-HTL-14: the key rule of 10.5.1 step 5."""
    add(workspace, expected=None)
    code, out = kit(workspace, "ce", "accept", "CE-001")
    assert code == EXIT_BLOCKED and "has no expected result" in out and "needs-spec" in out
    out = ok(workspace, "ce", "needs-spec", "CE-001", "--question", "Are A1 and a1 the same?")
    assert "Ask:          Are A1 and a1 the same?" in out
    linked_test(workspace)
    code, out = kit(workspace, "ce", "convert", "CE-001", "--test", "TC-031")
    assert code == EXIT_BLOCKED and "the reviewer must decide it" in out
    code, out = kit(workspace, "ce", "accept", "CE-001")
    assert code == EXIT_BLOCKED and "only the reviewer resolves it" in out
    code, _ = kit(workspace, "ce", "resolve", "CE-001", "--expected", "two records")
    assert code == EXIT_USAGE  # no --quote
    ok(
        workspace,
        "ce",
        "resolve",
        "CE-001",
        "--expected",
        "two records (reviewer)",
        "--quote",
        "다른 레코드로 둬요 password=hunter2",
    )
    item = items(workspace)["CE-001"]
    assert item["status"] == "ACCEPTED" and item["expected"] == "two records (reviewer)"
    assert item["decision"]["by"] == "agent-recorded"
    assert item["decision"]["quote"] == "다른 레코드로 둬요 password=***"
    ok(workspace, "ce", "convert", "CE-001", "--test", "TC-031")
    assert items(workspace)["CE-001"]["status"] == "CONVERTED"


def test_rejecting_keeps_the_reason_and_is_final(workspace):
    add(workspace)
    code, _ = kit(workspace, "ce", "reject", "CE-001")
    assert code == EXIT_USAGE
    ok(workspace, "ce", "reject", "CE-001", "--reason", "covered by TC-012")
    item = items(workspace)["CE-001"]
    assert item["rejected_because"] == "covered by TC-012"
    assert item["history"][-1] == {
        **item["history"][-1],
        "from": "PROPOSED",
        "to": "REJECTED",
        "detail": "covered by TC-012",
    }
    code, out = kit(workspace, "ce", "accept", "CE-001")
    assert code == EXIT_BLOCKED


@pytest.mark.parametrize(
    "steps, action, message",
    [
        ([], ["resolve", "CE-001", "--expected", "x", "--quote", "y"], "resolve is for NEEDS_SPEC"),
        ([], ["result", "CE-001", "--result", "PASS"], "belongs to a CONVERTED item"),
        (
            [["needs-spec", "CE-001", "--question", "q"]],
            ["needs-spec", "CE-001", "--question", "q"],
            "cannot become NEEDS_SPEC",
        ),
        ([], ["accept", "CE-404"], "no counterexample CE-404"),
        ([["accept", "CE-001"]], ["accept", "CE-001"], "is ACCEPTED; it cannot become ACCEPTED"),
        ([], ["convert", "CE-001", "--test", "TC-031"], "is PROPOSED; it cannot become CONVERTED"),
    ],
)
def test_wrong_transitions_are_refused(workspace, steps, action, message):
    add(workspace)
    linked_test(workspace)
    for step in steps:
        ok(workspace, "ce", *step)
    before = (workspace / ce.CE_REL).read_bytes()
    code, out = kit(workspace, "ce", *action)
    assert code == EXIT_BLOCKED and message in out
    assert (workspace / ce.CE_REL).read_bytes() == before


def test_convert_needs_a_traced_test_that_checks_the_requirements(workspace):
    add(workspace)
    ok(workspace, "ce", "accept", "CE-001")
    code, out = kit(workspace, "ce", "convert", "CE-001")
    assert code == EXIT_USAGE
    code, out = kit(workspace, "ce", "convert", "CE-001", "--test", "TC-031")
    assert code == EXIT_BLOCKED and "no test TC-031 in trace.json" in out
    linked_test(workspace, req="REQ-002")
    code, out = kit(workspace, "ce", "convert", "CE-001", "--test", "TC-031")
    assert code == EXIT_BLOCKED and "TC-031 does not check REQ-001" in out


def test_list_shows_states_and_open_questions(workspace):
    out = ok(workspace, "ce", "list")
    assert "(none; kit ce add)" in out
    add(workspace)
    add(workspace, "CE-002", expected=None, **{"--origin": "white-box", "--category": "empty"})
    ok(workspace, "ce", "needs-spec", "CE-002", "--question", "empty file: [] or error?")
    out = ok(workspace, "ce", "list")
    assert "CE-002     NEEDS_SPEC  white-box  REQ-001" in out
    assert "ask: empty file: [] or error?" in out
    assert "Totals:       PROPOSED 1, ACCEPTED 0, REJECTED 0, NEEDS_SPEC 1, CONVERTED 0" in out
    payload = json.loads(ok(workspace, "ce", "list", "--json"))
    assert payload["counts"]["NEEDS_SPEC"] == 1 and len(payload["items"]) == 2


def test_no_action_is_a_usage_error(workspace, capsys):
    code = commands.run(["ce"], workspace, KIT_ROOT, io.StringIO())
    assert code == EXIT_USAGE and "ce needs an action" in capsys.readouterr().err


# ---------------------------------------------------------------- the file


def _item(**over):
    base = {
        "id": "CE-001",
        "target": "f()",
        "requirements": ["REQ-001"],
        "assumption_challenged": "a",
        "category": "boundary",
        "origin": "white-box",
        "input": "0",
        "expected": "1",
        "would_catch": "w",
        "status": "PROPOSED",
    }
    base.update(over)
    return base


@pytest.mark.parametrize(
    "doc, message",
    [
        ("{oops", "not valid JSON"),
        ({"schema": 2, "items": []}, "schema 1"),
        ({"schema": 1, "items": {}}, "items must be a list"),
        ({"schema": 1, "items": [{"target": "f"}]}, "every item needs an id"),
        ({"schema": 1, "items": [_item(), _item()]}, "CE-001 is listed twice"),
        ({"schema": 1, "items": [_item(would_catch="")]}, "CE-001 needs would_catch"),
        ({"schema": 1, "items": [_item(requirements="REQ-001")]}, "list of REQ IDs"),
        ({"schema": 1, "items": [_item(category="x")]}, "category 'x'"),
        ({"schema": 1, "items": [_item(origin="x")]}, "origin 'x'"),
        ({"schema": 1, "items": [_item(status="DONE")]}, "status 'DONE'"),
        (
            {"schema": 1, "items": [_item(status="ACCEPTED", expected="")]},
            "ACCEPTED without an expected result",
        ),
        ({"schema": 1, "items": [_item(status="CONVERTED")]}, "CONVERTED without test_id"),
        (
            {"schema": 1, "items": [_item(status="CONVERTED", test_id="T", question="q")]},
            "left NEEDS_SPEC without a reviewer decision",
        ),
    ],
)
def test_a_hand_edited_file_is_a_target_problem(workspace, capsys, doc, message):
    p = workspace / ce.CE_REL
    p.parent.mkdir(parents=True)
    p.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    assert kit(workspace, "ce", "list")[0] == EXIT_TARGET
    assert message in capsys.readouterr().err


def test_an_empty_file_means_no_records(workspace):
    p = workspace / ce.CE_REL
    p.parent.mkdir(parents=True)
    p.write_text("\n", encoding="utf-8")
    assert "(none; kit ce add)" in ok(workspace, "ce", "list")


# ---------------------------------------------------------------- C-grade submit (TC-HTL-15)

ROW = "| TC-1 | REQ-001 | empty file | '' | [] | [] | PASS |\n"
SEP = "|---|---|---|---|---|---|---|\n"


def started(ws: Path, grade: str, *reqs: str):
    argv = ["task", "add", "T-001", "--title", "A", "--grade", grade]
    for r in reqs:
        argv += ["--requires", r]
    ok(ws, *argv)
    ok(ws, "task", "start", "T-001")
    ok(ws, "task", "report", "T-001")
    p = ws / tasks.default_report("T-001")
    p.write_text(p.read_text(encoding="utf-8").replace(SEP, SEP + ROW, 1), encoding="utf-8")


def test_a_c_grade_task_needs_a_settled_record(workspace):
    started(workspace, "C", "REQ-001")
    code, out = kit(workspace, "task", "submit", "T-001")
    assert code == EXIT_BLOCKED and "grade C needs a counterexample record for REQ-001" in out
    add(workspace, **{"--req": "REQ-002"})  # another requirement does not count
    assert "grade C needs" in kit(workspace, "task", "submit", "T-001")[1]
    add(workspace, "CE-002")
    code, out = kit(workspace, "task", "submit", "T-001")
    assert code == EXIT_BLOCKED and "still PROPOSED: CE-002" in out
    ok(workspace, "ce", "needs-spec", "CE-002", "--question", "q")  # asked in section 8: fine
    code, out = kit(workspace, "task", "submit", "T-001")
    assert code == EXIT_READY, out


def test_a_c_grade_task_without_requirements_needs_any_record(workspace):
    started(workspace, "C")
    assert (
        "grade C needs a counterexample record for the task"
        in kit(workspace, "task", "submit", "T-001")[1]
    )
    add(workspace)
    ok(workspace, "ce", "reject", "CE-001", "--reason", "covered by TC-1")
    assert kit(workspace, "task", "submit", "T-001")[0] == EXIT_READY


def test_other_grades_do_not_need_records(workspace):
    started(workspace, "S", "REQ-001")
    assert kit(workspace, "task", "submit", "T-001")[0] == EXIT_READY


def test_a_broken_record_file_stops_a_c_submit(workspace):
    started(workspace, "C", "REQ-001")
    (workspace / ce.CE_REL).write_text("{oops", encoding="utf-8")
    code, out = kit(workspace, "task", "submit", "T-001")
    assert code == EXIT_BLOCKED and "counterexamples.json is not valid" in out


# ---------------------------------------------------------------- the test report


def test_report_shows_the_review_per_requirement(workspace):
    linked_test(workspace)
    add(workspace)
    add(workspace, "CE-002", expected=None)
    ok(workspace, "ce", "needs-spec", "CE-002", "--question", "q")
    (workspace / "j.xml").write_text(
        '<testsuite><testcase classname="tests.t" name="test_ce"/></testsuite>', encoding="utf-8"
    )
    code, out = kit(workspace, "report", "tests", "--junit", "j.xml", "--json")
    q = json.loads(out)["requirements"][0]
    assert q["review"] == "CE 2: PROPOSED 1, NEEDS_SPEC 1"
    assert q["risks"] == ["NEEDS_SPEC CE-002"]
    assert code == EXIT_READY  # the test passed; the review is for the reviewer
    p = workspace / ce.CE_REL
    p.write_text("{oops", encoding="utf-8")
    assert kit(workspace, "report", "tests", "--junit", "j.xml")[0] == EXIT_TARGET


# ---------------------------------------------------------------- skill and subagent (TC-SKL-02)


def test_standard_claude_install_brings_the_black_box_subagent(workspace):
    code, out = kit(workspace, "install", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    agent = (workspace / AGENT_REL).read_text(encoding="utf-8")
    agent_bytes = (workspace / AGENT_REL).read_bytes()
    assert agent == (KIT_ROOT / subagents.source_rel("counterexample-blackbox")).read_text(
        encoding="utf-8"
    )
    front = agent.split("---")[1]
    assert "name: counterexample-blackbox" in front and "\ntools: TodoWrite\n" in front
    skill = (workspace / ".claude/skills/counterexample-hunter/SKILL.md").read_text("utf-8")
    original = (KIT_ROOT / ".agents/skills/counterexample-hunter/SKILL.md").read_text("utf-8")
    renamed = original.replace("tdd-automator", "test-driven-development").replace(
        "submission-validator", "verification-before-completion"
    )  # standard names the replacements (follow-up A)
    assert skill.startswith(renamed.rstrip("\n"))
    for text in (
        "Black box first",
        "counterexample-blackbox",
        "NEEDS_SPEC",
        "kit ce add",
        "--would-catch",
        "kit ce resolve",
        "independence is weaker",
    ):
        assert text in skill, text
    code, out = kit(workspace, "verify", "--agent", "claude", "--offline", "--verbose")
    assert code == EXIT_READY and "subagent:counterexample-blackbox" in out
    (workspace / AGENT_REL).write_text("edited\n", encoding="utf-8")
    code, out = kit(workspace, "verify", "--agent", "claude", "--offline", "--verbose")
    assert code != EXIT_READY and "subagent:counterexample-blackbox" in out
    (workspace / AGENT_REL).write_bytes(agent_bytes)  # bytes: write_text would add CRLF
    code, out = kit(workspace, "uninstall", "--agent", "claude", "--offline")
    assert code == EXIT_READY and not (workspace / AGENT_REL).exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["--agent", "claude", "--policy", "restricted"],
        ["--agent", "codex"],
        ["--agent", "claude", "--profile", "hitl"],  # no counterexample-hunter
    ],
)
def test_no_subagent_without_standard_claude_and_the_skill(workspace, argv):
    code, out = kit(workspace, "install", *argv, "--offline")
    assert code in (EXIT_READY, EXIT_PARTIAL), out
    assert not (workspace / ".claude/agents").exists()
    skill = workspace / ".claude/skills/counterexample-hunter/SKILL.md"
    if "restricted" in argv:
        assert (
            skill.read_bytes()
            == (KIT_ROOT / ".agents/skills/counterexample-hunter/SKILL.md").read_bytes()
        )


def test_a_users_own_subagent_file_is_a_conflict(workspace):
    own = workspace / AGENT_REL
    own.parent.mkdir(parents=True)
    own.write_text("my own\n", encoding="utf-8")
    code, out = kit(workspace, "install", "--agent", "claude", "--offline")
    assert code != EXIT_READY and "counterexample-blackbox" in out
    assert own.read_text(encoding="utf-8") == "my own\n"
    assert (
        "CONFLICT   optional [claude] subagent:counterexample-blackbox  "
        "(.claude/agents/counterexample-blackbox.md: differs from the kit copy" in out
    )


def test_a_kit_upgrade_shows_the_subagent_outdated_then_update_rewrites_it(kit, workspace):
    def run(*argv):
        out = io.StringIO()
        code = commands.run([*argv, "--target", str(workspace)], workspace, kit, out)
        return code, out.getvalue()

    assert run("install", "--agent", "claude", "--offline")[0] == EXIT_READY
    source = kit / subagents.source_rel("counterexample-blackbox")
    source.write_bytes(source.read_bytes() + b"\nNew line in a later kit.\n")
    code, out = run("verify", "--agent", "claude", "--offline", "--verbose")
    assert code != EXIT_READY
    assert "subagent:counterexample-blackbox" in out and "is outdated" in out
    code, out = run("update", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    assert (workspace / AGENT_REL).read_bytes() == source.read_bytes()


def test_a_requirement_named_twice_is_kept_once(workspace):
    add(workspace, **{"--req": "REQ-001"})
    ok(
        workspace,
        "ce",
        "add",
        "CE-002",
        "--function",
        "f",
        "--req",
        "REQ-002",
        "--req",
        "REQ-002",
        "--category",
        "empty",
        "--origin",
        "white-box",
        "--assumption",
        "a",
        "--input",
        "''",
        "--would-catch",
        "w",
    )
    assert items(workspace)["CE-002"]["requirements"] == ["REQ-002"]
