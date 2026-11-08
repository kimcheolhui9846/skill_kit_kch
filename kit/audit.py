"""Audit the target's MCP config against mcp/allowlist.json. Reduces risk; not a guarantee."""

from __future__ import annotations

import json
import re
from pathlib import Path, PureWindowsPath

from . import mcpconfig
from .model import FAIL, PASS, UNVERIFIED, ItemResult

LABEL = "security audit"
_REMOTE = re.compile(r"https?://", re.IGNORECASE)


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _command_name(command: object) -> str:
    name = PureWindowsPath(str(command)).name.lower()
    for suffix in (".cmd", ".exe", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def audit_config(data: dict, allowlist: dict) -> list[str]:
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict):
        return ["mcp_servers must be a table"]
    patterns = [re.compile(p) for p in allowlist["forbidden_env_patterns"]]
    problems = []
    for name, cfg in servers.items():
        if name not in allowlist["servers"]:
            problems.append(f"{name}: not in mcp/allowlist.json")
        if not isinstance(cfg, dict):
            problems.append(f"{name}: must be a table")
            continue
        for key in allowlist["forbidden_keys"]:
            if key in cfg:
                problems.append(f"{name}: forbidden key '{key}' (remote transport)")
        command = cfg.get("command")
        if command is not None and _command_name(command) not in allowlist["commands"]:
            problems.append(f"{name}: command '{command}' is not allowed")
        for text in _strings(cfg):
            if _REMOTE.search(text):
                problems.append(f"{name}: remote endpoint '{text}'")
        # P4-T9: a key name the catalog declares for this server may be passed through as a
        # reference (Codex env_vars, or Claude "NAME": "${NAME}"); a written value never may.
        declared = set(allowlist.get("declared_env", {}).get(name, []))
        env = cfg.get("env")
        env_names = []
        if isinstance(env, dict):
            env_names = [k for k, v in env.items() if not (k in declared and v == "${" + k + "}")]
        env_vars = cfg.get("env_vars")
        if isinstance(env_vars, list):
            env_names += [v for v in env_vars if isinstance(v, str) and v not in declared]
        for env_name in env_names:
            if any(p.search(env_name) for p in patterns):
                problems.append(f"{name}: secret-like env '{env_name}'")
    return problems


_TABLE = re.compile(r"^[ 	]*\[")
_MCP_TABLE = re.compile(r"^[ 	]*\[[ 	]*mcp_servers[ 	]*[.\]]")
_MCP_ROOT = re.compile(r"^[ 	]*\[[ 	]*mcp_servers[ 	]*\]")
# the server a [mcp_servers.<name>] or [mcp_servers.<name>.env] table belongs to
_SERVER = re.compile(r'^[ 	]*\[[ 	]*mcp_servers[ 	]*\.[ 	]*"?([A-Za-z0-9_-]+)"?')
# a server written inline under [mcp_servers]: name = { command = "...", ... }
_INLINE = re.compile(r'^[ 	]*"?([A-Za-z0-9_-]+)"?[ 	]*=[ 	]*\{')
_COMMAND = re.compile(r"""\bcommand[ 	]*=[ 	]*["']([^"']*)["']""")
_ENV_VARS = re.compile(r"^[ 	]*env_vars[ 	]*=")
_WORD = re.compile(r"[A-Za-z0-9_]+")
SCAN_NOTE = " (line scan; Python 3.11+ gives a full audit)"


def _reference(word: str, line: str) -> bool:
    """`env_vars = [..., "NAME"]` or `NAME = "${NAME}"`: a name passed through, not a value."""
    if _ENV_VARS.match(line):
        return True
    w = re.escape(word)
    return bool(re.match(rf'^[ 	]*"?{w}"?[ 	]*=[ 	]*"\$\{{{w}\}}"[ 	]*(#.*)?$', line))


