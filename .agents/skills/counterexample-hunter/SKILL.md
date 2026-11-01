---
name: counterexample-hunter
description: "Use after a solution passes the task's examples, when hidden tests decide the score - compares it to a brute-force oracle on many small random inputs, shrinks any mismatch and keeps it as a test. Do NOT use when no slow-but-sure reference or checker can be written."
---

# Counterexample Hunter

Example tests only show that the solution works on the cases you already thought of. Look for an input that breaks it before the hidden tests do.

## Steps

1. **Start green.** The task's examples and the `tdd-automator` tests must pass first. If they fail, use `systematic-debugging` instead.
2. **Write the oracle.** In a scratch folder `stress/` in the workspace, write `brute`: the simplest version that is obviously correct (try every option, simulate step by step). It may be exponential; it only sees tiny inputs. Do not copy code or helper functions from the solution, or both can share the same bug.
   - If no brute force exists, write a `check(input, output)` that tests the properties of a valid answer (sorted, a permutation, the sum matches, the path exists and has the claimed length).
3. **Write the generator.** `gen(seed)` returns one valid input: small sizes (n from 1 to about 8), small value ranges, and the statement's special values when they are allowed (0, negatives, duplicates, equal elements, n = 1). Never generate inputs the statement rules out.
4. **Run the stress loop** with fixed seeds, stopping at the first mismatch:

```python
for seed in range(2000):
    case = gen(seed)
    if solve(case) != brute(case):
        print("seed", seed, case, solve(case), brute(case))
        break
else:
    print("no counterexample in 2000 cases")
```

   For a program that reads stdin, run both sides with `subprocess` and compare the text output. For other languages see `../tdd-automator/references/languages.md`.
5. **Shrink.** Lower the maximum n and value range and run again until the failing input is as small as you can get. Small inputs make the cause visible.
6. **Decide who is wrong.** Work the shrunk input out by hand against the statement. If `brute` or `gen` is wrong, fix it and go back to step 4.
7. **Keep it.** Add the shrunk input as a regression test with the hand-checked answer, fix the cause with `systematic-debugging`, then re-run the same seeds and 2000 new ones.
8. **Record.** Append `- counterexample <input> -> <cause> -> <test name>` to the Decision log in `TASK_BRIEF.md`. If none was found, record the seed range and sizes tried.

## Rules

- "No counterexample" is evidence for the tried sizes only. Report the seed range and maximum n, not "correct".
- Never change a test's expected value to match the solution's output.
- Keep a run under about 30 s. Large-input speed is `benchmark`'s job.
- Delete `stress/` before submitting, or leave it out of the deliverable.
