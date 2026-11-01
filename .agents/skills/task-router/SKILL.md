---
name: task-router
description: "Use when starting a new non-trivial coding task or when requirements are unclear - writes goal, I/O, constraints and evaluation to TASK_BRIEF.md and picks the fewest other skills. Do NOT use for one-line fixes, follow-ups on a briefed task, or questions needing no code."
---

# Task Router

Turn the task statement into a short written brief, then choose the fewest skills that cover it.

## Steps

1. Read the whole task statement and list every provided file. Do not write solution code yet.
2. Extract, quoting the statement where possible:
   - **Goal**: one sentence.
   - **Inputs/outputs**: formats, file names and paths, encodings, exact output layout.
   - **Constraints**: language and version, allowed libraries, input size limits, time and memory limits.
   - **Evaluation**: how the result is judged (hidden tests, exact output match, performance, review).
3. Separate facts from assumptions. Anything the statement does not say is an assumption: mark it `ASSUMPTION` and choose the most conservative reading.
4. Classify the task as one of `algorithm`, `data`, `web-api`, `output-format`, `debugging`, `other`.
5. Select skills. Add a skill only when its condition holds:

   | Condition | Skill |
   |---|---|
   | Core logic with checkable inputs and outputs | `tdd-automator` |
   | Input sizes or time/memory limits are stated, or several algorithms could solve the core problem | `algorithm-options`, before writing core logic |
   | A working solution is too slow or exceeds the limits | `algorithm-optimizer` |
   | Hidden tests decide the score and a brute force or answer checker can be written | `counterexample-hunter`, after the examples pass |
   | The task gives an existing repository to modify or extend | `codebase-explorer`, before any edit |
   | A test fails or the program misbehaves and the cause is unknown | `systematic-debugging` |
   | There is a deliverable (files, output format, run command) | `submission-validator`, before finishing |
   | The user asks why the solution works | `implementation-review` (only on request) |
   | Measured slowness needs profiling | `benchmark` (only on request) |
   | The user asks about cohesion, coupling or structure | `design-review` (only on request) |

6. Write `TASK_BRIEF.md` in the workspace root with the template below. Keep it under 40 lines, not counting the Decision log.
7. Re-read `TASK_BRIEF.md` when the conversation gets long and before declaring the task done. Append one Decision log line for each non-obvious decision.

## TASK_BRIEF.md template

```markdown
# Task Brief
Type: <algorithm|data|web-api|output-format|debugging|other>

## Goal
<one sentence>

## Inputs / Outputs
- <format, files, paths, exact layout>

## Constraints
- <language, libraries, sizes, limits>

## Evaluation
- <how the result is judged>

## Facts vs assumptions
- FACT: <quoted from the statement>
- ASSUMPTION: <what you assumed and why>

## Risks
- <edge cases, ambiguities, performance traps>

## Repository (existing-repo tasks only; filled by codebase-explorer)
- Baseline: <test command> -> <N passed, M failed; names of already failing tests>
- Change: <files>
- Leave: <files>

## Skills
- <skill>: <why it is needed>

## Plan
1. <first step>
2. <next step>
<3 to 5 steps in order>

## Decision log
- <what> -> <why> -> <evidence>
```

## Rules

- If an ambiguity would change the output, ask the user before building.
- Keep the brief inside the workspace. Never send task content anywhere else.
