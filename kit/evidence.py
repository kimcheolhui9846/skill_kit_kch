"""Evidence-based test report: trace.json + JUnit XML (P5-T4, 00_PROMPT 10.4, ADR-012).

REQ-TEST-001/002, REQ-TRACE-005. Actual and Status come only from JUnit XML; a traced test
that no JUnit file has is NOT RUN, never PASS (R-01).

Reviewer decisions 2026-11-07: locators match after normalising (kit.junit); parametrised
cases of one locator are one row (any FAIL/ERROR -> FAIL, all SKIPPED -> SKIPPED, else PASS);
the report goes to --out FILE or stdout; exit 1 unless every traced test passed and every
requirement has one.

The section 4 table is written so that it can be pasted into a task report and passes
`kit task submit` (a NOT RUN row carries its reason). Headings are not numbered, so pasting
the report does not add sections to a task report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import counterexamples as ce_mod
from . import junit, trace
from .logs import mask

PASS, FAIL, SKIPPED, NOT_RUN, NO_TEST = "PASS", "FAIL", "SKIPPED", "NOT RUN", "NO TEST"
NOT_RUN_REASON = "NOT RUN: not in the JUnit XML"
# a requirement shows the worst status of its tests
_WORST = (FAIL, NOT_RUN, SKIPPED, PASS)


@dataclass
class Row:
    test: dict
    status: str  # PASS | FAIL | SKIPPED | NOT RUN
    actual: str
    cases: List[junit.Case] = field(default_factory=list)


@dataclass
class ReqResult:
    req: dict
    tests: List[str]
    status: str  # worst of its tests, or NO TEST
    cases: Dict[str, int]  # normal/boundary/error/counterexample -> count
    risks: List[str]
    review: str = ""  # counterexample review: records by state, or whether a test exists


@dataclass
class Report:
    rows: List[Row]
    reqs: List[ReqResult]
    untracked: List[junit.Case]
    findings: List[trace.Finding]
    sources: List[str]

    def totals(self) -> Dict[str, int]:
        out = {PASS: 0, FAIL: 0, SKIPPED: 0, NOT_RUN: 0}
        for r in self.rows:
            out[r.status] += 1
        return out


def _cell(text: str) -> str:
    """One table cell: no pipes or line breaks (kit task submit splits rows on '|').
    The CLI masks the whole report."""
    return " ".join(str(text).split()).replace("|", "/") or "-"


def _row(test: dict, cases: List[junit.Case]) -> Row:
    if not cases:
        return Row(test, NOT_RUN, "-")
    bad = [c for c in cases if c.outcome in (junit.FAIL, junit.ERROR)]
    skipped = [c for c in cases if c.outcome == junit.SKIPPED]
    if bad:
        status = FAIL
    elif len(skipped) == len(cases):
        status = SKIPPED
    else:
        status = PASS
    if len(cases) == 1:
        c = cases[0]
        word = {
            junit.PASS: "passed",
            junit.FAIL: "failed",
            junit.ERROR: "error",
            junit.SKIPPED: "skipped",
        }[c.outcome]
        actual = f"{word} ({c.seconds:.2f}s)" + (f": {c.message}" if c.message else "")
    else:
        counts = {}
        for c in cases:
            counts[c.outcome] = counts.get(c.outcome, 0) + 1
        actual = f"{len(cases)} cases: " + ", ".join(
            f"{k} {counts[k]}"
            for k in (junit.PASS, junit.FAIL, junit.ERROR, junit.SKIPPED)
            if k in counts
        )
        first = bad[0] if bad else None
        if first is not None:
            actual += f"; {first.name}: {first.message or first.outcome.lower()}"
    return Row(test, status, actual, cases)


def _review(records: List[dict], counted: Dict[str, int]) -> str:
    if not records:
        return "기록 없음" + (" (반례 테스트 있음)" if counted["counterexample"] else "")
    c = ce_mod.counts(records)
    return f"CE {len(records)}: " + ", ".join(f"{k} {v}" for k, v in c.items() if v)


def build(
    data: dict, cases: List[junit.Case], sources: List[str], ce_data: Optional[dict] = None
) -> Report:
    ce_data = ce_data or ce_mod.empty()
    rows: List[Row] = []
    used = set()
    for test in data["tests"]:
        key = junit.normalise(test.get("locator", ""))
        mine = [c for c in cases if junit.matches(key, c)]
        used.update(id(c) for c in mine)
        rows.append(_row(test, mine))
    findings = trace.check(data)
    by_test = {r.test["id"]: r for r in rows}
    reqs = []
    for req in data["requirements"]:
        tests = trace.tests_for(data, req["id"])
        statuses = [by_test[t["id"]].status for t in tests]
        status = next((s for s in _WORST if s in statuses), NO_TEST)
        counted = {c: 0 for c in trace.CASES}
        for t in tests:
            counted[t.get("case", "normal")] += 1
        risks = [f.kind for f in findings if f.subject == req["id"]]
        stale = {t["id"] for t, _ in trace.stale(data, req["id"])}
        if stale:
            risks.append("STALE " + ", ".join(sorted(stale)))
        if req["priority"] == "must" and status in (FAIL, NOT_RUN, SKIPPED):
            risks.append(f"must {status}")
        records = ce_mod.for_requirements(ce_data, [req["id"]])
        open_spec = [i["id"] for i in records if i["status"] == ce_mod.NEEDS_SPEC]
        if open_spec:
            risks.append("NEEDS_SPEC " + ", ".join(open_spec))
        review = _review(records, counted)
        reqs.append(ReqResult(req, [t["id"] for t in tests], status, counted, risks, review))
    untracked = [c for c in cases if id(c) not in used]
    return Report(rows, reqs, untracked, findings, sources)


# ---------------------------------------------------------------- markdown


def _status_cell(row: Row) -> str:
    return NOT_RUN_REASON if row.status == NOT_RUN else row.status


def markdown(report: Report) -> str:
    t = report.totals()
    lines = [
        "# 테스트 보고서 (kit report tests)",
        "",
        f"- 실행 근거(JUnit XML): {', '.join(report.sources)}",
        f"- 통계: PASS {t[PASS]} / FAIL {t[FAIL]} / SKIPPED {t[SKIPPED]} / NOT RUN {t[NOT_RUN]}"
        f" (추적되지 않은 테스트 {len(report.untracked)}개)",
        "- Actual과 Status는 JUnit XML에서만 만든다. JUnit XML에 없는 테스트는 NOT RUN이다.",
        "",
        "## 구현 정확성",
        "",
        "| Requirement | Priority | Tests | Status |",
        "|---|---|---|---|",
    ]
    for q in report.reqs:
        lines.append(
            f"| {q.req['id']} | {q.req['priority']} | {_cell(', '.join(q.tests))} | {q.status} |"
        )
    if not report.reqs:
        lines.append("| - | - | - | 요구사항 없음 (kit req sync) |")
    lines += [
        "",
        "| Test ID | Requirement | Scenario | Input/Condition | Expected | Actual | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report.rows:
        test = r.test
        reqs = ", ".join(x["id"] for x in test["requirements"])
        scenario = test.get("purpose") or f"{test.get('case', 'normal')} case"
        lines.append(
            f"| {_cell(test['id'])} | {_cell(reqs)} | {_cell(scenario)} | "
            f"{_cell(test.get('input', ''))} | {_cell(test.get('expected', ''))} | "
            f"{_cell(r.actual)} | {_status_cell(r)} |"
        )
    if not report.rows:
        lines.append("| - | - | - | - | - | - | 추적된 테스트 없음 (kit trace link) |")
    lines += ["", "### 추적되지 않은 테스트", ""]
    if report.untracked:
        lines += ["| JUnit testcase | Status | 출처 |", "|---|---|---|"]
        lines += [f"| {_cell(c.key)} | {c.outcome} | {_cell(c.source)} |" for c in report.untracked]
    else:
        lines.append("- 없음")
    lines += [
        "",
        "## 테스트 설계 타당성",
        "",
        "| Requirement | Priority | normal | boundary | error | counterexample "
        "| 반례 검토 | 검토자 확인 위험 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for q in report.reqs:
        c = q.cases
        risks = "; ".join(q.risks) or "-"
        lines.append(
            f"| {q.req['id']} | {q.req['priority']} | {c['normal']} | {c['boundary']} | "
            f"{c['error']} | {c['counterexample']} | {_cell(q.review)} | {_cell(risks)} |"
        )
    other = [f for f in report.findings if f.kind in ("UNKNOWN_REQ", "NO_REQUIREMENTS")]
    for f in other:
        lines.append(f"- {f.kind} {f.subject}: {_cell(f.detail)}")
    lines += ["", "## 질문 6개에 대한 답", ""] + _answers(report)
    return "\n".join(lines) + "\n"


def _ids(items: List[str]) -> str:
    return ", ".join(items) if items else "없음"


def _answers(report: Report) -> List[str]:
    passed = [q.req["id"] for q in report.reqs if q.status == PASS]
    declared = [q.req["id"] for q in report.reqs if q.req.get("status") == "implemented"]
    mapping = [f"{q.req['id']} ← {', '.join(q.tests)}" for q in report.reqs if q.tests]
    ran = [r for r in report.rows if r.status != NOT_RUN]
    not_run = [r.test["id"] for r in report.rows if r.status == NOT_RUN]
    failed = [r.test["id"] for r in report.rows if r.status == FAIL]
    skipped = [r.test["id"] for r in report.rows if r.status == SKIPPED]
    untested = [q.req["id"] for q in report.reqs if q.status == NO_TEST]
    unrun = [q.req["id"] for q in report.reqs if q.status == NOT_RUN]
    risks = [f"{q.req['id']}: {'; '.join(q.risks)}" for q in report.reqs if q.risks]
    risks += [
        f"{f.subject}: {f.kind}"
        for f in report.findings
        if f.kind in ("UNKNOWN_REQ", "NO_REQUIREMENTS")
    ]
    if report.untracked:
        risks.append(f"추적되지 않은 테스트 {len(report.untracked)}개(요구사항과 연결 안 됨)")
    return [
        f"1. 어떤 요구사항이 구현됐는가? 연결된 테스트가 모두 PASS: {_ids(passed)}. "
        f"trace.json에 implemented로 기록: {_ids(declared)}.",
        f"2. 어떤 테스트가 해당 요구사항을 검증하는가? {_ids(mapping)}.",
        f"3. 테스트는 실제로 실행됐는가? 추적된 테스트 {len(report.rows)}개 중 {len(ran)}개가 "
        f"JUnit XML에 있음. NOT RUN: {_ids(not_run)}. SKIPPED: {_ids(skipped)}.",
        f"4. 실패한 테스트는 무엇인가? {_ids(failed)}.",
        f"5. 테스트가 누락된 요구사항은 무엇인가? 테스트 없음: {_ids(untested)}. "
        f"실행된 테스트 없음: {_ids(unrun)}.",
        f"6. 사람이 추가로 검토해야 하는 위험은 무엇인가? {_ids([_cell(r) for r in risks])}.",
    ]


def summary(report: Report) -> Dict[str, object]:
    t = report.totals()
    return {
        "totals": {"pass": t[PASS], "fail": t[FAIL], "skipped": t[SKIPPED], "not_run": t[NOT_RUN]},
        "tests": [
            {
                "id": r.test["id"],
                "status": r.status,
                "actual": mask(r.actual),
                "cases": len(r.cases),
            }
            for r in report.rows
        ],
        "requirements": [
            {
                "id": q.req["id"],
                "priority": q.req["priority"],
                "status": q.status,
                "tests": q.tests,
                "cases": q.cases,
                "risks": q.risks,
                "review": q.review,
            }
            for q in report.reqs
        ],
        "untracked": [{"testcase": mask(c.key), "status": c.outcome} for c in report.untracked],
        "sources": report.sources,
    }


def first_problem(report: Report) -> Optional[str]:
    t = report.totals()
    if not report.rows:
        return "no traced test (kit trace link)"
    if t[FAIL] or t[NOT_RUN] or t[SKIPPED]:
        return f"FAIL {t[FAIL]}, NOT RUN {t[NOT_RUN]}, SKIPPED {t[SKIPPED]}"
    untested = [q.req["id"] for q in report.reqs if q.status == NO_TEST]
    if untested:
        return "requirements without tests: " + ", ".join(untested)
    return None
