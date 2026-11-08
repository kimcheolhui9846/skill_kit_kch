#!/usr/bin/env python3
"""Kit approval hook (P5-T2b, ADR-011 level L2). Installed by `kit install --hooks`.

One script for Claude Code and Codex; standard library only; it reads the hook event as
JSON on stdin.

UserPromptSubmit: when the whole prompt is an approval word ("승인", "approve", ...) with
at most a task id ("승인 T-001", "T-001 승인"), the SUBMITTED task is approved and recorded
as `by: human-hook` in .kit/work/tasks.json. Without an id there must be exactly one
SUBMITTED task. An approval word mixed with other text is not recorded; the agent is told
to ask. The prompt itself always goes through.

PreToolUse: denies (JSON permissionDecision "deny", exit 0) a tool call that would write
the approval record, run `task approve`, or change the hook and its registration. The
agent then has to leave the approval to the user.

This is a guardrail, not a security boundary (Codex: "not a complete enforcement
boundary"). A command that names none of the protected paths, or a hook that fails to
start, lets the tool run. `kit task status` shows `by` for every approval, so a bypass
stays visible afterwards.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TASKS_REL = ".kit/work/tasks.json"
EVIDENCE_MAX = 2000
REPEAT_SECONDS = 600  # the same prompt seen again within this window is a repeat
HOOK_DIR = Path(__file__).resolve().parent  # <root>/.claude/hooks or <root>/.codex/hooks
ROOT = HOOK_DIR.parents[1]
AGENT = HOOK_DIR.parent.name.lstrip(".")  # "claude" or "codex"

WORDS = (
    "승인합니다",
    "승인할게요",
    "승인해요",
    "승인함",
    "승인",
    "approved",
    "approve",
)
_WORD = "(?:" + "|".join(re.escape(w) for w in WORDS) + ")"
_ID = r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}"
_APPROVAL = re.compile(
    rf"^\s*(?:(?P<before>{_ID})\s+)?{_WORD}(?:\s+(?P<after>{_ID}))?\s*[.!]*\s*$",
    re.IGNORECASE,
)
_STARTS = re.compile(rf"^\s*(?:{_ID}\s+)?{_WORD}(?![A-Za-z])", re.IGNORECASE)

# PreToolUse: what the agent may not touch while the hook is on
_TASK_APPROVE = re.compile(r"\btask\s+approve\b", re.IGNORECASE)
_PROTECTED = ("kit_approval", ".codex/hooks.json")
_PATCH_PATH = re.compile(r"^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+?)\s*$", re.M)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _out(text: str) -> None:
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def _context(message: str) -> None:
    """Text the agent sees next to the prompt (both agents accept this shape)."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "kit approval hook: " + message,
        }
    }
    _out(json.dumps(payload, ensure_ascii=False))


# ---------------------------------------------------------------- UserPromptSubmit


def match_approval(prompt: str):
    """(is_approval, task id or None, mixed). mixed: starts like an approval, says more."""
    found = _APPROVAL.match(prompt)
    if found:
        if found.group("before") and found.group("after"):
            return False, None, True
        task_id = (found.group("before") or found.group("after") or "").rstrip(".")
        return True, task_id or None, False
    return False, None, bool(_STARTS.match(prompt))


