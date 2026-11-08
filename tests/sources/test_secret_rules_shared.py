"""`kit source add` and `kit capture` share one secret rule set (kit.secrets_scan).

Before, source add looked only for token formats (sk-, ghp_, AKIA ...) and passed a literal
`Authorization: Bearer ...` header or `TOKEN=<value>` line that capture stops on. Now both use
LITERAL_PATTERNS: capture stops on every hit; source add asks a person (REVIEW) about a literal
value and warns (WARN) about a placeholder. Token formats still block. Fixture values are
obvious filler, never real secrets.
"""

from __future__ import annotations

import pytest

from kit import capture, secrets_scan
from kit.source_scan import scan_file

LITERAL_BEARER = "Authorization: Bearer 0000aaaa1111bbbb2222cccc"
PLACEHOLDER_BEARER = "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."  # truncated JWT header
PLACEHOLDER_ASSIGN = "TOKEN=<your-token>"
LITERAL_ASSIGN = 'MY_API_KEY = "fillerfiller000"'


def levels(line: str):
    return [(f.level, f.text) for f in scan_file("x.md", line.encode("utf-8"))]


@pytest.mark.parametrize(
    "line, level, label",
    [
        (LITERAL_BEARER, "REVIEW", "bearer token"),
        (LITERAL_ASSIGN, "REVIEW", "token/secret assignment"),
        (PLACEHOLDER_BEARER, "WARN", "bearer token"),
        (PLACEHOLDER_ASSIGN, "WARN", "token/secret assignment"),
    ],
)
def test_source_add_reports_what_capture_flags(line, level, label):
    """The old source scan returned [] for all four lines."""
    assert [h[1] for h in capture.scan("x.md", line)] == [label]
    found = levels(line)
    assert [lv for lv, _ in found] == [level]
    assert label in found[0][1] and "(line 1)" in found[0][1]


@pytest.mark.parametrize(
    "line",
    [
        "Authorization: Bearer ${ENV:CTX_KEY}",
        'CONTEXT7_API_KEY = "${ENV:CONTEXT7_API_KEY}"',
        "const TOKEN = generateToken()",
        "export TOGETHER_API_KEY=$TOGETHER_API_KEY",
    ],
)
def test_references_are_not_values_in_either_scanner(line):
    assert capture.scan("x.md", line) == []
    assert levels(line) == []


def test_token_formats_still_block():
    line = "key: ghp_" + "F" * 30
    assert [lv for lv, _ in levels(line)] == ["BLOCK"]


def test_findings_never_carry_the_value():
    for line in (LITERAL_BEARER, LITERAL_ASSIGN, PLACEHOLDER_ASSIGN):
        for _, text in levels(line):
            for value in ("0000aaaa", "fillerfiller", "your-token"):
                assert value not in text


def test_both_scanners_use_the_same_patterns():
    assert capture.EXTRA_PATTERNS is secrets_scan.LITERAL_PATTERNS


@pytest.mark.parametrize(
    "value, expected",
    [
        ("<your-token>", True),
        ("eyJhbGciOiJIUzI1NiIs...", True),
        ("sk-xxxxxxxxxxxx", True),
        ("YOUR_API_KEY", True),
        ("changeme123", True),
        ("0000aaaa1111bbbb2222cccc", False),
    ],
)
def test_placeholder_heuristic(value, expected):
    assert secrets_scan.is_placeholder(value) is expected


def test_known_vendored_placeholder_is_a_warning_not_a_block(kit_root):
    """third_party/affaan-m-ECC api-design line 303 (tests/userscope/test_capture.py)."""
    path = kit_root / "third_party/affaan-m-ECC/skills/api-design/SKILL.md"
    found = scan_file("api-design/SKILL.md", path.read_bytes())
    secret = [f for f in found if "bearer" in f.text or "secret" in f.text]
    assert [(f.level, f.text.rsplit("(", 1)[1]) for f in secret] == [("WARN", "line 303)")]


def test_no_vendored_file_needs_a_person_for_a_secret(kit_root):
    """Everything already vendored stays below REVIEW for the secret rules."""
    bad = []
    for path in sorted((kit_root / "third_party").rglob("*")):
        if path.is_file():
            rel = path.relative_to(kit_root).as_posix()
            bad += [
                f.text
                for f in scan_file(rel, path.read_bytes())
                if f.level in ("BLOCK", "REVIEW") and ("token" in f.text or "secret" in f.text)
            ]
    assert bad == []
