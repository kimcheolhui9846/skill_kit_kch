"""Kit-owned keys inside a JSON file (ADR-005). JSON has no comments, so no marker blocks.

Ownership is recorded per JSON pointer (RFC 6901) as the SHA-256 of the value's canonical
form. The kit only adds, changes or removes a key when:
- the key is missing (add), or
- the current value already equals the kit value (unchanged), or
- the current value still has the hash the kit recorded last time (update / remove).
Anything else is a CONFLICT and nothing is written. Arrays can be owned per element:
the kit adds its elements and later removes only elements whose hash it recorded.

Formatting: key order is kept (dicts keep insertion order), the indent (spaces or tab) and
newline style (LF/CRLF) are taken from the existing file, a final newline is kept or added.
Whitespace inside lines is normalised by json.dumps (documented limitation, ADR-005).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..model import Outcome

Indent = Union[int, str]
_MISSING = object()


class JsonKeyError(ValueError):
    """The file or a pointer cannot be handled safely."""


def value_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_pointer(pointer: str) -> List[str]:
    if pointer == "" or not pointer.startswith("/"):
        raise JsonKeyError(f"JSON pointer must start with '/': {pointer!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def detect_format(text: str) -> Tuple[Indent, str]:
    """(indent, newline) used by an existing JSON file. Defaults: 2 spaces, LF."""
    newline = "\r\n" if "\r\n" in text else "\n"
    match = re.search(r"^[{\[][ \t]*\r?\n([ \t]+)\S", text)
    if not match:
        return 2, newline
    ws = match.group(1)
    return ("\t" if ws.startswith("\t") else len(ws)), newline


def dump(doc: Any, indent: Indent = 2, newline: str = "\n") -> str:
    text = json.dumps(doc, indent=indent, ensure_ascii=False)
    return text.replace("\n", newline) + newline


def _get(doc: Any, parts: List[str]) -> Any:
    node = doc
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _parent(doc: dict, parts: List[str], create: bool) -> Optional[dict]:
    node = doc
    for part in parts[:-1]:
        nxt = node.get(part, _MISSING)
        if nxt is _MISSING:
            if not create:
                return None
            nxt = node[part] = {}
        if not isinstance(nxt, dict):
            raise JsonKeyError(f"'{part}' is not an object")
        node = nxt
    return node


@dataclass
class JsonPlan:
    """Result of planning one JSON file. text is None when nothing must be written."""

    text: Optional[str]
    outcome: str
    detail: str = ""
    records: Dict[str, str] = field(default_factory=dict)  # pointer -> value hash
    element_records: Dict[str, List[str]] = field(default_factory=dict)  # pointer -> hashes
    conflicts: List[str] = field(default_factory=list)  # pointers left alone (plan_remove)


def _load(existing: Optional[str]) -> Tuple[Optional[dict], Indent, str, Optional[str]]:
    """(doc, indent, newline, error). Empty or missing file -> new empty object."""
    if existing is None or not existing.strip():
        return {}, 2, "\n", None
    try:
        doc = json.loads(existing)
    except ValueError as exc:
        return None, 2, "\n", f"existing file is not valid JSON: {exc}"
    if not isinstance(doc, dict):
        return None, 2, "\n", "existing JSON top level is not an object"
    indent, newline = detect_format(existing)
    return doc, indent, newline, None


def plan_merge(
    existing: Optional[str],
    keys: Optional[Dict[str, Any]] = None,
    recorded: Optional[Dict[str, str]] = None,
    elements: Optional[Dict[str, List[Any]]] = None,
    recorded_elements: Optional[Dict[str, List[str]]] = None,
) -> JsonPlan:
    """Plan setting kit-owned keys and array elements. Never raises for user content."""
    keys = keys or {}
    recorded = recorded or {}
    elements = elements or {}
    recorded_elements = recorded_elements or {}
    doc, indent, newline, error = _load(existing)
    if doc is None:
        return JsonPlan(None, Outcome.CONFLICT, error or "")
    created = existing is None or not existing.strip()
    changed = False
    records: Dict[str, str] = {}
    element_records: Dict[str, List[str]] = {}
    try:
        for pointer, value in keys.items():
            parts = parse_pointer(pointer)
            current = _get(doc, parts)
            records[pointer] = value_hash(value)
            if current is not _MISSING and current == value:
                continue
            if current is not _MISSING and value_hash(current) != recorded.get(pointer):
                return JsonPlan(None, Outcome.CONFLICT, f"{pointer} is not owned by the kit")
            parent = _parent(doc, parts, create=True)
            parent[parts[-1]] = value
            changed = True
        for pointer, wanted in elements.items():
            parts = parse_pointer(pointer)
            current = _get(doc, parts)
            if current is _MISSING:
                _parent(doc, parts, create=True)[parts[-1]] = current = []
                changed = True
            if not isinstance(current, list):
                return JsonPlan(None, Outcome.CONFLICT, f"{pointer} is not an array")
            mine = set(recorded_elements.get(pointer, []))
            have = {value_hash(item) for item in current}
            # drop stale kit elements that the kit no longer wants
            wanted_hashes = [value_hash(item) for item in wanted]
            keep = [
                item
                for item in current
                if not (value_hash(item) in mine and value_hash(item) not in wanted_hashes)
            ]
            if len(keep) != len(current):
                current[:] = keep
                changed = True
            for item, digest in zip(wanted, wanted_hashes):
                if digest not in have:
                    current.append(item)
                    changed = True
            # own only elements the kit added or already owned, never a user's identical one
            element_records[pointer] = [d for d in wanted_hashes if d in mine or d not in have]
    except JsonKeyError as exc:
        return JsonPlan(None, Outcome.CONFLICT, str(exc))
    if not changed:
        return JsonPlan(None, Outcome.UNCHANGED, "", records, element_records)
    outcome = Outcome.CREATE if created else Outcome.UPDATE
    return JsonPlan(dump(doc, indent, newline), outcome, "", records, element_records)


def plan_remove(
    existing: Optional[str],
    recorded: Dict[str, str],
    recorded_elements: Optional[Dict[str, List[str]]] = None,
) -> JsonPlan:
    """Plan removing kit-owned keys/elements. Keys the user changed are left and reported."""
    recorded_elements = recorded_elements or {}
    if existing is None:
        return JsonPlan(None, Outcome.UNCHANGED)
    doc, indent, newline, error = _load(existing)
    if doc is None:
        return JsonPlan(None, Outcome.CONFLICT, error or "")
    changed = False
    kept: List[str] = []
    try:
        for pointer, digest in recorded.items():
            parts = parse_pointer(pointer)
            current = _get(doc, parts)
            if current is _MISSING:
                continue
            if value_hash(current) != digest:
                kept.append(pointer)
                continue
            del _parent(doc, parts, create=False)[parts[-1]]
            changed = True
        for pointer, hashes in recorded_elements.items():
            current = _get(doc, parse_pointer(pointer))
            if not isinstance(current, list):
                continue
            mine = set(hashes)
            keep = [item for item in current if value_hash(item) not in mine]
            if len(keep) != len(current):
                current[:] = keep
                changed = True
    except JsonKeyError as exc:
        return JsonPlan(None, Outcome.CONFLICT, str(exc))
    detail = ("user-modified, left in place: " + ", ".join(kept)) if kept else ""
    if changed:
        return JsonPlan(dump(doc, indent, newline), Outcome.UPDATE, detail, conflicts=kept)
    return JsonPlan(None, Outcome.CONFLICT if kept else Outcome.UNCHANGED, detail, conflicts=kept)
