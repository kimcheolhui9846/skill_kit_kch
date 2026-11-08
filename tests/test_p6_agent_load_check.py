"""P6-T6: docs/v2/AGENT_LOAD_CHECK.md stays true to what the kit installs.

The checklist is run by a person inside each agent, so it cannot be tested itself. What can be
tested: the skill list and the installed files it names match a real `install --agent both`,
every check names a source, every source has a URL, and the result columns are left empty.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from kit import commands
from tests.conftest import KIT_ROOT

DOC = KIT_ROOT / "docs" / "v2" / "AGENT_LOAD_CHECK.md"


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def _rows(text: str, prefix: str):
    return [
        [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        for line in text.splitlines()
        if re.match(rf"^\| {prefix}-\d\d ", line)
    ]


def _install(ws: Path) -> None:
    out = io.StringIO()
    argv = ["install", "--agent", "both", "--mcp", "context7", "--hooks", "--offline"]
    code = commands.run([*argv, "--target", str(ws)], ws, KIT_ROOT, out)
    assert code == 0, out.getvalue()


def test_the_skill_list_is_what_both_installs(workspace):
    _install(workspace)
    line = next(x for x in _doc().splitlines() if x.startswith("**스킬 "))
    listed = re.findall(r"`([a-z0-9-]+)`", line)
    count = int(re.search(r"스킬 (\d+)개", line).group(1))
    for root in (".agents/skills", ".claude/skills"):
        installed = sorted(p.name for p in (workspace / root).iterdir() if p.is_dir())
        assert listed == installed, root
    assert count == len(listed)


def test_the_files_named_are_installed(workspace):
    _install(workspace)
    text = _doc()
    table = text[text.index("| Codex | `AGENTS.md`") : text.index("**스킬 ")]
    names = [
        n
        for n in re.findall(r"`([^`(]+?)`", table)
        if ("/" in n or "." in n) and not n.startswith("[")  # not the TOML table name
    ]
    assert len(names) >= 10
    for name in names:
        assert (workspace / name.rstrip("/")).exists(), name


def test_every_check_has_a_source_and_an_empty_result():
    text = _doc()
    sources = set(re.findall(r"^\| (C[XC]-[A-Z]+) \| https://", text, re.M))
    rows = _rows(text, "C") + _rows(text, "L")
    assert len(rows) == 16
    for row in rows:
        assert len(row) == 7, row
        cited = set(re.findall(r"C[XC]-[A-Z]+", row[4]))
        assert cited and cited <= sources, row[0]
        assert row[5] == "" and row[6] == "", f"{row[0]}: the reviewer fills the result"


def test_no_command_from_outside_the_docs():
    """`/memory` is no longer in Claude Code's memory page (2026-11-08); /context all is."""
    text = _doc()
    checks = text[text.index("## 1. Codex") : text.index("## 3.")]
    assert "/memory" not in checks
    assert "`/context all`" in checks
