"""Protected-block merge for Markdown-style files, never touching other text.

Extracted from kit/agentsmd.py in P3-T2 (behaviour unchanged). The default markers are the
AGENTS.md ones; kit.mcpconfig passes the TOML comment markers.
"""

from __future__ import annotations

from ..fsops import sha256
from ..model import Outcome

BEGIN = "<!-- hackathon-kit:begin -->"
END = "<!-- hackathon-kit:end -->"


class MarkerError(ValueError):
    """Protected-block markers are missing a partner, duplicated or out of order."""


def render_block(body: str, begin: str = BEGIN, end: str = END) -> str:
    return f"{begin}\n{body.strip()}\n{end}\n"


def extract_block(text: str, begin: str = BEGIN, end: str = END) -> tuple[int, int, str] | None:
    """Return (start, stop, stripped interior) of the block, or None if there is none."""
    begins, ends = text.count(begin), text.count(end)
    if begins == 0 and ends == 0:
        return None
    if begins != 1 or ends != 1:
        raise MarkerError("expected exactly one begin and one end marker")
    start, end_at = text.index(begin), text.index(end)
    if end_at < start:
        raise MarkerError("end marker appears before begin marker")
    stop = end_at + len(end)
    if text.startswith("\r\n", stop):
        stop += 2
    elif text.startswith("\n", stop):
        stop += 1
    return start, stop, text[start + len(begin) : end_at].replace("\r\n", "\n").strip()


def merge(
    existing: str | None,
    body: str,
    recorded_hash: str | None,
    begin: str = BEGIN,
    end: str = END,
) -> tuple[str | None, str, str]:
    """Return (new text or None when nothing is written, outcome, detail)."""
    block = render_block(body, begin, end)
    if existing is None or not existing.strip():
        return block, Outcome.CREATE, ""
    try:
        found = extract_block(existing, begin, end)
    except MarkerError as exc:
        return None, Outcome.CONFLICT, str(exc)
    if found is None:
        sep = "" if existing.endswith("\n") else "\n"
        return existing + sep + "\n" + block, Outcome.APPEND, ""
    start, stop, interior = found
    if interior == body.strip():
        return None, Outcome.UNCHANGED, ""
    if recorded_hash is not None and sha256(interior.encode("utf-8")) == recorded_hash:
        return existing[:start] + block + existing[stop:], Outcome.UPDATE, ""
    return None, Outcome.CONFLICT, "kit block was edited outside the kit"
