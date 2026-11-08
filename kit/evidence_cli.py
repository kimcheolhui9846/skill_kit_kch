"""`kit report tests --junit FILE... [--out FILE]` (P5-T4): the CLI over kit.evidence.

Exit codes: 0 every traced test PASS and every requirement has a test, 1 otherwise (the
report is still written), 2 a JUnit file is missing or broken or --out leaves the workspace
(nothing written), 64 bad arguments, 65 trace.json broken.

--junit and --out are relative to the workspace (--target). Without --out the Markdown goes
to stdout and nothing else does, so it can be redirected.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, TextIO

from . import counterexamples as ce_mod
from . import evidence, junit, trace
from .fsops import PathEscapeError, safe_path
from .logs import mask, mask_tree
from .model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, TargetError, UsageError
from .trace_cli import _workspace

KINDS = ("tests",)


def add_parser(sub) -> None:
    p = sub.add_parser("report", add_help=False)
    kinds = p.add_subparsers(dest="kind", parser_class=type(p))
    t = kinds.add_parser("tests", add_help=False)
    t.add_argument("--junit", action="append", default=[], metavar="FILE")
    t.add_argument("--out", metavar="FILE")
    t.add_argument("--target", metavar="DIR")
    t.add_argument("--json", action="store_true")


def display(path: Path, target: Path) -> str:
    """Workspace-relative, else ~/..., else as is (R-09: no home path in reports)."""
    for base, prefix in ((target, ""), (Path.home().resolve(), "~/")):
        try:
            return prefix + path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


def run(ns: argparse.Namespace, cwd: Path, out: TextIO) -> int:
    if ns.kind is None:
        raise UsageError(f"report needs a kind: {', '.join(KINDS)}")
    if not ns.junit:
        raise UsageError("--junit FILE is needed: the report is built from run evidence")
    target = _workspace(ns.target, cwd)
    try:
        data = trace.load(target)
        ce_data = ce_mod.load(target)
    except (trace.TraceError, ce_mod.CeError) as exc:
        raise TargetError(str(exc)) from None
    try:
        cases: List[junit.Case] = []
        sources, inputs = [], []
        for raw in ns.junit:
            p = (target / raw).resolve()  # an absolute raw stays as is
            inputs.append(p)
            sources.append(display(p, target))
            cases += junit.parse(p, sources[-1])
        dest = safe_path(target, ns.out) if ns.out else None
        if dest is not None:
            _check_out(dest, target, inputs)
    except (junit.JUnitError, _OutError) as exc:
        return _blocked(out, ns.json, str(exc))
    except PathEscapeError:
        return _blocked(out, ns.json, f"--out '{ns.out}' is outside the workspace")
    report = evidence.build(data, cases, sources, ce_data)
    text = mask(evidence.markdown(report))
    problem = evidence.first_problem(report)
    code = EXIT_READY if problem is None else EXIT_PARTIAL
    status = "READY" if problem is None else "PARTIAL"
    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(text.encode("utf-8"))
        os.replace(tmp, dest)
    payload = {"action": "report tests", "status": status, **evidence.summary(report)}
    if ns.json:
        payload["report"] = display(dest, target) if dest else None
        if dest is None:
            payload["markdown"] = text
        out.write(
            json.dumps(mask_tree({**payload, "exit_code": code}), indent=2, ensure_ascii=False)
            + "\n"
        )
        return code
    if dest is None:
        out.write(text)
        return code
    t = payload["totals"]
    lines = [
        f"Report:       {display(dest, target)}",
        f"Tests:        PASS {t['pass']} / FAIL {t['fail']} / SKIPPED {t['skipped']} / "
        f"NOT RUN {t['not_run']}",
        f"Untracked:    {len(report.untracked)} JUnit testcase(s) not linked to a requirement",
    ]
    if problem:
        lines.append(f"Problem:      {problem}")
    out.write(mask("\n".join(lines + [f"Status:       {status}"])) + "\n")
    return code


class _OutError(Exception):
    pass


def _check_out(dest: Path, target: Path, inputs: List[Path]) -> None:
    """--out never replaces evidence, kit state or a folder (counterexample review)."""
    kit_dir, reports = target / ".kit", target / ".kit/work/reports"
    if (kit_dir == dest or kit_dir in dest.parents) and reports not in dest.parents:
        raise _OutError(
            f"--out {display(dest, target)}: only .kit/work/reports/ "
            "is open for reports inside .kit/"
        )
    if dest in inputs:
        raise _OutError(f"--out {display(dest, target)} is one of the --junit files")
    if dest.is_dir():
        raise _OutError(f"--out {display(dest, target)} is a folder")


def _blocked(out: TextIO, as_json: bool, reason: str) -> int:
    if as_json:
        payload = {
            "action": "report tests",
            "status": "BLOCKED",
            "reason": reason,
            "exit_code": EXIT_BLOCKED,
        }
        out.write(json.dumps(mask_tree(payload), indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(mask(f"Blocked:      {reason}\nStatus:       BLOCKED") + "\n")
    return EXIT_BLOCKED
