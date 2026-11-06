"""P3-T6: bootstrap.sh / bootstrap.ps1 pass subcommands through unchanged (ADR-013)."""

from __future__ import annotations

import json

import pytest

from tests.test_entrypoints import NO_PYTHON, SHELLS, _path, _python, _run


@pytest.mark.parametrize("kind", SHELLS)
@pytest.mark.parametrize("agent,policy_file", [("codex", "AGENTS.md"), ("claude", "CLAUDE.md")])
def test_install_through_bootstrap(kind, agent, policy_file, tmp_path):
    target = tmp_path / "작업 폴더 'q'"
    target.mkdir()
    proc = _run(
        kind,
        "install",
        "--agent",
        agent,
        "--offline",
        "--target",
        _path(kind, target),
        cwd=tmp_path,
        python=_python(kind),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Agent {agent}:" in proc.stdout and f"shell={kind}" in proc.stdout
    assert (target / policy_file).is_file()


@pytest.mark.parametrize("kind", SHELLS)
def test_profile_list_value_with_comma_and_json(kind, workspace):
    proc = _run(
        kind,
        "plan",
        "--agent",
        "both",
        "--profile",
        "python,hitl",
        "--json",
        cwd=workspace,
        python=_python(kind),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["profiles"] == ["python", "hitl"] and set(data["agents"]) == {"codex", "claude"}
    assert list(workspace.iterdir()) == []


@pytest.mark.parametrize("kind", SHELLS)
def test_subcommand_help_is_not_the_legacy_usage(kind, workspace):
    proc = _run(kind, "install", "--help", cwd=workspace, python=_python(kind))
    assert proc.returncode == 0
    assert "kit install --agent claude" in proc.stdout and "Usage: bootstrap" not in proc.stdout
    legacy = _run(kind, "--help", cwd=workspace, python=_python(kind))
    assert "Usage: bootstrap" in legacy.stdout


@pytest.mark.parametrize("kind", SHELLS)
def test_usage_error_code_passes_through(kind, workspace):
    proc = _run(kind, "install", cwd=workspace, python=_python(kind))
    assert proc.returncode == 64 and "--agent is required" in proc.stderr


@pytest.mark.parametrize("kind", SHELLS)
def test_shell_only_mode_rejects_subcommands(kind, workspace):
    proc = _run(kind, "install", "--agent", "claude", cwd=workspace, python=NO_PYTHON)
    assert proc.returncode == 64
    assert "'install' requires Python 3.9+" in proc.stderr
    assert list(workspace.iterdir()) == []
