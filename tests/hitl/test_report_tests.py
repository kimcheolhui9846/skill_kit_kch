"""P5-T4 evidence-based test report (00_PROMPT 10.4, ADR-012, REQ-TEST-001/002, REQ-TRACE-005).

TC-HTL-07 the section 4 table has every column, TC-HTL-08 JUnit from pytest, vitest and
go-junit-report (missing locator -> NOT RUN, skipped/error), TC-HTL-13 implementation
correctness and test design adequacy are separate sections.

fixtures/junit/pytest.xml is real pytest output (path, host and time replaced);
vitest.xml and go.xml are hand-written in those reporters' formats (neither tool is here).
"""

from __future__ import annotations

import io
import json
import re
import shutil
from pathlib import Path

import pytest

from kit import commands, evidence, junit, tasks, trace
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import KIT_ROOT

FIXTURES = Path(__file__).parent / "fixtures" / "junit"
COLUMNS = "| Test ID | Requirement | Scenario | Input/Condition | Expected | Actual | Status |"


def kit(ws: Path, *argv):
    out = io.StringIO()
    code = commands.run([*argv, "--target", str(ws)], ws, KIT_ROOT, out)
    return code, out.getvalue()


def setup(ws: Path, reqs, tests, fixtures=("pytest",)):
    """reqs: [(id, priority)]; tests: [(test id, [req ids], locator, case)]."""
    for req_id, prio in reqs:
        assert kit(ws, "req", "add", req_id, "--text", f"{req_id} text", "--priority", prio)[0] == 0
    for test_id, req_ids, locator, case in tests:
        argv = ["trace", "link", test_id, "--locator", locator, "--case", case]
        for r in req_ids:
            argv += ["--req", r]
        assert kit(ws, *argv)[0] == 0
    (ws / "out").mkdir(exist_ok=True)
    for name in fixtures:
        shutil.copy(FIXTURES / f"{name}.xml", ws / "out" / f"{name}.xml")


def report(ws: Path, *names, json_out=True):
    argv = ["report", "tests"]
    for n in names or ("pytest",):
        argv += ["--junit", f"out/{n}.xml"]
    if json_out:
        argv.append("--json")
    code, out = kit(ws, *argv)
    return code, (json.loads(out) if json_out else out)


def statuses(payload) -> dict:
    return {t["id"]: t["status"] for t in payload["tests"]}


PY = "tests/test_csv.py"


def pytest_ws(ws: Path):
    setup(
        ws,
        [("REQ-001", "must"), ("REQ-002", "must"), ("REQ-003", "should"), ("REQ-004", "could")],
        [
            ("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary"),
            ("TC-002", ["REQ-002"], f"{PY}::test_field_count", "normal"),
            ("TC-003", ["REQ-002"], f"{PY}::test_uses_broken", "error"),
            ("TC-004", ["REQ-003"], f"{PY}::test_large_file", "normal"),
            ("TC-005", ["REQ-001"], f"{PY}::TestQuoted::test_keeps_quotes", "normal"),
            ("TC-006", ["REQ-003"], f"{PY}::test_not_written_yet", "error"),
        ],
    )


# ---------------------------------------------------------------- JUnit dialects (TC-HTL-08)


def test_pytest_outcomes(workspace):
    pytest_ws(workspace)
    code, payload = report(workspace)
    assert code == EXIT_PARTIAL
    assert statuses(payload) == {
        "TC-001": "PASS",
        "TC-002": "FAIL",  # one of three parametrised cases failed
        "TC-003": "FAIL",  # a setup error counts as FAIL
        "TC-004": "SKIPPED",
        "TC-005": "PASS",  # class test: tests.test_csv.TestQuoted
        "TC-006": "NOT RUN",  # traced, but no JUnit file has it (R-01)
    }
    actual = {t["id"]: t["actual"] for t in payload["tests"]}
    assert actual["TC-002"] == ('3 cases: PASS 2, FAIL 1; test_field_count["a,b"-1]: assert 2 == 1')
    assert actual["TC-003"].startswith('error (0.00s): failed on setup with "RuntimeError')
    assert actual["TC-004"] == "skipped (0.00s): needs a large file"
    assert actual["TC-006"] == "-"
    assert payload["totals"] == {"pass": 2, "fail": 2, "skipped": 1, "not_run": 1}
    assert payload["untracked"] == []
    reqs = {q["id"]: q["status"] for q in payload["requirements"]}
    assert reqs == {
        "REQ-001": "PASS",
        "REQ-002": "FAIL",
        "REQ-003": "NOT RUN",
        "REQ-004": "NO TEST",
    }


