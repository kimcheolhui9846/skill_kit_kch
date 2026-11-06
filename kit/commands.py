"""New CLI path: `kit <subcommand> ...` (05_CLI_SPEC, ADR-002). The legacy path is kit.app.

Implemented here: install, plan, verify, doctor, profiles, help, version (P3-T6),
update/uninstall/restore (P3-T7), capture and --scope user (P4-T7, ADR-018/019),
source (P4-T8, ADR-021; kit.source_cli), task (P5-T2; kit.task_cli). Recognised but
later: req/trace/report/recover (P5). They exit 64 with the Task that adds them.

--scope user: the target is the home folder (kit.userscope); writes need --yes or a yes at
a terminal, and paths are shown as ~.

Network (D-14, ADR-014): every network action is listed in plan and report, per agent.
--offline: never. --yes: allowed. Otherwise a terminal asks once; without a terminal the
network items are SKIPPED (exit code unaffected). The legacy path keeps its baseline behaviour.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, TextIO, Tuple

from . import (
    capture,
    catalog,
    credentials,
    lifecycle,
    mcp_catalog,
    mcpcheck,
    mcpconfig,
    plugin_install,
    policy_render,
    profile_resolver,
    source_cli,
    task_cli,
    tools,
    userscope,
    webcheck,
)
from . import manifest as manifest_mod
from .adapters import registry
from .adapters import user as user_adapters
from .cli import _Parser
from .fsops import (
    STATE_REL,
    PathEscapeError,
    State,
    backups_rel,
    own_files,
    safe_path,
    user_scope,
)
from .logs import mask, write_log
from .model import (
    CONFLICT,
    EXIT_BLOCKED,
    EXIT_PARTIAL,
    EXIT_READY,
    EXIT_TARGET,
    EXIT_USAGE,
    FAIL,
    PASS,
    SKIPPED,
    UNVERIFIED,
    ItemResult,
    Outcome,
    TargetError,
    UsageError,
)
from .plan import FileChange, format_plan
from .preflight import EnvReport, run_preflight
from .profiles import Profile, ProfileError
from .report import overall_status
from .transaction import TransactionError, apply_all, fresh_stamp

DEFAULT_PROFILE = "core,hitl"  # ADR-008
DEFAULT_POLICY = "standard"  # ADR-015
IMPLEMENTED = (
    "install",
    "plan",
    "verify",
    "doctor",
    "update",
    "uninstall",
    "restore",
    "profiles",
    "capture",
    "source",
    "task",
    "help",
    "version",
)
LATER = {
    "req": "P5",
    "trace": "P5",
    "report": "P5",
    "recover": "P5",
}
SUBCOMMANDS = IMPLEMENTED + tuple(LATER)
BAD = (FAIL, CONFLICT)
SELF_TARGET_MSG = (
    "target is the kit folder itself; run from your workspace or pass --target <workspace>"
)
HELP = """usage: kit <command> [options]     (bootstrap.sh / bootstrap.ps1 / python run_kit.py)

Install for one agent:
  kit install --agent codex            AGENTS.md, .agents/skills/, .codex/config.toml
  kit install --agent claude           CLAUDE.md, .claude/skills/, .mcp.json
  kit install --agent both             both of the above, all-or-nothing

Commands:
  install   --agent codex|claude|both [--profile a,b] [--policy standard|restricted]
            [--target DIR] [--dry-run] [--offline] [--yes] [--no-mcp] [--verbose]
            [--mcp NAME]... [--plugin NAME]... [--manual NAME]...
            [--json | --report-json FILE]
  plan      same arguments as install; never writes
  verify    --agent codex|claude|both [--target DIR] [--offline] [--yes] [--no-mcp]
  update    --agent A [--dry-run]    re-install kit-owned items at this kit's version;
                                     removes kit items the profile no longer has
  uninstall --agent A [--dry-run]    remove kit-owned items whose content is unchanged
  restore   --backup STAMP [--dry-run]  put back files saved in .kit/backups/STAMP/
  capture   [--agent A] [--write]    copy this PC's portable global settings into user/
                                     (dry run unless --write; secrets stop it)
  source    add URL [--path P]... [--all] [--pack K] [--yes]   copy a GitHub skill into
                                     third_party/ at a pinned commit (plan unless --yes)
            list | check [--online] | update ID [--ref R] | remove ID
  task      add ID --title T [--requires REQ]... [--depends-on ID]... [--grade L|S|C]
            | list | start ID | subtask add ID TITLE | subtask done SUB-ID | report ID
            | submit ID [--report FILE] | approve ID [--by agent-recorded --quote TEXT]
            | request-changes ID --reason TEXT | status [ID]     (.kit/work/tasks.json)
  doctor    [--target DIR]           which agents are on this PC, what the kit installed
  profiles  list | show a[,b] [--agent codex|claude|both]
  help, version

--scope user installs into ~/.codex and ~/.claude: the user/ snapshot, OMX (Codex) and the
profile's kit skills; it asks first (or needs --yes) and backs up to ~/.kit-backups/.
Defaults: --profile core,hitl  --policy standard  --scope project
--mcp / --plugin opt in to entries of catalog/mcp.json / catalog/plugins.json that are off
by default (verify and update keep what install chose).
--manual prints the steps and risks of a tool in catalog/manual.json; the kit never runs it.
--yes allows network use (installing missing tools, MCP handshake).
Without a command, the legacy installer runs (Codex, restricted policy); see --help.

