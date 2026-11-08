"""P6-T3 security checks (00_PROMPT 11).

1. Path escape: `..` and absolute paths are covered where each input is read (see
   docs/v2/regression/P6-T3-security.md). Here: a link inside the target that leads outside.
   Windows makes it a directory junction (no admin rights needed), other systems a symlink.
2. The kit never creates a link: no link call in its code, and nothing it installs is a link.
3. The audit rules (remote MCP, secret-like env names, forbidden keys, commands, names) give the
   same verdict for .codex/config.toml (full TOML audit and the Python 3.9/3.10 line scan) and
   for .mcp.json.
4. Every external file matches sources.lock.json, recomputed here without kit.sources.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from kit import audit, capture, mcp_catalog, mcpconfig, sources
from kit.app import main
from kit.fsops import PathEscapeError, safe_path
from kit.model import EXIT_READY, FAIL, PASS, UNVERIFIED
from kit.source_add import _Txn
from tests.conftest import KIT_ROOT, TOML_PASS

REFUSED = "refusing path outside target"


def link_dir(link: Path, to: Path) -> None:
    """A directory link at `link` leading to `to`; skip when this system cannot make one."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(to, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(to), str(link))
        return
    pytest.skip("this system cannot create a directory link")


def is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    return bool(attrs & getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def files_under(root: Path) -> list:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


@pytest.fixture
def kit_main(workspace, monkeypatch, capsys):
    """The real entry point: an unexpected error becomes BLOCKED (exit 2), as for a user."""

    def _run(*argv: str):
        monkeypatch.chdir(workspace)
        code = main(list(argv))
        captured = capsys.readouterr()
        return code, captured.out + captured.err

    return _run


@pytest.fixture
def outside(tmp_path) -> Path:
    path = tmp_path / "outside"
    path.mkdir()
    return path


# ---------------------------------------------------------------- 1. links leading outside


def test_safe_path_refuses_a_directory_link_that_leads_outside(workspace, outside):
    link_dir(workspace / "sub", outside)
    assert is_link(workspace / "sub")
    with pytest.raises(PathEscapeError):
        safe_path(workspace, "sub/file.txt")
    assert safe_path(workspace, "other/file.txt") == (workspace / "other/file.txt").resolve()


LINK_CASES = [
    (".kit", ("install", "--agent", "codex", "--offline")),
    # P6-T3 defect: the install manifest was written through this link, outside the workspace
    (".kit/state", ("install", "--agent", "both", "--offline")),
    (".kit/work", ("task", "add", "T-1", "--title", "x")),
    (".kit/work", ("recover", "decide", "keep the old API")),
    (".agents", ("install", "--agent", "codex", "--offline")),
    (".claude", ("install", "--agent", "claude", "--offline")),
    (".claude", ("install", "--agent", "claude", "--offline", "--hooks")),
    (".codex", ("install", "--agent", "codex", "--offline", "--hooks")),
    (".codex", ("install", "--agent", "codex", "--offline", "--mcp", "sequential-thinking")),
    (".agents", ("--offline",)),  # legacy installer
]


@pytest.mark.parametrize(
    "link_rel, argv", LINK_CASES, ids=[f"{r}:{' '.join(a[:3])}" for r, a in LINK_CASES]
)
def test_a_link_inside_the_target_never_leads_a_write_outside(
    kit_main, workspace, outside, link_rel, argv
):
    link_dir(workspace / link_rel, outside)
    code, out = kit_main(*argv)
    assert code != EXIT_READY, out
    assert REFUSED in out
    assert "unexpected" not in out  # P7-T1: a safety refusal is not reported as a crash
    assert files_under(outside) == []


def test_the_manifest_link_is_refused_before_anything_is_written(kit_main, workspace, outside):
    link_dir(workspace / ".kit/state", outside)
    code, out = kit_main("install", "--agent", "both", "--offline")
    assert code == 2 and "install-manifest.json" in out
    written = [p for p in files_under(workspace) if not p.startswith(".kit/state/")]
    assert written == []


def test_source_add_writes_cannot_follow_a_link_out_of_the_kit(kit, outside):
    link_dir(kit / "third_party/evil", outside)
    txn = _Txn(kit)
    with pytest.raises(PathEscapeError):
        txn.write("third_party/evil/SKILL.md", b"x")
    with pytest.raises(PathEscapeError):
        txn.delete("third_party/evil/SKILL.md")
    txn.rollback()
    assert files_under(outside) == []


def test_capture_writes_cannot_follow_a_link_out_of_the_kit(kit, outside):
    link_dir(kit / "user/codex", outside)
    result = capture.CaptureResult(files={"user/codex/AGENTS.md": "# mine\n"})
    with pytest.raises(PathEscapeError):
        capture.write(kit, result, ["codex"])
    assert files_under(outside) == []


# ---------------------------------------------------------------- 2. the kit makes no links

LINK_CALLS = {"symlink", "symlink_to", "hardlink_to", "CreateJunction", "CreateHardLink"}


def link_calls(source: str) -> list:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            owner = getattr(getattr(func, "value", None), "id", "")
            if name in LINK_CALLS or (name == "link" and owner == "os"):
                found.append(f"{name}() line {node.lineno}")
            for kw in node.keywords:
                if kw.arg == "symlinks" and getattr(kw.value, "value", False) is True:
                    found.append(f"symlinks=True line {node.lineno}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "mklink" in node.value.lower():
                found.append(f"mklink line {node.lineno}")
    return found


def test_the_link_checker_finds_every_form():
    source = (
        "import os, shutil\nos.symlink('a', 'b')\nPath('b').symlink_to('a')\n"
        "Path('c').hardlink_to('a')\nos.link('a', 'd')\nshutil.copytree('a', 'b', symlinks=True)\n"
        "run('cmd /c mklink /J a b')\n_winapi.CreateJunction('a', 'b')\n"
        "shutil.copytree('a', 'b', symlinks=False)\nos.path.islink('a')\nreq.link('R', 't')\n"
    )
    assert len(link_calls(source)) == 7


def test_kit_code_never_creates_a_link():
    files = sorted((KIT_ROOT / "kit").rglob("*.py")) + [KIT_ROOT / "run_kit.py"]
    found = {
        f.relative_to(KIT_ROOT).as_posix(): calls
        for f in files
        if (calls := link_calls(f.read_text(encoding="utf-8")))
    }
    assert found == {}


@pytest.mark.parametrize(
    "argv",
    [
        ("install", "--agent", "both", "--offline", "--hooks"),
        ("install", "--agent", "both", "--offline", "--profile", "core,hitl,python,web"),
        ("--offline",),
    ],
    ids=["both-hooks", "both-wide-profile", "legacy"],
)
def test_installed_skills_are_copies_not_links(run_kit, workspace, argv):
    code, out = run_kit(*argv)
    assert code in (EXIT_READY, 1), out
    paths = list(workspace.rglob("*"))
    assert any(p.name == "SKILL.md" for p in paths)
    assert [p.relative_to(workspace).as_posix() for p in paths if is_link(p)] == []


# ---------------------------------------------------------------- 3. TOML and JSON audit


@pytest.fixture(scope="module")
def rules() -> dict:
    return mcp_catalog.allowlist(KIT_ROOT)


def _value(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(x) for x in v) + "]"
    return json.dumps(v)


def to_toml(name: str, cfg: dict) -> str:
    lines = [f"[mcp_servers.{name}]"]
    lines += [f"{k} = {_value(v)}" for k, v in cfg.items() if k != "env"]
    if "env" in cfg:
        lines.append(f"[mcp_servers.{name}.env]")
        lines += [f"{k} = {_value(v)}" for k, v in cfg["env"].items()]
    return "\n".join(lines) + "\n"


def three_audits(workspace: Path, name: str, cfg: dict, rules: dict, monkeypatch):
    """(full TOML, line scan, .mcp.json) results for one server written both ways."""
    (workspace / ".codex").mkdir(exist_ok=True)
    (workspace / ".codex/config.toml").write_text(to_toml(name, cfg), encoding="utf-8")
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": {name: cfg}}, indent=2), encoding="utf-8"
    )
    full = audit.audit_target(workspace, KIT_ROOT, rules)
    jsn = audit.audit_mcp_json(workspace, KIT_ROOT, rules)
    with monkeypatch.context() as m:
        m.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
        scan = audit.audit_target(workspace, KIT_ROOT, rules)
    return full, scan, jsn


NPX = {"command": "npx", "args": ["-y", "pkg@1"]}
RULE_CASES = {
    "name not allowed": ("evil", NPX, "evil: not in mcp/allowlist.json"),
    "url (remote)": ("sequential-thinking", {**NPX, "url": "https://x.invalid/mcp"}, "url"),
    "bearer token key": (
        "sequential-thinking",
        {**NPX, "bearer_token_env_var": "X"},
        "forbidden key 'bearer_token_env_var'",
    ),
    "command not allowed": (
        "sequential-thinking",
        {"command": "bash", "args": ["-c", "x"]},
        "command 'bash' is not allowed",
    ),
    "command path": (
        "sequential-thinking",
        {"command": "C:/tools/curl.exe"},
        "command 'C:/tools/curl.exe' is not allowed",
    ),
    "remote in args": (
        "sequential-thinking",
        {"command": "npx", "args": ["mcp-remote", "https://x.invalid"]},
        "remote endpoint",
    ),
    "secret env value": (
        "sequential-thinking",
        {**NPX, "env": {"GITHUB_TOKEN": "abc"}},
        "secret-like env 'GITHUB_TOKEN'",
    ),
    "secret env_vars name": (
        "sequential-thinking",
        {**NPX, "env_vars": ["OPENAI_API_KEY"]},
        "secret-like env 'OPENAI_API_KEY'",
    ),
    "declared name with a value": (
        "context7",
        {**NPX, "env": {"CONTEXT7_API_KEY": "abc"}},
        "secret-like env 'CONTEXT7_API_KEY'",
    ),
    "undeclared name next to a declared one": (
        "context7",
        {**NPX, "env_vars": ["CONTEXT7_API_KEY", "OTHER_TOKEN"]},
        "secret-like env 'OTHER_TOKEN'",
    ),
}


@pytest.mark.parametrize("case", list(RULE_CASES))
def test_each_audit_rule_fails_in_toml_line_scan_and_json(workspace, rules, monkeypatch, case):
    name, cfg, fragment = RULE_CASES[case]
    for label, item in zip(
        ("toml", "scan", "json"), three_audits(workspace, name, cfg, rules, monkeypatch)
    ):
        assert item.verified == FAIL, (label, item.detail)
        assert fragment in item.detail, (label, item.detail)


def test_an_inline_server_table_is_audited_by_the_line_scan(workspace, rules):
    (workspace / ".codex").mkdir()
    text = '[mcp_servers]\nevil = { command = "bash", args = ["-c", "x"] }\n'
    (workspace / ".codex/config.toml").write_text(text, encoding="utf-8")
    problems = audit.scan_lines(text, rules)
    assert "evil: not in mcp/allowlist.json" in problems
    assert "evil: command 'bash' is not allowed" in problems
    assert audit.audit_target(workspace, KIT_ROOT, rules).verified == FAIL


@pytest.mark.parametrize(
    "transport", [{"type": "http", "url": "https://x.invalid"}, {"type": "sse"}, {"headers": {}}]
)
def test_json_only_remote_forms_fail(workspace, rules, transport):
    (workspace / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"sequential-thinking": {**NPX, **transport}}}), encoding="utf-8"
    )
    assert audit.audit_mcp_json(workspace, KIT_ROOT, rules).verified == FAIL


