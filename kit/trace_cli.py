"""`kit req ...` and `kit trace ...` (P5-T3): the CLI over kit.trace.

Exit codes: 0 done (trace check: nothing found), 1 trace check found something,
2 a rule refused (the reason is printed), 64 bad arguments, 65 trace.json or the brief broken.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, TextIO

from . import trace
from .logs import mask, mask_tree
from .model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, TargetError, UsageError

REQ_ACTIONS = ("add", "edit", "list", "impact", "sync")
TRACE_ACTIONS = ("link", "check")


def add_parsers(sub) -> None:
    p = sub.add_parser("req", add_help=False)
    actions = p.add_subparsers(dest="action", parser_class=type(p))
    a = actions.add_parser("add", add_help=False)
    a.add_argument("id")
    a.add_argument("--text", required=True)
    a.add_argument("--priority", default="must")
    a.add_argument("--source", default="")
    e = actions.add_parser("edit", add_help=False)
    e.add_argument("id")
    e.add_argument("--text")
    e.add_argument("--priority")
    e.add_argument("--status")
    lst = actions.add_parser("list", add_help=False)
    im = actions.add_parser("impact", add_help=False)
    im.add_argument("id")
    sy = actions.add_parser("sync", add_help=False)
    sy.add_argument("--brief", default=trace.BRIEF_REL, metavar="FILE")
    req_parsers = (a, e, lst, im, sy)

    p = sub.add_parser("trace", add_help=False)
    actions = p.add_subparsers(dest="action", parser_class=type(p))
    ln = actions.add_parser("link", add_help=False)
    ln.add_argument("id")
    ln.add_argument("--req", action="append", default=[], metavar="REQ")
    ln.add_argument("--locator")
    ln.add_argument("--case")
    ln.add_argument("--kind")
    ln.add_argument("--purpose")
    ln.add_argument("--input")
    ln.add_argument("--expected")
    ck = actions.add_parser("check", add_help=False)
    for q in (*req_parsers, ln, ck):
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


def run(command: str, ns: argparse.Namespace, cwd: Path, out: TextIO) -> int:
    if ns.action is None:
        names = REQ_ACTIONS if command == "req" else TRACE_ACTIONS
        raise UsageError(f"{command} needs an action: {', '.join(names)}")
    target = _workspace(ns.target, cwd)
    try:
        data = trace.load(target)
        if command == "trace" and ns.action == "check":
            return _check(data, ns, out)
        if command == "req" and ns.action in ("list", "impact"):
            return _read(data, ns, out)
        lines, payload = _change(target, data, command, ns)
        trace.save(target, data)
    except trace.TraceError as exc:
        raise TargetError(str(exc)) from None
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    except trace.Refused as exc:
        refused = {"action": f"{command} {ns.action}", "status": "REFUSED", "reason": str(exc)}
        return _emit(
            out, ns.json, refused, [f"Refused:      {exc}", "Status:       BLOCKED"], EXIT_BLOCKED
        )
    payload = {"action": f"{command} {ns.action}", "status": "DONE", **payload}
    return _emit(out, ns.json, payload, lines + ["Status:       DONE"], EXIT_READY)


def _change(target: Path, data: dict, command: str, ns):
    if command == "trace":  # link
        if not ns.req:
            raise ValueError("--req is needed: a test checks at least one requirement")
        test, created = trace.link(
            data, ns.id, ns.req, ns.locator, ns.case, ns.kind, ns.purpose, ns.input, ns.expected
        )
        what = "Linked" if created else "Updated"
        reqs = ", ".join(f"{x['id']} r{x['revision']}" for x in test["requirements"])
        return [
            f"{what}:{' ' * (13 - len(what))}{test['id']} ({test['case']}) {test['locator']}",
            f"Checks:       {reqs}",
        ], {"test": test}
    if ns.action == "add":
        req = trace.add_req(data, ns.id, ns.text, ns.priority, ns.source)
        return [f"Added:        {req['id']} ({req['priority']}) r1 {req['text']}"], {
            "requirement": req
        }
    if ns.action == "edit":
        if ns.text is None and ns.priority is None and ns.status is None:
            raise ValueError("req edit needs --text, --priority or --status")
        req, revised = trace.edit_req(data, ns.id, ns.text, ns.priority, ns.status)
        lines = [f"Edited:       {req['id']} ({req['priority']}) r{req['revision']}"]
        if revised:
            lines += _impact_lines(data, req["id"])
        return lines, {"requirement": req, "revised": revised}
    result = trace.sync(target, data, ns.brief)  # sync
    lines = [
        f"Synced:       {ns.brief}: {len(result.added)} added, {len(result.revised)} revised, "
        f"{len(result.unchanged)} unchanged"
    ]
    for req_id in result.revised:
        lines += _impact_lines(data, req_id)
    if result.missing:
        lines.append(f"Warning:      no longer in {ns.brief} (kept): {', '.join(result.missing)}")
    return lines, {
        "added": result.added,
        "revised": result.revised,
        "unchanged": result.unchanged,
        "missing": result.missing,
    }


def _impact_lines(data: dict, req_id: str) -> List[str]:
    stale = trace.stale(data, req_id)
    if not stale:
        return []
    return [f"Review:       {t['id']} {t['locator']} (saw r{seen})" for t, seen in stale]


def _read(data: dict, ns, out: TextIO) -> int:
    if ns.action == "list":
        lines = ["Requirements:"]
        for r in data["requirements"]:
            n = len(trace.tests_for(data, r["id"]))
            lines.append(
                f"  {r['id']:<12} {r['priority']:<6} r{r['revision']:<3} {n} test(s)  {r['text']}"
            )
        if not data["requirements"]:
            lines.append("  (none; kit req add or kit req sync)")
        payload = {"action": "req list", "status": "READY", **trace.counts(data)}
        payload["requirements"] = data["requirements"]
        return _emit(out, ns.json, payload, lines + ["Status:       READY"], EXIT_READY)
    req = trace.get_req(data, ns.id)
    if req is None:
        raise UsageError(f"no requirement {ns.id} (kit req list)")
    tests = trace.tests_for(data, ns.id)
    stale_ids = {t["id"] for t, _ in trace.stale(data, ns.id)}
    lines = [f"Requirement:  {req['id']} ({req['priority']}) r{req['revision']} {req['text']}"]
    for t in tests:
        mark = "REVIEW" if t["id"] in stale_ids else "ok"
        lines.append(f"  {mark:<7}{t['id']:<12} {t['case']:<15} {t['locator']}")
    if not tests:
        lines.append("  (no test checks it)")
    payload = {
        "action": "req impact",
        "status": "READY",
        "requirement": req,
        "tests": [t["id"] for t in tests],
        "review": sorted(stale_ids),
    }
    return _emit(out, ns.json, payload, lines + ["Status:       READY"], EXIT_READY)


def _check(data: dict, ns, out: TextIO) -> int:
    findings = trace.check(data)
    c = trace.counts(data)
    lines = [
        f"Traced:       {c['requirements']} requirement(s) ({c['must']} must), {c['tests']} test(s)"
    ]
    lines += [f"  {f.line()}" for f in findings]
    if not findings:
        lines.append("  no gaps found")
    code = EXIT_PARTIAL if findings else EXIT_READY
    status = "GAPS" if findings else "READY"
    payload = {
        "action": "trace check",
        "status": status,
        **c,
        "findings": [f.to_json() for f in findings],
    }
    return _emit(out, ns.json, payload, lines + [f"Status:       {status}"], code)


def _emit(out: TextIO, as_json: bool, payload: dict, lines: List[str], code: int) -> int:
    if as_json:
        out.write(
            json.dumps(mask_tree({**payload, "exit_code": code}), indent=2, ensure_ascii=False)
            + "\n"
        )
    else:
        out.write(mask("\n".join(lines)) + "\n")
    return code