exit codes: 0 READY, 1 PARTIAL, 2 BLOCKED, 64 invalid arguments, 65 target problem
"""


# ---------------------------------------------------------------- parsing


def _common(p: argparse.ArgumentParser, profile: bool = True) -> None:
    p.add_argument("--agent", choices=("codex", "claude", "both"))
    if profile:
        p.add_argument("--profile", default=DEFAULT_PROFILE)
        p.add_argument("--policy", choices=policy_render.POLICIES)
    p.add_argument("--scope", choices=("project", "user"), default="project")
    p.add_argument("--target")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--no-mcp", action="store_true")
    p.add_argument("--verbose", action="store_true")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true")
    out.add_argument("--report-json", metavar="FILE")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="kit", add_help=False)
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)
    for name in ("install", "plan"):
        p = sub.add_parser(name, add_help=False)
        _common(p)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--mcp", action="append", default=[], metavar="NAME")
        p.add_argument("--plugin", action="append", default=[], metavar="NAME")
        p.add_argument("--manual", action="append", default=[], metavar="NAME")
    _common(sub.add_parser("verify", add_help=False), profile=False)
    for name in ("update", "uninstall", "restore"):
        p = sub.add_parser(name, add_help=False)
        _common(p, profile=False)
        p.add_argument("--dry-run", action="store_true")
        if name == "restore":
            p.add_argument("--backup", required=True, metavar="STAMP")
    p = sub.add_parser("doctor", add_help=False)
    p.add_argument("--target")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("profiles", add_help=False)
    p.add_argument("action", choices=("list", "show"))
    p.add_argument("spec", nargs="?")
    p.add_argument("--agent", choices=("codex", "claude", "both"))
    p = sub.add_parser("capture", add_help=False)
    p.add_argument("--agent", choices=("codex", "claude", "both"), default="both")
    p.add_argument("--write", action="store_true")
    p.add_argument("--json", action="store_true")
    source_cli.add_parser(sub)
    task_cli.add_parser(sub)
    p = sub.add_parser("help", add_help=False)
    p.add_argument("topic", nargs="?")
    sub.add_parser("version", add_help=False)
    return parser


@dataclass
class Ctx:
    command: str
    kit_root: Path
    target: Path
    agents: List[str]
    profile: str = DEFAULT_PROFILE
    policy: Optional[str] = None
    dry_run: bool = False
    verify_only: bool = False
    offline: bool = False
    yes: bool = False
    no_mcp: bool = False
    mcp_opt_in: List[str] = field(default_factory=list)  # --mcp
    plugin_opt_in: List[str] = field(default_factory=list)  # --plugin
    manual: List[str] = field(default_factory=list)  # --manual: guides only (U-23)
    verbose: bool = False
    json: bool = False
    report_json: Optional[Path] = None
    ask: Optional[Callable[[str], str]] = None  # None = not interactive
    scope: str = "project"  # "user": target is the home folder (ADR-018)

    @property
    def user(self) -> bool:
        return self.scope == "user"


def _target(raw: Optional[str], cwd: Path, kit_root: Path, allow_kit: bool = False) -> Path:
    if raw is not None and not raw.strip():
        raise UsageError("--target needs a non-empty directory")
    target = Path(raw) if raw is not None else cwd
    if not target.is_absolute():
        target = cwd / target
    target = target.resolve()
    if not target.is_dir():
        raise TargetError(f"target is not an existing directory: {target}")
    if not allow_kit and target == kit_root.resolve():
        raise TargetError(SELF_TARGET_MSG)
    return target


def detected_agents() -> List[str]:
    return [n for n in registry.names() if shutil.which(registry.get(n).cli)]


def _agents(value: Optional[str]) -> List[str]:
    if value is None:
        found = ", ".join(detected_agents()) or "none"
        raise UsageError(
            f"--agent is required: codex, claude or both (agent CLIs found on this PC: {found})"
        )
    return ["codex", "claude"] if value == "both" else [value]


def _unique(names: List[str]) -> List[str]:
    out: List[str] = []
    for name in names:
        if not name.strip():
            raise UsageError("--mcp/--plugin/--manual need a name")
        if name not in out:
            out.append(name)
    return out


def _ctx(ns: argparse.Namespace, cwd: Path, kit_root: Path) -> Ctx:
    if ns.scope == "user":
        if ns.target is not None:
            raise UsageError("--scope user cannot be combined with --target")
        if getattr(ns, "plugin", []):
            raise UsageError(
                "--plugin is for --scope project; user plugins come from the captured settings"
            )
    if ns.offline and ns.yes:
        raise UsageError("--offline and --yes cannot be combined")
    mcp_opt_in = _unique(getattr(ns, "mcp", []))
    if mcp_opt_in and ns.no_mcp:
        raise UsageError("--mcp and --no-mcp cannot be combined")
    if ns.command == "restore":
        if ns.agent is not None:
            raise UsageError("restore works on a backup, not an agent; drop --agent")
        agents: List[str] = []
    else:
        agents = _agents(ns.agent)
    if ns.scope == "user":
        target = userscope.home()
        if not target.is_dir():
            raise TargetError(f"home folder not found: {target}")
    else:
        target = _target(ns.target, cwd, kit_root)
        if target == userscope.home():
            raise TargetError(
                "target is your home folder; use --scope user for ~/.codex and ~/.claude"
            )
    report_json = None
    if ns.report_json is not None:
        report_json = Path(ns.report_json)
        report_json = report_json if report_json.is_absolute() else cwd / report_json
    return Ctx(
        command=ns.command,
        kit_root=kit_root,
        target=target,
        agents=agents,
        profile=getattr(ns, "profile", DEFAULT_PROFILE),
        policy=getattr(ns, "policy", None),
        dry_run=ns.command == "plan" or getattr(ns, "dry_run", False),
        verify_only=ns.command == "verify",
        offline=ns.offline,
        yes=ns.yes,
        no_mcp=ns.no_mcp,
        mcp_opt_in=mcp_opt_in,
        plugin_opt_in=_unique(getattr(ns, "plugin", [])),
        manual=_unique(getattr(ns, "manual", [])),
        verbose=ns.verbose,
        json=ns.json,
        report_json=report_json,
        scope=ns.scope,
    )


def _adapter(ctx: Ctx, name: str):
    return user_adapters.adapter_for(name, ctx.target) if ctx.user else registry.get(name)


def _confirm_user(ctx: Ctx, plan_text: str) -> None:
    """--scope user writes to the home folder only after --yes or a yes at a terminal."""
    if not ctx.user or ctx.dry_run or ctx.verify_only or ctx.yes:
        return
    if ctx.ask is None:
        raise UsageError(
            f"--scope user changes files in your home folder; run `kit {ctx.command} --scope "
            "user --dry-run` to see them, then re-run with --yes (no terminal to ask)"
        )
    answer = ctx.ask(mask(plan_text) + "\nApply these changes to your home folder? [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        raise UsageError("not confirmed; nothing was written")


# ---------------------------------------------------------------- planning


@dataclass
class AgentPlan:
    adapter: object
    view: profile_resolver.AgentView
    policy_body: str
    include_mcp: bool
    changes: List[FileChange]
    items: List[ItemResult] = field(default_factory=list)
    backups: List[Path] = field(default_factory=list)
    stale: lifecycle.RemovalPlan = field(default_factory=lifecycle.RemovalPlan)
    skill_source: Optional[catalog.SkillSource] = None
    skipped_skills: List[str] = field(default_factory=list)  # "name (why)"
    replaced_skills: List[str] = field(default_factory=list)  # "old -> new"
    skill_warnings: List[str] = field(default_factory=list)  # kit.skill_check warnings
    skipped_mcp: List[str] = field(default_factory=list)  # "name (why)"
    plugins: mcp_catalog.Selection = field(default_factory=mcp_catalog.Selection)
    plugin_items: List[ItemResult] = field(default_factory=list)  # claude plugin install
    plugin_record: List[dict] = field(default_factory=list)  # manifest plugin_installs
    warnings: List[str] = field(default_factory=list)  # e.g. ~/.codex/AGENTS.md size


def _catalog_skills(entries, skills, required, order, agent, policy):
    """Apply the catalog to a profile's skill list for one agent and policy (P4-T4).

    1. A skill this agent/policy cannot have is replaced by an available entry that lists it
       in "replaces" (keeping its place and required flag), or else skipped.
    2. Available entries whose "packs" name a selected profile or pack join the list.
    Returns (skills, required, skipped "name (why)", replaced "old -> new").
    """
    out, req, skipped, replaced = [], [], [], []
    for skill in skills:
        why = entries[skill].available(agent, policy)
        if why:
            sub = next(
                (
                    e.name
                    for e in entries.values()
                    if skill in e.replaces and e.available(agent, policy) is None
                ),
                None,
            )
            if sub is None:
                skipped.append(f"{skill} ({why})")
                continue
            replaced.append(f"{skill} -> {sub}")
            if skill in required:
                req.append(sub)
            skill = sub
        elif skill in required:
            req.append(skill)
        if skill not in out:
            out.append(skill)
    selected = set(order)
    for entry in entries.values():
        if set(entry.packs) & selected and entry.available(agent, policy) is None:
            if entry.name not in out:
                out.append(entry.name)
    return out, req, skipped, replaced


def _plan_agents(
    ctx: Ctx, resolved: profile_resolver.ResolvedProfile, policy: str, state: State
) -> List[AgentPlan]:
    plans = []
    entries = catalog.load(ctx.kit_root, policy)
    guide = policy_render.guide_skills(ctx.kit_root, policy, entries)
    if ctx.command in ("install", "plan"):  # flags; verify/update reuse recorded choices
        mcp_catalog.check_opt_in(
            ctx.kit_root, ctx.mcp_opt_in, ctx.plugin_opt_in, ctx.agents, policy
        )
        _guides(ctx, policy)  # --manual names are checked before anything is written
    for name in ctx.agents:
        adapter = _adapter(ctx, name)
        view = resolved.for_agent(name)
        skills, required, skipped, replaced = _catalog_skills(
            entries, view.profile.skills, view.profile.required_skills, resolved.order, name, policy
        )
        opt_in, not_carried = list(ctx.mcp_opt_in), []
        if ctx.user:  # servers on the captured PC join when the catalog pins them
            known = mcp_catalog.known_names(ctx.kit_root)
            for server in userscope.mcp_names(ctx.kit_root, name):
                if server in known:
                    opt_in.append(server)
                else:
                    not_carried.append(f"{server} (captured; not in catalog/mcp.json, not pinned)")
        servers = mcp_catalog.select_servers(ctx.kit_root, view.profile.mcp, opt_in, name, policy)
        servers.skipped += not_carried
        if ctx.user:
            plugins = mcp_catalog.Selection()
        else:
            plugins = mcp_catalog.select_plugins(ctx.kit_root, [], ctx.plugin_opt_in, name, policy)
        view.profile = replace(
            view.profile,
            skills=skills,
            required_skills=required,
            mcp=mcpconfig.McpSelection(servers.items),
        )
        body = policy_render.render(ctx.kit_root, policy, adapter)
        include_mcp = bool(view.profile.mcp) and not ctx.no_mcp
        source = catalog.source_for(ctx.kit_root, name, policy)
        source.planned = set(skills)
        warnings = []
        for skill in view.profile.skills:
            report = source.check(skill)
            if report.errors:
                raise catalog.CatalogError(
                    f"skill '{skill}' for {name}: " + "; ".join(report.errors)
                )
            warnings += [f"{skill}: {w}" for w in report.warnings]
        changes = adapter.plan(
            ctx.target,
            ctx.kit_root,
            view.profile,
            state,
            include_mcp,
            policy_body=body,
            skill_source=source,
            plugins=plugins.items,
        )
        plan = AgentPlan(adapter, view, body, include_mcp, changes)
        plan.skipped_mcp = servers.skipped
        plan.plugins = plugins
        plan.skill_source = source
        plan.skipped_skills = skipped
        plan.replaced_skills = replaced
        plan.skill_warnings = warnings
        left_out = [s for s in guide if s not in view.profile.skills]
        if left_out:  # P5-T1 8-1: e.g. a pack on its own (--profile hitl)
            plan.warnings.append(
                f"the {policy} policy names skills this install leaves out: "
                f"{', '.join(left_out)}; add --profile core (or a profile that lists them)"
            )
        if ctx.user and name == "codex":
            for change in changes:
                if change.rel == adapter.policy.rel and change.data is not None:
                    size = len(change.data)
                    if size > userscope.AGENTS_MD_WARN:
                        plan.warnings.append(
                            f"~/{change.rel} would be {size:,} bytes; Codex reads 32 KiB by "
                            "default (project_doc_max_bytes)"
                        )
        plans.append(plan)
    seen: Dict[str, str] = {}
    for plan in plans:
        for change in plan.changes:
            other = seen.setdefault(change.rel, plan.adapter.name)
            if other != plan.adapter.name:
                raise UsageError(f"{change.rel} is planned by both {other} and {plan.adapter.name}")
    return plans


def _tool_profile(resolved: profile_resolver.ResolvedProfile, plans: List[AgentPlan]) -> Profile:
    """Tools are per workspace, not per agent: install them once."""
    tools_: List[dict] = []
    mcp = mcpconfig.McpSelection()
    for plan in plans:
        tools_ += [t for t in plan.view.profile.tools if t not in tools_]
        mcp = mcp.merged(plan.view.profile.mcp)
    return Profile(
        resolved.label,
        resolved.description,
        tools=tools_,
        mcp=mcp,
        report_only=resolved.report_only,
    )


@dataclass
class NetworkGate:
    allowed: bool
    reason: str  # --offline | --yes | confirmed | declined | non-interactive | plan only | none
    needs: List[Tuple[str, str]] = field(default_factory=list)  # (for whom, command)

    def to_json(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "needs": [{"for": who, "command": cmd} for who, cmd in self.needs],
        }


SKIP_REASON = {
    "non-interactive": "needs --yes (network)",
    "declined": "network declined",
}


def _network_needs(ctx: Ctx, actions, profile: Profile, plans: List[AgentPlan]) -> list:
    needs = [
        ("tools (user-scope install)", tools.show(a.commands[0]))
        for a in actions
        if a.status == tools.INSTALL
    ]
    if profile.mcp and not ctx.no_mcp and plans:
        for name, entry in mcpconfig.select_servers(ctx.kit_root, profile.mcp):
            agents = [p.adapter.name for p in plans if p.include_mcp and name in p.view.profile.mcp]
            if agents:
                command = tools.show([entry["command"], *entry["args"]])
                needs.append((f"MCP check for {', '.join(agents)}", command))
    if not ctx.verify_only:
        for plan in plans:
            if plan.plugins.items:
                agent = plan.adapter.name
                who = f"{agent} plugins ({plugin_install.USER_CHANGES[agent]})"
                needs.append((who, _plugin_commands(ctx, plan)))
    return needs


def _market(ctx: Ctx) -> str:
    return mcp_catalog.load_plugins(ctx.kit_root)[0]


def _plugin_commands(ctx: Ctx, plan: AgentPlan) -> str:
    agent = plan.adapter.name
    cmds = plugin_install.install_commands(ctx.target, _market(ctx), plan.plugins.names, agent)
    return " && ".join(tools.show(c) for c in cmds)


def _decide(ctx: Ctx, needs: list) -> NetworkGate:
    if ctx.offline:
        return NetworkGate(False, "--offline", needs)
    if not needs:
        return NetworkGate(False, "none", needs)
    if ctx.yes:
        return NetworkGate(True, "--yes", needs)
    if ctx.dry_run:
        return NetworkGate(False, "plan only", needs)
    if ctx.ask is None:
        return NetworkGate(False, "non-interactive", needs)
    listing = "".join(f"\n  - {who}: {cmd}" for who, cmd in needs)
    answer = ctx.ask(f"This will use the network:{listing}\nContinue? [y/N] ")
    ok = answer.strip().lower() in ("y", "yes")
    return NetworkGate(ok, "confirmed" if ok else "declined", needs)


def _without_network(actions):
    return [replace(a, status=tools.OFFLINE) if a.status == tools.INSTALL else a for a in actions]


def _network_lines(gate: NetworkGate, done: bool) -> List[str]:
    head = {
        "--offline": "not used (--offline)",
        "none": "not used",
        "--yes": ("used" if done else "would use") + " (--yes)",
        "confirmed": "used (confirmed)",
        "declined": "not used (declined); these were skipped:",
        "non-interactive": "not used; no terminal to ask, pass --yes to allow:",
        "plan only": "would use (install asks first; --yes skips the question):",
    }[gate.reason]
    lines = [f"Network:      {head}"]
    if gate.reason != "--offline":
        lines += [f"  - {who}: {cmd}" for who, cmd in gate.needs]
    return lines


# ---------------------------------------------------------------- manifest


def _entry(
    plan: AgentPlan, names: List[str], policy: str, stamp: str, target: Path, opt_in: tuple
) -> dict:
    adapter = plan.adapter
    files, blocks, json_keys = [], [], []
    for change in plan.changes:
        if change.outcome == Outcome.CONFLICT:
            continue
        if change.extra_records:
            for key, digest in sorted(change.extra_records.items()):
                path, pointer = key.split("#", 1)
                json_keys.append({"path": path, "pointer": pointer, "sha256": digest})
        elif change.record is None:
            continue
        elif change.rel in (adapter.policy.rel, adapter.mcp_config.rel):
            blocks.append({"path": change.rel, "marker": "hackathon-kit", "sha256": change.record})
        else:
            files.append({"path": change.rel, "sha256": change.record})
    return {
        "agent": adapter.name,
        "profiles": names,
        "policy": policy,
        "installed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": files,
        "blocks": blocks,
        "json_keys": json_keys,
        "manual_steps": adapter.manual_checks(target),
        "backups": [f"{backups_rel(target)}/{stamp}/"] if plan.backups else [],
        # the install's --mcp/--plugin flags, the same for every agent so verify and update
        # check agents installed together as one group
        "opt_in": {"mcp": list(opt_in[0]), "plugins": list(opt_in[1])},
        "plugin_installs": plan.plugin_record,  # what the claude CLI installed (uninstall)
    }


def _manifest_path(ctx: Ctx) -> Path:
    return manifest_mod.manifest_path(ctx.target, ctx.scope)


def _load_manifest(ctx: Ctx) -> manifest_mod.Manifest:
    try:
        return manifest_mod.load(_manifest_path(ctx), ctx.scope)
    except manifest_mod.ManifestError as exc:
        rel = manifest_mod.USER_REL if ctx.user else manifest_mod.PROJECT_REL
        raise TargetError(f"{rel}: {exc}") from None


# ---------------------------------------------------------------- install / plan / verify


def _installed_spec(ctx: Ctx, man: manifest_mod.Manifest, agent: str) -> Optional[tuple]:
    """(profile spec, policy, mcp opt-ins, plugin opt-ins) recorded for an agent.

    v1 state counts for codex.
    """
    entry = man.install_for(agent)
    if entry and entry.get("profiles"):
        opt = entry.get("opt_in") if isinstance(entry.get("opt_in"), dict) else {}
        return (
            ",".join(entry["profiles"]),
            entry.get("policy") or DEFAULT_POLICY,
            tuple(opt.get("mcp") or ()),
            tuple(opt.get("plugins") or ()),
        )
    if agent == "codex" and not ctx.user:
        try:
            data = json.loads((ctx.target / STATE_REL).read_text(encoding="utf-8"))
            if isinstance(data.get("profile"), str):
                # legacy path = restricted (ADR-015)
                return data["profile"], "restricted", (), ()
        except (OSError, ValueError, AttributeError):
            pass
    return None


def _owned_entry(ctx: Ctx, man: manifest_mod.Manifest, agent: str) -> tuple:
    """(manifest entry or None, adoption conflicts). A v1 install is adopted for codex."""
    entry = man.install_for(agent)
    if entry is not None or agent != "codex" or ctx.user:
        return entry, []
    adapter = registry.get(agent)
    blocks = {
        adapter.policy.rel: (adapter.policy.begin, adapter.policy.end),
        adapter.mcp_config.rel: (adapter.mcp_config.begin, adapter.mcp_config.end),
    }
    adoption = manifest_mod.adopt_v1(ctx.target, agent, blocks)
    return adoption.entry, adoption.conflicts


def run_install(ctx: Ctx, out: TextIO) -> int:
    man = _load_manifest(ctx)
    if ctx.command == "uninstall":
        return run_uninstall(ctx, man, out)
    if ctx.verify_only or ctx.command == "update":
        return _run_verify(ctx, man, out)
    resolved = profile_resolver.resolve(ctx.kit_root, ctx.profile, policy_override=ctx.policy)
    policy = resolved.policy or DEFAULT_POLICY
    return _execute(ctx, man, resolved, policy, {a: None for a in ctx.agents}, out)


def _run_verify(ctx: Ctx, man: manifest_mod.Manifest, out: TextIO) -> int:
    """verify and update: use the profile and policy each agent was installed with."""
    missing: Dict[str, Optional[str]] = {}
    specs = {}
    for agent in ctx.agents:
        spec = _installed_spec(ctx, man, agent)
        if spec is None:
            missing[agent] = f"no kit install for {agent} here; run: kit install --agent {agent}"
        else:
            specs[agent] = spec
    if not specs:
        resolved = profile_resolver.resolve(ctx.kit_root, DEFAULT_PROFILE)
        return _execute(ctx, man, resolved, DEFAULT_POLICY, missing, out, plans_for=[])
    # one resolution per group: agents installed with different profiles are checked apart
    groups: Dict[tuple, List[str]] = {}
    for agent, spec in specs.items():
        groups.setdefault(spec, []).append(agent)
    codes = []
    for (spec, policy, mcp, plugins), agents in groups.items():
        resolved = profile_resolver.resolve(ctx.kit_root, spec, policy_override=policy)
        group = replace(ctx, mcp_opt_in=list(mcp), plugin_opt_in=list(plugins))
        codes.append(_execute(group, man, resolved, policy, missing, out, plans_for=agents))
        missing = {}
    return max(codes)


def _execute(
    ctx: Ctx,
    man: manifest_mod.Manifest,
    resolved: profile_resolver.ResolvedProfile,
    policy: str,
    missing: Dict[str, Optional[str]],
    out: TextIO,
    plans_for: Optional[List[str]] = None,
) -> int:
    env = run_preflight(ctx.target)
    state = State.load(ctx.target)
    plan_ctx = ctx if plans_for is None else Ctx(**{**ctx.__dict__, "agents": plans_for})
    plans = _plan_agents(plan_ctx, resolved, policy, state)
    if ctx.command == "update":
        for plan in plans:
            plan.stale = _stale_removal(ctx, man, plan)
    ops = [op for p in plans for op in p.stale.ops]
    forget = [key for p in plans for key in p.stale.forgotten]
    tool_profile = _tool_profile(resolved, plans)
    if ctx.user:  # tools and the MCP handshake are per workspace
        tool_profile = Profile(tool_profile.name, tool_profile.description)
    online = tools.plan_tools(tool_profile, env, ctx.offline, ctx.verify_only)
    gate = _decide(ctx, _network_needs(ctx, online, tool_profile, plans))
    network = gate.allowed
    actions = online if network else _without_network(online)

    if ctx.dry_run:
        text = _dry_run_text(ctx, env, resolved, policy, plans, online, gate)
        data = _dry_json(ctx, resolved, policy, plans)
        data["network"] = gate.to_json()
        return _emit(ctx, out, text, data, EXIT_READY)
    _confirm_user(ctx, _dry_run_text(ctx, env, resolved, policy, plans, online, gate))

    stamp = fresh_stamp(ctx.target)
    extra: List[ItemResult] = []
    for agent, why in missing.items():
        if why:
            extra.append(ItemResult(f"{agent}: install", True, False, False, FAIL, why))
    wrote = False
    if not ctx.verify_only and env.target_writable and plans:
        try:
            backups = apply_all(
                ctx.target,
                [p.changes for p in plans],
                state,
                stamp,
                resolved.label,
                ops=ops,
                forget=forget,
            )
            for plan, made in zip(plans, backups):
                plan.backups = made
            wrote = True
        except TransactionError as exc:
            detail = f"write failed: {exc.cause}; rolled back {len(exc.restored)} file(s)"
            if exc.unrestored:
                detail += f"; could not restore: {', '.join(exc.unrestored)}"
            extra.append(ItemResult(ctx.command, True, False, False, FAIL, detail))
    for plan in plans:
        _plugins(ctx, man, plan, gate, wrote)
    if wrote:
        for plan in plans:
            opt_in = (ctx.mcp_opt_in, ctx.plugin_opt_in)
            man.record(_entry(plan, resolved.names, policy, stamp, ctx.target, opt_in))
        try:
            manifest_mod.save(_manifest_path(ctx), man)
        except OSError as exc:
            extra.append(ItemResult("manifest", False, False, False, FAIL, str(exc)))

    shared_items = tools.run_tools(actions)
    if any(t["kind"] == "node-project" for t in tool_profile.tools):
        shared_items.append(webcheck.check_node_project(ctx.target, env.tools.get("node")))
    if tool_profile.mcp and plans:
        shared_items.extend(
            mcpcheck.check_servers(
                ctx.kit_root,
                tool_profile.mcp,
                env,
                ctx.target,
                not network,
                ctx.no_mcp,
                cli_check=any(p.adapter.mcp_cli_check for p in plans),
            )
        )
    if gate.reason in SKIP_REASON:
        shared_items = [_relabel(i, SKIP_REASON[gate.reason]) for i in shared_items]

    rules = mcp_catalog.allowlist(ctx.kit_root)  # new path: catalog servers are allowed
    for plan in plans:
        adapter = plan.adapter
        plan.items = adapter.verify(
            ctx.target,
            ctx.kit_root,
            plan.view.profile,
            plan.changes,
            not ctx.verify_only,
            env.target_writable,
            plan.include_mcp,
            policy_body=plan.policy_body,
            skill_source=plan.skill_source,
            plugins=plan.plugins.items,
        )
        if not plan.include_mcp:
            stale = adapter.stale_mcp(ctx.target)
            if stale is not None:
                plan.items.append(stale)
        plan.items += plan.plugin_items
        audit = adapter.audit(ctx.target, ctx.kit_root, rules)
        if audit is not None:
            plan.items.append(audit)
        for conflict in plan.stale.conflicts:
            path, _, why = conflict.partition(": ")
            plan.items.append(ItemResult(f"stale:{path}", False, True, False, CONFLICT, why))

    every = extra + shared_items + [i for p in plans for i in p.items]
    status, code = _status(ctx, every)
    text = _report_text(ctx, env, resolved, policy, plans, extra, shared_items, status, gate)
    data = _report_json(ctx, resolved, policy, plans, extra, shared_items, status, code)
    data["network"] = gate.to_json()
    if env.target_writable and not ctx.verify_only:
        try:
            write_log(ctx.target, text, stamp)
        except (OSError, PathEscapeError):
            pass
    return _emit(ctx, out, text, data, code)


def _plugins(ctx: Ctx, man: manifest_mod.Manifest, plan: AgentPlan, gate, wrote: bool) -> None:
    """Install (or, for verify, check) this agent's --plugin choices on this PC."""
    names = plan.plugins.names
    if not names:
        return
    agent = plan.adapter.name
    previous = (man.install_for(plan.adapter.name) or {}).get("plugin_installs") or []
    plan.plugin_record = list(previous)
    if ctx.verify_only:
        plan.plugin_items = plugin_install.verify(ctx.target, _market(ctx), names, agent)
        return
    if not wrote:
        plan.plugin_items = plugin_install.skipped(names, "files were not written")
        return
    if not gate.allowed:
        why = SKIP_REASON.get(gate.reason, "offline (--offline)")
        plan.plugin_items = plugin_install.skipped(names, why)
        return
    outcome = plugin_install.install(ctx.target, _market(ctx), names, agent)
    plan.plugin_items = outcome.items
    if outcome.record:
        done = {r.get("id") for r in outcome.record}
        kept = [r for r in previous[1:] if r.get("id") not in done]
        plan.plugin_record = outcome.record + kept