@pytest.mark.parametrize(
    "name, cfg",
    [
        ("sequential-thinking", NPX),
        ("context7", {**NPX, "env_vars": ["CONTEXT7_API_KEY"]}),
        ("context7", {**NPX, "env": {"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"}}),
    ],
    ids=["allowed", "declared-env_vars", "declared-reference"],
)
def test_allowed_servers_pass_everywhere(workspace, rules, monkeypatch, name, cfg):
    full, scan, jsn = three_audits(workspace, name, cfg, rules, monkeypatch)
    assert full.verified == TOML_PASS and jsn.verified == PASS, (full.detail, jsn.detail)
    assert scan.verified == UNVERIFIED, scan.detail  # the line scan never claims PASS


@pytest.mark.parametrize("line_scan", [False, True], ids=["tomllib", "line-scan"])
def test_every_installable_catalog_server_passes_its_own_audit(
    run_kit, workspace, monkeypatch, line_scan
):
    """P6-T3 defect: on Python 3.9/3.10 the line scan blocked the kit's own context7 block."""
    if line_scan:
        monkeypatch.setattr(mcpconfig, "parse_toml", lambda text: (None, None, ""))
    servers = mcp_catalog.load_servers(KIT_ROOT)
    names = [n for n, e in servers.items() if mcp_catalog.installable(e)]
    argv = ["install", "--agent", "both", "--offline"]
    for name in names:
        argv += ["--mcp", name]
    code, out = run_kit(*argv)
    assert code == EXIT_READY, out
    assert "FAIL" not in out
    config = (workspace / ".codex/config.toml").read_text(encoding="utf-8")
    assert all(f"[mcp_servers.{n}]" in config for n in names)
    assert set(json.loads((workspace / ".mcp.json").read_text("utf-8"))["mcpServers"]) >= set(names)


# ---------------------------------------------------------------- 4. sources.lock.json


def test_every_external_file_matches_the_lock_recomputed_independently():
    lock = json.loads((KIT_ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    listed = set()
    for entry in lock["sources"]:
        files = entry["files"]
        for rel, sha in files.items():
            listed.add(rel)
            data = (KIT_ROOT / rel).read_bytes()
            assert hashlib.sha256(data).hexdigest() == sha, rel
        lines = "".join(f"{rel}\0{sha}\n" for rel, sha in sorted(files.items()))
        assert hashlib.sha256(lines.encode("utf-8")).hexdigest() == entry["content_sha256"]
    on_disk = {
        p.relative_to(KIT_ROOT).as_posix()
        for p in (KIT_ROOT / sources.THIRD_PARTY).rglob("*")
        if p.is_file()
    }
    assert on_disk and on_disk <= listed


def test_a_changed_byte_is_found_by_the_lock_check(kit):
    lock = json.loads((kit / "sources.lock.json").read_text(encoding="utf-8"))
    rel = sorted(lock["sources"][0]["files"])[0]
    path = kit / rel
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    assert any(rel in p and "sha256" in p for p in sources.check(kit))
