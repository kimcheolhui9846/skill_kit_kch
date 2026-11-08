"""P5-T2 `kit task` state machine and approvals (00_PROMPT 10.2, REQ-HITL-001~006).

TC-HTL-01 add with depends_on and subtasks, TC-HTL-02 subtasks need no approval,
TC-HTL-03 start refused before the dependency is approved (V-14), TC-HTL-05 the report
template has the nine 5.6 sections, TC-HTL-06 (L1 part) the `by` values and a refused
non-interactive human-cli approval.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from kit import commands, tasks
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import KIT_ROOT

ROW = "| TC-1 | REQ-001 | empty file | '' | [] | [] | PASS |\n"
SEP = "|---|---|---|---|---|---|---|\n"


def kit(ws: Path, *argv, ask=None):
    out = io.StringIO()
    code = commands.run(["task", *argv, "--target", str(ws)], ws, KIT_ROOT, out, ask)
    return code, out.getvalue()


def data(ws: Path) -> dict:
    return json.loads((ws / tasks.TASKS_REL).read_text(encoding="utf-8"))


def state(ws: Path, task_id: str) -> str:
    return next(t["state"] for t in data(ws)["tasks"] if t["id"] == task_id)


def fill(ws: Path, task_id: str, rows: str = ROW) -> Path:
    path = ws / tasks.default_report(task_id)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(SEP, SEP + rows, 1), encoding="utf-8")
    return path


def submitted(ws: Path, task_id: str = "T-001", req: str = "REQ-001") -> Path:
    """T-001 (or task_id) added, started, reported, filled and submitted."""
    if not (ws / tasks.TASKS_REL).exists() or not any(
        t["id"] == task_id for t in data(ws)["tasks"]
    ):
        assert kit(ws, "add", task_id, "--title", "CSV parser", "--requires", req)[0] == 0
    assert kit(ws, "start", task_id)[0] == EXIT_READY
    assert kit(ws, "report", task_id)[0] == EXIT_READY
    path = fill(ws, task_id, ROW.replace("REQ-001", req))
    code, out = kit(ws, "submit", task_id)
    assert code == EXIT_READY, out
    return path


def approve(ws: Path, task_id: str = "T-001"):
    return kit(ws, "approve", task_id, "--by", "agent-recorded", "--evidence", "승인")


# ---------------------------------------------------------------- add / start


def test_add_records_dependencies_and_list_shows_them(workspace):
    assert kit(workspace, "add", "T-001", "--title", "A", "--requires", "REQ-001")[0] == 0
    code, out = kit(
        workspace, "add", "T-002", "--title", "B", "--depends-on", "T-001", "--grade", "C"
    )
    assert code == EXIT_READY, out
    t2 = data(workspace)["tasks"][1]
    assert t2["depends_on"] == ["T-001"] and t2["grade"] == "C" and t2["state"] == "TODO"
    code, out = kit(workspace, "list")
    assert code == EXIT_READY and "T-002" in out and "TODO" in out


@pytest.mark.parametrize(
    "argv, code, message",
    [
        (["add", "T-001", "--title", "again"], EXIT_BLOCKED, "already exists"),
        (
            ["add", "T-009", "--title", "x", "--depends-on", "T-404"],
            EXIT_BLOCKED,
            "unknown task 'T-404'",
        ),
        (
            ["add", "T-009", "--title", "x", "--depends-on", "T-009"],
            EXIT_BLOCKED,
            "cannot depend on itself",
        ),
        (["add", "bad id", "--title", "x"], EXIT_USAGE, "task id"),
        (["add", "T-009", "--title", " "], EXIT_USAGE, "--title needs text"),
        (["add", "T-009", "--title", "x", "--grade", "Z"], EXIT_USAGE, "--grade"),
        (["add", "T-009", "--title", "x", "--requires", "req1"], EXIT_USAGE, "REQ-001"),
    ],
)
def test_bad_add_is_refused(workspace, capsys, argv, code, message):
    kit(workspace, "add", "T-001", "--title", "A")
    got, out = kit(workspace, *argv)
    assert got == code
    assert message in out + capsys.readouterr().err


def test_start_waits_for_an_approved_dependency(workspace):
    """TC-HTL-03 / V-14."""
    kit(workspace, "add", "T-001", "--title", "A", "--requires", "REQ-001")
    kit(workspace, "add", "T-002", "--title", "B", "--depends-on", "T-001")
    code, out = kit(workspace, "start", "T-002")
    assert code == EXIT_BLOCKED
    assert "cannot start T-002: T-001 is TODO, not APPROVED" in out
    submitted(workspace)
    code, out = kit(workspace, "start", "T-002")
    assert code == EXIT_BLOCKED and "T-001 is SUBMITTED, not APPROVED" in out
    approve(workspace)
    assert kit(workspace, "start", "T-002")[0] == EXIT_READY
    assert state(workspace, "T-002") == "IN_PROGRESS"


def test_only_one_task_in_progress(workspace):
    kit(workspace, "add", "T-001", "--title", "A")
    kit(workspace, "add", "T-002", "--title", "B")
    assert kit(workspace, "start", "T-001")[0] == EXIT_READY
    code, out = kit(workspace, "start", "T-002")
    assert code == EXIT_BLOCKED and "T-001 is IN_PROGRESS" in out
    code, out = kit(workspace, "start", "T-001")
    assert code == EXIT_BLOCKED and "only TODO or CHANGES_REQUESTED can start" in out


def test_submitted_or_approved_cannot_start_again(workspace):
    submitted(workspace)
    code, out = kit(workspace, "start", "T-001")
    assert code == EXIT_BLOCKED and "T-001 is SUBMITTED; only TODO" in out
    approve(workspace)
    code, out = kit(workspace, "start", "T-001")
    assert code == EXIT_BLOCKED and "T-001 is APPROVED; only TODO" in out


# ---------------------------------------------------------------- subtasks


def test_subtasks_need_no_approval_but_block_submit_until_done(workspace):
    """TC-HTL-01 / TC-HTL-02."""
    kit(workspace, "add", "T-001", "--title", "A", "--requires", "REQ-001")
    kit(workspace, "start", "T-001")
    code, out = kit(workspace, "subtask", "add", "T-001", "write tests")
    assert code == EXIT_READY and "T-001.1" in out
    kit(workspace, "report", "T-001")
    fill(workspace, "T-001")
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED and "subtask(s) not done: T-001.1" in out
    code, out = kit(workspace, "subtask", "done", "T-001.1")
    assert code == EXIT_READY and "no approval needed" in out
    assert data(workspace)["approvals"] == []
    assert kit(workspace, "submit", "T-001")[0] == EXIT_READY


def test_subtasks_only_while_in_progress(workspace):
    kit(workspace, "add", "T-001", "--title", "A")
    code, out = kit(workspace, "subtask", "add", "T-001", "x")
    assert code == EXIT_BLOCKED and "IN_PROGRESS" in out


# ---------------------------------------------------------------- report / submit


def test_report_template_has_every_5_6_section():
    """TC-HTL-05: the template carries the nine sections of 00_PROMPT 5.6."""
    text = (KIT_ROOT / tasks.TEMPLATE_REL).read_text(encoding="utf-8")
    prompt = (KIT_ROOT / "docs/v2/00_PROMPT.md").read_text(encoding="utf-8")
    block = prompt[prompt.index("### 5.6") :]
    block = block[block.index("```markdown") : block.index("```\n", block.index("```markdown") + 3)]
    headings = re.findall(r"^### \d\. .+$", block, re.M)
    assert len(headings) == 9
    for heading in headings:
        assert heading in text, heading
    assert (
        "| Test ID | Requirement | Scenario | Input/Condition | Expected | Actual | Status |"
        in text
    )


def test_report_fills_the_task_and_does_not_overwrite(workspace):
    kit(workspace, "add", "T-001", "--title", "CSV parser", "--requires", "REQ-001", "--grade", "C")
    code, out = kit(workspace, "report", "T-001")
    assert code == EXIT_READY
    text = (workspace / tasks.default_report("T-001")).read_text(encoding="utf-8")
    assert text.startswith("## [T-001] CSV parser — 완료 보고 (등급: C)")
    assert "- 관련 요구사항: REQ-001" in text
    code, out = kit(workspace, "report", "T-001")
    assert code == EXIT_BLOCKED and "--force" in out
    assert kit(workspace, "report", "T-001", "--force")[0] == EXIT_READY


def _started(ws, *reqs):
    argv = ["add", "T-001", "--title", "A"]
    for r in reqs:
        argv += ["--requires", r]
    kit(ws, *argv)
    kit(ws, "start", "T-001")


def test_submit_needs_a_report(workspace):
    _started(workspace, "REQ-001")
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED
    assert "report .kit/work/reports/T-001.md does not exist" in out
    assert state(workspace, "T-001") == "IN_PROGRESS"


def test_submit_needs_every_section(workspace):
    _started(workspace, "REQ-001")
    kit(workspace, "report", "T-001")
    path = fill(workspace, "T-001")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("### 7. 미검증·위험·한계", "### 미검증"), encoding="utf-8")
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED and "missing section(s) 7" in out


@pytest.mark.parametrize(
    "rows, problem",
    [
        ("", "no test row for must requirement REQ-001"),
        ("| … | REQ-001 | | | | | |\n", "no test row for must requirement REQ-001"),
        ("| TC-1 | REQ-0011 | x | x | x | x | PASS |\n", "no test row for must requirement"),
        ("| TC-1 | XREQ-001 | x | x | x | x | PASS |\n", "no test row for must requirement"),
        (
            "| TC-1 | REQ-001 | x | x | x | | NOT RUN |\n",
            "TC-1 (REQ-001) is NOT RUN without a reason",
        ),
        ("| TC-1 | REQ-001 | x | x | x | | NOT RUN: |\n", "NOT RUN without a reason"),
    ],
)
def test_submit_checks_the_test_table(workspace, rows, problem):
    _started(workspace, "REQ-001")
    kit(workspace, "report", "T-001")
    fill(workspace, "T-001", rows)
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED and problem in out


def test_not_run_with_a_reason_and_several_requirements_in_one_row(workspace):
    _started(workspace, "REQ-001", "REQ-002")
    kit(workspace, "report", "T-001")
    fill(workspace, "T-001", "| TC-1 | REQ-001, REQ-002 | x | x | x | | NOT RUN: needs a GPU |\n")
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_READY, out


def test_trace_priority_decides_must_once_trace_exists(workspace):
    """Reviewer decision 2026-11-07: every task requirement is must until trace.json exists."""
    _started(workspace, "REQ-001", "REQ-002")
    kit(workspace, "report", "T-001")
    fill(workspace, "T-001")  # a row for REQ-001 only
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED and "must requirement REQ-002" in out
    trace = {
        "schema": 1,
        "requirements": [
            {"id": "REQ-001", "text": "a", "priority": "must", "revision": 1},
            {"id": "REQ-002", "text": "b", "priority": "should", "revision": 1},
        ],
        "tests": [],
    }
    (workspace / tasks.TRACE_REL).write_text(json.dumps(trace), encoding="utf-8")
    assert kit(workspace, "submit", "T-001")[0] == EXIT_READY


def test_a_broken_trace_file_is_a_target_problem(workspace, capsys):
    _started(workspace, "REQ-001")
    kit(workspace, "report", "T-001")
    fill(workspace, "T-001")
    (workspace / tasks.TRACE_REL).write_text("{not json", encoding="utf-8")
    assert kit(workspace, "submit", "T-001")[0] == EXIT_TARGET
    assert "trace.json is not valid" in capsys.readouterr().err


def test_report_outside_the_workspace_is_refused(workspace, tmp_path):
    _started(workspace, "REQ-001")
    code, out = kit(workspace, "submit", "T-001", "--report", "../elsewhere.md")
    assert code == EXIT_BLOCKED and "outside the workspace" in out


def test_submit_only_from_in_progress(workspace):
    kit(workspace, "add", "T-001", "--title", "A")
    code, out = kit(workspace, "submit", "T-001")
    assert code == EXIT_BLOCKED and "only IN_PROGRESS can be submitted" in out


# ---------------------------------------------------------------- approve


def test_approve_only_when_submitted(workspace):
    kit(workspace, "add", "T-001", "--title", "A", "--requires", "REQ-001")
    code, out = approve(workspace)
    assert code == EXIT_BLOCKED and "only SUBMITTED can be approved" in out
    kit(workspace, "start", "T-001")
    assert approve(workspace)[0] == EXIT_BLOCKED
    assert data(workspace)["approvals"] == []


def test_agent_recorded_approval_keeps_the_words_and_the_report_hash(workspace):
    path = submitted(workspace)
    code, out = kit(
        workspace,
        "approve",
        "T-001",
        "--by",
        "agent-recorded",
        "--evidence",
        "승인 token=ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    )
    assert code == EXIT_READY and "by agent-recorded" in out
    (rec,) = data(workspace)["approvals"]
    assert rec["by"] == "agent-recorded" and rec["task"] == "T-001"
    assert rec["evidence"].startswith("승인") and "ghp_" not in rec["evidence"]
    import hashlib

    assert rec["report_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert state(workspace, "T-001") == "APPROVED"


def test_quote_is_the_spec_name_for_evidence(workspace):
    """05_CLI_SPEC 4.4 spells it --quote."""
    submitted(workspace)
    code, out = kit(workspace, "approve", "T-001", "--by", "agent-recorded", "--quote", "승인")
    assert code == EXIT_READY
    assert data(workspace)["approvals"][0]["evidence"] == "승인"


def test_agent_recorded_needs_evidence(workspace, capsys):
    submitted(workspace)
    code, _ = kit(workspace, "approve", "T-001", "--by", "agent-recorded")
    assert code == EXIT_USAGE and "--evidence" in capsys.readouterr().err
    assert state(workspace, "T-001") == "SUBMITTED"


def test_human_cli_needs_a_terminal(workspace):
    """TC-HTL-06: a non-interactive human-cli approval is refused."""
    submitted(workspace)
    code, out = kit(workspace, "approve", "T-001")
    assert code == EXIT_BLOCKED and "needs a person at a terminal" in out
    assert state(workspace, "T-001") == "SUBMITTED"


def test_human_cli_retypes_the_id(workspace):
    submitted(workspace)
    code, out = kit(workspace, "approve", "T-001", ask=lambda q: "T-002")
    assert code == EXIT_BLOCKED and "does not match" in out
    code, out = kit(workspace, "approve", "T-001", ask=lambda q: " T-001 ")
    assert code == EXIT_READY and "by human-cli" in out
    assert data(workspace)["approvals"][0]["by"] == "human-cli"


@pytest.mark.parametrize("argv", [["--by", "human-hook"], ["--evidence", "ok"]])
def test_cli_cannot_claim_a_hook_or_add_evidence_to_a_person(workspace, argv):
    submitted(workspace)
    code, _ = kit(workspace, "approve", "T-001", *argv, ask=lambda q: "T-001")
    assert code == EXIT_USAGE
    assert state(workspace, "T-001") == "SUBMITTED"


def test_a_report_changed_after_submit_cannot_be_approved(workspace):
    path = submitted(workspace)
    path.write_text(path.read_text(encoding="utf-8") + "late edit\n", encoding="utf-8")
    code, out = approve(workspace)
    assert code == EXIT_BLOCKED and "changed after submit; submit T-001 again" in out


def test_status_warns_when_an_approved_report_changes(workspace):
    path = submitted(workspace)
    approve(workspace)
    code, out = kit(workspace, "status")
    assert code == EXIT_READY and "Warning" not in out
    path.write_text(path.read_text(encoding="utf-8") + "edit\n", encoding="utf-8")
    code, out = kit(workspace, "status")
    assert code == EXIT_PARTIAL
    assert "T-001: report .kit/work/reports/T-001.md changed after approval" in out
    path.unlink()
    code, out = kit(workspace, "status", "--json")
    assert code == EXIT_PARTIAL
    assert json.loads(out)["warnings"] == [
        "T-001: report .kit/work/reports/T-001.md is missing after approval"
    ]


def test_request_changes_then_start_again(workspace):
    submitted(workspace)
    code, out = kit(workspace, "request-changes", "T-001", "--reason", "add an edge case")
    assert code == EXIT_READY and state(workspace, "T-001") == "CHANGES_REQUESTED"
    assert data(workspace)["tasks"][0]["history"][-1]["detail"] == "add an edge case"
    assert kit(workspace, "request-changes", "T-001", "--reason", "x")[0] == EXIT_BLOCKED
    assert kit(workspace, "start", "T-001")[0] == EXIT_READY


def test_status_shows_who_approved_and_what_can_start(workspace):
    kit(workspace, "add", "T-001", "--title", "A", "--requires", "REQ-001")
    kit(workspace, "add", "T-002", "--title", "B", "--depends-on", "T-001")
    code, out = kit(workspace, "status")
    assert "Can start:    T-001\n" in out and "waits for: T-001 is TODO, not APPROVED" in out
    submitted(workspace)
    approve(workspace)
    code, out = kit(workspace, "status", "--json")
    payload = json.loads(out)
    assert payload["can_start"] == ["T-002"]
    assert payload["tasks"][0]["approval"]["by"] == "agent-recorded"
    code, out = kit(workspace, "status")
    assert re.search(r"T-001\s+APPROVED\s+by agent-recorded", out)


# ---------------------------------------------------------------- the file


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d["tasks"][0]["depends_on"].append("T-002"), "dependency cycle"),
        (lambda d: d["tasks"][0].update(state="DONE"), "unknown state"),
        (lambda d: d["tasks"].append(dict(d["tasks"][0])), "listed twice"),
        (lambda d: d["tasks"][1]["depends_on"].append("T-404"), "unknown T-404"),
        (lambda d: d["approvals"].append({"task": "T-001", "by": "me"}), "approval record"),
        (lambda d: d.update(schema=2), "schema 1"),
    ],
)
def test_a_hand_edited_file_is_refused(workspace, capsys, change, message):
    kit(workspace, "add", "T-001", "--title", "A")
    kit(workspace, "add", "T-002", "--title", "B", "--depends-on", "T-001")
    d = data(workspace)
    change(d)
    (workspace / tasks.TASKS_REL).write_text(json.dumps(d), encoding="utf-8")
    code, _ = kit(workspace, "status")
    assert code == EXIT_TARGET
    assert message in capsys.readouterr().err


def test_find_cycle_reports_the_loop():
    graph = [
        {"id": "A", "depends_on": ["B"]},
        {"id": "B", "depends_on": ["C"]},
        {"id": "C", "depends_on": ["A"]},
        {"id": "D", "depends_on": []},
    ]
    assert tasks.find_cycle(graph) == ["A", "B", "C", "A"]
    assert tasks.find_cycle([{"id": "A", "depends_on": []}]) is None


def test_no_action_and_unknown_task(workspace, capsys):
    out = io.StringIO()
    assert commands.run(["task"], workspace, KIT_ROOT, out) == EXIT_USAGE
    code, out = kit(workspace, "start", "T-404")
    assert code == EXIT_BLOCKED and "no task 'T-404'" in out
    assert not (workspace / tasks.TASKS_REL).exists()  # nothing written on a refusal
