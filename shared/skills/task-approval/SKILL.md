---
name: task-approval
description: "Use when work is split into Tasks that need the user's approval before the next one starts - records them with `kit task` (add, start, report, submit, approve), writes the 5.6 report and records approvals honestly. Do NOT use for classifying a request (use task-router) or for one-line fixes (light path)."
---

# Task approval

The kit keeps Task state in `.kit/work/tasks.json` with `kit task`. It makes a skipped approval
visible; it cannot stop an agent that ignores it. Follow it because the user relies on it.

## Flow
1. Plan: `kit task add T-001 --title "..." --requires REQ-001 --grade S` per Task, with
   `--depends-on` for order. Use the requirement ids from TASK_BRIEF.md.
2. Start: `kit task start T-001`. Exit 2 means a dependency is not approved or another Task
   is in progress: stop and report, do not work around it.
3. Work: `kit task subtask add T-001 "..."` / `kit task subtask done T-001.1` for your own
   steps. Subtasks never need approval.
4. Report: `kit task report T-001` writes the 5.6 template to `.kit/work/reports/T-001.md`.
   Fill every section. Section 4 needs a row for each requirement; a test you did not run is
   `NOT RUN: <reason>`. Never write PASS for a test that did not run.
5. Submit: `kit task submit T-001`, then show the report to the user and wait.
6. Approval comes from the user, never from you:
   - The user may run `kit task approve T-001` at a terminal (recorded as `human-cli`).
   - If the user approves in chat, record it with their exact words:
     `kit task approve T-001 --by agent-recorded --quote "<the user's message>"`.
   - A conditional, partial or unclear reply is not approval: ask. Feedback instead of
     approval: `kit task request-changes T-001 --reason "..."`, then start it again.
7. `kit task status` before each new Task. Exit 1 means an approved report changed after
   approval: tell the user.

Never edit `.kit/work/tasks.json` by hand, never approve on the user's behalf, and never
change a report after approval without saying so.

## Without Python
Keep the same record in `.kit/work/TASKS.md`:

| Task | Title | Requirements | Depends on | State | Approved by | Evidence |
|---|---|---|---|---|---|---|

States are TODO, IN_PROGRESS, SUBMITTED, CHANGES_REQUESTED, APPROVED. Start a Task only when
every Task it depends on is APPROVED. Write `agent-recorded` and the user's exact words for
each approval, and keep the report in `.kit/work/reports/<Task>.md`.
