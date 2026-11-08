"""Codex adapter: the v1 behaviour, unchanged (ADR-002, golden tests in tests/golden/).

With --plugin (new path only), also the repo marketplace .agents/plugins/marketplace.json
(kit-owned file, kit.plugin_install); the install itself runs through the codex CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .. import approval_hooks, mcp_catalog, plugin_install
from .. import audit as audit_mod
from ..audit import audit_target
from ..fsops import State
from ..mcpconfig import stale_block_item
from ..model import FAIL, PASS, ItemResult, Outcome
from ..plan import SKILL_SOURCE, FileChange, plan_changes, plan_file
from ..profiles import Profile
from ..verify import verify_target
from ..writers import markdown_block, toml_block
from .base import BlockTarget


def _market_file(kit_root: Path, plugins) -> bytes:
    market, _ = mcp_catalog.load_plugins(kit_root)
    return plugin_install.marketplace_json(market, list(plugins), "codex")


def _verify_market_file(target: Path, kit_root: Path, plugins) -> ItemResult:
    label = plugin_install.CODEX_MARKETPLACE_REL
    try:
        data = (target / label).read_bytes()
    except OSError:
        return ItemResult(label, False, False, False, FAIL, "missing")
    if data != _market_file(kit_root, plugins):
        return ItemResult(label, False, True, False, FAIL, "outdated")
    return ItemResult(label, False, True, True, PASS, "repo plugin marketplace")


class CodexAdapter:
    name = "codex"
    display_name = "Codex"
    cli = "codex"
    mcp_cli_check = True  # `codex mcp list` can confirm registration (kit.mcpcheck)
    policy = BlockTarget("AGENTS.md", markdown_block.BEGIN, markdown_block.END)
    skill_root = SKILL_SOURCE
    mcp_config = BlockTarget(".codex/config.toml", toml_block.BEGIN, toml_block.END)

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
            include_mcp,
            policy_rel=self.policy.rel,
            skill_root=self.skill_root,
            policy_body=policy_body,
            skill_source=skill_source,
        )
        if plugins:
            rel = plugin_install.CODEX_MARKETPLACE_REL
            changes.append(
                plan_file(target, rel, "plugin-config", _market_file(kit_root, plugins), state)
            )
        if hooks:
            config = approval_hooks.plan_config(target, self.name, state)
            changes.append(config)
            if config.outcome != Outcome.CONFLICT:  # no script without its registration
                changes.append(approval_hooks.plan_script(target, kit_root, self.name, state))
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
        # The legacy path (kit.app) still calls verify_target itself; the new path uses this.
        items = verify_target(
            target,
            kit_root,
            profile,
            changes,
            check_writable,
            writable,
            include_mcp=include_mcp,
            policy_rel=self.policy.rel,
            skill_root=self.skill_root,
            policy_body=policy_body,
            skill_source=skill_source,
        )
        if plugins:
            items.append(_verify_market_file(target, kit_root, plugins))
        if hooks:
            items += approval_hooks.verify(target, kit_root, self.name, changes)
        return items

    def audit(self, target: Path, kit_root: Path, allowlist: Optional[dict] = None) -> ItemResult:
        return audit_target(target, kit_root, allowlist)

    def audit_planned(
        self,
        target: Path,
        kit_root: Path,
        allowlist: Optional[dict],
        planned: Dict[str, Optional[bytes]],
    ) -> ItemResult:
        """B-3: the audit of the config this run would leave (planned bytes over the disk)."""
        rel = self.mcp_config.rel
        if rel not in planned:
            return self.audit(target, kit_root, allowlist)
        return audit_mod.audit_toml_data(planned[rel], kit_root, allowlist)

    def stale_mcp(self, target: Path) -> Optional[ItemResult]:
        """An earlier kit MCP block left in place when MCP is now off."""
        return stale_block_item(target)

    def manual_checks(self, target: Path) -> List[str]:
        steps = [f"Open Codex in {target} and run /skills to confirm the kit skills load."]
        return steps + approval_hooks.manual_step(self.name, target)
