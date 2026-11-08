"""B-3 (2026-11-08): the v2 path audits the MCP config before it writes anything.

The audit looks at the config the run would leave behind: what is on disk with the planned
kit changes laid over it. A FAIL ends the run BLOCKED (exit 2) with nothing written: no kit
files, no backups, no state, no manifest, no log. plan / --dry-run give the same verdict.
A finding that does not block (PASS, UNVERIFIED) still lets the write go ahead, and the audit
after the write stays. The legacy installer keeps its order (write, then audit).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kit import audit as audit_mod
from kit import mcpconfig
from kit.model import EXIT_BLOCKED, EXIT_READY, PASS, ItemResult
from tests.conftest import HAS_TOMLLIB

MINE = b'{"mcpServers": {"mine": {"command": "my-tool"}}}\n'
REMOTE = b'model = "mine"\n\n[mcp_servers.remote]\nurl = "https://example.invalid/mcp"\n'
USER_MD = b"# my notes\n\nkeep me\n"


def snapshot(root: Path) -> dict:
    """Every file (bytes) and every folder under root, .kit/ included."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        out[rel] = path.read_bytes() if path.is_file() else "<dir>"
    return out


def _claude_blocker(ws: Path) -> None:
    (ws / ".mcp.json").write_bytes(MINE)
    (ws / "CLAUDE.md").write_bytes(USER_MD)


def _codex_blocker(ws: Path) -> None:
    (ws / ".codex").mkdir()
    (ws / ".codex/config.toml").write_bytes(REMOTE)
    (ws / "AGENTS.md").write_bytes(USER_MD)


# ---------------------------------------------------------------- BLOCKED writes nothing


