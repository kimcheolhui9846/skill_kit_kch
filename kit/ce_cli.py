"""`kit ce ...` (P5-T5): the CLI over kit.counterexamples.

Exit codes: 0 done, 2 a rule refused (the reason is printed), 64 bad arguments,
65 counterexamples.json or trace.json broken.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, TextIO

from . import counterexamples as ce
from . import trace
from .logs import mask, mask_tree
from .model import EXIT_BLOCKED, EXIT_READY, TargetError, UsageError
from .trace_cli import _workspace

ACTIONS = ("add", "list", "accept", "reject", "needs-spec", "resolve", "convert", "result")


def add_parser(sub) -> None:
    p = sub.add_parser("ce", add_help=False)
    actions = p.add_subparsers(dest="action", parser_class=type(p))
    a = actions.add_parser("add", add_help=False)
    a.add_argument("id")
    a.add_argument("--function", metavar="NAME")  # the record's "target"
    a.add_argument("--req", action="append", default=[], metavar="REQ")
    a.add_argument("--assumption")
    a.add_argument("--category")
    a.add_argument("--origin")
    a.add_argument("--input")
    a.add_argument("--expected")
    a.add_argument("--would-catch")
    a.add_argument("--rationale")
    parsers = [a, actions.add_parser("list", add_help=False)]
    for name, extra in (
        ("accept", ()),
        ("reject", ("--reason",)),
        ("needs-spec", ("--question",)),
        ("resolve", ("--expected", "--quote")),
        ("convert", ("--test",)),
        ("result", ("--result",)),
    ):
        q = actions.add_parser(name, add_help=False)
        q.add_argument("id")
        for flag in extra:
            q.add_argument(flag)
        parsers.append(q)
    for q in parsers:
        q.add_argument("--target", metavar="DIR")
        q.add_argument("--json", action="store_true")


def run(ns: argparse.Namespace, cwd: Path, out: TextIO) -> int:
    if ns.action is None:
        raise UsageError(f"ce needs an action: {', '.join(ACTIONS)}")
    target = _workspace(ns.target, cwd)
    try:
        data = ce.load(target)
        if ns.action == "list":
            return _list(data, ns, out)
        item = _change(target, data, ns)
        ce.save(target, data)
    except (ce.CeError, trace.TraceError) as exc:
        raise TargetError(str(exc)) from None
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    except ce.Refused as exc:
        payload = {"action": f"ce {ns.action}", "status": "REFUSED", "reason": str(exc)}
        return _emit(
            out, ns.json, payload, [f"Refused:      {exc}", "Status:       BLOCKED"], EXIT_BLOCKED
        )
    lines = [f"{item['id']:<13} {item['status']:<11} {item['target']}"]
    if item["status"] == ce.NEEDS_SPEC:
        lines.append(f"Ask:          {item['question']}")
    payload = {"action": f"ce {ns.action}", "status": "DONE", "item": item}
    return _emit(out, ns.json, payload, lines + ["Status:       DONE"], EXIT_READY)


def _change(target: Path, data: dict, ns) -> dict:
    action = ns.action
    if action == "add":
        return ce.add(
            data,
            ns.id,
            ns.function,
            ns.req,
            ns.assumption,
            ns.category,
            ns.origin,
            ns.input,
            ns.would_catch,
            ns.expected,
            ns.rationale,
            trace.load(target),
        )
    if action == "accept":
        return ce.accept(data, ns.id)
    if action == "reject":
        return ce.reject(data, ns.id, ns.reason)
    if action == "needs-spec":
        return ce.needs_spec(data, ns.id, ns.question)
    if action == "resolve":
        return ce.resolve(data, ns.id, ns.expected, ns.quote)
    if action == "convert":
        if not ns.test:
            raise ValueError("--test TEST-ID is needed (the test in trace.json)")
        return ce.convert(data, ns.id, ns.test, trace.load(target))
    return ce.record_result(data, ns.id, ns.result)  # result


def _list(data: dict, ns, out: TextIO) -> int:
    items = data["items"]
    c = ce.counts(items)
    lines = ["Counterexamples:"]
    for i in items:
        reqs = ",".join(i["requirements"]) or "-"
        lines.append(
            f"  {i['id']:<10} {i['status']:<11} {i['origin']:<10} {reqs:<16} "
            f"{i['category']:<10} {i['target']}"
        )
        if i["status"] == ce.NEEDS_SPEC:
            lines.append(f"             ask: {i['question']}")
    if not items:
        lines.append("  (none; kit ce add)")
    lines.append("Totals:       " + ", ".join(f"{k} {v}" for k, v in c.items()))
    payload = {"action": "ce list", "status": "READY", "counts": c, "items": items}
    return _emit(out, ns.json, payload, lines + ["Status:       READY"], EXIT_READY)


def _emit(out: TextIO, as_json: bool, payload: dict, lines: List[str], code: int) -> int:
    if as_json:
        out.write(
            json.dumps(mask_tree({**payload, "exit_code": code}), indent=2, ensure_ascii=False)
            + "\n"
        )
    else:
        out.write(mask("\n".join(lines)) + "\n")
    return code
