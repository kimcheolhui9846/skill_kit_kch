# Example: mock count of pairs

Task (mock): count pairs `i < j` with `a[i] + a[j] <= K`. `n <= 2e5`, `|a[i]| <= 1e9`, Python, 2 s.

1. Limits: n = 2e5 in Python needs O(n log n) or better (`../algorithm-optimizer/SKILL.md`, one row lower for Python).
2. Shape: pair counting with a sum threshold.
3. and 4. Candidates:

   | # | Approach | Core idea | Time / space | Fits limits? | Risks |
   |---|---|---|---|---|---|
   | A | Brute force | check every pair | O(n^2) / O(1) | no: 2e10 ops at n = 2e5 | none; use as the oracle |
   | B | Sort + two pointers | after sorting, for each left end move the right end down while the sum is too big | O(n log n) / O(n) | yes: about 4e6 ops | off-by-one when the pointers meet |
   | C | Sort + binary search | for each i, `bisect_right` for `K - a[i]` among the later elements | O(n log n) / O(n) | yes: about 4e6 ops | counting a pair twice or with itself |

   Requirements: none of them needs non-negative values. Python integers do not overflow.
5. Recommendation: C. It is a single loop around `bisect`, so it has the fewest moving parts at the same complexity as B.
6. Stop: "A is only for checking. B and C both fit; I recommend C. Which one?" The user answers "B".
7. Decision log line:

   `- chose B (two pointers) -> user choice; same O(n log n) as C -> n = 2e5, about 4e6 ops`
