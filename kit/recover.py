"""Session recovery (P5-T7, 00_PROMPT 10.7, REQ-SESS-001~003).

Files, all under .kit/work/ (D-06); the kit writes nothing at the workspace root, so a
HANDOFF.md there is the user's and is never read or changed (TC-HTL-18):

- HANDOFF.md      approved state only, rebuilt from tasks.json when the newest approval is
                  not in it yet: by `kit task approve` at once, after a hook approval by the
                  next `kit task` or `kit recover`. Its first line is the kit's marker; a file
                  without it is left alone.
- decisions.md    decision log, append only (`kit recover decide`).
- wip.json        temporary state (`kit recover save`), overwritten atomically and marked
                  UNAPPROVED. A broken one is ignored: recover falls back to the approved state.
- snapshots/<Task>.json  taken at submit: git HEAD if any and a hash of every workspace file,
                  so "changed since the last approval" is the same with or without git and
                  with or without uncommitted work (reviewer decision 2026-11-07).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import tasks
from .fsops import safe_path, sha256
from .logs import mask

WORK_REL = ".kit/work"
HANDOFF_REL = ".kit/work/HANDOFF.md"
DECISIONS_REL = ".kit/work/decisions.md"
WIP_REL = ".kit/work/wip.json"
SNAPSHOTS_REL = ".kit/work/snapshots"
ROOT_HANDOFF = "HANDOFF.md"
MARKER = "<!-- kit:handoff"
SCHEMA = 1
FIELD_MAX = 2000
ERRORS_MAX = 20
DECISION_MAX = 500
MAX_FILES = 20000
BIG_FILE = 32 * 1024 * 1024
SKIP_DIRS = {
    ".git",
    ".kit",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
}
WIP_FIELDS = ("task", "subtask", "note", "last_command", "last_tests")


class WipError(Exception):
    """wip.json cannot be read; recover ignores it and says so."""


def _write(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, p)


def _clean(text: str, limit: int = FIELD_MAX) -> str:
    return mask(" ".join(text.split()))[:limit]


# ---------------------------------------------------------------- snapshots


def _git(target: Path, *args: str) -> Optional[bytes]:
    exe = shutil.which("git")
    if not exe:
        return None
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    try:
        r = subprocess.run(
            [exe, "-C", str(target), *args], capture_output=True, timeout=60, env=env
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _walk(target: Path) -> List[str]:
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        base = Path(root)
        out += [(base / f).relative_to(target).as_posix() for f in sorted(files)]
    return out


def listing(target: Path, method: str) -> Tuple[List[str], str]:
    """Workspace files (never .kit/), with git (.gitignore respected) or by walking."""
    if method == "git":
        raw = _git(target, "ls-files", "-z", "-c", "-o", "--exclude-standard")
        if raw is not None:
            names = sorted({n for n in raw.decode("utf-8", "replace").split("\0") if n})
            return [n for n in names if not n.startswith(".kit/")], "git"
    return _walk(target), "files"


def _digest(p: Path) -> str:
    size = p.stat().st_size
    return f"size:{size}" if size > BIG_FILE else sha256(p.read_bytes())


def hashes(target: Path, method: str) -> Tuple[Dict[str, str], str, bool]:
    names, used = listing(target, method)
    files: Dict[str, str] = {}
    for rel in names[:MAX_FILES]:
        p = target / rel
        try:
            if p.is_file():
                files[rel] = _digest(p)
        except OSError:
            files[rel] = "unreadable"
    return files, used, len(names) > MAX_FILES


def snapshot_path(target: Path, task_id: str) -> Path:
    return safe_path(target, f"{SNAPSHOTS_REL}/{task_id}.json")


def take_snapshot(target: Path, task: dict) -> dict:
    """Called at submit: the state the reviewer is asked to approve."""
    head = _git(target, "rev-parse", "HEAD")
    commit = head.decode("ascii", "replace").strip() if head else None
    files, used, truncated = hashes(target, "git" if commit else "files")
    snap = {
        "schema": SCHEMA,
        "task": task["id"],
        "at": tasks.now(),
        "commit": commit,
        "method": used,
        "truncated": truncated,
        "files": files,
    }
    _write(snapshot_path(target, task["id"]), json.dumps(snap, indent=1).encode("utf-8"))
    return snap


def load_snapshot(target: Path, task_id: str) -> Optional[dict]:
    p = snapshot_path(target, task_id)
    try:
        snap = json.loads(p.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(snap, dict) or not isinstance(snap.get("files"), dict):
        return None
    return snap


def changes(target: Path, snap: dict) -> Tuple[List[Tuple[str, str]], bool]:
    """[(A|M|D, path)] between the snapshot and now, and whether the listing was cut short."""
    now, _, truncated = hashes(target, snap.get("method", "files"))
    before = snap["files"]
    out = [("A", r) for r in now if r not in before]
    out += [("M", r) for r in now if r in before and now[r] != before[r]]
    out += [("D", r) for r in before if r not in now]
    return sorted(out, key=lambda c: c[1]), truncated or bool(snap.get("truncated"))


# ---------------------------------------------------------------- reports


def _body(text: str, number: int, limit: int = 15) -> List[str]:
    lines = tasks._section(text, number).splitlines()[1:]
    keep = [mask(line.rstrip())[:300] for line in lines if line.strip()]
    if len(keep) > limit:
        keep = keep[:limit] + [f"... ({len(keep) - limit} more line(s) in the report)"]
    return keep


def test_counts(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in tasks.test_rows(text):
        status = row["status"].strip().upper()
        if not status or status in ("…", "..."):
            continue
        key = "NOT RUN" if status.startswith("NOT RUN") else status.split()[0].strip(":")
        counts[key] = counts.get(key, 0) + 1
    return counts


def approved_report(target: Path, task: dict) -> Optional[str]:
    """The report text only while it still has the hash it was approved with."""
    approval = task.get("approval") or {}
    if not task.get("report") or tasks.current_sha(target, task) != approval.get("report_sha256"):
        return None
    return tasks.report_path(target, task["report"]).read_bytes().decode("utf-8", "replace")


# ---------------------------------------------------------------- decisions and WIP


def decide(target: Path, text: str, task_id: Optional[str]) -> str:
    text = _clean(text, DECISION_MAX)
    if not text:
        raise ValueError("a decision needs text")
    p = safe_path(target, DECISIONS_REL)
    p.parent.mkdir(parents=True, exist_ok=True)
    head = b"" if p.is_file() else "# Decisions (append only, kit recover decide)\n\n".encode()
    line = f"- {tasks.now()} [{task_id or '-'}] {text}\n"
    with p.open("ab") as fh:
        fh.write(head + line.encode("utf-8"))
    return line.strip()


def recent_decisions(target: Path, n: int = 5) -> List[str]:
    p = safe_path(target, DECISIONS_REL)
    if not p.is_file():
        return []
    lines = p.read_bytes().decode("utf-8", "replace").splitlines()
    return [mask(x)[:300] for x in lines if x.startswith("- ")][-n:]


def save_wip(target: Path, fields: Dict[str, Optional[str]], errors: List[str]) -> dict:
    wip: dict = {"schema": SCHEMA, "status": "UNAPPROVED", "saved_at": tasks.now()}
    for key in WIP_FIELDS:
        value = fields.get(key)
        wip[key] = _clean(value) if value else None
    wip["errors"] = [_clean(e) for e in errors if e.strip()][:ERRORS_MAX]
    _write(
        safe_path(target, WIP_REL), (json.dumps(wip, indent=2, ensure_ascii=False) + "\n").encode()
    )
    return wip


def load_wip(target: Path) -> Optional[dict]:
    p = safe_path(target, WIP_REL)
    if not p.is_file():
        return None
    try:
        wip = json.loads(p.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise WipError(f"{WIP_REL} is not valid JSON ({exc})") from None
    if (
        not isinstance(wip, dict)
        or wip.get("schema") != SCHEMA
        or wip.get("status") != "UNAPPROVED"
        or not isinstance(wip.get("errors", []), list)
        or not all(isinstance(wip.get(k), (str, type(None))) for k in WIP_FIELDS)
    ):
        raise WipError(f"{WIP_REL} does not have the expected shape")
    return wip


# ---------------------------------------------------------------- HANDOFF.md


def marker(data: dict) -> str:
    last = data["approvals"][-1]
    return f"{MARKER} approvals={len(data['approvals'])} last={last['task']}@{last['at']} -->"


def _first_line(p: Path) -> str:
    with p.open("rb") as fh:
        return fh.readline().decode("utf-8", "replace").strip()


def handoff_text(target: Path, data: dict) -> str:
    rec = data["approvals"][-1]
    task = tasks.get(data, rec["task"])
    snap = load_snapshot(target, task["id"])
    commit = (snap or {}).get("commit")
    text = approved_report(target, task)
    report = task.get("report") or "-"
    out = [
        marker(data),
        "# HANDOFF (승인된 상태만 기록)",
        "",
        "`kit`이 `.kit/work/tasks.json`의 승인 기록으로 만듭니다. 손으로 고치지 마세요. "
        "임시(미승인) 상태는 여기에 없습니다(`kit recover`, `.kit/work/wip.json`).",
        "",
        "## 마지막 승인 Task",
        f"- ID / 제목: {task['id']} / {mask(task['title'])}",
        f"- 승인 시각: {rec['at']}",
        f"- 승인 기록 방식: {rec['by']}",
        f"- 승인 시 커밋: {commit or '없음 (git 없음 또는 커밋 없음)'} (submit 때 기록)",
        f"- 보고서: `{report}` (sha256 {str(rec.get('report_sha256'))[:12]})",
    ]
    if text is None:
        gone = ["- (보고서가 승인 뒤 바뀌었거나 없어 내용을 옮기지 않았습니다: kit task status)"]
        sections = {n: gone for n in (1, 2, 7, 9)}
        tests = "알 수 없음"
    else:
        sections = {n: _body(text, n) or ["- (비어 있음)"] for n in (1, 2, 7, 9)}
        counts = test_counts(text)
        tests = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "표에 행 없음"
    out += ["", "## 요약", *sections[1], "", "## 변경 파일", *sections[2]]
    out += ["", "## 테스트 결과 요약 (보고서 링크)", f"- {tests} (`{report}` 4절)"]
    out += ["", "## 결정 사항 (decisions.md 링크)", f"- `{DECISIONS_REL}` 최근 항목:"]
    out += [f"  {d}" for d in recent_decisions(target)] or ["  (없음)"]
    out += ["", "## 남은 위험·미해결 이슈", *sections[7], "", "## 다음 계획", *sections[9]]
    out += ["", "## 승인 이력", "| Task | 제목 | 승인 시각 | 방식 |", "|---|---|---|---|"]
    for a in data["approvals"]:
        title = mask(tasks.get(data, a["task"])["title"]).replace("|", "/")
        out.append(f"| {a['task']} | {title} | {a['at']} | {a['by']} |")
    return "\n".join(out) + "\n"


def refresh_handoff(target: Path, data: dict) -> str:
    """'none' (no approval yet), 'current', 'updated' or 'not-ours' (left alone)."""
    if not data["approvals"]:
        return "none"
    p = safe_path(target, HANDOFF_REL)
    if p.exists():
        first = _first_line(p) if p.is_file() else ""
        if not first.startswith(MARKER):
            return "not-ours"
        if first == marker(data):
            return "current"
    _write(p, handoff_text(target, data).encode("utf-8"))
    return "updated"


# ---------------------------------------------------------------- recover


def current_task(data: dict) -> Optional[dict]:
    """The task being worked on: IN_PROGRESS first, then SUBMITTED, then CHANGES_REQUESTED."""
    for state in ("IN_PROGRESS", "SUBMITTED", "CHANGES_REQUESTED"):
        for t in data["tasks"]:
            if t["state"] == state:
                return t
    return None


def recover(target: Path, data: dict) -> dict:
    """Everything `kit recover` shows; approved and temporary parts are kept apart."""
    warns = list(tasks.warnings(target, data))
    handoff = refresh_handoff(target, data)
    if handoff == "not-ours":
        warns.append(f"{HANDOFF_REL} was not written by the kit; left as is")
    cur = current_task(data)
    approved: dict = {
        "current": None,
        "last_approved": None,
        "approved": [a["task"] for a in data["approvals"]],
        "changed": None,
        "tests": None,
        "risks": [],
        "next": [],
        "can_start": tasks.next_startable(data),
        "decisions": recent_decisions(target),
        "handoff": handoff,
    }
    if cur:
        subs = cur.get("subtasks", [])
        approved["current"] = {
            "id": cur["id"],
            "title": cur["title"],
            "state": cur["state"],
            "subtasks_done": sum(1 for s in subs if s["state"] == "DONE"),
            "subtasks": len(subs),
        }
    if data["approvals"]:
        rec = data["approvals"][-1]
        task = tasks.get(data, rec["task"])
        approved["last_approved"] = {
            "id": task["id"],
            "title": task["title"],
            "at": rec["at"],
            "by": rec["by"],
        }
        snap = load_snapshot(target, task["id"])
        if snap is None:
            warns.append(f"no snapshot for {task['id']}; changed files are unknown")
        else:
            found, cut = changes(target, snap)
            approved["changed"] = {
                "since": f"{task['id']} submit",
                "commit": snap.get("commit"),
                "method": snap.get("method"),
                "files": [{"change": c, "path": mask(r)} for c, r in found],
                "truncated": cut,
            }
            if cut:
                warns.append(f"more than {MAX_FILES} files; the changed-file list is partial")
        text = approved_report(target, task)
        if text is not None:
            approved["tests"] = test_counts(text)
            approved["risks"] = [r for r in _body(text, 7) if not r.startswith(("| 항목", "|---"))]
            approved["next"] = _body(text, 9, limit=5)
    wip = None
    try:
        wip = load_wip(target)
    except WipError as exc:
        warns.append(f"{exc}; ignored, showing the approved state only")
    if wip is not None:
        wip = {k: (mask(v) if isinstance(v, str) else v) for k, v in wip.items()}
        wip["errors"] = [mask(str(e)) for e in wip.get("errors", [])]
        owner = next((t for t in data["tasks"] if t["id"] == wip.get("task")), None)
        if owner is not None and owner["state"] == "APPROVED":
            wip["stale"] = f"{owner['id']} is APPROVED now; this may predate the approval"
    root = target / ROOT_HANDOFF
    return {
        "approved": approved,
        "wip": wip,
        "root_handoff": ROOT_HANDOFF if root.exists() else None,
        "warnings": warns,
    }
