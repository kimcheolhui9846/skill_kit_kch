"""Local-only run logs with secrets masked. Environment variable values are never logged."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .fsops import logs_rel, safe_path
from .secrets_scan import TOKEN_PATTERNS

# P4-T9: two things after NAME= are not values and stay readable: the guide's placeholder
# "<your key>" and an environment reference ${VAR} (e.g. claude mcp add -e 'NAME=${NAME}').
# Anything else after NAME= is still masked.
PLACEHOLDER_GUARD = (
    r'(?!"<your key>"(?:\s|$))'
    r"(?!'?\$\{[A-Za-z_][A-Za-z0-9_]*\}'?(?:\s|$))"
)
_PATTERNS = [
    (
        re.compile(
            r"(?i)\b([\w-]*?(?:api[_-]?key|token|secret|password))\s*[=:]\s*"
            + PLACEHOLDER_GUARD
            + r"(?:bearer\s+)?\S+"
        ),
        r"\1=***",
    ),
    (re.compile(r"(?i)\bbearer\s+\S+"), "Bearer ***"),
] + [(pattern, "***") for _, pattern in TOKEN_PATTERNS]


def mask(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def mask_tree(value: Any) -> Any:
    """Mask every string inside a JSON-like value before it is dumped (P6-T2, V-17).

    Masking the dumped text instead can swallow a closing quote: NAME=\\S+ runs to the next
    space, so the output would no longer be JSON.
    """
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, dict):
        return {k: mask_tree(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask_tree(v) for v in value]
    return value


def write_log(target: Path, text: str, stamp: str) -> Path:
    path = safe_path(target, f"{logs_rel(target)}/{stamp}.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(mask(text).encode("utf-8"))
    return path
