# Example: mock maximum subarray sum

Task (mock): print the largest sum of a non-empty contiguous subarray. `1 <= n <= 2e5`, `-1e9 <= a[i] <= 1e9`. The solution passes all three statement examples.

1. Start green: `python -m pytest -q` gives `3 passed`.
2. Oracle: `brute(a)` tries every pair `i <= j` and returns `max(sum(a[i:j+1]))`. Written from the statement, not from the solution.
3. Generator: `gen(seed)` uses `random.Random(seed)`, n from 1 to 8, values from -5 to 5 (negatives and zero are allowed by the statement).
4. Stress loop: stops at `seed 7 [-3, -1, -2] 0 -1`. The solution returns 0, the brute force returns -1.
5. Shrink: with n up to 2 the loop stops at `[-2]`: solution 0, brute -2.
6. By hand: the only non-empty subarray is `[-2]`, so the answer is -2, as the brute force says. The solution is wrong.
7. Keep it: add `test_all_negative` with `[-2] -> -2`. Cause: the running best starts at 0, which is the empty subarray. Fix: start from `a[0]`. The same 2000 seeds and 2000 new ones show no mismatch; `4 passed`.
8. Decision log line:

   `- counterexample [-2] -> best started at 0 (empty subarray) -> test_all_negative`
