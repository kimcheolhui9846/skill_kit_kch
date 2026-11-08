"""Step 3 (2026-11-08): MCP servers, Claude plugins, manual tools and remote-MCP guides.

The kit records these entries and prints commands; it never runs, installs or builds them.
Checks: every pinned entry has a matching sources.lock.json entry, risky or key-needing entries
are off, catalog/mcp.json is stdio only, manual guides are complete, no catalog holds a
secret-looking value, and a default install enables none of the new entries.
"""

from __future__ import annotations

import io
import json
import re

import pytest

from kit import capture, commands, mcp_catalog, sources
from kit.model import EXIT_READY
from tests.conftest import KIT_ROOT

NEW_SERVERS = ("codebase-memory", "markitdown", "inspo", "rea", "scrapling")
NEW_PLUGINS = ("filetree", "replay-theater", "savvy-progress", "effortless")
NEW_MANUAL = (
    "headroom",
    "rtk",
    "graphify",
    "claude-mem",
    "openrig",
    "ruflo",
    "bureau-des-agents",
    "mobbin",
    "nicelydone",
    "refero",
)
REMOTE_GUIDES = ("mobbin", "nicelydone", "refero")
CATALOGS = (mcp_catalog.MCP_REL, mcp_catalog.PLUGINS_REL, mcp_catalog.MANUAL_REL, sources.LOCK_REL)


def run(*argv):
    out = io.StringIO()
    return commands.run(list(argv[1:]), argv[0], KIT_ROOT, out), out.getvalue()


@pytest.fixture(scope="module")
def servers():
    return mcp_catalog.load_servers(KIT_ROOT)


@pytest.fixture(scope="module")
def plugins():
    return mcp_catalog.load_plugins(KIT_ROOT)[1]


@pytest.fixture(scope="module")
def manual():
    return mcp_catalog.load_manual(KIT_ROOT)


@pytest.fixture(scope="module")
def lock():
    return sources.load(KIT_ROOT)


def test_the_new_entries_are_there(servers, plugins, manual):
    assert set(NEW_SERVERS) <= set(servers)
    assert set(NEW_PLUGINS) <= set(plugins)
    assert set(NEW_MANUAL) | {"claude-code-router"} <= set(manual)
    assert not mcp_catalog.installable(servers["scrapling"])  # listed only


def test_context_mode_is_not_a_plugin(plugins):
    """ELv2 is not in the license table (kit.source_add.ALLOWED): reference only in 07."""
    assert "context-mode" not in plugins


def test_security_guidance_keeps_its_pin(plugins):
    assert plugins["security-guidance"]["source"]["sha"].startswith("ff920a4094a3")


def test_every_installable_server_matches_a_pinned_mcp_lock_entry(servers, lock):
    for name, entry in servers.items():
        if not mcp_catalog.installable(entry) or name == "sequential-thinking":
            continue  # sequential-thinking predates the lock and mirrors mcp/manifest.json
        src = lock[entry["source"]]
        assert src.kind == "mcp", name
        assert src.raw["version"] == entry["version"], name
        assert re.fullmatch(r"[0-9a-f]{40}", src.commit), name
        assert src.integration == "referenced" and src.files == {}, name


def test_every_plugin_matches_a_plugin_lock_entry(plugins, lock):
    for name, entry in plugins.items():
        src = lock[entry.get("lock", name)]
        assert src.kind == "plugin" and src.commit == entry["source"]["sha"], name
        assert src.integration == "referenced" and src.files == {}, name


@pytest.mark.parametrize("which", ["servers", "plugins"])
def test_high_risk_or_key_needing_entries_are_off(which, servers, plugins):
    catalog = servers if which == "servers" else plugins
    for name, entry in catalog.items():
        if entry["risk"] == "high" or entry.get("credentials"):
            assert entry["enabled_by_default"] is False, name
    new = NEW_SERVERS if which == "servers" else NEW_PLUGINS
    assert all(catalog[n]["enabled_by_default"] is False for n in new)


def test_mcp_catalog_is_stdio_only_with_no_remote_url(servers):
    raw = (KIT_ROOT / mcp_catalog.MCP_REL).read_text(encoding="utf-8")
    for name, entry in servers.items():
        assert entry["transport"] == "stdio", name
        assert not set(entry) & {"url", "headers", "bearer_token_env_var", "type"}, name
        if mcp_catalog.installable(entry):
            assert entry["command"] in ("npx", "uvx"), name
            assert not any("://" in a for a in entry["args"]), name
    for host in ("api.mobbin.com", "nicelydone.club", "api.refero.design", "--transport"):
        assert host not in raw


