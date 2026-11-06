"""Apply several plans as one unit (05_CLI_SPEC §7): if any write fails, put every file this run
touched back the way it was, including .kit/state.json, so no half-installed state is left.

Backups under .kit/backups/<stamp>/ are still made by kit.register and are never deleted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .fsops import PathEscapeError, State, backup_file, backups_rel, safe_path, state_rel, timestamp
from .lifecycle import Op
from .plan import FileChange
from .register import WRITES, _write_atomic, apply_changes


class TransactionError(Exception):
    """A write failed; `restored` lists what was put back, `unrestored` what could not be."""

    def __init__(self, cause: Exception, restored: List[str], unrestored: List[str]):
        super().__init__(str(cause))
        self.cause = cause
        self.restored = restored
        self.unrestored = unrestored


def _snapshot(target: Path, rels: List[str]) -> Dict[str, Optional[bytes]]:
    saved: Dict[str, Optional[bytes]] = {}
    for rel in rels:
        if rel in saved:
            continue
        path = safe_path(target, rel)
        saved[rel] = path.read_bytes() if path.is_file() else None
    return saved


def _remove_empty_parents(target: Path, path: Path) -> None:
    root = target.resolve()
    parent = path.parent
    while parent != root and root in parent.parents:
        try:
            parent.rmdir()  # only succeeds when empty
        except OSError:
            return
        parent = parent.parent


def rollback(target: Path, saved: Dict[str, Optional[bytes]]) -> tuple[List[str], List[str]]:
    restored, unrestored = [], []
    for rel, data in saved.items():
        try:
            path = safe_path(target, rel)
            if data is None:
                if path.is_file():
                    path.unlink()
                    _remove_empty_parents(target, path)
            elif not path.is_file() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            restored.append(rel)
        except (OSError, PathEscapeError):
            unrestored.append(rel)
    return restored, unrestored


def fresh_stamp(target: Path) -> str:
    """A backup stamp whose folder does not exist yet (two runs in one second differ)."""
    stamp = base = timestamp()
    n = 1
    while (target / backups_rel(target) / stamp).exists():
        stamp = f"{base}-{n}"
        n += 1
    return stamp


def apply_all(
    target: Path,
    groups: List[List[FileChange]],
    state: State,
    stamp: str,
    label: str,
    ops: Optional[List[Op]] = None,
    forget: Optional[List[str]] = None,
) -> List[List[Path]]:
    """Apply groups in order (codex before claude), then ops (removals and rewrites).

    Any exception, not only OSError, rolls back every file this call touched and raises
    TransactionError. Returns the backups made per group; ops backups are the last group.
    """
    ops = ops or []
    rels = [c.rel for g in groups for c in g if c.outcome in WRITES and c.data is not None]
    saved = _snapshot(target, rels + [op.rel for op in ops] + [state_rel(target)])
    before = dict(state.files)
    backups: List[List[Path]] = []
    try:
        for changes in groups:
            backups.append(apply_changes(target, changes, state, stamp, label))
        made: List[Path] = []
        for op in ops:
            path = safe_path(target, op.rel)
            if path.is_file():
                made.append(backup_file(target, op.rel, stamp))
            if op.data is None:
                if path.is_file():
                    path.unlink()
                    _remove_empty_parents(target, path)
            else:
                _write_atomic(path, op.data)
        backups.append(made)
        if ops or forget:
            for key in forget or []:
                state.files.pop(key, None)
            state.save(target, label)
    except Exception as exc:  # noqa: BLE001 - every failure must roll back
        state.files = before
        restored, unrestored = rollback(target, saved)
        raise TransactionError(exc, restored, unrestored) from exc
    return backups
