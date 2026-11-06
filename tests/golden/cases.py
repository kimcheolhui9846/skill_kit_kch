"""Golden cases for the legacy invocation (no subcommand). Shared by both golden test modules.

The case list mirrors the P1-T3 baseline (docs/v2/baseline/install-snapshots/snapshot.py).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable, List, Optional, Tuple

KIT_ROOT = Path(__file__).resolve().parents[2]
PROFILES = ["core", "python", "data", "web", "full"]
MODES = {
    "default": [],
    "dry-run": ["--dry-run"],
    "verify-only": ["--verify-only"],
    "no-mcp": ["--no-mcp"],
}
STAMP = re.compile(r"\d{8}-\d{6}")
ENV_LINE = re.compile(r"^Environment:.*$", re.MULTILINE)

Setup = Optional[Callable[[Path], None]]


def _user_agents(target: Path) -> None:
    (target / "AGENTS.md").write_text("# My rules\n\nkeep me\n", encoding="utf-8")


def _edited_block(target: Path) -> None:
    body = (KIT_ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
    (target / "AGENTS.md").write_text(
        f"<!-- hackathon-kit:begin -->\n{body}\n- user edit\n<!-- hackathon-kit:end -->\n",
        encoding="utf-8",
    )


def all_cases() -> List[Tuple[str, List[List[str]], Setup]]:
    cases: List[Tuple[str, List[List[str]], Setup]] = []
    for prof in PROFILES:
        for mode, extra in MODES.items():
            cases.append((f"{prof}__{mode}", [["--profile", prof, "--offline", *extra]], None))
    base = ["--profile", "python", "--offline"]
    cases.append(("python__rerun-x3", [base, base, base], None))
    cases.append(("core__existing-agents-md", [["--offline"]], _user_agents))
    cases.append(("core__conflict-edited-block", [["--offline"]], _edited_block))
    cases.append(("self-target", [["--offline", "--target", "<KIT>"]], None))
    return cases


def expand(args: List[str]) -> List[str]:
    return [str(KIT_ROOT) if a == "<KIT>" else a for a in args]


def normalize(text: str, target: Path) -> str:
    for p in sorted({str(target), str(target.resolve()), target.as_posix()}, key=len, reverse=True):
        text = text.replace(p, "<TARGET>")
    text = text.replace(str(KIT_ROOT), "<KIT>")
    text = STAMP.sub("<STAMP>", text)
    return ENV_LINE.sub("Environment:  <ENV>", text)


def tree(root: Path) -> dict:
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(".kit/logs/"):
            out[STAMP.sub("<STAMP>", rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out
