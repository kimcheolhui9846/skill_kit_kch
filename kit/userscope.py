"""User (home) scope: where things go and what the repo snapshot holds (P4-T7, ADR-018).

`kit install --scope user` installs, per agent:
- the captured personal policy text (user/<agent>/*.block.md) as the kit block of
  ~/.codex/AGENTS.md or ~/.claude/CLAUDE.md. The kit's own policy text stays in projects
  (decision 2026-11-06: snapshot + OMX + kit skills);
- the profile's kit skills in ~/.codex/skills/ or ~/.claude/skills/;
- Codex: OMX skills and prompts (third_party/Yeachan-Heo-oh-my-codex, sources.lock.json), and
  a kit block in ~/.codex/config.toml with the catalog MCP servers and the captured tables;
- Claude: captured ~/.claude/settings.json keys (kit-owned keys, ADR-005). User MCP servers live
  in ~/.claude.json, which Claude rewrites while it runs, so the kit only prints
  `claude mcp add --scope user ...` commands.

CODEX_HOME and CLAUDE_CONFIG_DIR are honoured when they are inside the home folder.
The snapshot uses ${HOME} for the home folder; nothing else is machine specific.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .fsops import path_order
from .model import TargetError

HOME_VAR = "${HOME}"
SNAPSHOT_DIR = "user"
OMX_DIR = "third_party/Yeachan-Heo-oh-my-codex"
OMX_LOCK_ID = "oh-my-codex"
AGENTS_MD_WARN = 28 * 1024  # 05_CLI_SPEC: warn above 28 KiB (Codex reads 32 KiB by default)
ENV = {"codex": "CODEX_HOME", "claude": "CLAUDE_CONFIG_DIR"}
DEFAULT_DIR = {"codex": ".codex", "claude": ".claude"}
BLOCK_FILE = {"codex": "user/codex/AGENTS.block.md", "claude": "user/claude/CLAUDE.block.md"}
CODEX_CONFIG = "user/codex/config.toml"
CLAUDE_SETTINGS = "user/claude/settings.json"
MCP_NAMES = {"codex": "user/codex/mcp.json", "claude": "user/claude/mcp.json"}


def home() -> Path:
    return Path.home().resolve()


def agent_dir(agent: str, home_dir: Optional[Path] = None) -> str:
    """The agent's config folder relative to home, e.g. ".codex"."""
    home_dir = home_dir or home()
    raw = os.environ.get(ENV[agent])
    if not raw:
        return DEFAULT_DIR[agent]
    path = Path(raw).expanduser().resolve()
    if path != home_dir and home_dir not in path.parents:
        raise TargetError(
            f"{ENV[agent]}={raw} is outside the home folder; --scope user only writes under ~"
        )
    return path.relative_to(home_dir).as_posix()


def tilde(rel: str) -> str:
    return "~/" + rel


# ---------------------------------------------------------------- ${HOME} templating


def home_variants(home_dir: Path) -> List[str]:
    """Spellings of the home folder found in config files, longest first."""
    native = str(home_dir)
    found = {native, home_dir.as_posix(), native.replace("\\", "\\\\")}
    return sorted(found, key=len, reverse=True)


def template_home(text: str, home_dir: Path) -> str:
    for variant in home_variants(home_dir):
        text = re.sub(re.escape(variant), lambda _: HOME_VAR, text, flags=re.IGNORECASE)
    return text


def expand_home(text: str, home_dir: Path, posix: bool = False) -> str:
    value = home_dir.as_posix() if posix else str(home_dir)
    return text.replace(HOME_VAR, value)


# ---------------------------------------------------------------- snapshot (user/)


def _read(kit_root: Path, rel: str) -> Optional[str]:
    path = kit_root / rel
    return path.read_text(encoding="utf-8") if path.is_file() else None


def policy_block(kit_root: Path, agent: str, home_dir: Path) -> Optional[str]:
    text = _read(kit_root, BLOCK_FILE[agent])
    if text is None or not text.strip():
        return None
    return expand_home(text, home_dir)


def codex_tables(kit_root: Path, home_dir: Path) -> Optional[str]:
    text = _read(kit_root, CODEX_CONFIG)
    if text is None or not text.strip():
        return None
    return expand_home(text, home_dir, posix=True).strip() + "\n"


def claude_settings(kit_root: Path, home_dir: Path) -> Dict[str, object]:
    text = _read(kit_root, CLAUDE_SETTINGS)
    if text is None:
        return {}
    data = json.loads(text)
    keys = data.get("keys", {}) if isinstance(data, dict) else {}
    return {p: _expand_value(v, home_dir) for p, v in keys.items()}


