"""Orchestration: preflight -> plan -> apply -> verify -> report."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from . import audit, commands, mcpcheck, mcpconfig, tools, webcheck
from .adapters import registry
from .cli import Options, parse_args
from .fsops import PathEscapeError, State, timestamp
from .logs import write_log
from .model import EXIT_BLOCKED, EXIT_READY, EXIT_TARGET, EXIT_USAGE, TargetError, UsageError
from .plan import FileChange, format_plan
from .preflight import EnvReport, run_preflight
from .profiles import available_profiles, load_profile
from .register import apply_changes
from .report import next_actions, overall_status, render
from .verify import verify_target

KIT_ROOT = Path(__file__).resolve().parent.parent
SELF_TARGET_MSG = (
    "target is the kit folder itself; run from your workspace or pass --target <workspace>"
)


def run(
    argv: list[str],
    cwd: Path | None = None,
    kit_root: Path = KIT_ROOT,
    out: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    cwd = cwd or Path.cwd()
    if argv and argv[0] in commands.SUBCOMMANDS:  # new path (ADR-002); anything else is legacy
        ask = commands.terminal_ask() if out is sys.stdout else None
        return commands.run(argv, cwd, kit_root, out, ask)
    try:
        opts = parse_args(argv, cwd, available_profiles(kit_root))
        profile = load_profile(kit_root, opts.profile)
        mcpconfig.select_servers(kit_root, profile.mcp)
        if opts.target == kit_root.resolve():
            raise TargetError(SELF_TARGET_MSG)
    except UsageError as exc:
        print(f"error: {exc}\nRun with --help for usage.", file=sys.stderr)
        return EXIT_USAGE
    except TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TARGET

    adapter = registry.get("codex")  # the legacy invocation is always Codex (ADR-002)
    env = run_preflight(opts.target)
    state = State.load(opts.target)
    include_mcp = bool(profile.mcp) and not opts.no_mcp
    changes = adapter.plan(opts.target, kit_root, profile, state, include_mcp)
    actions = tools.plan_tools(profile, env, opts.offline, opts.verify_only)

    if opts.dry_run:
        out.write(_dry_run_text(opts, env, changes, actions, profile))
        return EXIT_READY

    stamp = timestamp()
    lines = []
    if not opts.verify_only and env.target_writable:
        try:
            apply_changes(opts.target, changes, state, stamp, opts.profile)
        except (OSError, PathEscapeError) as exc:
            lines.append(f"error: write failed: {exc}")
    tool_items = tools.run_tools(actions)

    items = verify_target(
        opts.target,
        kit_root,
        profile,
        changes,
        check_writable=not opts.verify_only,
        writable=env.target_writable,
        include_mcp=include_mcp,
        policy_rel=adapter.policy.rel,
        skill_root=adapter.skill_root,
    )
    if not include_mcp:
        stale = mcpconfig.stale_block_item(opts.target)
        if stale is not None:
            items.append(stale)
    items.append(audit.audit_target(opts.target, kit_root))
    items.extend(tool_items)
    if any(spec["kind"] == "node-project" for spec in profile.tools):
        items.append(webcheck.check_node_project(opts.target, env.tools.get("node")))
    if profile.mcp:
        items.extend(
            mcpcheck.check_servers(
                kit_root, profile.mcp, env, opts.target, opts.offline, opts.no_mcp
            )
        )
    status, code = overall_status(items)
    network = _network_line(opts, actions, profile)
    lines.append(
        render(env, opts, items, status, next_actions(items, opts.target, status), network)
    )
    text = "\n".join(lines)
    out.write(text)
    if env.target_writable:
        try:
            write_log(opts.target, text, stamp)
        except (OSError, PathEscapeError):
            pass
    return code


def main(argv: list[str]) -> int:
    """Entry-point wrapper: any unexpected error is BLOCKED, never a bare traceback."""
    for stream in (sys.stdout, sys.stderr):  # a cp949/cp1252 console must not crash the run
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        return run(argv)
    except PathEscapeError as exc:  # a safety refusal, not a crash (P7-T1 wording)
        print("Status:       BLOCKED", file=sys.stderr)
        print(f"error: {exc}; a link or path leads outside the target", file=sys.stderr)
        return EXIT_BLOCKED
    except Exception as exc:
        print("Status:       BLOCKED", file=sys.stderr)
        print(f"error: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BLOCKED


def _network_line(opts: Options, actions, profile) -> str:
    if opts.offline:
        return "not used (--offline)"
    used = tools.network_used(actions)
    if profile.mcp and not opts.no_mcp:
        used.append("npx (MCP handshake)")
    return "used: " + "; ".join(used) if used else "not used"


def _dry_run_text(
    opts: Options, env: EnvReport, changes: list[FileChange], actions, profile
) -> str:
    planned = tools.network_used(actions)
    if profile.mcp and not opts.no_mcp:
        planned.append("npx (MCP handshake)")
    if opts.offline:
        network = "none (--offline)"
    elif planned:
        network = "would use: " + "; ".join(planned)
    elif not profile.tools and not profile.mcp:
        network = "none (this profile installs no tools)"
    else:
        network = "none"
    lines = [
        f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}",
        f"Target:       {opts.target}",
        f"Profile:      {opts.profile}",
        f"Network:      {network}",
        "Planned changes:",
        format_plan(changes, opts.verbose),
    ]
    if actions:
        lines += ["Planned tools:", tools.format_tool_plan(actions)]
    if profile.mcp:
        reason = "--no-mcp" if opts.no_mcp else ("--offline" if opts.offline else None)
        lines.append("Planned MCP checks:")
        for name in profile.mcp:
            lines.append(
                f"  SKIPPED   mcp:{name}  ({reason})"
                if reason
                else f"  HANDSHAKE mcp:{name}  (npx -y <pinned package>) [network]"
            )
    lines += ["DRY RUN: nothing was written.", ""]
    return "\n".join(lines)
