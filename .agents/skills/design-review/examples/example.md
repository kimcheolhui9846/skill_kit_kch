# Example: design review of a mock grade report

Code (mock): `main.py` (80 lines) reads `scores.csv`, computes per-student averages and prints a ranked table. `test_main.py` has 4 tests.

1. Scope: `main.py` only. `load()`, `report()` and the global `STUDENTS` list.
2. and 3. Findings:

   | # | Location | Problem | Impact | Suggestion | Cost |
   |---|---|---|---|---|---|
   | 1 | `main.py:22` | `report()` reads the file, averages and prints | tests must create a CSV and capture stdout to check one average | split out `average(rows) -> dict` and call it from `report()` | S |
   | 2 | `main.py:5` | `load()` appends to the global `STUDENTS` | calling it twice doubles the data; tests depend on their order | return the list instead of filling a global | S |
   | 3 | `main.py:40`, `main.py:61` | rounding to 2 places written twice | a format change must be made in two places | one `fmt(x)` helper | S |

   Not reported: "use classes" - 80 lines do not need them.
4. First change: row 1, because it makes the averaging logic testable without files.

The user picks rows 1 and 2. After each change `python -m pytest -q` gives `4 passed`, then `6 passed` with two new tests for `average`.
