"""P4-T5 MCP and plugin catalogs (REQ-SAFE-009, REQ-ARCH-002, ADR-010, TC-ADP-01, TC-SRC-01).

catalog/mcp.json and catalog/plugins.json are read only by the new path. Rules: stdio only,
allowed commands, exact version pins that match sources.lock.json, high risk never on by
default, off-by-default entries need --mcp/--plugin, plugins are declared (never installed)
and only for Claude Code.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import commands, mcp_catalog
from kit.mcp_catalog import CatalogError
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_USAGE
from tests.catalog.kit_fixture import write
from tests.conftest import TOML_PASS, tree_digest

SETTINGS = ".claude/settings.json"
PLUGIN_ID = "security-guidance@hackathon-kit"


def run(kit, workspace, *argv):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out), out.getvalue()


def edit(kit: Path, rel: str, change) -> None:
    data = json.loads((kit / rel).read_text(encoding="utf-8"))
    change(data)
    write(kit, rel, json.dumps(data, indent=2))


def server(kit: Path, name: str, **fields) -> None:
    def change(data):
        data["servers"][name].update(fields)
        for key, value in fields.items():
            if value is None and key not in ("disabled_reason",):
                del data["servers"][name][key]

    edit(kit, mcp_catalog.MCP_REL, change)


def plugin(kit: Path, **fields) -> None:
    def change(data):
        entry = data["plugins"]["security-guidance"]
        for key, value in fields.items():
            if key == "sha":
                entry["source"]["sha"] = value
            else:
                entry[key] = value

    edit(kit, mcp_catalog.PLUGINS_REL, change)


def browser_pack(kit: Path) -> None:
    """A pack that lists playwright (off by default) in its MCP list."""
    pack = {"schema": 2, "kind": "pack", "name": "browser", "mcp": {"shared": ["playwright"]}}
    write(kit, "profiles/packs/browser.json", json.dumps(pack))


# ---------------------------------------------------------------- the shipped catalogs


def test_shipped_catalogs_load(kit_root):
    servers = mcp_catalog.load_servers(kit_root)
    installable = sorted(n for n, e in servers.items() if mcp_catalog.installable(e))
    assert installable == [
        "codebase-memory",
        "context7",
        "inspo",
        "markitdown",
        "playwright",
        "rea",
        "sequential-thinking",
    ]  # step 3 (2026-11-08) added codebase-memory, inspo, markitdown and rea, all off
    assert servers["context7"]["enabled_by_default"] is False  # needs a key (P4-T9)
    assert servers["context7"]["args"] == ["-y", "@upstash/context7-mcp@4.5.1"]
    for name in ("fetch", "git", "filesystem"):
        assert servers[name]["enabled_by_default"] is False
        assert not mcp_catalog.installable(servers[name])
    assert servers["playwright"]["enabled_by_default"] is False
    assert servers["playwright"]["args"] == ["-y", "@playwright/mcp@0.0.84"]
    market, plugins = mcp_catalog.load_plugins(kit_root)
    assert market == "hackathon-kit"
    assert plugins["security-guidance"]["enabled_by_default"] is False
    assert plugins["security-guidance"]["agents"] == ["claude"]


def test_every_high_risk_entry_is_off_by_default(kit_root):
    _, plugins = mcp_catalog.load_plugins(kit_root)
    entries = list(mcp_catalog.load_servers(kit_root).values()) + list(plugins.values())
    high = [e for e in entries if e["risk"] == "high"]
    assert high and all(e["enabled_by_default"] is False for e in high)


def test_sequential_thinking_matches_the_legacy_manifest(kit_root):
    """Same command line as mcp/manifest.json, so the new path renders the same block."""
    legacy = json.loads((kit_root / "mcp/manifest.json").read_text(encoding="utf-8"))
    old = legacy["servers"]["sequential-thinking"]
    new = mcp_catalog.load_servers(kit_root)["sequential-thinking"]
    for key in ("command", "args", "startup_timeout_sec", "version"):
        assert new[key] == old[key]


# ---------------------------------------------------------------- validation (BLOCKED)


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"risk": "high", "enabled_by_default": True, "disabled_reason": None}, "high-risk"),
        ({"disabled_reason": None}, "needs a disabled_reason"),
        ({"disabled_reason": "  "}, "needs a disabled_reason"),
        ({"command": "bash"}, "not in mcp/allowlist.json"),
        ({"version": "latest"}, "pinned exactly"),
        ({"version": "^0.0.84"}, "pinned exactly"),
        ({"version": "~0.0.84"}, "pinned exactly"),
        ({"version": None}, "pinned exactly"),
        ({"args": ["-y", "@playwright/mcp@latest"]}, "must run the pinned"),
        ({"args": ["-y", "@playwright/mcp"]}, "must run the pinned"),
        ({"transport": "http"}, "only stdio"),
        ({"url": "https://example.invalid/mcp"}, "not allowed (remote"),
        ({"env": ["GITHUB_TOKEN"]}, "looks like a secret"),
        ({"network_egress": ""}, "network_egress must describe"),
        ({"agents": ["gemini"]}, "agents must be"),
        ({"policies": []}, "policies must be"),
        ({"version": "0.0.85", "args": ["-y", "@playwright/mcp@0.0.85"]}, "differs from"),
        ({"source": "superpowers-core"}, "not an mcp lock entry"),
    ],
)
def test_bad_server_entry_is_refused(kit, fields, message):
    server(kit, "playwright", **fields)
    with pytest.raises(CatalogError, match=message.replace("(", r"\(").replace("^", r"\^")):
        mcp_catalog.load_servers(kit)


def test_listed_only_server_cannot_be_on_by_default(kit):
    server(kit, "filesystem", enabled_by_default=True, disabled_reason=None)
    with pytest.raises(CatalogError, match="listed-only"):
        mcp_catalog.load_servers(kit)


@pytest.mark.parametrize(
    "fields, message",
    [
        ({"sha": "ff920a4"}, "40-character sha"),
        ({"sha": "main"}, "40-character sha"),
        ({"sha": "0" * 40}, "sha differs from sources.lock.json"),
        (
            {
                "agents": ["codex", "claude"],
                "source": {
                    "source": "github",
                    "repo": "o/r",
                    "sha": "ff920a4094a341f282d5dee00daef2c3b8339c72",
                },
            },
            "codex does not take a 'github' plugin source",
        ),
        ({"enabled_by_default": True, "disabled_reason": None}, "high-risk"),
        ({"source": {"source": "npm", "package": "x"}}, "github, url or git-subdir"),
        ({"category": 3}, "category must be text"),
        (
            {
                "source": {
                    "source": "git-subdir",
                    "url": "anthropics/claude-plugins-official",
                    "path": "plugins/security-guidance",
                    "sha": "ff920a4094a341f282d5dee00daef2c3b8339c72",
                }
            },
            "full https:// URL",
        ),
    ],
)
def test_bad_plugin_entry_is_refused(kit, fields, message):
    plugin(kit, **fields)
    with pytest.raises(CatalogError, match=message):
        mcp_catalog.load_plugins(kit)


def test_broken_catalog_blocks_install_before_writing(kit, workspace):
    server(kit, "playwright", version="latest")
    before = tree_digest(workspace)
    code, _ = run(kit, workspace, "install", "--agent", "claude")
    assert code == EXIT_BLOCKED
    assert tree_digest(workspace) == before


# ---------------------------------------------------------------- selection


def test_off_by_default_server_in_a_profile_needs_opt_in(kit, workspace):
    browser_pack(kit)
    code, out = run(
        kit, workspace, "install", "--agent", "both", "--profile", "core,browser", "--json"
    )
    assert code == EXIT_READY, out
    for agent in json.loads(out)["agents"].values():
        assert agent["mcp_servers"] == []
        assert agent["skipped_mcp"] == ["playwright (off by default; add --mcp playwright)"]
    assert not (workspace / ".mcp.json").exists()
    assert not (workspace / ".codex/config.toml").exists()


def test_opt_in_registers_the_pinned_server_for_both_agents(kit, workspace):
    code, out = run(kit, workspace, "install", "--agent", "both", "--mcp", "playwright")
    assert code == EXIT_READY, out
    mcp_json = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp_json == {
        "mcpServers": {"playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@0.0.84"]}}
    }
    toml = (workspace / ".codex/config.toml").read_text(encoding="utf-8")
    assert (
        '[mcp_servers.playwright]\ncommand = "npx"\nargs = ["-y", "@playwright/mcp@0.0.84"]' in toml
    )
    assert "startup_timeout_sec = 60" in toml
    assert "opted in; network: npm registry" in out


def test_opt_in_server_is_listed_as_a_network_need(kit, workspace):
    code, out = run(kit, workspace, "plan", "--agent", "codex", "--mcp", "playwright", "--json")
    assert code == EXIT_READY
    needs = json.loads(out)["network"]["needs"]
    assert {"for": "MCP check for codex", "command": "npx -y @playwright/mcp@0.0.84"} in needs


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--agent", "codex", "--mcp", "nope"], "unknown mcp 'nope'"),
        (["--agent", "codex", "--mcp", "fetch"], "listed only"),
        (["--agent", "codex", "--plugin", "nope"], "unknown plugin 'nope'"),
        (["--agent", "codex", "--plugin", "security-guidance"], "not for codex"),
        (["--agent", "codex", "--mcp", "playwright", "--policy", "restricted"], "restricted"),
        (["--agent", "codex", "--mcp", "playwright", "--no-mcp"], "cannot be combined"),
        (["--agent", "codex", "--mcp", ""], "need a name"),
    ],
)
def test_bad_opt_in_is_a_usage_error(kit, workspace, capsys, argv, message):
    before = tree_digest(workspace)
    code, _ = run(kit, workspace, "install", *argv)
    assert code == EXIT_USAGE
    assert message in capsys.readouterr().err
    assert tree_digest(workspace) == before


@pytest.mark.parametrize("flag", ["--mcp", "--plugin"])
def test_unknown_name_points_at_a_catalog_file_that_exists(kit, workspace, capsys, flag):
    """P7-T1: --plugin used to point at catalog/plugin.json; the file is plugins.json."""
    assert run(kit, workspace, "install", "--agent", "claude", flag, "nope")[0] == EXIT_USAGE
    err = capsys.readouterr().err
    named = err.split("(see ", 1)[1].split(")", 1)[0]
    assert (kit / named).is_file(), named


def test_profile_with_unknown_server_is_a_usage_error(kit, workspace):
    pack = {"schema": 2, "kind": "pack", "name": "odd", "mcp": {"shared": ["evil-server"]}}
    write(kit, "profiles/packs/odd.json", json.dumps(pack))
    assert run(kit, workspace, "install", "--agent", "codex", "--profile", "core,odd")[0] == 64


# ---------------------------------------------------------------- plugins (Claude Code)


def test_plugin_is_declared_for_claude_only(kit, workspace):
    """TC-ADP-01: an agent-specific entry never reaches the other agent's files."""
    code, out = run(kit, workspace, "install", "--agent", "both", "--plugin", "security-guidance")
    assert code == EXIT_READY, out
    doc = json.loads((workspace / SETTINGS).read_text(encoding="utf-8"))
    assert doc["enabledPlugins"] == {PLUGIN_ID: True}
    market = doc["extraKnownMarketplaces"]["hackathon-kit"]["source"]
    assert market["source"] == "settings" and market["name"] == "hackathon-kit"
    assert market["plugins"] == [
        {
            "name": "security-guidance",
            "source": {
                "source": "git-subdir",
                "url": "https://github.com/anthropics/claude-plugins-official",
                "path": "plugins/security-guidance",
                "sha": "ff920a4094a341f282d5dee00daef2c3b8339c72",
            },
        }
    ]
    assert not (workspace / ".claude/settings.local.json").exists()
    codex_text = "".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in [workspace / "AGENTS.md", *(workspace / ".agents").rglob("*")]
        if p.is_file()
    )
    assert "security-guidance" not in codex_text and "hackathon-kit@" not in codex_text
    assert not (workspace / ".codex").exists()
    assert "Skipped plugins: security-guidance (not for codex)" in out
    assert f"/plugin install {PLUGIN_ID}" in out


