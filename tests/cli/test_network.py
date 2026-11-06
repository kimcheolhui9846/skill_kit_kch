"""P3-T8 network gate and report (D-14, ADR-014). REQ-SAFE-006/007, REQ-INST-007/009."""

from __future__ import annotations

import io
import json

import pytest

from kit import app, commands, mcpcheck, preflight, tools
from kit.logs import mask
from kit.model import EXIT_READY
from kit.preflight import ToolInfo
from kit.secrets_scan import find
from tests.conftest import KIT_ROOT

NPX = "npx -y @modelcontextprotocol/server-sequential-thinking@2026.8.31"


@pytest.fixture
def recorder(monkeypatch):
    """Record every network action instead of running it."""
    calls = []
    monkeypatch.setattr(
        mcpcheck, "handshake", lambda cmd, timeout=120.0: calls.append(cmd) or ("PASS", "ok")
    )
    monkeypatch.setattr(
        tools, "run_command", lambda cmd, timeout=600.0, cwd=None: calls.append(cmd) or (0, "")
    )
    return calls


@pytest.fixture
def ruff_missing(monkeypatch):
    def probe(name, timeout=15.0):
        return ToolInfo(name) if name == "ruff" else ToolInfo(name, f"/fake/{name}", "fake 1.0")

    monkeypatch.setattr(preflight, "probe_tool", probe)


def run_with(workspace, *argv, ask=None):
    out = io.StringIO()
    code = commands.run(list(argv), workspace, KIT_ROOT, out, ask)
    return code, out.getvalue()


# ---------------------------------------------------------------- no terminal, no --yes


def test_non_interactive_without_yes_skips_network(workspace, recorder, ruff_missing):
    code, out = run_with(
        workspace, "install", "--agent", "both", "--profile", "python", "--verbose"
    )
    assert code == EXIT_READY, out
    assert recorder == []
    assert "Network:      not used; no terminal to ask, pass --yes to allow:" in out
    assert "  - tools (user-scope install): uv tool install ruff==0.17.3" in out
    assert f"  - MCP check for codex, claude: {NPX}" in out
    assert "SKIPPED    optional tool:ruff  (needs --yes (network); install later with" in out
    assert "SKIPPED    optional mcp:sequential-thinking  (needs --yes (network)" in out


def test_yes_allows_network(workspace, recorder, ruff_missing):
    code, out = run_with(workspace, "install", "--agent", "claude", "--profile", "python", "--yes")
    assert len(recorder) == 2  # one tool install, one MCP handshake
    assert "Network:      used (--yes)" in out
    assert f"  - MCP check for claude: {NPX}" in out


# ---------------------------------------------------------------- terminal prompt


def test_terminal_prompt_confirmed(workspace, recorder, ruff_missing):
    asked = []
    code, out = run_with(
        workspace,
        "install",
        "--agent",
        "codex",
        "--profile",
        "python",
        ask=lambda q: asked.append(q) or "y",
    )
    assert len(asked) == 1
    assert "This will use the network:" in asked[0] and NPX in asked[0]
    assert "uv tool install ruff==0.17.3" in asked[0] and asked[0].endswith("[y/N] ")
    assert len(recorder) == 2 and "Network:      used (confirmed)" in out


@pytest.mark.parametrize("answer", ["", "n", "no", "maybe"])
def test_terminal_prompt_declined(workspace, recorder, answer):
    code, out = run_with(
        workspace,
        "install",
        "--agent",
        "claude",
        "--profile",
        "python",
        "--verbose",
        ask=lambda q: answer,
    )
    assert code == EXIT_READY and recorder == []
    assert "Network:      not used (declined); these were skipped:" in out
    assert "(network declined: npx would download the package)" in out


def test_no_prompt_when_nothing_needs_network(workspace, recorder):
    asked = []
    code, out = run_with(workspace, "install", "--agent", "both", ask=asked.append)
    assert asked == [] and "Network:      not used\n" in out


