"""P3-T1 golden regression tests for the legacy invocation.

Requirements: REQ-COMPAT-001/002/003/005, REQ-SAFE-006. Two layers:
- test_matches_p1_baseline: the real entry point (`python -I run_kit.py`) in a subprocess,
  compared with the P1-T3 baseline recorded before any v2 change (tests/golden/baseline/).
  Compares exit codes, the installed file tree (path -> SHA-256) and that HOME stays empty.
  These values do not depend on the machine's installed tools.
- test_matches_inprocess_golden: kit.app.run in-process with the suite's fake tool probes and the
  no_network fixture. Also compares the full normalised report text, which on a real machine varies
  with the Environment/Tools lines. Regenerate with UPDATE_GOLDEN=1 only when a change is approved.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from kit.app import run
from tests.golden.cases import KIT_ROOT, all_cases, expand, normalize, tree

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline"
INPROCESS = HERE / "inprocess"
CASES = all_cases()
IDS = [c[0] for c in CASES]


def _fresh(tmp_path: Path, setup) -> tuple[Path, Path]:
    home = tmp_path / "golden-home"
    home.mkdir()
    target = tmp_path / "golden-ws"
    target.mkdir()
    if setup:
        setup(target)
    return target, home


@pytest.mark.parametrize("name,steps,setup", CASES, ids=IDS)
def test_matches_p1_baseline(name, steps, setup, tmp_path):
    expected = json.loads((BASELINE / f"{name}.json").read_text(encoding="utf-8"))
    target, home = _fresh(tmp_path, setup)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    codes = []
    for args in steps:
        proc = subprocess.run(
            [sys.executable, "-I", str(KIT_ROOT / "run_kit.py"), *expand(args)],
            cwd=target,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        codes.append(proc.returncode)
    assert codes == [r["exit"] for r in expected["runs"]]
    assert tree(target) == expected["tree"]
    assert not any(home.rglob("*")) and expected["home_untouched"]


def _run_inprocess(steps, setup, tmp_path) -> dict:
    target, home = _fresh(tmp_path, setup)
    runs = []
    for args in steps:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = run(expand(args), cwd=target, out=out)
        runs.append(
            {
                "args": args,
                "exit": code,
                "stdout": normalize(out.getvalue(), target),
                "stderr": normalize(err.getvalue(), target),
            }
        )
    return {"runs": runs, "tree": tree(target), "home_untouched": not any(home.rglob("*"))}


@pytest.mark.parametrize("name,steps,setup", CASES, ids=IDS)
def test_matches_inprocess_golden(name, steps, setup, tmp_path, monkeypatch, no_network):
    home = tmp_path / "golden-home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    actual = _run_inprocess(steps, setup, tmp_path)
    path = INPROCESS / f"{name}.json"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.write_text(json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected
    # The in-process run must agree with the P1 baseline on everything machine-independent.
    baseline = json.loads((BASELINE / f"{name}.json").read_text(encoding="utf-8"))
    assert [r["exit"] for r in actual["runs"]] == [r["exit"] for r in baseline["runs"]]
    assert actual["tree"] == baseline["tree"]


def test_no_network_fixture_blocks(no_network):
    import socket

    with pytest.raises(RuntimeError, match="socket connect blocked"):
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    with pytest.raises(RuntimeError, match="network command blocked"):
        subprocess.run(["npx", "--version"])
    with pytest.raises(RuntimeError, match="network command blocked"):
        subprocess.run(["pip.exe", "--version"])
    assert subprocess.run([sys.executable, "-c", "pass"]).returncode == 0
