"""Plans for removing what the kit owns (P3-T7): uninstall, and stale items during update.

Only manifest-owned items whose current content still has the recorded hash are removed.
Anything the user changed is left in place and reported as a conflict. Pure: no writes here;
kit.transaction applies the result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .fsops import PathEscapeError, safe_path, sha256
from .model import Outcome
from .writers import json_keys
from .writers.markdown_block import MarkerError, extract_block


@dataclass
class Op:
    """One file operation: data None = delete the file."""

    rel: str
    data: Optional[bytes]
    detail: str = ""


@dataclass
class RemovalPlan:
    ops: List[Op] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)  # "path: why", left in place
    forgotten: List[str] = field(default_factory=list)  # state.json keys to drop
    kept: List[str] = field(default_factory=list)  # "path" or "path#pointer" still owned

    def extend(self, other: "RemovalPlan") -> None:
        self.ops += other.ops
        self.conflicts += other.conflicts
        self.forgotten += other.forgotten
        self.kept += other.kept

    def keep(self, key: str, why: str) -> None:
        self.kept.append(key)
        self.conflicts.append(f"{key}: {why}")


def _read(target: Path, rel: str) -> Optional[bytes]:
    path = safe_path(target, rel)
    return path.read_bytes() if path.is_file() else None


def plan_removal(target: Path, entry: dict, adapter) -> RemovalPlan:
    """Undo one manifest entry. Block markers come from the adapter that owns the entry."""
    plan = RemovalPlan()
    markers = {
        adapter.policy.rel: (adapter.policy.begin, adapter.policy.end),
        adapter.mcp_config.rel: (adapter.mcp_config.begin, adapter.mcp_config.end),
    }
    for item in entry.get("files", []):
        rel = item["path"]
        try:
            raw = _read(target, rel)
        except (OSError, PathEscapeError) as exc:
            plan.keep(rel, str(exc))
            continue
        if raw is None:
            plan.forgotten.append(rel)
        elif sha256(raw) == item["sha256"]:
            plan.ops.append(Op(rel, None, "kit file"))
            plan.forgotten.append(rel)
        else:
            plan.keep(rel, "changed since the kit wrote it, left in place")
    for item in entry.get("blocks", []):
        plan.extend(_remove_block(target, item, markers.get(item["path"])))
    by_path: Dict[str, Dict[str, str]] = {}
    for item in entry.get("json_keys", []):
        if "sha256" in item:
            by_path.setdefault(item["path"], {})[item["pointer"]] = item["sha256"]
    for rel, recorded in by_path.items():
        plan.extend(_remove_keys(target, rel, recorded))
    return plan


def _remove_block(target: Path, item: dict, marker: Optional[tuple]) -> RemovalPlan:
    plan = RemovalPlan()
    rel = item["path"]
    if marker is None:
        plan.keep(rel, "no block markers known for this file")
        return plan
    try:
        raw = _read(target, rel)
        if raw is None:
            plan.forgotten.append(rel)
            return plan
        text = raw.decode("utf-8")
        found = extract_block(text, *marker)
    except (OSError, PathEscapeError, UnicodeDecodeError, MarkerError) as exc:
        plan.keep(rel, str(exc))
        return plan
    if found is None:
        plan.forgotten.append(rel)
        return plan
    start, stop, interior = found
    if sha256(interior.encode("utf-8")) != item["sha256"]:
        plan.keep(rel, "kit block was edited, left in place")
        return plan
    # Undo the append exactly (markdown_block.merge adds one "\n" before the block), so the
    # user's own bytes, CRLF included, come back unchanged.
    prefix = text[:start]
    if prefix.endswith("\n") and prefix[:-1].endswith("\n"):
        prefix = prefix[:-1]
    rest = prefix + text[stop:]
    if not rest.strip():
        plan.ops.append(Op(rel, None, "only the kit block was left"))
    else:
        plan.ops.append(Op(rel, rest.encode("utf-8"), "kit block removed"))
    plan.forgotten.append(rel)
    return plan


def _remove_keys(target: Path, rel: str, recorded: Dict[str, str]) -> RemovalPlan:
    plan = RemovalPlan()
    try:
        raw = _read(target, rel)
        text = raw.decode("utf-8") if raw is not None else None
    except (OSError, PathEscapeError, UnicodeDecodeError) as exc:
        for pointer in recorded:
            plan.keep(f"{rel}#{pointer}", str(exc))
        return plan
    result = json_keys.plan_remove(text, recorded)
    if result.outcome == Outcome.CONFLICT and not result.conflicts:
        for pointer in recorded:
            plan.keep(f"{rel}#{pointer}", result.detail)
        return plan
    for pointer in result.conflicts:
        plan.keep(f"{rel}#{pointer}", "changed since the kit wrote it, left in place")
    removed = [p for p in recorded if p not in result.conflicts]
    plan.forgotten += [f"{rel}#{p}" for p in removed]
    if result.text is not None:
        doc = json.loads(result.text)
        if _prune(doc, removed):
            indent, newline = json_keys.detect_format(text or "")
            result.text = json_keys.dump(doc, indent, newline)
        if doc == {}:
            plan.ops.append(Op(rel, None, "only kit keys were left"))
        else:
            plan.ops.append(Op(rel, result.text.encode("utf-8"), "kit keys removed"))
    return plan


def _prune(doc: dict, pointers: List[str]) -> bool:
    """Drop objects left empty above removed kit keys (e.g. {"mcpServers": {}})."""
    changed = False
    for pointer in pointers:
        parts = json_keys.parse_pointer(pointer)[:-1]
        while parts:
            parent: object = doc
            for part in parts[:-1]:
                parent = parent.get(part) if isinstance(parent, dict) else None
            if not isinstance(parent, dict) or parent.get(parts[-1]) != {}:
                break
            del parent[parts[-1]]
            changed = True
            parts = parts[:-1]
    return changed


def stale_part(entry: dict, wanted_rels: set, wanted_keys: set) -> dict:
    """The part of an old manifest entry the new plan no longer covers (update)."""
    return {
        "files": [f for f in entry.get("files", []) if f["path"] not in wanted_rels],
        "blocks": [b for b in entry.get("blocks", []) if b["path"] not in wanted_rels],
        "json_keys": [
            k
            for k in entry.get("json_keys", [])
            if f"{k['path']}#{k['pointer']}" not in wanted_keys
        ],
    }


def remaining(entry: dict, plan: RemovalPlan) -> dict:
    """The manifest entry reduced to the items that were left in place."""
    kept = set(plan.kept)
    out = dict(entry)
    out["files"] = [f for f in entry.get("files", []) if f["path"] in kept]
    out["blocks"] = [b for b in entry.get("blocks", []) if b["path"] in kept]
    out["json_keys"] = [
        k for k in entry.get("json_keys", []) if f"{k['path']}#{k['pointer']}" in kept
    ]
    return out


def format_ops(ops: List[Op]) -> List[str]:
    return [
        f"  {'REMOVE' if op.data is None else 'UPDATE':<9} {op.rel}  ({op.detail})" for op in ops
    ]
