---
name: algorithm-optimizer
description: "Use when a working solution is too slow or exceeds the time/memory limits - estimates allowed complexity, finds the bottleneck, compares better algorithms and re-runs tests. Do NOT use before a solution exists (use algorithm-options) or when limits are met."
---

# Algorithm Optimizer

## Steps

1. Find the limits: input sizes (n, m, ...), time limit, memory limit. If missing, write them as ASSUMPTION.
2. Work out the budget. Roughly 1e8 simple operations per second in C++/Java and 1e7 in Python.

   | Largest n | Target complexity |
   |---|---|
   | 10 to 12 | O(n!) or O(2^n * n) |
   | 20 to 25 | O(2^n) |
   | 500 | O(n^3) |
   | 5,000 | O(n^2) |
   | 1e5 to 1e6 | O(n log n) |
   | 1e7 and more | O(n) |

   In Python aim one row lower than this table.
3. Write the current complexity of each loop and call, and name the dominant term.
4. Pick a fix that matches the bottleneck:
   - repeated lookups: hash map or set
   - pair or range queries: sorting with two pointers or binary search, prefix sums
   - overlapping subproblems: dynamic programming or memoization
   - repeated min/max: heap
   - connectivity: union-find; shortest paths: BFS or Dijkstra
5. Avoid myths: `for` loops are fine; list comprehensions do not change complexity; use NumPy/pandas vectorization only if the library is allowed and a measurement shows a gain.
6. Change one thing at a time and re-run the correctness tests after each change.
7. Record before and after: complexity, and time on the same input if you measured it.

Language-specific speed notes are in `references/languages.md`.
