"""API keys the user sets later (P4-T9, 00_PROMPT §15: names only, never values).

A catalog entry (catalog/mcp.json server, catalog/plugins.json plugin, catalog/skills.json skill)
may list the keys it needs:

    "credentials": [{"env": "CONTEXT7_API_KEY", "required": false,
                     "purpose": "higher rate limits", "get_it": "https://...", "cost": "free tier"}]

The kit never asks for, reads out, writes or logs a key value. Config files get references only:
Codex `env_vars = ["NAME"]` (passed through from the shell), Claude `.mcp.json`
`"env": {"NAME": "${NAME}"}`. Plan, install and verify print one "API keys" section with where to
create each key and how to set it; whether it is set is checked by name in this process's
environment. Entries with credentials stay off by default (opt in with --mcp/--plugin/a pack).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_URL = re.compile(r"^https://[^\s]+$")
_FIELDS = {"env", "required", "purpose", "get_it", "cost"}


class CredentialError(ValueError):
    pass


def parse(where: str, value: object) -> List[dict]:
    """Validate a catalog "credentials" list; returns it unchanged."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise CredentialError(f"{where}: credentials must be a list")
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            raise CredentialError(f"{where}: each credential must be an object")
        unknown = sorted(set(item) - _FIELDS)
        if unknown:
            raise CredentialError(f"{where}: unknown credential field(s) {', '.join(unknown)}")
        env = item.get("env")
        if not isinstance(env, str) or not ENV_RE.match(env):
            raise CredentialError(f"{where}: credential env must be an UPPER_SNAKE name")
        if env in seen:
            raise CredentialError(f"{where}: credential {env} listed twice")
        seen.add(env)
        if not isinstance(item.get("required"), bool):
            raise CredentialError(f"{where}: {env}: required must be true or false")
        if not isinstance(item.get("purpose"), str) or not item["purpose"].strip():
            raise CredentialError(f"{where}: {env}: purpose is required")
        if not isinstance(item.get("get_it"), str) or not _URL.match(item["get_it"]):
            raise CredentialError(f"{where}: {env}: get_it must be an https:// page")
        if "cost" in item and not (isinstance(item["cost"], str) and item["cost"].strip()):
            raise CredentialError(f"{where}: {env}: cost must be text")
    return list(value)


def names(entry: dict) -> List[str]:
    return [c["env"] for c in entry.get("credentials") or []]


def is_set(env: str) -> bool:
    return bool(os.environ.get(env, "").strip())


@dataclass
class Need:
    env: str
    required: bool
    purpose: str
    get_it: str
    cost: Optional[str] = None
    used_by: List[str] = field(default_factory=list)  # "MCP context7 (codex, claude)"

    @property
    def set(self) -> bool:
        return is_set(self.env)


def collect(found: List[tuple]) -> List[Need]:
    """found: (kind, name, agent, entry). One Need per env name, users merged."""
    needs: Dict[str, Need] = {}
    users: Dict[str, Dict[str, List[str]]] = {}
    for kind, name, agent, entry in found:
        for c in entry.get("credentials") or []:
            need = needs.get(c["env"])
            if need is None:
                need = needs[c["env"]] = Need(
                    c["env"], c["required"], c["purpose"], c["get_it"], c.get("cost")
                )
            need.required = need.required or c["required"]
            agents = users.setdefault(c["env"], {}).setdefault(f"{kind} {name}", [])
            if agent not in agents:
                agents.append(agent)
    for env, need in needs.items():
        need.used_by = [f"{who} ({', '.join(a)})" for who, a in users[env].items()]
    return [needs[k] for k in sorted(needs)]


def lines(needs: List[Need]) -> List[str]:
    if not needs:
        return []
    out = ["API keys (set later; the kit never asks for, stores or prints a key):"]
    for n in needs:
        state = "set" if n.set else "not set"
        kind = "required" if n.required else "optional"
        out.append(f"  {n.env}  [{kind}, {state}]  {n.purpose}")
        out.append(f"    used by:  {'; '.join(n.used_by)}")
        out.append(f"    get it:   {n.get_it}" + (f"  ({n.cost})" if n.cost else ""))
        out.append(
            f'    set it:   PowerShell  [Environment]::SetEnvironmentVariable("{n.env}", '
            '"<your key>", "User")'
        )
        out.append(
            f'              bash/zsh    add  export {n.env}="<your key>"  to ~/.bashrc or ~/.zshrc'
        )  # noqa: E501
    out.append(
        "  Then open a new terminal and restart the agent; `kit verify` shows set / not set."
    )
    return out


def to_json(needs: List[Need]) -> List[dict]:
    return [
        {
            "env": n.env,
            "required": n.required,
            "set": n.set,
            "purpose": n.purpose,
            "get_it": n.get_it,
            "cost": n.cost,
            "used_by": n.used_by,
        }
        for n in needs
    ]


def missing_required(needs: List[Need]) -> List[str]:
    return [n.env for n in needs if n.required and not n.set]
