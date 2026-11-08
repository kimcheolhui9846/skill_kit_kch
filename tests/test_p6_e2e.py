"""P6-T5 E2E HITL scenario (00_PROMPT 11, P6-T5).

One fixture project goes through the whole human-in-the-loop flow. Every kit call is a real
`python -I run_kit.py ...` process, as bootstrap runs it: no terminal (stdin is closed), a
temporary HOME, and a new process each time, so nothing survives between calls except the
files under .kit/. The JUnit XML comes from a real pytest run inside the fixture project.

1. three requirements, two tasks (T-2 depends on T-1)
2. T-1 started; submit without a report is refused; submit with the report and JUnit works
3. T-2 cannot start before T-1 is approved (exit 2)
4. T-1 approved; HANDOFF.md is rebuilt with the approved state
5. WIP saved while T-2 runs; a new process (the "restarted session") runs `recover`, which
   shows T-1 approved and the T-2 WIP apart
6. a requirement is revised; `req impact` names the test to review

The scenario runs once (module fixture); each step is checked by its own test.
"""

from __future__ import annotations

import json
import locale
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kit import tasks
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY
from tests.conftest import KIT_ROOT

SEP = "|---|---|---|---|---|---|---|\n"
WIP_NOTE = "mean() half done; empty list case left"

CALC = """def add(a, b):
    return a + b


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("b is 0")
    return a / b
"""
TEST_CALC = """import pytest

from calc import add, div


def test_add():
    assert add(2, 3) == 5


def test_div_by_zero():
    with pytest.raises(ZeroDivisionError):
        div(1, 0)
"""
STATS = """def mean(xs):
    return sum(xs) / len(xs)
"""


