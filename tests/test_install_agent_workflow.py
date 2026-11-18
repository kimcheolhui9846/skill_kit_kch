import codecs
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "devtools" / "install_agent_workflow.py"
ASSETS = SCRIPT.parents[1] / "user" / "workflow"
BEGIN = b"<!-- BEGIN SKILL-KIT-KCH WORKFLOW -->"
END = b"<!-- END SKILL-KIT-KCH WORKFLOW -->"
CODEX_AGENT = "harness-sol-worker.toml"
CLAUDE_AGENTS = ("harness-opus-review.md", "harness-sonnet-worker.md")


@pytest.fixture
def setup(tmp_path):
    home = tmp_path / "installer-home"
    env = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "PATH") if key in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="utf-8")
    return home, env


def run(setup, *args):
    home, env = setup
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=home.parent,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )


def test_clean_preview_apply_and_repeat(setup):
    home, _ = setup
    preview = run(setup)
    assert preview.returncode == 0, preview.stderr
    assert "AGENTS.md" in preview.stdout
    assert "CLAUDE.md" in preview.stdout
    assert not home.exists(), [p.relative_to(home) for p in home.rglob("*")]

    applied = run(setup, "--apply")
    assert applied.returncode == 0, applied.stderr
    codex, claude = home / ".codex", home / ".claude"
    content = (codex / "AGENTS.md").read_bytes()
    assert content == (claude / "CLAUDE.md").read_bytes()
    assert content.splitlines()[0] == BEGIN
    assert content.splitlines()[-1] == END
    assert (
        b"\n".join(content.splitlines()[1:-1])
        == (ASSETS / "WORKFLOW.md").read_bytes().replace(b"\r\n", b"\n").strip()
    )
    assert (codex / "agents" / CODEX_AGENT).is_file()
    assert all((claude / "agents" / name).is_file() for name in CLAUDE_AGENTS)

    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in home.rglob("*") if p.is_file()}
    repeated = run(setup, "--apply")
    assert repeated.returncode == 0, repeated.stderr
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    assert {p for p in home.rglob("*") if p.is_file()} == before.keys()


def test_existing_custom_dirs_bom_crlf_and_override(setup):
    home, env = setup
    codex = home / "codex custom"
    claude = home / "claude custom"
    env.update(CODEX_HOME=str(codex), CLAUDE_CONFIG_DIR=str(claude))
    (codex / "agents").mkdir(parents=True)
    claude.mkdir()
    override = codex / "AGENTS.override.md"
    original = codecs.BOM_UTF8 + b"# Existing\r\n\r\nTrailing without newline"
    override.write_bytes(original)
    preferences = {
        codex / "AGENTS.md": b"inactive",
        codex / "config.toml": b"model = 'unrelated'",
        codex / "agents" / "other.toml": b"other agent",
        claude / "settings.json": b'{"hooks":{}}',
    }
    for path, content in preferences.items():
        path.write_bytes(content)
    local = claude / "CLAUDE.md"
    local.write_bytes(b"old advice\n" + BEGIN + b"\nold block\n" + END + b"\nend")

    result = run(setup, "--apply")
    assert result.returncode == 0, result.stderr
    merged = override.read_bytes()
    assert merged.startswith(codecs.BOM_UTF8 + BEGIN + b"\r\n")
    assert merged.endswith(original[3:])
    assert b"\n" not in merged.replace(b"\r\n", b"")
    updated = local.read_bytes()
    assert updated.startswith(BEGIN + b"\n")
    assert updated.endswith(b"old advice\nend")
    assert updated.count(BEGIN) == updated.count(END) == 1
    assert list(codex.glob("AGENTS.override.md.backup-*"))[0].read_bytes() == original
    assert list(claude.glob("CLAUDE.md.backup-*"))[0].read_bytes().endswith(b"\nend")
    assert all(path.read_bytes() == data for path, data in preferences.items())
    assert not (home / ".codex").exists()
    assert not (home / ".claude").exists()


