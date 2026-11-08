"""Install the plugins named with --plugin through each agent's own CLI (P4-T5, ADR-010).

Both flows were checked against isolated config folders on 2026-11-06; the real ~/.claude and
~/.codex were not touched.

Claude Code 2.1.319 (CLAUDE_CONFIG_DIR):
- The shell CLI does not register a marketplace that only .claude/settings.json declares (that
  happens inside a session, after the workspace trust dialog): `claude plugin install` alone
  answers "not found in marketplace".
- `claude plugin marketplace add <dir> --scope project` writes the directory as an absolute
  path into the shared .claude/settings.json, so the kit uses `--scope local`
  (.claude/settings.local.json, personal) for this PC and keeps the portable inline "settings"
  marketplace in .claude/settings.json for teammates (kit.adapters.claude).
- Then `claude plugin install <id> --scope project`. Files go to ~/.claude/plugins/.

Codex 0.166.0 (CODEX_HOME):
- `codex plugin` does not see the repo marketplace .agents/plugins/marketplace.json on its own
  (trusted folder and git repository tried). `codex plugin marketplace add <workspace>` reads it
  and records [marketplaces.<name>] in ~/.codex/config.toml (no scope option).
- `codex plugin add <id>` installs to ~/.codex/plugins/cache/ at the pinned sha and writes
  [plugins."<id>"] enabled = true to ~/.codex/config.toml: the plugin is on for every
  project. `codex plugin remove` and `codex plugin marketplace remove` take both entries out.
- A Windows clone failed on the 260-character path limit when CODEX_HOME was a very long path.

Every install is a user-level change, so it runs only behind the network gate (--yes or a
confirmed prompt, ADR-014, R-06). Plugin sources must be full https:// URLs: the owner/repo
shorthand failed to clone with Claude Code.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import tools
from .model import FAIL, PASS, SKIPPED, UNVERIFIED, ItemResult

TIMEOUT = 300.0  # install clones the plugin source
LOCAL_SETTINGS_REL = ".claude/settings.local.json"

# Claude: kit marketplace for this PC (the shared declaration is in .claude/settings.json)
MARKETPLACE_DIR = ".kit/claude-marketplace"
MARKETPLACE_REL = MARKETPLACE_DIR + "/.claude-plugin/marketplace.json"
# Codex: the documented repo marketplace location; `marketplace add <workspace>` reads it
CODEX_MARKETPLACE_REL = ".agents/plugins/marketplace.json"

USER_CHANGES = {
    "claude": f"writes ~/.claude/plugins/, {LOCAL_SETTINGS_REL}",
    "codex": "writes ~/.codex/plugins/ and ~/.codex/config.toml; Codex enables it in every project",
}


def find_claude() -> Optional[str]:
    return shutil.which("claude")


def find_codex() -> Optional[str]:
    return shutil.which("codex")


def find_cli(agent: str) -> Optional[str]:
    return find_codex() if agent == "codex" else find_claude()


def marketplace_rel(agent: str) -> str:
    return CODEX_MARKETPLACE_REL if agent == "codex" else MARKETPLACE_REL


def marketplace_json(market: str, plugins: List[Tuple[str, dict]], agent: str = "claude") -> bytes:
    """The kit marketplace file in the agent's format, with the catalog's pinned sources."""
    if agent == "codex":
        doc = {
            "name": market,
            "interface": {"displayName": "Hackathon kit"},
            "plugins": [
                {
                    "name": n,
                    "source": dict(e["source"]),
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": e.get("category", "Developer Tools"),
                }
                for n, e in plugins
            ],
        }
    else:
        doc = {
            "name": market,
            "owner": {"name": "hackathon-kit"},
            "description": "Plugins the hackathon kit pins to a commit (catalog/plugins.json)",
            "plugins": [{"name": n, "source": dict(e["source"])} for n, e in plugins],
        }
    return (json.dumps(doc, indent=2) + "\n").encode("utf-8")


def plugin_id(name: str, market: str) -> str:
    return f"{name}@{market}"


def install_commands(
    target: Path, market: str, names: List[str], agent: str = "claude"
) -> List[List[str]]:
    """Shown in plan/report; run with the real CLI path."""
    if agent == "codex":
        commands = [["codex", "plugin", "marketplace", "add", str(target), "--json"]]
        commands += [["codex", "plugin", "add", plugin_id(n, market), "--json"] for n in names]
        return commands
    local = ["--scope", "local", "--json"]
    commands = [["claude", "plugin", "marketplace", "add", str(target / MARKETPLACE_DIR), *local]]
    for name in names:
        commands.append(
            ["claude", "plugin", "install", plugin_id(name, market), "--scope", "project", "--json"]
        )
    return commands


def uninstall_commands(market: str, names: List[str], agent: str = "claude") -> List[List[str]]:
    if agent == "codex":
        commands = [["codex", "plugin", "remove", plugin_id(n, market), "--json"] for n in names]
        commands.append(["codex", "plugin", "marketplace", "remove", market, "--json"])
        return commands
    commands = [
        ["claude", "plugin", "uninstall", plugin_id(n, market), "--scope", "project", "--json"]
        for n in names
    ]
    commands.append(
        ["claude", "plugin", "marketplace", "remove", market, "--scope", "local", "--json"]
    )
    return commands


def _result(output: str) -> dict:
    """The JSON object of a `--json` run.

    Claude prints one object on the last line (after any command a marketplace declares);
    Codex prints one indented object.
    """
    lines = output.strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
            except ValueError:
                break
            return data if isinstance(data, dict) else {}
    start = output.find("{")
    if start < 0:
        return {}
    try:
        data, _ = json.JSONDecoder().raw_decode(output[start:])
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _message(result: dict, output: str) -> str:
    if result.get("message"):
        return str(result["message"])
    if result.get("pluginId"):
        version = f" {result['version']}" if result.get("version") else ""
        return f"{result['pluginId']}{version}"
    if result.get("marketplaceName"):
        return f"marketplace {result['marketplaceName']}"
    lines = [ln for ln in output.strip().splitlines() if not ln.startswith("WARNING:")]
    return lines[-1] if lines else "no output"


def _run(exe: str, cmd: List[str], target: Path) -> Tuple[bool, str]:
    code, output = tools.run_command([exe, *cmd[1:]], TIMEOUT, target)
    result = _result(output)
    return code == 0 and result.get("outcome", "ok") == "ok", _message(result, output)


@dataclass
class InstallOutcome:
    items: List[ItemResult] = field(default_factory=list)
    record: List[dict] = field(default_factory=list)  # manifest: what the kit installed


def _label(name: str) -> str:
    return f"plugin:{name}"


def _missing(agent: str) -> str:
    app = "Codex" if agent == "codex" else "Claude Code"
    return f"{agent} CLI not found; install {app}, then re-run with --yes"


def install(target: Path, market: str, names: List[str], agent: str = "claude") -> InstallOutcome:
    out = InstallOutcome()
    if not names:
        return out
    exe = find_cli(agent)
    if exe is None:
        for name in names:
            out.items.append(ItemResult(_label(name), False, False, False, FAIL, _missing(agent)))
        return out
    created_local = agent == "claude" and not (target / LOCAL_SETTINGS_REL).exists()
    commands = install_commands(target, market, names, agent)
    ok, message = _run(exe, commands[0], target)
    if not ok:
        detail = f"marketplace add failed: {message}"
        for name in names:
            out.items.append(ItemResult(_label(name), False, False, False, FAIL, detail))
        return out
    scope = "user" if agent == "codex" else "project"
    for name, cmd in zip(names, commands[1:]):
        ok, message = _run(exe, cmd, target)
        verdict = PASS if ok else FAIL
        out.items.append(ItemResult(_label(name), False, ok, ok, verdict, message))
        if ok:
            out.record.append({"id": plugin_id(name, market), "scope": scope})
    head = {"marketplace": market, "scope": "user" if agent == "codex" else "local"}
    if agent == "claude":
        head["created_local_settings"] = created_local
    out.record.insert(0, head)
    return out


def skipped(names: List[str], reason: str) -> List[ItemResult]:
    return [ItemResult(_label(n), False, False, False, SKIPPED, reason) for n in names]


def _listing(output: str) -> Optional[list]:
    start = min((i for i in (output.find("["), output.find("{")) if i >= 0), default=-1)
    if start < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(output[start:])
    except ValueError:
        return None
    if isinstance(data, dict):  # codex: {"installed": [...], "available": [...]}
        data = data.get("installed")
    return data if isinstance(data, list) else None


def installed(target: Path, agent: str = "claude") -> Optional[Dict[str, dict]]:
    """id -> entry from `<cli> plugin list --json` that applies here; None if unknown."""
    exe = find_cli(agent)
    if exe is None:
        return None
    code, output = tools.run_command([exe, "plugin", "list", "--json"], 60.0, target)
    data = _listing(output) if code == 0 else None
    if data is None:
        return None
    found = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if agent == "codex":
            if entry.get("installed"):
                found[str(entry.get("pluginId"))] = entry
            continue
        if entry.get("scope") != "project":
            continue
        project = entry.get("projectPath")
        if project and Path(project).resolve() != target.resolve():
            continue
        found[str(entry.get("id"))] = entry
    return found


def verify(target: Path, market: str, names: List[str], agent: str = "claude") -> List[ItemResult]:
    seen = installed(target, agent)
    scope = "user, every project" if agent == "codex" else "scope project"
    items = []
    for name in names:
        label = _label(name)
        if seen is None:
            detail = f"cannot read `{agent} plugin list --json`; check the agent's plugin list"
            items.append(ItemResult(label, False, False, False, UNVERIFIED, detail))
            continue
        entry = seen.get(plugin_id(name, market))
        if entry is None:
            detail = "not installed; re-run kit install with --yes"
            items.append(ItemResult(label, False, False, False, FAIL, detail))
        elif not entry.get("enabled"):
            items.append(ItemResult(label, False, True, False, FAIL, "installed but disabled"))
        else:
            detail = f"installed {entry.get('version', '?')} ({scope})"
            items.append(ItemResult(label, False, True, True, PASS, detail))
    return items


def uninstall(
    target: Path, record: List[dict], agent: str = "claude"
) -> Tuple[List[str], List[str]]:
    """Undo what install recorded. Returns (done, problems)."""
    if not record:
        return [], []
    market = record[0].get("marketplace")
    names = [r["id"].split("@")[0] for r in record[1:] if "id" in r]
    exe = find_cli(agent)
    if exe is None or not market:
        cmds = "; ".join(tools.show(c) for c in uninstall_commands(market or "?", names, agent))
        return [], [f"{agent} plugins: {agent} CLI not found; run by hand: {cmds}"]
    done, problems = [], []
    for cmd in uninstall_commands(market, names, agent):
        ok, message = _run(exe, cmd, target)
        (done if ok else problems).append(f"{tools.show(cmd)}: {message}")
    return done, problems


def local_settings_left_empty(target: Path) -> bool:
    """True when .claude/settings.local.json holds only empty objects (what the CLI leaves)."""
    try:
        doc = json.loads((target / LOCAL_SETTINGS_REL).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return isinstance(doc, dict) and all(v == {} for v in doc.values())
