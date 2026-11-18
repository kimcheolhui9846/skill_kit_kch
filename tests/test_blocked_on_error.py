import os
import subprocess
import sys

from kit import app
from kit.fsops import PathEscapeError, State
from kit.model import FAIL
from kit.verify import _verify_skill


def test_unexpected_error_in_run_is_blocked_by_main(workspace, monkeypatch, capsys):
    from kit.app import main

    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(app, "verify_target", boom)
    code = main(["--target", str(workspace)])
    assert code == 2
    err = capsys.readouterr().err
    assert "Status:       BLOCKED" in err and "RuntimeError: kaboom" in err


def test_main_does_not_swallow_system_exit(monkeypatch):
    import pytest

    from kit.app import main

    monkeypatch.setattr(app, "run", lambda argv: (_ for _ in ()).throw(SystemExit(0)))
    with pytest.raises(SystemExit):
        main([])


def test_path_escape_on_state_save_is_reported(run_kit, monkeypatch):
    def boom(self, target, profile_name):
        raise PathEscapeError("refusing path outside target: x")

    monkeypatch.setattr(State, "save", boom)
    code, out = run_kit()  # must not raise; the failure is reported in the output
    assert "error: write failed: refusing path outside target" in out


def test_path_escape_on_log_is_ignored(run_kit, monkeypatch):
    def boom(*a, **k):
        raise PathEscapeError("nope")

    monkeypatch.setattr(app, "write_log", boom)
    code, _ = run_kit()
    assert code == 0


def test_malformed_profile_json_exits_2(workspace, tmp_path, kit_root):
    import shutil

    root = tmp_path / "kit"
    ignore = shutil.ignore_patterns(".git", ".kit", ".venv", "__pycache__")
    shutil.copytree(kit_root, root, ignore=ignore)
    (root / "profiles" / "core.json").write_text("{not json", encoding="utf-8")
    env = dict(os.environ)
    proc = subprocess.run(
        [sys.executable, "-I", str(root / "run_kit.py"), "--target", str(workspace)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "BLOCKED" in proc.stderr


def test_unreadable_skill_file_is_fail(run_kit, workspace, kit_root, monkeypatch):
    run_kit()
    real = type(workspace).read_bytes

    def flaky(self):
        if self.name == "SKILL.md" and workspace in self.parents:
            raise PermissionError("denied")
        return real(self)

    monkeypatch.setattr(type(workspace), "read_bytes", flaky)
    res = _verify_skill(workspace, kit_root, "task-router", True, {})
    assert res.verified == FAIL and "cannot read" in res.detail
