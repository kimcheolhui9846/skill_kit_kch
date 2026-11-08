"""Secret patterns shared by log masking (kit.logs), `kit capture` and `kit source add`.

Two rule sets, one home (05_CLI_SPEC §9, R-09):
- TOKEN_PATTERNS: values in a known token format (sk-, ghp_, AKIA ...). `find` reports them.
- LITERAL_PATTERNS: a literal value next to a secret-looking name or an `Authorization: Bearer`
  header (REQ-USER-004). `find_literal` reports them and whether the value looks like a
  documentation placeholder (`<your-token>`, `eyJhbGciOi...`, `xxxx`).

Each caller picks the level: capture stops on any hit (it writes the user's own settings into
the repo); source add blocks token formats and asks a person about literals (downloaded docs
often show placeholders). Callers get labels and line numbers, never the value itself.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# (label, pattern). Each pattern matches the secret value only.
TOKEN_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("openai/anthropic key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("github fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("aws access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("huggingface token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


# (label, pattern). A literal value only: ${NAME} references and $NAME are not values.
LITERAL_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    # the optional "..." keeps a truncated example ("eyJhbGciOi...") whole for is_placeholder
    ("bearer token", re.compile(r"(?i)\bbearer\s+(?!\$\{)[A-Za-z0-9._~+/=-]{8,}(?:\.\.\.)?")),
    (  # NAME = "value" / NAME: 'value' / NAME=value (env style, no spaces)
        "token/secret assignment",
        re.compile(
            r"(?i)\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY)\b"
            r"(?:\s*[=:]\s*[\"'](?!\$\{)[^\s\"'$]{6,}[\"']|=(?![\"'$])[^\s\"'$]{6,})"
        ),
    ),
]
# what documentation writes instead of a real value
_PLACEHOLDER = re.compile(
    r"<[^<>]*>|\.\.\.|\*{3,}|x{4,}|X{4,}|(?i:your[_-]|example|placeholder|changeme|redacted)"
)


def is_placeholder(value: str) -> bool:
    return bool(_PLACEHOLDER.search(value))


def find_literal(text: str) -> List[Tuple[str, int, bool]]:
    """[(label, line number, looks like a placeholder)] for LITERAL_PATTERNS; no values."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in LITERAL_PATTERNS:
            match = pattern.search(line)
            if match:
                hits.append((label, number, is_placeholder(match.group(0))))
    return hits


def find(text: str) -> List[Tuple[str, int]]:
    """[(label, line number)] for every secret-like value; values are not returned."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                hits.append((label, number))
    return hits
