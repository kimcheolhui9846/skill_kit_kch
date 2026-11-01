---
name: algorithm-options
description: "Use before writing core logic for an algorithm problem with stated input sizes or time limits, or when several approaches could work - lists 2-3 candidates with complexity, fit to limits and risks, recommends one and waits for the user's choice. Do NOT use to speed up existing code."
---

# Algorithm Options

Lay out the realistic ways to solve the problem and let the user choose before any solution code exists.

## Steps

1. Read the constraints from `TASK_BRIEF.md` (or the statement). Work out the allowed complexity with the table in step 2 of `../algorithm-optimizer/SKILL.md`. Missing limits are ASSUMPTIONs.
2. Name the problem's shape in one line (shortest path, intervals, subsequences, counting modulo p, connectivity, top-k, string matching, scheduling, ...). It points to the candidate families.
3. Choose 2 or 3 candidates. Always include the straightforward brute force: it is the baseline and the oracle for `counterexample-hunter`.
4. Show this table:

   | # | Approach | Core idea | Time / space | Fits limits? | Risks |
   |---|---|---|---|---|---|
   | A | <name> | <one line> | O(...) / O(...) | yes/no, with the number (n = ..., about ... ops) | <edge cases, recursion depth, float precision, hard to get right> |

   Under the table, write what each approach requires from the input (non-negative weights, sorted input, small value range) and whether the statement guarantees it.
5. Mark one recommendation with a one-line reason: the simplest approach that fits the limits with margin, not the most advanced one.
6. **Stop and wait** for the user's choice. Write no solution code until the user picks. If the user says "you choose", take the recommendation.
7. Append `- chose <approach> -> <reason> -> <limits check>` to the Decision log in `TASK_BRIEF.md`.

## Rules

- Use only the language and libraries the task allows.
- Do not present an approach you cannot state the complexity of. If unsure whether one is correct, say so in Risks.
- If the user later reports it too slow, use `algorithm-optimizer`; do not reopen this table unless the limits changed.