def test_no_plugin_without_opt_in(kit, workspace):
    code, out = run(kit, workspace, "install", "--agent", "claude", "--json")
    assert code == EXIT_READY
    assert json.loads(out)["agents"]["claude"]["plugins"] == []
    assert not (workspace / SETTINGS).exists()


def test_plan_with_plugin_writes_nothing(kit, workspace):
    before = tree_digest(workspace)
    code, out = run(kit, workspace, "plan", "--agent", "claude", "--plugin", "security-guidance")
    assert code == EXIT_READY
    assert f"CREATE    {SETTINGS}" in out
    assert tree_digest(workspace) == before


def test_user_settings_survive_install_and_uninstall(kit, workspace):
    original = json.dumps({"permissions": {"allow": ["Bash(ls)"]}}, indent=2) + "\n"
    write(workspace, SETTINGS, original)
    assert (
        run(kit, workspace, "install", "--agent", "claude", "--plugin", "security-guidance")[0] == 0
    )
    doc = json.loads((workspace / SETTINGS).read_text(encoding="utf-8"))
    assert doc["permissions"] == {"allow": ["Bash(ls)"]}
    assert run(kit, workspace, "uninstall", "--agent", "claude")[0] == EXIT_READY
    assert (workspace / SETTINGS).read_text(encoding="utf-8") == original


