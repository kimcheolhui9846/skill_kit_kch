---
name: session-recovery
description: "Use at the start of a session, after a context reset or when resuming earlier work in a workspace that has .kit/work/ - restores the approved state and the temporary (unapproved) state with `kit recover`, shows both to the user before any work, and saves progress with `kit recover save`. Do NOT use for a new workspace without .kit/work/ or to approve tasks (use task-approval)."
---

# Session recovery

A new session remembers nothing. The kit keeps what was approved and what was only in
progress in `.kit/work/`, apart from each other. Restore both, show them, then continue.

## At the start of a session
1. Run `kit recover`. It prints two parts:
   - **Approved state:** current Task and its state, the last approved Task (time and who
     recorded it: human-cli, human-hook or agent-recorded), files changed since that Task was
     submitted, its test result, open risks, the next plan, recent decisions.
   - **Temporary (not approved):** what the last session saved with `kit recover save`.
2. Show the user both parts before doing anything else. Say which part is approved. The
   temporary part was never reviewed: never present it as approved or as done.
3. Point out what needs attention: warnings, files changed since the last approval that the
   current Task does not explain, a temporary state that is out of date.
4. Continue only after the user agrees to the plan. If the current Task is SUBMITTED, wait
   for the approval; do not start the next Task.

## While working
- After each meaningful step and before anything long: `kit recover save --note "..."
  --command "<last command>" --tests "<last test summary>" --error "<open error>"`. It
  overwrites the previous temporary state; repeat `--error` for each open error.
- When the user decides something: `kit recover decide "<decision, in the user's words>"
  --task T-001`. The log only grows.
- Approvals go through task-approval. After an approval the kit rewrites
  `.kit/work/HANDOFF.md` from the approval record; never edit it by hand.

## Files
| File | Holds | Who writes |
|---|---|---|
| `.kit/work/HANDOFF.md` | approved state only | kit, after an approval |
| `.kit/work/tasks.json` | Tasks and approvals | `kit task`, the approval hook |
| `.kit/work/wip.json` | temporary state, `UNAPPROVED` | `kit recover save` |
| `.kit/work/decisions.md` | decisions, append only | `kit recover decide` |
| `.kit/work/reports/<Task>.md` | Task reports | you, then `kit task submit` |

A `HANDOFF.md` at the workspace root belongs to the user. The kit never reads or changes it;
read it only if the user asks.

## Without Python
Read `.kit/work/HANDOFF.md`, then `.kit/work/tasks.json` (or `TASKS.md`), the latest report,
`.kit/work/decisions.md`, and last `.kit/work/wip.json` (or `wip.md`). Report them in that
order with the temporary part under a heading that says `임시(미승인)`. Keep your own
temporary notes in `.kit/work/wip.md` under the same heading, and never in HANDOFF.md.
