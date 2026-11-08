"""P7-T2: the requirement map of devtools/req_coverage.py stays complete and points at real tests.

The final report's coverage table (docs/v2/FINAL_REPORT.md section 4) is made from this map and
a JUnit file. A requirement missing from the map, or a pattern that names no test, would show
as NOT RUN or silently count nothing, so both are checked here against the sources.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from tests.conftest import KIT_ROOT

SPEC = importlib.util.spec_from_file_location("req_coverage", KIT_ROOT / "devtools/req_coverage.py")
req_coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(req_coverage)

LATER_DECISIONS = {"SAFE-011", "SAFE-012", "USER-008"}  # 06_TEST_PLAN, P4-T9 and Q4


def _documented_ids():
    found = set()
    for name in ("00_PROMPT.md", "00_ADDENDUM.md"):
        text = (KIT_ROOT / "docs" / "v2" / name).read_text(encoding="utf-8")
        found |= set(re.findall(r"\*\*REQ-([A-Z]+-\d{3})[*\s]", text))
    return found


def test_every_requirement_is_mapped_once():
    documented = _documented_ids()
    assert len(documented) == 81
    assert set(req_coverage.MAP) == documented | LATER_DECISIONS


@pytest.mark.parametrize(
    "key, pattern",
    [(k, p) for k, r in req_coverage.MAP.items() for p in r.tests],
)
def test_each_pattern_names_an_existing_test(key, pattern):
    path, name = req_coverage.split(pattern)
    source = (KIT_ROOT / path).read_text(encoding="utf-8")
    tests = re.findall(r"^def (test_\w+)", source, re.M)
    assert tests, f"{key}: {path} has no tests"
    if name:
        assert any(re.match(rf"test_(?:{name})", t) for t in tests), f"{key}: {pattern}"


def test_no_tests_means_a_document_or_not_built():
    for key, req in req_coverage.MAP.items():
        if not req.tests:
            assert req.impl == "미구현" or "문서" in req.note, key


def test_a_requirement_without_cases_is_not_run(tmp_path):
    junit = tmp_path / "j.xml"
    junit.write_text(
        '<testsuites><testsuite><testcase classname="tests.test_model" name="test_exit_codes"/>'
        '<testcase classname="tests.test_cli" name="test_defaults"><failure/></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    cases = req_coverage.parse_junit(junit)
    table, summary = req_coverage.render(cases)
    rows = {line.split(" | ")[0][2:]: line for line in table.splitlines()[2:]}
    assert "| FAIL (1 failed) |" in rows["REQ-COMPAT-001"]
    assert "| PASS (1 passed) |" in rows["REQ-COMPAT-005"]
    assert "| NOT RUN |" in rows["REQ-INST-004"]
    assert "| 문서 |" in rows["REQ-SRC-001"]
    assert summary["NOT RUN"] > 0