def _stale_removal(ctx: Ctx, man: manifest_mod.Manifest, plan: AgentPlan):
    """update: kit items recorded before that the current profile no longer installs."""
    entry, _ = _owned_entry(ctx, man, plan.adapter.name)
    if entry is None:
        return lifecycle.RemovalPlan()
    rels = {c.rel for c in plan.changes}
    keys = {k for c in plan.changes for k in (c.extra_records or {})}
    if plan.include_mcp:
        rels.add(plan.adapter.mcp_config.rel)  # partly owned file: compare per key
    stale = lifecycle.stale_part(entry, rels, keys)
    return lifecycle.plan_removal(ctx.target, stale, plan.adapter)


# ---------------------------------------------------------------- uninstall / restore


def _rollback_detail(exc: TransactionError) -> str:
    detail = f"write failed: {exc.cause}; rolled back {len(exc.restored)} file(s)"
    if exc.unrestored:
        detail += f"; could not restore: {', '.join(exc.unrestored)}"
    return detail


def run_uninstall(ctx: Ctx, man: manifest_mod.Manifest, out: TextIO) -> int:
    """Remove manifest-owned items with unchanged content. Backups are kept (P3-T7)."""
    removals: Dict[str, lifecycle.RemovalPlan] = {}
    entries: Dict[str, dict] = {}
    lines = _where(ctx)
    for agent in ctx.agents:
        entry, adoption_conflicts = _owned_entry(ctx, man, agent)
        if entry is None:
            lines.append(f"Agent {agent + ':':<8}nothing installed by the kit")
            continue
        record = entry.get("plugin_installs") or []
        undone: List[str] = []
        if record and ctx.dry_run:
            market = record[0].get("marketplace", "?")
            names = [r["id"].split("@")[0] for r in record[1:] if "id" in r]
            cmds = plugin_install.uninstall_commands(market, names, agent)
            lines += [f"[{agent}] Would run: {tools.show(c)}" for c in cmds]
        elif record:
            undone, problems = plugin_install.uninstall(ctx.target, record, agent)
            adoption_conflicts = adoption_conflicts + problems
        removal = lifecycle.plan_removal(ctx.target, entry, _adapter(ctx, agent))
        removal.conflicts += adoption_conflicts
        if record and not ctx.dry_run:
            lines += [f"[{agent}] Ran: {d}" for d in undone]
            local = plugin_install.LOCAL_SETTINGS_REL
            if record[0].get("created_local_settings") and (
                plugin_install.local_settings_left_empty(ctx.target)
            ):
                removal.ops.append(lifecycle.Op(local, None, "left empty by claude CLI"))
        removals[agent] = removal
        entries[agent] = entry
    ops = [op for r in removals.values() for op in r.ops]
    conflicts = [(a, c) for a, r in removals.items() for c in r.conflicts]
    data = {
        "command": "uninstall",
        "target": str(ctx.target),
        "agents": {
            a: {
                "remove": [op.rel for op in r.ops if op.data is None],
                "rewrite": [op.rel for op in r.ops if op.data is not None],
                "left_in_place": r.conflicts,
            }
            for a, r in removals.items()
        },
    }
    if ctx.dry_run:
        for agent, removal in removals.items():
            lines.append(f"[{agent}] Planned removals:")
            lines += lifecycle.format_ops(removal.ops) or ["  (nothing to remove)"]
            lines += [f"  CONFLICT  {c}" for c in removal.conflicts]
        lines += ["DRY RUN: nothing was written.", ""]
        data["status"] = "DRY RUN"
        return _emit(ctx, out, "\n".join(lines), data, EXIT_READY)
    planned = [f"  REMOVE    {op.rel}" for r in removals.values() for op in r.ops]
    _confirm_user(ctx, "\n".join(lines + planned))

    stamp = fresh_stamp(ctx.target)
    state = State.load(ctx.target)
    forget = [k for r in removals.values() for k in r.forgotten]
    failure = None
    if ops or forget:
        try:
            apply_all(ctx.target, [], state, stamp, "uninstall", ops=ops, forget=forget)
        except TransactionError as exc:
            failure = _rollback_detail(exc)
    if failure is None:
        for agent, removal in removals.items():
            left = lifecycle.remaining(entries[agent], removal)
            if left["files"] or left["blocks"] or left["json_keys"]:
                man.record(left)
            else:
                man.forget(agent)
        if removals:
            manifest_mod.save(_manifest_path(ctx), man)
    for agent, removal in removals.items():
        gone = sum(1 for op in removal.ops if op.data is None)
        edited = len(removal.ops) - gone
        done = "rolled back" if failure else f"removed {gone} file(s), edited {edited}"
        lines.append(f"Agent {agent + ':':<8}{done}; {len(removal.conflicts)} left in place")
    if failure:
        status, code = "BLOCKED", EXIT_BLOCKED
        lines += ["Items:", f"  FAIL       required uninstall  ({failure})"]
    elif conflicts:
        status, code = "BLOCKED", EXIT_BLOCKED
        lines.append("Items:")
        lines += [f"  CONFLICT   [{a}] {c}" for a, c in conflicts]
    else:
        status, code = "READY", EXIT_READY
    if ops and not failure:
        scope = " --scope user" if ctx.user else ""
        lines.append(
            f"Backups:      {backups_rel(ctx.target)}/{stamp}/ "
            f"(kept; kit restore --backup {stamp}{scope})"
        )
    lines.append(f"Status:       {status}")
    if conflicts and not failure:
        lines.append("Next action:")
        lines.append("  - The items above changed after the kit wrote them; remove them by hand.")
    data["status"] = status
    text = "\n".join(lines) + "\n"
    try:
        write_log(ctx.target, text, stamp)
    except (OSError, PathEscapeError):
        pass
    return _emit(ctx, out, text, data, code)


