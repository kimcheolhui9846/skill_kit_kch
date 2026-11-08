"""Task state machine and approvals (P5-T2, 00_PROMPT 10.2, ADR-011 L1, REQ-HITL-001~006).

State lives in the workspace at .kit/work/tasks.json (ADR-006):

    {"schema": 1,
     "tasks": [{"id", "title", "requirements", "depends_on", "grade", "state", "subtasks",
                "report", "submitted_sha256", "approval", "history"}],
     "approvals": [{"task", "at", "by", "evidence", "report_sha256"}]}

States: TODO -> IN_PROGRESS -> SUBMITTED -> APPROVED, and SUBMITTED -> CHANGES_REQUESTED ->
IN_PROGRESS. Subtasks are TODO or DONE and never need an approval (REQ-HITL-002).

Rules (a broken rule is a Refused, exit 2; a broken file is a TasksError, exit 65):
- start: every depends_on task is APPROVED and no other task is IN_PROGRESS.
- submit: IN_PROGRESS, every subtask DONE, the report exists inside the workspace, has the
  nine 00_PROMPT 5.6 sections, and its test table (section 4) has a row for every must
  requirement of the task. A NOT RUN row needs a reason in its Status cell. Until
  .kit/work/trace.json exists every requirement of the task counts as must (reviewer
  decision 2026-11-07); after that its "priority" decides.
- approve: only SUBMITTED, and only while the report still has the hash it had at submit.
  The record keeps the report hash; status warns when the report changes after approval.
- by: human-cli (a person retyped the task id at a terminal), agent-recorded (the agent
  quotes the user's words as evidence). human-hook is written only by the L2 hook
  (P5-T2b, kit.approval_hooks); while that hook is installed agent-recorded is refused.

Honesty: L1 is a state machine an agent can still bypass (for example by editing the JSON by
hand). It makes skipped approvals visible after the fact through the `by` field and the
report hashes; it is not an enforcement boundary.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import approval_hooks, counterexamples
from . import trace as trace_mod
from .fsops import PathEscapeError, safe_path, sha256

TASKS_REL = ".kit/work/tasks.json"
TRACE_REL = ".kit/work/trace.json"
REPORTS_REL = ".kit/work/reports"
TEMPLATE_REL = "shared/templates/task-report.md"
SCHEMA = 1
STATES = ("TODO", "IN_PROGRESS", "SUBMITTED", "CHANGES_REQUESTED", "APPROVED")
GRADES = ("L", "S", "C")
BY = ("human-cli", "human-hook", "agent-recorded")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
_REQ = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*-[A-Za-z0-9_.-]+$")
_SECTION = re.compile(r"^#{2,4}\s*(\d)\.\s", re.M)
EVIDENCE_MAX = 2000


class TasksError(Exception):
    """tasks.json is missing a required shape or cannot be read/written (exit 65)."""


class Refused(Exception):
    """A rule of the state machine said no (exit 2). The message says why."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------- load / save


def path(target: Path) -> Path:
    return safe_path(target, TASKS_REL)


def empty() -> dict:
    return {"schema": SCHEMA, "tasks": [], "approvals": []}


def load(target: Path) -> dict:
    p = path(target)
    if not p.is_file():
        return empty()
    try:
        data = json.loads(p.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise TasksError(f"{TASKS_REL} is not valid JSON: {exc}") from None
    validate(data)
    return data


def save(target: Path, data: dict) -> None:
    validate(data)
    p = path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, p)


