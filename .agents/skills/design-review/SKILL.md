---
name: design-review
description: "Use only when the user invokes $design-review or asks for a design review ('설계 리뷰', '응집도', '결합도', 'cohesion', 'coupling') - reports cohesion, coupling, duplication and layering problems with file:line and a cost, without editing code. Do NOT use unasked."
---

# Design Review

Look at the code's structure from a software-design point of view and report what you find. This is a read-only report; the user decides what to change.

## Steps

1. Read `TASK_BRIEF.md` if present and list the modules, classes and main functions in scope. Review only the code the task touches unless the user names a wider scope.
2. Check each item and note concrete evidence (`file:line`):
   - **Cohesion**: a function or module that does several unrelated jobs (parsing, computing and printing together; a name that needs "and").
   - **Coupling**: shared global or mutable state, modules that reach into each other's internals, circular imports, long parameter lists passed through many layers.
   - **Dependency direction**: core logic that depends on I/O, files, the network or the CLI instead of the other way round.
   - **Duplication**: the same logic in two or more places that must change together.
   - **Size**: functions too long to read in one screen, or nesting deeper than about three levels.
   - **Testability**: logic that cannot be called from a test without real files, input or time.
3. Output this table, most important first, at most 10 rows:

   | # | Location | Problem | Impact | Suggestion | Cost |
   |---|---|---|---|---|---|
   | 1 | `file:line` | <what, in one line> | <what goes wrong or gets harder> | <smallest change that helps> | S/M/L |

4. End with one line: the single change worth doing first, or "No change needed for this task" if nothing affects correctness, the tests or the next change.

## Rules

- Do not edit code. Change something only after the user picks rows from the table.
- Judge against the task's size. A short solution script does not need layers or classes; do not suggest patterns for their own sake.
- Every row needs a location and a concrete impact. Drop rows that are only taste.
- If the user approves changes, re-run the tests after each one (see `../tdd-automator/references/languages.md`).
