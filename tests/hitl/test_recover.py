"""P5-T7 session recovery (00_PROMPT 10.7, REQ-SESS-001~003).

TC-HTL-16 (V-15) recover restores the seven items from two approved tasks and one in
progress, with the temporary state apart; TC-HTL-17 HANDOFF.md holds the approved state only
and the WIP lives in .kit/work/wip.json; TC-HTL-18 a HANDOFF.md the kit did not write is left
alone and every state file is under .kit/. Also: a broken WIP falls back to the approved state,
a folder without git, the submit snapshot, the hook approval catch-up.
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from kit import approval_hooks, commands, recover, tasks
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_TARGET, EXIT_USAGE
from tests.conftest import KIT_ROOT

SEP = "|---|---|---|---|---|---|---|\n"
RISK_SEP = "| 항목 | 이유 | 검토자 확인 방법 |\n|---|---|---|\n"


def kit(ws: Path, *argv, ask=None):
    out = io.StringIO()
    code = commands.run([*argv, "--target", str(ws)], ws, KIT_ROOT, out, ask)
    return code, out.getvalue()


def ok(ws: Path, *argv) -> str:
    code, out = kit(ws, *argv)
    assert code == EXIT_READY, out
    return out


def report(ws: Path, task_id: str, req: str, status: str = "PASS", risk: str = "", plan: str = ""):
    ok(ws, "task", "report", task_id)
    p = ws / tasks.default_report(task_id)
    text = p.read_text(encoding="utf-8")
    rows = (
        f"| TC-{task_id}-a | {req} | normal | 'a' | 1 | 1 | PASS |\n"
        f"| TC-{task_id}-b | {req} | boundary | '' | 0 | 0 | {status} |\n"
    )
    text = text.replace(SEP, SEP + rows, 1)
    if risk:
        text = text.replace(RISK_SEP, RISK_SEP + f"| {risk} | not measured | run it |\n", 1)
    text = text.replace("- 무엇을 했는가(3줄 이내):", f"- 무엇을 했는가(3줄 이내): {task_id} done")
    if plan:
        text = text.replace("승인하시면 다음으로 <Task ID: 내용>을 진행합니다.", plan)
    p.write_bytes(text.encode("utf-8"))


def run_task(ws: Path, task_id: str, req: str, approve: bool = True, **kw) -> None:
    ok(ws, "task", "start", task_id)
    report(ws, task_id, req, **kw)
    ok(ws, "task", "submit", task_id)
    if approve:
        ok(ws, "task", "approve", task_id, "--by", "agent-recorded", "--quote", "승인")


@pytest.fixture
def two_approved(workspace):
    """T-1 and T-2 approved, T-3 in progress with a saved WIP: the 00_PROMPT 10.7 fixture."""
    (workspace / "src").mkdir()
    (workspace / "src/a.py").write_bytes(b"a = 1\n")
    (workspace / "old.txt").write_bytes(b"old\n")
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    ok(
        workspace,
        "task",
        "add",
        "T-2",
        "--title",
        "writer",
        "--requires",
        "REQ-002",
        "--depends-on",
        "T-1",
    )
    ok(
        workspace,
        "task",
        "add",
        "T-3",
        "--title",
        "cli",
        "--requires",
        "REQ-003",
        "--depends-on",
        "T-2",
    )
    run_task(workspace, "T-1", "REQ-001")
    ok(
        workspace,
        "recover",
        "decide",
        "keep IDs case-sensitive (user: '대소문자 구분')",
        "--task",
        "T-1",
    )
    run_task(
        workspace,
        "T-2",
        "REQ-002",
        status="NOT RUN: no Windows here",
        risk="cp949 console",
        plan="승인하시면 다음으로 T-3: CLI를 진행합니다.",
    )
    # after T-2 was submitted: one change, one new file, one deleted file
    (workspace / "src/a.py").write_bytes(b"a = 2\n")
    (workspace / "src/b.py").write_bytes(b"b = 1\n")
    (workspace / "old.txt").unlink()
    ok(workspace, "task", "start", "T-3")
    ok(workspace, "task", "subtask", "add", "T-3", "parse args")
    ok(
        workspace,
        "recover",
        "save",
        "--subtask",
        "T-3.1",
        "--note",
        "half of the flags done",
        "--command",
        "pytest -q tests/test_cli.py",
        "--tests",
        "3 passed, 1 failed",
        "--error",
        "test_help fails: usage line differs",
        "--error",
        "flaky timeout",
    )
    return workspace


# ---------------------------------------------------------------- TC-HTL-16 / V-15


def test_recover_restores_the_seven_items_and_keeps_wip_apart(two_approved):
    code, out = kit(two_approved, "recover")
    assert code == EXIT_READY, out
    approved, _, temporary = out.partition("Temporary (not approved")
    # 1 current task and its state
    assert "Current task:   T-3 IN_PROGRESS - cli [subtasks 0/1]" in approved
    # 2 last approved task, time and how it was recorded
    assert "Last approved:  T-2 at 20" in approved and "by agent-recorded - writer" in approved
    assert "Approved:       2: T-1, T-2" in approved
    # 3 files changed since the last approved task was submitted
    assert "Changed since T-2 submit (no git commit, by files): 3" in approved
    for line in ("    M src/a.py", "    A src/b.py", "    D old.txt"):
        assert line in approved
    # 4 last test result of the approved report
    assert "Last tests:     NOT RUN 1, PASS 1 (approved report, section 4)" in approved
    # 5 open risks, 6 next plan, 7 recent decisions
    assert "| cp949 console | not measured | run it |" in approved
    assert "| 항목 |" not in approved and "|---|" not in approved  # only the risk rows
    assert "승인하시면 다음으로 T-3: CLI를 진행합니다." in approved
    assert "[T-1] keep IDs case-sensitive (user: '대소문자 구분')" in approved
    # the temporary part is separate and comes after the approved one
    assert "half of the flags done" not in approved
    for text in (
        "Subtask:        T-3.1",
        "Note:           half of the flags done",
        "Last command:   pytest -q tests/test_cli.py",
        "Last tests:     3 passed, 1 failed",
        "Open error:     test_help fails: usage line differs",
        "Open error:     flaky timeout",
        "Task:           T-3",
    ):
        assert text in temporary, text
    assert out.rstrip().endswith("Status:       READY")


def test_recover_json_has_the_same_items(two_approved):
    code, out = kit(two_approved, "recover", "--json")
    assert code == EXIT_READY
    doc = json.loads(out)
    a = doc["approved"]
    assert a["current"]["id"] == "T-3" and a["current"]["state"] == "IN_PROGRESS"
    assert a["last_approved"]["id"] == "T-2" and a["last_approved"]["by"] == "agent-recorded"
    assert a["approved"] == ["T-1", "T-2"]
    assert {(f["change"], f["path"]) for f in a["changed"]["files"]} == {
        ("M", "src/a.py"),
        ("A", "src/b.py"),
        ("D", "old.txt"),
    }
    assert a["changed"]["commit"] is None and a["changed"]["method"] == "files"
    assert a["tests"] == {"PASS": 1, "NOT RUN": 1}
    assert a["can_start"] == []
    assert doc["wip"]["status"] == "UNAPPROVED" and doc["wip"]["task"] == "T-3"
    assert doc["wip"]["errors"] == ["test_help fails: usage line differs", "flaky timeout"]
    assert doc["warnings"] == [] and doc["exit_code"] == 0


def test_an_empty_workspace_recovers_to_nothing(workspace):
    code, out = kit(workspace, "recover")
    assert code == EXIT_READY, out
    assert "Current task:   none" in out and "Last approved:  none yet" in out
    assert "Temporary (not approved): none saved" in out
    assert not (workspace / ".kit").exists()  # recover alone writes nothing


def test_submitted_task_is_the_current_one_while_it_waits(workspace):
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001", approve=False)
    out = ok(workspace, "recover")
    assert "Current task:   T-1 SUBMITTED - parser" in out
    assert "Last approved:  none yet" in out


# ---------------------------------------------------------------- broken WIP


@pytest.mark.parametrize(
    "content",
    [
        b"{not json",
        b"[]",
        b'{"schema": 1, "status": "APPROVED", "errors": []}',
        b'{"schema": 1, "status": "UNAPPROVED", "errors": "x"}',
        b'{"schema": 1, "status": "UNAPPROVED", "errors": [], "note": 3}',
        b'{"schema": 2, "status": "UNAPPROVED", "errors": []}',
        b"\xff\xfe",
    ],
)
def test_a_broken_wip_falls_back_to_the_approved_state(two_approved, content):
    (two_approved / recover.WIP_REL).write_bytes(content)
    code, out = kit(two_approved, "recover")
    assert code == EXIT_PARTIAL, out
    assert "Last approved:  T-2" in out and "    M src/a.py" in out
    assert "Temporary (not approved): none saved" in out
    assert f"Warning:      {recover.WIP_REL}" in out and "showing the approved state only" in out
    assert out.rstrip().endswith("Status:       PARTIAL")


def test_save_replaces_a_broken_wip_and_overwrites_the_previous_one(two_approved):
    p = two_approved / recover.WIP_REL
    p.write_bytes(b"{broken")
    ok(two_approved, "recover", "save", "--note", "second session")
    wip = json.loads(p.read_text(encoding="utf-8"))
    assert wip["note"] == "second session" and wip["errors"] == [] and wip["subtask"] is None
    assert wip["task"] == "T-3" and wip["status"] == "UNAPPROVED"
    assert not p.with_name(p.name + ".tmp").exists()


def test_wip_of_a_task_approved_later_is_marked(workspace):
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    ok(workspace, "task", "start", "T-1")
    ok(workspace, "recover", "save", "--note", "almost")
    report(workspace, "T-1", "REQ-001")
    ok(workspace, "task", "submit", "T-1")
    ok(workspace, "task", "approve", "T-1", "--by", "agent-recorded", "--quote", "승인")
    out = ok(workspace, "recover")
    assert "Out of date?    T-1 is APPROVED now" in out


# ---------------------------------------------------------------- TC-HTL-17 HANDOFF


def test_handoff_holds_the_approved_state_only(two_approved):
    text = (two_approved / recover.HANDOFF_REL).read_text(encoding="utf-8")
    assert text.startswith("<!-- kit:handoff approvals=2 last=T-2@")
    assert "# HANDOFF (승인된 상태만 기록)" in text
    for heading in (
        "## 마지막 승인 Task",
        "## 요약",
        "## 변경 파일",
        "## 테스트 결과 요약",
        "## 결정 사항",
        "## 남은 위험·미해결 이슈",
        "## 다음 계획",
        "## 승인 이력",
    ):
        assert heading in text, heading
    assert "- ID / 제목: T-2 / writer" in text and "- 승인 기록 방식: agent-recorded" in text
    assert "- 승인 시 커밋: 없음" in text
    assert "- NOT RUN 1, PASS 1 (`.kit/work/reports/T-2.md` 4절)" in text
    assert "T-2 done" in text and "| cp949 console | not measured | run it |" in text
    assert "keep IDs case-sensitive" in text
    assert "| T-1 | parser |" in text and "| T-2 | writer |" in text
    # nothing temporary: the WIP and the in-progress task are not in it
    for wip in ("half of the flags done", "flaky timeout", "IN_PROGRESS", "parse args"):
        assert wip not in text, wip


def test_approve_writes_the_handoff_at_once(workspace):
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001", approve=False)
    assert not (workspace / recover.HANDOFF_REL).exists()  # submitted is not approved
    out = ok(workspace, "task", "approve", "T-1", "--by", "agent-recorded", "--quote", "승인")
    assert "Handoff:      .kit/work/HANDOFF.md updated (approved state only)" in out
    assert "last=T-1@" in (workspace / recover.HANDOFF_REL).read_text(encoding="utf-8")


def test_handoff_is_not_rewritten_without_a_new_approval(two_approved):
    p = two_approved / recover.HANDOFF_REL
    before = p.read_bytes()
    ok(two_approved, "recover", "decide", "a later decision")
    ok(two_approved, "recover")
    ok(two_approved, "task", "status")
    assert p.read_bytes() == before


def _hook_approve(ws: Path, task_id: str) -> None:
    spec = importlib.util.spec_from_file_location(
        "kit_approval", KIT_ROOT / approval_hooks.SOURCE_REL
    )
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    assert task_id in hook.approve(ws, "승인", task_id)


@pytest.mark.parametrize("catch_up", [("recover",), ("task", "status"), ("task", "list")])
def test_a_hook_approval_reaches_the_handoff_at_the_next_kit_command(workspace, catch_up):
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001", approve=False)
    _hook_approve(workspace, "T-1")
    assert not (workspace / recover.HANDOFF_REL).exists()
    kit(workspace, *catch_up)
    text = (workspace / recover.HANDOFF_REL).read_text(encoding="utf-8")
    assert "- 승인 기록 방식: human-hook" in text and "last=T-1@" in text


def test_a_report_changed_after_approval_is_not_copied(two_approved):
    (two_approved / recover.HANDOFF_REL).unlink()
    (two_approved / tasks.default_report("T-2")).write_bytes(b"## rewritten later\n")
    code, out = kit(two_approved, "recover")
    assert code == EXIT_PARTIAL
    assert "Warning:      T-2: report .kit/work/reports/T-2.md changed after approval" in out
    approved = out.partition("Temporary (not approved")[0]
    assert "Last tests:" not in approved and "cp949 console" not in out
    text = (two_approved / recover.HANDOFF_REL).read_text(encoding="utf-8")
    assert "rewritten later" not in text and "보고서가 승인 뒤 바뀌었거나 없어" in text


# ---------------------------------------------------------------- TC-HTL-18 / REQ-SESS-003


def tree(ws: Path) -> dict:
    return {
        p.relative_to(ws).as_posix(): p.read_bytes()
        for p in ws.rglob("*")
        if p.is_file() and ".kit" not in p.relative_to(ws).parts
    }


def test_a_root_handoff_is_never_read_or_changed(workspace):
    mine = "# 내 HANDOFF\n\nkit:handoff 흉내도 아님\n".encode()
    (workspace / "HANDOFF.md").write_bytes(mine)
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    before = tree(workspace)
    run_task(workspace, "T-1", "REQ-001")
    ok(workspace, "recover", "save", "--note", "n")
    ok(workspace, "recover", "decide", "d")
    out = ok(workspace, "recover")
    after = tree(workspace)
    assert after == before  # nothing outside .kit/ was written
    assert (workspace / "HANDOFF.md").read_bytes() == mine
    assert "Note:         HANDOFF.md at the workspace root is not the kit's" in out
    assert "내 HANDOFF" not in out
    assert (workspace / recover.HANDOFF_REL).is_file()


def test_a_kit_work_handoff_without_the_marker_is_left_alone(workspace):
    p = workspace / recover.HANDOFF_REL
    p.parent.mkdir(parents=True)
    p.write_bytes("# written by hand\n".encode())
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001")
    assert p.read_bytes() == b"# written by hand\n"
    code, out = kit(workspace, "recover")
    assert code == EXIT_PARTIAL
    assert "Handoff:        .kit/work/HANDOFF.md (not-ours)" in out
    assert "was not written by the kit; left as is" in out


def test_state_files_are_all_under_kit_work(two_approved):
    made = sorted(
        p.relative_to(two_approved).as_posix()
        for p in (two_approved / ".kit").rglob("*")
        if p.is_file()
    )
    assert made == [
        ".kit/work/HANDOFF.md",
        ".kit/work/decisions.md",
        ".kit/work/reports/T-1.md",
        ".kit/work/reports/T-2.md",
        ".kit/work/snapshots/T-1.json",
        ".kit/work/snapshots/T-2.json",
        ".kit/work/tasks.json",
        ".kit/work/wip.json",
    ]


# ---------------------------------------------------------------- snapshots and git


def test_snapshot_is_taken_at_submit_and_replaced_on_resubmit(workspace):
    (workspace / "a.txt").write_bytes(b"1")
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001", approve=False)
    snap = recover.load_snapshot(workspace, "T-1")
    assert snap["files"]["a.txt"] == recover.sha256(b"1") and snap["method"] == "files"
    assert not any(k.startswith(".kit") for k in snap["files"])
    ok(workspace, "task", "request-changes", "T-1", "--reason", "more tests")
    (workspace / "a.txt").write_bytes(b"2")
    ok(workspace, "task", "start", "T-1")
    ok(workspace, "task", "submit", "T-1")
    assert recover.load_snapshot(workspace, "T-1")["files"]["a.txt"] == recover.sha256(b"2")


def test_skipped_folders_are_not_in_the_snapshot(workspace):
    for d in ("node_modules/x", ".venv/lib", "pkg/__pycache__", ".git"):
        (workspace / d).mkdir(parents=True)
        (workspace / d / "f").write_bytes(b"x")
    (workspace / "pkg/m.py").write_bytes(b"x")
    files, method, cut = recover.hashes(workspace, "files")
    assert method == "files" and not cut and list(files) == ["pkg/m.py"]


def test_no_snapshot_means_changed_files_are_unknown(two_approved):
    (two_approved / ".kit/work/snapshots/T-2.json").unlink()
    code, out = kit(two_approved, "recover")
    assert code == EXIT_PARTIAL
    assert "Warning:      no snapshot for T-2; changed files are unknown" in out
    assert "Changed since" not in out


def test_too_many_files_makes_the_list_partial(two_approved, monkeypatch):
    monkeypatch.setattr(recover, "MAX_FILES", 1)
    code, out = kit(two_approved, "recover")
    assert code == EXIT_PARTIAL
    assert "more than 1 files; the changed-file list is partial" in out


def test_big_files_are_compared_by_size(workspace, monkeypatch):
    monkeypatch.setattr(recover, "BIG_FILE", 3)
    (workspace / "big.bin").write_bytes(b"12345")
    (workspace / "small.txt").write_bytes(b"12")
    (workspace / "edge.txt").write_bytes(b"123")  # exactly the limit is still hashed
    files, _, _ = recover.hashes(workspace, "files")
    assert files == {
        "big.bin": "size:5",
        "edge.txt": recover.sha256(b"123"),
        "small.txt": recover.sha256(b"12"),
    }


def test_long_change_lists_are_cut_in_the_text_output(two_approved):
    for i in range(35):
        (two_approved / f"n{i:02}.txt").write_bytes(b"x")
    out = kit(two_approved, "recover")[1]
    assert "Changed since T-2 submit (no git commit, by files): 38" in out
    assert "    ... and 8 more (--json lists all)" in out
    doc = json.loads(kit(two_approved, "recover", "--json")[1])
    assert len(doc["approved"]["changed"]["files"]) == 38


GIT = shutil.which("git")


def git(ws: Path, *args: str) -> str:
    cfg = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    r = subprocess.run([GIT, "-C", str(ws), *cfg, *args], capture_output=True, check=True)
    return r.stdout.decode().strip()


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_with_git_the_commit_is_recorded_and_ignored_files_are_left_out(workspace):
    git(workspace, "init", "-q")
    (workspace / ".gitignore").write_bytes(b"build/\n.kit/\n")
    (workspace / "src.py").write_bytes(b"x = 1\n")
    git(workspace, "add", "-A")
    git(workspace, "commit", "-q", "-m", "init")
    head = git(workspace, "rev-parse", "HEAD")
    (workspace / "src.py").write_bytes(b"x = 2\n")  # uncommitted, part of the submitted work
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001")
    snap = recover.load_snapshot(workspace, "T-1")
    assert snap["commit"] == head and snap["method"] == "git"
    (workspace / "build").mkdir()
    (workspace / "build/out.bin").write_bytes(b"ignored")
    (workspace / "new.py").write_bytes(b"untracked but not ignored")
    doc = json.loads(kit(workspace, "recover", "--json")[1])
    files = doc["approved"]["changed"]["files"]
    # src.py changed before submit, so it is not reported; build/ is ignored
    assert files == [{"change": "A", "path": "new.py"}]
    assert f"- 승인 시 커밋: {head}" in (workspace / recover.HANDOFF_REL).read_text("utf-8")
    assert f"commit {head[:12]}, by git" in kit(workspace, "recover")[1]


def test_without_git_on_path_the_files_are_walked(workspace, monkeypatch):
    monkeypatch.setattr(recover.shutil, "which", lambda name: None)
    (workspace / "a.txt").write_bytes(b"1")
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001")
    snap = recover.load_snapshot(workspace, "T-1")
    assert snap["commit"] is None and snap["method"] == "files" and "a.txt" in snap["files"]


# ---------------------------------------------------------------- save / decide


def test_decisions_are_appended_and_masked(workspace):
    ok(workspace, "recover", "decide", "first")
    p = workspace / recover.DECISIONS_REL
    before = p.read_bytes()
    ok(workspace, "recover", "decide", "use api_key=sk-abcdef1234567890abcdef in\nthe test")
    text = p.read_text(encoding="utf-8")
    assert text.encode("utf-8").startswith(before)
    assert text.startswith("# Decisions (append only") and text.count("# Decisions") == 1
    last = text.splitlines()[-1]
    assert last.endswith("[-] use api_key=*** in the test")
    assert "sk-abcdef" not in text


def test_save_masks_secrets_and_caps_long_fields(workspace):
    ok(
        workspace,
        "recover",
        "save",
        "--command",
        "curl -H 'Authorization: Bearer abc.def.ghi'",
        "--note",
        "x" * 5000,
    )
    wip = json.loads((workspace / recover.WIP_REL).read_text(encoding="utf-8"))
    assert "abc.def.ghi" not in json.dumps(wip) and "Bearer ***" in wip["last_command"]
    assert len(wip["note"]) == recover.FIELD_MAX and wip["task"] is None


def test_save_keeps_at_most_twenty_errors(workspace):
    argv = ["recover", "save"]
    for i in range(25):
        argv += ["--error", f"e{i}"]
    ok(workspace, *argv)
    wip = json.loads((workspace / recover.WIP_REL).read_text(encoding="utf-8"))
    assert wip["errors"] == [f"e{i}" for i in range(20)]


@pytest.mark.parametrize(
    "argv",
    [
        ["recover", "save"],
        ["recover", "save", "text", "--note", "n"],
        ["recover", "decide"],
        ["recover", "decide", "  "],
        ["recover", "decide", "d", "--note", "n"],
        ["recover", "--note", "n"],
        ["recover", "--task", "T-1"],
        ["recover", "list"],
    ],
)
def test_bad_recover_arguments_are_usage_errors(workspace, argv):
    assert kit(workspace, *argv)[0] == EXIT_USAGE
    assert not (workspace / ".kit").exists()


def test_decide_with_save_options_names_the_option(workspace, capsys):
    assert kit(workspace, "recover", "decide", "d", "--command", "c")[0] == EXIT_USAGE
    assert "--command is for recover save" in capsys.readouterr().err


def test_an_unknown_task_is_refused(workspace):
    for argv in (["save", "--note", "n"], ["decide", "d"]):
        code, out = kit(workspace, "recover", *argv, "--task", "T-9")
        assert code == EXIT_BLOCKED and "Refused:      no task 'T-9'" in out
    assert not (workspace / ".kit").exists()


def test_a_broken_tasks_file_is_a_target_problem(workspace):
    p = workspace / tasks.TASKS_REL
    p.parent.mkdir(parents=True)
    p.write_bytes(b"{")
    assert kit(workspace, "recover")[0] == EXIT_TARGET


def test_help_lists_recover_and_it_is_no_longer_later():
    assert "recover" in commands.IMPLEMENTED and "recover" not in commands.LATER
    assert "  recover   [save" in commands.HELP


# ---------------------------------------------------------------- skill


def test_session_recovery_skill_is_installed_in_standard_core_only(workspace, tmp_path):
    ok(workspace, "install", "--agent", "both", "--offline")
    for agent_dir in (".agents/skills", ".claude/skills"):
        text = (workspace / agent_dir / "session-recovery/SKILL.md").read_text(encoding="utf-8")
        assert "kit recover" in text and "임시(미승인)" in text
        assert "Show the user both parts before doing anything else" in text
    res = tmp_path / "restricted"
    res.mkdir()
    ok(res, "install", "--agent", "codex", "--policy", "restricted", "--offline")
    assert not (res / ".agents/skills/session-recovery").exists()
    policy = (workspace / "AGENTS.md").read_text(encoding="utf-8")
    assert "session-recovery" in policy


# ---------------------------------------------------------------- counterexample review


@pytest.mark.parametrize("note", ["password: abc", 'token="x", "y"', "api_key=sk-zz9"])
def test_json_stays_valid_when_a_value_looks_like_a_secret(workspace, note):
    code, out = kit(workspace, "recover", "save", "--note", note, "--json")
    assert code == EXIT_READY and "***" in json.loads(out)["wip"]["note"]
    doc = json.loads(kit(workspace, "recover", "--json")[1])
    shown = doc["wip"]["note"]
    assert "***" in shown and not any(v in shown for v in ("abc", '"x"', "zz9"))


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_a_workspace_inside_a_bigger_git_repo_sees_only_its_own_files(tmp_path):
    repo = tmp_path / "repo"
    ws = repo / "sub dir/작업"
    ws.mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "outside.txt").write_bytes(b"1")
    (ws / "inside.txt").write_bytes(b"1")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    ok(ws, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(ws, "T-1", "REQ-001")
    snap = recover.load_snapshot(ws, "T-1")
    assert snap["method"] == "git" and list(snap["files"]) == ["inside.txt"]
    (repo / "outside.txt").write_bytes(b"2")
    (ws / "inside.txt").write_bytes(b"2")
    doc = json.loads(kit(ws, "recover", "--json")[1])
    assert doc["approved"]["changed"]["files"] == [{"change": "M", "path": "inside.txt"}]


def test_in_progress_is_current_before_a_submitted_task(workspace):
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    ok(workspace, "task", "add", "T-2", "--title", "docs", "--requires", "REQ-002")
    run_task(workspace, "T-1", "REQ-001", approve=False)
    ok(workspace, "task", "start", "T-2")
    assert "Current task:   T-2 IN_PROGRESS - docs" in ok(workspace, "recover")


def test_only_the_latest_five_decisions_are_shown(workspace):
    for i in range(7):
        ok(workspace, "recover", "decide", f"decision {i}")
    doc = json.loads(kit(workspace, "recover", "--json")[1])
    assert [d.split("] ")[1] for d in doc["approved"]["decisions"]] == [
        f"decision {i}" for i in range(2, 7)
    ]


def test_a_handoff_path_that_is_a_folder_is_left_alone(workspace):
    (workspace / recover.HANDOFF_REL).mkdir(parents=True)
    ok(workspace, "task", "add", "T-1", "--title", "parser", "--requires", "REQ-001")
    run_task(workspace, "T-1", "REQ-001")
    code, out = kit(workspace, "recover")
    assert code == EXIT_PARTIAL and "(not-ours)" in out
    assert (workspace / recover.HANDOFF_REL).is_dir()


def test_json_masks_values_the_kit_did_not_mask_on_the_way_in(workspace):
    ok(
        workspace,
        "task",
        "add",
        "T-1",
        "--title",
        "rotate token=abc123def",
        "--requires",
        "REQ-001",
    )
    ok(workspace, "task", "start", "T-1")
    out = kit(workspace, "recover", "--json")[1]
    assert "abc123def" not in out and json.loads(out)["approved"]["current"]["title"] == (
        "rotate token=***"
    )