def validate(data: object) -> None:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise TasksError(f"{TASKS_REL}: expected an object with schema {SCHEMA}")
    tasks, approvals = data.get("tasks"), data.get("approvals")
    if not isinstance(tasks, list) or not isinstance(approvals, list):
        raise TasksError(f"{TASKS_REL}: tasks and approvals must be lists")
    seen = set()
    for t in tasks:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str):
            raise TasksError(f"{TASKS_REL}: every task needs an id")
        if t["id"] in seen:
            raise TasksError(f"{TASKS_REL}: task {t['id']} is listed twice")
        seen.add(t["id"])
        if t.get("state") not in STATES:
            raise TasksError(f"{TASKS_REL}: task {t['id']} has an unknown state")
        for key in ("requirements", "depends_on", "subtasks", "history"):
            if not isinstance(t.get(key, []), list):
                raise TasksError(f"{TASKS_REL}: task {t['id']}: {key} must be a list")
    for t in tasks:
        missing = [d for d in t.get("depends_on", []) if d not in seen]
        if missing:
            raise TasksError(f"{TASKS_REL}: task {t['id']} depends on unknown {missing[0]}")
    cycle = find_cycle(tasks)
    if cycle:
        raise TasksError(f"{TASKS_REL}: dependency cycle {' -> '.join(cycle)}")
    for a in approvals:
        if not isinstance(a, dict) or a.get("by") not in BY or a.get("task") not in seen:
            raise TasksError(f"{TASKS_REL}: an approval record is malformed")