def test_remote_guides_print_claude_mcp_add_without_a_token(manual):
    for name in REMOTE_GUIDES:
        entry = manual[name]
        assert entry["agents"] == ["claude"] and entry["risk"] == "high"
        add = [s for s in entry["steps"] if s.startswith("claude mcp add --transport http ")]
        assert len(add) == 1, name
        assert re.match(rf"claude mcp add --transport http {name} https://\S+", add[0]), add[0]
        text = json.dumps(entry)
        assert "--header" not in add[0] and "Bearer" not in text, name
        assert any(u.startswith(f"claude mcp remove {name}") for u in entry["undo"]), name


def test_manual_guides_are_complete(manual):
    for name in NEW_MANUAL:
        entry = manual[name]
        for key in mcp_catalog.MANUAL_REQUIRED:
            assert entry.get(key), (name, key)
        assert entry["docs"].startswith("https://"), name
        assert entry["steps"][0].startswith("Read the risks above; the kit does not run"), name


def test_manual_guides_never_pipe_a_download_into_a_shell(manual):
    pipe = re.compile(r"\b(?:curl|wget|irm|iwr)\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b|\|\s*iex\b")
    for name, entry in manual.items():
        for line in entry["steps"] + entry["undo"]:
            assert not pipe.search(line), (name, line)


def test_partly_documented_undo_says_so(manual):
    for name in ("claude-mem", "openrig", "ruflo"):
        assert any("only partly documented upstream" in u for u in manual[name]["undo"]), name


def test_pinned_versions_appear_in_the_manual_steps(manual):
    for name in ("headroom", "graphify", "claude-mem", "openrig", "ruflo"):
        entry = manual[name]
        assert any(entry["version"] in s for s in entry["steps"]), name


@pytest.mark.parametrize("rel", CATALOGS)
def test_no_secret_looking_values_in_the_catalogs(rel):
    text = (KIT_ROOT / rel).read_text(encoding="utf-8")
    assert capture.scan(rel, text) == []


def test_credentials_are_names_only(servers, plugins):
    for entry in list(servers.values()) + list(plugins.values()):
        for need in entry.get("credentials") or []:
            assert set(need) <= {"env", "required", "purpose", "get_it", "cost"}
            assert need["required"] is False or entry["enabled_by_default"] is False


def test_prerelease_pin_is_exact(servers):
    assert servers["markitdown"]["args"] == ["markitdown-mcp==0.0.1a8"]
    assert mcp_catalog._VERSION.match("0.0.1a8") and mcp_catalog._VERSION.match("2.0rc1")
    for loose in ("latest", ">=0.0.1a8", "0.0.*", "^0.0.1a8"):
        assert not mcp_catalog._VERSION.match(loose), loose


@pytest.mark.parametrize("profile", [[], ["--profile", "python"], ["--profile", "full"]])
def test_default_install_enables_none_of_the_new_entries(workspace, profile):
    argv = ["install", "--agent", "both", *profile, "--offline", "--json"]
    code, out = run(workspace, *argv)
    assert code == EXIT_READY, out
    for agent in json.loads(out)["agents"].values():
        names = {s["name"] if isinstance(s, dict) else s for s in agent["mcp_servers"]}
        assert names <= {"sequential-thinking"}
        assert agent.get("plugins", []) == []
    text = "".join(
        (workspace / rel).read_text(encoding="utf-8")
        for rel in (".mcp.json", ".codex/config.toml")
        if (workspace / rel).is_file()
    )
    for name in NEW_SERVERS + NEW_PLUGINS + NEW_MANUAL:
        assert f'"{name}"' not in text and f"mcp_servers.{name}]" not in text, name
    assert not (workspace / ".claude/settings.json").exists()


@pytest.mark.parametrize("name", ["codebase-memory", "inspo"])
def test_opt_in_writes_only_a_pinned_stdio_server_and_env_names(workspace, name):
    code, out = run(workspace, "install", "--agent", "claude", "--mcp", name, "--offline")
    assert code == EXIT_READY, out
    doc = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    server = doc["mcpServers"][name]
    assert set(server) <= {"command", "args", "env"}
    for key, value in (server.get("env") or {}).items():
        assert value == "${" + key + "}"  # a reference, never a value


def test_manual_guide_prints_and_runs_nothing(workspace, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(a))
    argv = ["install", "--agent", "claude", "--offline"]
    for name in ("mobbin", "refero", "headroom"):
        argv += ["--manual", name]
    code, out = run(workspace, *argv)
    assert code == EXIT_READY, out
    assert "claude mcp add --transport http mobbin https://api.mobbin.com/mcp" in out
    assert "HEADROOM_TELEMETRY=off" in out
    assert calls == []
    mcp_json = workspace / ".mcp.json"
    assert not mcp_json.is_file() or "mobbin" not in mcp_json.read_text(encoding="utf-8")
