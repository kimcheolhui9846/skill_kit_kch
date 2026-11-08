"""Claude Code adapter, project scope only (P3-T4, 02 matrix CC-MEM/CC-SK/CC-MCP).

Writes CLAUDE.md (kit block), .claude/skills/<name>/ and .mcp.json (kit-owned keys).
With --plugin, also declares plugins in .claude/settings.json (kit-owned keys, ADR-010):
extraKnownMarketplaces/<kit marketplace> and enabledPlugins/<plugin>@<kit marketplace>.
The plugin itself is installed on this PC by kit.plugin_install (claude CLI, behind the
network gate); teammates get the declaration and install it inside Claude Code.
Never writes ~/.claude/... or .claude/settings.local.json (personal file).

Policy text: until the policy renderer exists (P4-T6, ADR-004) the CLAUDE.md block carries the
same kit policy text as the AGENTS.md block. Claude Code stops reading AGENTS.md once
CLAUDE.md exists (CC-MEM), so the policy has to be in CLAUDE.md itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .. import approval_hooks, mcp_catalog, plugin_install, subagents
from ..audit import audit_mcp_json
from ..fsops import State
from ..mcpjson import plan_mcp_json, plan_owned_keys, verify_mcp_json, verify_owned_keys
from ..model import FAIL, PASS, ItemResult, Outcome
from ..plan import FileChange, plan_changes, plan_file
from ..profiles import Profile
from ..verify import verify_target
from ..writers import markdown_block
from .base import BlockTarget

SETTINGS_REL = ".claude/settings.json"
PLUGIN_OWNER = "plugin-config"
PLUGIN_NOTE = "declared for everyone who clones the project; it loads after the folder is trusted"


def _mcp_conflict(changes: List[FileChange], owner: str = "mcp-config") -> Optional[str]:
    for change in changes:
        if change.owner == owner and change.outcome == Outcome.CONFLICT:
            return f"{change.rel}: {change.detail}"
    return None


def _plugin_keys(kit_root: Path, plugins) -> dict:
    if not plugins:
        return {}
    market, _ = mcp_catalog.load_plugins(kit_root)
    return mcp_catalog.claude_settings_keys(market, list(plugins))


def _marketplace_file(kit_root: Path, plugins) -> bytes:
    market, _ = mcp_catalog.load_plugins(kit_root)
    return plugin_install.marketplace_json(market, list(plugins))


def _verify_marketplace(target: Path, kit_root: Path, plugins) -> ItemResult:
    label = plugin_install.MARKETPLACE_REL
    try:
        data = (target / label).read_bytes()
    except OSError:
        return ItemResult(label, False, False, False, FAIL, "missing")
    if data != _marketplace_file(kit_root, plugins):
        return ItemResult(label, False, True, False, FAIL, "outdated")
    return ItemResult(label, False, True, True, PASS, "kit marketplace for this PC")


def declared_plugins(target: Path) -> List[str]:
    """plugin@marketplace ids enabled in the project settings for the kit marketplace."""
    try:
        doc = json.loads((target / SETTINGS_REL).read_bytes().decode("utf-8"))
        enabled = doc.get("enabledPlugins") or {}
        known = doc.get("extraKnownMarketplaces") or {}
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return []
    if not isinstance(enabled, dict) or not isinstance(known, dict):
        return []
    return sorted(k for k, v in enabled.items() if v is True and k.split("@")[-1] in known)


def _subagents(profile: Profile, skill_source) -> List[str]:
    policy = getattr(skill_source, "policy", None)
    return subagents.wanted(profile.skills, policy)


class ClaudeAdapter:
    name = "claude"
    display_name = "Claude Code"
    cli = "claude"
    mcp_cli_check = False  # approval happens inside Claude Code (/mcp)
    policy = BlockTarget("CLAUDE.md", markdown_block.BEGIN, markdown_block.END)
    skill_root = ".claude/skills"
    mcp_config = BlockTarget(".mcp.json", "", "")  # JSON: owned keys, no markers
    plugin_config = SETTINGS_REL

    def plan(
        self,
        target: Path,
        kit_root: Path,
        profile: Profile,
        state: State,
        include_mcp: bool,
        policy_body: Optional[str] = None,
        skill_source=None,
        plugins=None,
        hooks: bool = False,
    ) -> List[FileChange]:
        changes = plan_changes(
            target,
            kit_root,
            profile,
            state,
            include_mcp=False,
            policy_rel=self.policy.rel,
            skill_root=self.skill_root,
            policy_body=policy_body,
            skill_source=skill_source,
        )
        if include_mcp and profile.mcp:
            changes.append(plan_mcp_json(target, kit_root, profile.mcp, state))
        keys = _plugin_keys(kit_root, plugins)
        hook_keys = approval_hooks.keys(self.name) if hooks else {}
        if keys or hook_keys:  # one change per file: plugin and hook keys share settings.json
            owner = PLUGIN_OWNER if keys else approval_hooks.OWNER
            merged = {**keys, **hook_keys}
            changes.append(plan_owned_keys(target, SETTINGS_REL, owner, merged, state))
        if keys:
            data = _marketplace_file(kit_root, plugins)
            rel = plugin_install.MARKETPLACE_REL
            changes.append(plan_file(target, rel, PLUGIN_OWNER, data, state))
        if hooks and approval_hooks.conflict_in(changes, SETTINGS_REL) is None:
            changes.append(approval_hooks.plan_script(target, kit_root, self.name, state))
        changes += subagents.plan(target, kit_root, _subagents(profile, skill_source), state)
        return changes

    def verify(
        self,
        target: Path,
        kit_root: Path,
        profile: Profile,
        changes: List[FileChange],
        check_writable: bool,
        writable: bool,
        include_mcp: bool,
        policy_body: Optional[str] = None,
        skill_source=None,
        plugins=None,
        hooks: bool = False,
    ) -> List[ItemResult]:
        items = verify_target(
            target,
            kit_root,
            profile,
            changes,
            check_writable,
            writable,
            include_mcp=False,
            policy_rel=self.policy.rel,
            skill_root=self.skill_root,
            policy_body=policy_body,
            skill_source=skill_source,
        )
        if include_mcp and profile.mcp:
            conflict = _mcp_conflict(changes)
            items.append(verify_mcp_json(target, kit_root, profile.mcp, conflict))
        keys = _plugin_keys(kit_root, plugins)
        if hooks:
            items += approval_hooks.verify(target, kit_root, self.name, changes)
        if keys:
            conflict = approval_hooks.conflict_in(changes, SETTINGS_REL) or _mcp_conflict(
                changes, PLUGIN_OWNER
            )
            items.append(
                verify_owned_keys(target, SETTINGS_REL, PLUGIN_OWNER, keys, conflict, PLUGIN_NOTE)
            )
            items.append(_verify_marketplace(target, kit_root, plugins))
        names = _subagents(profile, skill_source)
        return items + subagents.verify(target, kit_root, names, changes)

    def audit(self, target: Path, kit_root: Path, allowlist: Optional[dict] = None) -> ItemResult:
        return audit_mcp_json(target, kit_root, allowlist)

    def stale_mcp(self, target: Path) -> Optional[ItemResult]:
        return None

    def manual_checks(self, target: Path) -> List[str]:
        steps = [f"Open Claude Code in {target} and run /skills to confirm the kit skills load."]
        if (target / self.mcp_config.rel).is_file():
            steps.append(
                "Run /mcp in Claude Code and approve the project MCP servers from .mcp.json."
            )
        for plugin in declared_plugins(target):
            steps.append(
                f"Trust this folder in Claude Code and check /plugin for {plugin}. "
                f"Teammates who clone the project install it with /plugin install {plugin}."
            )
        return steps + approval_hooks.manual_step(self.name, target)
