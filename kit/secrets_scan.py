"""Token patterns shared by log masking (kit.logs) and, later, `kit capture` (05_CLI_SPEC §9).

`find` reports where a secret-like value is, never the value itself (R-09).
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


def find(text: str) -> List[Tuple[str, int]]:
    """[(label, line number)] for every secret-like value; values are not returned."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                hits.append((label, number))
    return hits