def _expand_value(value, home_dir: Path):
    if isinstance(value, str):
        return expand_home(value, home_dir)
    if isinstance(value, list):
        return [_expand_value(v, home_dir) for v in value]
    if isinstance(value, dict):
        return {k: _expand_value(v, home_dir) for k, v in value.items()}
    return value


def mcp_names(kit_root: Path, agent: str) -> List[str]:
    text = _read(kit_root, MCP_NAMES[agent])
    if text is None:
        return []
    data = json.loads(text)
    return [s["name"] for s in data.get("servers", []) if isinstance(s, dict) and "name" in s]


# ---------------------------------------------------------------- OMX (REQ-USER-005)


def omx_files(kit_root: Path, codex_dir: str) -> List[Tuple[str, str, bytes]]:
    """(home-relative path, kit-relative source, bytes) for the vendored OMX skills and
    prompts. agents/*.toml are not in the pinned tag (omx setup generates them)."""
    root = kit_root / OMX_DIR
    out = []
    for sub in ("skills", "prompts"):
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*"), key=path_order):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                out.append(
                    (f"{codex_dir}/{rel}", path.relative_to(kit_root).as_posix(), path.read_bytes())
                )
    return out


OWN_DIR = "user/codex/own"  # PC files kept as the user's own (capture "copy", Q4)


def own_files(kit_root: Path, codex_dir: str) -> List[Tuple[str, str, bytes]]:
    """(home-relative path, kit-relative source, bytes) for user/codex/own/{skills,prompts}."""
    root = kit_root / OWN_DIR
    out = []
    for sub in ("skills", "prompts"):
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*"), key=path_order):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                out.append(
                    (f"{codex_dir}/{rel}", path.relative_to(kit_root).as_posix(), path.read_bytes())
                )
    return out


def own_skill_names(kit_root: Path) -> List[str]:
    base = kit_root / OWN_DIR / "skills"
    return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


def omx_skill_names(kit_root: Path) -> List[str]:
    base = kit_root / OMX_DIR / "skills"
    return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


# ---------------------------------------------------------------- TOML tables (no parser)

_KEY_PART = re.compile(r'^(?:[A-Za-z0-9_-]+|"(?:[^"\\]|\\.)*"|\'[^\']*\')$')


def header(line: str) -> Optional[str]:
    """Table name of a `[a.b]` or `[[a.b]]` line (quoted keys may hold brackets), else None."""
    text = line.strip()
    if not text.startswith("["):
        return None
    double = text.startswith("[[")
    start = i = 2 if double else 1
    quote = None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "]":
            break
        i += 1
    else:
        return None
    rest = text[i + 1 :]
    if double:
        if not rest.startswith("]"):
            return None
        rest = rest[1:]
    rest = rest.strip()
    if rest and not rest.startswith("#"):
        return None
    name = table_name(text[start:i])
    parts = split_name(name)
    if not parts or not all(_KEY_PART.match(p) for p in parts):
        return None
    return name


def split_name(name: str) -> List[str]:
    parts, buf, quote = [], "", None
    for ch in name:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ".":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return parts


def table_name(raw: str) -> str:
    """'plugins . "a@b"' -> 'plugins."a@b"' (quotes kept, spaces around dots dropped)."""
    parts, buf, quote = [], "", None
    for ch in raw.strip():
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ".":
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    parts.append(buf.strip())
    return ".".join(parts)


def split_tables(text: str) -> List[Tuple[Optional[str], str]]:
    """[(table name or None for the top, its lines)] in file order. Lines inside multi-line
    strings are never taken for headers."""
    chunks: List[Tuple[Optional[str], List[str]]] = [(None, [])]
    in_string: Optional[str] = None
    for line in text.splitlines(keepends=True):
        name = header(line) if in_string is None else None
        if name is not None:
            chunks.append((name, [line]))
        else:
            chunks[-1][1].append(line)
        for quote in ('"""', "'''"):
            if line.count(quote) % 2 == 1 and in_string in (None, quote):
                in_string = None if in_string == quote else quote
    return [(name, "".join(lines)) for name, lines in chunks]


def matches(name: str, patterns: List[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith(".*"):
            if name.startswith(pattern[:-1]):
                return True
        elif name == pattern or name.startswith(pattern + "."):
            return True
    return False


def table_names(text: str) -> List[str]:
    return [name for name, _ in split_tables(text) if name is not None]
