"""MCP server and plugin catalogs for the new path (P4-T5, REQ-SAFE-009, REQ-ARCH-002, ADR-010).

catalog/mcp.json and catalog/plugins.json. The legacy installer never reads them; it keeps
mcp/manifest.json and mcp/allowlist.json (golden tests).

Rules enforced on load (a broken catalog is BLOCKED, like the skill catalog):
- every entry fills enabled_by_default, disabled_reason, network_egress, file_access, risk,
  agents and policies; an entry that is off by default says why
- risk "high" is never on by default
- an installable MCP server is stdio, runs an allowed command (mcp/allowlist.json) and pins an
  exact version that also appears in its args (package@version for npx, package==version
  for uvx); "latest", ranges and missing versions are refused
- a plugin source is pinned to a 40-character commit sha over a full https:// URL and matches
  its sources.lock.json entry; Codex takes url and git-subdir sources (its documented
  sha-pinned types), Claude Code also github

Selection per agent and policy: servers/plugins the profile lists join when they are on by
default; the rest join only when named with --mcp / --plugin. What does not apply is skipped
and reported, never silently dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import credentials, mcpconfig, sources
from .model import UsageError
from .profiles import ProfileError

MCP_REL = "catalog/mcp.json"
PLUGINS_REL = "catalog/plugins.json"
MANUAL_REL = "catalog/manual.json"
MANUAL_REQUIRED = (
    "agents",
    "policies",
    "risk",
    "license",
    "summary",
    "network_egress",
    "file_access",
    "steps",
    "undo",
    "docs",
)
SCHEMA = 1
RISKS = ("low", "medium", "high")
POLICIES = ("restricted", "standard")
REQUIRED = (
    "transport",
    "agents",
    "policies",
    "risk",
    "enabled_by_default",
    "disabled_reason",
    "network_egress",
    "file_access",
)
_VERSION = re.compile(r"^\d+(\.\d+)*([-.+][0-9A-Za-z.-]+)?$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_REMOTE_KEYS = ("url", "headers", "bearer_token_env_var", "type")
_SECRETISH = re.compile(r"(?i)(TOKEN|SECRET|API_KEY|PASSWORD)")
PLUGIN_AGENTS = ("claude", "codex")  # kit.plugin_install
# plugin source types each agent documents with a sha pin; github is Claude-only
PLUGIN_SOURCES = {"claude": ("github", "url", "git-subdir"), "codex": ("url", "git-subdir")}


class CatalogError(ProfileError):
    """catalog/mcp.json or catalog/plugins.json is malformed (BLOCKED)."""


@dataclass
class Selection:
    """What one agent gets: (name, entry) in order, plus skipped 'name (why)'."""

    items: List[Tuple[str, dict]] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def names(self) -> List[str]:
        return [n for n, _ in self.items]


def _read(kit_root: Path, rel: str) -> dict:
    try:
        data = json.loads((kit_root / rel).read_bytes().decode("utf-8"))
    except FileNotFoundError:
        raise CatalogError(f"{rel} is missing") from None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CatalogError(f"{rel} is not valid JSON: {exc}") from None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise CatalogError(f"{rel}: expected an object with schema {SCHEMA}")
    return data


def _names(where: str, key: str, value: object, allowed: Sequence[str]) -> None:
    if not isinstance(value, list) or not value or not all(v in allowed for v in value):
        raise CatalogError(f"{where}: {key} must be a non-empty list from {', '.join(allowed)}")


def _common(where: str, entry: dict, agents: Sequence[str]) -> None:
    missing = [k for k in REQUIRED if k not in entry]
    if missing:
        raise CatalogError(f"{where}: missing {', '.join(missing)}")
    _names(where, "agents", entry["agents"], agents)
    _names(where, "policies", entry["policies"], POLICIES)
    if entry["risk"] not in RISKS:
        raise CatalogError(f"{where}: risk must be one of {', '.join(RISKS)}")
    on = entry["enabled_by_default"]
    if not isinstance(on, bool):
        raise CatalogError(f"{where}: enabled_by_default must be true or false")
    if on and entry["risk"] == "high":
        raise CatalogError(f"{where}: a high-risk entry cannot be enabled by default")
    reason = entry["disabled_reason"]
    if on and reason is not None:
        raise CatalogError(f"{where}: disabled_reason must be null when enabled by default")
    if not on and not (isinstance(reason, str) and reason.strip()):
        raise CatalogError(f"{where}: an entry that is off by default needs a disabled_reason")
    for key in ("network_egress", "file_access"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise CatalogError(f"{where}: {key} must describe the access")
    try:
        needs = credentials.parse(where, entry.get("credentials"))
    except credentials.CredentialError as exc:
        raise CatalogError(str(exc)) from None
    if needs and on:
        raise CatalogError(f"{where}: an entry that needs API keys stays off by default (P4-T9)")


def installable(entry: dict) -> bool:
    return "command" in entry


def _check_server(where: str, entry: dict, commands: Sequence[str]) -> None:
    if entry["transport"] != "stdio":
        raise CatalogError(f"{where}: only stdio servers are allowed (remote is refused)")
    for key in _REMOTE_KEYS:
        if key in entry:
            raise CatalogError(f"{where}: key '{key}' is not allowed (remote transport)")
    for name in entry.get("env", []):
        if not isinstance(name, str) or (_SECRETISH.search(name) and entry["risk"] != "high"):
            raise CatalogError(f"{where}: env '{name}' looks like a secret; mark the risk high")
    if not installable(entry):
        if entry["enabled_by_default"]:
            raise CatalogError(f"{where}: a listed-only server cannot be enabled by default")
        return
    if entry["command"] not in commands:
        raise CatalogError(f"{where}: command '{entry['command']}' is not in mcp/allowlist.json")
    args = entry.get("args")
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise CatalogError(f"{where}: args must be a list of strings")
    version, package = entry.get("version"), entry.get("package")
    if not isinstance(version, str) or not _VERSION.match(version):
        raise CatalogError(f"{where}: version must be pinned exactly (no latest, ^, ~ or ranges)")
    pinned = f"{package}=={version}" if entry["command"] == "uvx" else f"{package}@{version}"
    if pinned not in args:
        raise CatalogError(f"{where}: args must run the pinned '{pinned}'")
    timeout = entry.get("startup_timeout_sec", 30)
    if not isinstance(timeout, int) or not 1 <= timeout <= 600:
        raise CatalogError(f"{where}: startup_timeout_sec must be 1-600")


def _agents() -> List[str]:
    from .adapters import registry  # late import (adapters import plan)

    return registry.names()


def load_servers(kit_root: Path) -> Dict[str, dict]:
    data = _read(kit_root, MCP_REL)
    servers = data.get("servers")
    if not isinstance(servers, dict):
        raise CatalogError(f"{MCP_REL}: servers must be an object")
    commands = mcpconfig.load_allowlist(kit_root)["commands"]
    agents = _agents()
    for name, entry in servers.items():
        where = f"{MCP_REL} '{name}'"
        if not re.match(r"^[A-Za-z0-9_-]+$", name) or not isinstance(entry, dict):
            raise CatalogError(f"{where}: bad name or entry")
        _common(where, entry, agents)
        _check_server(where, entry, commands)
    pinned = {n: e for n, e in servers.items() if "source" in e}
    if pinned:
        lock = sources.load(kit_root)
        for name, entry in pinned.items():
            src = lock.get(entry["source"])
            where = f"{MCP_REL} '{name}'"
            if src is None or src.kind != "mcp":
                raise CatalogError(f"{where}: source '{entry['source']}' is not an mcp lock entry")
            if installable(entry) and src.raw.get("version") != entry["version"]:
                raise CatalogError(f"{where}: version differs from {sources.LOCK_REL}")
    return servers


def load_plugins(kit_root: Path) -> Tuple[str, Dict[str, dict]]:
    data = _read(kit_root, PLUGINS_REL)
    market, plugins = data.get("marketplace"), data.get("plugins")
    if not isinstance(market, str) or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", market):
        raise CatalogError(f"{PLUGINS_REL}: marketplace must be a kebab-case name")
    if not isinstance(plugins, dict):
        raise CatalogError(f"{PLUGINS_REL}: plugins must be an object")
    for name, entry in plugins.items():
        where = f"{PLUGINS_REL} '{name}'"
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or not isinstance(entry, dict):
            raise CatalogError(f"{where}: bad name or entry")
        _common(where, {"transport": "plugin", **entry}, _agents())
        unsupported = [a for a in entry["agents"] if a not in PLUGIN_AGENTS]
        if unsupported:
            raise CatalogError(f"{where}: plugins for {', '.join(unsupported)} are not supported")
        source = entry.get("source")
        kind = source.get("source") if isinstance(source, dict) else None
        if kind not in ("github", "url", "git-subdir"):
            raise CatalogError(f"{where}: source must be a github, url or git-subdir object")
        for agent in entry["agents"]:
            if kind not in PLUGIN_SOURCES[agent]:
                raise CatalogError(f"{where}: {agent} does not take a '{kind}' plugin source")
        if not isinstance(source.get("sha"), str) or not _SHA.match(source["sha"]):
            raise CatalogError(f"{where}: source must be pinned to a 40-character sha")
        if not isinstance(entry.get("category", ""), str):
            raise CatalogError(f"{where}: category must be text")
        url = "https://github.com/" if kind == "github" else source.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            # owner/repo shorthand failed to clone with Claude Code 2.1.319 (kit.plugin_install)
            raise CatalogError(f"{where}: source url must be a full https:// URL")
    lock = sources.load(kit_root) if plugins else {}
    for name, entry in plugins.items():
        lock_id = entry.get("lock", name)  # the lock entry, when its id is not the plugin name
        src = lock.get(lock_id)
        where = f"{PLUGINS_REL} '{name}'"
        if src is None or src.kind != "plugin":
            raise CatalogError(f"{where}: no plugin entry '{lock_id}' in {sources.LOCK_REL}")
        if src.commit != entry["source"]["sha"]:
            raise CatalogError(f"{where}: sha differs from {sources.LOCK_REL}")
    return market, plugins


def _why_not(entry: dict, agent: str, policy: str) -> Optional[str]:
    if agent not in entry["agents"]:
        return f"not for {agent}"
    if policy not in entry["policies"]:
        return f"not in the {policy} policy"
    return None


def _select(
    catalog: Dict[str, dict],
    listed: Sequence[str],
    opt_in: Sequence[str],
    agent: str,
    policy: str,
    flag: str,
    need_installable: bool,
) -> Selection:
    sel = Selection()
    for name in list(listed) + [n for n in opt_in if n not in listed]:
        entry = catalog.get(name)
        if entry is None:
            raise UsageError(f"unknown {flag[2:]} '{name}' (see {CATALOG_FILE[flag]})")
        why = _why_not(entry, agent, policy)
        if why is None and need_installable and not installable(entry):
            why = "listed only: " + entry["disabled_reason"]
        if why is None and not entry["enabled_by_default"] and name not in opt_in:
            why = f"off by default; add {flag} {name}"
        if why:
            sel.skipped.append(f"{name} ({why})")
        else:
            sel.items.append((name, entry))
    return sel


# the file each opt-in flag names (P7-T1: --plugin pointed at a plugin.json that does not exist)
CATALOG_FILE = {"--mcp": "catalog/mcp.json", "--plugin": "catalog/plugins.json"}


def select_servers(
    kit_root: Path, listed: Sequence[str], opt_in: Sequence[str], agent: str, policy: str
) -> Selection:
    return _select(load_servers(kit_root), listed, opt_in, agent, policy, "--mcp", True)


def select_plugins(
    kit_root: Path, listed: Sequence[str], opt_in: Sequence[str], agent: str, policy: str
) -> Selection:
    _, plugins = load_plugins(kit_root)
    return _select(plugins, listed, opt_in, agent, policy, "--plugin", False)


def check_opt_in(kit_root: Path, mcp: Sequence[str], plugins: Sequence[str], agents, policy):
    """--mcp/--plugin names that no selected agent can take are usage errors (64)."""
    servers = load_servers(kit_root)
    _, known_plugins = load_plugins(kit_root)
    for flag, names, catalog in (("--mcp", mcp, servers), ("--plugin", plugins, known_plugins)):
        for name in names:
            entry = catalog.get(name)
            if entry is None:
                raise UsageError(f"unknown {flag[2:]} '{name}' (see {CATALOG_FILE[flag]})")
            if flag == "--mcp" and not installable(entry):
                raise UsageError(f"MCP server '{name}' is listed only: {entry['disabled_reason']}")
            reasons = [_why_not(entry, a, policy) for a in agents]
            if all(reasons):
                raise UsageError(f"{flag} {name}: {'; '.join(r for r in reasons if r)}")


def allowlist(kit_root: Path) -> dict:
    """mcp/allowlist.json rules with the catalog's installable servers (new-path audit)."""
    rules = dict(mcpconfig.load_allowlist(kit_root))
    servers = load_servers(kit_root)
    rules["servers"] = sorted(n for n, e in servers.items() if installable(e))
    # P4-T9: key names a server declares may appear as references (never values)
    rules["declared_env"] = {
        n: credentials.names(e) for n, e in servers.items() if e.get("credentials")
    }
    return rules


