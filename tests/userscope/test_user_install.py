"""P4-T7 `--scope user` (ADR-018). TC-USR-02..06, TC-USR-09, TC-USR-10."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kit import userscope
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from kit.writers.markdown_block import extract_block
from tests.conftest import tree_digest
from tests.userscope.pc_fixture import USER, kit_run, make_pc, put

OMX_SKILLS = 29
OMX_PROMPTS = 32
STANDARD_CORE = 14
CODEX_BLOCK = "## Rules\n- Work from `${HOME}\\work`.\n"
CLAUDE_BLOCK = "# Global\n- Commit as the user.\n"
TABLES = '[features]\ngoals = true\n\n[plugins."browser@openai-bundled"]\nenabled = true\n'
KEYS = {
    "/enabledPlugins/superpowers@superpowers-marketplace": True,
    "/attribution/commit": "",
    "/model": "opus",
}


def snapshot(kit: Path, mcp_codex=(), mcp_claude=()) -> None:
    put(kit, "user/codex/AGENTS.block.md", CODEX_BLOCK)
    put(kit, "user/codex/config.toml", TABLES)
    put(kit, "user/claude/CLAUDE.block.md", CLAUDE_BLOCK)
    put(kit, "user/claude/settings.json", json.dumps({"schema": 1, "keys": KEYS}))
    put(kit, "user/codex/mcp.json", json.dumps({"servers": [{"name": n} for n in mcp_codex]}))
    put(kit, "user/claude/mcp.json", json.dumps({"servers": [{"name": n} for n in mcp_claude]}))


def user(kit, cwd, *argv, ask=None):
    return kit_run(kit, cwd, *argv, "--scope", "user", ask=ask)


def items(out: str, agent: str) -> dict:
    return {i["name"]: i for i in json.loads(out)["agents"][agent]["items"]}


def home_files(home: Path) -> list:
    return sorted(p.relative_to(home).as_posix() for p in home.rglob("*") if p.is_file())


@pytest.fixture
def ready(kit, home, workspace):
    # docs-demo: captured on the PC but not in catalog/mcp.json (not carried)
    snapshot(kit, mcp_codex=["playwright", "docs-demo"], mcp_claude=["playwright", "docs-demo"])
    put(home, ".codex/AGENTS.md", "# My own rules\n")
    put(home, ".claude/settings.json", json.dumps({"theme": "dark"}, indent=2))
    return kit


def test_a_captured_keyed_server_gets_references_only(kit, home, workspace, monkeypatch):
    """P4-T9: context7 is pinned in the catalog; its key is passed by name, never by value."""
    snapshot(kit, mcp_codex=["context7"], mcp_claude=["context7"])
    monkeypatch.setenv("CONTEXT7_API_KEY", "ctx7sk-fake-0123")
    code, out = user(kit, workspace, "install", "--agent", "both", "--yes", "--json")
    assert code == EXIT_READY, out
    config = (home / ".codex/config.toml").read_text(encoding="utf-8")
    assert 'env_vars = ["CONTEXT7_API_KEY"]' in config and "ctx7sk" not in config
    data = json.loads(out)
    assert any(
        "-e 'CONTEXT7_API_KEY=${CONTEXT7_API_KEY}' -- npx -y @upstash/context7-mcp@4.5.1" in s
        for s in data["agents"]["claude"]["manual_steps"]
    )
    assert data["api_keys"][0]["env"] == "CONTEXT7_API_KEY" and data["api_keys"][0]["set"]
    assert "ctx7sk" not in out


# ---------------------------------------------------------------- confirmation and dry run


def test_dry_run_leaves_home_unchanged(ready, home, workspace):
    """TC-USR-02."""
    before = tree_digest(home, exclude=())
    code, out = user(ready, workspace, "install", "--agent", "both", "--dry-run")
    assert code == EXIT_READY, out
    assert tree_digest(home, exclude=()) == before
    assert "Home:         ~" in out and "Scope:        user" in out
    assert USER not in out and str(home) not in out
    assert "CREATE    .codex/skills/ralph/SKILL.md" in out


@pytest.mark.parametrize(
    "argv",
    [
        ("install", "--agent", "codex"),
        ("update", "--agent", "codex"),
        ("uninstall", "--agent", "codex"),
    ],
)
def test_non_interactive_without_yes_is_64(ready, home, workspace, capsys, argv):
    """TC-USR-03."""
    if argv[0] != "install":
        user(ready, workspace, "install", "--agent", "codex", "--yes")
    before = tree_digest(home, exclude=())
    code, _ = user(ready, workspace, *argv)
    assert code == EXIT_USAGE
    assert "re-run with --yes" in capsys.readouterr().err
    assert tree_digest(home, exclude=()) == before


def test_terminal_answer_decides(ready, home, workspace, capsys):
    asked = []

    def no(question):
        asked.append(question)
        return "n"

    before = tree_digest(home, exclude=())
    code, _ = user(ready, workspace, "install", "--agent", "codex", ask=no)
    assert code == EXIT_USAGE and tree_digest(home, exclude=()) == before
    assert "Apply these changes to your home folder?" in asked[0]
    assert ".codex/AGENTS.md" in asked[0] and str(home) not in asked[0]
    code, out = user(ready, workspace, "install", "--agent", "codex", ask=lambda q: "y")
    assert code == EXIT_READY, out


def test_scope_user_argument_errors(ready, home, workspace, monkeypatch, capsys, tmp_path):
    code, _ = user(ready, workspace, "install", "--agent", "claude", "--plugin", "x", "--yes")
    assert code == EXIT_USAGE and "--plugin is for --scope project" in capsys.readouterr().err
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "elsewhere"))
    code, _ = user(ready, workspace, "install", "--agent", "codex", "--yes")
    assert code == EXIT_TARGET and "outside the home folder" in capsys.readouterr().err
    code, _ = kit_run(ready, workspace, "install", "--agent", "codex", "--target", str(home))
    assert code == EXIT_TARGET and "use --scope user" in capsys.readouterr().err


# ---------------------------------------------------------------- install


def test_install_writes_only_kit_owned_parts(ready, home, workspace):
    """TC-USR-04 (write part), TC-USR-05, TC-USR-10."""
    code, out = user(ready, workspace, "install", "--agent", "both", "--yes", "--json")
    assert code == EXIT_READY, out
    agents_md = (home / ".codex/AGENTS.md").read_text(encoding="utf-8")
    assert agents_md.startswith("# My own rules\n")
    found = extract_block(agents_md)
    assert found[2] == userscope.expand_home(CODEX_BLOCK, home).strip()
    assert f"{home}\\work" in found[2]
    claude_md = extract_block((home / ".claude/CLAUDE.md").read_text(encoding="utf-8"))
    assert claude_md[2] == CLAUDE_BLOCK.strip()
    # skills: kit (core,hitl standard) + OMX for Codex; kit only for Claude
    codex_skills = {p.parent.name for p in (home / ".codex/skills").glob("*/SKILL.md")}
    assert len(codex_skills) == STANDARD_CORE + OMX_SKILLS
    assert len(list((home / ".codex/prompts").glob("*.md"))) == OMX_PROMPTS
    claude_skills = {p.parent.name for p in (home / ".claude/skills").glob("*/SKILL.md")}
    assert len(claude_skills) == STANDARD_CORE and "ralph" not in claude_skills
    # config.toml: catalog-pinned server from the snapshot + captured tables
    block = extract_block(
        (home / ".codex/config.toml").read_text(encoding="utf-8"),
        "# hackathon-kit:begin",
        "# hackathon-kit:end",
    )[2]
    assert "[mcp_servers.playwright]" in block and "@playwright/mcp@0.0.84" in block
    assert "docs-demo" not in block and "[features]" in block
    # settings.json: user key kept, captured keys added
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["theme"] == "dark" and settings["model"] == "opus"
    assert settings["enabledPlugins"] == {"superpowers@superpowers-marketplace": True}
    # ~/.claude.json is never written; MCP is a manual step (TC-USR-05)
    assert not (home / ".claude.json").exists() and not (home / ".claude/.claude.json").exists()
    data = json.loads(out)
    steps = data["agents"]["claude"]["manual_steps"]
    assert any(
        s.endswith("claude mcp add --scope user playwright -- npx -y @playwright/mcp@0.0.84")
        for s in steps
    )
    skipped = data["agents"]["codex"]["skipped_mcp"]
    assert "docs-demo (captured; not in catalog/mcp.json, not pinned)" in skipped
    # kit bookkeeping in the user places, nothing in ~/.kit/
    assert (home / ".kit-state/manifest.json").is_file()
    assert not (home / ".kit").exists()
    man = json.loads((home / ".kit-state/manifest.json").read_text(encoding="utf-8"))
    assert man["scope"] == "user" and [i["agent"] for i in man["installs"]] == ["claude", "codex"]
    assert data["target"] == "~" and str(home) not in out


def test_backups_restore_and_uninstall(ready, home, workspace):
    """TC-USR-04: backup before change, uninstall removes only kit parts, restore puts back."""
    original = (home / ".codex/AGENTS.md").read_bytes()
    code, out = user(ready, workspace, "install", "--agent", "codex", "--yes")
    assert code == EXIT_READY, out
    stamps = [p.name for p in (home / ".kit-backups").iterdir()]
    assert len(stamps) == 1
    assert (home / ".kit-backups" / stamps[0] / ".codex/AGENTS.md").read_bytes() == original
    code, out = user(ready, workspace, "verify", "--agent", "codex")
    assert code == EXIT_READY, out
    code, out = user(ready, workspace, "uninstall", "--agent", "codex", "--yes")
    assert code == EXIT_READY, out
    assert "kit restore --backup" in out and "--scope user" in out
    assert (home / ".codex/AGENTS.md").read_bytes() == original
    assert not (home / ".codex/skills").exists() and not (home / ".codex/prompts").exists()
    assert not (home / ".codex/config.toml").exists()
    # restore the backup made before install: the user's file as it was
    code, out = user(ready, workspace, "restore", "--backup", stamps[0], "--yes")
    assert code == EXIT_READY, out
    assert (home / ".codex/AGENTS.md").read_bytes() == original


def test_user_edits_are_conflicts_and_survive_uninstall(ready, home, workspace):
    user(ready, workspace, "install", "--agent", "codex", "--yes")
    path = home / ".codex/AGENTS.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Work from", "Edited"), "utf-8")
    skill = home / ".codex/skills/task-router/SKILL.md"
    skill.write_text("mine\n", encoding="utf-8")
    code, out = user(ready, workspace, "update", "--agent", "codex", "--yes", "--json")
    assert code == EXIT_BLOCKED
    found = items(out, "codex")
    assert found[".codex/AGENTS.md"]["verified"] == "CONFLICT"
    # the edited items are the user's now: update dropped them from the manifest
    man = json.loads((home / ".kit-state/manifest.json").read_text(encoding="utf-8"))
    owned = {f["path"] for f in man["installs"][0]["files"]}
    assert ".codex/skills/task-router/SKILL.md" not in owned
    assert man["installs"][0]["blocks"] == [
        b for b in man["installs"][0]["blocks"] if b["path"] != ".codex/AGENTS.md"
    ]
    code, out = user(ready, workspace, "uninstall", "--agent", "codex", "--yes")
    assert code == EXIT_READY, out
    assert "Edited" in path.read_text(encoding="utf-8")
    assert skill.read_text(encoding="utf-8") == "mine\n"


def test_omx_installed_by_itself_is_a_conflict_and_never_overwritten(kit, pc, workspace):
    """TC-USR-10: OMX files the kit did not write stay as they are and stay unowned."""
    snapshot(kit)
    own = (pc / ".codex/skills/ralph/SKILL.md").read_bytes()
    code, out = user(kit, workspace, "install", "--agent", "codex", "--yes", "--json")
    assert code == EXIT_PARTIAL  # optional item: the kit's own parts are installed
    omx = items(out, "codex")["omx"]
    assert omx["verified"] == "CONFLICT" and "not written by the kit" in omx["detail"]
    assert (pc / ".codex/skills/ralph/SKILL.md").read_bytes() == own


def test_identical_files_already_there_stay_unowned(ready, home, workspace, kit_root):
    source = kit_root / userscope.OMX_DIR / "skills/ralph/SKILL.md"
    put(home, ".codex/skills/ralph/SKILL.md", source.read_text(encoding="utf-8"))
    code, out = user(ready, workspace, "install", "--agent", "codex", "--yes")
    assert code == EXIT_READY, out
    man = json.loads((home / ".kit-state/manifest.json").read_text(encoding="utf-8"))
    owned = {f["path"] for f in man["installs"][0]["files"]}
    assert ".codex/skills/ralph/SKILL.md" not in owned
    assert ".codex/skills/plan/SKILL.md" in owned
    user(ready, workspace, "uninstall", "--agent", "codex", "--yes")
    assert (home / ".codex/skills/ralph/SKILL.md").is_file()


def test_settings_key_the_user_already_has_stays_theirs(ready, home, workspace):
    put(home, ".claude/settings.json", json.dumps({"model": "opus", "theme": "dark"}))
    user(ready, workspace, "install", "--agent", "claude", "--yes")
    user(ready, workspace, "uninstall", "--agent", "claude", "--yes")
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings == {"model": "opus", "theme": "dark"}


def test_captured_table_set_differently_is_a_conflict(ready, home, workspace):
    put(home, ".codex/config.toml", "[features]\ngoals = false\n")
    code, out = user(ready, workspace, "install", "--agent", "codex", "--yes", "--json")
    assert code == EXIT_PARTIAL  # optional item: the rest is installed
    item = items(out, "codex")[".codex/config.toml"]
    assert item["verified"] == "CONFLICT" and "[features]" in item["detail"]
    assert (home / ".codex/config.toml").read_text(
        encoding="utf-8"
    ) == "[features]\ngoals = false\n"


def test_captured_table_set_the_same_way_is_left_out(ready, home, workspace):
    put(home, ".codex/config.toml", "[features]\ngoals = true\n")
    code, out = user(ready, workspace, "install", "--agent", "codex", "--yes", "--json")
    assert code == EXIT_READY, out
    text = (home / ".codex/config.toml").read_text(encoding="utf-8")
    assert text.count("[features]") == 1
    assert "already set the same way" in items(out, "codex")[".codex/config.toml"]["detail"]


def test_large_agents_md_warns(ready, home, workspace):
    """TC-USR-06."""
    put(home, ".codex/AGENTS.md", "# Mine\n" + "x" * (29 * 1024) + "\n")
    code, out = user(ready, workspace, "install", "--agent", "codex", "--dry-run", "--json")
    assert code == EXIT_READY
    warnings = json.loads(out)["agents"]["codex"]["warnings"]
    assert warnings and "Codex reads 32 KiB by default" in warnings[0]


def test_project_scope_never_touches_home(ready, home, workspace):
    before = tree_digest(home, exclude=())
    code, out = kit_run(ready, workspace, "install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert tree_digest(home, exclude=()) == before


# ---------------------------------------------------------------- TC-USR-09 round trip


def test_capture_on_one_pc_installs_the_same_on_another(kit, workspace, tmp_path, monkeypatch):
    first = tmp_path / "Users" / "one"
    first.mkdir(parents=True)
    for var, value in (
        ("HOME", first),
        ("USERPROFILE", first),
        ("CODEX_HOME", first / ".codex"),
        ("CLAUDE_CONFIG_DIR", first / ".claude"),
    ):
        monkeypatch.setenv(var, str(value))
    make_pc(first)
    code, out = kit_run(kit, workspace, "capture", "--write")
    assert code == EXIT_READY, out
    second = (tmp_path / "Users" / "two").resolve()
    second.mkdir(parents=True)
    for var, value in (
        ("HOME", second),
        ("USERPROFILE", second),
        ("CODEX_HOME", second / ".codex"),
        ("CLAUDE_CONFIG_DIR", second / ".claude"),
    ):
        monkeypatch.setenv(var, str(value))
    code, out = user(kit, workspace, "install", "--agent", "both", "--yes")
    assert code == EXIT_READY, out
    block = extract_block((second / ".codex/AGENTS.md").read_text(encoding="utf-8"))[2]
    assert f"`{second}\\tools`" in block and "## Templates" in block
    assert "secret-project" not in block and str(first) not in block
    claude = extract_block((second / ".claude/CLAUDE.md").read_text(encoding="utf-8"))[2]
    assert f"{second}\\runpod-hf-harness" in claude
    settings = json.loads((second / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"] == {"superpowers@superpowers-marketplace": True}
    assert "theme" not in settings
    config = (second / ".codex/config.toml").read_text(encoding="utf-8")
    assert '[plugins."browser@openai-bundled"]' in config and "computer-use" not in config
    assert "@playwright/mcp@0.0.84" in config  # captured name -> pinned catalog entry


def test_catalog_server_defined_outside_the_block_is_a_conflict(ready, home, workspace):
    """The user's own [mcp_servers.playwright] is never shadowed by a second definition."""
    mine = '[mcp_servers.playwright]\ncommand = "my-npx"\n'
    put(home, ".codex/config.toml", mine)
    code, out = user(ready, workspace, "install", "--agent", "codex", "--yes", "--json")
    assert code == EXIT_PARTIAL
    item = items(out, "codex")[".codex/config.toml"]
    assert item["verified"] == "CONFLICT" and "[mcp_servers.playwright]" in item["detail"]
    assert (home / ".codex/config.toml").read_text(encoding="utf-8") == mine
