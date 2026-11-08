"""`kit source ...` output and approval (P4-T8, 05_CLI_SPEC §4.2). Logic: kit.source_add."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, List, Optional, TextIO

from . import source_add as sa
from . import sources
from .github_fetch import NetworkError
from .model import (
    EXIT_BLOCKED,
    EXIT_PARTIAL,
    EXIT_READY,
    TargetError,
    UsageError,
)

STATUS = {EXIT_READY: "READY", EXIT_PARTIAL: "PARTIAL", EXIT_BLOCKED: "BLOCKED"}
Ask = Optional[Callable[[str], str]]


def add_parser(sub) -> None:
    p = sub.add_parser("source", add_help=False)
    actions = p.add_subparsers(dest="action", parser_class=type(p))
    a = actions.add_parser("add", add_help=False)
    a.add_argument("url")
    a.add_argument("--ref")
    a.add_argument("--path", action="append", default=[])
    a.add_argument("--all", action="store_true")
    a.add_argument("--name")
    a.add_argument("--pack")
    a.add_argument("--include", action="append", default=[], metavar="PATH")
    a.add_argument("--replaces", action="append", default=[], metavar="SKILL")
    a.add_argument("--keep-both", action="store_true")
    a.add_argument("--overlap-threshold", type=float, default=sa.THRESHOLD)
    u = actions.add_parser("update", add_help=False)
    u.add_argument("id")
    u.add_argument("--ref")
    for q in (a, u):
        q.add_argument("--accept-license", action="store_true")
        q.add_argument("--accept-risk", action="store_true")
        q.add_argument("--offline", action="store_true")
    c = actions.add_parser("check", add_help=False)
    c.add_argument("--online", action="store_true")
    r = actions.add_parser("remove", add_help=False)
    r.add_argument("id")
    lst = actions.add_parser("list", add_help=False)
    for q in (a, u, c, r):
        q.add_argument("--yes", action="store_true")
    for q in (a, u, c, r, lst):
        q.add_argument("--json", action="store_true")


def run(ns: argparse.Namespace, kit_root: Path, out: TextIO, ask: Ask) -> int:
    if ns.action is None:
        raise UsageError("source needs an action: add, list, check, update or remove")
    if getattr(ns, "offline", False):
        raise UsageError(f"source {ns.action} needs the network; it cannot run with --offline")
    if ns.action == "list":
        return _list(kit_root, ns.json, out)
    if ns.action == "check":
        return _check(kit_root, ns, out, ask)
    if ns.action == "remove":
        return _remove(kit_root, ns, out, ask)
    return _add_or_update(kit_root, ns, out, ask)


# ---------------------------------------------------------------- list / check


def _list(kit_root: Path, as_json: bool, out: TextIO) -> int:
    lock = sources.load(kit_root)
    rows = [
        {
            "id": s.id,
            "kind": s.kind,
            "integration": s.integration,
            "license": s.license,
            "commit": s.commit,
            "origin": s.origin,
            "packs": s.raw.get("packs", []),
            "added_by": s.raw.get("added_by"),
        }
        for s in lock.values()
    ]
    if as_json:
        out.write(json.dumps({"command": "source list", "sources": rows}, indent=2) + "\n")
        return EXIT_READY
    out.write(f"{'id':<28} {'kind':<13} {'integration':<18} {'license':<12} commit\n")
    for r in rows:
        out.write(
            f"{r['id']:<28} {r['kind']:<13} {r['integration']:<18} {r['license']:<12} "
            f"{r['commit'][:12]}  {r['origin'].replace('https://github.com/', '')}\n"
        )
    return EXIT_READY


def _check(kit_root: Path, ns, out: TextIO, ask: Ask) -> int:
    try:
        problems = sources.check(kit_root)
    except sources.LockError as exc:
        raise TargetError(str(exc)) from None
    online = "not run (offline check; add --online)"
    code = EXIT_PARTIAL if problems else EXIT_READY
    if ns.online:
        if _approved(ns, ask, "Check every pinned commit on github.com? [y/N] ") is not True:
            online = "SKIPPED (network; re-run with --yes)"
        else:
            try:
                remote = sa.check_online(kit_root, sa.make_client())
            except NetworkError as exc:
                remote, online, code = [], f"FAILED: {exc}", EXIT_BLOCKED
            else:
                online = "every commit found" if not remote else f"{len(remote)} problem(s)"
                problems += remote
                if remote and code == EXIT_READY:
                    code = EXIT_PARTIAL
    data = {
        "command": "source check",
        "status": STATUS[code],
        "problems": problems,
        "online": online,
        "exit_code": code,
    }
    if ns.json:
        out.write(json.dumps(data, indent=2) + "\n")
        return code
    lines = [f"Lock:         {sources.LOCK_REL} ({len(sources.load(kit_root))} sources)"]
    lines.append(f"Files:        {'match the lock' if not problems else 'problems found'}")
    lines += [f"  - {p}" for p in problems]
    lines += [f"Online:       {online}", f"Status:       {STATUS[code]}"]
    out.write("\n".join(lines) + "\n")
    return code


# ---------------------------------------------------------------- add / update


def _approved(ns, ask: Ask, question: str) -> Optional[bool]:
    """True: go. None: nobody to ask (plan only). False: the person said no."""
    if getattr(ns, "yes", False):
        return True
    if ask is None:
        return None
    return ask(question).strip().lower() in ("y", "yes")


def _changes(kit_root: Path, plan: sa.Plan) -> List[tuple]:
    rows = []
    for rel, data in sorted(plan.writes.items()):
        path = kit_root / rel
        change = (
            "CREATE"
            if not path.is_file()
            else ("UNCHANGED" if path.read_bytes() == data else "UPDATE")
        )
        rows.append((change, rel))
    rows += [("DELETE", rel) for rel in plan.deletes]
    return rows


def _plan_lines(kit_root: Path, plan: sa.Plan, verb: str) -> List[str]:
    spec = plan.spec
    lines = [
        f"Source:       {spec.owner}/{spec.repo} @ {plan.ref} -> {plan.commit[:12]}",
        f"Id:           {plan.source_id}",
        f"Kind:         {plan.kind}"
        + (f" ({', '.join(p.name for p in plan.picks)})" if plan.picks else ""),
        f"License:      {plan.license.spdx}"
        + (f" ({plan.license.rel})" if plan.license.rel else "")
        + (" -> vendored-verbatim" if plan.vendored else " -> referenced (no files copied)"),
    ]
    if plan.unchanged:
        return lines + [f"Changes:      none ({plan.notes[0]})"]
    lines.append("Files:")
    rows = _changes(kit_root, plan)
    lines += [f"  {c:<10}{rel}" for c, rel in rows] or ["  (none)"]
    touched = [sources.LOCK_REL]
    if plan.vendored or verb == "update":
        touched += [sa.CATALOG_REL, sources.NOTICES_REL]
    lines.append(f"  UPDATE    {', '.join(touched)}")
    for pick in plan.picks:
        lines += [
            f"  LEFT OUT  {rel} (script; --include {rel} to take it)" for rel in pick.left_out
        ]  # noqa: E501
    for item in plan.catalog_entries:
        extra = f"; replaces {', '.join(item['replaces'])}" if item.get("replaces") else ""
        extra += f"; requires {', '.join(item['requires'])}" if item.get("requires") else ""
        packs = ", ".join(item["packs"]) or "none"
        lines.append(f"Catalog:      {item['name']} (packs: {packs}; policy: standard{extra})")
    for o in plan.overlaps:
        lines.append(
            f"Overlap:      {o.get('skill')} ~ {o['with']} {o.get('score')} -> "
            f"{o.get('decision') or 'needs a decision'}"
        )
    if plan.findings:
        lines.append("Findings:")
        lines += [f"  {f.level:<7}{f.text}" for f in plan.findings]
    lines += [f"Note:         {n}" for n in plan.notes]
    return lines


def _add_or_update(kit_root: Path, ns, out: TextIO, ask: Ask) -> int:
    previous = None
    if ns.action == "update":
        lock = sources.load(kit_root)
        if ns.id not in lock:
            raise TargetError(f"no source '{ns.id}' in {sources.LOCK_REL}")
        previous = lock[ns.id]
        if previous.raw.get("added_by") != sa.ADDED_BY:
            return _needs(
                ns, out, [f"'{ns.id}' was not added by `kit source add`; update it by hand"]
            )  # noqa: E501
        changed = sources._file_problems(kit_root, previous)
        if changed:
            return _needs(ns, out, changed + ["local changes are never overwritten"])
        spec = sa.parse_url(previous.origin, ns.ref or previous.raw.get("ref"))
        spec.paths = list(previous.raw.get("paths", []))
        opts = sa.Options(
            all_skills=True, accept_license=ns.accept_license, accept_risk=ns.accept_risk
        )
    else:
        spec = sa.parse_url(ns.url, ns.ref, ns.path)
        opts = sa.Options(
            pack=ns.pack,
            all_skills=ns.all,
            name=ns.name,
            accept_license=ns.accept_license,
            accept_risk=ns.accept_risk,
            replaces=ns.replaces,
            keep_both=ns.keep_both,
            include=ns.include,
            threshold=ns.overlap_threshold,
        )
    try:
        plan = sa.build(kit_root, spec, opts, sa.make_client(), previous)
    except sa._Needs as exc:
        return _needs(ns, out, [str(exc)])
    except NetworkError as exc:
        return _needs(ns, out, [str(exc)], network=True)
    except sa.SourceBlocked as exc:
        return _finish(
            ns,
            out,
            ["Status:       PARTIAL", f"Blocked:      {exc}"],
            EXIT_PARTIAL,
            {"blocked": str(exc)},
        )  # noqa: E501
    lines = _plan_lines(kit_root, plan, ns.action)
    data = {
        "source": plan.entry or None,
        "files": [{"change": c, "path": r} for c, r in _changes(kit_root, plan)],
        "left_out": [r for p in plan.picks for r in p.left_out],
        "catalog": plan.catalog_entries,
        "overlap": plan.overlaps,
        "findings": [{"level": f.level, "text": f.text} for f in plan.findings],
        "needs": plan.needs,
        "notes": plan.notes,
        "written": False,
    }
    if plan.unchanged:
        return _finish(ns, out, lines + ["Status:       READY"], EXIT_READY, data)
    if plan.blocked:
        lines += [
            "Status:       PARTIAL",
            "Next action:",
            "  - Nothing was written. Fix or narrow the source (--path) and re-run.",
        ]  # noqa: E501
        return _finish(ns, out, lines, EXIT_PARTIAL, data)
    if plan.needs:
        lines += ["Status:       BLOCKED (a person must decide)", "Next action:"]
        lines += [f"  - {n}" for n in plan.needs]
        return _finish(ns, out, lines, EXIT_BLOCKED, data)
    answer = _approved(ns, None if ns.json else ask, "\n".join(lines) + "\nApply? [y/N] ")
    if answer is not True:
        why = "cancelled" if answer is False else "plan only"
        lines += [
            "Status:       READY",
            "Next action:",
            f"  - {why}: nothing was written. Re-run with --yes to apply.",
        ]
        return _finish(ns, out, lines, EXIT_READY, data)
    problems = sa.apply(kit_root, plan, previous)
    if problems:
        lines += ["Status:       PARTIAL", "Rolled back:  every file was put back"]
        lines += [f"  - {p}" for p in problems]
        data["problems"] = problems
        return _finish(ns, out, lines, EXIT_PARTIAL, data)
    data["written"] = True
    lines += [
        "Status:       READY",
        "Next action:",
        "  - Run the tests (`uv run pytest -q`), then review `git diff`; the kit never commits.",
    ]
    if plan.vendored and not plan.entry.get("packs"):
        lines.append("  - Add the skill to a profile or pack (or re-run add with --pack).")
    return _finish(ns, out, lines, EXIT_READY, data)


def _needs(ns, out: TextIO, reasons: List[str], network: bool = False) -> int:
    lines = ["Status:       BLOCKED (" + ("network" if network else "a person must decide") + ")"]
    lines += ["Next action:"] + [f"  - {r}" for r in reasons]
    return _finish(ns, out, lines, EXIT_BLOCKED, {"needs": reasons, "written": False})


def _finish(ns, out: TextIO, lines: List[str], code: int, data: dict) -> int:
    if getattr(ns, "json", False):
        payload = {"command": f"source {ns.action}", "status": STATUS[code], "exit_code": code}
        payload.update(data)
        out.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        out.write("\n".join(lines) + "\n")
    return code


# ---------------------------------------------------------------- remove


def _remove(kit_root: Path, ns, out: TextIO, ask: Ask) -> int:
    removal = sa.plan_remove(kit_root, ns.id)
    lines = [f"Source:       {ns.id} ({removal.source.origin})", "Files:"]
    lines += [f"  DELETE    {rel}" for rel in removal.deletes] or ["  (none)"]
    lines.append(f"  UPDATE    {sources.LOCK_REL}, {sa.CATALOG_REL}, {sources.NOTICES_REL}")
    if removal.skills:
        lines.append(f"Catalog:      remove {', '.join(removal.skills)}")
    data = {"deletes": removal.deletes, "skills": removal.skills, "needs": removal.needs}
    if removal.needs:
        lines += ["Status:       BLOCKED (a person must decide)", "Next action:"]
        lines += [f"  - {n}" for n in removal.needs]
        return _finish(ns, out, lines, EXIT_BLOCKED, dict(data, written=False))
    answer = _approved(ns, None if ns.json else ask, "\n".join(lines) + "\nRemove? [y/N] ")
    if answer is not True:
        lines += [
            "Status:       READY",
            "Next action:",
            "  - nothing was removed. Re-run with --yes.",
        ]  # noqa: E501
        return _finish(ns, out, lines, EXIT_READY, dict(data, written=False))
    problems = sa.apply_remove(kit_root, removal)
    if problems:
        lines += ["Status:       PARTIAL", "Rolled back:  every file was put back"]
        lines += [f"  - {p}" for p in problems]
        return _finish(ns, out, lines, EXIT_PARTIAL, dict(data, written=False, problems=problems))  # noqa: E501
    lines += ["Status:       READY"]
    return _finish(ns, out, lines, EXIT_READY, dict(data, written=True))