def known_names(kit_root: Path) -> set:
    """Server names a v2 profile may list."""
    if not (kit_root / MCP_REL).is_file():
        return set(mcpconfig.load_allowlist(kit_root)["servers"])
    return set(load_servers(kit_root))


# ---------------------------------------------------------------- manual guides (U-23)


def load_manual(kit_root: Path) -> Dict[str, dict]:
    """catalog/manual.json: tools the kit only explains (never runs). Missing file = none."""
    if not (kit_root / MANUAL_REL).is_file():
        return {}
    tools_ = _read(kit_root, MANUAL_REL).get("tools")
    if not isinstance(tools_, dict):
        raise CatalogError(f"{MANUAL_REL}: tools must be an object")
    agents = _agents()
    for name, entry in tools_.items():
        where = f"{MANUAL_REL} '{name}'"
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or not isinstance(entry, dict):
            raise CatalogError(f"{where}: bad name or entry")
        missing = [k for k in MANUAL_REQUIRED if k not in entry]
        if missing:
            raise CatalogError(f"{where}: missing {', '.join(missing)}")
        _names(where, "agents", entry["agents"], agents)
        _names(where, "policies", entry["policies"], POLICIES)
        if entry["risk"] not in RISKS:
            raise CatalogError(f"{where}: risk must be one of {', '.join(RISKS)}")
        for key in ("steps", "undo"):
            value = entry[key]
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(v, str) and v.strip() for v in value)
            ):
                raise CatalogError(f"{where}: {key} must be a non-empty list of text")
        if not isinstance(entry["docs"], str) or not entry["docs"].startswith("https://"):
            raise CatalogError(f"{where}: docs must be an https:// page")
        try:
            credentials.parse(where, entry.get("credentials"))
        except credentials.CredentialError as exc:
            raise CatalogError(str(exc)) from None
    return tools_


