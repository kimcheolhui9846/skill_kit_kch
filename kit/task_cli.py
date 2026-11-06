"""`kit task ...` (P5-T2): the CLI over kit.tasks. Exit codes: 0 done, 1 status has warnings,
2 a rule refused (the reason is printed), 64 bad arguments, 65 tasks.json is broken.

approve: by default `human-cli`, which needs a person at a terminal who retypes the task id;
without a terminal it refuses (2). `--by agent-recorded --evidence "<the user's words>"` is
the agent's path and is shown as such everywhere. `human-hook` comes only from the L2 hook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, List, Optional, TextIO

from . import tasks
from .logs import mask
from .model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, TargetError, UsageError

Ask = Optional[Callable[[str], str]]
ACTIONS = (
    "add",
    "list",
    "start",
    "subtask",
    "report",
    "submit",
    "approve",
    "request-changes",
    "status",
)


def add_parser(sub) -> None:
    p = sub.add_parser("task", add_help=False)
    actions = p.add_subparsers(dest="action", parser_class=type(p))
    a = actions.add_parser("add", add_help=False)
    a.add_argument("id")
    a.add_argument("--title", required=True)
    a.add_argument("--requires", action="append", default=[], metavar="REQ")
    a.add_argument("--depends-on", action="append", default=[], metavar="TASK")
    a.add_argument("--grade", default="S")
    lst = actions.add_parser("list", add_help=False)
    s = actions.add_parser("start", add_help=False)
    s.add_argument("id")
    st = actions.add_parser("subtask", add_help=False)
    st.add_argument("verb", choices=("add", "done"))
    st.add_argument("id")
    st.add_argument("title", nargs="?", default="")
    r = actions.add_parser("report", add_help=False)
    r.add_argument("id")
    r.add_argument("--force", action="store_true")
    sm = actions.add_parser("submit", add_help=False)
    sm.add_argument("id")
    sm.add_argument("--report", metavar="FILE")
    ap = actions.add_parser("approve", add_help=False)
    ap.add_argument("id")
    ap.add_argument("--by", default="human-cli", choices=("human-cli", "agent-recorded"))
    ap.add_argument("--evidence", "--quote", dest="evidence", default="")
    rc = actions.add_parser("request-changes", add_help=False)
    rc.add_argument("id")
    rc.add_argument("--reason", required=True)
    stat = actions.add_parser("status", add_help=False)
    stat.add_argument("id", nargs="?")
    for q in (a, lst, s, st, r, sm, ap, rc, stat):
        q.add_argument("--target", metavar="DIR")
        q.add_argument("--json", action="store_true")


def _workspace(raw: Optional[str], cwd: Path) -> Path:
    target = Path(raw) if raw else cwd
    if not target.is_absolute():
        target = cwd / target
    target = target.resolve()
    if not target.is_dir():
        raise TargetError(f"target is not an existing directory: {target}")
    return target


def run(ns: argparse.Namespace, cwd: Path, kit_root: Path, out: TextIO, ask: Ask) -> int:
    if ns.action is None:
        raise UsageError(f"task needs an action: {', '.join(ACTIONS)}")
    target = _workspace(ns.target, cwd)
    try:
        data = tasks.load(target)
        if ns.action in ("list", "status"):
            return _status(target, data, ns, out)
        result = _change(target, kit_root, data, ns, ask)
    except tasks.TasksError as exc:
        raise TargetError(str(exc)) from None
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    except tasks.Refused as exc:
        return _emit(
            out,
            ns.json,
            {"action": ns.action, "status": "REFUSED", "reason": str(exc)},
            [f"Refused:      {exc}", "Status:       BLOCKED"],
            EXIT_BLOCKED,
        )
    tasks.save(target, data)
    lines, payload = result
    return _emit(
        out,
        ns.json,
        {"action": ns.action, "status": "DONE", **payload},
        lines + ["Status:       DONE"],
        EXIT_READY,
    )


def _change(target: Path, kit_root: Path, data: dict, ns, ask: Ask):
    a = ns.action
    if a == "add":
        t = tasks.add(data, ns.id, ns.title, ns.requires, ns.depends_on, ns.grade)
        return [f"Added:        {t['id']} {t['title']} (grade {t['grade']})"], {"task": t}
    if a == "start":
        t = tasks.start(data, ns.id)
        return [f"Started:      {t['id']} -> IN_PROGRESS"], {"task": t}
    if a == "subtask":
        if ns.verb == "add":
            s = tasks.subtask_add(data, ns.id, ns.title)
            return [f"Subtask:      {s['id']} {s['title']}"], {"subtask": s}
        s = tasks.subtask_done(data, ns.id)
        return [f"Subtask:      {s['id']} DONE (no approval needed)"], {"subtask": s}
    if a == "report":
        t = tasks.get(data, ns.id)
        rel = tasks.write_template(target, kit_root, t, ns.force)
        return [f"Report:       {rel} (00_PROMPT 5.6 template; fill it in, then submit)"], {
            "report": rel
        }
    if a == "submit":
        t = tasks.submit(target, data, ns.id, ns.report)
        return [
            f"Submitted:    {t['id']} with {t['report']}",
            "Next:         wait for the reviewer's approval",
        ], {"task": t}
    if a == "approve":
        evidence = _confirm(ns, ask)
        rec = tasks.approve(target, data, ns.id, ns.by, evidence)
        return [
            f"Approved:     {ns.id} by {rec['by']} (report sha256 {rec['report_sha256'][:12]})"
        ], {"approval": rec}
    t = tasks.request_changes(data, ns.id, ns.reason)
    return [f"Changes:      {t['id']} -> CHANGES_REQUESTED"], {"task": t}


def _confirm(ns, ask: Ask) -> str:
    if ns.by == "agent-recorded":
        if not ns.evidence.strip():
            raise ValueError("--by agent-recorded needs --evidence with the user's own words")
        return mask(ns.evidence.strip())
    if ns.evidence:
        raise ValueError("--evidence is for --by agent-recorded; a person approves by retyping")
    if ask is None:
        raise tasks.Refused(
            "human-cli approval needs a person at a terminal (retype the task id). An agent "
            'records the user\'s words with --by agent-recorded --evidence "..."'
        )
    typed = ask(f"Approve {ns.id}? Type the task id to confirm: ").strip()
    if typed != ns.id:
        raise tasks.Refused("the typed id does not match; nothing was approved")
    return "task id retyped at a terminal"


def _status(target: Path, data: dict, ns, out: TextIO) -> int:
    rows = data["tasks"]
    if ns.action == "status" and ns.id:
        rows = [tasks.get(data, ns.id)] if any(t["id"] == ns.id for t in rows) else []
        if not rows:
            raise UsageError(f"no task '{ns.id}'")
    warns = tasks.warnings(target, data)
    ready = tasks.next_startable(data)
    lines = []
    for t in rows:
        appr = t.get("approval")
        by = f" by {appr['by']}" if appr else ""
        subs = t.get("subtasks", [])
        done = sum(1 for s in subs if s["state"] == "DONE")
        lines.append(
            f"  {t['id']:<12} {t['state']:<18}{by:<20} {t['title']}"
            + (f"  [subtasks {done}/{len(subs)}]" if subs else "")
        )
        if ns.action == "status" and t["state"] in ("TODO", "CHANGES_REQUESTED"):
            lines += [f"      waits for: {w}" for w in tasks.blockers(data, t)]
    text = ["Tasks:"] + (lines or ["  (none)"])
    if ns.action == "status":
        text.append(f"Can start:    {', '.join(ready) or 'none'}")
        text += [f"Warning:      {w}" for w in warns]
    code = EXIT_PARTIAL if warns and ns.action == "status" else EXIT_READY
    status = "WARN" if code == EXIT_PARTIAL else "READY"
    payload = {
        "action": ns.action,
        "status": status,
        "tasks": rows,
        "can_start": ready,
        "warnings": warns,
        "approvals": data["approvals"],
    }
    return _emit(out, ns.json, payload, text + [f"Status:       {status}"], code)


def _emit(out: TextIO, as_json: bool, payload: dict, lines: List[str], code: int) -> int:
    if as_json:
        out.write(json.dumps({**payload, "exit_code": code}, indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(mask("\n".join(lines)) + "\n")
    return code