STAMP_RE = re.compile(r"^\d{8}-\d{6}(-\d+)?$")


def run_restore(ctx: Ctx, stamp: str, out: TextIO) -> int:
    """Put back files saved in .kit/backups/<stamp>/. Current versions are backed up first."""
    if not STAMP_RE.match(stamp):
        raise UsageError(f"--backup expects a stamp like 20261105-101200, got '{stamp}'")
    backups = backups_rel(ctx.target)
    root = ctx.target / backups / stamp
    if not root.is_dir():
        found = sorted(p.name for p in (ctx.target / backups).glob("*") if p.is_dir())
        raise TargetError(f"no backup '{stamp}' (available: {', '.join(found) or 'none'})")
    ops: List[lifecycle.Op] = []
    same = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(own_files(ctx.target)):
            continue
        content = path.read_bytes()
        current = safe_path(ctx.target, rel)
        if current.is_file() and current.read_bytes() == content:
            same += 1
            continue
        ops.append(lifecycle.Op(rel, content, f"from backup {stamp}"))
    lines = _where(ctx)[:1] + [f"Backup:       {backups}/{stamp}/"]
    data = {"command": "restore", "backup": stamp, "restore": [op.rel for op in ops]}
    if ctx.dry_run:
        lines.append("Planned restores:")
        lines += [f"  RESTORE   {op.rel}" for op in ops] or ["  (nothing differs)"]
        lines += ["DRY RUN: nothing was written.", ""]
        data["status"] = "DRY RUN"
        return _emit(ctx, out, "\n".join(lines), data, EXIT_READY)
    _confirm_user(ctx, "\n".join(lines + [f"  RESTORE   {op.rel}" for op in ops]))
    new_stamp = fresh_stamp(ctx.target)
    try:
        if ops:
            apply_all(ctx.target, [], State.load(ctx.target), new_stamp, "restore", ops=ops)
    except TransactionError as exc:
        lines += ["Items:", f"  FAIL       required restore  ({_rollback_detail(exc)})"]
        lines.append("Status:       BLOCKED")
        data["status"] = "BLOCKED"
        return _emit(ctx, out, "\n".join(lines) + "\n", data, EXIT_BLOCKED)
    lines.append(f"Restored:     {len(ops)} file(s); {same} already matched")
    if ops:
        lines.append(f"Saved first:  {backups}/{new_stamp}/ (the versions just replaced)")
    lines += [
        "Status:       READY",
        "Next action:",
        "  - Run kit verify --agent codex|claude; restored files may differ from kit records.",
    ]
    data["status"] = "READY"
    return _emit(ctx, out, "\n".join(lines) + "\n", data, EXIT_READY)