def test_vitest_names_and_masking(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [
            ("TC-001", ["REQ-001"], "src/sum.test.ts::sum > adds two numbers", "normal"),
            ("TC-002", ["REQ-001"], "src/sum.test.ts::sum > handles negatives", "error"),
            ("TC-003", ["REQ-001"], "src/sum.test.ts::sum > big numbers", "boundary"),
            ("TC-004", ["REQ-001"], "src/sum.test.ts::sum > a | b in the name", "normal"),
        ],
        fixtures=("vitest",),
    )
    code, payload = report(workspace, "vitest")
    assert statuses(payload) == {
        "TC-001": "PASS",
        "TC-002": "FAIL",
        "TC-003": "SKIPPED",
        "TC-004": "PASS",
    }
    assert [u["testcase"] for u in payload["untracked"]] == ["src/parse/test/parse > reads one row"]
    text = json.dumps(payload) + report(workspace, "vitest", json_out=False)[1]
    assert "FAKEKEY" not in text and "api_key=***" in text  # V-17
    assert "추적되지 않은 테스트 1개(요구사항과 연결 안 됨)" in text
    md = report(workspace, "vitest", json_out=False)[1]
    row = next(line for line in md.splitlines() if line.startswith("| TC-004 "))
    assert len(row.strip("|").split("|")) == 7  # the '|' in the name does not add a cell


def test_go_subtests_are_their_own_tests(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [
            ("TC-001", ["REQ-001"], "example.com/calc::TestAdd", "normal"),
            ("TC-002", ["REQ-001"], "example.com/calc::TestDiv/positive", "boundary"),
            ("TC-003", ["REQ-001"], "example.com/calc::TestBig", "normal"),
        ],
        fixtures=("go",),
    )
    code, payload = report(workspace, "go")
    assert statuses(payload) == {"TC-001": "PASS", "TC-002": "PASS", "TC-003": "SKIPPED"}
    assert sorted(u["testcase"] for u in payload["untracked"]) == [
        "example/com/calc/TestDiv",
        "example/com/calc/TestDiv/negative",
    ]


def test_several_junit_files_are_joined(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [
            ("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary"),
            ("TC-002", ["REQ-001"], "example.com/calc::TestAdd", "normal"),
        ],
        fixtures=("pytest", "go"),
    )
    code, payload = report(workspace, "pytest", "go")
    assert statuses(payload) == {"TC-001": "PASS", "TC-002": "PASS"}
    assert payload["sources"] == ["out/pytest.xml", "out/go.xml"]
    assert len(payload["untracked"]) == 6 + 4


# ---------------------------------------------------------------- matching


@pytest.mark.parametrize(
    "locator, keys",
    [
        (f"{PY}::test_field_count", 3),  # every parametrised case
        (f"{PY}::test_field_count[a-1]", 1),  # exactly that one
        (f"{PY}::test_field_count[a", 0),  # no partial parameters
        (f"{PY}::test_field", 0),  # no prefix of a name
        ("tests/test_csv::test_empty_file", 1),  # extension optional
        (r"tests\test_csv.py::test_empty_file", 1),  # Windows separators
        ("tests.test_csv::test_empty_file", 1),  # module form
        ("other/test_csv.py::test_empty_file", 0),  # same name, other file: never
        ("test_empty_file", 0),  # a bare name never matches
        ("", 0),
    ],
)
def test_locator_matching(locator, keys):
    cases = junit.parse(FIXTURES / "pytest.xml", "pytest.xml")
    key = junit.normalise(locator)
    assert len([c for c in cases if key and junit.matches(key, c)]) == keys


