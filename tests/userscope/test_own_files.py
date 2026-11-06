"""Q4 (reviewer 2026-11-06): PC files kept as the user's own.

The capture allowlist lists them under codex.copy; `kit capture` copies them into
user/codex/own/ (secret scan included) and `install --scope user` puts them back in ~/.codex,
kit-owned, with a verify item of their own.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kit import capture, userscope
from kit.model import EXIT_PARTIAL, EXIT_READY, EXIT_USAGE
from tests.userscope.pc_fixture import FAKE_GITHUB, kit_run, put

SKILL = "---\nname: planner-own\ndescription: My planner. Do NOT use for other work.\n---\n\nBody\n"


def allow(kit: Path, skills=("planner-own",), prompts=("mine.md",)) -> None:
    path = kit / capture.ALLOWLIST_REL
    data = json.loads(path.read_text(encoding="utf-8"))
    data["codex"]["copy"] = {"skills": list(skills), "prompts": list(prompts)}
    path.write_text(json.dumps(data), encoding="utf-8")


def own_pc(home: Path) -> None:
    put(home, ".codex/skills/planner-own/SKILL.md", SKILL)
    put(home, ".codex/skills/planner-own/references/a.md", "ref\r\nwith CRLF\r\n")
    put(home, ".codex/prompts/mine.md", "my prompt\n")
    put(home, ".codex/prompts/other.md", "not listed\n")


def test_capture_copies_only_the_listed_files(kit, home, workspace):
    allow(kit)
    own_pc(home)
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    assert code == EXIT_READY, out
    own = kit / userscope.OWN_DIR
    files = sorted(p.relative_to(own).as_posix() for p in own.rglob("*") if p.is_file())
    assert files == [
        "prompts/mine.md",
        "skills/planner-own/SKILL.md",
        "skills/planner-own/references/a.md",
    ]
    assert (own / "skills/planner-own/references/a.md").read_bytes() == b"ref\r\nwith CRLF\r\n"
    rows = json.loads((kit / "user/codex/inventory.json").read_text(encoding="utf-8"))
    origin = {r["name"]: r["origin"] for r in rows["prompts"]}
    assert origin["mine.md"] == "carried as your own (user/codex/own/prompts)"
    assert origin["other.md"] == "unknown origin (not carried)"


def test_a_file_no_longer_listed_is_removed_on_the_next_capture(kit, home, workspace):
    allow(kit)
    own_pc(home)
    kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    allow(kit, prompts=())
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex")
    assert code == EXIT_READY, out
    assert "REMOVE           user/codex/own/prompts/mine.md" in out
    kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    assert not (kit / userscope.OWN_DIR / "prompts/mine.md").exists()


def test_a_listed_file_that_is_missing_is_a_note(kit, home, workspace):
    allow(kit, skills=("gone",), prompts=())
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex")
    assert code == EXIT_READY, out
    assert "codex skills/gone: not found (or a link), not copied" in out


def test_a_binary_listed_file_is_a_note(kit, home, workspace):
    allow(kit, skills=(), prompts=("bin.md",))
    (home / ".codex/prompts").mkdir(parents=True, exist_ok=True)
    (home / ".codex/prompts/bin.md").write_bytes(b"\xff\xfe\x00bad")
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    assert code == EXIT_READY, out
    assert "user/codex/own/prompts/bin.md: not UTF-8 text, not copied" in out
    assert not (kit / userscope.OWN_DIR).exists()


def test_a_linked_listed_file_is_a_note(kit, home, workspace):
    allow(kit, skills=(), prompts=("mine.md",))
    put(home, ".codex/prompts/real.md", "x\n")
    try:
        (home / ".codex/prompts/mine.md").symlink_to(home / ".codex/prompts/real.md")
    except OSError:
        pytest.skip("this system cannot create symlinks")
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    assert code == EXIT_READY, out
    assert "codex prompts/mine.md: not found (or a link), not copied" in out
    assert not (kit / userscope.OWN_DIR).exists()


def test_a_secret_in_an_own_file_stops_the_capture(kit, home, workspace):
    allow(kit)
    own_pc(home)
    put(home, ".codex/prompts/mine.md", f"token {FAKE_GITHUB}\n")
    code, out = kit_run(kit, workspace, "capture", "--agent", "codex", "--write")
    assert code == EXIT_PARTIAL, out
    assert "user/codex/own/prompts/mine.md" in out and FAKE_GITHUB not in out
    assert not (kit / userscope.OWN_DIR).exists()


def _install(kit, workspace, *extra):
    return kit_run(
        kit, workspace, "install", "--scope", "user", "--agent", "codex", "--yes", "--json", *extra
    )


def test_user_install_puts_own_files_back_and_verifies_them(kit, home, workspace):
    put(kit, f"{userscope.OWN_DIR}/skills/planner-own/SKILL.md", SKILL)
    put(kit, f"{userscope.OWN_DIR}/prompts/mine.md", "my prompt\n")
    code, out = _install(kit, workspace)
    assert code == EXIT_READY, out
    assert (home / ".codex/skills/planner-own/SKILL.md").read_text(encoding="utf-8") == SKILL
    assert (home / ".codex/prompts/mine.md").read_text(encoding="utf-8") == "my prompt\n"
    code, out = kit_run(kit, workspace, "verify", "--scope", "user", "--agent", "codex", "--json")
    assert code == EXIT_READY, out
    items = {i["name"]: i for i in json.loads(out)["agents"]["codex"]["items"]}
    assert items["own"]["verified"] == "PASS"
    (home / ".codex/prompts/mine.md").write_text("edited\n", encoding="utf-8")
    code, out = kit_run(kit, workspace, "verify", "--scope", "user", "--agent", "codex", "--json")
    items = {i["name"]: i for i in json.loads(out)["agents"]["codex"]["items"]}
    assert items["own"]["verified"] != "PASS"


def test_an_identical_pc_copy_is_left_unowned(kit, home, workspace):
    put(kit, f"{userscope.OWN_DIR}/prompts/mine.md", "my prompt\n")
    put(home, ".codex/prompts/mine.md", "my prompt\n")
    code, out = _install(kit, workspace)
    assert code == EXIT_READY, out
    man = json.loads((home / ".kit-state/manifest.json").read_text(encoding="utf-8"))
    owned = [f["path"] for inst in man["installs"] for f in inst["files"]]
    assert any(p.endswith("skills/task-router/SKILL.md") for p in owned)  # the list is real
    assert not any(p.endswith("prompts/mine.md") for p in owned)


@pytest.mark.parametrize("name", ["ralph", "task-router"])
def test_an_own_skill_cannot_shadow_an_omx_or_kit_skill(kit, home, workspace, name, capsys):
    put(kit, f"{userscope.OWN_DIR}/skills/{name}/SKILL.md", SKILL.replace("planner-own", name))
    code, out = _install(kit, workspace)
    assert code == EXIT_USAGE, out
    message = f"skill '{name}' in user/codex/own is also a kit or OMX skill"
    assert message in out + capsys.readouterr().err


def test_without_own_files_there_is_no_own_item(kit, home, workspace):
    code, out = _install(kit, workspace)
    assert code == EXIT_READY, out
    names = [i["name"] for i in json.loads(out)["agents"]["codex"]["items"]]
    assert "own" not in names
