"""Kit-owned Claude Code subagents that come with a skill (P5-T5, reviewer decision 2026-11-07).

counterexample-hunter (standard policy) brings .claude/agents/counterexample-blackbox.md: a
subagent with no file, shell or web tools, so its counterexamples come from the requirements
in its prompt alone (00_PROMPT 10.5.1 step 1). CC-SUB: a subagent "starts with a fresh,
isolated context window" and `tools` is an allowlist. Codex has no project subagents; its
overlay text asks for a separate session instead.

Restricted installs never get one: the 11 original skills stay as they were (REQ-COMPAT-002).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .fsops import State
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import FileChange, plan_file

OWNER = "subagent"
POLICIES = ("standard",)
BY_SKILL: Dict[str, List[str]] = {"counterexample-hunter": ["counterexample-blackbox"]}


def source_rel(name: str) -> str:
    return f"shared/agents/{name}.md"


def rel(name: str) -> str:
    return f".claude/agents/{name}.md"


def wanted(skills: Iterable[str], policy: Optional[str]) -> List[str]:
    if policy not in POLICIES:
        return []
    return [a for s in skills for a in BY_SKILL.get(s, [])]


def plan(target: Path, kit_root: Path, names: List[str], state: State) -> List[FileChange]:
    return [
        plan_file(target, rel(n), OWNER, (kit_root / source_rel(n)).read_bytes(), state)
        for n in names
    ]


def verify(target: Path, kit_root: Path, names: List[str], changes: List[FileChange]):
    items = []
    for n in names:
        path, label = rel(n), f"subagent:{n}"
        conflict = next(
            (c.detail for c in changes if c.rel == path and c.outcome == Outcome.CONFLICT), None
        )
        if conflict:
            items.append(ItemResult(label, False, True, False, CONFLICT, f"{path}: {conflict}"))
        elif not (target / path).is_file():
            items.append(ItemResult(label, False, False, False, FAIL, f"{path} missing"))
        elif (target / path).read_bytes() != (kit_root / source_rel(n)).read_bytes():
            items.append(ItemResult(label, False, True, False, FAIL, f"{path} is outdated"))
        else:
            items.append(ItemResult(label, False, True, True, PASS, path))
    return items
