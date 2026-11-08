"""Requirement-test tracing (P5-T3, 00_PROMPT 10.3, ADR-012, REQ-TRACE-001~004).

State lives at .kit/work/trace.json (00_PROMPT P2-T4 shape, plus "case"):

    {"schema": 1,
     "requirements": [{"id", "text", "source", "priority", "revision", "status"}],
     "tests": [{"id", "requirements": [{"id", "revision"}], "locator", "purpose",
                "input", "expected", "kind", "case"}]}

- A requirement's revision starts at 1 and goes up when its text or priority changes
  (`kit req edit`, or `kit req sync` reading TASK_BRIEF.md).
- A test records, per requirement, the revision it was written or last reviewed against
  (`kit trace link` sets the current one). An older one means the test needs a new look.
- case: normal | boundary | error | counterexample. A must requirement needs at least one
  test that is not "normal" (reviewer decision 2026-11-07).

Reviewer decisions 2026-11-07: requirements come from a "## Requirements" section in
TASK_BRIEF.md (standard task-router overlay) or `kit req add`; tests are linked with
`kit trace link`; test names are not scanned for tags.

Test results are never stored here; P5-T4 joins JUnit XML for PASS/FAIL/NOT RUN.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .fsops import PathEscapeError, safe_path

TRACE_REL = ".kit/work/trace.json"
BRIEF_REL = "TASK_BRIEF.md"
SCHEMA = 1
PRIORITIES = ("must", "should", "could")
STATUSES = ("not-started", "partial", "implemented")
CASES = ("normal", "boundary", "error", "counterexample")
KINDS = ("unit", "integration", "counterexample")
REQ_ID = re.compile(r"^REQ-[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")
TEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
# "- REQ-001 (must): text" in the "## Requirements" section of TASK_BRIEF.md
_BRIEF_LINE = re.compile(
    r"^\s*[-*]\s+(?P<id>REQ-[A-Za-z0-9][A-Za-z0-9_.-]*)\s*(?:\((?P<prio>[A-Za-z]+)\))?\s*:\s*"
    r"(?P<text>\S.*?)\s*$"
)
_SECTION = re.compile(r"^##\s+Requirements\s*$", re.I)


class TraceError(ValueError):
    """trace.json or TASK_BRIEF.md cannot be used as it is (exit 65)."""


class Refused(Exception):
    """A tracing rule refused the request; nothing was written (exit 2)."""


# ---------------------------------------------------------------- storage


def path(target: Path) -> Path:
    return safe_path(target, TRACE_REL)


def empty() -> dict:
    return {"schema": SCHEMA, "requirements": [], "tests": []}


def load(target: Path) -> dict:
    """Missing or empty file: nothing traced yet. Anything unreadable is a TraceError."""
    p = path(target)
    if not p.is_file():
        return empty()
    try:
        raw = p.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise TraceError(f"{TRACE_REL} cannot be read: {exc}") from None
    if not raw.strip():
        return empty()
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise TraceError(f"{TRACE_REL} is not valid JSON: {exc}") from None
    validate(data)
    return data


def save(target: Path, data: dict) -> None:
    validate(data)
    p = path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, p)


def _bad(message: str) -> TraceError:
    return TraceError(f"{TRACE_REL}: {message}")


def validate(data: object) -> None:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise _bad(f"expected an object with schema {SCHEMA}")
    reqs, tests = data.get("requirements"), data.get("tests")
    if not isinstance(reqs, list) or not isinstance(tests, list):
        raise _bad("requirements and tests must be lists")
    seen = set()
    for r in reqs:
        if not isinstance(r, dict) or not isinstance(r.get("id"), str):
            raise _bad("every requirement needs an id")
        if r["id"] in seen:
            raise _bad(f"requirement {r['id']} is listed twice")  # TC-HTL-09
        seen.add(r["id"])
        if r.get("priority") not in PRIORITIES:
            raise _bad(f"requirement {r['id']} has priority {r.get('priority')!r}")
        rev = r.get("revision")
        if not isinstance(rev, int) or isinstance(rev, bool) or rev < 1:
            raise _bad(f"requirement {r['id']} needs a revision of 1 or more")
    seen = set()
    for t in tests:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str):
            raise _bad("every test needs an id")
        if t["id"] in seen:
            raise _bad(f"test {t['id']} is listed twice")
        seen.add(t["id"])
        links = t.get("requirements")
        if not isinstance(links, list) or not all(
            isinstance(x, dict) and isinstance(x.get("id"), str) for x in links
        ):
            raise _bad(f"test {t['id']}: requirements must be a list of {{id, revision}}")
        if t.get("case", "normal") not in CASES:
            raise _bad(f"test {t['id']} has case {t.get('case')!r}")


def get_req(data: dict, req_id: str) -> Optional[dict]:
    return next((r for r in data["requirements"] if r["id"] == req_id), None)


def get_test(data: dict, test_id: str) -> Optional[dict]:
    return next((t for t in data["tests"] if t["id"] == test_id), None)


# ---------------------------------------------------------------- requirements


def _check_req(req_id: str, text: str, priority: str) -> None:
    if not REQ_ID.match(req_id):
        raise ValueError(f"requirement ids look like REQ-001; got '{req_id}'")
    if not text.strip():
        raise ValueError("--text needs the requirement in one sentence")
    if priority not in PRIORITIES:
        raise ValueError(f"--priority must be one of {', '.join(PRIORITIES)}")


def add_req(data: dict, req_id: str, text: str, priority: str, source: str = "") -> dict:
    _check_req(req_id, text, priority)
    if get_req(data, req_id) is not None:
        raise Refused(f"requirement {req_id} already exists (kit req edit changes it)")
    req = {
        "id": req_id,
        "text": text.strip(),
        "source": source,
        "priority": priority,
        "revision": 1,
        "status": "not-started",
    }
    data["requirements"].append(req)
    return req


def edit_req(
    data: dict,
    req_id: str,
    text: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[dict, bool]:
    """(requirement, revised). Text or priority changes raise the revision."""
    req = get_req(data, req_id)
    if req is None:
        raise Refused(f"no requirement {req_id} (kit req list)")
    new_text = req["text"] if text is None else text.strip()
    new_prio = req["priority"] if priority is None else priority
    _check_req(req_id, new_text, new_prio)
    if status is not None and status not in STATUSES:
        raise ValueError(f"--status must be one of {', '.join(STATUSES)}")
    revised = (new_text, new_prio) != (req["text"], req["priority"])
    req["text"], req["priority"] = new_text, new_prio
    if revised:
        req["revision"] += 1
    if status is not None:
        req["status"] = status
    return req, revised


def parse_brief(text: str) -> List[Tuple[str, str, str]]:
    """(id, priority, text) from the "## Requirements" section; priority defaults to must."""
    out: List[Tuple[str, str, str]] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = bool(_SECTION.match(line.strip()))
            continue
        if not inside:
            continue
        found = _BRIEF_LINE.match(line)
        if found:
            prio = (found.group("prio") or "must").lower()
            out.append((found.group("id"), prio, found.group("text")))
    return out


@dataclass
class SyncResult:
    added: List[str]
    revised: List[str]
    unchanged: List[str]
    missing: List[str]  # from the brief before, not in it now (kept, reported)


def sync(target: Path, data: dict, brief_rel: str = BRIEF_REL) -> SyncResult:
    try:
        brief = safe_path(target, brief_rel)
    except PathEscapeError:
        raise Refused(f"'{brief_rel}' is outside the workspace") from None
    if not brief.is_file():
        raise Refused(f"{brief_rel} does not exist (task-router writes it)")
    try:
        text = brief.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise TraceError(f"{brief_rel} cannot be read: {exc}") from None
    found = parse_brief(text)
    if not found:
        raise Refused(f"{brief_rel} has no '## Requirements' lines like '- REQ-001 (must): ...'")
    ids = [i for i, _, _ in found]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise Refused(f"{brief_rel} lists {', '.join(dup)} more than once")
    bad = [p for _, p, _ in found if p not in PRIORITIES]
    if bad:
        raise Refused(f"{brief_rel}: priority '{bad[0]}' is not one of {', '.join(PRIORITIES)}")
    result = SyncResult([], [], [], [])
    for req_id, prio, req_text in found:
        if get_req(data, req_id) is None:
            add_req(data, req_id, req_text, prio, f"{brief_rel}#{req_id}")
            result.added.append(req_id)
        else:
            _, revised = edit_req(data, req_id, req_text, prio)
            (result.revised if revised else result.unchanged).append(req_id)
    prefix = f"{brief_rel}#"
    result.missing = [
        r["id"]
        for r in data["requirements"]
        if str(r.get("source", "")).startswith(prefix) and r["id"] not in ids
    ]
    return result


# ---------------------------------------------------------------- tests


def link(
    data: dict,
    test_id: str,
    req_ids: List[str],
    locator: Optional[str],
    case: Optional[str],
    kind: Optional[str] = None,
    purpose: Optional[str] = None,
    input_: Optional[str] = None,
    expected: Optional[str] = None,
) -> Tuple[dict, bool]:
    """Create or update a test; every linked requirement is recorded at its current revision
    (linking again after a revision means the test was reviewed). (test, created)."""
    if not TEST_ID.match(test_id):
        raise ValueError("test id: letters, digits, '.', '_' or '-' (up to 40), e.g. TC-007")
    if case is not None and case not in CASES:
        raise ValueError(f"--case must be one of {', '.join(CASES)}")
    if kind is not None and kind not in KINDS:
        raise ValueError(f"--kind must be one of {', '.join(KINDS)}")
    unknown = [r for r in req_ids if get_req(data, r) is None]
    if unknown:
        raise Refused(f"no requirement {unknown[0]} (kit req add or kit req sync first)")
    test = get_test(data, test_id)
    created = test is None
    if created:
        if not locator or not locator.strip():
            raise ValueError("a new test needs --locator (e.g. tests/test_x.py::test_y)")
        test = {
            "id": test_id,
            "requirements": [],
            "locator": locator.strip(),
            "purpose": "",
            "input": "",
            "expected": "",
            "kind": "unit",
            "case": "normal",
        }
        data["tests"].append(test)
    if locator:
        test["locator"] = locator.strip()
    if case:
        test["case"] = case
    if kind:
        test["kind"] = kind
    if purpose is not None:
        test["purpose"] = purpose.strip()
    if input_ is not None:
        test["input"] = input_.strip()
    if expected is not None:
        test["expected"] = expected.strip()
    links = {x["id"]: x for x in test["requirements"]}
    for req_id in dict.fromkeys(req_ids):
        rev = get_req(data, req_id)["revision"]
        if req_id in links:
            links[req_id]["revision"] = rev
        else:
            test["requirements"].append({"id": req_id, "revision": rev})
    return test, created


# ---------------------------------------------------------------- checks


@dataclass(frozen=True)
class Finding:
    kind: str  # UNTESTED | WEAK | UNKNOWN_REQ | STALE | NO_REQUIREMENTS
    subject: str  # requirement or test id
    detail: str

    def line(self) -> str:
        return f"{self.kind:<16} {self.subject:<12} {self.detail}"

    def to_json(self) -> dict:
        return {"kind": self.kind, "subject": self.subject, "detail": self.detail}


ORDER = ("UNTESTED", "WEAK", "UNKNOWN_REQ", "STALE", "NO_REQUIREMENTS")


def tests_for(data: dict, req_id: str) -> List[dict]:
    return [t for t in data["tests"] if any(x["id"] == req_id for x in t["requirements"])]


def stale(data: dict, req_id: str) -> List[Tuple[dict, int]]:
    """(test, revision it saw) for tests written against an older revision of req_id."""
    req = get_req(data, req_id)
    if req is None:
        return []
    out = []
    for t in tests_for(data, req_id):
        seen = next(x for x in t["requirements"] if x["id"] == req_id).get("revision")
        if not isinstance(seen, int) or seen < req["revision"]:
            out.append((t, seen))
    return out


def check(data: dict) -> List[Finding]:
    found: List[Finding] = []
    for req in data["requirements"]:
        mine = tests_for(data, req["id"])
        if not mine:
            found.append(Finding("UNTESTED", req["id"], f"{req['priority']}: no test"))
        elif req["priority"] == "must" and all(t.get("case", "normal") == "normal" for t in mine):
            ids = ", ".join(t["id"] for t in mine)
            found.append(
                Finding(
                    "WEAK",
                    req["id"],
                    f"must, only normal-case tests ({ids}); add a boundary, error or "
                    "counterexample test",
                )
            )
        for t, seen in stale(data, req["id"]):
            found.append(
                Finding(
                    "STALE",
                    t["id"],
                    f"written for {req['id']} r{seen}, now r{req['revision']}; review it, "
                    f"then kit trace link {t['id']} --req {req['id']}",
                )
            )
    known = {r["id"] for r in data["requirements"]}
    for t in data["tests"]:
        if not t["requirements"]:
            found.append(Finding("NO_REQUIREMENTS", t["id"], "links no requirement"))
        for x in t["requirements"]:
            if x["id"] not in known:
                found.append(Finding("UNKNOWN_REQ", t["id"], f"points to {x['id']}, not recorded"))
    return sorted(found, key=lambda f: (ORDER.index(f.kind), f.subject))


def counts(data: dict) -> Dict[str, int]:
    return {
        "requirements": len(data["requirements"]),
        "must": sum(1 for r in data["requirements"] if r["priority"] == "must"),
        "tests": len(data["tests"]),
    }