@pytest.mark.parametrize("existing", [BEGIN, END + b"\n" + BEGIN, b"prefix " + BEGIN])
def test_malformed_markers_fail_before_changes(setup, existing):
    home, _ = setup
    claude = home / ".claude"
    claude.mkdir(parents=True)
    target = claude / "CLAUDE.md"
    target.write_bytes(existing)
    result = run(setup, "--apply")
    assert result.returncode != 0
    assert "marker" in result.stderr.lower()
    assert list(home.rglob("*")) == [claude, target]
    assert target.read_bytes() == existing


def test_unowned_agent_blocks_any_writes(setup):
    home, _ = setup
    agent = home / ".claude" / "agents" / CLAUDE_AGENTS[0]
    agent.parent.mkdir(parents=True)
    agent.write_bytes(b"---\nname: user-agent\n---\ncustom agent")
    result = run(setup, "--apply")
    assert result.returncode != 0
    assert agent.name in result.stderr
    assert agent.read_bytes().endswith(b"custom agent")
    assert not (home / ".codex").exists()
    assert not (home / ".claude" / "CLAUDE.md").exists()


def test_blank_override_is_preserved(setup):
    home, _ = setup
    override = home / ".codex" / "AGENTS.override.md"
    override.parent.mkdir(parents=True)
    whitespace = codecs.BOM_UTF8 + b" \r\n"
    override.write_bytes(whitespace)
    result = run(setup, "--apply")
    assert result.returncode == 0, result.stderr
    assert override.read_bytes() == whitespace
    assert override.with_name("AGENTS.md").read_bytes().startswith(BEGIN)


def test_overlapping_directories_fail_without_writes(setup):
    home, env = setup
    env["CLAUDE_CONFIG_DIR"] = str(home / ".codex" / "AGENTS.override.md")
    result = run(setup, "--apply")
    assert result.returncode != 0
    assert "overlap" in result.stderr
    assert not home.exists()


def test_owned_agent_replaced_with_backup(setup):
    home, _ = setup
    agent = home / ".codex" / "agents" / CODEX_AGENT
    agent.parent.mkdir(parents=True)
    marker = b"# Managed by skill-kit-kch agent workflow installer"
    original = codecs.BOM_UTF8 + marker + b"\r\nname = 'old'"
    agent.write_bytes(original)
    existing_backup = agent.with_name(f"{agent.name}.backup-reserved")
    existing_backup.write_bytes(b"existing backup")

    result = run(setup, "--apply")
    assert result.returncode == 0, result.stderr
    source = (ASSETS / CODEX_AGENT).read_bytes().replace(b"\r\n", b"\n").strip()
    assert agent.read_bytes() == codecs.BOM_UTF8 + source.replace(b"\n", b"\r\n")
    assert {p.read_bytes() for p in agent.parent.glob(f"{agent.name}.backup-*")} == {
        original,
        b"existing backup",
    }


def test_blocked_replacement_can_be_retried(setup, monkeypatch):
    from devtools import install_agent_workflow as installer

    home, _ = setup
    codex = home / ".codex"
    claude = home / ".claude"
    codex.mkdir(parents=True)
    claude.mkdir()
    agents = codex / "AGENTS.md"
    claude_md = claude / "CLAUDE.md"
    agents.write_bytes(b"Codex instructions")
    claude_md.write_bytes(b"Claude instructions")
    monkeypatch.setenv("CODEX_HOME", str(codex))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    replace = os.replace

    def blocked_replace(src, dst):
        if dst == claude_md:
            raise PermissionError("simulated blocked replacement")
        replace(src, dst)

    with monkeypatch.context() as patch:
        patch.setattr(installer.os, "replace", blocked_replace)
        with pytest.raises(PermissionError, match="simulated blocked replacement"):
            installer.apply(*installer.plan())

    assert agents.read_bytes().startswith(BEGIN)
    assert claude_md.read_bytes() == b"Claude instructions"
    assert not list(home.rglob(".workflow-stage-*"))
    assert list(codex.glob("AGENTS.md.backup-*"))[0].read_bytes() == b"Codex instructions"

    installer.apply(*installer.plan())
    assert claude_md.read_bytes().startswith(BEGIN)
    assert all(target.action == "UNCHANGED" for target in installer.plan()[0])
