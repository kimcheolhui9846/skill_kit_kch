---
name: benchmark
description: "Use only when the user invokes $benchmark or asks to measure speed or memory ('벤치마크', '프로파일링', 'benchmark', 'profile') - times synthetic inputs (timeit, cProfile, tracemalloc) and compares before and after. Do NOT use unasked or when tests show it is fast enough."
---

# Benchmark

## Steps

1. Generate synthetic input at the stated maximum size with a fixed random seed. Never use real task data from outside the workspace.
2. Measure wall time first (Python shown; other languages in `references/languages.md`):

```python
import random
import timeit

random.seed(0)
data = [random.randint(-(10**9), 10**9) for _ in range(200_000)]
print(min(timeit.repeat(lambda: solve(data), number=1, repeat=5)))
```

3. Only if it is too slow, find where the time goes:

```python
import cProfile
import pstats

cProfile.run("solve(data)", "prof.out")
pstats.Stats("prof.out").sort_stats("cumulative").print_stats(10)
```

4. Only if memory is the problem:

```python
import tracemalloc

tracemalloc.start()
solve(data)
print(tracemalloc.get_traced_memory())  # (current, peak) in bytes
tracemalloc.stop()
```

5. After a change, re-run the correctness tests, then the same measurement with the same seed and size.
6. Report a table: `Version | Input size | Best of 5 (s) | Peak memory`. Note noise: other processes, first-run warm-up, timer resolution.

## Rules

- Delete temporary profiling files (such as `prof.out`) before submitting.
