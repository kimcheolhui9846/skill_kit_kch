"""Agent adapter interface (04_DESIGN section 2, ADR-002).

An adapter owns the agent-specific facts: where the policy file, skills and MCP config live,
and how to plan them. Applying the plan (backup, atomic writes, state) stays in the shared
executor (kit.register), so adding an agent never touches it (REQ-ARCH-003).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol

from ..fsops import State
from ..model import ItemResult
from ..plan import FileChange
from ..profiles import Profile


@dataclass(frozen=True)
class BlockTarget:
    """A file in the target whose kit-owned part is a marker block."""

    rel: str
    begin: str
    end: str


class AgentAdapter(Protocol):
    name: str
    display_name: str  # shown in reports, e.g. "Claude Code"
    cli: str  # executable name probed by `kit doctor`
    mcp_cli_check: bool  # the agent CLI can list registered MCP servers
    policy: BlockTarget
    skill_root: str
    mcp_config: BlockTarget

    def plan(
        self,
        target: Path,
        kit_root: Path,
        profile: Profile,
        state: State,
        include_mcp: bool,
        policy_body: Optional[str] = None,
        skill_source=None,
        plugins=None,  # [(name, catalog entry)] from catalog/plugins.json
        hooks: bool = False,  # --hooks: approval hook (kit.approval_hooks, project scope)
    ) -> List[FileChange]:
        """Pure: decide every change without writing (REQ-ARCH-004)."""
        ...

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
        """Item-by-item check of what is actually in the target."""
        ...

    def audit(self, target: Path, kit_root: Path, allowlist: Optional[dict] = None) -> ItemResult:
        """Security audit of this agent's MCP config (default rules: mcp/allowlist.json)."""
        ...

    def stale_mcp(self, target: Path) -> Optional[ItemResult]:
        """A kit MCP entry left over from an earlier install, when MCP is now off."""
        ...

    def manual_checks(self, target: Path) -> List[str]:
        """Steps only a human can do inside the agent (REQ-AGENT-005)."""
        ...
