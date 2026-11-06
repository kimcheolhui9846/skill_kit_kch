"""Static checks for a merged skill, per agent (P4-T2). Standard library only.

Sources (read 2026-11-06):
- Agent Skills spec, agentskills.io/specification: name 1-64 chars [a-z0-9-], no leading,
  trailing or double hyphen, equals the folder; description 1-1024 chars; compatibility
  1-500 chars; metadata is a map.
- Claude Code, code.claude.com/docs/en/skills: description + when_to_use are cut at 1,536
  characters in the listing; unknown fields are ignored silently; a name may not hold < or >.
- Codex, learn.chatgpt.com/docs/build-skills: name and description required; optional
  agents/openai.yaml with interface / policy / dependencies.

Errors stop an install (BLOCKED). Warnings are reported only. Kit-written skills also follow
the kit's own stricter rules (description <= 400 chars and a "Do NOT use" sentence).
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Union

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
CLAUDE_LISTING = 1536
KIT_MAX_DESCRIPTION = 400
MAX_LINES = 500  # spec: keep SKILL.md under 500 lines

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_FIELDS = SPEC_FIELDS | {
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "paths",
    "hooks",
    "shell",
}
CLAUDE_ONLY = CLAUDE_FIELDS - SPEC_FIELDS
OPENAI_YAML = "agents/openai.yaml"
OPENAI_KEYS = {
    "interface": {
        "display_name",
        "short_description",
        "icon_small",
        "icon_large",
        "brand_color",
        "default_prompt",
    },
    "policy": {"allow_implicit_invocation"},
    "dependencies": {"tools"},
}
_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^\s*(```|~~~)")

Value = Union[str, Dict[str, str], List[str]]
# (sibling skill name, path inside it) -> True when that file is installed next to this skill
Sibling = Callable[[str, str], bool]


@dataclass
class Report:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def parse_frontmatter(text: str) -> Dict[str, Value]:
    """YAML subset used by skills: `key: value`, and one level of `key:` + indented
    `sub: value` (map) or `- item` (list). Raises ValueError on anything else."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with '---' on the first line")
    data: Dict[str, Value] = {}
    current = None
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            if current is None:
                raise ValueError(f"indented line without a parent key: {line!r}")
            item = line.strip()
            if item.startswith("- "):
                value = data[current] if isinstance(data[current], list) else []
                value.append(_scalar(item[2:]))
                data[current] = value
            else:
                key, sep, value = item.partition(":")
                if not sep:
                    raise ValueError(f"bad frontmatter line: {line!r}")
                mapping = data[current] if isinstance(data[current], dict) else {}
                mapping[key.strip()] = _scalar(value)
                data[current] = mapping
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad frontmatter line: {line!r}")
        key = key.strip()
        if key in data:
            raise ValueError(f"duplicate key '{key}'")
        data[key] = _scalar(value)
        current = key
    raise ValueError("frontmatter is not closed with '---'")


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _check_name(name: object, folder: str, report: Report) -> None:
    if not isinstance(name, str) or not name:
        report.errors.append("name is missing")
        return
    if len(name) > MAX_NAME:
        report.errors.append(f"name is longer than {MAX_NAME} characters")
    if not NAME_RE.match(name):
        report.errors.append(
            f"name '{name}' must use a-z, 0-9 and single hyphens, not at the start or end"
        )
    if name != folder:
        report.errors.append(f"name '{name}' does not match the folder '{folder}'")


def _links(text: str) -> List[str]:
    found, fenced = [], False
    for line in text.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        line = re.sub(r"`[^`]*`", "", line)  # code spans are not links
        for match in _LINK.finditer(line):
            found.append(match.group(1) or match.group(2))
    return found


def _check_links(files: Dict[str, bytes], report: Report, sibling: Optional[Sibling]) -> None:
    for rel, data in files.items():
        if not rel.endswith(".md"):
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            report.errors.append(f"{rel} is not UTF-8")
            continue
        for link in _links(text):
            target = link.split("#", 1)[0]
            if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target[0] == "/":
                continue  # anchor, URL (http:, mailto:) or absolute: not checked here
            joined = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
            if joined.startswith("../") or joined == "..":
                parts = joined.split("/", 2)  # ['..', '<sibling>', '<path>']
                if len(parts) == 3 and sibling is not None and sibling(parts[1], parts[2]):
                    continue  # a file of a skill that is always installed with this one
                report.errors.append(f"{rel}: link '{link}' points outside the skill")
            elif joined not in files and not any(f.startswith(joined + "/") for f in files):
                report.errors.append(f"{rel}: broken link '{link}'")