def test_offline_never_prompts(workspace, recorder):
    asked = []
    run_with(
        workspace,
        "install",
        "--agent",
        "both",
        "--profile",
        "python",
        "--offline",
        ask=asked.append,
    )
    assert asked == [] and recorder == []


def test_plan_lists_network_without_asking(workspace, recorder, ruff_missing):
    asked = []
    code, out = run_with(
        workspace, "plan", "--agent", "both", "--profile", "python", ask=asked.append
    )
    assert asked == [] and recorder == []
    assert "Network:      would use (install asks first; --yes skips the question):" in out
    assert "INSTALL   tool:ruff" in out and "[network]" in out
    data = json.loads(
        run_with(workspace, "plan", "--agent", "claude", "--profile", "python", "--json")[1]
    )
    assert data["network"]["reason"] == "plan only"
    assert data["network"]["needs"] == [
        {"for": "tools (user-scope install)", "command": "uv tool install ruff==0.17.3"},
        {"for": "MCP check for claude", "command": NPX},
    ]


def test_no_mcp_removes_the_mcp_need(workspace, recorder):
    code, out = run_with(workspace, "install", "--agent", "both", "--profile", "python", "--no-mcp")
    assert "Network:      not used\n" in out


def test_app_passes_no_prompt_for_captured_output(workspace, monkeypatch, recorder):
    """Tests and embedding callers that pass their own `out` are never prompted."""
    monkeypatch.setattr(commands, "terminal_ask", lambda: pytest.fail("must not ask"))
    out = io.StringIO()
    app.run(["install", "--agent", "claude", "--profile", "python"], cwd=workspace, out=out)
    assert "no terminal to ask" in out.getvalue()


def test_terminal_ask_is_none_without_a_tty(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert commands.terminal_ask() is None


# ---------------------------------------------------------------- --offline: zero network calls


@pytest.mark.real_mcp
def test_offline_makes_zero_network_calls(workspace, no_network, monkeypatch):
    """Real handshake code path, network blocked at socket and subprocess level."""
    monkeypatch.setattr(mcpcheck, "find_command", lambda name: pytest.fail("looked up npx"))
    code, out = run_with(
        workspace, "install", "--agent", "both", "--profile", "python", "--offline"
    )
    assert code == EXIT_READY, out
    code, out = run_with(workspace, "verify", "--agent", "both", "--offline")
    assert code == EXIT_READY, out


# ---------------------------------------------------------------- masking


SECRETS = [
    "sk-ant-api03-" + "A" * 30,
    "ghp_" + "B" * 36,
    "github_pat_" + "C" * 40,
    "AKIA" + "D" * 16,
    "AIza" + "E" * 35,
    "xoxb-" + "1234567890-abcdef",
    "hf_" + "F" * 34,
    "npm_" + "G" * 36,
]


@pytest.mark.parametrize("secret", SECRETS)
def test_mask_covers_shared_token_patterns(secret):
    assert secret not in mask(f"value {secret} end")
    assert find(f"x\n{secret}")[0][1] == 2


def test_find_reports_location_not_value():
    hits = find("ok\n-----BEGIN OPENSSH PRIVATE KEY-----\n")
    assert hits == [("private key", 2)]


def test_new_path_masks_stdout_log_and_json(workspace, monkeypatch, tmp_path, recorder):
    token = "ghp_" + "Z" * 36
    monkeypatch.setattr(
        mcpcheck, "handshake", lambda cmd, timeout=120.0: ("FAIL", f"server said {token}")
    )
    report = tmp_path / "r.json"
    code, out = run_with(
        workspace,
        "install",
        "--agent",
        "claude",
        "--profile",
        "python",
        "--yes",
        "--verbose",
        "--report-json",
        str(report),
    )
    assert "server said ***" in out and token not in out
    assert token not in report.read_text(encoding="utf-8")
    logs = list((workspace / ".kit/logs").glob("*.log"))
    assert logs and all(token not in p.read_text(encoding="utf-8") for p in logs)
    code, out = run_with(workspace, "verify", "--agent", "claude", "--yes", "--json")
    assert token not in out and "***" in out