def _env(home: Path) -> dict:
    env = dict(os.environ)
    for name in ("HOME", "USERPROFILE"):
        env[name] = str(home)
    env["CODEX_HOME"] = str(home / ".codex")
    env["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
    return env


class Project:
    def __init__(self, root: Path, home: Path):
        self.root, self.home, self.env = root, home, _env(home)
        self.calls = []

    def kit(self, *argv):
        """(exit code, stdout) of one fresh kit process with no terminal."""
        proc = subprocess.run(
            [sys.executable, "-I", str(KIT_ROOT / "run_kit.py"), *argv],
            cwd=str(self.root),
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        enc = locale.getpreferredencoding(False)
        out = proc.stdout.decode(enc, "replace") + proc.stderr.decode(enc, "replace")
        self.calls.append((argv, proc.returncode))
        return proc.returncode, out

    def ok(self, *argv) -> str:
        code, out = self.kit(*argv)
        assert code == EXIT_READY, (argv, out)
        return out

    def json(self, *argv):
        code, out = self.kit(*argv, "--json")
        return code, json.loads(out)

    def pytest(self, *paths) -> int:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
            + ["--junitxml=out/junit.xml", *paths],
            cwd=str(self.root),
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        return proc.returncode

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def read(self, rel: str) -> str:
        return (self.root / rel).read_bytes().decode("utf-8")


def _fill_report(p: Project, task_id: str, table_md: str, next_step: str) -> str:
    """Paste the evidence table rows into section 4 and fill the summary, as a person would."""
    rel = tasks.default_report(task_id)
    text = p.read(rel)
    rows = "".join(line + "\n" for line in table_md.splitlines() if line.startswith("| TC-"))
    assert rows, table_md
    text = text.replace(SEP, SEP + rows, 1)
    text = text.replace("- 무엇을 했는가(3줄 이내):", f"- 무엇을 했는가(3줄 이내): {task_id} calc")
    text = text.replace("승인하시면 다음으로 <Task ID: 내용>을 진행합니다.", next_step)
    p.write(rel, text)
    return rel


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """Runs the six steps in order and keeps what each step showed."""
    base = tmp_path_factory.mktemp("e2e")
    root, home = base / "e2e 프로젝트", base / "home"
    root.mkdir()
    home.mkdir()
    p = Project(root, home)
    p.write("pytest.ini", "[pytest]\n")
    p.write("calc.py", CALC)
    p.write("tests/test_calc.py", TEST_CALC)
    s = {"project": p}

    # 1. requirements and tasks
    for rid, text in (
        ("REQ-001", "add returns the sum"),
        ("REQ-002", "div refuses a zero divisor"),
        ("REQ-003", "mean of a list"),
    ):
        p.ok("req", "add", rid, "--text", text)
    p.ok("trace", "link", "TC-001", "--req", "REQ-001", "--locator",
         "tests/test_calc.py::test_add", "--case", "normal")  # fmt: skip
    p.ok("trace", "link", "TC-002", "--req", "REQ-002", "--locator",
         "tests/test_calc.py::test_div_by_zero", "--case", "error")  # fmt: skip
    p.ok("task", "add", "T-1", "--title", "calc", "--requires", "REQ-001", "--requires", "REQ-002")
    p.ok("task", "add", "T-2", "--title", "stats", "--requires", "REQ-003", "--depends-on", "T-1")
    s["reqs"] = p.json("req", "list")
    s["tasks_1"] = p.json("task", "list")

    # 2. T-1: start, submit refused twice, then submit with report and JUnit
    p.ok("task", "start", "T-1")
    s["submit_no_report"] = p.kit("task", "submit", "T-1")
    p.ok("task", "report", "T-1")
    s["submit_empty_report"] = p.kit("task", "submit", "T-1")
    s["pytest_t1"] = p.pytest("tests")
    s["evidence"] = p.json(
        "report", "tests", "--junit", "out/junit.xml", "--out", ".kit/work/reports/T-1-tests.md"
    )
    table = p.read(".kit/work/reports/T-1-tests.md")
    s["report_rel"] = _fill_report(p, "T-1", table, "승인하시면 다음으로 T-2: stats를 진행합니다.")
    s["submit"] = p.kit("task", "submit", "T-1")

    # 3. T-2 before T-1 is approved
    s["start_t2_early"] = p.kit("task", "start", "T-2")
    s["handoff_before"] = (root / ".kit/work/HANDOFF.md").exists()

    # 4. approval: no terminal -> human-cli refused; the agent records the user's words
    s["approve_no_terminal"] = p.kit("task", "approve", "T-1")
    s["approve"] = p.kit("task", "approve", "T-1", "--by", "agent-recorded", "--evidence", "승인")
    s["handoff"] = p.read(".kit/work/HANDOFF.md")

    # 5. T-2 in progress, WIP saved, the session ends; a new process recovers
    s["start_t2"] = p.kit("task", "start", "T-2")
    p.write("stats.py", STATS)
    p.ok("recover", "save", "--note", WIP_NOTE, "--command", "pytest tests", "--tests", "2 passed")
    s["wip_file"] = json.loads(p.read(".kit/work/wip.json"))
    s["recover_json"] = p.json("recover")
    s["recover_text"] = p.kit("recover")
    s["handoff_after_wip"] = p.read(".kit/work/HANDOFF.md")

    # 6. REQ-002 is revised
    s["edit"] = p.kit("req", "edit", "REQ-002", "--text", "div refuses zero and None divisors")
    s["impact_002"] = p.json("req", "impact", "REQ-002")
    s["impact_001"] = p.json("req", "impact", "REQ-001")
    s["trace_check"] = p.json("trace", "check")
    s["home_files"] = [x for x in home.rglob("*") if x.is_file()]
    return s


def test_step1_requirements_and_dependent_tasks(run):
    code, reqs = run["reqs"]
    assert code == EXIT_READY
    assert [r["id"] for r in reqs["requirements"]] == ["REQ-001", "REQ-002", "REQ-003"]
    assert all(r["revision"] == 1 for r in reqs["requirements"])
    code, listed = run["tasks_1"]
    by_id = {t["id"]: t for t in listed["tasks"]}
    assert by_id["T-1"]["state"] == by_id["T-2"]["state"] == "TODO"
    assert by_id["T-2"]["depends_on"] == ["T-1"]
    assert listed["can_start"] == ["T-1"]


def test_step2_submit_needs_the_report_and_the_evidence(run):
    code, out = run["submit_no_report"]
    assert code == EXIT_BLOCKED
    assert "does not exist" in out and "kit task report T-1" in out
    code, out = run["submit_empty_report"]  # the template alone has no test rows
    assert code == EXIT_BLOCKED
    assert "no test row for must requirement REQ-001" in out
    assert "no test row for must requirement REQ-002" in out
    assert run["pytest_t1"] == 0  # the JUnit XML is a real run
    code, ev = run["evidence"]
    # PARTIAL by design: REQ-003 belongs to T-2 and has no test yet. T-1's own rows all pass.
    assert code == EXIT_PARTIAL, ev
    assert ev["totals"] == {"pass": 2, "fail": 0, "skipped": 0, "not_run": 0}
    no_test = [q["id"] for q in ev["requirements"] if not q["tests"]]
    assert no_test == ["REQ-003"]
    code, out = run["submit"]
    assert code == EXIT_READY, out
    assert f"Submitted:    T-1 with {run['report_rel']}" in out
    report = run["project"].read(run["report_rel"])
    assert "| TC-001 | REQ-001 |" in report and "| TC-002 | REQ-002 |" in report


def test_step3_dependent_task_waits_for_approval(run):
    code, out = run["start_t2_early"]
    assert code == EXIT_BLOCKED == 2
    assert "cannot start T-2: T-1 is SUBMITTED, not APPROVED" in out
    assert run["handoff_before"] is False  # nothing approved yet, no handoff


def test_step4_approval_updates_handoff(run):
    code, out = run["approve_no_terminal"]
    assert code == EXIT_BLOCKED
    assert "needs a person at a terminal" in out
    code, out = run["approve"]
    assert code == EXIT_READY, out
    assert "Approved:     T-1 by agent-recorded" in out
    assert "Handoff:      .kit/work/HANDOFF.md updated (approved state only)" in out
    h = run["handoff"]
    assert h.startswith("<!-- kit:handoff approvals=1 last=T-1@")
    assert "- ID / 제목: T-1 / calc" in h
    assert "- 승인 기록 방식: agent-recorded" in h
    assert "PASS 2" in h  # the approved report's section 4
    assert "승인하시면 다음으로 T-2: stats를 진행합니다." in h
    assert "| T-1 | calc |" in h


def test_step5_recover_keeps_approved_and_wip_apart(run):
    code, out = run["start_t2"]
    assert code == EXIT_READY, out
    assert run["wip_file"]["task"] == "T-2" and run["wip_file"]["note"] == WIP_NOTE
    code, res = run["recover_json"]
    assert code == EXIT_READY, res
    a = res["approved"]
    assert a["approved"] == ["T-1"]
    assert a["last_approved"]["id"] == "T-1"
    assert a["current"]["id"] == "T-2" and a["current"]["state"] == "IN_PROGRESS"
    assert a["tests"] == {"PASS": 2}
    assert res["wip"]["task"] == "T-2" and res["wip"]["note"] == WIP_NOTE
    assert "stale" not in res["wip"]  # T-2 is not approved, so the WIP is current
    code, text = run["recover_text"]
    assert code == EXIT_READY
    approved, sep, temporary = text.partition("Temporary (not approved")
    assert sep, text
    assert "Last approved:  T-1" in approved and "Current task:   T-2 IN_PROGRESS" in approved
    assert WIP_NOTE not in approved
    assert "Task:           T-2" in temporary and WIP_NOTE in temporary
    assert WIP_NOTE not in run["handoff_after_wip"]  # HANDOFF.md holds approved state only


def test_step6_revised_requirement_names_the_tests_to_review(run):
    code, out = run["edit"]
    assert code == EXIT_READY, out
    assert "Edited:       REQ-002 (must) r2" in out
    assert "Review:       TC-002 tests/test_calc.py::test_div_by_zero (saw r1)" in out
    code, imp = run["impact_002"]
    assert code == EXIT_READY
    assert imp["requirement"]["revision"] == 2
    assert imp["tests"] == ["TC-002"] and imp["review"] == ["TC-002"]
    code, imp = run["impact_001"]
    assert imp["tests"] == ["TC-001"] and imp["review"] == []
    code, chk = run["trace_check"]
    assert any("TC-002" in json.dumps(f) for f in chk["findings"])


def test_scenario_left_home_alone_and_used_no_terminal(run):
    assert run["home_files"] == []
    assert len(run["project"].calls) >= 25
