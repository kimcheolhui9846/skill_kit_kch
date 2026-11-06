"""Apply planned changes: atomic writes, backups before replacing, state saved even on failure."""

from __future__ import annotations

import os
from pathlib import Path

from .fsops import State, backup_file, safe_path
from .model import Outcome
from .plan import FileChange

WRITES = (Outcome.CREATE, Outcome.UPDATE, Outcome.APPEND)


def apply_changes(
    target: Path, changes: list[FileChange], state: State, stamp: str, profile_name: str
) -> list[Path]:
    backups = []
    try:
        for change in changes:
            if change.outcome in (Outcome.UPDATE, Outcome.APPEND):
                backups.append(backup_file(target, change.rel, stamp))
            if change.outcome in WRITES and change.data is not None:
                _write_atomic(safe_path(target, change.rel), change.data)
            if change.record is not None:
                state.files[change.rel] = change.record
            if change.extra_records:
                state.files.update(change.extra_records)
    finally:
        state.save(target, profile_name)
    return backups


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".kit-tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
