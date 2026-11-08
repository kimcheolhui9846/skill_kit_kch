"""JUnit XML as run evidence (P5-T4, ADR-012, REQ-TEST-002).

Only xml.etree.ElementTree (stdlib). A document with a DOCTYPE is refused: JUnit reporters
never write one, and refusing it rules out entity expansion.

Matching a trace locator to a testcase (reviewer decision 2026-11-07: normalise, then match
exactly): the file part (before the first "::" of a locator, the classname of a testcase)
loses its extension and '/', '.' and '\\' all become '/'; the remaining "::" parts and the
testcase name are joined with '/' as they are. So these meet:

    tests/test_x.py::TestA::test_y    classname="tests.test_x.TestA" name="test_y"   (pytest)
    src/sum.test.ts::sum > adds       classname="src/sum.test.ts" name="sum > adds"  (vitest)
    example.com/calc::TestAdd         classname="example.com/calc" name="TestAdd"    (go)

A locator also takes the parametrised cases "name[...]" of the same test.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List

PASS, FAIL, ERROR, SKIPPED = "PASS", "FAIL", "ERROR", "SKIPPED"
_EXT = re.compile(r"\.(?:py|pyi|js|jsx|mjs|cjs|ts|tsx|mts|cts|go)$", re.I)
MESSAGE_MAX = 160


class JUnitError(Exception):
    """The JUnit XML cannot be used (exit 2: the report would have no evidence)."""


@dataclass(frozen=True)
class Case:
    key: str  # normalised classname/name
    name: str  # as written, for the report
    outcome: str  # PASS | FAIL | ERROR | SKIPPED
    message: str  # first line of the failure/error/skip message, "" for PASS
    seconds: float
    source: str  # which file it came from (display form)


def _path_part(text: str) -> str:
    text = _EXT.sub("", text.strip().replace("\\", "/"))
    return "/".join(p for p in re.split(r"[/.]", text) if p)


def normalise(locator: str) -> str:
    """'tests/test_x.py::A::b' -> 'tests/test_x/A/b'."""
    head, _, rest = locator.strip().partition("::")
    parts = [_path_part(head)] + [p.strip() for p in rest.split("::") if p.strip()]
    return "/".join(p for p in parts if p)


def case_key(classname: str, name: str) -> str:
    return "/".join(p for p in (_path_part(classname), name.strip()) if p)


def matches(locator_key: str, case: Case) -> bool:
    """Exact, or a parametrised case of the test the locator names."""
    if case.key == locator_key:
        return True
    return case.key.startswith(locator_key + "[")


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            line = line.strip()
            return line if len(line) <= MESSAGE_MAX else line[: MESSAGE_MAX - 3] + "..."
    return ""


def _seconds(raw) -> float:
    try:
        return float(raw or 0)
    except ValueError:
        return 0.0


def parse(path: Path, display: str) -> List[Case]:
    if not path.is_file():
        raise JUnitError(f"{display} does not exist")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise JUnitError(f"{display} cannot be read: {exc}") from None
    if b"<!DOCTYPE" in raw.upper():  # an ENTITY needs one; without it expat refuses
        raise JUnitError(f"{display} has a DOCTYPE; JUnit reports never do")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise JUnitError(f"{display} is not valid XML: {exc}") from None
    if root.tag not in ("testsuites", "testsuite"):
        raise JUnitError(f"{display}: root is <{root.tag}>, not <testsuites> or <testsuite>")
    cases: List[Case] = []
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    for suite in suites:  # nested suites are listed separately; findall takes direct children
        for tc in suite.findall("testcase"):
            name = tc.get("name")
            if not name:
                raise JUnitError(f"{display}: a <testcase> has no name")
            classname = tc.get("classname") or tc.get("file") or suite.get("name") or ""
            cases.append(_case(tc, classname, name, display))
    return cases


def _case(tc, classname: str, name: str, display: str) -> Case:
    outcome, message = PASS, ""
    for tag, kind in (("failure", FAIL), ("error", ERROR), ("skipped", SKIPPED)):
        found = tc.find(tag)
        if found is not None:
            outcome = kind
            message = _first_line(found.get("message") or "") or _first_line(found.text or "")
            break
    return Case(
        case_key(classname, name), name, outcome, message, _seconds(tc.get("time")), display
    )
