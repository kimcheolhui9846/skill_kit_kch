"""What `kit source add` looks for in downloaded text (P4-T8, ADR-021). Detection only.

The patterns name things the kit itself never does (remote-script one-liners such as a download
piped into a shell); tests/test_security.py allows them in this file only, and checks that this
file runs nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from . import secrets_scan

_SHELLS = r"(?:ba|z|da)?sh"
_REMOTE_EXEC = [
    re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?" + _SHELLS + r"\b", re.I),
    re.compile(
        r"\b(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^\n|]*\|\s*"
        r"(?:iex|Invoke-Expression)\b",
        re.I,
    ),
]
_INJECTION = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?"
    r"(?:previous|prior|above|earlier)\s+instructions\b",
    re.I,
)
_USER_PATH = re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+|/home/[a-z][^/\s]*|/Users/[A-Za-z][^/\s]*")
# zero-width, bidi controls, word joiners, BOM, tag characters (written as escapes on purpose)
_HIDDEN = re.compile(
    "[\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u2064\\u2066-\\u2069\\ufeff\\U000e0000-\\U000e007f]"
)


@dataclass
class Finding:
    level: str  # BLOCK (exit 1), REVIEW (exit 2 unless --accept-risk), WARN
    text: str


def scan_file(rel: str, data: bytes) -> List[Finding]:
    if b"\x00" in data:
        return [Finding("BLOCK", f"{rel}: binary file")]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [Finding("BLOCK", f"{rel}: binary file (not UTF-8)")]
    out = [Finding("BLOCK", f"{rel}: {label} (line {n})") for label, n in secrets_scan.find(text)]
    body = text[1:] if text.startswith("\ufeff") else text
    for number, line in enumerate(body.splitlines(), start=1):
        if any(p.search(line) for p in _REMOTE_EXEC):
            out.append(
                Finding("REVIEW", f"{rel}: downloads and runs a remote script (line {number})")
            )  # noqa: E501
        if _HIDDEN.search(line):
            out.append(Finding("REVIEW", f"{rel}: hidden Unicode characters (line {number})"))
        if _INJECTION.search(line):
            out.append(Finding("REVIEW", f"{rel}: prompt-injection phrase (line {number})"))
        if _USER_PATH.search(line):
            out.append(Finding("WARN", f"{rel}: machine-specific user path (line {number})"))
    return out