def _load(path: Path):
    data = json.loads(path.read_bytes().decode("utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("schema") != 1
        or not isinstance(data.get("tasks"), list)
        or not isinstance(data.get("approvals"), list)
    ):
        raise ValueError("unexpected shape")
    return data


def _save(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def _done(task_id: str) -> str:
    return (
        f"the user approved {task_id}; recorded by human-hook. "
        "Do not run kit task approve yourself; continue with the next task."
    )


def _repeat(data: dict, prompt: str, task_id):
    """The task this same prompt approved moments ago, or None.

    Codex 0.166 ran UserPromptSubmit twice for one prompt (M-05, 2026-11-07); the second run
    must say the same thing as the first, not "not SUBMITTED".
    """
    if not data["approvals"]:
        return None
    last = data["approvals"][-1]
    if not isinstance(last, dict) or last.get("by") != "human-hook":
        return None
    if last.get("evidence") != prompt.strip()[:EVIDENCE_MAX]:
        return None
    if task_id is not None and last.get("task") != task_id:
        return None
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(last["at"])
    except (KeyError, TypeError, ValueError):
        return None
    return last.get("task") if 0 <= age.total_seconds() <= REPEAT_SECONDS else None


def approve(root: Path, prompt: str, task_id) -> str:
    """Record the approval; returns the message for the agent."""
    path = root / TASKS_REL
    try:
        data = _load(path)
    except (OSError, ValueError, UnicodeDecodeError):
        return f"{TASKS_REL} could not be read; nothing was recorded (run kit task status)."
    repeated = _repeat(data, prompt, task_id)
    if repeated is not None:
        return _done(repeated)
    submitted = [t for t in data["tasks"] if isinstance(t, dict) and t.get("state") == "SUBMITTED"]
    if task_id is not None:
        task = next((t for t in data["tasks"] if t.get("id") == task_id), None)
        if task is None:
            return f"no task '{task_id}'; nothing was recorded."
        if task.get("state") != "SUBMITTED":
            return f"{task_id} is {task.get('state')}, not SUBMITTED; nothing was recorded."
    elif len(submitted) == 1:
        task = submitted[0]
    elif not submitted:
        return "no task is SUBMITTED; nothing was recorded."
    else:
        ids = ", ".join(t["id"] for t in submitted)
        example = submitted[0]["id"]
        return f"several tasks are SUBMITTED ({ids}); ask which one (e.g. '승인 {example}')."
    report = task.get("report")
    try:
        report_path = (root / report).resolve()
        if root.resolve() not in report_path.parents:
            raise ValueError("outside")
        digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    except (TypeError, ValueError, OSError):
        return f"the report of {task['id']} is missing; nothing was recorded."
    if digest != task.get("submitted_sha256"):
        return f"{report} changed after submit; submit {task['id']} again, nothing was recorded."
    record = {
        "task": task["id"],
        "at": _now(),
        "by": "human-hook",
        "evidence": prompt.strip()[:EVIDENCE_MAX],
        "report_sha256": digest,
        "agent": AGENT,
    }
    data["approvals"].append(record)
    task["approval"] = record
    task["state"] = "APPROVED"
    task.setdefault("history", []).append(
        {"at": record["at"], "event": "approved", "detail": "human-hook"}
    )
    try:
        _save(path, data)
    except OSError as exc:
        return f"could not write {TASKS_REL} ({exc}); nothing was recorded."
    return _done(task["id"])


def on_prompt(event: dict) -> None:
    prompt = event.get("prompt")
    if not isinstance(prompt, str) or not (ROOT / TASKS_REL).is_file():
        return
    ok, task_id, mixed = match_approval(prompt)
    if ok:
        _context(approve(ROOT, prompt, task_id))
    elif mixed:
        _context(
            "the prompt starts like an approval but says more, so nothing was recorded. "
            "If the user meant to approve, ask them to reply with only '승인' "
            "(or '승인 <task id>')."
        )


# ---------------------------------------------------------------- PreToolUse


def _norm(text: str) -> str:
    return text.replace("\\", "/").lower()


def _paths(tool_input):
    """Target paths of a file tool (Write/Edit/NotebookEdit, apply_patch), else None."""
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "notebook_path", "path"):
        if isinstance(tool_input.get(key), str):
            return [tool_input[key]]
    command = tool_input.get("command")
    if isinstance(command, str) and command.lstrip().startswith("*** Begin Patch"):
        return [m.group(1) for m in _PATCH_PATH.finditer(command)]
    return None


def _path_refusal(path: str, tool_input) -> str:
    p = _norm(path).rstrip("/")
    if p.endswith(".kit/work/tasks.json"):
        return f"{TASKS_REL} is written by kit task and the approval hook only"
    if "kit_approval" in p or p.endswith(".codex/hooks.json"):
        return "the approval hook and its registration are not for the agent to change"
    if p.endswith(".claude/settings.json"):
        body = _norm(json.dumps(tool_input, ensure_ascii=False))
        if "hooks" in body or "kit_approval" in body:
            return "the hooks in .claude/settings.json are not for the agent to change"
    return ""


def refusal(tool_input) -> str:
    """Why this tool call is refused, or ''. File tools are judged by their target paths,
    shell commands by their text."""
    paths = _paths(tool_input)
    if paths is not None:
        return next((r for r in (_path_refusal(x, tool_input) for x in paths) if r), "")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    low = _norm(command if isinstance(command, str) else json.dumps(tool_input))
    if "tasks.json" in low and ".kit" in low:
        return f"{TASKS_REL} is written by kit task and the approval hook only"
    if _TASK_APPROVE.search(low):
        return "approvals come from the user (the hook records '승인'), not from the agent"
    if any(x in low for x in _PROTECTED):
        return "the approval hook and its registration are not for the agent to change"
    if ".claude/settings" in low and "hooks" in low:
        return "the hooks in .claude/settings.json are not for the agent to change"
    return ""


def on_tool(event: dict) -> int:
    why = refusal(event.get("tool_input"))
    if not why:
        return 0
    message = (
        f"Blocked by the kit approval hook: {why}. Show the report and ask the user to "
        "reply '승인'; use kit task status to read the state."
    )
    # JSON deny, exit 0. Codex 0.166 on Windows ran the tool after an exit 2 ("hook Failed",
    # M-05 2026-11-07); permissionDecision "deny" is the documented form for both agents.
    _out(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    try:
        event = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return 0
    if not isinstance(event, dict):
        return 0
    name = event.get("hook_event_name")
    if name == "UserPromptSubmit":
        on_prompt(event)
        return 0
    if name == "PreToolUse":
        return on_tool(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