def test_parametrised_case_named_in_the_locator(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [("TC-001", ["REQ-001"], f"{PY}::test_field_count[a-1]", "boundary")],
    )
    code, payload = report(workspace)
    assert (code, statuses(payload)) == (EXIT_READY, {"TC-001": "PASS"})
    assert payload["tests"][0]["actual"].startswith("passed")


def test_all_skipped_parametrised_is_skipped_and_mixed_skip_passes(tmp_path):
    xml = tmp_path / "j.xml"
    xml.write_text(
        '<testsuite name="s"><testcase classname="t" name="a[1]"><skipped/></testcase>'
        '<testcase classname="t" name="a[2]"><skipped/></testcase>'
        '<testcase classname="t" name="b[1]"><skipped/></testcase>'
        '<testcase classname="t" name="b[2]"/></testsuite>',
        encoding="utf-8",
    )
    cases = junit.parse(xml, "j.xml")
    data = trace.empty()
    trace.add_req(data, "REQ-1", "x", "must")
    trace.link(data, "A", ["REQ-1"], "t::a", "boundary")
    trace.link(data, "B", ["REQ-1"], "t::b", "boundary")
    rows = {r.test["id"]: r for r in evidence.build(data, cases, ["j.xml"]).rows}
    assert rows["A"].status == "SKIPPED" and rows["A"].actual == "2 cases: SKIPPED 2"
    assert rows["B"].status == "PASS" and rows["B"].actual == "2 cases: PASS 1, SKIPPED 1"


# ---------------------------------------------------------------- the report (07, 13)


def test_report_sections_and_columns(workspace):
    pytest_ws(workspace)
    code, md = report(workspace, json_out=False)
    assert code == EXIT_PARTIAL
    assert COLUMNS in md  # TC-HTL-07
    correct, design = md.index("## 구현 정확성"), md.index("## 테스트 설계 타당성")
    answers = md.index("## 질문 6개에 대한 답")
    assert correct < design < answers  # TC-HTL-13: separate sections
    assert "| REQ-002 | must | TC-002, TC-003 | FAIL |" in md[correct:design]
    assert "| REQ-002 | must | 1 | 0 | 1 | 0 | 기록 없음 |" in md[design:answers]
    assert "| REQ-004 | could | 0 | 0 | 0 | 0 | 기록 없음 | UNTESTED |" in md[design:answers]
    for n in range(1, 7):
        assert re.search(rf"^{n}\. ", md[answers:], re.M)
    assert "4. 실패한 테스트는 무엇인가? TC-002, TC-003." in md
    assert "연결된 테스트가 모두 PASS: REQ-001. trace.json에 implemented로 기록: 없음." in md
    assert (
        "6. 사람이 추가로 검토해야 하는 위험은 무엇인가? REQ-002: must FAIL, REQ-004: UNTESTED."
        in md
    )
    assert "NOT RUN: TC-006." in md
    assert "PASS 2 / FAIL 2 / SKIPPED 1 / NOT RUN 1" in md
    assert "| TC-006 | REQ-003 | error case | - | - | - | NOT RUN: not in the JUnit XML |" in md


def test_the_table_can_be_pasted_into_a_task_report(workspace):
    """The rows parse with kit task's own reader, NOT RUN has its reason, and the report adds
    no numbered section that would confuse `kit task submit`."""
    pytest_ws(workspace)
    md = report(workspace, json_out=False)[1]
    assert not re.search(r"^#{2,4}\s*\d\.\s", md, re.M)
    start = md.index(COLUMNS)
    table = md[start : md.index("\n\n", start)]  # what a person pastes into section 4
    design = md[md.index("## 테스트 설계 타당성") :]  # and this into section 5
    rows = tasks.test_rows(f"### 4. 테스트 결과\n{table}\n### 5. 설계\n{design}")
    assert [r["test"] for r in rows] == [f"TC-00{i}" for i in range(1, 7)]
    assert rows[5]["status"] == "NOT RUN: not in the JUnit XML"


