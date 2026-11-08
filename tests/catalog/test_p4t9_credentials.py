"""P4-T9: API keys are set later, by name only (00_PROMPT §15).

A catalog entry lists the keys it needs ("credentials"). The kit:
- keeps such entries off by default (servers, plugins) or out of the default packs (skills),
- writes references only (Codex env_vars, Claude "${NAME}"), never a value,
- lets the audit accept exactly those references and nothing else,
- prints where to create each key and how to set it, and whether it is set, never the value.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from kit import audit, commands, credentials, mcp_catalog, mcpconfig, mcpjson
from kit.adapters.user import claude_mcp_commands
from kit.catalog import CatalogError as SkillCatalogError
from kit.catalog import load as load_skills
from kit.logs import mask
from kit.mcp_catalog import CatalogError
from kit.model import EXIT_READY
from tests.catalog.kit_fixture import write

KEY = "PLAYWRIGHT_DEMO_API_KEY"
SECRET = "sk-test-0123456789abcdef"
NEED = {
    "env": KEY,
    "required": True,
    "purpose": "demo service",
    "get_it": "https://example.com/keys",
    "cost": "free tier",
}


def run(kit, workspace, *argv):
    out = io.StringIO()
    return commands.run(list(argv), workspace, kit, out), out.getvalue()


def edit(kit: Path, rel: str, change) -> None:
    data = json.loads((kit / rel).read_text(encoding="utf-8"))
    change(data)
    write(kit, rel, json.dumps(data, indent=2))


def keyed_playwright(kit: Path, **need) -> None:
    def change(data):
        data["servers"]["playwright"]["credentials"] = [{**NEED, **need}]

    edit(kit, mcp_catalog.MCP_REL, change)


# ---------------------------------------------------------------- validation


@pytest.mark.parametrize(
    "value, message",
    [
        ("KEY", "must be a list"),
        (["KEY"], "must be an object"),
        ([{**NEED, "value": "x"}], "unknown credential field(s) value"),
        ([{**NEED, "env": "lower_key"}], "UPPER_SNAKE"),
        ([{**NEED, "env": "A=B"}], "UPPER_SNAKE"),
        ([NEED, NEED], "listed twice"),
        ([{**NEED, "required": "yes"}], "required must be true or false"),
        ([{**NEED, "purpose": " "}], "purpose is required"),
        ([{**NEED, "get_it": "http://example.com"}], "https://"),
        ([{**NEED, "get_it": "https://a b"}], "https://"),
        ([{**NEED, "cost": ""}], "cost must be text"),
    ],
)
def test_bad_credentials_are_refused(value, message):
    with pytest.raises(credentials.CredentialError, match=re.escape(message)):
        credentials.parse("x", value)


def test_good_credentials_parse():
    assert credentials.parse("x", None) == []
    assert credentials.parse("x", [NEED]) == [NEED]
    no_cost = {k: v for k, v in NEED.items() if k != "cost"}
    assert credentials.parse("x", [no_cost]) == [no_cost]


def test_bad_credentials_in_the_mcp_catalog_block(kit):
    keyed_playwright(kit, get_it="ftp://x")
    with pytest.raises(CatalogError, match="get_it"):
        mcp_catalog.load_servers(kit)


def test_a_keyed_server_or_plugin_stays_off_by_default(kit):
    def server_on(data):
        entry = data["servers"]["sequential-thinking"]
        entry["credentials"] = [NEED]

    edit(kit, mcp_catalog.MCP_REL, server_on)
    with pytest.raises(CatalogError, match="stays off by default"):
        mcp_catalog.load_servers(kit)


def test_a_keyed_plugin_stays_off_by_default(kit):
    def plugin_on(data):
        entry = data["plugins"]["security-guidance"]
        entry.update(enabled_by_default=True, disabled_reason=None, risk="medium")

    edit(kit, mcp_catalog.PLUGINS_REL, plugin_on)
    with pytest.raises(CatalogError, match="stays off by default"):
        mcp_catalog.load_plugins(kit)


def _skill_need(kit: Path, name: str, packs=None) -> None:
    def change(data):
        for entry in data["skills"]:
            if entry["name"] == name:
                entry["credentials"] = [NEED]
                if packs is not None:
                    entry["packs"] = packs

    edit(kit, "catalog/skills.json", change)


def test_a_keyed_skill_cannot_be_in_a_default_pack(kit):
    _skill_need(kit, "tree-demo", packs=["hitl"])
    with pytest.raises(SkillCatalogError, match="default pack"):
        load_skills(kit)


def test_a_keyed_skill_outside_the_default_packs_loads(kit):
    _skill_need(kit, "tree-demo")
    assert load_skills(kit)["tree-demo"].credentials == [NEED]


def test_the_shipped_plugin_declares_its_optional_key(kit_root):
    _, plugins = mcp_catalog.load_plugins(kit_root)
    (need,) = plugins["security-guidance"]["credentials"]
    assert need["env"] == "ANTHROPIC_API_KEY"
    assert need["required"] is False
    assert need["get_it"] == "https://platform.claude.com/settings/keys"


# ---------------------------------------------------------------- references, never values


def test_renderers_write_references_only():
    entry = {"command": "npx", "args": ["-y", "p@1"], "credentials": [NEED]}
    toml = mcpconfig.render_servers([("demo", entry)])
    assert f'env_vars = ["{KEY}"]' in toml
    assert mcpjson.render_entry(entry) == {
        "command": "npx",
        "args": ["-y", "p@1"],
        "env": {KEY: "${" + KEY + "}"},
    }
    plain = {"command": "npx", "args": ["-y", "p@1"]}
    assert "env_vars" not in mcpconfig.render_servers([("demo", plain)])
    assert "env" not in mcpjson.render_entry(plain)


def test_claude_user_scope_command_passes_a_quoted_reference(kit):
    keyed_playwright(kit)
    servers = mcp_catalog.load_servers(kit)
    (cmd,) = claude_mcp_commands(
        kit, mcpconfig.McpSelection([("playwright", servers["playwright"])])
    )
    assert f"-e '{KEY}=${{{KEY}}}' --" in cmd


def _rules(kit) -> dict:
    keyed_playwright(kit)
    return mcp_catalog.allowlist(kit)


@pytest.mark.parametrize(
    "cfg",
    [
        {"command": "npx", "args": [], "env_vars": [KEY]},
        {"command": "npx", "args": [], "env": {KEY: "${" + KEY + "}"}},
    ],
)
def test_audit_accepts_a_declared_reference(kit, cfg):
    rules = _rules(kit)
    assert audit.audit_config({"mcp_servers": {"playwright": cfg}}, rules) == []


@pytest.mark.parametrize(
    "server, cfg",
    [
        ("playwright", {"env": {KEY: SECRET}}),  # a written value
        ("playwright", {"env": {KEY: "${OTHER}"}}),  # a reference to something else
        ("playwright", {"env_vars": ["OTHER_API_KEY"]}),  # not declared
        ("sequential-thinking", {"env_vars": [KEY]}),  # declared for another server
    ],
)
def test_audit_refuses_values_and_undeclared_names(kit, server, cfg):
    rules = _rules(kit)
    cfg = {"command": "npx", "args": [], **cfg}
    problems = audit.audit_config({"mcp_servers": {server: cfg}}, rules)
    assert any("secret-like env" in p for p in problems), problems


def test_legacy_allowlist_has_no_exception(kit_root):
    rules = mcpconfig.load_allowlist(kit_root)
    assert "declared_env" not in rules


@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_install_with_a_keyed_server_writes_no_value_and_verifies(
    kit, workspace, monkeypatch, agent
):
    keyed_playwright(kit)
    monkeypatch.setenv(KEY, SECRET)
    code, out = run(kit, workspace, "install", "--agent", agent, "--mcp", "playwright")
    assert code == EXIT_READY, out
    rel = ".codex/config.toml" if agent == "codex" else ".mcp.json"
    written = (workspace / rel).read_text(encoding="utf-8")
    assert KEY in written and SECRET not in written
    assert f"{KEY}  [required, set]" in out
    code, out = run(kit, workspace, "verify", "--agent", agent)
    assert code == EXIT_READY, out
    assert SECRET not in out
    for log in (workspace / ".kit").rglob("*.log"):
        assert SECRET not in log.read_text(encoding="utf-8")


# ---------------------------------------------------------------- the guide


def test_plan_explains_the_key_without_printing_it(kit, workspace, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    argv = ("plan", "--agent", "claude", "--plugin", "security-guidance")
    code, out = run(kit, workspace, *argv)
    assert code == EXIT_READY, out
    assert "API keys (set later; the kit never asks for, stores or prints a key):" in out
    assert "ANTHROPIC_API_KEY  [optional, not set]" in out
    assert "used by:  plugin security-guidance (claude)" in out
    assert "get it:   https://platform.claude.com/settings/keys  (pay per use)" in out
    assert '[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "<your key>", "User")' in out
    assert 'export ANTHROPIC_API_KEY="<your key>"' in out
    assert out.index("API keys") < out.index("DRY RUN")

    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    code, out = run(kit, workspace, *argv, "--json")
    assert SECRET not in out
    (need,) = json.loads(out)["api_keys"]
    assert need["env"] == "ANTHROPIC_API_KEY" and need["set"] is True
    assert need["used_by"] == ["plugin security-guidance (claude)"]


def test_no_key_section_without_keyed_entries(kit, workspace):
    code, out = run(kit, workspace, "plan", "--agent", "both")
    assert code == EXIT_READY
    assert "API keys" not in out
    code, out = run(kit, workspace, "plan", "--agent", "both", "--json")
    assert json.loads(out)["api_keys"] == []


def test_a_missing_required_key_is_a_next_action_not_a_failure(kit, workspace, monkeypatch):
    keyed_playwright(kit)
    monkeypatch.delenv(KEY, raising=False)
    code, out = run(kit, workspace, "install", "--agent", "both", "--mcp", "playwright")
    assert code == EXIT_READY, out
    assert f"{KEY}  [required, not set]" in out
    assert "used by:  MCP playwright (codex, claude)" in out
    assert f"  - Set {KEY} (see API keys above), open a new terminal and restart the agent." in out
    data = json.loads(run(kit, workspace, "verify", "--agent", "both", "--json")[1])
    assert data["api_keys"][0]["set"] is False


def test_an_optional_key_is_no_next_action(kit, workspace, monkeypatch):
    keyed_playwright(kit, required=False)
    monkeypatch.delenv(KEY, raising=False)
    code, out = run(kit, workspace, "install", "--agent", "codex", "--mcp", "playwright")
    assert code == EXIT_READY, out
    assert f"Set {KEY}" not in out


def test_collect_merges_users_of_one_key():
    entry = {"credentials": [{**NEED, "required": False}]}
    strict = {"credentials": [NEED]}
    needs = credentials.collect(
        [
            ("skill", "b", "codex", strict),
            ("MCP", "a", "codex", entry),
            ("MCP", "a", "claude", entry),
        ]
    )
    (need,) = needs
    assert need.required is True  # required by any user wins, whatever the order
    assert need.used_by == ["skill b (codex)", "MCP a (codex, claude)"]


def test_a_keyed_skill_in_a_selected_pack_is_listed(kit, workspace, monkeypatch):
    _skill_need(kit, "tree-demo")
    monkeypatch.delenv(KEY, raising=False)
    code, out = run(kit, workspace, "plan", "--agent", "codex", "--profile", "core,demo")
    assert code == EXIT_READY, out
    assert "used by:  skill tree-demo (codex)" in out


def test_mask_keeps_the_placeholder_and_hides_values():
    assert mask('export X_API_KEY="<your key>"  to') == 'export X_API_KEY="<your key>"  to'
    assert mask(f"X_API_KEY={SECRET}") == "X_API_KEY=***"
    assert SECRET not in mask(f'X_API_KEY="<your key>"{SECRET}')
    assert mask('X_TOKEN="<your key>"x').startswith("X_TOKEN=***")  # masked as before
