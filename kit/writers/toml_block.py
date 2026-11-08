"""Kit-owned block inside a TOML file (Codex .codex/config.toml). Extracted in P3-T2.

The block uses TOML comment markers, so the Markdown block merge works unchanged on it.
"""

from __future__ import annotations

from .markdown_block import extract_block

BEGIN = "# hackathon-kit:begin"
END = "# hackathon-kit:end"


def parse_toml(text: str) -> tuple[bool | None, dict | None, str]:
    """(True, data, "") parsed; (False, None, error) invalid; (None, None, "") no tomllib."""
    try:
        import tomllib
    except ImportError:
        return None, None, ""
    try:
        return True, tomllib.loads(text), ""
    except tomllib.TOMLDecodeError as exc:
        return False, None, str(exc)


def without_block(text: str, begin: str = BEGIN, end: str = END) -> str:
    """Text with the kit block removed. Raises MarkerError on broken markers."""
    found = extract_block(text, begin, end)
    return text if found is None else text[: found[0]] + text[found[1] :]
