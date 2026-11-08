"""P3-T3 install manifest and v1 adoption (ADR-006, REQ-COMPAT-004). TC-MAN-01/02."""

from __future__ import annotations

import json

import pytest

from kit import manifest
from kit.adapters.codex import CodexAdapter
from kit.fsops import State, sha256
from kit.manifest import Manifest, ManifestError, adopt_v1, load, manifest_path, save
from kit.profiles import load_profile
from kit.register import apply_changes
from tests.conftest import tree_digest


def _blocks():
    a = CodexAdapter()
    return {
        a.policy.rel: (a.policy.begin, a.policy.end),
        a.mcp_config.rel: (a.mcp_config.begin, a.mcp_config.end),
    }


def _install_v1(kit_root, workspace, profile="python"):
    prof = load_profile(kit_root, profile)
    changes = CodexAdapter().plan(workspace, kit_root, prof, State(), bool(prof.mcp))
    apply_changes(workspace, changes, State(), "s", profile)


def test_missing_manifest_is_empty(workspace):
    m = load(manifest_path(workspace, "project"))
    assert m.installs == [] and m.scope == "project"


def test_roundtrip_keeps_unknown_fields(workspace):
    path = manifest_path(workspace, "project")
    m = Manifest()
    m.record({"agent": "claude", "profiles": ["core", "hitl"], "policy": "standard"})
    m.record({"agent": "codex", "profiles": ["core"], "policy": "standard"})
    m.extra["future_field"] = {"x": 1}
    save(path, m)
    again = load(path)
    assert [i["agent"] for i in again.installs] == ["claude", "codex"]
    assert again.install_for("claude")["json_keys"] == []
    assert again.extra == {"future_field": {"x": 1}}
    assert not path.with_name(path.name + ".kit-tmp").exists()


def test_record_replaces_same_agent():
    m = Manifest()
    m.record({"agent": "codex", "profiles": ["core"]})
    m.record({"agent": "codex", "profiles": ["web"]})
    assert len(m.installs) == 1 and m.installs[0]["profiles"] == ["web"]
    m.forget("codex")
    assert m.installs == []


@pytest.mark.parametrize(
    "content",
    [
        b"{broken",
        b"\xff\xfe",
        b"[]",
        b'{"installs": []}',
        b'{"schema": 2, "installs": []}',
        b'{"schema": 1, "installs": [{"no_agent": 1}]}',
        b'{"schema": 1, "scope": "user", "installs": []}',
    ],
)
def test_untrusted_manifest_raises_and_is_not_rewritten(workspace, content):
    path = manifest_path(workspace, "project")
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    with pytest.raises(ManifestError):
        load(path, "project")
    assert path.read_bytes() == content


def test_user_scope_path(tmp_path):
    assert manifest_path(tmp_path, "user") == tmp_path / ".kit-state" / "manifest.json"


def test_adopt_clean_v1_workspace(kit_root, workspace):
    _install_v1(kit_root, workspace)
    before = tree_digest(workspace)
    result = adopt_v1(workspace, "codex", _blocks())
    assert result.conflicts == []
    entry = result.entry
    assert entry["adopted_from"] == "v1" and entry["profiles"] == ["python"]
    assert {b["path"] for b in entry["blocks"]} == {"AGENTS.md", ".codex/config.toml"}
    assert len(entry["files"]) == 26  # the 11 skills' files
    assert tree_digest(workspace) == before  # adoption reads only


def test_adopt_reports_user_edits(kit_root, workspace):
    _install_v1(kit_root, workspace, "core")
    skill = workspace / ".agents/skills/benchmark/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"\nmine\n")
    agents = workspace / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    agents.write_text(
        text.replace("<!-- hackathon-kit:end -->", "edit\n<!-- hackathon-kit:end -->"),
        encoding="utf-8",
    )
    result = adopt_v1(workspace, "codex", _blocks())
    paths = {c.split(":")[0] for c in result.conflicts}
    assert paths == {".agents/skills/benchmark/SKILL.md", "AGENTS.md"}
    assert all(f["path"] != ".agents/skills/benchmark/SKILL.md" for f in result.entry["files"])


def test_adopt_accepts_known_kit_content(kit_root, workspace):
    _install_v1(kit_root, workspace, "core")
    rel = ".agents/skills/benchmark/SKILL.md"
    state = json.loads((workspace / ".kit/state.json").read_text(encoding="utf-8"))
    state["files"][rel] = "0" * 64  # stale record
    (workspace / ".kit/state.json").write_text(json.dumps(state), encoding="utf-8")
    current = sha256((workspace / rel).read_bytes())
    assert any(rel in c for c in adopt_v1(workspace, "codex", _blocks()).conflicts)
    result = adopt_v1(workspace, "codex", _blocks(), {rel: [current]})
    assert not any(rel in c for c in result.conflicts)


def test_adopt_without_v1_state(workspace):
    assert adopt_v1(workspace, "codex", _blocks()).entry is None


def test_adopt_unreadable_v1_state(workspace):
    (workspace / ".kit").mkdir()
    (workspace / ".kit/state.json").write_text("{oops", encoding="utf-8")
    result = adopt_v1(workspace, "codex", _blocks())
    assert result.entry is None and result.conflicts


def test_module_constants():
    assert manifest.PROJECT_REL == ".kit/state/install-manifest.json"
    assert manifest.SCHEMA == 1
