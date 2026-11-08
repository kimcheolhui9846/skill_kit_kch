"""`kit install --hooks` (P5-T2b, ADR-011 L2, project scope only; reviewer decision 2026-11-07).

Installs shared/hooks/kit_approval.py per agent and registers it for UserPromptSubmit and
PreToolUse:
- Claude Code: .claude/hooks/kit_approval.py, kit-owned keys /hooks/UserPromptSubmit and
  /hooks/PreToolUse in .claude/settings.json (CC-HK). Loads after the folder is trusted.
- Codex: .codex/hooks/kit_approval.py and the same keys in .codex/hooks.json (CX-HK). Project
  hooks load only when the project .codex/ layer is trusted and the hook is reviewed in
  /hooks. Codex calls tool hooks "a useful guardrail, not a complete enforcement boundary".

The kit owns the whole event arrays (ADR-005 per-key ownership): a project that already has
its own UserPromptSubmit or PreToolUse hooks gets a CONFLICT and nothing is written.

With the hook installed, `kit task approve --by agent-recorded` is refused (kit.tasks).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from .fsops import State
from .mcpjson import plan_owned_keys, verify_owned_keys
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import FileChange, plan_file

SOURCE_REL = "shared/hooks/kit_approval.py"
SCRIPT_REL = {"claude": ".claude/hooks/kit_approval.py", "codex": ".codex/hooks/kit_approval.py"}
CONFIG_REL = {"claude": ".claude/settings.json", "codex": ".codex/hooks.json"}
OWNER = "hook-config"
SCRIPT_OWNER = "hook-script"
TIMEOUT = 30  # seconds; the hook reads one small JSON file
# tools that can write files or run commands (CC-HK: PowerShell is a tool on Windows)
CLAUDE_TOOLS = "Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit"
CODEX_TOOLS = "Bash|apply_patch|Edit|Write"  # CX-HK: apply_patch also matches Edit/Write
NOTE = {
    "claude": "approval hook (L2); loads after the folder is trusted",
    "codex": "approval hook (L2, a guardrail only); trust .codex/ and review it in /hooks",
}


def python_command() -> str:
    """The interpreter name for the hook command on this PC."""
    return "python" if os.name == "nt" else "python3"


def script(kit_root: Path) -> bytes:
    return (kit_root / SOURCE_REL).read_bytes()


def keys(agent: str) -> Dict[str, object]:
    """Kit-owned JSON pointers of the agent's hook registration."""
    rel = SCRIPT_REL[agent]
    if agent == "claude":
        handler: dict = {
            "type": "command",
            "command": f'{python_command()} "${{CLAUDE_PROJECT_DIR}}/{rel}"',
            "timeout": TIMEOUT,
        }
        tools = CLAUDE_TOOLS
    else:
        # Codex runs the command in the session folder; commandWindows is its Windows override
        handler = {
            "type": "command",
            "command": f"python3 {rel}",
            "commandWindows": f"python {rel}",
            "timeout": TIMEOUT,
            "statusMessage": "kit approval hook",
        }
        tools = CODEX_TOOLS
    return {
        "/hooks/UserPromptSubmit": [{"hooks": [handler]}],
        "/hooks/PreToolUse": [{"matcher": tools, "hooks": [handler]}],
    }


def plan_script(target: Path, kit_root: Path, agent: str, state: State) -> FileChange:
    return plan_file(target, SCRIPT_REL[agent], SCRIPT_OWNER, script(kit_root), state)


def plan_config(target: Path, agent: str, state: State) -> FileChange:
    """Codex only; Claude merges these keys into its settings change (one file, one change)."""
    return plan_owned_keys(target, CONFIG_REL[agent], OWNER, keys(agent), state)


def conflict_in(changes: List[FileChange], rel: str) -> Optional[str]:
    for change in changes:
        if change.rel == rel and change.outcome == Outcome.CONFLICT:
            return f"{rel}: {change.detail}"
    return None


def verify(target: Path, kit_root: Path, agent: str, changes: List[FileChange]) -> List[ItemResult]:
    rel = SCRIPT_REL[agent]
    label = "approval-hook"
    config = CONFIG_REL[agent]
    conflict = conflict_in(changes, rel) or conflict_in(changes, config)
    if conflict:
        script_item = ItemResult(label, False, True, False, CONFLICT, conflict)
    elif not (target / rel).is_file():
        script_item = ItemResult(label, False, False, False, FAIL, f"{rel} missing")
    elif (target / rel).read_bytes() != script(kit_root):
        script_item = ItemResult(label, False, True, False, FAIL, f"{rel} is outdated")
    else:
        script_item = ItemResult(label, False, True, True, PASS, rel)
    keys_item = verify_owned_keys(
        target, config, OWNER, keys(agent), conflict_in(changes, config), NOTE[agent]
    )
    return [script_item, keys_item]


def installed(target: Path) -> List[str]:
    """Agents whose approval hook is in the workspace: the script and its registration."""
    out = []
    for agent, rel in SCRIPT_REL.items():
        try:
            registered = "kit_approval" in (target / CONFIG_REL[agent]).read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            registered = False
        if registered and (target / rel).is_file():
            out.append(agent)
    return out


def manual_step(agent: str, target: Path) -> List[str]:
    if agent not in installed(target):
        return []
    if agent == "claude":
        return [
            "Approval hook: trust this folder in Claude Code; after submit, reply only "
            "'approve' and check kit task status shows 'by human-hook'."
        ]
    return [
        "Approval hook: trust this project in Codex, review the kit hook in /hooks and start "
        "Codex in this folder; after submit, reply only 'approve' and check "
        "kit task status. "
        "Codex hooks are a guardrail, not a complete enforcement boundary."
    ]
