"""sources.lock.json: pinned external files and their offline check (P4-T4, REQ-SRC-002/003).

The lock records every external file the kit carries, at a pinned commit, with a sha256 per
file. `check` works without the network: it compares the files on disk with the lock, checks
that each license file exists, that every file under third_party/ belongs to a lock entry and
that THIRD_PARTY_NOTICES.md names every source (V-23, V-24). Standard library only.

Format: 04_DESIGN §3.7. `files` maps kit-relative paths to sha256; `content_sha256` is the
sha256 of the sorted "path\\0sha256\\n" lines, so one value identifies the whole entry.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from .profiles import ProfileError

LOCK_REL = "sources.lock.json"
NOTICES_REL = "THIRD_PARTY_NOTICES.md"
THIRD_PARTY = "third_party"
SCHEMA = 1
KINDS = ("skill", "skill-bundle", "mcp", "plugin", "reference")
INTEGRATIONS = ("vendored-verbatim", "adapted", "referenced")
RISKS = ("low", "medium", "high")
SCOPES = ("project", "user")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ORIGIN = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REQUIRED = (
    "id",
    "kind",
    "origin",
    "commit",
    "license",
    "integration",
    "agents",
    "scope",
    "risk",
    "files",
    "content_sha256",
)


class LockError(ProfileError):
    """sources.lock.json is missing or malformed (BLOCKED, like a broken catalog)."""


@dataclass
class Source:
    id: str
    kind: str
    origin: str
    commit: str
    license: str
    license_file: Optional[str]
    integration: str
    agents: List[str]
    scope: List[str]
    risk: str
    files: Dict[str, str]
    content_sha256: str
    raw: dict = field(default_factory=dict)


def digest(files: Dict[str, str]) -> str:
    lines = "".join(f"{path}\0{sha}\n" for path, sha in sorted(files.items()))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel_ok(rel: str) -> bool:
    p = PurePosixPath(rel)
    return bool(rel) and not p.is_absolute() and ".." not in p.parts and "\\" not in rel


def _list(where: str, key: str, value: object, allowed=None) -> List[str]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
        raise LockError(f"{where}: {key} must be a non-empty list of names")
    for item in value:
        if allowed is not None and item not in allowed:
            raise LockError(f"{where}: unknown {key} value '{item}'")
    return list(value)


def _parse(raw: object, agents: List[str]) -> Source:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise LockError(f"{LOCK_REL}: every source needs an id")
    where = f"{LOCK_REL} '{raw['id']}'"
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise LockError(f"{where}: missing {', '.join(missing)}")
    if not _ID.match(raw["id"]):
        raise LockError(f"{where}: id must use a-z, 0-9 and single hyphens")
    if raw["kind"] not in KINDS:
        raise LockError(f"{where}: kind must be one of {', '.join(KINDS)}")
    if raw["integration"] not in INTEGRATIONS:
        raise LockError(f"{where}: integration must be one of {', '.join(INTEGRATIONS)}")
    if raw["risk"] not in RISKS:
        raise LockError(f"{where}: risk must be one of {', '.join(RISKS)}")
    if not isinstance(raw["origin"], str) or not _ORIGIN.match(raw["origin"]):
        raise LockError(f"{where}: origin must be https://github.com/<owner>/<repo>")
    if not isinstance(raw["commit"], str) or not _SHA1.match(raw["commit"]):
        raise LockError(f"{where}: commit must be a full 40-character SHA (pinned)")
    if not isinstance(raw["license"], str) or not raw["license"]:
        raise LockError(f"{where}: license is required")
    files = raw["files"]
    if not isinstance(files, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in files.items()
    ):
        raise LockError(f"{where}: files must map paths to sha256")
    for rel, sha in files.items():
        if not _rel_ok(rel):
            raise LockError(f"{where}: bad path '{rel}'")
        if not _SHA256.match(sha):
            raise LockError(f"{where}: '{rel}' needs a sha256")
    referenced = raw["integration"] == "referenced"
    if referenced and files:
        raise LockError(f"{where}: a referenced source carries no files")
    if not referenced and not files:
        raise LockError(f"{where}: no files")
    license_file = raw.get("license_file")
    if not referenced:
        if not isinstance(license_file, str) or license_file not in files:
            raise LockError(f"{where}: license_file must be one of its files")
    if raw["content_sha256"] != digest(files):
        raise LockError(f"{where}: content_sha256 does not match files")
    return Source(
        id=raw["id"],
        kind=raw["kind"],
        origin=raw["origin"],
        commit=raw["commit"],
        license=raw["license"],
        license_file=license_file,
        integration=raw["integration"],
        agents=_list(where, "agents", raw["agents"], agents),
        scope=_list(where, "scope", raw["scope"], SCOPES),
        risk=raw["risk"],
        files=dict(files),
        content_sha256=raw["content_sha256"],
        raw=raw,
    )


def load(kit_root: Path) -> Dict[str, Source]:
    path = kit_root / LOCK_REL
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError:
        raise LockError(f"{LOCK_REL} is missing") from None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise LockError(f"{LOCK_REL} is not valid JSON: {exc}") from None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise LockError(f"{LOCK_REL}: expected an object with schema {SCHEMA}")
    if not isinstance(data.get("sources"), list):
        raise LockError(f"{LOCK_REL}: sources must be a list")
    from .adapters import registry  # late import (adapters import plan)

    agents = registry.names()
    found: Dict[str, Source] = {}
    for raw in data["sources"]:
        source = _parse(raw, agents)
        if source.id in found:
            raise LockError(f"{LOCK_REL} '{source.id}': listed twice")
        found[source.id] = source
    return found


def _file_problems(kit_root: Path, source: Source) -> List[str]:
    problems = []
    for rel, sha in sorted(source.files.items()):
        path = kit_root / rel
        if not path.is_file():
            problems.append(f"{source.id}: {rel} is missing")
        elif file_sha256(path) != sha:
            problems.append(f"{source.id}: {rel} differs from the lock (sha256)")
    return problems


def check_files(
    kit_root: Path, rels: List[str], lock: Optional[Dict[str, Source]] = None
) -> List[str]:
    """Problems for kit files that must come from the lock (used before installing a skill)."""
    lock = load(kit_root) if lock is None else lock
    owner = {rel: s for s in lock.values() for rel in s.files}
    problems = []
    for rel in rels:
        source = owner.get(rel)
        if source is None:
            problems.append(f"{rel} is not in {LOCK_REL}")
            continue
        path = kit_root / rel
        if not path.is_file():
            problems.append(f"{rel} is missing")
        elif file_sha256(path) != source.files[rel]:
            problems.append(f"{rel} differs from {LOCK_REL} ({source.id})")
    return problems


def check(kit_root: Path) -> List[str]:
    """Every problem found offline; [] means the lock and the files agree (V-23, V-24)."""
    lock = load(kit_root)
    problems: List[str] = []
    for source in lock.values():
        problems += _file_problems(kit_root, source)
    covered = {rel for s in lock.values() for rel in s.files}
    root = kit_root / THIRD_PARTY
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(kit_root).as_posix()
                if rel not in covered:
                    problems.append(f"{rel} is not in {LOCK_REL}")
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            prefix = folder.relative_to(kit_root).as_posix() + "/"
            licensed = any(
                s.license_file and s.license_file.startswith(prefix) for s in lock.values()
            )
            if not licensed:
                problems.append(f"{prefix} has no license_file in {LOCK_REL}")
    notices_path = kit_root / NOTICES_REL
    notices = notices_path.read_text(encoding="utf-8") if notices_path.is_file() else ""
    for source in lock.values():
        if source.integration != "referenced" and source.origin not in notices:
            problems.append(f"{NOTICES_REL} does not mention {source.origin} ({source.id})")
    return problems
