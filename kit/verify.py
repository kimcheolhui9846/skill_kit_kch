"""Check what is actually in the target, item by item. Codex loading itself is not observable."""

from __future__ import annotations

from pathlib import Path

from .agentsmd import MarkerError, extract_block
from .mcpconfig import verify_config
from .model import CONFLICT, FAIL, PASS, ItemResult, Outcome
from .plan import SKILL_SOURCE, FileChange, skill_target_files
from .profiles import Profile
from .skills import validate_skill


def verify_target(
    target: Path,
    kit_root: Path,
    profile: Profile,
    changes: list[FileChange],
    check_writable: bool,
    writable: bool,
    include_mcp: bool = False,
    policy_rel: str = "AGENTS.md",
    skill_root: str = SKILL_SOURCE,
    policy_body: str | None = None,
    skill_source=None,
) -> list[ItemResult]:
    conflicts: dict[str, str] = {}
    for change in changes:
        if change.outcome == Outcome.CONFLICT:
            conflicts.setdefault(change.owner, f"{change.rel}: {change.detail}")

    items = []
    if check_writable:
        items.append(
            ItemResult(
                "target writable",
                True,
                True,
                True,
                PASS if writable else FAIL,
                "" if writable else f"cannot write to {target}",
            )
        )
    items.append(_verify_agents_md(target, kit_root, conflicts, policy_rel, policy_body))
    for name in profile.skills:
        required = name in profile.required_skills
        items.append(
            _verify_skill(target, kit_root, name, required, conflicts, skill_root, skill_source)
        )
    if include_mcp and profile.mcp:
        items.append(verify_config(target, kit_root, profile.mcp, conflicts.get("mcp-config")))
    return items


def _verify_agents_md(
    target: Path,
    kit_root: Path,
    conflicts: dict[str, str],
    policy_rel: str = "AGENTS.md",
    policy_body: str | None = None,
) -> ItemResult:
    name = policy_rel
    if name in conflicts:
        return ItemResult(name, True, True, False, CONFLICT, conflicts[name])
    path = target / name
    if not path.is_file():
        return ItemResult(name, True, False, False, FAIL, f"{name} missing")
    try:
        found = extract_block(path.read_bytes().decode("utf-8"))
    except (MarkerError, UnicodeDecodeError) as exc:
        return ItemResult(name, True, True, False, FAIL, str(exc))
    if found is None:
        return ItemResult(name, True, True, False, FAIL, "kit block missing")
    if policy_body is None:
        policy_body = (kit_root / "AGENTS.md").read_text(encoding="utf-8")
    body = policy_body.strip()
    if found[2] != body:
        return ItemResult(name, True, True, True, FAIL, "kit block is outdated")
    return ItemResult(name, True, True, True, PASS)


def _verify_skill(
    target: Path,
    kit_root: Path,
    name: str,
    required: bool,
    conflicts: dict[str, str],
    skill_root: str = SKILL_SOURCE,
    skill_source=None,
) -> ItemResult:
    label = f"skill:{name}"
    if label in conflicts:
        return ItemResult(label, required, True, False, CONFLICT, conflicts[label])
    skill_dir = target / skill_root / name
    if not skill_dir.is_dir():
        return ItemResult(label, required, False, False, FAIL, "not installed")
    validate = getattr(skill_source, "validate", validate_skill)
    errors = validate(skill_dir)
    if errors:
        return ItemResult(label, required, True, True, FAIL, "; ".join(errors))
    for rel, data in skill_target_files(kit_root, name, skill_root, skill_source):
        path = target / rel
        try:
            differs = not path.is_file() or path.read_bytes() != data
        except OSError as exc:
            return ItemResult(label, required, True, True, FAIL, f"cannot read {rel}: {exc}")
        if differs:
            return ItemResult(
                label, required, True, True, FAIL, f"files differ from the kit copy ({rel})"
            )
    return ItemResult(label, required, True, True, PASS)