def find_cycle(tasks: List[dict]) -> Optional[List[str]]:
    graph = {t["id"]: list(t.get("depends_on", [])) for t in tasks}
    color: Dict[str, int] = {}
    stack: List[str] = []

    def visit(node: str) -> Optional[List[str]]:
        color[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if color.get(nxt) == 1:
                return stack[stack.index(nxt) :] + [nxt]
            if color.get(nxt) is None:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = 2
        return None

    for node in sorted(graph):
        if color.get(node) is None:
            found = visit(node)
            if found:
                return found
    return None


def get(data: dict, task_id: str) -> dict:
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    raise Refused(f"no task '{task_id}' (see kit task list)")


def _event(task: dict, event: str, detail: str = "") -> None:
    task.setdefault("history", []).append({"at": now(), "event": event, "detail": detail})


# ---------------------------------------------------------------- transitions


def add(
    data: dict, task_id: str, title: str, requirements: List[str], depends_on: List[str], grade: str
) -> dict:
    if not _ID.match(task_id):
        raise ValueError("task id: letters, digits, '.', '_' or '-' (up to 40), e.g. T-001")
    if not title.strip():
        raise ValueError("--title needs text")
    if grade not in GRADES:
        raise ValueError(f"--grade must be one of {', '.join(GRADES)}")
    bad = [r for r in requirements if not _REQ.match(r)]
    if bad:
        raise ValueError(f"requirement ids look like REQ-001; got '{bad[0]}'")
    if any(t["id"] == task_id for t in data["tasks"]):
        raise Refused(f"task '{task_id}' already exists")
    if task_id in depends_on:
        raise Refused(f"task '{task_id}' cannot depend on itself")
    unknown = [d for d in depends_on if not any(t["id"] == d for t in data["tasks"])]
    if unknown:
        raise Refused(f"depends on unknown task '{unknown[0]}'; add it first")
    task = {
        "id": task_id,
        "title": title.strip(),
        "requirements": list(dict.fromkeys(requirements)),
        "depends_on": list(dict.fromkeys(depends_on)),
        "grade": grade,
        "state": "TODO",
        "subtasks": [],
        "report": None,
        "submitted_sha256": None,
        "approval": None,
        "history": [],
    }
    _event(task, "added")
    data["tasks"].append(task)
    return task


def blockers(data: dict, task: dict) -> List[str]:
    """Why `start` would refuse: unapproved dependencies and a task already in progress."""
    out = []
    for dep in task.get("depends_on", []):
        state = get(data, dep)["state"]
        if state != "APPROVED":
            out.append(f"{dep} is {state}, not APPROVED")
    for t in data["tasks"]:
        if t["state"] == "IN_PROGRESS":
            out.append(f"{t['id']} is IN_PROGRESS (submit it first)")
    return out


def start(data: dict, task_id: str) -> dict:
    task = get(data, task_id)
    if task["state"] not in ("TODO", "CHANGES_REQUESTED"):
        raise Refused(f"{task_id} is {task['state']}; only TODO or CHANGES_REQUESTED can start")
    why = blockers(data, task)
    if why:
        raise Refused(f"cannot start {task_id}: " + "; ".join(why))
    _event(task, "started", task["state"])
    task["state"] = "IN_PROGRESS"
    return task


def subtask_add(data: dict, task_id: str, title: str) -> dict:
    task = get(data, task_id)
    if task["state"] != "IN_PROGRESS":
        raise Refused(f"{task_id} is {task['state']}; add subtasks while it is IN_PROGRESS")
    if not title.strip():
        raise ValueError("a subtask needs a title")
    sub = {"id": f"{task_id}.{len(task['subtasks']) + 1}", "title": title.strip(), "state": "TODO"}
    task["subtasks"].append(sub)
    return sub


def subtask_done(data: dict, sub_id: str) -> dict:
    """No approval: a subtask is the agent's own bookkeeping (REQ-HITL-002)."""
    for task in data["tasks"]:
        for sub in task["subtasks"]:
            if sub["id"] == sub_id:
                if task["state"] != "IN_PROGRESS":
                    raise Refused(f"{task['id']} is {task['state']}, not IN_PROGRESS")
                sub["state"] = "DONE"
                return sub
    raise Refused(f"no subtask '{sub_id}'")


# ---------------------------------------------------------------- reports


def default_report(task_id: str) -> str:
    return f"{REPORTS_REL}/{task_id}.md"


def report_path(target: Path, rel: str) -> Path:
    try:
        return safe_path(target, rel)
    except PathEscapeError:
        raise Refused(f"report '{rel}' is outside the workspace") from None


def write_template(target: Path, kit_root: Path, task: dict, force: bool) -> str:
    rel = task.get("report") or default_report(task["id"])
    p = report_path(target, rel)
    if p.exists() and not force:
        raise Refused(f"{rel} already exists (use --force to replace it)")
    text = (kit_root / TEMPLATE_REL).read_text(encoding="utf-8")
    text = text.replace("<TASK_ID>", task["id"]).replace("<TITLE>", task["title"])
    text = text.replace("<GRADE>", task["grade"])
    text = text.replace("<REQUIREMENTS>", ", ".join(task["requirements"]) or "—")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    task["report"] = rel
    return rel


def _section(text: str, number: int) -> str:
    marks = [(int(m.group(1)), m.start()) for m in _SECTION.finditer(text)]
    for i, (n, pos) in enumerate(marks):
        if n == number:
            end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
            return text[pos:end]
    return ""


def test_rows(text: str) -> List[Dict[str, str]]:
    """Rows of the section 4 table: Test ID | Requirement | Scenario | Input | Expected |
    Actual | Status. The header and separator rows are skipped."""
    rows = []
    for line in _section(text, 4).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or set("".join(cells)) <= set("-: ") or cells[0].lower() == "test id":
            continue
        rows.append(
            dict(zip(("test", "req", "scenario", "input", "expected", "actual", "status"), cells))
        )
    return rows


def must_requirements(target: Path, task: dict) -> List[str]:
    """All task requirements until trace.json exists; then those with priority must."""
    try:
        data = trace_mod.load(target)  # missing or empty file: nothing recorded yet
    except trace_mod.TraceError as exc:
        raise TasksError(f"{TRACE_REL} is not valid ({exc})") from None
    prio = {r["id"]: r["priority"] for r in data["requirements"]}
    return [r for r in task["requirements"] if prio.get(r, "must") == "must"]


_PLACEHOLDER = re.compile(r"^(?:|…|\.\.\.|-|<.*>)$")


def check_report(target: Path, task: dict, rel: str) -> Tuple[str, List[str]]:
    """(sha256, problems). Problems make submit refuse."""
    p = report_path(target, rel)
    if not p.is_file():
        return "", [f"report {rel} does not exist (kit task report {task['id']} makes one)"]
    data = p.read_bytes()
    text = data.decode("utf-8", "replace")
    problems = []
    found = {int(m.group(1)) for m in _SECTION.finditer(text)}
    missing = [str(n) for n in range(1, 10) if n not in found]
    if missing:
        problems.append(f"report is missing section(s) {', '.join(missing)} of 00_PROMPT 5.6")
    rows = [r for r in test_rows(text) if not _PLACEHOLDER.match(r["test"])]
    for req in must_requirements(target, task):
        mine = [r for r in rows if re.search(rf"(?<![\w-]){re.escape(req)}(?![\w-])", r["req"])]
        if not mine:
            problems.append(f"no test row for must requirement {req} in section 4")
        for r in mine:
            status = r["status"]
            if status.upper().startswith("NOT RUN") and not re.search(r"\w", status[7:]):
                problems.append(f"{r['test']} ({req}) is NOT RUN without a reason")
    return sha256(data), problems


def submit(target: Path, data: dict, task_id: str, report: Optional[str]) -> dict:
    task = get(data, task_id)
    if task["state"] != "IN_PROGRESS":
        raise Refused(f"{task_id} is {task['state']}; only IN_PROGRESS can be submitted")
    open_subs = [s["id"] for s in task["subtasks"] if s["state"] != "DONE"]
    if open_subs:
        raise Refused(f"subtask(s) not done: {', '.join(open_subs)}")
    rel = report or task.get("report") or default_report(task_id)
    digest, problems = check_report(target, task, rel)
    if task.get("grade") == "C":  # TC-HTL-15
        problems += counterexamples.submit_problems(target, task)
    if problems:
        raise Refused(f"cannot submit {task_id}: " + "; ".join(problems))
    task["report"] = rel
    task["submitted_sha256"] = digest
    task["state"] = "SUBMITTED"
    _event(task, "submitted", rel)
    return task


def current_sha(target: Path, task: dict) -> Optional[str]:
    if not task.get("report"):
        return None
    p = report_path(target, task["report"])
    return sha256(p.read_bytes()) if p.is_file() else None


def approve(target: Path, data: dict, task_id: str, by: str, evidence: str) -> dict:
    task = get(data, task_id)
    if task["state"] != "SUBMITTED":
        raise Refused(f"{task_id} is {task['state']}; only SUBMITTED can be approved")
    if by not in BY:
        raise ValueError(f"--by must be one of {', '.join(BY)}")
    hooked = approval_hooks.installed(target)
    if by == "agent-recorded" and hooked:
        raise Refused(
            f"the approval hook is on here ({', '.join(hooked)}); the user approves by replying "
            "only 'approve' (recorded by human-hook) or with kit task approve at "
            "a terminal"
        )
    digest = current_sha(target, task)
    if digest != task.get("submitted_sha256"):
        raise Refused(f"{task['report']} changed after submit; submit {task_id} again")
    record = {
        "task": task_id,
        "at": now(),
        "by": by,
        "evidence": evidence[:EVIDENCE_MAX],
        "report_sha256": digest,
    }
    data["approvals"].append(record)
    task["approval"] = record
    task["state"] = "APPROVED"
    _event(task, "approved", by)
    return record


def request_changes(data: dict, task_id: str, reason: str) -> dict:
    task = get(data, task_id)
    if task["state"] != "SUBMITTED":
        raise Refused(f"{task_id} is {task['state']}; only SUBMITTED can get change requests")
    if not reason.strip():
        raise ValueError("--reason needs text")
    task["state"] = "CHANGES_REQUESTED"
    _event(task, "changes requested", reason.strip())
    return task


def warnings(target: Path, data: dict) -> List[str]:
    """Approved reports that changed afterwards (00_PROMPT 10.2)."""
    out = []
    for t in data["tasks"]:
        approval = t.get("approval")
        if t["state"] == "APPROVED" and approval:
            digest = current_sha(target, t)
            if digest != approval.get("report_sha256"):
                what = "is missing" if digest is None else "changed"
                out.append(f"{t['id']}: report {t['report']} {what} after approval")
    return out


def next_startable(data: dict) -> List[str]:
    return [
        t["id"]
        for t in data["tasks"]
        if t["state"] in ("TODO", "CHANGES_REQUESTED") and not blockers(data, t)
    ]