def test_kit_created_settings_file_is_removed_on_uninstall(kit, workspace):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", "security-guidance")
    assert run(kit, workspace, "uninstall", "--agent", "claude")[0] == EXIT_READY
    assert not (workspace / SETTINGS).exists()


def test_user_changed_plugin_key_is_left_and_reported(kit, workspace):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", "security-guidance")
    path = workspace / SETTINGS
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["enabledPlugins"][PLUGIN_ID] = False
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    code, out = run(kit, workspace, "uninstall", "--agent", "claude")
    assert code == EXIT_BLOCKED
    assert f"/enabledPlugins/{PLUGIN_ID}" in out
    left = json.loads(path.read_text(encoding="utf-8"))
    assert left == {"enabledPlugins": {PLUGIN_ID: False}}


def test_existing_user_plugin_key_is_a_conflict(kit, workspace):
    """Optional item, like an .mcp.json conflict: PARTIAL, and the user's file is untouched."""
    original = json.dumps({"enabledPlugins": {PLUGIN_ID: False}})
    write(workspace, SETTINGS, original)
    code, out = run(kit, workspace, "install", "--agent", "claude", "--plugin", "security-guidance")
    assert code == EXIT_PARTIAL
    assert f"CONFLICT   optional [claude] plugin-config  ({SETTINGS}: " in out
    assert "not owned by the kit" in out
    assert (workspace / SETTINGS).read_text(encoding="utf-8") == original