def _yaml_top_keys(text: str) -> Dict[str, List[str]]:
    """Top-level keys of a small YAML file and the keys directly under each (2-space)."""
    keys: Dict[str, List[str]] = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key = line.strip().split(":", 1)[0]
        if indent == 0:
            current = key
            keys[current] = []
        elif current is not None and not line.strip().startswith("-"):
            if indent == 2:
                keys[current].append(key)
    return keys


def _check_openai_yaml(data: bytes, report: Report) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        report.errors.append(f"{OPENAI_YAML} is not UTF-8")
        return
    for top, subs in _yaml_top_keys(text).items():
        if top not in OPENAI_KEYS:
            report.warnings.append(f"{OPENAI_YAML}: unknown key '{top}'")
            continue
        for sub in subs:
            if sub not in OPENAI_KEYS[top]:
                report.warnings.append(f"{OPENAI_YAML}: unknown key '{top}.{sub}'")
    match = re.search(r"^\s+allow_implicit_invocation:\s*(\S+)", text, re.MULTILINE)
    if match and match.group(1).lower() not in ("true", "false"):
        report.errors.append(f"{OPENAI_YAML}: allow_implicit_invocation must be true or false")


def check(
    name: str,
    files: List[Tuple[str, bytes]],
    agent: str,
    kit_rules: bool = True,
    sibling: Optional[Sibling] = None,
) -> Report:
    """Check one skill as `agent` will receive it (files after kit.catalog merges layers).

    `sibling` allows links to `../<other skill>/<path>` when that file is installed with it
    (catalog "requires"); without it every link outside the skill folder is an error."""
    report = Report()
    by_path = dict(files)
    if "SKILL.md" not in by_path:
        report.errors.append("SKILL.md is missing")
        return report
    try:
        text = by_path["SKILL.md"].decode("utf-8")
        meta = parse_frontmatter(text)
    except (UnicodeDecodeError, ValueError) as exc:
        report.errors.append(f"SKILL.md: {exc}")
        return report

    _check_name(meta.get("name"), name, report)
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        report.errors.append("description is missing")
        description = ""
    elif len(description) > MAX_DESCRIPTION:
        report.errors.append(f"description is longer than {MAX_DESCRIPTION} characters")
    compatibility = meta.get("compatibility")
    if compatibility is not None and not (
        isinstance(compatibility, str) and 1 <= len(compatibility) <= MAX_COMPATIBILITY
    ):
        report.errors.append(f"compatibility must be 1-{MAX_COMPATIBILITY} characters")
    if "metadata" in meta and not isinstance(meta["metadata"], dict):
        report.errors.append("metadata must be a map of key: value lines")

    if agent == "claude":
        if any(c in str(meta.get("name", "")) for c in "<>"):
            report.errors.append("name may not contain < or > (Claude Code)")
        listing = len(description) + len(str(meta.get("when_to_use", "")))
        if listing > CLAUDE_LISTING:
            report.warnings.append(
                f"description + when_to_use is {listing} characters; Claude Code cuts the "
                f"listing at {CLAUDE_LISTING}"
            )
        for key in sorted(set(meta) - CLAUDE_FIELDS):
            report.warnings.append(f"field '{key}' is ignored by Claude Code")
        if OPENAI_YAML in by_path:
            report.warnings.append(f"{OPENAI_YAML} is Codex-only; move it to codex/skills/{name}/")
    elif agent == "codex":
        for key in sorted(set(meta) & CLAUDE_ONLY):
            report.warnings.append(
                f"field '{key}' is Claude Code only; move it to claude/skills/{name}/"
            )
        for key in sorted(set(meta) - CLAUDE_FIELDS):
            report.warnings.append(f"field '{key}' is not a known skill field")
        if OPENAI_YAML in by_path:
            _check_openai_yaml(by_path[OPENAI_YAML], report)

    if text.count("\n") + 1 > MAX_LINES:
        report.warnings.append(f"SKILL.md is longer than {MAX_LINES} lines")
    _check_links(by_path, report, sibling)

    if kit_rules and description:
        if len(description) > KIT_MAX_DESCRIPTION:
            report.errors.append(
                f"kit rule: description is longer than {KIT_MAX_DESCRIPTION} characters"
            )
        if "Do NOT use" not in description:
            report.errors.append("kit rule: description must say when 'Do NOT use' the skill")
    return report