def _relabel(item: ItemResult, reason: str) -> ItemResult:
    """Skipped-for-offline items say why the network was not used instead."""
    if item.verified == SKIPPED and item.detail.startswith("offline"):
        detail = reason + item.detail[len("offline") :]
        return ItemResult(
            item.name, item.required, item.installed, item.registered, SKIPPED, detail
        )
    return item


def _status(ctx: Ctx, items: List[ItemResult]) -> tuple:
    if not ctx.verify_only:
        return overall_status(items)
    # verify: 0 all pass, 1 a check failed, 2 cannot check (conflict, nothing installed)
    if any(i.verified == CONFLICT for i in items) or any(
        i.name.endswith(": install") for i in items
    ):
        return "BLOCKED", EXIT_BLOCKED
    if any(i.verified == FAIL for i in items):
        return "PARTIAL", EXIT_PARTIAL
    return "READY", EXIT_READY


# ---------------------------------------------------------------- output


def _emit(ctx: Ctx, out: TextIO, text: str, data: dict, code: int) -> int:
    data["exit_code"] = code
    payload = mask(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    if ctx.json:
        out.write(payload)
    else:
        out.write(mask(text))
    if ctx.report_json is not None:
        try:
            ctx.report_json.parent.mkdir(parents=True, exist_ok=True)
            ctx.report_json.write_text(payload, encoding="utf-8")
        except OSError as exc:
            print(f"warning: cannot write {ctx.report_json}: {exc}", file=sys.stderr)
    return code


def _agent_summary(plan: AgentPlan) -> str:
    adapter = plan.adapter
    by_name = {i.name: i for i in plan.items}
    policy_item = by_name.get(adapter.policy.rel)
    label = "SKIPPED"
    if policy_item is not None:
        label = {PASS: "INSTALLED", CONFLICT: "CONFLICT"}.get(policy_item.verified, "FAILED")
    skills = [i for i in plan.items if i.name.startswith("skill:")]
    ok = sum(1 for i in skills if i.verified == PASS)
    mcp_item = by_name.get("mcp-config") or by_name.get(adapter.mcp_config.rel)
    if not plan.view.profile.mcp:
        mcp = "none"
    elif getattr(adapter, "mcp_manual", False):
        mcp = f"{len(plan.view.profile.mcp)} to add by hand (claude mcp add --scope user)"
    elif not plan.include_mcp:
        mcp = "off (--no-mcp)"
    elif mcp_item is not None and mcp_item.verified == PASS:
        mcp = f"{len(plan.view.profile.mcp)} registered in {adapter.mcp_config.rel}"
    else:
        mcp = f"{mcp_item.verified if mcp_item else 'FAILED'} ({adapter.mcp_config.rel})"
    return (
        f"{adapter.policy.rel} {label} | Skills {ok}/{len(skills)} verified in "
        f"{adapter.skill_root}/ | MCP {mcp} | Load UNVERIFIED (run /skills in "
        f"{adapter.display_name})"
    )


def _choice(name: str, entry: dict) -> str:
    flag = "" if entry["enabled_by_default"] else ", opted in"
    return f"{name} (risk {entry['risk']}{flag}; network: {entry['network_egress']})"


def _catalog_lines(plan: AgentPlan, indent: str) -> List[str]:
    """MCP servers and plugins this agent gets or skips (REQ-SAFE-009)."""
    lines = []
    servers = plan.view.profile.mcp.entries
    if servers and plan.include_mcp:
        lines += [f"{indent}MCP: {_choice(n, e)}" for n, e in servers.items()]
    if plan.skipped_mcp:
        lines.append(f"{indent}Skipped MCP: {', '.join(plan.skipped_mcp)}")
    for name, entry in plan.plugins.items:
        lines.append(f"{indent}Plugin: {_choice(name, entry)}")
    if plan.plugins.skipped:
        lines.append(f"{indent}Skipped plugins: {', '.join(plan.plugins.skipped)}")
    return lines


def _catalog_json(plan: AgentPlan) -> dict:
    def one(name: str, entry: dict) -> dict:
        keys = ("risk", "enabled_by_default", "network_egress", "file_access")
        return {"name": name, **{k: entry[k] for k in keys}}

    servers = plan.view.profile.mcp.entries if plan.include_mcp else {}
    return {
        "mcp_servers": [one(n, e) for n, e in servers.items()],
        "skipped_mcp": plan.skipped_mcp,
        "plugins": [one(n, e) for n, e in plan.plugins.items],
        "skipped_plugins": plan.plugins.skipped,
    }


def _guides(ctx: Ctx, policy: str) -> list:
    return mcp_catalog.select_manual(ctx.kit_root, ctx.manual, ctx.agents, policy)


def _api_needs(ctx: Ctx, policy: str, plans: List[AgentPlan]) -> List[credentials.Need]:
    """P4-T9: keys the selected MCP servers, plugins and skills need; names only."""
    skills = catalog.load(ctx.kit_root, policy)
    found = [("guide", n, "manual", e) for n, e in _guides(ctx, policy)]
    for plan in plans:
        agent = plan.adapter.name
        if plan.include_mcp:
            found += [("MCP", n, agent, e) for n, e in plan.view.profile.mcp.entries.items()]
        found += [("plugin", n, agent, e) for n, e in plan.plugins.items]
        for name in plan.view.profile.skills:
            entry = skills.get(name)
            if entry is not None and entry.credentials:
                found.append(("skill", name, agent, {"credentials": entry.credentials}))
    return credentials.collect(found)


def _where(ctx: Ctx) -> List[str]:
    """R-09: the user scope shows ~ instead of the home path (it holds the user name)."""
    if ctx.user:
        return ["Home:         ~", "Scope:        user"]
    return [f"Target:       {ctx.target}", "Scope:        project"]


def _header(ctx: Ctx, env: EnvReport, resolved, policy: str) -> List[str]:
    lines = [f"Environment:  {env.os} {env.arch}, shell={env.shell}, python {env.python}"]
    lines += _where(ctx)
    lines += [f"Profiles:     {', '.join(resolved.names)}   Policy: {policy}"]
    return lines + [f"Warning:      {w}" for w in resolved.policy_warnings(policy)]


def _dry_run_text(ctx, env, resolved, policy, plans, actions, gate) -> str:
    lines = _header(ctx, env, resolved, policy)
    lines += _network_lines(gate, False)
    for plan in plans:
        lines.append(f"[{plan.adapter.name}] Planned changes:")
        lines.append(format_plan(plan.changes, ctx.verbose))
        if plan.view.skipped:
            lines.append(f"  Skipped (not for {plan.adapter.name}): {', '.join(plan.view.skipped)}")
        if plan.replaced_skills:
            lines.append(f"  Replaced skills ({policy}): {', '.join(plan.replaced_skills)}")
        if plan.skipped_skills:
            lines.append(f"  Skipped skills: {', '.join(plan.skipped_skills)}")
        lines += [f"  Skill warning: {w}" for w in plan.skill_warnings]
        lines += [f"  Warning: {w}" for w in plan.warnings]
        lines += _catalog_lines(plan, "  ")
        if plan.stale.ops or plan.stale.conflicts:
            lines.append(f"[{plan.adapter.name}] No longer in the profile:")
            lines += lifecycle.format_ops(plan.stale.ops)
            lines += [f"  CONFLICT  {c}" for c in plan.stale.conflicts]
    if actions:
        lines += ["Planned tools:", tools.format_tool_plan(actions)]
    lines += mcp_catalog.manual_lines(_guides(ctx, policy))
    lines += credentials.lines(_api_needs(ctx, policy, plans))
    lines += ["DRY RUN: nothing was written.", ""]
    return "\n".join(lines)


def _shown(item: ItemResult, verbose: bool) -> bool:
    return verbose or item.verified in BAD or (item.required and item.verified == UNVERIFIED)


def _report_text(ctx, env, resolved, policy, plans, extra, shared, status, gate) -> str:
    lines = _header(ctx, env, resolved, policy)
    for plan in plans:
        lines.append(f"Agent {plan.adapter.name + ':':<8}{_agent_summary(plan)}")
        if plan.replaced_skills:
            lines.append(f"              replaced skills: {', '.join(plan.replaced_skills)}")
        if plan.skipped_skills:
            lines.append(f"              skipped skills: {', '.join(plan.skipped_skills)}")
        lines += [f"              skill warning: {w}" for w in plan.skill_warnings]
        lines += [f"              warning: {w}" for w in plan.warnings]
        lines += _catalog_lines(plan, " " * 14)
    for item in extra:
        if item.name.endswith(": install"):
            lines.append(f"Agent {item.name.split(':')[0] + ':':<8}not installed")
    lines += _network_lines(gate, True)
    rows = [("", i) for i in extra + shared] + [(p.adapter.name, i) for p in plans for i in p.items]
    shown = [(a, i) for a, i in rows if _shown(i, ctx.verbose)]
    if shown:
        lines.append("Items:")
        for agent, i in shown:
            kind = "required" if i.required else "optional"
            where = f"[{agent}] " if agent else ""
            detail = f"  ({i.detail})" if i.detail else ""
            lines.append(f"  {i.verified:<10} {kind} {where}{i.name}{detail}")
    needs = _api_needs(ctx, policy, plans)
    lines += mcp_catalog.manual_lines(_guides(ctx, policy))
    lines += credentials.lines(needs)
    lines.append(f"Status:       {status}")
    lines.append("Next action:")
    for agent, i in rows:
        where = f"[{agent}] " if agent else ""
        if i.verified == CONFLICT:
            lines.append(f"  - {where}Resolve conflict in {i.name}: {i.detail}. Then re-run.")
        elif i.verified == FAIL:
            lines.append(f"  - {where}Fix {i.name}: {i.detail}. Then re-run.")
    for plan in plans:
        if any(i.verified == SKIPPED for i in plan.plugin_items):
            lines.append(
                f"  - [{plan.adapter.name}] Install plugins: re-run with --yes, or run "
                f"{_plugin_commands(ctx, plan)}"
            )
    missing = credentials.missing_required(needs)
    if missing and status != "BLOCKED":
        lines.append(
            f"  - Set {', '.join(missing)} (see API keys above), open a new terminal and "
            "restart the agent."
        )
    if status != "BLOCKED":
        for plan in plans:
            lines.extend(f"  - {step}" for step in plan.adapter.manual_checks(ctx.target))
    return "\n".join(lines) + "\n"


def _items_json(items: List[ItemResult]) -> List[dict]:
    return [
        {"name": i.name, "required": i.required, "verified": i.verified, "detail": i.detail}
        for i in items
    ]


def _report_json(ctx, resolved, policy, plans, extra, shared, status, code) -> dict:
    return {
        "command": ctx.command,
        "status": status,
        "target": "~" if ctx.user else str(ctx.target),
        "scope": ctx.scope,
        "profiles": resolved.names,
        "policy": policy,
        "policy_warnings": resolved.policy_warnings(policy),
        "agents": {
            p.adapter.name: {
                "policy_file": p.adapter.policy.rel,
                "skill_root": p.adapter.skill_root,
                "mcp_config": p.adapter.mcp_config.rel,
                "skipped_profiles": p.view.skipped,
                "skipped_skills": p.skipped_skills,
                "replaced_skills": p.replaced_skills,
                "skill_warnings": p.skill_warnings,
                "warnings": p.warnings,
                **_catalog_json(p),
                "items": _items_json(p.items),
                "manual_steps": p.adapter.manual_checks(ctx.target),
            }
            for p in plans
        },
        "items": _items_json(extra + shared),
        "api_keys": credentials.to_json(_api_needs(ctx, policy, plans)),
        "manual_guides": mcp_catalog.manual_json(_guides(ctx, policy)),
    }


def _dry_json(ctx, resolved, policy, plans) -> dict:
    return {
        "command": ctx.command,
        "status": "DRY RUN",
        "target": "~" if ctx.user else str(ctx.target),
        "scope": ctx.scope,
        "profiles": resolved.names,
        "policy": policy,
        "policy_warnings": resolved.policy_warnings(policy),
        "agents": {
            p.adapter.name: {
                "changes": [
                    {"path": c.rel, "outcome": c.outcome, "detail": c.detail} for c in p.changes
                ],
                "skipped_profiles": p.view.skipped,
                "skipped_skills": p.skipped_skills,
                "replaced_skills": p.replaced_skills,
                "warnings": p.warnings,
                **_catalog_json(p),
            }
            for p in plans
        },
        "api_keys": credentials.to_json(_api_needs(ctx, policy, plans)),
        "manual_guides": mcp_catalog.manual_json(_guides(ctx, policy)),
    }


# ---------------------------------------------------------------- capture


def run_capture(ns: argparse.Namespace, kit_root: Path, out: TextIO) -> int:
    """ADR-019. Reads the home folder, writes only user/ in the kit, and only with --write."""
    home = userscope.home()
    if not home.is_dir():
        raise TargetError(f"home folder not found: {home}")
    agents = ["codex", "claude"] if ns.agent == "both" else [ns.agent]
    result = capture.capture(kit_root, home, agents)
    rows = capture.changes(kit_root, result, agents)
    blocked = bool(result.hits)
    wrote = ns.write and not blocked
    if wrote:
        capture.write(kit_root, result, agents)
    lines = ["Home:         ~", f"Capture:      {', '.join(agents)} -> user/"]
    lines.append("Files:")
    lines += [f"  {status:<16} {rel}" for rel, status in rows] or ["  (nothing to capture)"]
    if result.notes:
        lines.append("Left out:")
        lines += [f"  - {note}" for note in result.notes]
    if blocked:
        lines.append(f"Secret scan:  {len(result.hits)} hit(s); nothing was written")
        lines += [f"  - {rel}: {label} (line {line})" for rel, label, line in result.hits]
    else:
        lines.append("Secret scan:  clean")
    status = "PARTIAL" if blocked else "READY"
    code = EXIT_PARTIAL if blocked else EXIT_READY
    lines.append(f"Status:       {status}")
    lines.append("Next action:")
    if blocked:
        lines.append(
            "  - Remove the value from the global file or narrow user/capture-allowlist.json."
        )
    elif not ns.write:
        lines.append("  - DRY RUN: nothing was written. Re-run with --write to update user/.")
    else:
        lines.append("  - Review `git diff user/` before committing; the kit never commits.")
    data = {
        "command": "capture",
        "status": status,
        "agents": agents,
        "written": wrote,
        "files": [{"path": rel, "change": change} for rel, change in rows],
        "left_out": result.notes,
        "secret_hits": [{"path": r, "kind": k, "line": n} for r, k, n in result.hits],
        "exit_code": code,
    }
    if ns.json:
        out.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(mask("\n".join(lines) + "\n"))
    return code


# ---------------------------------------------------------------- doctor / profiles


def run_doctor(target: Path, kit_root: Path, as_json: bool, out: TextIO) -> int:
    """Read-only: agent CLIs on PATH and what the kit has put in the target."""
    try:
        man = manifest_mod.load(manifest_mod.manifest_path(target, "project"))
    except manifest_mod.ManifestError as exc:
        raise TargetError(f"{manifest_mod.PROJECT_REL}: {exc}") from None
    agents = {}
    for name in registry.names():
        adapter = registry.get(name)
        skills_dir = target / adapter.skill_root
        policy_file = target / adapter.policy.rel
        has_block = False
        if policy_file.is_file():
            try:
                has_block = adapter.policy.begin in policy_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        agents[name] = {
            "cli": shutil.which(adapter.cli) is not None,
            "policy_block": has_block,
            "skills": sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md")),
            "manifest": man.install_for(name) is not None,
        }
    legacy = (target / STATE_REL).is_file()
    found = [n for n, a in agents.items() if a["cli"]]
    if len(found) == len(agents):
        advice = "kit install --agent both"
    elif found:
        advice = f"kit install --agent {found[0]}"
    else:
        advice = "no agent CLI on PATH; install Codex or Claude Code, then: kit install --agent …"
    if as_json:
        data = {
            "target": str(target),
            "agents": agents,
            "legacy_state": legacy,
            "suggestion": advice,
        }
        out.write(json.dumps(data, indent=2) + "\n")
        return EXIT_READY
    lines = [f"Target:       {target}"]
    for name, a in agents.items():
        adapter = registry.get(name)
        lines.append(
            f"Agent {name + ':':<8}CLI {'found' if a['cli'] else 'not found'} | "
            f"{adapter.policy.rel} kit block {'yes' if a['policy_block'] else 'no'} | "
            f"{len(a['skills'])} skill(s) in {adapter.skill_root}/ | "
            f"manifest {'yes' if a['manifest'] else 'no'}"
        )
    lines.append(f"Legacy state: {'yes (' + STATE_REL + ')' if legacy else 'no'}")
    lines.append(f"Suggestion:   {advice}")
    out.write("\n".join(lines) + "\n")
    return EXIT_READY


def run_profiles(ns: argparse.Namespace, kit_root: Path, out: TextIO) -> int:
    if ns.action == "list":
        if ns.spec is not None or ns.agent is not None:
            raise UsageError("profiles list takes no other arguments")
        lines = []
        for name, kind in profile_resolver.list_entries(kit_root):
            node = profile_resolver.load_node(kit_root, name)
            lines.append(f"  {name:<10} {kind:<8} {node.description}")
        out.write("Profiles and packs:\n" + "\n".join(lines) + "\n")
        return EXIT_READY
    if not ns.spec:
        raise UsageError("profiles show needs a profile, e.g. profiles show core,hitl")
    agents = None if ns.agent in (None, "both") else [ns.agent]
    out.write(profile_resolver.render_show(profile_resolver.resolve(kit_root, ns.spec), agents))
    return EXIT_READY


# ---------------------------------------------------------------- entry


def terminal_ask() -> Optional[Callable[[str], str]]:
    """A prompt on stderr when a person is at a terminal; None otherwise (D-14)."""
    try:
        if not (sys.stdin.isatty() and sys.stderr.isatty()):
            return None
    except (AttributeError, ValueError):
        return None

    def ask(question: str) -> str:
        sys.stderr.write(question)
        sys.stderr.flush()
        try:
            return input()
        except EOFError:
            return ""

    return ask


def run(
    argv: List[str],
    cwd: Path,
    kit_root: Path,
    out: TextIO,
    ask: Optional[Callable[[str], str]] = None,
) -> int:
    command = argv[0]
    try:
        if command in LATER:
            raise UsageError(f"'{command}' is not available yet (added in {LATER[command]})")
        if command in ("help", "version") and len(argv) == 1:
            out.write(HELP if command == "help" else f"kit {manifest_mod.KIT_VERSION}\n")
            return EXIT_READY
        if any(a in ("-h", "--help") for a in argv[1:]):
            out.write(HELP)
            return EXIT_READY
        ns = build_parser().parse_args(argv)
        if command in ("help", "version"):
            raise UsageError(f"{command} takes no arguments")
        if command == "profiles":
            return run_profiles(ns, kit_root, out)
        if command == "doctor":
            return run_doctor(_target(ns.target, cwd, kit_root, True), kit_root, ns.json, out)
        if command == "capture":
            return run_capture(ns, kit_root, out)
        if command == "source":
            return source_cli.run(ns, kit_root, out, ask)
        if command == "task":
            return task_cli.run(ns, cwd, kit_root, out, ask)
        ctx = _ctx(ns, cwd, kit_root)
        ctx.ask = ask
        if ctx.user:
            with user_scope(ctx.target):
                if command == "restore":
                    return run_restore(ctx, ns.backup, out)
                return run_install(ctx, out)
        if command == "restore":
            return run_restore(ctx, ns.backup, out)
        return run_install(ctx, out)
    except UsageError as exc:
        print(f"error: {exc}\nRun `kit help` for usage.", file=sys.stderr)
        return EXIT_USAGE
    except TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TARGET
    except ProfileError as exc:
        print(f"Status:       BLOCKED\nerror: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
