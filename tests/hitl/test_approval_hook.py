"""P5-T2b approval hook (ADR-011 L2, 00_PROMPT D-11, REQ-HITL-006, TC-HTL-06 hook part).

The script is run the way the agents run it: a child process with the hook event as JSON on
stdin. Real agent runs are the manual check M-05.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from kit import approval_hooks, commands, tasks
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY, EXIT_USAGE
from tests.conftest import KIT_ROOT

ROW = "| TC-1 | REQ-001 | x | x | x | x | PASS |\n"
SEP = "|---|---|---|---|---|---|---|\n"
MANIFEST = ".kit/state/install-manifest.json"


def _module():
    spec = importlib.util.spec_from_file_location(
        "kit_approval", KIT_ROOT / approval_hooks.SOURCE_REL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _module()


def kit(ws: Path, *argv, ask=None):
    out = io.StringIO()
    code = commands.run(list(argv), ws, KIT_ROOT, out, ask)
    return code, out.getvalue()


def task(ws: Path, *argv, ask=None):
    return kit(ws, "task", *argv, "--target", str(ws), ask=ask)


def run_hook(ws: Path, agent: str, event: dict, raw: bytes = None):
    script = ws / approval_hooks.SCRIPT_REL[agent]
    done = subprocess.run(
        [sys.executable, str(script)],
        input=raw if raw is not None else json.dumps(event, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=str(ws.parent),  # the script finds the workspace from its own path
        timeout=60,
    )
    return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")


def prompt(ws: Path, text: str, agent: str = "claude"):
    code, out, err = run_hook(ws, agent, {"hook_event_name": "UserPromptSubmit", "prompt": text})
    assert code == 0, err
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def tool(ws: Path, name: str, tool_input: dict, agent: str = "claude"):
    event = {"hook_event_name": "PreToolUse", "tool_name": name, "tool_input": tool_input}
    return run_hook(ws, agent, event)


def data(ws: Path) -> dict:
    return json.loads((ws / tasks.TASKS_REL).read_text(encoding="utf-8"))


def submit(ws: Path, task_id: str = "T-001") -> Path:
    assert task(ws, "add", task_id, "--title", "A", "--requires", "REQ-001")[0] == 0
    assert task(ws, "start", task_id)[0] == 0
    assert task(ws, "report", task_id)[0] == 0
    path = ws / tasks.default_report(task_id)
    path.write_text(path.read_text(encoding="utf-8").replace(SEP, SEP + ROW, 1), "utf-8")
    code, out = task(ws, "submit", task_id)
    assert code == EXIT_READY, out
    return path


@pytest.fixture
def hooked(workspace, isolated_home):
    code, out = kit(workspace, "install", "--agent", "both", "--offline", "--hooks")
    assert code == EXIT_READY, out
    return workspace


# ---------------------------------------------------------------- what counts as approval


@pytest.mark.parametrize(
    "text, task_id",
    [
        ("승인", None),
        ("  승인합니다. ", None),
        ("승인할게요!", None),
        ("approve", None),
        ("Approved", None),
        ("승인 T-001", "T-001"),
        ("T-001 승인", "T-001"),
        ("approve T-002.", "T-002"),
    ],
)
def test_an_approval_word_alone_counts(text, task_id):
    assert hook.match_approval(text) == (True, task_id, False)


@pytest.mark.parametrize(
    "text, mixed",
    [
        ("승인 근데 저장소 용량은?", True),
        ("승인된 거 맞아?", True),
        ("approve if the tests pass", True),
        ("T-001 승인 T-002", True),
        ("approval", False),
        ("좋아요", False),
        ("다음 Task 진행해", False),
        ("미승인", False),
        ("", False),
    ],
)
def test_anything_else_is_not_an_approval(text, mixed):
    assert hook.match_approval(text) == (False, None, mixed)


# ---------------------------------------------------------------- UserPromptSubmit


def test_the_users_word_is_recorded_as_human_hook(hooked):
    report = submit(hooked)
    context = prompt(hooked, "승인")
    assert "the user approved T-001; recorded by human-hook" in context
    (rec,) = data(hooked)["approvals"]
    assert rec["by"] == "human-hook" and rec["agent"] == "claude" and rec["evidence"] == "승인"
    assert rec["report_sha256"] == tasks.sha256(report.read_bytes())
    tasks.validate(data(hooked))  # the hook writes what kit task reads
    code, out = task(hooked, "status")
    assert code == EXIT_READY
    assert re.search(r"T-001\s+APPROVED\s+by human-hook\s", out)
    assert "Can start" in out


def test_a_codex_approval_is_marked_as_a_guardrail(hooked):
    submit(hooked)
    assert "recorded by human-hook" in prompt(hooked, "approve", agent="codex")
    assert data(hooked)["approvals"][0]["agent"] == "codex"
    code, out = task(hooked, "status")
    assert "by human-hook (codex hook: guardrail only)" in out


def test_mixed_words_are_not_recorded_and_the_agent_is_told(hooked):
    submit(hooked)
    context = prompt(hooked, "승인 근데 저장소 용량은 크게 문제가 없는데?")
    assert "nothing was recorded" in context and "'승인'" in context
    assert data(hooked)["approvals"] == []
    assert prompt(hooked, "테스트 다시 돌려줘") == ""


def test_several_submitted_tasks_need_the_id(hooked):
    submit(hooked, "T-001")
    submit(hooked, "T-002")
    assert "several tasks are SUBMITTED (T-001, T-002)" in prompt(hooked, "승인")
    assert data(hooked)["approvals"] == []
    assert "approved T-002" in prompt(hooked, "승인 T-002")
    states = {t["id"]: t["state"] for t in data(hooked)["tasks"]}
    assert states == {"T-001": "SUBMITTED", "T-002": "APPROVED"}


@pytest.mark.parametrize(
    "setup, text, message",
    [
        (None, "승인", "no task is SUBMITTED"),
        ("submit", "승인 T-404", "no task 'T-404'"),
        ("add", "승인 T-001", "T-001 is TODO, not SUBMITTED"),
        ("edit", "승인", "changed after submit; submit T-001 again"),
        ("delete", "승인", "the report of T-001 is missing"),
        ("broken", "승인", "could not be read"),
    ],
)
def test_nothing_is_recorded_when_the_rules_say_no(hooked, setup, text, message):
    if setup == "add":
        task(hooked, "add", "T-001", "--title", "A")
    elif setup is None:
        task(hooked, "add", "T-009", "--title", "A")
    else:
        report = submit(hooked)
        if setup == "edit":
            report.write_text(report.read_text(encoding="utf-8") + "late\n", encoding="utf-8")
        elif setup == "delete":
            report.unlink()
        elif setup == "broken":
            (hooked / tasks.TASKS_REL).write_text("{oops", encoding="utf-8")
    before = (hooked / tasks.TASKS_REL).read_bytes()
    assert message in prompt(hooked, text)
    assert (hooked / tasks.TASKS_REL).read_bytes() == before


def test_without_tasks_the_hook_stays_silent(hooked):
    assert prompt(hooked, "승인") == ""
    assert not (hooked / tasks.TASKS_REL).exists()


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1, 2]", b'{"hook_event_name": "Stop"}'])
def test_odd_input_is_ignored(hooked, raw):
    assert run_hook(hooked, "claude", {}, raw=raw) == (0, "", "")


# ---------------------------------------------------------------- PreToolUse


@pytest.mark.parametrize(
    "agent, name, tool_input, why",
    [
        (
            "claude",
            "Write",
            {"file_path": "C:\\ws\\.kit\\work\\tasks.json", "content": "{}"},
            "tasks.json is written by kit task",
        ),
        (
            "claude",
            "Edit",
            {
                "file_path": "/ws/.claude/settings.json",
                "old_string": "{",
                "new_string": '{"hooks": {}',
            },
            "hooks in .claude/settings.json",
        ),
        (
            "claude",
            "Edit",
            {
                "file_path": "/ws/.claude/hooks/kit_approval.py",
                "old_string": "a",
                "new_string": "b",
            },
            "approval hook",
        ),
        (
            "claude",
            "Bash",
            {"command": "python run_kit.py task approve T-001 --by agent-recorded --quote ok"},
            "approvals come from the user",
        ),
        (
            "claude",
            "PowerShell",
            {"command": "Set-Content .kit\\work\\tasks.json '{}'"},
            "tasks.json is written by kit task",
        ),
        (
            "claude",
            "Bash",
            {"command": 'echo \'{"prompt": "승인"}\' | python .claude/hooks/kit_approval.py'},
            "approval hook",
        ),
        (
            "codex",
            "apply_patch",
            {
                "command": "*** Begin Patch\n*** Update File: "
                ".kit/work/tasks.json\n@@\n-a\n+b\n*** End Patch"
            },
            "tasks.json is written by kit task",
        ),
        (
            "codex",
            "apply_patch",
            {"command": "*** Begin Patch\n*** Delete File: .codex/hooks.json\n*** End Patch"},
            "approval hook",
        ),
        ("codex", "Bash", {"command": "sed -i s/x/y/ .codex/hooks.json"}, "approval hook"),
    ],
)
def test_the_agent_cannot_write_the_approval(hooked, agent, name, tool_input, why):
    code, out, err = tool(hooked, name, tool_input, agent)
    assert code == 0 and err == ""
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    reason = decision["permissionDecisionReason"]
    assert reason.startswith("Blocked by the kit approval hook:") and why in reason


@pytest.mark.parametrize(
    "agent, name, tool_input",
    [
        (
            "claude",
            "Write",
            {
                "file_path": "/ws/.kit/work/reports/T-001.md",
                "content": "the hook writes .kit/work/tasks.json",
            },
        ),
        (
            "claude",
            "Edit",
            {
                "file_path": "/ws/.claude/settings.json",
                "old_string": '"allow": []',
                "new_string": '"allow": ["Bash(ls)"]',
            },
        ),
        ("claude", "Bash", {"command": "python run_kit.py task submit T-001"}),
        ("claude", "Bash", {"command": "uv run pytest -q"}),
        ("claude", "Write", {"file_path": "/ws/.vscode/tasks.json", "content": "{}"}),
        (
            "codex",
            "apply_patch",
            {
                "command": "*** Begin Patch\n*** Add File: src/app.py\n"
                "+# see .kit/work/tasks.json\n*** End Patch"
            },
        ),
        ("codex", "Bash", {"command": "python run_kit.py task status"}),
    ],
)
def test_ordinary_work_goes_through(hooked, agent, name, tool_input):
    assert tool(hooked, name, tool_input, agent) == (0, "", "")


# ---------------------------------------------------------------- L1 with the hook on


def test_agent_recorded_is_refused_while_the_hook_is_on(hooked):
    submit(hooked)
    code, out = task(hooked, "approve", "T-001", "--by", "agent-recorded", "--quote", "승인")
    assert code == EXIT_BLOCKED and "the approval hook is on here (claude, codex)" in out
    assert data(hooked)["approvals"] == []
    code, out = task(hooked, "approve", "T-001", ask=lambda q: "T-001")
    assert code == EXIT_READY and "by human-cli" in out


# ---------------------------------------------------------------- install / verify / uninstall


def test_install_writes_the_scripts_and_owned_keys(hooked):
    for agent in ("claude", "codex"):
        script = hooked / approval_hooks.SCRIPT_REL[agent]
        assert script.read_bytes() == (KIT_ROOT / approval_hooks.SOURCE_REL).read_bytes()
        doc = json.loads((hooked / approval_hooks.CONFIG_REL[agent]).read_text("utf-8"))
        assert doc["hooks"] == {
            "UserPromptSubmit": approval_hooks.keys(agent)["/hooks/UserPromptSubmit"],
            "PreToolUse": approval_hooks.keys(agent)["/hooks/PreToolUse"],
        }
    claude = approval_hooks.keys("claude")["/hooks/PreToolUse"][0]
    assert claude["matcher"] == "Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit"
    assert "${CLAUDE_PROJECT_DIR}/.claude/hooks/kit_approval.py" in claude["hooks"][0]["command"]
    codex = approval_hooks.keys("codex")["/hooks/PreToolUse"][0]["hooks"][0]
    assert codex["commandWindows"] == "python .codex/hooks/kit_approval.py"
    man = json.loads((hooked / MANIFEST).read_text("utf-8"))
    for entry in man["installs"]:
        assert entry["opt_in"]["hooks"] is True
        assert any(f["path"] == approval_hooks.SCRIPT_REL[entry["agent"]] for f in entry["files"])


def test_verify_and_update_keep_the_hook(hooked):
    code, out = kit(hooked, "verify", "--agent", "both", "--offline", "--verbose")
    assert code == EXIT_READY, out
    assert "approval-hook" in out and "hook-config" in out
    (hooked / approval_hooks.SCRIPT_REL["codex"]).write_text("# edited\n", encoding="utf-8")
    code, out = kit(hooked, "verify", "--agent", "codex", "--offline", "--verbose")
    assert code != EXIT_READY
    assert "approval-hook: .codex/hooks/kit_approval.py: differs from the kit copy" in out


def test_uninstall_removes_the_hook_and_keeps_user_settings(hooked):
    settings = hooked / ".claude/settings.json"
    doc = json.loads(settings.read_text("utf-8"))
    doc["permissions"] = {"allow": ["Bash(ls)"]}
    settings.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    code, out = kit(hooked, "uninstall", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert approval_hooks.installed(hooked) == []
    left = json.loads(settings.read_text("utf-8"))
    assert left["permissions"] == {"allow": ["Bash(ls)"]}
    assert left.get("hooks", {}) == {}  # kit keys gone; an emptied parent object may stay
    assert not (hooked / ".codex/hooks.json").exists()  # only kit keys there: file removed


def test_a_project_with_its_own_hooks_gets_a_conflict(workspace, isolated_home):
    own = {
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "lint"}]}]
        }
    }
    (workspace / ".claude").mkdir()
    (workspace / ".claude/settings.json").write_text(json.dumps(own), encoding="utf-8")
    code, out = kit(workspace, "install", "--agent", "claude", "--offline", "--hooks", "--verbose")
    assert code == EXIT_PARTIAL, out
    assert "hook-config  (.claude/settings.json: /hooks/PreToolUse is not owned by the kit)" in out
    assert json.loads((workspace / ".claude/settings.json").read_text("utf-8")) == own
    assert not (workspace / ".claude/hooks").exists()  # no script without its registration
    assert approval_hooks.installed(workspace) == []
    assert "CONFLICT   optional [claude] approval-hook" in out


def test_hooks_are_project_scope_only(workspace, isolated_home, capsys):
    code, _ = kit(workspace, "install", "--agent", "claude", "--scope", "user", "--hooks")
    assert code == EXIT_USAGE
    assert "--hooks is for --scope project" in capsys.readouterr().err


def test_without_hooks_nothing_changes(workspace, isolated_home):
    code, out = kit(workspace, "install", "--agent", "both", "--offline")
    assert code == EXIT_READY, out
    assert approval_hooks.installed(workspace) == []
    assert not (workspace / ".claude/settings.json").exists()
    assert not (workspace / ".codex/hooks.json").exists()
    man = json.loads((workspace / MANIFEST).read_text("utf-8"))
    assert all("hooks" not in e["opt_in"] for e in man["installs"])


def test_plugin_and_hook_keys_share_settings_json(workspace, isolated_home):
    kit(
        workspace,
        "install",
        "--agent",
        "claude",
        "--offline",
        "--hooks",
        "--plugin",
        "security-guidance",
    )
    doc = json.loads((workspace / ".claude/settings.json").read_text("utf-8"))
    assert set(doc) >= {"hooks", "enabledPlugins", "extraKnownMarketplaces"}
    assert set(doc["hooks"]) == {"UserPromptSubmit", "PreToolUse"}


# ---------------------------------------------------------------- gaps found by mutation


def test_a_tasks_file_of_another_schema_is_not_touched(hooked):
    submit(hooked)
    doc = data(hooked)
    doc["schema"] = 2
    (hooked / tasks.TASKS_REL).write_text(json.dumps(doc), encoding="utf-8")
    before = (hooked / tasks.TASKS_REL).read_bytes()
    assert "could not be read" in prompt(hooked, "승인")
    assert (hooked / tasks.TASKS_REL).read_bytes() == before


def test_a_report_outside_the_workspace_is_not_trusted(hooked):
    report = submit(hooked)
    outside = hooked.parent / "outside.md"
    outside.write_bytes(report.read_bytes())
    doc = data(hooked)
    doc["tasks"][0]["report"] = "../outside.md"
    (hooked / tasks.TASKS_REL).write_text(json.dumps(doc), encoding="utf-8")
    assert "the report of T-001 is missing" in prompt(hooked, "승인")
    assert data(hooked)["approvals"] == []


def test_other_tasks_files_are_not_protected(hooked):
    assert tool(hooked, "Bash", {"command": "cat .vscode/tasks.json"}) == (0, "", "")


def test_installed_needs_the_script_and_its_registration(hooked):
    assert approval_hooks.installed(hooked) == ["claude", "codex"]
    (hooked / ".codex/hooks.json").write_text("{}", encoding="utf-8")
    (hooked / ".claude/hooks/kit_approval.py").unlink()
    assert approval_hooks.installed(hooked) == []


def test_verify_reports_an_outdated_script(hooked):
    script = hooked / approval_hooks.SCRIPT_REL["claude"]
    script.write_text("# old\n", encoding="utf-8")
    item = approval_hooks.verify(hooked, KIT_ROOT, "claude", [])[0]
    assert item.verified == "FAIL" and "is outdated" in item.detail
    script.unlink()
    item = approval_hooks.verify(hooked, KIT_ROOT, "claude", [])[0]
    assert item.verified == "FAIL" and "missing" in item.detail


def test_codex_with_its_own_hooks_gets_a_conflict_and_no_script(workspace, isolated_home):
    own = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "x"}]}]}}
    (workspace / ".codex").mkdir()
    (workspace / ".codex/hooks.json").write_text(json.dumps(own), encoding="utf-8")
    code, out = kit(workspace, "install", "--agent", "codex", "--offline", "--hooks")
    assert code == EXIT_PARTIAL, out
    assert not (workspace / ".codex/hooks").exists()
    assert json.loads((workspace / ".codex/hooks.json").read_text("utf-8")) == own


def test_the_same_prompt_twice_is_one_approval(hooked):
    """M-05 finding: Codex 0.166 ran UserPromptSubmit twice for one prompt."""
    submit(hooked)
    first = prompt(hooked, "승인 T-001", agent="codex")
    second = prompt(hooked, "승인 T-001", agent="codex")
    assert first == second and "the user approved T-001" in second
    assert len(data(hooked)["approvals"]) == 1
    doc = data(hooked)
    doc["approvals"][0]["at"] = "2020-01-01T00:00:00+00:00"  # long ago: not a repeat
    (hooked / tasks.TASKS_REL).write_text(json.dumps(doc), encoding="utf-8")
    assert "T-001 is APPROVED, not SUBMITTED" in prompt(hooked, "승인 T-001")
    assert "no task is SUBMITTED" in prompt(hooked, "승인")


def test_a_different_prompt_is_not_a_repeat(hooked):
    submit(hooked, "T-001")
    submit(hooked, "T-002")
    assert "approved T-001" in prompt(hooked, "승인 T-001")
    assert "approved T-002" in prompt(hooked, "승인 T-002")
    assert "T-001 is APPROVED, not SUBMITTED" in prompt(hooked, "approve T-001")
    assert len(data(hooked)["approvals"]) == 2


@pytest.mark.parametrize(
    "change, text",
    [
        (None, "approve T-001"),  # another prompt for the same task
        ({"by": "human-cli"}, "승인 T-001"),  # the last approval did not come from the hook
        ({"task": "T-009"}, "승인 T-001"),  # the same words named another task
    ],
)
def test_only_the_same_hook_prompt_is_a_repeat(hooked, change, text):
    submit(hooked)
    assert "approved T-001" in prompt(hooked, "승인 T-001")
    if change:
        doc = data(hooked)
        doc["approvals"][-1].update(change)
        (hooked / tasks.TASKS_REL).write_text(json.dumps(doc), encoding="utf-8")
    assert "T-001 is APPROVED, not SUBMITTED" in prompt(hooked, text)


def test_a_longer_word_is_not_an_approval_start():
    assert hook.match_approval("approvers list") == (False, None, False)
