"""Profile v2 resolver for the new CLI path (P3-T5, 04_DESIGN §3.2, prompt §7.4).

The legacy path keeps using kit.profiles.load_profile; this module never changes what it does.

- Files: profiles/<name>.json (profiles) and profiles/packs/<name>.json (packs, "kind": "pack").
- v1 files (no "schema") are normalised: extends "x" -> ["x"], skills/required_skills/mcp
  lists -> {"shared": [...]}, policy null.
- Order: for each requested name, extends left to right depth first, then packs, then the
  profile itself; every profile appears once, at its first position. Lists are unions that
  keep the first position.
- Scalars: two different non-null policies are an error unless the caller passes an override.
  report_only is not inherited (v1 meaning of `full`): it is true when a requested profile
  sets it itself.
- Agents: a profile whose "agents" does not list the target agent contributes nothing for that
  agent; the view reports it as skipped.
- Reference errors (unknown profile, cycle, unknown skill/MCP, scalar conflict) are UsageError
  (exit 64). Malformed kit files are ProfileError (BLOCKED), as on the legacy path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .model import UsageError
from .profiles import KINDS, REQUIRED_TOOL_KEYS, Profile, ProfileError
from .profiles import _validate as _validate_v1

SCHEMA = 2
POLICIES = ("restricted", "standard")
SHARED = "shared"
PER_AGENT_KEYS = ("skills", "required_skills", "mcp")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROFILE_DIR = "profiles"
PACK_DIR = "profiles/packs"
SKILL_DIRS = (".agents/skills", "shared/skills")
V2_KEYS = {
    "schema",
    "name",
    "description",
    "kind",
    "extends",
    "packs",
    "agents",
    "policy",
    "report_only",
    "skills",
    "required_skills",
    "tools",
    "checks",
    "mcp",
    "plugins",
    "recommended_policy",
}


def known_agents() -> List[str]:
    from .adapters import registry  # late import: adapters import plan, which imports profiles

    return registry.names()


@dataclass
class Node:
    """One profile or pack file after normalisation to the v2 shape."""

    name: str
    kind: str  # "profile" | "pack"
    schema: int  # 1 or 2, as read
    description: str
    extends: List[str]
    packs: List[str]
    agents: List[str]
    policy: Optional[str]
    report_only: bool
    skills: Dict[str, List[str]]
    required_skills: Dict[str, List[str]]
    mcp: Dict[str, List[str]]
    tools: List[dict]
    checks: List[dict]
    plugins: Dict[str, List[str]]
    recommended_policy: Optional[str] = None  # warn only (ADR-015), never forced


@dataclass
class AgentView:
    """What one agent gets from a resolved profile. `profile` feeds the adapters."""

    agent: str
    profile: Profile
    policy: Optional[str]
    checks: List[dict]
    plugins: List[str]
    skipped: List[str] = field(default_factory=list)  # profiles that do not list the agent


@dataclass
class ResolvedProfile:
    names: List[str]  # as requested, deduplicated
    order: List[str]  # resolution order
    nodes: Dict[str, Node]
    description: str
    policy: Optional[str]
    report_only: bool

    def policy_warnings(self, policy: str) -> List[str]:
        """ADR-015: a profile may recommend a policy; installing with another one warns."""
        out = []
        for name in self.order:
            wanted = self.nodes[name].recommended_policy
            if wanted and wanted != policy:
                out.append(
                    f"profile '{name}' is meant for --policy {wanted} (installing with {policy}); "
                    f"for an exam or an event with tool rules, re-run with --policy {wanted}"
                )
        return out

    @property
    def label(self) -> str:
        return ",".join(self.names)

    def for_agent(self, agent: str) -> AgentView:
        if agent not in known_agents():
            raise UsageError(f"unknown agent '{agent}' (known: {', '.join(known_agents())})")
        lists: Dict[str, List[str]] = {key: [] for key in PER_AGENT_KEYS}
        tools: List[dict] = []
        checks: List[dict] = []
        plugins: List[str] = []
        skipped: List[str] = []
        for name in self.order:
            node = self.nodes[name]
            if agent not in node.agents:
                skipped.append(name)
                continue
            for key in PER_AGENT_KEYS:
                part = getattr(node, key)
                _extend(lists[key], part.get(SHARED, []) + part.get(agent, []))
            _extend(tools, node.tools)
            _extend(checks, node.checks)
            _extend(plugins, node.plugins.get(agent, []))
        profile = Profile(
            name=self.label,
            description=self.description,
            skills=lists["skills"],
            required_skills=lists["required_skills"],
            tools=tools,
            mcp=lists["mcp"],
            report_only=self.report_only,
        )
        return AgentView(agent, profile, self.policy, checks, plugins, skipped)


def _extend(into: list, items: Iterable) -> None:
    for item in items:
        if item not in into:
            into.append(item)


# ---------------------------------------------------------------- loading


def _check_name(name: str) -> str:
    if not NAME_RE.match(name):
        raise UsageError(f"invalid profile name '{name}' (use lowercase letters, digits and -)")
    return name


def list_entries(kit_root: Path) -> List[Tuple[str, str]]:
    """[(name, kind)] for every profile and pack file, sorted by kind then name."""
    found = [(p.stem, "profile") for p in (kit_root / PROFILE_DIR).glob("*.json")]
    found += [(p.stem, "pack") for p in (kit_root / PACK_DIR).glob("*.json")]
    return sorted(found, key=lambda e: (e[1] != "profile", e[0]))


def _locate(kit_root: Path, name: str) -> Tuple[Path, str]:
    profile = kit_root / PROFILE_DIR / f"{name}.json"
    pack = kit_root / PACK_DIR / f"{name}.json"
    if profile.is_file() and pack.is_file():
        raise ProfileError(f"'{name}' is both a profile and a pack")
    if profile.is_file():
        return profile, "profile"
    if pack.is_file():
        return pack, "pack"
    available = ", ".join(n for n, _ in list_entries(kit_root))
    raise UsageError(f"unknown profile or pack '{name}' (available: {available})")


def load_node(kit_root: Path, name: str) -> Node:
    path, where = _locate(kit_root, _check_name(name))
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProfileError(f"profile '{name}' is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"profile '{name}' must be a JSON object")
    schema = data.get("schema", 1)
    if schema == 1 and "schema" not in data:
        node = _normalise_v1(name, data)
    elif schema == SCHEMA:
        node = _normalise_v2(name, data)
    else:
        raise ProfileError(f"profile '{name}': unsupported schema {schema!r} (this kit reads 2)")
    if node.kind != where:
        raise ProfileError(
            f"'{name}' is in {PACK_DIR if where == 'pack' else PROFILE_DIR}/ "
            f"but declares kind '{node.kind}'"
        )
    if node.kind == "pack" and (node.extends or node.packs):
        raise ProfileError(f"pack '{name}' cannot use extends or packs")
    return node


def _normalise_v1(name: str, data: dict) -> Node:
    _validate_v1(name, data)
    if "kind" in data:
        raise ProfileError(f"profile '{name}': kind needs schema 2")
    extends = data.get("extends")
    return Node(
        name=name,
        kind="profile",
        schema=1,
        description=data.get("description", ""),
        extends=[extends] if extends else [],
        packs=[],
        # 04_DESIGN §3.2 said ["codex"]; corrected in P3-T5 so v1 skills reach every agent.
        agents=known_agents(),
        policy=None,
        report_only=data.get("report_only", False),
        skills={SHARED: list(data.get("skills", []))},
        required_skills={SHARED: list(data.get("required_skills", []))},
        mcp={SHARED: list(data.get("mcp", []))},
        tools=list(data.get("tools", [])),
        checks=[],
        plugins={},
    )


def _names(name: str, key: str, value: object) -> List[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ProfileError(f"profile '{name}': {key} must be a list of names")
    return list(value)


def _per_agent(name: str, key: str, value: object, agents: List[str], shared: bool) -> dict:
    if value is None:
        return {}
    allowed = ([SHARED] if shared else []) + agents
    if not isinstance(value, dict):
        raise ProfileError(f"profile '{name}': {key} must map {'/'.join(allowed)} to lists")
    for sub in value:
        if sub not in allowed:
            raise ProfileError(f"profile '{name}': {key} has unknown section '{sub}'")
    return {sub: _names(name, f"{key}.{sub}", v) for sub, v in value.items()}


def _tools(name: str, value: object) -> List[dict]:
    if not isinstance(value, list):
        raise ProfileError(f"profile '{name}': tools must be a list")
    for tool in value:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise ProfileError(f"profile '{name}': every tool needs a name")
        kind = tool.get("kind")
        if kind not in KINDS:
            raise ProfileError(f"profile '{name}': tool '{tool['name']}' has unknown kind {kind!r}")
        for key in REQUIRED_TOOL_KEYS[kind]:
            if not isinstance(tool.get(key), str):
                raise ProfileError(f"profile '{name}': tool '{tool['name']}' needs {key}")
    return list(value)


def _normalise_v2(name: str, data: dict) -> Node:
    unknown = sorted(set(data) - V2_KEYS)
    if unknown:
        raise ProfileError(f"profile '{name}': unknown field(s) {', '.join(unknown)}")
    if data.get("name", name) != name:
        raise ProfileError(f"profile '{name}': name field says '{data['name']}'")
    kind = data.get("kind", "profile")
    if kind not in ("profile", "pack"):
        raise ProfileError(f"profile '{name}': kind must be profile or pack")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise ProfileError(f"profile '{name}': description must be a string")
    extends = data.get("extends")
    if extends is None:
        extends = []
    elif isinstance(extends, str):
        extends = [extends]
    extends = _names(name, "extends", extends)
    every = known_agents()
    agents = _names(name, "agents", data.get("agents", every))
    for agent in agents:
        if agent not in every:
            raise ProfileError(f"profile '{name}': unknown agent '{agent}'")
    policy = data.get("policy")
    if policy is not None and policy not in POLICIES:
        raise ProfileError(f"profile '{name}': policy must be one of {', '.join(POLICIES)}")
    recommended = data.get("recommended_policy")
    if recommended is not None and recommended not in POLICIES:
        raise ProfileError(
            f"profile '{name}': recommended_policy must be one of {', '.join(POLICIES)}"
        )
    report_only = data.get("report_only", False)
    if not isinstance(report_only, bool):
        raise ProfileError(f"profile '{name}': report_only must be true or false")
    checks = data.get("checks", [])
    if not isinstance(checks, list) or not all(
        isinstance(c, dict) and isinstance(c.get("name"), str) for c in checks
    ):
        raise ProfileError(f"profile '{name}': every check needs a name")
    return Node(
        name=name,
        kind=kind,
        schema=SCHEMA,
        description=description,
        extends=extends,
        packs=_names(name, "packs", data.get("packs", [])),
        agents=agents,
        policy=policy,
        report_only=report_only,
        skills=_per_agent(name, "skills", data.get("skills"), every, True),
        required_skills=_per_agent(
            name, "required_skills", data.get("required_skills"), every, True
        ),
        mcp=_per_agent(name, "mcp", data.get("mcp"), every, True),
        tools=_tools(name, data.get("tools", [])),
        checks=list(checks),
        plugins=_per_agent(name, "plugins", data.get("plugins"), every, False),
        recommended_policy=recommended,
    )


# ---------------------------------------------------------------- resolving


def parse_spec(spec: str) -> List[str]:
    """'core, hitl' -> ['core', 'hitl']; empty parts are an error."""
    parts = [p.strip() for p in spec.split(",")]
    if not spec.strip() or any(not p for p in parts):
        raise UsageError(f"invalid --profile value '{spec}' (expected name[,name…])")
    names: List[str] = []
    _extend(names, (_check_name(p) for p in parts))
    return names


def known_skills(kit_root: Path) -> set:
    """Skill names a profile may use: the catalog when it exists (P4-T1)."""
    if (kit_root / "catalog/skills.json").is_file():
        from . import catalog

        return set(catalog.load(kit_root))
    found = set()
    for rel in SKILL_DIRS:
        root = kit_root / rel
        if root.is_dir():
            found.update(p.parent.name for p in root.glob("*/SKILL.md"))
    return found


def resolve(
    kit_root: Path,
    spec: str,
    policy_override: Optional[str] = None,
    skills: Optional[set] = None,
    mcp: Optional[set] = None,
) -> ResolvedProfile:
    if policy_override is not None and policy_override not in POLICIES:
        raise UsageError(f"--policy must be one of {', '.join(POLICIES)}")
    names = parse_spec(spec)
    nodes: Dict[str, Node] = {}
    order: List[str] = []

    def visit(name: str, stack: List[str]) -> None:
        if name in stack:
            raise UsageError(f"profile cycle: {' -> '.join(stack + [name])}")
        if name in nodes:
            return
        node = load_node(kit_root, name)
        for parent in node.extends:
            visit(parent, stack + [name])
        for pack in node.packs:
            if load_node(kit_root, pack).kind != "pack":
                raise UsageError(f"profile '{name}': '{pack}' in packs is not a pack")
            visit(pack, stack + [name])
        nodes[name] = node
        order.append(name)

    for name in names:
        visit(name, [])

    policy = _policy(order, nodes, policy_override)
    _check_references(kit_root, order, nodes, skills, mcp)
    if len(names) == 1:
        description = nodes[names[0]].description
    else:
        description = " + ".join(names)
    report_only = any(nodes[n].report_only for n in names)
    return ResolvedProfile(names, order, nodes, description, policy, report_only)


def _policy(order: List[str], nodes: Dict[str, Node], override: Optional[str]) -> Optional[str]:
    if override is not None:
        return override
    seen: Dict[str, str] = {}
    for name in order:
        value = nodes[name].policy
        if value is not None and value not in seen:
            seen[value] = name
    if len(seen) > 1:
        parts = ", ".join(f"{who} sets '{value}'" for value, who in seen.items())
        raise UsageError(f"conflicting policy: {parts}; choose one with --policy")
    return next(iter(seen), None)


def _check_references(
    kit_root: Path,
    order: List[str],
    nodes: Dict[str, Node],
    skills: Optional[set],
    mcp: Optional[set],
) -> None:
    skills = known_skills(kit_root) if skills is None else skills
    if mcp is None:
        from . import mcp_catalog  # late: mcp_catalog -> adapters -> plan

        mcp = mcp_catalog.known_names(kit_root)
    for name in order:
        node = nodes[name]
        for key, known, what in (
            ("skills", skills, "skill"),
            ("required_skills", skills, "skill"),
            ("mcp", mcp, "MCP server"),
        ):
            for items in getattr(node, key).values():
                for item in items:
                    if item not in known:
                        raise UsageError(f"profile '{name}': unknown {what} '{item}'")


# ---------------------------------------------------------------- showing


def render_show(
    resolved: ResolvedProfile,
    agents: Optional[List[str]] = None,
    policy: Optional[str] = None,
    skills_for: Optional[Callable[[AgentView], tuple]] = None,
) -> str:
    """Text for `kit profiles show` (REQ-PROF-005). Read-only.

    Without `skills_for` the skills are the profile files' lists. The CLI passes the planner's
    catalog step (B-1): `skills_for(view)` -> (skills, required, skipped, replaced).
    """
    lines = [
        f"Profile: {resolved.label}",
        f"Description: {resolved.description}",
        f"Order: {' -> '.join(resolved.order)}",
        f"Policy: {policy or resolved.policy or 'default'}",
    ]
    if policy is not None:
        lines += [f"Warning: {w}" for w in resolved.policy_warnings(policy)]
    if resolved.report_only:
        lines.append("Report only: yes (installs no tools)")
    for agent in agents or known_agents():
        view = resolved.for_agent(agent)
        profile = view.profile
        skills, required = profile.skills, profile.required_skills
        skipped: List[str] = []
        replaced: List[str] = []
        if skills_for is not None:
            skills, required, skipped, replaced = skills_for(view)
        lines.append("")
        lines.append(f"[{agent}]")
        lines.append(f"  Skills ({len(skills)}): {', '.join(skills) or '-'}")
        lines.append(f"  Required: {', '.join(required) or '-'}")
        lines += [f"  replaced: {r}" for r in replaced]
        lines += [f"  skipped: {s}" for s in skipped]
        lines.append(f"  Tools: {', '.join(t['name'] for t in profile.tools) or '-'}")
        lines.append(f"  MCP: {', '.join(profile.mcp) or '-'}")
        if view.checks:
            lines.append(f"  Checks: {', '.join(c['name'] for c in view.checks)}")
        if view.plugins:
            lines.append(f"  Plugins (declared only): {', '.join(view.plugins)}")
        if view.skipped:
            lines.append(f"  Skipped (not for {agent}): {', '.join(view.skipped)}")
    return "\n".join(lines) + "\n"
