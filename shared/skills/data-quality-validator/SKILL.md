---
name: data-quality-validator
description: "Use before training, evaluating or reporting on a dataset (CSV, tables, logs turned into rows) - checks missing values, outliers, duplicates, type mismatches, leakage and what cleaning changed, and reports each decision with its reason and limits. Do NOT use to tune a model or to fix code; never use it to delete data silently."
---

# Data quality validator

Results built on a dataset are only as good as the data. Check it before using it, and make
every cleaning step visible to the reviewer.

**Never drop missing values or outliers by default.** Each one is either an error, a real but
rare value, or a signal. Decide per column, write the reason and the limit, and report how
many rows each step touched.

## Steps

1. **Profile first, change nothing.** Count rows and columns, then per column: missing values,
   inferred type and values that do not fit it, distinct values, min / max. With Python run
   `python scripts/profile_csv.py data.csv` (standard library only; reads, never writes) or
   use pandas if the task already has it. Without either, do the same counts by hand on a
   sample and say it was a sample.
2. **Missing values.** Where and how many; whether they cluster (one source, one period, one
   class). Options: keep and mark, impute (say how), or drop. Choose per column and write why.
3. **Outliers.** Candidates by a stated rule (IQR, z-score, domain limits). Check a few by hand:
   a typo, a unit error, or a real extreme? Keep real extremes unless the task says otherwise.
4. **Duplicates.** Exact duplicate rows and duplicate keys with different values. Decide which
   is the true record and why; a repeated measurement may be legitimate.
5. **Type mismatches.** Numbers stored as text, mixed date formats, decimal commas, encodings
   (UTF-8 vs cp949), booleans spelled several ways. Convert explicitly and count failures.
6. **Leakage.** Train / evaluation split done before any fitting (scalers, imputers, encoders);
   no future rows in the past (time order); no feature that is the target in disguise (an ID
   or timestamp that encodes the label, a column computed from the target); the same entity
   in both splits when it should not be.
7. **Assumptions of the processing.** List what every step assumes (independent rows, one row
   per entity, stable units, the target is correct).
8. **Before and after.** Row counts and the distribution of key columns and of the target
   before and after cleaning. Say which rows were excluded and what that may change in the
   results (a class or a group that shrank, a range that is no longer covered).

## Report

```markdown
### Data quality report
| Check | Finding (counts) | Decision | Reason | Limit |
|---|---|---|---|---|
| Missing values | | keep / impute / drop | | |
| Outliers | | | | |
| Duplicates | | | | |
| Type mismatches | | | | |
| Leakage | | | | |
- Assumptions:
- Rows before -> after: (and per step)
- Distribution change of key columns and target:
- Effect of excluded data on the results:
- Open questions for the reviewer:
```

## Rules

- Keep the raw data unchanged; write cleaned data to a new file and say which.
- Every drop, fill or conversion has a count, a reason and a limit in the report.
- If a decision changes the meaning of the result (excluding a group, imputing the target),
  ask the user before applying it.
- A requirement that does not say how to treat a case is a question for the user, not a guess.
