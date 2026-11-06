"""P4-T5 plugin install through the claude CLI (kit.plugin_install).

The CLI is faked: it behaves like Claude Code 2.1.319 did in an isolated CLAUDE_CONFIG_DIR
(marketplace add --scope local writes .claude/settings.local.json; plugin uninstall removes
the enabledPlugins key; marketplace remove leaves {"extraKnownMarketplaces": {}}). The real
claude and codex executables are blocked in tests (conftest NETWORK_COMMANDS), so nothing here
can touch ~/.claude.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import commands, plugin_install, tools
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY
from tests.catalog.kit_fixture import write

PLUGIN = "security-guidance"
PID = "security-guidance@hackathon-kit"
SETTINGS = ".claude/settings.json"
LOCAL = ".claude/settings.local.json"
SHA = "ff920a4094a341f282d5dee00daef2c3b8339c72"


def run(kit, workspace, *argv, ask=None):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out, ask), out.getvalue()


def _ok(command, **extra):
    return 0, json.dumps({"command": command, "outcome": "ok", "message": "done", **extra})


class FakeClaude:
    def __init__(self):
        self.calls = []
        self.installed = {}  # id -> project path
        self.fail = None  # subcommand to fail

    def __call__(self, cmd, timeout=600.0, cwd=None):
        args = cmd[1:]
        self.calls.append(args)
        cwd = Path(cwd)
        if self.fail and self.fail in " ".join(args):
            return 1, json.dumps({"command": "x", "outcome": "failed", "message": "boom"})
        if args[:3] == ["plugin", "marketplace", "add"]:
            path = cwd / LOCAL
            doc = json.loads(path.read_text("utf-8")) if path.exists() else {}
            doc.setdefault("extraKnownMarketplaces", {})["hackathon-kit"] = {
                "source": {"source": "directory", "path": args[3]}
            }
            write(cwd, LOCAL, json.dumps(doc, indent=2))
            return _ok("marketplace-add")
        if args[:2] == ["plugin", "install"]:
            self.installed[args[2]] = str(cwd)
            return _ok("install")
        if args[:2] == ["plugin", "list"]:
            listing = [
                {
                    "id": i,
                    "version": "2.0.17",
                    "scope": "project",
                    "enabled": True,
                    "installPath": "x",
                    "projectPath": p,
                }
                for i, p in self.installed.items()
            ]
            return 0, json.dumps(listing)
        if args[:2] == ["plugin", "uninstall"]:
            self.installed.pop(args[2], None)
            doc = json.loads((cwd / SETTINGS).read_text("utf-8"))
            doc.get("enabledPlugins", {}).pop(args[2], None)
            write(cwd, SETTINGS, json.dumps(doc, indent=2))
            return _ok("uninstall")
        if args[:3] == ["plugin", "marketplace", "remove"]:
            doc = json.loads((cwd / LOCAL).read_text("utf-8"))
            doc["extraKnownMarketplaces"].pop("hackathon-kit", None)
            write(cwd, LOCAL, json.dumps(doc, indent=2))
            return _ok("marketplace-remove")
        return 1, "unexpected"


@pytest.fixture
def claude(monkeypatch):
    fake = FakeClaude()
    monkeypatch.setattr(plugin_install, "find_claude", lambda: "/fake/claude")
    monkeypatch.setattr(tools, "run_command", fake)
    return fake


def items(out: str, agent="claude") -> dict:
    return {i["name"]: i for i in json.loads(out)["agents"][agent]["items"]}


def files_outside_kit(ws: Path):
    return sorted(
        p.relative_to(ws).as_posix() for p in ws.rglob("*") if p.is_file() and ".kit" not in p.parts
    )


# ---------------------------------------------------------------- install


def test_install_with_yes_installs_through_the_cli(kit, workspace, claude):
    code, out = run(
        kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes", "--json"
    )
    assert code == EXIT_READY, out
    market_dir = str(workspace / plugin_install.MARKETPLACE_DIR)
    assert claude.calls[:2] == [
        ["plugin", "marketplace", "add", market_dir, "--scope", "local", "--json"],
        ["plugin", "install", PID, "--scope", "project", "--json"],
    ]
    found = items(out)
    assert found[f"plugin:{PLUGIN}"]["verified"] == "PASS"
    assert found[plugin_install.MARKETPLACE_REL]["verified"] == "PASS"
    market = json.loads((workspace / plugin_install.MARKETPLACE_REL).read_text("utf-8"))
    assert market["name"] == "hackathon-kit"
    assert market["plugins"][0]["source"]["sha"] == SHA
    assert market["plugins"][0]["source"]["url"].startswith("https://")
    man = json.loads((workspace / ".kit/state/install-manifest.json").read_text("utf-8"))
    record = man["installs"][0]["plugin_installs"]
    assert record == [
        {"marketplace": "hackathon-kit", "scope": "local", "created_local_settings": True},
        {"id": PID, "scope": "project"},
    ]
    # the shared file keeps the portable inline declaration; the local path stays personal
    shared = json.loads((workspace / SETTINGS).read_text("utf-8"))
    assert shared["extraKnownMarketplaces"]["hackathon-kit"]["source"]["source"] == "settings"


def test_network_need_lists_the_cli_commands(kit, workspace, claude):
    code, out = run(kit, workspace, "plan", "--agent", "claude", "--plugin", PLUGIN, "--json")
    assert code == EXIT_READY
    needs = json.loads(out)["network"]["needs"]
    need = next(n for n in needs if n["for"].startswith("claude plugins"))
    assert "~/.claude/plugins/" in need["for"] and LOCAL in need["for"]
    assert f"claude plugin install {PID} --scope project --json" in need["command"]
    assert claude.calls == []


@pytest.mark.parametrize(
    "flags, reason",
    [([], "needs --yes (network)"), (["--offline"], "--offline")],
)
def test_without_network_permission_nothing_runs(kit, workspace, claude, flags, reason):
    code, out = run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, *flags)
    assert claude.calls == []
    assert code == EXIT_READY  # optional item skipped
    assert "Install plugins: re-run with --yes, or run claude plugin marketplace add" in out
    code, out = run(
        kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, *flags, "--json"
    )
    assert reason in items(out)[f"plugin:{PLUGIN}"]["detail"]
    assert (workspace / SETTINGS).is_file()  # the declaration is still written


def test_declined_prompt_runs_nothing_and_confirmed_prompt_installs(kit, workspace, claude):
    argv = ("install", "--agent", "claude", "--plugin", PLUGIN)
    asked = []
    run(kit, workspace, *argv, ask=lambda q: asked.append(q) or "n")
    assert claude.calls == [] and "~/.claude/plugins/" in asked[0]
    code, _ = run(kit, workspace, *argv, ask=lambda q: "y")
    assert code == EXIT_READY
    assert ["plugin", "install", PID, "--scope", "project", "--json"] in claude.calls


def test_missing_cli_is_reported(kit, workspace, claude, monkeypatch):
    monkeypatch.setattr(plugin_install, "find_claude", lambda: None)
    code, out = run(
        kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes", "--json"
    )
    assert code == EXIT_PARTIAL
    assert "claude CLI not found" in items(out)[f"plugin:{PLUGIN}"]["detail"]


@pytest.mark.parametrize("step", ["marketplace add", "plugin install"])
def test_cli_failure_is_reported(kit, workspace, claude, step):
    claude.fail = step
    code, out = run(
        kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes", "--json"
    )
    assert code == EXIT_PARTIAL
    assert items(out)[f"plugin:{PLUGIN}"]["verified"] == "FAIL"
    assert "boom" in items(out)[f"plugin:{PLUGIN}"]["detail"]


def test_no_cli_call_without_plugin(kit, workspace, claude):
    assert run(kit, workspace, "install", "--agent", "both", "--yes")[0] == EXIT_READY
    assert claude.calls == []


# ---------------------------------------------------------------- verify


def test_verify_reads_claude_plugin_list(kit, workspace, claude):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes")
    code, out = run(kit, workspace, "verify", "--agent", "claude", "--json")
    assert code == EXIT_READY, out
    assert items(out)[f"plugin:{PLUGIN}"]["detail"] == "installed 2.0.17 (scope project)"
    assert ["plugin", "list", "--json"] in claude.calls
    claude.installed.clear()  # removed outside the kit
    code, out = run(kit, workspace, "verify", "--agent", "claude", "--json")
    assert code == 1
    assert "not installed" in items(out)[f"plugin:{PLUGIN}"]["detail"]


# ---------------------------------------------------------------- uninstall


def test_uninstall_undoes_the_cli_install_and_leaves_nothing(kit, workspace, claude):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes")
    claude.calls.clear()
    code, out = run(kit, workspace, "uninstall", "--agent", "claude")
    assert code == EXIT_READY, out
    assert claude.calls == [
        ["plugin", "uninstall", PID, "--scope", "project", "--json"],
        ["plugin", "marketplace", "remove", "hackathon-kit", "--scope", "local", "--json"],
    ]
    assert claude.installed == {}
    assert files_outside_kit(workspace) == []
    assert not (workspace / plugin_install.MARKETPLACE_REL).exists()


@pytest.mark.parametrize(
    "original",
    [{"permissions": {"allow": ["Bash(ls)"]}}, {"extraKnownMarketplaces": {}}],
)
def test_uninstall_keeps_a_local_settings_file_the_user_had(kit, workspace, claude, original):
    """Even a user file that is only empty objects stays: the kit did not create it."""
    write(workspace, LOCAL, json.dumps(original))
    run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes")
    man = json.loads((workspace / ".kit/state/install-manifest.json").read_text("utf-8"))
    assert man["installs"][0]["plugin_installs"][0]["created_local_settings"] is False
    assert run(kit, workspace, "uninstall", "--agent", "claude")[0] == EXIT_READY
    left = json.loads((workspace / LOCAL).read_text("utf-8"))
    # the user's keys stay; the claude CLI leaves an empty extraKnownMarketplaces behind
    assert {k: v for k, v in left.items() if v != {}} == {
        k: v for k, v in original.items() if v != {}
    }


def test_uninstall_dry_run_runs_no_cli(kit, workspace, claude):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes")
    claude.calls.clear()
    code, out = run(kit, workspace, "uninstall", "--agent", "claude", "--dry-run")
    assert code == EXIT_READY
    assert claude.calls == []
    assert f"Would run: claude plugin uninstall {PID} --scope project --json" in out


def test_uninstall_reports_a_cli_failure(kit, workspace, claude):
    run(kit, workspace, "install", "--agent", "claude", "--plugin", PLUGIN, "--yes")
    claude.fail = "plugin uninstall"
    code, out = run(kit, workspace, "uninstall", "--agent", "claude")
    assert code == EXIT_BLOCKED
    assert f"claude plugin uninstall {PID} --scope project --json: boom" in out


# ---------------------------------------------------------------- Codex (codex-cli 0.166.0 shapes)

CODEX_PLUGIN = "demo-codex"
CODEX_PID = "demo-codex@hackathon-kit"
SP_SHA = "22f0b463e7a5e579904dd6211a520321035526f7"
CODEX_MARKET = plugin_install.CODEX_MARKETPLACE_REL


def add_codex_plugin(kit: Path, agents=("codex",)) -> None:
    """A Codex plugin entry and its referenced lock entry in the kit copy."""
    from kit.sources import digest

    catalog = json.loads((kit / "catalog/plugins.json").read_text("utf-8"))
    catalog["plugins"][CODEX_PLUGIN] = {
        "agents": list(agents),
        "policies": ["standard"],
        "license": "MIT",
        "origin": "https://github.com/obra/superpowers",
        "source": {
            "source": "url",
            "url": "https://github.com/obra/superpowers.git",
            "sha": SP_SHA,
        },
        "category": "Developer Tools",
        "risk": "medium",
        "enabled_by_default": False,
        "disabled_reason": "test entry. Opt in with --plugin demo-codex",
        "network_egress": "git clone of the pinned commit",
        "file_access": "none",
    }
    write(kit, "catalog/plugins.json", json.dumps(catalog, indent=2))
    lock = json.loads((kit / "sources.lock.json").read_text("utf-8"))
    lock["sources"].append(
        {
            "id": CODEX_PLUGIN,
            "kind": "plugin",
            "origin": "https://github.com/obra/superpowers",
            "commit": SP_SHA,
            "license": "MIT",
            "license_file": None,
            "integration": "referenced",
            "agents": list(agents),
            "scope": ["user"],
            "risk": "medium",
            "files": {},
            "content_sha256": digest({}),
        }
    )
    write(kit, "sources.lock.json", json.dumps(lock, indent=2))


class FakeCodex:
    def __init__(self):
        self.calls = []
        self.installed = set()
        self.fail = None
        self.listed_as = True  # what `plugin list` says in "installed"

    def __call__(self, cmd, timeout=600.0, cwd=None):
        args = cmd[1:]
        self.calls.append(args)
        if self.fail and self.fail in " ".join(args):
            return 1, "Error: boom"
        if args[:3] == ["plugin", "marketplace", "add"]:
            body = {"marketplaceName": "hackathon-kit", "installedRoot": args[3]}
            return 0, json.dumps({**body, "alreadyAdded": False}, indent=2)
        if args[:2] == ["plugin", "add"]:
            self.installed.add(args[2])
            return 0, json.dumps({"pluginId": args[2], "version": "7.0.2"}, indent=2)
        if args[:2] == ["plugin", "list"]:
            listing = [
                {"pluginId": i, "version": "7.0.2", "installed": self.listed_as, "enabled": True}
                for i in sorted(self.installed)
            ]
            return 0, "WARNING: x\n" + json.dumps({"installed": listing, "available": []})
        if args[:2] == ["plugin", "remove"]:
            self.installed.discard(args[2])
            return 0, json.dumps({"pluginId": args[2]}, indent=2)
        if args[:3] == ["plugin", "marketplace", "remove"]:
            return 0, json.dumps({"marketplaceName": args[3]}, indent=2)
        return 1, "unexpected"


@pytest.fixture
def clis(monkeypatch):
    """Both fake CLIs behind one run_command."""
    fake_claude, fake_codex = FakeClaude(), FakeCodex()
    monkeypatch.setattr(plugin_install, "find_claude", lambda: "/fake/claude")
    monkeypatch.setattr(plugin_install, "find_codex", lambda: "/fake/codex")

    def runner(cmd, timeout=600.0, cwd=None):
        fake = fake_codex if Path(cmd[0]).name == "codex" else fake_claude
        return fake(cmd, timeout, cwd)

    monkeypatch.setattr(tools, "run_command", runner)
    return fake_claude, fake_codex


def test_codex_plugin_installs_through_the_codex_cli(kit, workspace, clis):
    _, codex = clis
    add_codex_plugin(kit)
    code, out = run(
        kit, workspace, "install", "--agent", "codex", "--plugin", CODEX_PLUGIN, "--yes", "--json"
    )
    assert code == EXIT_READY, out
    assert codex.calls == [
        ["plugin", "marketplace", "add", str(workspace), "--json"],
        ["plugin", "add", CODEX_PID, "--json"],
    ]
    found = items(out, "codex")
    assert found[f"plugin:{CODEX_PLUGIN}"]["detail"] == f"{CODEX_PID} 7.0.2"
    assert found[CODEX_MARKET]["verified"] == "PASS"
    market = json.loads((workspace / CODEX_MARKET).read_text("utf-8"))
    entry = market["plugins"][0]
    assert market["name"] == "hackathon-kit"
    assert entry["source"] == {
        "source": "url",
        "url": "https://github.com/obra/superpowers.git",
        "sha": SP_SHA,
    }
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Developer Tools"
    man = json.loads((workspace / ".kit/state/install-manifest.json").read_text("utf-8"))
    assert man["installs"][0]["plugin_installs"] == [
        {"marketplace": "hackathon-kit", "scope": "user"},
        {"id": CODEX_PID, "scope": "user"},
    ]


def test_codex_network_need_says_it_is_user_wide(kit, workspace, clis):
    add_codex_plugin(kit)
    code, out = run(kit, workspace, "plan", "--agent", "codex", "--plugin", CODEX_PLUGIN, "--json")
    need = next(n for n in json.loads(out)["network"]["needs"] if n["for"].startswith("codex"))
    assert "~/.codex/config.toml" in need["for"] and "every project" in need["for"]
    assert f"codex plugin add {CODEX_PID} --json" in need["command"]


def test_each_agent_gets_only_its_own_plugins(kit, workspace, clis):
    """TC-ADP-01 for plugins: a Codex-only plugin never reaches Claude, and the reverse."""
    claude, codex = clis
    add_codex_plugin(kit)
    argv = ("install", "--agent", "both", "--plugin", CODEX_PLUGIN, "--plugin", PLUGIN, "--yes")
    code, out = run(kit, workspace, *argv)
    assert code == EXIT_READY, out
    assert ["plugin", "add", CODEX_PID, "--json"] in codex.calls
    assert not any(PID in " ".join(c) for c in codex.calls)
    assert ["plugin", "install", PID, "--scope", "project", "--json"] in claude.calls
    assert not any(CODEX_PID in " ".join(c) for c in claude.calls)
    shared = json.loads((workspace / SETTINGS).read_text("utf-8"))
    assert list(shared["enabledPlugins"]) == [PID]
    codex_market = json.loads((workspace / CODEX_MARKET).read_text("utf-8"))
    assert [p["name"] for p in codex_market["plugins"]] == [CODEX_PLUGIN]


def test_codex_verify_and_uninstall(kit, workspace, clis):
    _, codex = clis
    add_codex_plugin(kit)
    run(kit, workspace, "install", "--agent", "codex", "--plugin", CODEX_PLUGIN, "--yes")
    code, out = run(kit, workspace, "verify", "--agent", "codex", "--json")
    assert code == EXIT_READY, out
    detail = items(out, "codex")[f"plugin:{CODEX_PLUGIN}"]["detail"]
    assert detail == "installed 7.0.2 (user, every project)"
    codex.calls.clear()
    code, out = run(kit, workspace, "uninstall", "--agent", "codex")
    assert code == EXIT_READY, out
    assert codex.calls == [
        ["plugin", "remove", CODEX_PID, "--json"],
        ["plugin", "marketplace", "remove", "hackathon-kit", "--json"],
    ]
    assert codex.installed == set()
    assert files_outside_kit(workspace) == []


def test_codex_cli_missing_or_failing(kit, workspace, clis, monkeypatch):
    _, codex = clis
    add_codex_plugin(kit)
    argv = ("install", "--agent", "codex", "--plugin", CODEX_PLUGIN, "--yes", "--json")
    codex.fail = "plugin add"
    code, out = run(kit, workspace, *argv)
    assert code == EXIT_PARTIAL
    assert items(out, "codex")[f"plugin:{CODEX_PLUGIN}"]["detail"] == "Error: boom"
    monkeypatch.setattr(plugin_install, "find_codex", lambda: None)
    code, out = run(kit, workspace, *argv)
    assert "codex CLI not found" in items(out, "codex")[f"plugin:{CODEX_PLUGIN}"]["detail"]


def test_codex_listed_but_not_installed_fails_verify(kit, workspace, clis):
    _, codex = clis
    add_codex_plugin(kit)
    run(kit, workspace, "install", "--agent", "codex", "--plugin", CODEX_PLUGIN, "--yes")
    codex.listed_as = False
    code, out = run(kit, workspace, "verify", "--agent", "codex", "--json")
    assert code != EXIT_READY
    item = items(out, "codex")[f"plugin:{CODEX_PLUGIN}"]
    assert item["verified"] == "FAIL" and item["detail"].startswith("not installed")
