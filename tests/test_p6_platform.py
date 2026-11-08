"""P6-T4 platform checks that hold on every system (results: docs/v2/regression/P6-T4-platform.md).

- Windows PowerShell 5.1 reads a .ps1 file without a BOM in the ANSI code page (cp949 on a
  Korean PC), so the kit's PowerShell files stay ASCII.
- The golden fixtures write the same bytes on Windows and Linux.
- Without tomllib (Python 3.9/3.10) a captured Codex table is compared by its lines.
"""

from __future__ import annotations

import subprocess

import pytest

from kit.adapters import user as user_adapters
from tests.conftest import KIT_ROOT
from tests.golden import cases


def ps_files() -> list:
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "*.ps1", "*.psm1", "*.psd1"],
        cwd=KIT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if out.returncode != 0:
        return sorted(p.relative_to(KIT_ROOT).as_posix() for p in KIT_ROOT.glob("*.ps1"))
    return sorted(line for line in out.stdout.splitlines() if line)


def test_powershell_files_are_ascii_for_windows_powershell_5():
    files = ps_files()
    assert "bootstrap.ps1" in files
    bad = {}
    for rel in files:
        data = (KIT_ROOT / rel).read_bytes()
        lines = [n for n, line in enumerate(data.split(b"\n"), 1) if any(b > 0x7F for b in line)]
        if lines:
            bad[rel] = lines[:5]
    assert bad == {}


def test_golden_fixtures_write_the_same_bytes_everywhere(tmp_path):
    cases._user_agents(tmp_path)
    assert (tmp_path / "AGENTS.md").read_bytes() == b"# My rules\r\n\r\nkeep me\r\n"


@pytest.fixture
def no_tomllib(monkeypatch):
    monkeypatch.setattr(user_adapters, "parse_toml", lambda text: (None, None, ""))


@pytest.mark.parametrize(
    "outside, captured, same",
    [
        ("[features]\ngoals = true\n", "[features]\ngoals = true", True),
        ("  [features]\n\n# mine\ngoals = true  \n", "[features]\ngoals = true\n", True),
        ("[features]\ngoals = false\n", "[features]\ngoals = true\n", None),
        ("[features]\ngoals=true\n", "[features]\ngoals = true\n", None),
    ],
    ids=["same", "blank-and-comment-lines", "other-value", "other-spacing"],
)
def test_without_tomllib_only_the_same_lines_count_as_the_same(no_tomllib, outside, captured, same):
    assert user_adapters._same_table(outside, captured) is same


@pytest.mark.skipif(not user_adapters.parse_toml("")[0], reason="needs tomllib (3.11+)")
@pytest.mark.parametrize(
    "outside, same",
    [("[features]\ngoals=true\n", True), ("[features]\ngoals = false\n", False)],
    ids=["other-spacing", "other-value"],
)
def test_with_tomllib_the_values_decide(outside, same):
    assert user_adapters._same_table(outside, "[features]\ngoals = true\n") is same
