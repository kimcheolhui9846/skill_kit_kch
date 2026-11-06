"""Claude Code project MCP config: <target>/.mcp.json (02 matrix CC-MCP, ADR-005).

Same server data and allowlist as the Codex TOML block (kit.mcpconfig); only the file format
differs. The kit owns one key per server, /mcpServers/<name>; other servers are the user's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from . import mcpconfig
from .fsops import PathEscapeError, State, safe_path
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import FileChange
from .writers import json_keys

MCP_JSON_REL = ".mcp.json"
APPROVAL_NOTE = "Claude Code asks to approve project MCP servers on first use (run /mcp)"


def pointer(name: str) -> str:
    return "/mcpServers/" + name.replace("~", "~0").replace("/", "~1")


def record_key(ptr: str, rel: str = MCP_JSON_REL) -> str:
    """Key under which the per-pointer hash is stored in State.files."""
    return f"{rel}#{ptr}"


def render_entry(entry: dict) -> dict:
    """stdio entry; `type` is omitted because stdio is the default (CC-MCP)."""
    value = {"command": entry["command"], "args": list(entry["args"])}
    names = [c["env"] for c in entry.get("credentials") or []]
    if names:  # P4-T9: Claude expands ${NAME} from the environment; no value is written
        value["env"] = {n: "${" + n + "}" for n in names}
    return value


def wanted_keys(kit_root: Path, names: List[str]) -> Dict[str, dict]:
    return {pointer(n): render_entry(e) for n, e in mcpconfig.select_servers(kit_root, names)}


def _read(target: Path, rel: str = MCP_JSON_REL) -> tuple[Optional[str], Optional[str]]:
    """(text or None when missing, error)."""
    try:
        path = safe_path(target, rel)
        if path.exists() and not path.is_file():
            return None, "exists but is not a regular file"
        return (path.read_bytes().decode("utf-8") if path.is_file() else None), None
    except PathEscapeError as exc:
        return None, str(exc)
    except UnicodeDecodeError:
        return None, f"existing {rel} is not UTF-8"
    except OSError as exc:
        return None, f"cannot read {rel}: {exc}"


def plan_owned_keys(
    target: Path, rel: str, owner: str, keys: Dict[str, object], state: State
) -> FileChange:
    """Merge kit-owned JSON pointers into <target>/<rel> (ADR-005); user keys are kept."""
    text, error = _read(target, rel)
    if error:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=error)
    recorded = {
        p: state.files[record_key(p, rel)] for p in keys if record_key(p, rel) in state.files
    }
    plan = json_keys.plan_merge(text, keys, recorded)
    if plan.outcome == Outcome.CONFLICT:
        return FileChange(rel, owner, Outcome.CONFLICT, detail=plan.detail)
    data = plan.text.encode("utf-8") if plan.text is not None else None
    extra = {record_key(p, rel): h for p, h in plan.records.items()}
    return FileChange(rel, owner, plan.outcome, data, None, "", extra)


def verify_owned_keys(
    target: Path,
    rel: str,
    label: str,
    keys: Dict[str, object],
    conflict_detail: Optional[str],
    note: str,
) -> ItemResult:
    """PASS when every kit pointer in <rel> has exactly the kit value."""
    if conflict_detail:
        return ItemResult(label, False, True, False, CONFLICT, conflict_detail)
    text, error = _read(target, rel)
    if error:
        return ItemResult(label, False, True, False, FAIL, error)
    if text is None:
        return ItemResult(label, False, False, False, FAIL, f"{rel} missing")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ItemResult(label, False, True, False, FAIL, f"not valid JSON: {exc}")
    for ptr, value in keys.items():
        node: object = doc
        for part in json_keys.parse_pointer(ptr):
            node = node.get(part, json_keys._MISSING) if isinstance(node, dict) else None
        if node is json_keys._MISSING or node is None:
            return ItemResult(label, False, True, False, FAIL, f"{ptr} missing")
        if node != value:
            return ItemResult(label, False, True, True, FAIL, f"{ptr} is outdated")
    return ItemResult(label, False, True, True, PASS, note)


def plan_mcp_json(target: Path, kit_root: Path, names: List[str], state: State) -> FileChange:
    return plan_owned_keys(target, MCP_JSON_REL, "mcp-config", wanted_keys(kit_root, names), state)


def verify_mcp_json(
    target: Path, kit_root: Path, names: List[str], conflict_detail: Optional[str]
) -> ItemResult:
    label = "mcp-config"
    if conflict_detail:
        return ItemResult(label, False, True, False, CONFLICT, conflict_detail)
    text, error = _read(target)
    if error:
        return ItemResult(label, False, True, False, FAIL, error)
    if text is None:
        return ItemResult(label, False, False, False, FAIL, f"{MCP_JSON_REL} missing")
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ItemResult(label, False, True, False, FAIL, f"not valid JSON: {exc}")
    servers = doc.get("mcpServers") if isinstance(doc, dict) else None
    if not isinstance(servers, dict):
        return ItemResult(label, False, True, False, FAIL, "mcpServers missing")
    for name, entry in mcpconfig.select_servers(kit_root, names):
        if name not in servers:
            return ItemResult(label, False, True, False, FAIL, f"{name} not registered")
        if servers[name] != render_entry(entry):
            return ItemResult(label, False, True, True, FAIL, f"{name} entry is outdated")
    return ItemResult(label, False, True, True, PASS, APPROVAL_NOTE)
