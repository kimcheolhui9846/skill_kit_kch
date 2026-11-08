"""`kit capture`: copy this PC's portable global settings into user/ (P4-T7, ADR-019).

Allowlist only (user/capture-allowlist.json): nothing outside it is read into the repo, so
auth files, sessions, sqlite, history, `projects.*` trust paths and connector IDs never come
in. Home paths become ${HOME}; env and header values become ${ENV:NAME}. A final scan of every
output stops the whole capture (nothing written, exit 1) on any secret-like value; the report
names the file and line, never the value (R-09).

Default is a dry run; --write writes user/. The kit's own block in the global files is left
out, so capture after `install --scope user` does not copy the kit back into itself.
"""

from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import secrets_scan, userscope
from .fsops import path_order, safe_path, sha256
from .model import TargetError
from .writers import markdown_block, toml_block
from .writers.markdown_block import MarkerError, extract_block

ALLOWLIST_REL = "user/capture-allowlist.json"
SNAPSHOT_FILES = {
    "codex": [
        "user/codex/AGENTS.block.md",
        "user/codex/config.toml",
        "user/codex/mcp.json",
        "user/codex/inventory.json",
    ],
    "claude": ["user/claude/CLAUDE.block.md", "user/claude/settings.json", "user/claude/mcp.json"],
}
# REQ-USER-004 patterns on top of kit.secrets_scan
EXTRA_PATTERNS = [
    ("bearer token", re.compile(r"(?i)\bbearer\s+(?!\$\{)[A-Za-z0-9._~+/=-]{8,}")),
    (  # a literal value: NAME = "value" / NAME: 'value' / NAME=value (env style, no spaces)
        "token/secret assignment",
        re.compile(
            r"(?i)\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY)\b"
            r"(?:\s*[=:]\s*[\"'](?!\$\{)[^\s\"'$]{6,}[\"']|=(?![\"'$])[^\s\"'$]{6,})"
        ),
    ),
]
_REDACT_TABLE = re.compile(r"(?:^|\.)(env|headers|http_headers|env_http_headers)$")
_KEY_VALUE = re.compile(r"^(\s*)([A-Za-z0-9_\"'.-]+)(\s*=\s*)(.+?)\s*$")
_INLINE = re.compile(r"^(\s*(?:env|headers|http_headers|env_http_headers)\s*=\s*)\{(.*)\}\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class CaptureResult:
    files: Dict[str, str] = field(default_factory=dict)  # repo rel -> text
    notes: List[str] = field(default_factory=list)  # what was left out, and why
    hits: List[Tuple[str, str, int]] = field(default_factory=list)  # (rel, label, line)


def load_allowlist(kit_root: Path) -> dict:
    data = json.loads((kit_root / ALLOWLIST_REL).read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise TargetError(f"{ALLOWLIST_REL}: unsupported schema {data.get('schema')!r}")
    return data


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_bytes().decode("utf-8") if path.is_file() else None
    except (OSError, UnicodeDecodeError):
        return None


def _strip_block(text: str, begin: str, end: str) -> str:
    try:
        found = extract_block(text, begin, end)
    except MarkerError:
        return text
    if found is None:
        return text
    return (text[: found[0]].rstrip("\n") + "\n" + text[found[1] :].lstrip("\n")).strip() + "\n"


# ---------------------------------------------------------------- markdown sections


def sections(text: str) -> List[Tuple[Optional[str], str]]:
    """[(level-2 heading title or None for the top, text)]; headings in code fences ignored."""
    out: List[Tuple[Optional[str], List[str]]] = [(None, [])]
    fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            fence = not fence
        if not fence and line.startswith("## "):
            out.append((line[3:].strip(), [line]))
        else:
            out[-1][1].append(line)
    return [(title, "".join(lines)) for title, lines in out]


def _excluded(title: Optional[str], patterns: List[str]) -> bool:
    return title is not None and any(fnmatch.fnmatchcase(title, p) for p in patterns)


def capture_policy(text: str, rule: dict, home: Path, notes: List[str], label: str) -> str:
    text = _strip_block(text, markdown_block.BEGIN, markdown_block.END)
    if rule.get("mode") == "sections":
        kept = []
        for title, body in sections(text):
            if _excluded(title, rule.get("sections_exclude", [])):
                notes.append(f"{label}: section left out: {userscope.template_home(title, home)}")
            else:
                kept.append(body)
        text = "".join(kept)
    return userscope.template_home(text, home).strip() + "\n"


# ---------------------------------------------------------------- config.toml


def _redact_line(line: str) -> str:
    inline = _INLINE.match(line)
    if inline:
        keys = re.findall(r"([A-Za-z0-9_\"'-]+)\s*=", inline.group(2))
        names = [k.strip("\"'") for k in keys]
        body = ", ".join(f'{n} = "${{ENV:{n}}}"' for n in names)
        return f"{inline.group(1)}{{ {body} }}\n"
    return line


def _redact_table(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        match = _KEY_VALUE.match(line)
        if match and not line.lstrip().startswith("["):
            name = match.group(2).strip("\"'")
            out.append(f'{match.group(1)}{match.group(2)}{match.group(3)}"${{ENV:{name}}}"\n')
        else:
            out.append(line)
    return "".join(out)


def capture_toml(text: str, rule: dict, home: Path, notes: List[str]) -> Tuple[str, List[str]]:
    """(captured tables, MCP server names)."""
    text = _strip_block(text, toml_block.BEGIN, toml_block.END)
    keep_patterns = rule.get("toml_tables", [])
    drop_patterns = rule.get("toml_tables_exclude", [])
    kept, left = [], {}
    servers = []
    top_keys = []
    for name, body in userscope.split_tables(text):
        if name is None:
            top_keys = [m.group(2) for m in map(_KEY_VALUE.match, body.splitlines()) if m]
            continue
        parts = userscope.split_name(name)
        if parts[0] == "mcp_servers" and len(parts) == 2:
            servers.append(parts[1].strip("\"'"))
        if userscope.matches(name, keep_patterns) and not userscope.matches(name, drop_patterns):
            if _REDACT_TABLE.search(name):
                body = _redact_table(body)
            body = "".join(_redact_line(line) for line in body.splitlines(keepends=True))
            kept.append(body.strip())
        else:
            left[parts[0]] = left.get(parts[0], 0) + 1  # names only: projects.* hold paths
    if top_keys:
        notes.append(
            "codex config.toml: top-level keys are not carried (set them by hand): "
            + ", ".join(k.strip("\"'") for k in top_keys)
        )
    for head, count in sorted(left.items()):
        notes.append(f"codex config.toml: [{head}.*] left out ({count} table(s))")
    out = "\n\n".join(kept)
    return (userscope.template_home(out, home) + "\n") if out else "", servers


# ---------------------------------------------------------------- inventory


def _same_tree(a: Path, b: Path) -> bool:
    def files(root: Path) -> Dict[str, str]:
        return {
            p.relative_to(root).as_posix(): sha256(p.read_bytes())
            for p in root.rglob("*")
            if p.is_file()
        }

    try:
        return files(a) == files(b)
    except OSError:
        return False


def inventory(kit_root: Path, codex_root: Path, rule: dict) -> dict:
    """Names and origin only; contents are never copied (REQ-USER-001)."""
    omx = kit_root / userscope.OMX_DIR
    exclude = rule.get("inventory_exclude", [])
    out: Dict[str, List[dict]] = {}
    for kind in rule.get("inventory", []):
        folder = codex_root / kind
        if not folder.is_dir():
            continue
        rows = []
        for path in sorted(folder.iterdir(), key=lambda p: p.name):
            if path.name in exclude or ".backup" in path.name or path.name.startswith("."):
                continue
            copied = rule.get("copy", {}).get(kind, [])
            if path.is_symlink():
                origin = "link (external source)"
            elif path.name in copied:
                origin = f"carried as your own ({userscope.OWN_DIR}/{kind})"
            elif kind == "skills" and (omx / "skills" / path.name).is_dir():
                same = _same_tree(path, omx / "skills" / path.name)
                origin = "omx v0.21.46" if same else "omx (differs from v0.21.46)"
            elif kind == "prompts" and (omx / "prompts" / path.name).is_file():
                same = path.read_bytes() == (omx / "prompts" / path.name).read_bytes()
                origin = "omx v0.21.46" if same else "omx (differs from v0.21.46)"
            elif kind == "agents":
                origin = "generated by omx setup (not carried)"
            else:
                origin = "unknown origin (not carried)"
            rows.append({"name": path.name, "origin": origin})
        out[kind] = rows
    return out


# ---------------------------------------------------------------- settings and MCP names


def capture_settings(text: str, pointers: List[str], home: Path) -> Dict[str, object]:
    doc = json.loads(text)
    keys: Dict[str, object] = {}
    for pointer in pointers:
        name = pointer.lstrip("/")
        if name not in doc:
            continue
        value = doc[name]
        if isinstance(value, dict):  # own each child, so the user's other entries stay theirs
            for child, sub in value.items():
                keys[f"/{name}/{child.replace('~', '~0').replace('/', '~1')}"] = sub
        else:
            keys[pointer] = value
    return json.loads(userscope.template_home(json.dumps(keys), home))


def claude_json_path(home: Path) -> Path:
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(raw) / ".claude.json") if raw else home / ".claude.json"


def claude_mcp_names(text: str) -> List[dict]:
    """Names and transport only (names-and-commands-only: values are never kept)."""
    doc = json.loads(text)
    servers = doc.get("mcpServers") or {}
    out = []
    for name, entry in sorted(servers.items()):
        if isinstance(entry, dict):
            kind = entry.get("type") or ("stdio" if "command" in entry else "unknown")
            out.append({"name": name, "transport": kind})
    return out


# ---------------------------------------------------------------- capture


def _dump(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def scan(rel: str, text: str) -> List[Tuple[str, str, int]]:
    hits = [(rel, label, line) for label, line in secrets_scan.find(text)]
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in EXTRA_PATTERNS:
            if pattern.search(line):
                hits.append((rel, label, number))
    return hits


def capture(kit_root: Path, home: Path, agents: List[str]) -> CaptureResult:
    rules = load_allowlist(kit_root)
    result = CaptureResult()
    if "codex" in agents:
        _capture_codex(kit_root, home, rules["codex"], result)
    if "claude" in agents:
        _capture_claude(home, rules["claude"], result)
    for rel, text in result.files.items():
        result.hits += scan(rel, text)
        leftover = re.search(r"(?i)\b[A-Z]:\\Users\\|/home/[^/$]+/|/Users/[^/$]+/", text)
        if leftover:
            result.notes.append(f"{rel}: a home path of another user is still in the text")
    return result


def _capture_codex(kit_root: Path, home: Path, rule: dict, result: CaptureResult) -> None:
    root = home / userscope.agent_dir("codex", home)
    policy = rule["policy"]
    text = _read(root / policy["from"])
    if text is not None:
        body = capture_policy(text, policy, home, result.notes, "codex AGENTS.md")
        if body.strip():
            result.files[policy["to"]] = body
    config = _read(root / "config.toml")
    if config is not None:
        tables, servers = capture_toml(config, rule, home, result.notes)
        if tables:
            result.files[userscope.CODEX_CONFIG] = tables
        if rule.get("mcp_names") and servers:
            names = [{"name": n} for n in servers]
            result.files[userscope.MCP_NAMES["codex"]] = _dump({"schema": 1, "servers": names})
    rows = inventory(kit_root, root, rule)
    if rows:
        result.files["user/codex/inventory.json"] = _dump({"schema": 1, **rows})
    _copy_own(root, rule, result)


def _copy_own(root: Path, rule: dict, result: CaptureResult) -> None:
    """Q4: files the user keeps as their own, copied as text (the secret scan still runs)."""
    for kind in ("skills", "prompts"):
        for name in rule.get("copy", {}).get(kind, []):
            source = root / kind / name
            paths = (
                sorted((p for p in source.rglob("*") if p.is_file()), key=path_order)
                if source.is_dir()
                else [source]
            )
            if not source.exists() or source.is_symlink():
                result.notes.append(f"codex {kind}/{name}: not found (or a link), not copied")
                continue
            for path in paths:
                rel = f"{userscope.OWN_DIR}/{kind}/{path.relative_to(root / kind).as_posix()}"
                text = _read(path)
                if text is None:
                    result.notes.append(f"{rel}: not UTF-8 text, not copied")
                    continue
                result.files[rel] = text


def _capture_claude(home: Path, rule: dict, result: CaptureResult) -> None:
    root = home / userscope.agent_dir("claude", home)
    policy = rule["policy"]
    text = _read(root / policy["from"])
    if text is not None:
        body = capture_policy(text, policy, home, result.notes, "claude CLAUDE.md")
        if body.strip():
            result.files[policy["to"]] = body
    settings = _read(root / "settings.json")
    if settings is not None:
        try:
            keys = capture_settings(settings, rule.get("settings_pointers", []), home)
        except ValueError:
            result.notes.append("claude settings.json: not valid JSON, left out")
            keys = {}
        if keys:
            result.files[userscope.CLAUDE_SETTINGS] = _dump({"schema": 1, "keys": keys})
    if rule.get("mcp_names"):
        raw = _read(claude_json_path(home))
        if raw is not None:
            try:
                names = claude_mcp_names(raw)
            except (ValueError, AttributeError):
                names = []
                result.notes.append("~/.claude.json: not valid JSON, MCP names left out")
            if names:
                body = _dump({"schema": 1, "servers": names})
                result.files[userscope.MCP_NAMES["claude"]] = body


def changes(kit_root: Path, result: CaptureResult, agents: List[str]) -> List[Tuple[str, str]]:
    """[(rel, CREATE|UPDATE|UNCHANGED|REMOVE (+N -M))] against the files in user/ now."""
    rows = []
    known = [r for a in agents for r in SNAPSHOT_FILES[a]]
    own = kit_root / userscope.OWN_DIR
    if "codex" in agents and own.is_dir():  # so a file no longer copied is removed
        known += [p.relative_to(kit_root).as_posix() for p in own.rglob("*") if p.is_file()]
    for rel in sorted(set(known) | set(result.files)):
        old = _read(kit_root / rel)
        new = result.files.get(rel)
        if new is None:
            if old is not None:
                rows.append((rel, "REMOVE"))
            continue
        if old is None:
            rows.append((rel, f"CREATE (+{len(new.splitlines())})"))
        elif old == new:
            rows.append((rel, "UNCHANGED"))
        else:
            diff = list(difflib.ndiff(old.splitlines(), new.splitlines()))
            plus = sum(1 for d in diff if d.startswith("+ "))
            minus = sum(1 for d in diff if d.startswith("- "))
            rows.append((rel, f"UPDATE (+{plus} -{minus})"))
    return rows


def write(kit_root: Path, result: CaptureResult, agents: List[str]) -> None:
    for rel, status in changes(kit_root, result, agents):
        path = safe_path(kit_root, rel)  # P6-T3: a link under user/ cannot lead outside
        if status == "REMOVE":
            path.unlink()
        elif status != "UNCHANGED":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(result.files[rel].encode("utf-8"))
