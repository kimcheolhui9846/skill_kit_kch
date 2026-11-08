"""Filesystem helpers: confined paths, hashing, kit state and backups."""

from __future__ import annotations

import hashlib
import json
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PurePath

STATE_REL = ".kit/state.json"
BACKUPS_REL = ".kit/backups"
LOGS_REL = ".kit/logs"
# user scope (ADR-018): the kit's own files in the home folder
USER_STATE_REL = ".kit-state/state.json"
USER_BACKUPS_REL = ".kit-backups"
USER_LOGS_REL = ".kit-state/logs"

_user_root: "Path | None" = None  # set only while a --scope user command runs


@contextmanager
def user_scope(home: Path):
    """Inside this block the kit keeps its state, backups and logs for `home` in the user
    places (~/.kit-state/, ~/.kit-backups/). Every other target keeps .kit/ (legacy too)."""
    global _user_root
    previous, _user_root = _user_root, home.resolve()
    try:
        yield
    finally:
        _user_root = previous


def _is_user(target: Path) -> bool:
    return _user_root is not None and target.resolve() == _user_root


def state_rel(target: Path) -> str:
    return USER_STATE_REL if _is_user(target) else STATE_REL


def backups_rel(target: Path) -> str:
    return USER_BACKUPS_REL if _is_user(target) else BACKUPS_REL


def logs_rel(target: Path) -> str:
    return USER_LOGS_REL if _is_user(target) else LOGS_REL


def own_files(target: Path) -> tuple:
    """Prefixes of the kit's own bookkeeping under target (never installed content)."""
    if _is_user(target):
        return (".kit-state/", USER_BACKUPS_REL + "/")
    return (".kit/",)


class PathEscapeError(Exception):
    """A path resolved outside the target workspace."""


def safe_path(root: Path, rel: str) -> Path:
    """Resolve rel under root, refusing anything (.., absolute, symlink) that escapes it."""
    root = root.resolve()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathEscapeError(f"refusing path outside target: {rel}")
    return candidate


def path_order(path) -> tuple:
    """Sort key giving the same file order on every system (P6-T4).

    Path objects compare case-insensitively on Windows and case-sensitively elsewhere, so
    sorted(paths) put `SKILL.md` after `examples/` on Windows and before it on Linux. This key
    is the Windows order (parts in lower case; the legacy baselines were recorded there), then
    the exact parts, so names that differ only in case keep a fixed order on Linux.
    """
    parts = PurePath(path).parts
    return (tuple(p.lower() for p in parts), parts)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class State:
    """Hashes of files the kit wrote, so re-runs can tell kit edits from user edits."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = dict(files or {})

    @classmethod
    def load(cls, target: Path) -> State:
        path = target / state_rel(target)
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        files = data.get("files", {}) if isinstance(data, dict) else {}
        return cls(files if isinstance(files, dict) else {})

    def save(self, target: Path, profile: str) -> None:
        path = safe_path(target, state_rel(target))
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "profile": profile, "files": dict(sorted(self.files.items()))}
        path.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def backup_file(target: Path, rel: str, stamp: str) -> Path:
    src = safe_path(target, rel)
    dst = safe_path(target, f"{backups_rel(target)}/{stamp}/{rel}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
