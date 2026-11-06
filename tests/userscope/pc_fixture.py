"""A fake PC home for P4-T7 tests: global files a real PC has, secrets included (fakes)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from kit import commands

FAKE_OPENAI = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2"
FAKE_GITHUB = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"
FAKE_BEARER = "Bearer " + "zzzzzzzzzzzzzzzzzzzz"
USER = "alice-kit-test"


def put(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def make_pc(home: Path) -> Path:
    win = str(home)
    put(
        home,
        ".codex/AGENTS.md",
        "# Workflow\n\nIntro line.\n\n"
        "## Windows command execution\n"
        f"- Run tools from `{win}\\tools`.\n\n"
        "## Project Workspace Registry\n"
        f"- `{win}\\Desktop\\secret-project`\n\n"
        f"## Project: demo (`{win}\\Desktop\\demo`)\n- private notes\n\n"
        "## Templates\n```markdown\n## not a section\n```\n- end\n",
    )
    put(
        home,
        ".codex/config.toml",
        'model = "gpt-x"\n'
        'developer_instructions = """\n[not.a.table]\n"""\n'
        "[features]\ngoals = true\n\n"
        '[plugins."browser@openai-bundled"]\nenabled = true\n\n'
        '[plugins."computer-use@openai-bundled"]\nenabled = true\n\n'
        '[hooks.state."browser@openai-bundled:plugin.json#hooks[0]:stop:0:0"]\n'
        'trusted_hash = "sha256:abc"\n\n'
        "[mcp_servers.context7]\n"
        'command = "npx"\nargs = ["-y", "@upstash/context7-mcp"]\n'
        f'env = {{ CONTEXT7_API_KEY = "{FAKE_OPENAI}" }}\n\n'
        "[mcp_servers.playwright]\n"
        f'command = "{home.as_posix()}/.codex/tools/npx.cmd"\n'
        'args = ["@playwright/mcp@latest"]\n\n'
        "[mcp_servers.playwright.env]\n"
        f'GITHUB_TOKEN = "{FAKE_GITHUB}"\n\n'
        f"[projects.'{win}\\Desktop\\demo']\n"
        'trust_level = "trusted"\n\n'
        '[apps.connector_0123456789abcdef.tools."github.create_branch"]\n'
        'approval_mode = "approve"\n',
    )
    put(home, ".codex/auth.json", json.dumps({"OPENAI_API_KEY": FAKE_OPENAI}))
    put(home, ".codex/history.jsonl", f'{{"text": "{FAKE_GITHUB}"}}\n')
    put(home, ".codex/state_5.sqlite", "SQLite format 3\x00")
    put(home, ".codex/sessions/2026/x.jsonl", "{}\n")
    put(home, ".codex/skills/ralph/SKILL.md", "---\nname: ralph\ndescription: old\n---\n")
    put(home, ".codex/skills/mystery/SKILL.md", "---\nname: mystery\ndescription: x\n---\n")
    put(home, ".codex/skills/.system/imagegen/SKILL.md", "---\nname: imagegen\n---\n")
    put(home, ".codex/prompts/analyst.md", "old analyst\n")
    put(home, ".codex/agents/analyst.toml", 'name = "analyst"\n')
    put(
        home,
        ".claude/CLAUDE.md",
        f"# Rules\n\n- Harness at `{win}\\runpod-hf-harness`.\n- Commit as the user.\n",
    )
    put(
        home,
        ".claude/settings.json",
        json.dumps(
            {
                "model": "opus",
                "theme": "dark",
                "attribution": {"commit": "", "pr": ""},
                "enabledPlugins": {"superpowers@superpowers-marketplace": True},
                "extraKnownMarketplaces": {
                    "superpowers-marketplace": {
                        "source": {"source": "github", "repo": "obra/superpowers-marketplace"}
                    }
                },
                "autoMode": {"environment": f"work in {win}"},
            },
            indent=2,
        ),
    )
    put(home, ".claude/.credentials.json", json.dumps({"token": FAKE_OPENAI}))
    put(
        home,
        ".claude/.claude.json",  # CLAUDE_CONFIG_DIR is set, so ~/.claude.json lives here
        json.dumps(
            {
                "oauthAccount": {"emailAddress": "alice@example.com"},
                "projects": {win: {"allowedTools": []}},
                "mcpServers": {
                    "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]},
                    "context7": {
                        "type": "http",
                        "url": "https://mcp.context7.com/mcp",
                        "headers": {"Authorization": FAKE_BEARER},
                    },
                },
            }
        ),
    )
    return home


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """An empty home whose path holds a user name, with agent folders inside it."""
    root = tmp_path / "Users" / USER
    root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("USERPROFILE", str(root))
    monkeypatch.setenv("CODEX_HOME", str(root / ".codex"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(root / ".claude"))
    return root.resolve()


@pytest.fixture
def pc(home) -> Path:
    return make_pc(home)


def kit_run(kit: Path, cwd: Path, *argv, ask=None):
    out = io.StringIO()
    return commands.run(list(argv), cwd, kit, out, ask), out.getvalue()


def secrets_in(text: str) -> list:
    return [s for s in (FAKE_OPENAI, FAKE_GITHUB, FAKE_BEARER) if s in text]