def select_manual(kit_root: Path, names: Sequence[str], agents, policy: str):
    """--manual names -> [(name, entry)]; unknown or unusable names are usage errors (64)."""
    if not names:
        return []
    guides = load_manual(kit_root)
    out = []
    for name in names:
        entry = guides.get(name)
        if entry is None:
            raise UsageError(f"unknown manual guide '{name}' (see {MANUAL_REL})")
        reasons = [_why_not(entry, a, policy) for a in agents]
        if all(reasons):
            raise UsageError(f"--manual {name}: {'; '.join(r for r in reasons if r)}")
        out.append((name, entry))
    return out


def manual_lines(guides) -> List[str]:
    if not guides:
        return []
    lines = ["Manual guides (the kit runs none of this; you decide and run it):"]
    for name, e in guides:
        lines.append(
            f"  {name} {e.get('version', '')}".rstrip() + f" (risk {e['risk']}, "
            f"{e['license']}): {e['summary']}"
        )
        lines.append(f"    network:  {e['network_egress']}")
        lines.append(f"    files:    {e['file_access']}")
        lines += [f"    {i}. {step}" for i, step in enumerate(e["steps"], 1)]
        lines.append(f"    undo:     {'; '.join(e['undo'])}")
        lines.append(f"    docs:     {e['docs']}")
    return lines


def manual_json(guides) -> List[dict]:
    keys = (
        "version",
        "risk",
        "license",
        "summary",
        "network_egress",
        "file_access",
        "steps",
        "undo",
        "docs",
    )
    return [{"name": n, **{k: e.get(k) for k in keys}} for n, e in guides]


# ---------------------------------------------------------------- Claude Code declaration


def claude_settings_keys(market: str, plugins: List[Tuple[str, dict]]) -> Dict[str, object]:
    """JSON pointer -> value the kit owns in .claude/settings.json (ADR-010, D-05)."""
    if not plugins:
        return {}
    keys: Dict[str, object] = {
        f"/extraKnownMarketplaces/{market}": {
            "source": {
                "source": "settings",
                "name": market,
                "plugins": [{"name": n, "source": dict(e["source"])} for n, e in plugins],
            }
        }
    }
    for name, _ in plugins:
        keys[f"/enabledPlugins/{name}@{market}"] = True
    return keys