# ---------------------------------------------------------------- verify / update / audit


def test_verify_and_update_keep_the_install_choices(kit, workspace):
    argv = ("--agent", "both", "--mcp", "playwright", "--plugin", "security-guidance")
    assert run(kit, workspace, "install", *argv)[0] == EXIT_READY
    man = json.loads((workspace / ".kit/state/install-manifest.json").read_text("utf-8"))
    for entry in man["installs"]:
        assert entry["opt_in"] == {"mcp": ["playwright"], "plugins": ["security-guidance"]}
    for command in ("verify", "update"):
        code, out = run(kit, workspace, command, "--agent", "both", "--offline", "--json")
        assert code == EXIT_READY, out
        data = json.loads(out)  # one document: both agents checked as one group
        items = {
            a: {i["name"]: i["verified"] for i in v["items"]} for a, v in data["agents"].items()
        }
        assert items["codex"]["mcp-config"] == TOML_PASS
        assert items["claude"]["mcp-config"] == "PASS"
        assert items["claude"]["plugin-config"] == "PASS"
        assert items["claude"]["security audit"] == "PASS"
        assert items["codex"]["security audit"] == TOML_PASS
        assert "plugin-config" not in items["codex"]
    assert (workspace / SETTINGS).is_file()


def test_verify_reports_a_removed_plugin_declaration(kit, workspace):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", "security-guidance")
    path = workspace / SETTINGS
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["enabledPlugins"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    code, out = run(kit, workspace, "verify", "--agent", "claude", "--offline")
    assert code == 1
    assert f"/enabledPlugins/{PLUGIN_ID} missing" in out


def test_audit_still_flags_servers_outside_the_catalog(kit, workspace):
    run(kit, workspace, "install", "--agent", "claude", "--mcp", "playwright")
    path = workspace / ".mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["mcpServers"]["mine"] = {"command": "npx", "args": ["-y", "something"]}
    path.write_text(json.dumps(doc), encoding="utf-8")
    code, out = run(kit, workspace, "verify", "--agent", "claude", "--offline", "--json")
    items = {i["name"]: i for i in json.loads(out)["agents"]["claude"]["items"]}
    assert items["security audit"]["verified"] == "FAIL"
    assert "mine: not in mcp/allowlist.json" in items["security audit"]["detail"]
    assert code == 1