def scan_lines(text: str, allowlist: dict) -> list[str]:
    """Conservative audit of raw text for when TOML cannot be parsed (Python 3.9/3.10).

    P6-T3: the same rules as audit_config, where a line can show them: server names (table
    headers and inline tables), commands, forbidden keys, remote endpoints and secret-like env
    names, with the catalog's declared names allowed as references only.
    """
    keys = [re.compile(rf"^[ 	]*({re.escape(k)})[ 	]*=") for k in allowlist["forbidden_keys"]]
    patterns = [re.compile(p) for p in allowlist["forbidden_env_patterns"]]
    declared_env = allowlist.get("declared_env", {})
    problems: list[str] = []

    def add(problem: str) -> None:
        if problem not in problems:
            problems.append(problem)

    in_mcp = in_root = False
    server = ""
    for line in text.splitlines():
        if _TABLE.match(line):
            in_mcp = bool(_MCP_TABLE.match(line))
            in_root = bool(_MCP_ROOT.match(line))
            found = _SERVER.match(line)
            server = found.group(1) if found else ""
            header = mcpconfig._HEADER.match(line)
            if header and header.group(1) not in allowlist["servers"]:
                add(f"{header.group(1)}: not in mcp/allowlist.json")
        if not in_mcp:
            continue
        name = server
        inline = _INLINE.match(line) if in_root else None
        if inline:
            name = inline.group(1)
            if name not in allowlist["servers"]:
                add(f"{name}: not in mcp/allowlist.json")
        for key in keys:
            found = key.match(line)
            if found:
                add(f"forbidden key '{found.group(1)}' (remote transport)")
        for command in _COMMAND.findall(line):
            if _command_name(command) not in allowlist["commands"]:
                add(f"{name or 'mcp_servers'}: command '{command}' is not allowed")
        if _REMOTE.search(line):
            add("remote endpoint in mcp_servers")
        declared = set(declared_env.get(name, []))
        for word in _WORD.findall(line):
            if word in declared and _reference(word, line):
                continue
            if any(p.search(word) for p in patterns):
                add(f"secret-like env '{word}'")
    return problems


def _fail(problems: list[str], suffix: str = "") -> ItemResult:
    more = f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""
    return ItemResult(LABEL, True, True, True, FAIL, "; ".join(problems[:3]) + more + suffix)


def audit_target(target: Path, kit_root: Path, allowlist: dict | None = None) -> ItemResult:
    path = target / mcpconfig.CONFIG_REL
    if not path.is_file():
        return audit_toml_data(None, kit_root, allowlist)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ItemResult(LABEL, True, True, False, FAIL, f"cannot read config: {exc}")
    return audit_toml_data(raw, kit_root, allowlist)


def audit_toml_data(raw: bytes | None, kit_root: Path, allowlist: dict | None = None) -> ItemResult:
    """The TOML audit of given bytes (None = no file). B-3: the v2 path passes the config it
    plans to leave behind, before it writes; audit_target passes the file on disk."""
    if raw is None:
        return ItemResult(LABEL, True, True, True, PASS, f"no {mcpconfig.CONFIG_REL}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ItemResult(LABEL, True, True, False, FAIL, f"cannot read config: {exc}")
    status, data, error = mcpconfig.parse_toml(text)
    allowlist = allowlist or mcpconfig.load_allowlist(kit_root)
    if status is None or status is False:
        problems = scan_lines(text, allowlist)
        if problems:
            return _fail(problems, SCAN_NOTE)
        if status is None:
            detail = "config audit needs Python 3.11+ (tomllib)"
        else:
            detail = f"cannot audit: config is not valid TOML ({error})"
        return ItemResult(LABEL, True, True, False, UNVERIFIED, detail)
    problems = audit_config(data, allowlist)
    if problems:
        return _fail(problems)
    return ItemResult(LABEL, True, True, True, PASS, "MCP config matches the allowlist")


MCP_JSON_REL = ".mcp.json"
_LOCAL_TYPES = (None, "stdio")


def audit_mcp_json(target: Path, kit_root: Path, allowlist: dict | None = None) -> ItemResult:
    """Same rules as the TOML audit, applied to Claude Code's .mcp.json (P3-T4)."""
    path = target / MCP_JSON_REL
    if not path.is_file():
        return audit_mcp_json_data(None, kit_root, allowlist)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return ItemResult(
            LABEL, True, True, False, UNVERIFIED, f"cannot audit {MCP_JSON_REL}: {exc}"
        )
    return audit_mcp_json_data(raw, kit_root, allowlist)


def audit_mcp_json_data(
    raw: bytes | None, kit_root: Path, allowlist: dict | None = None
) -> ItemResult:
    """The .mcp.json audit of given bytes (None = no file); see audit_toml_data."""
    if raw is None:
        return ItemResult(LABEL, True, True, True, PASS, f"no {MCP_JSON_REL}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return ItemResult(
            LABEL, True, True, False, UNVERIFIED, f"cannot audit {MCP_JSON_REL}: {exc}"
        )
    if not isinstance(data, dict):
        return _fail([f"{MCP_JSON_REL}: top level must be an object"])
    servers = data.get("mcpServers", {})
    allowlist = allowlist or mcpconfig.load_allowlist(kit_root)
    problems = audit_config({"mcp_servers": servers}, allowlist)
    if isinstance(servers, dict):
        for name, cfg in servers.items():
            if isinstance(cfg, dict) and cfg.get("type") not in _LOCAL_TYPES:
                problems.append(f"{name}: transport '{cfg.get('type')}' is remote")
            if isinstance(cfg, dict) and "headers" in cfg:
                problems.append(f"{name}: forbidden key 'headers' (remote transport)")
    if problems:
        return _fail(problems)
    return ItemResult(LABEL, True, True, True, PASS, f"{MCP_JSON_REL} matches the allowlist")
