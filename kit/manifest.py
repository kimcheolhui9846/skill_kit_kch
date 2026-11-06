"""Install manifest for the new (subcommand) path: what the kit owns, per agent (ADR-006).

project: <target>/.kit/state/install-manifest.json
user:    ~/.kit-state/manifest.json           (same format, paths written as "~/...")

The legacy path keeps writing .kit/state.json (v1) and never reads this file. The new path
adopts a v1 workspace: an entry is owned only when its current content still has the hash v1
recorded (or a hash of content the kit ships); anything else is a conflict. The v1 file is
left in place. Format: 04_DESIGN section 3.1.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .fsops import STATE_REL, sha256
from .writers.markdown_block import MarkerError, extract_block

SCHEMA = 1
KIT_VERSION = "2.0.0.dev0"
PROJECT_REL = ".kit/state/install-manifest.json"
USER_REL = ".kit-state/manifest.json"
_ENTRY_LISTS = ("files", "blocks", "json_keys", "manual_steps", "backups")


class ManifestError(Exception):
    """The manifest exists but cannot be trusted. Callers must stop without writing."""


@dataclass
class Manifest:
    scope: str = "project"
    installs: List[dict] = field(default_factory=list)
    kit_version: str = KIT_VERSION
    extra: Dict[str, object] = field(default_factory=dict)  # unknown top-level fields, kept

    def install_for(self, agent: str) -> Optional[dict]:
        return next((i for i in self.installs if i.get("agent") == agent), None)

    def record(self, entry: dict) -> None:
        """Replace the entry of the same agent (one install per agent per scope)."""
        for key in _ENTRY_LISTS:
            entry.setdefault(key, [])
        self.installs = [i for i in self.installs if i.get("agent") != entry["agent"]]
        self.installs.append(entry)
        self.installs.sort(key=lambda i: str(i.get("agent")))

    def forget(self, agent: str) -> None:
        self.installs = [i for i in self.installs if i.get("agent") != agent]

    def to_json(self) -> str:
        data = dict(self.extra)
        data.update(
            {
                "schema": SCHEMA,
                "kit_version": self.kit_version,
                "scope": self.scope,
                "installs": self.installs,
            }
        )
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def manifest_path(root: Path, scope: str) -> Path:
    return root / (USER_REL if scope == "user" else PROJECT_REL)


def load(path: Path, scope: str = "project") -> Manifest:
    """Missing file -> empty manifest. Unreadable, invalid or newer schema -> ManifestError."""
    if not path.exists():
        return Manifest(scope=scope)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ManifestError(f"cannot read {path.name}: {exc}") from None
    if not isinstance(data, dict):
        raise ManifestError(f"{path.name}: top level is not an object")
    schema = data.get("schema")
    if not isinstance(schema, int) or schema < 1:
        raise ManifestError(f"{path.name}: missing or invalid schema")
    if schema > SCHEMA:
        raise ManifestError(f"{path.name}: schema {schema} is newer than this kit ({SCHEMA})")
    installs = data.get("installs", [])
    if not isinstance(installs, list) or not all(
        isinstance(i, dict) and isinstance(i.get("agent"), str) for i in installs
    ):
        raise ManifestError(f"{path.name}: 'installs' must be a list of objects with 'agent'")
    if data.get("scope", scope) != scope:
        raise ManifestError(f"{path.name}: scope is {data.get('scope')!r}, expected {scope!r}")
    known = {"schema", "kit_version", "scope", "installs"}
    extra = {k: v for k, v in data.items() if k not in known}
    return Manifest(scope, installs, str(data.get("kit_version", KIT_VERSION)), extra)


def save(path: Path, manifest: Manifest) -> None:
    """Atomic write (same pattern as kit.register)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".kit-tmp")
    try:
        tmp.write_bytes(manifest.to_json().encode("utf-8"))
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


@dataclass
class Adoption:
    entry: Optional[dict]  # None when the workspace has no v1 state
    conflicts: List[str] = field(default_factory=list)


def adopt_v1(
    target: Path,
    agent: str,
    blocks: Dict[str, Iterable[str]],
    known_file_hashes: Optional[Dict[str, Iterable[str]]] = None,
) -> Adoption:
    """Turn <target>/.kit/state.json (v1) into a manifest entry without touching any file.

    blocks: rel -> (begin, end) for files whose v1 record is the hash of the kit block body
    (AGENTS.md, .codex/config.toml). known_file_hashes: rel -> hashes of content the kit
    ships, accepted even when the v1 record is stale.
    """
    path = target / STATE_REL
    if not path.is_file():
        return Adoption(None)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, dict):
            raise TypeError
    except (OSError, ValueError, KeyError, TypeError):
        return Adoption(None, [f"{STATE_REL}: unreadable v1 state, nothing adopted"])
    known = {rel: set(h) for rel, h in (known_file_hashes or {}).items()}
    entry: dict = {"agent": agent, "profiles": [], "policy": "restricted", "adopted_from": "v1"}
    if isinstance(data.get("profile"), str):
        entry["profiles"] = [data["profile"]]
    for key in _ENTRY_LISTS:
        entry[key] = []
    conflicts: List[str] = []
    for rel, recorded in sorted(files.items()):
        file_path = target / rel
        if not file_path.is_file():
            continue  # gone: nothing to own
        try:
            raw = file_path.read_bytes()
        except OSError as exc:
            conflicts.append(f"{rel}: cannot read ({exc})")
            continue
        if rel in blocks:
            begin, end = blocks[rel]
            try:
                found = extract_block(raw.decode("utf-8"), begin, end)
            except (UnicodeDecodeError, MarkerError) as exc:
                conflicts.append(f"{rel}: {exc}")
                continue
            if found is not None and sha256(found[2].encode("utf-8")) == recorded:
                entry["blocks"].append({"path": rel, "marker": "hackathon-kit", "sha256": recorded})
            else:
                conflicts.append(f"{rel}: kit block missing or edited since v1 install")
            continue
        current = sha256(raw)
        if current == recorded or current in known.get(rel, set()):
            entry["files"].append({"path": rel, "sha256": current})
        else:
            conflicts.append(f"{rel}: differs from what the kit wrote")
    return Adoption(entry, conflicts)
