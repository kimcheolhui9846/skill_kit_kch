"""P6-T2 verification matrix: the items whose 00_PROMPT 11 method no single earlier test followed
exactly. The other V items are mapped to their tests in docs/v2/regression/P6-T2-matrix.md.

V-04 three installs in a row, V-05 user content in every file the kit touches, V-07 the
codex -> claude -> both -> uninstall claude order, V-08 every dry run leaves the workspace and
HOME as they were, V-09 the new path under the network-blocking fixture, V-16 a path with a
space and Hangul plus a CRLF original and the AST check for encoding=, V-17 planted tokens
never reach stdout, JSON, the report file or the logs, V-18 project-scope commands leave HOME
as it was.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from kit.model import EXIT_BLOCKED, EXIT_READY
from tests.conftest import KIT_ROOT, tree_digest

CODEX_OWNED = ("AGENTS.md", ".agents/", ".codex/")
TOKEN = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3i2"


def digest(root: Path, skip: tuple = (".kit/",)) -> dict:
    return tree_digest(root, exclude=skip)


def must(run_kit, *argv, cwd=None) -> str:
    code, out = run_kit(*argv, cwd=cwd)
    assert code == EXIT_READY, out
    return out


# ---------------------------------------------------------------- V-04


def test_v04_three_installs_in_a_row_leave_the_same_tree(run_kit, workspace):
    trees = []
    for _ in range(3):
        must(run_kit, "install", "--agent", "both", "--offline")
        trees.append(digest(workspace))
    assert trees[0] == trees[1] == trees[2]
    manifest = json.loads((workspace / ".kit/state/install-manifest.json").read_text("utf-8"))
    assert sorted(i["agent"] for i in manifest["installs"]) == ["claude", "codex"]


# ---------------------------------------------------------------- V-05


USER_FILES = {
    "AGENTS.md": b"# Team rules\r\n\r\nKeep this line.\r\n",
    "CLAUDE.md": "# 팀 규칙\n\n이 줄은 그대로.\n".encode(),
    ".codex/config.toml": b'model = "mine"\n\n[profiles.fast]\nmodel_reasoning_effort = "low"\n',
    ".mcp.json": b'{\n  "x-team": "keep me",\n  "mcpServers": {}\n}\n',
    ".claude/settings.json": b'{\n  "theme": "dark",\n  "permissions": {"allow": ["Bash(ls)"]}}\n',
}


def _plant(ws: Path) -> None:
    for rel, data in USER_FILES.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes(data)


def test_v05_user_content_survives_install_both(run_kit, workspace):
    _plant(workspace)
    must(run_kit, "install", "--agent", "both", "--offline", "--hooks")
    for rel in ("AGENTS.md", "CLAUDE.md"):
        assert (workspace / rel).read_bytes().startswith(USER_FILES[rel]), rel
    toml = (workspace / ".codex/config.toml").read_bytes()
    assert toml.startswith(b'model = "mine"\n')
    assert b'[profiles.fast]\nmodel_reasoning_effort = "low"' in toml
    assert json.loads((workspace / ".mcp.json").read_text("utf-8"))["x-team"] == "keep me"
    settings = json.loads((workspace / ".claude/settings.json").read_text("utf-8"))
    assert settings["theme"] == "dark" and settings["permissions"] == {"allow": ["Bash(ls)"]}
    assert "hooks" in settings  # the kit did write its part next to the user's


def test_v05_uninstall_gives_the_user_files_back(run_kit, workspace):
    _plant(workspace)
    must(run_kit, "install", "--agent", "both", "--offline", "--hooks")
    must(run_kit, "uninstall", "--agent", "both")
    assert (workspace / "AGENTS.md").read_bytes() == USER_FILES["AGENTS.md"]
    assert (workspace / "CLAUDE.md").read_bytes() == USER_FILES["CLAUDE.md"]
    assert json.loads((workspace / ".mcp.json").read_text("utf-8"))["x-team"] == "keep me"
    assert (workspace / ".codex/config.toml").read_bytes() == USER_FILES[".codex/config.toml"]
    settings = json.loads((workspace / ".claude/settings.json").read_text("utf-8"))
    assert settings == json.loads(USER_FILES[".claude/settings.json"])


def test_v05_a_user_server_outside_the_allowlist_blocks_but_stays_as_written(run_kit, workspace):
    """The run is BLOCKED and says why; the user's server is neither removed nor changed.
    B-3 (2026-11-08): the v2 audit runs before the write, so CLAUDE.md stays as it was too
    (the legacy installer still audits after writing, test_audit.py)."""
    mine = b'{"mcpServers": {"mine": {"command": "my-tool"}}}\n'
    (workspace / ".mcp.json").write_bytes(mine)
    (workspace / "CLAUDE.md").write_bytes(USER_FILES["CLAUDE.md"])
    code, out = run_kit("install", "--agent", "claude", "--offline")
    assert code == EXIT_BLOCKED and "mine: not in mcp/allowlist.json" in out
    assert (workspace / ".mcp.json").read_bytes() == mine
    assert (workspace / "CLAUDE.md").read_bytes() == USER_FILES["CLAUDE.md"]


# ---------------------------------------------------------------- V-07


def test_v07_codex_files_keep_their_hash_through_the_whole_order(run_kit, workspace):
    must(run_kit, "install", "--agent", "codex", "--offline")
    codex = {k: v for k, v in digest(workspace).items() if k.startswith(CODEX_OWNED)}
    assert codex
    must(run_kit, "install", "--agent", "claude", "--offline")
    must(run_kit, "install", "--agent", "both", "--offline")
    must(run_kit, "uninstall", "--agent", "claude")
    after = {k: v for k, v in digest(workspace).items() if k.startswith(CODEX_OWNED)}
    assert after == codex
    assert not (workspace / "CLAUDE.md").exists() and not (workspace / ".claude/skills").exists()
    must(run_kit, "verify", "--agent", "codex", "--offline")


# ---------------------------------------------------------------- V-08


def test_v08_every_dry_run_leaves_workspace_and_home_alone(run_kit, workspace, isolated_home):
    (workspace / "AGENTS.md").write_bytes(b"# mine\n")
    must(run_kit, "install", "--agent", "codex", "--offline")
    stamp = sorted(p.name for p in (workspace / ".kit/backups").iterdir())[0]
    ws_before, home_before = digest(workspace, ()), digest(isolated_home, ())
    for argv in (
        ("plan", "--agent", "both"),
        ("install", "--agent", "both", "--dry-run", "--offline"),
        ("update", "--agent", "codex", "--dry-run"),
        ("uninstall", "--agent", "codex", "--dry-run"),
        ("restore", "--backup", stamp, "--dry-run"),
        ("install", "--agent", "codex", "--scope", "user", "--dry-run", "--offline"),
    ):
        run_kit(*argv)
        assert digest(workspace, ()) == ws_before, argv
        assert digest(isolated_home, ()) == home_before, argv
    # capture without --write is a dry run too (it reads HOME, writes nothing into the kit)
    kit_before = digest(KIT_ROOT / "user", ())
    run_kit("capture", "--agent", "both")
    assert digest(KIT_ROOT / "user", ()) == kit_before
    assert digest(isolated_home, ()) == home_before


# ---------------------------------------------------------------- V-09


def test_v09_new_path_runs_with_the_network_blocked(run_kit, workspace, no_network):
    for argv in (
        ("plan", "--agent", "both"),
        ("install", "--agent", "both", "--offline"),
        ("verify", "--agent", "both", "--offline"),
        ("update", "--agent", "both", "--offline"),
        ("uninstall", "--agent", "both"),
    ):
        must(run_kit, *argv)


# ---------------------------------------------------------------- V-16


def test_v16_space_hangul_path_and_crlf_original(run_kit, tmp_path):
    ws = tmp_path / "my work" / "작업 공간"
    ws.mkdir(parents=True)
    original = "# 내 규칙\r\nline two\r\n".encode()
    (ws / "AGENTS.md").write_bytes(original)
    must(run_kit, "install", "--agent", "both", "--offline", cwd=ws)
    assert (ws / "AGENTS.md").read_bytes().startswith(original)
    assert (ws / ".claude/skills/task-router/SKILL.md").is_file()
    must(run_kit, "verify", "--agent", "both", "--offline", cwd=ws)
    must(run_kit, "uninstall", "--agent", "both", cwd=ws)
    assert (ws / "AGENTS.md").read_bytes() == original


def _text_io_without_encoding(path: Path) -> list:
    bad = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        keys = {k.arg for k in node.keywords}
        if "encoding" in keys:
            continue
        if name == "read_text" and not node.args or name == "write_text" and len(node.args) < 2:
            bad.append(f"{node.lineno} {name}")
        elif name == "open":
            if isinstance(fn, ast.Attribute) and getattr(fn.value, "id", "") == "tarfile":
                continue  # an archive, not text
            modes = [a for a in node.args if isinstance(a, ast.Constant)]
            modes += [k.value for k in node.keywords if k.arg == "mode"]
            if not any(isinstance(m, ast.Constant) and "b" in str(m.value) for m in modes):
                bad.append(f"{node.lineno} open")
        elif name in ("run", "Popen", "check_output") and keys & {"text", "universal_newlines"}:
            bad.append(f"{node.lineno} {name} text without encoding")
    return bad


def test_v16_every_text_io_in_the_kit_names_its_encoding():
    files = [p for p in sorted((KIT_ROOT / "kit").rglob("*.py")) if "__pycache__" not in p.parts]
    files += [
        p for p in sorted((KIT_ROOT / "shared").rglob("*.py")) if "__pycache__" not in p.parts
    ]
    files += [KIT_ROOT / "run_kit.py"]
    found = {p.relative_to(KIT_ROOT).as_posix(): _text_io_without_encoding(p) for p in files}
    assert {k: v for k, v in found.items() if v} == {}
    assert len(files) > 50


def test_v16_the_ast_check_catches_what_it_should(tmp_path):
    p = tmp_path / "m.py"
    p.write_text(
        "open('a')\nopen('a', 'rb')\nPath('a').read_text()\nPath('a').write_text('x')\n"
        "Path('a').read_text(encoding='utf-8')\nsubprocess.run(['x'], text=True)\n"
        "tarfile.open(fileobj=f, mode='r:')\n",
        encoding="utf-8",
    )
    assert _text_io_without_encoding(p) == [
        "1 open",
        "3 read_text",
        "4 write_text",
        "6 run text without encoding",
    ]


# ---------------------------------------------------------------- V-17


def test_v17_planted_tokens_never_reach_any_output(run_kit, workspace, monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setenv("MY_API_KEY", TOKEN)
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"mine": {"command": "x", "env": {"GITHUB_TOKEN": TOKEN}}}}),
        encoding="utf-8",
    )
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_text(
        f'[mcp_servers.mine]\ncommand = "x"\nenv = {{ API_TOKEN = "{TOKEN}" }}\n', encoding="utf-8"
    )
    report = tmp_path / "report.json"
    outputs = []
    for argv in (
        ("plan", "--agent", "both", "--verbose"),
        ("install", "--agent", "both", "--offline", "--verbose", "--report-json", str(report)),
        ("install", "--agent", "both", "--offline", "--json"),
        ("verify", "--agent", "both", "--offline", "--verbose"),
        ("doctor",),
    ):
        outputs.append(run_kit(*argv)[1])
    # paths that do print what the user typed, so masking itself is exercised
    for argv in (
        ("task", "add", "T-1", "--title", f"rotate {TOKEN}", "--requires", "REQ-001"),
        ("task", "list", "--json"),
        ("recover", "save", "--note", f"token={TOKEN}", "--command", f"gh auth {TOKEN}"),
        ("recover", "decide", f"use {TOKEN} for now"),
        ("recover",),
        ("recover", "--json"),
    ):
        outputs.append(run_kit(*argv)[1])
    outputs += [
        (workspace / rel).read_text(encoding="utf-8")
        for rel in (".kit/work/wip.json", ".kit/work/decisions.md")
    ]
    outputs.append(report.read_text(encoding="utf-8"))
    outputs += [
        p.read_text(encoding="utf-8") for p in (workspace / ".kit/logs").rglob("*") if p.is_file()
    ]
    assert len(outputs) > 6
    joined = "\n".join(outputs)  # the run did reach the planted values: it names them
    assert "secret-like env 'API_TOKEN'" in joined and "secret-like env 'GITHUB_TOKEN'" in joined
    for text in outputs:
        assert TOKEN not in text and TOKEN[4:20] not in text


# ---------------------------------------------------------------- V-18


def test_v18_project_scope_commands_leave_home_alone(run_kit, workspace, isolated_home):
    (isolated_home / ".codex").mkdir()
    (isolated_home / ".codex/config.toml").write_bytes(b'model = "mine"\n')
    (isolated_home / ".claude").mkdir()
    (isolated_home / ".claude/settings.json").write_bytes(b'{"theme": "dark"}\n')
    before = digest(isolated_home, ())
    for argv in (
        ("install", "--agent", "both", "--offline", "--hooks"),
        ("verify", "--agent", "both", "--offline"),
        ("update", "--agent", "both", "--offline"),
        ("doctor",),
        ("task", "add", "T-1", "--title", "t", "--requires", "REQ-001"),
        ("task", "start", "T-1"),
        ("recover", "save", "--note", "n"),
        ("recover",),
        ("req", "add", "REQ-001", "--text", "t"),
        ("trace", "check"),
        ("uninstall", "--agent", "both"),
    ):
        run_kit(*argv)
        assert digest(isolated_home, ()) == before, argv


@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_v18_also_holds_for_one_agent_at_a_time(run_kit, workspace, isolated_home, agent):
    before = digest(isolated_home, ())
    must(run_kit, "install", "--agent", agent, "--offline")
    must(run_kit, "uninstall", "--agent", agent)
    assert digest(isolated_home, ()) == before


def test_v17_masking_each_value_keeps_the_json_valid():
    from kit.logs import mask, mask_tree

    data = {"detail": "server said token=abc", "list": ["password: x", 3, None]}
    with pytest.raises(ValueError):  # the old way: mask the dumped text
        json.loads(mask(json.dumps(data)))
    doc = json.loads(json.dumps(mask_tree(data)))
    assert doc == {"detail": "server said token=***", "list": ["password=***", 3, None]}


@pytest.mark.parametrize(
    "argv",
    [
        ("task", "list", "--json"),
        ("task", "status", "--json"),
        ("req", "list", "--json"),
        ("ce", "list", "--json"),
    ],
)
def test_v17_every_hitl_json_output_is_masked_and_valid(run_kit, workspace, argv):
    run_kit("task", "add", "T-1", "--title", "password: hunter2", "--requires", "REQ-001")
    run_kit("req", "add", "REQ-001", "--text", "api_key=sk-zz9 must stay out")
    run_kit(
        "ce",
        "add",
        "CE-001",
        "--function",
        "f()",
        "--req",
        "REQ-001",
        "--category",
        "boundary",
        "--origin",
        "black-box",
        "--assumption",
        "token=abc assumption",
        "--input",
        "x",
        "--would-catch",
        "y",
    )
    out = run_kit(*argv)[1]
    json.loads(out)
    assert not any(v in out for v in ("hunter2", "sk-zz9", "token=abc"))
