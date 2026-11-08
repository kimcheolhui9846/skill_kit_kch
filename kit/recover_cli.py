"""`kit recover [save|decide]` (P5-T7): the CLI over kit.recover.

    kit recover                       restore: approved state, then the temporary state apart
    kit recover save [--task ID] [--subtask ID] [--note T] [--command C] [--tests T]
                     [--error E]...   overwrite .kit/work/wip.json (UNAPPROVED)
    kit recover decide "TEXT" [--task ID]   append to .kit/work/decisions.md

Exit codes: 0 done, 1 recover has warnings (a broken wip.json, a report changed after
approval, no snapshot, a HANDOFF.md the kit did not write), 2 a rule refused (unknown task),
64 bad arguments, 65 tasks.json is broken.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, TextIO

from . import recover, tasks
from .logs import mask, mask_tree
from .model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, TargetError, UsageError
from .trace_cli import _workspace

SHOWN = 30
SAVE_OPTS = ("subtask", "note", "last_command", "tests", "error")


def add_parser(sub) -> None:
    p = sub.add_parser("recover", add_help=False)
    p.add_argument("action", nargs="?", choices=("save", "decide"))
    p.add_argument("text", nargs="?")
    p.add_argument("--task", metavar="ID")
    p.add_argument("--subtask", metavar="ID")
    p.add_argument("--note")
    p.add_argument("--command", dest="last_command")  # ns.command is the subcommand
    p.add_argument("--tests")
    p.add_argument("--error", action="append", default=[])
    p.add_argument("--target", metavar="DIR")
    p.add_argument("--json", action="store_true")


def run(ns: argparse.Namespace, cwd: Path, out: TextIO) -> int:
    _check_args(ns)
    target = _workspace(ns.target, cwd)
    try:
        data = tasks.load(target)
    except tasks.TasksError as exc:
        raise TargetError(str(exc)) from None
    if ns.action is None:
        return _show(target, data, ns.json, out)
    try:
        if ns.task is not None:
            tasks.get(data, ns.task)
        if ns.action == "decide":
            line = recover.decide(target, ns.text, ns.task)
            return _emit(
                out,
                ns.json,
                {"action": "decide", "status": "DONE", "decision": line},
                [f"Decision:     appended to {recover.DECISIONS_REL}", "Status:       DONE"],
                EXIT_READY,
            )
        cur = recover.current_task(data)
        task_id = ns.task or (cur["id"] if cur else None)
        fields = {
            "task": task_id,
            "subtask": ns.subtask,
            "note": ns.note,
            "last_command": ns.last_command,
            "last_tests": ns.tests,
        }
        wip = recover.save_wip(target, fields, ns.error)
    except tasks.Refused as exc:
        return _emit(
            out,
            ns.json,
            {"action": ns.action, "status": "REFUSED", "reason": str(exc)},
            [f"Refused:      {exc}", "Status:       BLOCKED"],
            EXIT_BLOCKED,
        )
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    return _emit(
        out,
        ns.json,
        {"action": "save", "status": "DONE", "wip": wip},
        [
            f"Saved:        {recover.WIP_REL} (temporary, not approved; task {task_id or '-'})",
            "Status:       DONE",
        ],
        EXIT_READY,
    )


def _check_args(ns: argparse.Namespace) -> None:
    given = [o for o in SAVE_OPTS if getattr(ns, o)]
    if ns.action is None:
        if ns.text is not None or given or ns.task is not None:
            raise UsageError("kit recover takes no arguments; use recover save or recover decide")
    elif ns.action == "decide":
        if not (ns.text or "").strip():
            raise UsageError('recover decide needs the decision text: kit recover decide "..."')
        if given:
            raise UsageError(f"--{given[0].replace('last_', '')} is for recover save")
    else:
        if ns.text is not None:
            raise UsageError("recover save takes options, not text (use --note)")
        if not given:
            raise UsageError("recover save needs --note, --command, --tests, --error or --subtask")


def _show(target: Path, data: dict, as_json: bool, out: TextIO) -> int:
    res = recover.recover(target, data)
    code = EXIT_PARTIAL if res["warnings"] else EXIT_READY
    status = "PARTIAL" if code else "READY"
    if as_json:
        payload = {"action": "recover", "status": status, **res}
        return _emit(out, True, payload, [], code)
    return _emit(out, False, {}, lines(res) + [f"Status:       {status}"], code)


def lines(res: dict) -> List[str]:
    a = res["approved"]
    out = [f"Approved state (from {tasks.TASKS_REL}):"]
    cur = a["current"]
    if cur:
        subs = f" [subtasks {cur['subtasks_done']}/{cur['subtasks']}]" if cur["subtasks"] else ""
        out.append(f"  Current task:   {cur['id']} {cur['state']} - {cur['title']}{subs}")
    else:
        out.append("  Current task:   none")
    last = a["last_approved"]
    if last:
        out.append(
            f"  Last approved:  {last['id']} at {last['at']} by {last['by']} - {last['title']}"
        )
        out.append(f"  Approved:       {len(a['approved'])}: {', '.join(a['approved'])}")
    else:
        out.append("  Last approved:  none yet")
    ch = a["changed"]
    if ch:
        where = f"commit {ch['commit'][:12]}" if ch["commit"] else "no git commit"
        out.append(
            f"  Changed since {ch['since']} ({where}, by {ch['method']}): {len(ch['files'])}"
        )
        out += [f"    {f['change']} {f['path']}" for f in ch["files"][:SHOWN]]
        if len(ch["files"]) > SHOWN:
            out.append(f"    ... and {len(ch['files']) - SHOWN} more (--json lists all)")
    if a["tests"] is not None:
        counts = ", ".join(f"{k} {v}" for k, v in sorted(a["tests"].items())) or "no rows"
        out.append(f"  Last tests:     {counts} (approved report, section 4)")
    out += ["  Open risks:"] + [f"    {r}" for r in a["risks"]] if a["risks"] else []
    out += ["  Next plan:"] + [f"    {n}" for n in a["next"]] if a["next"] else []
    out.append(f"  Can start:      {', '.join(a['can_start']) or 'none'}")
    if a["decisions"]:
        out.append(f"  Decisions ({recover.DECISIONS_REL}, latest {len(a['decisions'])}):")
        out += [f"    {d}" for d in a["decisions"]]
    out.append(f"  Handoff:        {recover.HANDOFF_REL} ({a['handoff']})")
    w = res["wip"]
    if w is None:
        out.append("Temporary (not approved): none saved")
    else:
        out.append(f"Temporary (not approved, {recover.WIP_REL}, saved {w.get('saved_at')}):")
        if w.get("stale"):
            out.append(f"  Out of date?    {w['stale']}")
        names = (
            ("task", "Task"),
            ("subtask", "Subtask"),
            ("note", "Note"),
            ("last_command", "Last command"),
            ("last_tests", "Last tests"),
        )
        for key, label in names:
            if w.get(key):
                out.append(f"  {label + ':':<16}{w[key]}")
        out += [f"  Open error:     {e}" for e in w.get("errors", [])]
    if res["root_handoff"]:
        out.append(
            f"Note:         {res['root_handoff']} at the workspace root is not the kit's; "
            "not read, not changed"
        )
    out += [f"Warning:      {w}" for w in res["warnings"]]
    return out


def _emit(out: TextIO, as_json: bool, payload: dict, lines_: List[str], code: int) -> int:
    if as_json:
        doc = mask_tree({**payload, "exit_code": code})
        out.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(mask("\n".join(lines_)) + "\n")
    return code