def test_claude_user_server_blocks_before_anything_is_written(run_kit, workspace):
    _claude_blocker(workspace)
    before = snapshot(workspace)
    code, out = run_kit("install", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "FAIL       required [claude] security audit  (mine: not in mcp/allowlist.json;" in out
    assert "Status:       BLOCKED" in out
    assert "Nothing was written" in out
    assert snapshot(workspace) == before


@pytest.mark.skipif(not HAS_TOMLLIB, reason="the TOML audit needs Python 3.11+")
def test_codex_remote_server_blocks_before_anything_is_written(run_kit, workspace):
    _codex_blocker(workspace)
    before = snapshot(workspace)
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "[codex] security audit" in out and "remote: not in mcp/allowlist.json" in out
    assert snapshot(workspace) == before


def test_line_scan_blocks_before_writing_without_tomllib(run_kit, workspace, monkeypatch):
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    _codex_blocker(workspace)
    before = snapshot(workspace)
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code == EXIT_BLOCKED and "line scan" in out, out
    assert snapshot(workspace) == before


def test_both_agents_write_nothing_when_one_audit_blocks(run_kit, workspace):
    _claude_blocker(workspace)
    before = snapshot(workspace)
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "mine: not in mcp/allowlist.json" in out
    assert snapshot(workspace) == before
    assert not (workspace / "AGENTS.md").exists()


def test_update_blocks_before_anything_is_written(run_kit, workspace):
    code, out = run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    path = workspace / ".mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["mcpServers"]["mine"] = {"command": "my-tool"}
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (workspace / "CLAUDE.md").write_bytes(USER_MD)  # the update would rewrite the kit block
    before = snapshot(workspace)
    code, out = run_kit("update", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "mine: not in mcp/allowlist.json" in out
    assert snapshot(workspace) == before


def test_update_groups_write_nothing_when_one_group_blocks(run_kit, workspace):
    """codex and claude installed with different profiles are updated as two groups."""
    assert run_kit("install", "--agent", "codex", "--profile", "core", "--offline")[0] == 0
    code, out = run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    path = workspace / ".mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["mcpServers"]["mine"] = {"command": "my-tool"}
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (workspace / "AGENTS.md").write_bytes(USER_MD)
    before = snapshot(workspace)
    code, out = run_kit("update", "--agent", "both", "--offline")
    assert code == EXIT_BLOCKED, out
    assert snapshot(workspace) == before


# ---------------------------------------------------------------- the planned result counts


def test_the_planned_content_is_what_is_audited(run_kit, workspace, monkeypatch):
    """The audit gets the merged result in memory, not the file on disk."""
    seen = []
    real = audit_mod.audit_mcp_json_data

    def spy(data, kit_root, allowlist=None):
        seen.append(data)
        return real(data, kit_root, allowlist)

    monkeypatch.setattr(audit_mod, "audit_mcp_json_data", spy)
    _claude_blocker(workspace)
    code, out = run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    assert code == EXIT_BLOCKED, out
    planned = json.loads(seen[0].decode("utf-8"))["mcpServers"]
    assert set(planned) == {"mine", "sequential-thinking"}
    assert (workspace / ".mcp.json").read_bytes() == MINE


# ---------------------------------------------------------------- dry run gives the same verdict


@pytest.mark.parametrize("argv", [("plan",), ("install", "--dry-run")])
def test_dry_run_reports_blocked(run_kit, workspace, argv):
    _claude_blocker(workspace)
    before = snapshot(workspace)
    code, out = run_kit(*argv, "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "FAIL       required [claude] security audit  (mine: not in mcp/allowlist.json;" in out
    assert "Status:       BLOCKED" in out and "DRY RUN: nothing was written." in out
    assert snapshot(workspace) == before


def test_dry_run_json_reports_blocked(run_kit, workspace):
    _claude_blocker(workspace)
    code, out = run_kit("plan", "--agent", "claude", "--offline", "--json")
    assert code == EXIT_BLOCKED
    data = json.loads(out)
    assert data["status"] == "BLOCKED" and data["exit_code"] == EXIT_BLOCKED
    items = data["agents"]["claude"]["items"]
    assert items[0]["name"] == "security audit" and items[0]["verified"] == "FAIL"


def test_blocked_json_report(run_kit, workspace):
    _claude_blocker(workspace)
    code, out = run_kit("install", "--agent", "claude", "--offline", "--json")
    assert code == EXIT_BLOCKED
    data = json.loads(out)
    assert data["status"] == "BLOCKED" and data["written"] is False
    detail = data["agents"]["claude"]["items"][0]["detail"]
    assert detail.startswith("mine: not in mcp/allowlist.json; mine: command")


# ---------------------------------------------------------------- non-blocking still writes


def test_allowed_user_server_still_writes(run_kit, workspace):
    (workspace / ".mcp.json").write_bytes(
        b'{"mcpServers": {"playwright": {"command": "npx", "args": ["-y", "x@1"]}}}\n'
    )
    code, out = run_kit("install", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    assert (workspace / "CLAUDE.md").is_file()


def test_unverified_audit_still_writes(run_kit, workspace, monkeypatch):
    monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_bytes(b'# nothing here\nmodel = "x"\n')
    code, out = run_kit("install", "--agent", "codex", "--offline")
    assert code != EXIT_BLOCKED, out
    assert "UNVERIFIED required [codex] security audit" in out
    assert (workspace / "AGENTS.md").is_file()


def test_the_audit_after_the_write_stays(run_kit, workspace, monkeypatch):
    """Should the planned result pass but the file on disk fail, the run is still BLOCKED."""
    from kit.adapters.claude import ClaudeAdapter

    ok = ItemResult(audit_mod.LABEL, True, True, True, PASS, "stub")
    monkeypatch.setattr(ClaudeAdapter, "audit_planned", lambda self, *a, **k: ok)
    _claude_blocker(workspace)
    code, out = run_kit("install", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "mine: not in mcp/allowlist.json" in out
    assert (workspace / "CLAUDE.md").read_bytes() != USER_MD  # written, then blocked


# ---------------------------------------------------------------- legacy keeps its order


@pytest.mark.skipif(not HAS_TOMLLIB, reason="the TOML audit needs Python 3.11+")
def test_legacy_still_writes_then_audits(run_kit, workspace):
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_bytes(REMOTE)
    code, out = run_kit()
    assert code == EXIT_BLOCKED and "security audit" in out
    assert (workspace / "AGENTS.md").is_file()  # v1: the audit runs after the write
    assert any((workspace / ".kit").rglob("*.log"))
