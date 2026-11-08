"""Profile loading. A profile may extend another; list fields merge base-first."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import UsageError


class ProfileError(Exception):
    """A kit profile file is malformed (reported as BLOCKED)."""


LIST_KEYS = ("skills", "required_skills", "tools", "mcp")
NAME_LISTS = ("skills", "required_skills", "mcp")
KINDS = ("python-tool", "python-lib", "node-project")
REQUIRED_TOOL_KEYS = {
    "python-tool": ("package", "version", "command"),
    "python-lib": ("package",),
    "node-project": (),
}


@dataclass
class Profile:
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)
    report_only: bool = False


def _is_v2(path: Path) -> bool:
    """Profile v2 files (P4-T6: fullstack, ai-research, hackathon) belong to the new path only."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return isinstance(data, dict) and "schema" in data


def available_profiles(kit_root: Path) -> list[str]:
    """The legacy path's profiles: v1 files only, so its choices and messages stay as before."""
    paths = (kit_root / "profiles").glob("*.json")
    return sorted(path.stem for path in paths if not _is_v2(path))


def _read(kit_root: Path, name: str) -> dict:
    path = kit_root / "profiles" / f"{name}.json"
    if not path.is_file() or _is_v2(path):
        available = ", ".join(available_profiles(kit_root))
        raise UsageError(f"unknown profile '{name}' (available: {available})")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProfileError(f"profile '{name}' is not valid JSON: {exc}") from exc
    _validate(name, data)
    return data


def _validate(name: str, data: object) -> None:
    if not isinstance(data, dict):
        raise ProfileError(f"profile '{name}' must be a JSON object")
    extends = data.get("extends")
    if extends is not None and not isinstance(extends, str):
        raise ProfileError(f"profile '{name}': extends must be a profile name or null")
    if not isinstance(data.get("report_only", False), bool):
        raise ProfileError(f"profile '{name}': report_only must be true or false")
    for key in NAME_LISTS:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ProfileError(f"profile '{name}': {key} must be a list of names")
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        raise ProfileError(f"profile '{name}': tools must be a list")
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise ProfileError(f"profile '{name}': every tool needs a name")
        kind = tool.get("kind")
        if kind not in KINDS:
            raise ProfileError(f"profile '{name}': tool '{tool['name']}' has unknown kind {kind!r}")
        for key in REQUIRED_TOOL_KEYS[kind]:
            if not isinstance(tool.get(key), str):
                raise ProfileError(f"profile '{name}': tool '{tool['name']}' needs {key}")


def load_profile(kit_root: Path, name: str) -> Profile:
    chain: list[dict] = []
    seen: set[str] = set()
    current: str | None = name
    while current:
        if current in seen:
            raise UsageError(f"profile inheritance cycle at '{current}'")
        seen.add(current)
        data = _read(kit_root, current)
        chain.append(data)
        current = data.get("extends")

    merged: dict[str, list] = {key: [] for key in LIST_KEYS}
    for data in reversed(chain):
        for key in LIST_KEYS:
            for item in data.get(key, []):
                if item not in merged[key]:
                    merged[key].append(item)
    return Profile(
        name=name,
        description=chain[0].get("description", ""),
        report_only=chain[0].get("report_only", False),
        **merged,
    )
