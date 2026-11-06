"""Shared fixtures for catalog tests: a copy of the kit with a layered skill tree."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


@pytest.fixture
def kit(tmp_path, kit_root):
    """A copy of the kit with a layered tree to install from."""
    root = tmp_path / "kit"
    root.mkdir()
    for rel in ("AGENTS.md", "sources.lock.json", "THIRD_PARTY_NOTICES.md"):
        shutil.copy(kit_root / rel, root / rel)
    for rel in (".agents", "shared", "profiles", "mcp", "catalog", "third_party"):
        if (kit_root / rel).is_dir():
            shutil.copytree(kit_root / rel, root / rel)
    # user/: the rules only. The captured snapshot of this PC is not a test input.
    (root / "user").mkdir()
    shutil.copy(kit_root / "user/capture-allowlist.json", root / "user/capture-allowlist.json")
    skill = "---\nname: {n}\ndescription: {d} Do NOT use for other work.\n---\n\n# {n}\n"
    # shared skill with an agent file for codex and a Claude-only addition
    write(root, "shared/skills/tree-demo/SKILL.md", skill.format(n="tree-demo", d="Shared."))
    write(root, "shared/skills/tree-demo/references/notes.md", "shared notes\n")
    write(root, "codex/skills/tree-demo/agents/openai.yaml", "policy: {}\n")
    write(root, "claude/skills/tree-demo/SKILL.md.append", "Claude-only line.\n")
    write(root, "claude/skills/tree-demo/references/notes.md", "claude notes\n")
    # codex-only skill (no shared base)
    write(root, "codex/skills/codex-only/SKILL.md", skill.format(n="codex-only", d="Codex."))
    # standard-policy overlay on a legacy skill
    write(root, "shared/skills/overlays/benchmark/SKILL.md.append", "Standard overlay line.\n")
    data = json.loads((root / "catalog/skills.json").read_text(encoding="utf-8"))
    for entry in data["skills"]:
        if entry["name"] == "benchmark":
            entry["overlay"] = "shared/skills/overlays/benchmark"
            entry["overlay_policies"] = ["standard"]
    data["skills"] += [
        {"name": "tree-demo", "location": "shared/skills/tree-demo", "packs": ["demo"]},
        {"name": "codex-only", "location": None, "agents": ["codex"], "packs": ["demo"]},
    ]
    write(root, "catalog/skills.json", json.dumps(data, indent=2))
    pack = {
        "schema": 2,
        "kind": "pack",
        "name": "demo",
        "skills": {"shared": ["tree-demo", "codex-only"]},
    }
    write(root, "profiles/packs/demo.json", json.dumps(pack))
    return root
