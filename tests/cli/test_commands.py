"""P3-T6 new CLI path (05_CLI_SPEC). TC-CLI-*, REQ-INST-001~004/009, REQ-AGENT-001, SAFE-010."""

from __future__ import annotations

import json

import pytest

from kit import commands, register
from kit.adapters import registry
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from kit.plan import kit_policy_text
from kit.profile_resolver import render_show, resolve
from tests.conftest import tree_digest

CODEX_FILES = ("AGENTS.md", ".agents/", ".codex/")
CLAUDE_FILES = ("CLAUDE.md", ".claude/", ".mcp.json")
MANIFEST = ".kit/state/install-manifest.json"


def files(ws):
    return set(tree_digest(ws, exclude=(".kit/",)))


# core on the standard policy: 11 kit skills - 3 replaced/varied by superpowers + 3 of them
# + requesting-code-review, receiving-code-review, karpathy-guidelines (P4-T4)
STANDARD_CORE = (
    17  # +task-approval (P5-T2), +data-quality-validator (P5-T6), +session-recovery (P5-T7)
)


def manifest(ws):
    return json.loads((ws / MANIFEST).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- each agent gets its own setup


def test_codex_install_writes_only_codex_files(run_kit, workspace, isolated_home):
    code, out = run_kit("install", "--agent", "codex", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    found = files(workspace)
    assert found and all(f.startswith(CODEX_FILES) for f in found)
    assert ".codex/config.toml" in found
    assert len([f for f in found if f.endswith("/SKILL.md")]) == STANDARD_CORE
    text = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert "# Codex Project Policy" in text and "Restrictions" not in text
    assert "`.agents/skills/`" in text and "Claude" not in text
    assert "Agent codex:  AGENTS.md INSTALLED | Skills 17/17 verified in .agents/skills/" in out
    assert (
        "replaced skills: tdd-automator -> test-driven-development, "
        "submission-validator -> verification-before-completion" in out
    )
    assert "run /skills in Codex" in out and "Agent claude" not in out
    assert not any(isolated_home.rglob("*"))


def test_claude_install_writes_only_claude_files(run_kit, workspace, isolated_home):
    code, out = run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    found = files(workspace)
    assert found and all(f.startswith(CLAUDE_FILES) for f in found)
    assert len([f for f in found if f.endswith("/SKILL.md")]) == STANDARD_CORE
    text = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# Claude Code Project Policy" in text and "`.claude/skills/`" in text
    assert "Codex" not in text
    mcp = json.loads((workspace / ".mcp.json").read_text(encoding="utf-8"))
    assert list(mcp["mcpServers"]) == ["sequential-thinking"]
    assert "Agent claude: CLAUDE.md INSTALLED | Skills 17/17 verified in .claude/skills/" in out
    assert "Run /mcp in Claude Code" in out and "Agent codex" not in out
    assert not (workspace / ".claude/settings.local.json").exists()
    assert not any(isolated_home.rglob("*"))


def test_both_installs_each_agent_in_its_place(run_kit, workspace):
    code, out = run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    found = files(workspace)
    assert {"AGENTS.md", "CLAUDE.md", ".codex/config.toml", ".mcp.json"} <= found
    assert "Agent codex:" in out and "Agent claude:" in out
    data = manifest(workspace)
    assert [i["agent"] for i in data["installs"]] == ["claude", "codex"]
    claude = data["installs"][0]
    assert claude["profiles"] == ["python"] and claude["policy"] == "standard"
    assert {b["path"] for b in claude["blocks"]} == {"CLAUDE.md"}
    assert claude["json_keys"][0]["pointer"] == "/mcpServers/sequential-thinking"
    assert all(
        f["path"].startswith((".claude/skills/", ".claude/agents/")) for f in claude["files"]
    )
    assert ".claude/agents/counterexample-blackbox.md" in {f["path"] for f in claude["files"]}
    codex = data["installs"][1]
    assert {b["path"] for b in codex["blocks"]} == {"AGENTS.md", ".codex/config.toml"}


def test_rerun_is_idempotent(run_kit, workspace):
    run_kit("install", "--agent", "both", "--offline")
    before = tree_digest(workspace, exclude=(".kit/",))
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert tree_digest(workspace, exclude=(".kit/",)) == before


def test_claude_after_codex_leaves_codex_files(run_kit, workspace):
    run_kit("install", "--agent", "codex", "--profile", "python", "--offline")
    codex = {k: v for k, v in tree_digest(workspace).items() if k.startswith(CODEX_FILES)}
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    after = tree_digest(workspace)
    assert {k: after[k] for k in codex} == codex
    assert {i["agent"] for i in manifest(workspace)["installs"]} == {"codex", "claude"}


def test_restricted_policy_is_the_legacy_text(run_kit, workspace, kit_root):
    run_kit("install", "--agent", "claude", "--policy", "restricted", "--offline")
    text = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
    assert kit_policy_text(kit_root).strip() in text


def test_policy_switch_updates_the_block(run_kit, workspace):
    run_kit("install", "--agent", "codex", "--offline")
    code, out = run_kit("install", "--agent", "codex", "--policy", "restricted", "--offline")
    assert code == EXIT_READY, out
    assert "## Restrictions" in (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert manifest(workspace)["installs"][0]["policy"] == "restricted"


@pytest.mark.parametrize("profile", ["core", "python", "data", "web", "full"])
def test_new_codex_restricted_equals_legacy_tree(run_kit, tmp_path, profile):
    """05_CLI_SPEC §2: `install --agent codex --policy restricted` = legacy install."""
    legacy, new = tmp_path / "legacy", tmp_path / "new"
    legacy.mkdir()
    new.mkdir()
    run_kit("--profile", profile, "--offline", cwd=legacy)
    run_kit(
        "install",
        "--agent",
        "codex",
        "--policy",
        "restricted",
        "--profile",
        profile,
        "--offline",
        cwd=new,
    )
    assert tree_digest(new, exclude=(".kit/",)) == tree_digest(legacy, exclude=(".kit/",))


# ---------------------------------------------------------------- plan / dry-run write nothing


@pytest.mark.parametrize(
    "argv",
    [
        ("plan", "--agent", "both", "--profile", "python"),
        ("install", "--agent", "claude", "--dry-run"),
        ("plan", "--agent", "codex", "--json"),
    ],
)
def test_plan_and_dry_run_write_nothing(run_kit, workspace, argv):
    (workspace / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    before = tree_digest(workspace, exclude=())
    code, out = run_kit(*argv)
    assert code == EXIT_READY, out
    assert tree_digest(workspace, exclude=()) == before


def test_plan_output_lists_each_agent(run_kit):
    code, out = run_kit("plan", "--agent", "both", "--profile", "python")
    assert "[codex] Planned changes:" in out and "[claude] Planned changes:" in out
    assert "CREATE    .claude/skills/task-router/SKILL.md" in out
    assert "CREATE    .mcp.json" in out and "CREATE    .codex/config.toml" in out
    assert "DRY RUN: nothing was written." in out


def test_plan_json_is_one_document(run_kit):
    code, out = run_kit("plan", "--agent", "claude", "--json")
    data = json.loads(out)
    assert data["status"] == "DRY RUN" and data["exit_code"] == 0
    assert set(data["agents"]) == {"claude"}


def test_report_json_file(run_kit, workspace, tmp_path):
    report = tmp_path / "r" / "report.json"
    code, out = run_kit("install", "--agent", "codex", "--offline", "--report-json", str(report))
    assert "Status:       READY" in out
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "READY" and data["exit_code"] == code == 0
    assert data["agents"]["codex"]["skill_root"] == ".agents/skills"


# ---------------------------------------------------------------- --agent both is all-or-nothing


def test_both_rolls_back_when_a_write_fails(run_kit, workspace, monkeypatch):
    (workspace / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    real = register._write_atomic

    def fail_on_claude(path, data):
        if ".claude" in path.as_posix():
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(register, "_write_atomic", fail_on_claude)
    before = tree_digest(workspace, exclude=(".kit/backups/",))
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_BLOCKED, out
    assert "write failed: disk full; rolled back" in out
    assert tree_digest(workspace, exclude=(".kit/backups/", ".kit/logs/")) == {
        k: v for k, v in before.items()
    }
    assert not (workspace / ".agents").exists() and not (workspace / MANIFEST).exists()
    assert (workspace / "AGENTS.md").read_text(encoding="utf-8") == "# mine\n"
    monkeypatch.setattr(register, "_write_atomic", real)
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out  # converges on re-run


def test_conflict_in_one_agent_is_reported_per_agent(run_kit, workspace):
    (workspace / ".claude/skills/task-router").mkdir(parents=True)
    (workspace / ".claude/skills/task-router/SKILL.md").write_text("mine", encoding="utf-8")
    code, out = run_kit("install", "--agent", "both", "--offline")
    assert code == EXIT_BLOCKED
    assert "CONFLICT   required [claude] skill:task-router" in out
    assert "Agent codex:  AGENTS.md INSTALLED" in out


# ---------------------------------------------------------------- verify


def test_verify_reads_the_manifest(run_kit, workspace):
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    code, out = run_kit("verify", "--agent", "claude", "--offline")
    assert code == EXIT_READY, out
    assert "Profiles:     python   Policy: standard" in out
    (workspace / ".claude/skills/benchmark/SKILL.md").unlink()
    before = tree_digest(workspace, exclude=())
    code, out = run_kit("verify", "--agent", "claude", "--offline")
    assert code == EXIT_PARTIAL and "FAIL       optional [claude] skill:benchmark" in out
    assert tree_digest(workspace, exclude=()) == before  # verify never writes
    (workspace / ".claude/skills/task-router/SKILL.md").write_text("x", encoding="utf-8")
    code, out = run_kit("verify", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED and "CONFLICT   required [claude] skill:task-router" in out


def test_verify_without_install_is_blocked(run_kit):
    code, out = run_kit("verify", "--agent", "claude")
    assert code == EXIT_BLOCKED
    assert "no kit install for claude here; run: kit install --agent claude" in out


def test_verify_accepts_a_legacy_install(run_kit):
    run_kit("--profile", "python", "--offline")
    code, out = run_kit("verify", "--agent", "codex", "--offline")
    assert code == EXIT_READY, out
    assert "Profiles:     python   Policy: restricted" in out


def test_verify_both_with_different_profiles(run_kit):
    run_kit("install", "--agent", "codex", "--profile", "core", "--offline")
    run_kit("install", "--agent", "claude", "--profile", "python", "--offline")
    code, out = run_kit("verify", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert "Profiles:     core   Policy" in out and "Profiles:     python   Policy" in out


# ---------------------------------------------------------------- network gate (minimum)


def test_offline_makes_no_network_calls(run_kit, no_network):
    code, out = run_kit("install", "--agent", "both", "--profile", "python", "--offline")
    assert code == EXIT_READY, out
    assert "Network:      not used (--offline)" in out


# ---------------------------------------------------------------- errors: 64 / 65


@pytest.mark.parametrize(
    "argv,match",
    [
        (("install",), "--agent is required"),
        (("install", "--agent", "gemini"), "invalid choice"),
        (("install", "--agent", "codex", "--profile", "nope"), "unknown profile or pack"),
        (("install", "--agent", "codex", "--policy", "loose"), "invalid choice"),
        (("install", "--agent", "codex", "--scope", "user"), "re-run with --yes"),  # TC-USR-03
        (("install", "--agent", "codex", "--scope", "user", "--target", "."), "--target"),
        (("install", "--agent", "codex", "--offline", "--yes"), "cannot be combined"),
        (("install", "--agent", "codex", "--json", "--report-json", "x"), "not allowed with"),
        (("install", "--agent", "codex", "--target", " "), "non-empty"),
        (("install", "--agent", "codex", "--bogus"), "unrecognized"),
        (("capture", "--agent", "gemini"), "invalid choice"),
        (("profiles", "show"), "needs a profile"),
        (("profiles", "list", "core"), "no other arguments"),
        (("version", "x"), "unrecognized"),
    ],
)
def test_usage_errors_exit_64(run_kit, workspace, capsys, argv, match):
    before = tree_digest(workspace, exclude=())
    code, out = run_kit(*argv)
    assert code == EXIT_USAGE
    assert match in capsys.readouterr().err
    assert tree_digest(workspace, exclude=()) == before


def test_target_errors_exit_65(run_kit, workspace, kit_root, capsys):
    assert run_kit("install", "--agent", "codex", "--target", "missing")[0] == EXIT_TARGET
    assert run_kit("install", "--agent", "codex", "--target", str(kit_root))[0] == EXIT_TARGET
    (workspace / MANIFEST).parent.mkdir(parents=True)
    (workspace / MANIFEST).write_text('{"schema": 99}', encoding="utf-8")
    assert run_kit("install", "--agent", "codex")[0] == EXIT_TARGET
    assert "newer than this kit" in capsys.readouterr().err


def _profile_mcp(monkeypatch, names):
    from kit import profile_resolver

    real = profile_resolver.resolve

    def with_mcp(*args, **kwargs):
        resolved = real(*args, **kwargs)
        resolved.nodes[resolved.order[-1]].mcp = {"shared": list(names)}
        return resolved

    monkeypatch.setattr(profile_resolver, "resolve", with_mcp)


def test_mcp_outside_the_catalog_is_64(run_kit, workspace, monkeypatch):
    _profile_mcp(monkeypatch, ["evil-server"])
    assert run_kit("install", "--agent", "claude")[0] == EXIT_USAGE
    assert not (workspace / ".mcp.json").exists()


def test_listed_only_mcp_in_a_profile_is_skipped_and_reported(run_kit, workspace, monkeypatch):
    _profile_mcp(monkeypatch, ["fetch"])
    code, out = run_kit("install", "--agent", "claude", "--json")
    assert code == EXIT_READY
    agent = json.loads(out)["agents"]["claude"]
    assert agent["mcp_servers"] == []
    assert agent["skipped_mcp"][0].startswith("fetch (listed only: fetches arbitrary URLs")
    assert not (workspace / ".mcp.json").exists()


# ---------------------------------------------------------------- routing, doctor, profiles


def test_unknown_first_word_stays_on_legacy_path(run_kit, capsys):
    assert run_kit("instal")[0] == EXIT_USAGE
    assert "Run with --help for usage." in capsys.readouterr().err


def test_subcommand_help_and_version(run_kit):
    assert "kit install --agent claude" in run_kit("help")[1]
    assert "kit install --agent claude" in run_kit("install", "--help")[1]
    assert run_kit("version")[1].startswith("kit 2.")


def test_doctor_is_read_only(run_kit, workspace):
    run_kit("install", "--agent", "claude", "--offline")
    before = tree_digest(workspace, exclude=())
    code, out = run_kit("doctor")
    assert code == EXIT_READY
    assert "CLAUDE.md kit block yes | 17 skill(s) in .claude/skills/ | manifest yes" in out
    assert "AGENTS.md kit block no | 0 skill(s)" in out
    assert tree_digest(workspace, exclude=()) == before
    data = json.loads(run_kit("doctor", "--json")[1])
    assert data["agents"]["claude"]["manifest"] is True


def test_doctor_suggests_detected_agents(run_kit, monkeypatch):
    monkeypatch.setattr(commands.shutil, "which", lambda n: "/x" if n == "claude" else None)
    assert "Suggestion:   kit install --agent claude" in run_kit("doctor")[1]


def test_profiles_show_matches_resolver(run_kit, kit_root):
    code, out = run_kit("profiles", "show", "core,hitl", "--agent", "claude")
    assert code == EXIT_READY
    resolved = resolve(kit_root, "core,hitl")
    skills = commands._shown_skills(kit_root, resolved, "standard")  # B-1: after the policy
    assert out == render_show(resolved, ["claude"], "standard", skills)
    assert "hitl       pack" in run_kit("profiles", "list")[1]


def test_every_registered_agent_has_a_cli_name():
    for name in registry.names():
        adapter = registry.get(name)
        assert adapter.cli and adapter.display_name