def test_design_section_counts_cases_and_risks(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [
            ("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "normal"),
            ("TC-002", ["REQ-001"], f"{PY}::TestQuoted::test_keeps_quotes", "normal"),
        ],
    )
    kit(workspace, "req", "edit", "REQ-001", "--text", "revised")
    code, payload = report(workspace)
    q = payload["requirements"][0]
    assert q["cases"] == {"normal": 2, "boundary": 0, "error": 0, "counterexample": 0}
    assert q["risks"] == ["WEAK", "STALE TC-001, TC-002"]
    assert code == EXIT_READY  # every test passed: risks are for the reviewer, not the exit code
    kit(
        workspace,
        "trace",
        "link",
        "TC-003",
        "--req",
        "REQ-001",
        "--locator",
        f"{PY}::test_field_count",
        "--case",
        "counterexample",
    )
    md = report(workspace, json_out=False)[1]
    assert "| REQ-001 | must | 2 | 0 | 0 | 1 | 기록 없음 (반례 테스트 있음) |" in md
    assert "must FAIL" in md


def test_input_and_expected_come_from_trace_link(workspace):
    setup(workspace, [("REQ-001", "must")], [])
    kit(
        workspace,
        "trace",
        "link",
        "TC-001",
        "--req",
        "REQ-001",
        "--locator",
        f"{PY}::test_empty_file",
        "--case",
        "boundary",
        "--purpose",
        "empty input",
        "--input",
        "''",
        "--expected",
        "[]",
    )
    shutil.copy(FIXTURES / "pytest.xml", workspace / "out" / "pytest.xml")
    md = report(workspace, json_out=False)[1]
    assert "| TC-001 | REQ-001 | empty input | '' | [] | passed (0.00s) | PASS |" in md


def test_unknown_and_unlinked_tests_are_named(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary")],
    )
    doc = json.loads((workspace / trace.TRACE_REL).read_text(encoding="utf-8"))
    doc["tests"].append(dict(doc["tests"][0], id="TC-002", requirements=[]))
    (workspace / trace.TRACE_REL).write_text(json.dumps(doc), encoding="utf-8")
    md = report(workspace, json_out=False)[1]
    assert "- NO_REQUIREMENTS TC-002: links no requirement" in md
    assert "TC-002: NO_REQUIREMENTS" in md  # question 6


# ---------------------------------------------------------------- exit codes and output


def test_everything_passing_is_ready(workspace):
    setup(
        workspace,
        [("REQ-001", "must")],
        [("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary")],
    )
    code, out = kit(
        workspace, "report", "tests", "--junit", "out/pytest.xml", "--out", "reports/tests.md"
    )
    assert code == EXIT_READY
    assert "Report:       reports/tests.md" in out and "Status:       READY" in out
    assert "Untracked:    6 JUnit" in out
    written = (workspace / "reports/tests.md").read_text(encoding="utf-8")
    assert written == report(workspace, json_out=False)[1]


@pytest.mark.parametrize(
    "reqs, tests, problem",
    [
        ([], [], "no traced test"),
        (
            [("REQ-001", "must"), ("REQ-002", "could")],
            [("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary")],
            "requirements without tests: REQ-002",
        ),
        (
            [("REQ-001", "must")],
            [("TC-001", ["REQ-001"], f"{PY}::nope", "boundary")],
            "FAIL 0, NOT RUN 1, SKIPPED 0",
        ),
        (
            [("REQ-001", "could")],
            [("TC-001", ["REQ-001"], f"{PY}::test_large_file", "error")],
            "FAIL 0, NOT RUN 0, SKIPPED 1",
        ),
    ],
)
def test_anything_short_of_all_pass_is_partial(workspace, reqs, tests, problem):
    setup(workspace, reqs, tests)
    code, out = kit(workspace, "report", "tests", "--junit", "out/pytest.xml", "--out", "r.md")
    assert code == EXIT_PARTIAL
    assert f"Problem:      {problem}" in out and "Status:       PARTIAL" in out
    assert (workspace / "r.md").is_file()  # the report is written anyway


@pytest.mark.parametrize(
    "xml, message",
    [
        (None, "does not exist"),
        ("<testsuites><testsuite>", "is not valid XML"),
        ('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><testsuite/>', "DOCTYPE"),
        ('<?xml version="1.0"?><!doctype x><testsuite/>', "DOCTYPE"),
        ("<results/>", "root is <results>"),
        ('<testsuite><testcase classname="a"/></testsuite>', "has no name"),
        (b"\xff\xfe<testsuite/>", "is not valid XML"),
    ],
)
def test_unusable_junit_blocks_and_writes_nothing(workspace, xml, message):
    setup(
        workspace,
        [("REQ-001", "must")],
        [("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary")],
        fixtures=(),
    )
    if xml is not None:
        data = xml if isinstance(xml, bytes) else xml.encode("utf-8")
        (workspace / "out" / "bad.xml").write_bytes(data)
    code, out = kit(workspace, "report", "tests", "--junit", "out/bad.xml", "--out", "r.md")
    assert code == EXIT_BLOCKED and message in out and "Status:       BLOCKED" in out
    assert not (workspace / "r.md").exists()
    code, out = kit(workspace, "report", "tests", "--junit", "out/bad.xml", "--json")
    assert json.loads(out)["status"] == "BLOCKED" and code == EXIT_BLOCKED


@pytest.mark.parametrize(
    "out, message",
    [
        (".kit/work/trace.json", "only .kit/work/reports/"),
        (".kit/state.json", "only .kit/work/reports/"),
        (".kit", "only .kit/work/reports/"),
        ("out/pytest.xml", "is one of the --junit files"),
        ("out", "is a folder"),
    ],
)
def test_out_never_replaces_evidence_or_state(workspace, out, message):
    setup(
        workspace,
        [("REQ-001", "must")],
        [("TC-001", ["REQ-001"], f"{PY}::test_empty_file", "boundary")],
    )
    before = (workspace / trace.TRACE_REL).read_bytes()
    code, text = kit(workspace, "report", "tests", "--junit", "out/pytest.xml", "--out", out)
    assert code == EXIT_BLOCKED and message in text
    assert (workspace / trace.TRACE_REL).read_bytes() == before
    assert (workspace / "out/pytest.xml").read_bytes() == (FIXTURES / "pytest.xml").read_bytes()
    code, text = kit(
        workspace,
        "report",
        "tests",
        "--junit",
        "out/pytest.xml",
        "--out",
        ".kit/work/reports/tests.md",
    )
    assert code == EXIT_READY, text


def test_out_stays_in_the_workspace(workspace):
    setup(workspace, [], [])
    code, out = kit(workspace, "report", "tests", "--junit", "out/pytest.xml", "--out", "../r.md")
    assert code == EXIT_BLOCKED and "outside the workspace" in out
    assert not (workspace.parent / "r.md").exists()


def test_junit_outside_the_workspace_is_shown_without_the_home_path(workspace, tmp_path):
    setup(workspace, [], [], fixtures=())
    home = Path.home()
    shutil.copy(FIXTURES / "pytest.xml", home / "j.xml")
    shutil.copy(FIXTURES / "pytest.xml", tmp_path / "elsewhere.xml")
    code, out = kit(
        workspace,
        "report",
        "tests",
        "--junit",
        str(home / "j.xml"),
        "--junit",
        str(tmp_path / "elsewhere.xml"),
        "--json",
    )
    sources = json.loads(out)["sources"]
    assert sources[0] == "~/j.xml"
    assert sources[1] == (tmp_path / "elsewhere.xml").resolve().as_posix()


@pytest.mark.parametrize(
    "argv, message",
    [
        (["report"], "report needs a kind"),
        (["report", "tests"], "--junit FILE is needed"),
    ],
)
def test_usage_errors(workspace, capsys, argv, message):
    code = commands.run(
        [*argv, *(["--target", str(workspace)] if len(argv) > 1 else [])],
        workspace,
        KIT_ROOT,
        io.StringIO(),
    )
    assert code == EXIT_USAGE and message in capsys.readouterr().err


def test_broken_trace_is_a_target_problem(workspace):
    setup(workspace, [], [])
    (workspace / trace.TRACE_REL).parent.mkdir(parents=True, exist_ok=True)
    (workspace / trace.TRACE_REL).write_text("{oops", encoding="utf-8")
    assert kit(workspace, "report", "tests", "--junit", "out/pytest.xml")[0] == EXIT_TARGET


def test_json_without_out_carries_the_markdown(workspace):
    pytest_ws(workspace)
    code, payload = report(workspace)
    assert payload["report"] is None and payload["markdown"].startswith("# 테스트 보고서")
    assert payload["exit_code"] == code == EXIT_PARTIAL
    code, out = kit(
        workspace, "report", "tests", "--junit", "out/pytest.xml", "--out", "r.md", "--json"
    )
    payload = json.loads(out)
    assert payload["report"] == "r.md" and "markdown" not in payload


def test_cells_messages_and_names_are_kept_safe(workspace, tmp_path):
    """Pipes and line breaks never split a row; long messages are cut; untracked names are
    masked in JSON too; a testcase without classname takes the file, then the suite name."""
    long = "x" * 400
    (workspace / "out").mkdir()
    (workspace / "out" / "j.xml").write_text(
        '<testsuites><testsuite name="pkg">'
        f'<testcase classname="t" name="long"><failure message="{long}"/></testcase>'
        '<testcase name="TestNoClass"/>'
        '<testcase file="f.py" name="test_file_attr"/>'
        '<testcase classname="t" name="token=abcdef123456secret"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    setup(workspace, [("REQ-001", "must"), ("REQ-002", "could")], [], fixtures=())
    for test_id, locator in (
        ("TC-001", "t::long"),
        ("TC-002", "pkg::TestNoClass"),
        ("TC-003", "f.py::test_file_attr"),
    ):
        kit(
            workspace,
            "trace",
            "link",
            test_id,
            "--req",
            "REQ-001",
            "--locator",
            locator,
            "--case",
            "error",
            "--purpose",
            "a | b\nnext line",
        )
    code, out = kit(workspace, "report", "tests", "--junit", "out/j.xml", "--json")
    payload = json.loads(out)
    assert statuses(payload) == {"TC-001": "FAIL", "TC-002": "PASS", "TC-003": "PASS"}
    actual = payload["tests"][0]["actual"]
    assert actual == "failed (0.00s): " + "x" * 157 + "..."
    assert payload["untracked"] == [{"testcase": "t/token=***", "status": "PASS"}]
    md = payload["markdown"]
    assert "secret" not in md
    row = next(line for line in md.splitlines() if line.startswith("| TC-002 "))
    assert "| a / b next line |" in row and len(row.strip("|").split("|")) == 7
    req2 = next(q for q in payload["requirements"] if q["id"] == "REQ-002")
    assert req2["risks"] == ["UNTESTED"]  # could: no "must ..." risk


def test_a_could_requirement_that_did_not_pass_is_not_a_must_risk(workspace):
    setup(
        workspace,
        [("REQ-001", "could")],
        [("TC-001", ["REQ-001"], f"{PY}::test_large_file", "error")],
    )
    code, payload = report(workspace)
    assert payload["requirements"][0]["status"] == "SKIPPED"
    assert payload["requirements"][0]["risks"] == []
