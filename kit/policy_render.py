"""Policy text for the policy block of each agent (ADR-004, ADR-015, P4-T6).

- restricted: the kit's AGENTS.md text, byte for byte (the legacy policy, ADR-002). Same for
  every agent; its Restrictions section is the exam rule set and is never reworded.
- standard: the policy modules in shared/policies/, joined in MODULES order, with {agent} and
  {skill_root} filled in per agent. Each rule lives in one module only, so AGENTS.md and
  CLAUDE.md always carry the same text (TC-POL-01).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Collection, Dict, List, Tuple

from .plan import kit_policy_text

POLICIES = ("restricted", "standard")
POLICY_DIR = "shared/policies"
MODULES: Dict[str, Tuple[str, ...]] = {
    "standard": (
        "core.md",  # title, the ten principles, where the skills are
        "light-path.md",  # L/S/C grades: one-line fixes skip the task procedure
        "skills.md",  # when to use which skill (P5-T1); the steps stay in the skills
        "testing.md",
        "hitl.md",
        "environments/standard.md",  # what needs approval first
    ),
}


GUIDE = "skills.md"
_WORD = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b")


def guide_skills(kit_root: Path, policy: str, known: Collection[str]) -> List[str]:
    """Skills the policy's "when to use which skill" guide names (P5-T1); [] without a guide."""
    if GUIDE not in MODULES.get(policy, ()):
        return []
    text = (kit_root / POLICY_DIR / GUIDE).read_text(encoding="utf-8")
    return sorted({w for w in _WORD.findall(text) if w in known})


def module_paths(kit_root: Path, policy: str):
    return [kit_root / POLICY_DIR / rel for rel in MODULES[policy]]


def render(kit_root: Path, policy: str, adapter) -> str:
    if policy == "restricted":
        return kit_policy_text(kit_root)
    if policy in MODULES:
        text = "".join(p.read_text(encoding="utf-8") for p in module_paths(kit_root, policy))
        return text.replace("{agent}", adapter.display_name).replace(
            "{skill_root}", adapter.skill_root
        )
    raise ValueError(f"unknown policy '{policy}'")
