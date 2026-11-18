#!/usr/bin/env python3
"""Preview or install the shared user workflow for Codex and Claude Code."""

from __future__ import annotations

import argparse
import codecs
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "user" / "workflow"
BEGIN = "<!-- BEGIN SKILL-KIT-KCH WORKFLOW -->"
END = "<!-- END SKILL-KIT-KCH WORKFLOW -->"
CODEX_MARKER = "# Managed by skill-kit-kch agent workflow installer"
CLAUDE_MARKER = "<!-- Managed by skill-kit-kch agent workflow installer -->"
NEWLINE = re.compile(r"\r\n|\n|\r")


@dataclass(frozen=True)
class FileState:
    content: bytes
    mode: int


@dataclass(frozen=True)
class Target:
    path: Path
    original: FileState | None
    content: bytes

    @property
    def action(self) -> str:
        if self.original is None:
            return "CREATE"
        return "UNCHANGED" if self.original.content == self.content else "UPDATE"


def read_file(path: Path) -> FileState | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        raise ValueError(f"{path}: expected a regular file")
    return FileState(path.read_bytes(), stat.S_IMODE(mode))


def decode(content: bytes, path: Path) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: expected UTF-8 text") from exc


def asset(name: str) -> str:
    path = ASSETS / name
    return NEWLINE.sub("\n", decode(path.read_bytes(), path)).strip()


def line_ending(text: str) -> str:
    match = NEWLINE.search(text)
    return match.group() if match else "\n"


def encode(text: str, original: bytes) -> bytes:
    content = text.encode("utf-8")
    return codecs.BOM_UTF8 + content if original.startswith(codecs.BOM_UTF8) else content


def replace_instructions(path: Path, original: FileState | None, body: str) -> Target:
    raw = original.content if original else b""
    text = decode(raw, path)
    newline = line_ending(text)
    block = newline.join((BEGIN, body.replace("\n", newline), END))
    if BEGIN in text or END in text:
        # Require exactly one pair on their own lines before replacing it.
        normalized = NEWLINE.sub("\n", text)
        markers = normalized.split("\n")
        if any(text.count(marker) != 1 or marker not in markers for marker in (BEGIN, END)):
            raise ValueError(f"{path}: malformed workflow markers")
        start, end = text.index(BEGIN), text.index(END)
        if end < start:
            raise ValueError(f"{path}: workflow markers are out of order")
        stop = end + len(END)
        terminator = NEWLINE.match(text, stop)
        if start == 0:
            return Target(path, original, encode(block + text[stop:], raw))
        # Promote a previously placed block while preserving surrounding text.
        text = text[:start] + text[terminator.end() if terminator else stop:]
    merged = block + newline + (newline + text if text else "")
    return Target(path, original, encode(merged, raw))


def replace_agent(path: Path, marker: str) -> Target:
    body = asset(path.name)
    if body.split("\n").count(marker) != 1:
        raise ValueError(f"{ASSETS / path.name}: missing or duplicate ownership marker")
    original = read_file(path)
    raw = original.content if original else b""
    current = decode(raw, path)
    if original and NEWLINE.sub("\n", current).split("\n").count(marker) != 1:
        raise ValueError(f"{path}: existing agent has no unique installer ownership marker")
    newline = line_ending(current)
    final_newline = newline if not original or NEWLINE.split(current)[-1] == "" else ""
    return Target(path, original, encode(body.replace("\n", newline) + final_newline, raw))


def config_dir(variable: str, default: str) -> Path:
    configured = os.environ.get(variable)
    return (Path(configured).expanduser() if configured else Path.home() / default).resolve()


def plan() -> tuple[list[Target], tuple[Path, FileState | None]]:
    codex_dir = config_dir("CODEX_HOME", ".codex")
    claude_dir = config_dir("CLAUDE_CONFIG_DIR", ".claude")
    override_path = codex_dir / "AGENTS.override.md"
    override = read_file(override_path)
    if override and decode(override.content, override_path).strip():
        codex_path, original = override_path, override
    else:
        codex_path = codex_dir / "AGENTS.md"
        original = read_file(codex_path)
    claude_path = claude_dir / "CLAUDE.md"
    body = asset("WORKFLOW.md")
    if not body or BEGIN in body or END in body:
        raise ValueError(f"{ASSETS / 'WORKFLOW.md'}: expected a workflow body without markers")

    for directory in (codex_dir, claude_dir, codex_dir / "agents", claude_dir / "agents"):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError(f"{directory}: expected a real directory")

    targets = [
        replace_instructions(codex_path, original, body),
        replace_instructions(claude_path, read_file(claude_path), body),
        replace_agent(codex_dir / "agents" / "harness-sol-worker.toml", CODEX_MARKER),
        replace_agent(claude_dir / "agents" / "harness-opus-review.md", CLAUDE_MARKER),
        replace_agent(claude_dir / "agents" / "harness-sonnet-worker.md", CLAUDE_MARKER),
    ]
    paths = {target.path for target in targets} | {override_path, codex_dir / "AGENTS.md"}
    for target in targets:
        if paths.intersection(target.path.parents):
            raise ValueError(f"{target.path}: client directories overlap a managed file")
    return targets, (override_path, override)


def write_temp(directory: Path, prefix: str, content: bytes, mode: int | None = None) -> Path:
    fd, name = tempfile.mkstemp(dir=directory, prefix=prefix)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            path.chmod(mode)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def check_original(path: Path, original: FileState | None) -> None:
    if read_file(path) != original:
        raise ValueError(f"{path}: changed after preview; run the installer again")


def apply(targets: list[Target], override: tuple[Path, FileState | None]) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    staged = []
    try:
        for target in targets:
            if target.action == "UNCHANGED":
                continue
            target.path.parent.mkdir(parents=True, exist_ok=True)
            mode = target.original.mode if target.original and os.name != "nt" else None
            stage = write_temp(target.path.parent, ".workflow-stage-", target.content, mode)
            staged.append((target, stage))

        check_original(*override)
        for target, _ in staged:
            check_original(target.path, target.original)
            if target.original:
                backup = write_temp(
                    target.path.parent, f"{target.path.name}.backup-{stamp}-",
                    target.original.content,
                )
                print(f"BACKUP    {backup}")

        check_original(*override)
        for target, stage in staged:
            check_original(target.path, target.original)
            os.replace(stage, target.path)
    finally:
        for _, stage in staged:
            stage.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the changes shown in preview")
    args = parser.parse_args()
    try:
        targets, override = plan()
        for target in targets:
            print(f"{target.action:9} {target.path}")
        if args.apply:
            apply(targets, override)
        else:
            print("Preview only. Run with --apply to install.")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Workflow installer: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
