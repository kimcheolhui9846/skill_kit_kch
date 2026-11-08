"""Profile a CSV file for data-quality-validator. Reads only; never changes or writes data.

    python scripts/profile_csv.py data.csv [--key COLUMN] [--json] [--max-rows N]
                                  [--delimiter ,] [--encoding utf-8]

Reports rows, ragged rows, exact duplicate rows, duplicate keys with different values, and
per column: missing values, inferred type and values that do not fit it, distinct values,
min / max and IQR outlier candidates for numbers. These are candidates for a human decision,
not things to delete.

Python 3.9+, standard library only. Exit codes: 0 done, 2 the file cannot be read, 64 bad
arguments.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

MISSING = {"", "na", "n/a", "nan", "null", "none", "-", "?"}
TRUE_FALSE = {"true", "false", "yes", "no", "y", "n", "t", "f"}
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y")
INT = re.compile(r"^[+-]?\d+$")
FLOAT = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")
EXAMPLES = 3
ENCODINGS = ("utf-8-sig", "cp949")


class ArgError(Exception):
    """A bad argument found after reading the header (exit 64)."""


def kind(value: str) -> str:
    v = value.strip()
    if INT.match(v):
        return "int"
    if FLOAT.match(v):
        return "float"
    if v.lower() in TRUE_FALSE:
        return "bool"
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(v, fmt)
            return "date"
        except ValueError:
            continue
    return "text"


def column_type(kinds: Dict[str, int]) -> str:
    """The type most values have; int and float together are float."""
    if not kinds:
        return "empty"
    merged = dict(kinds)
    if "int" in merged and "float" in merged:
        merged["float"] += merged.pop("int")
    return max(sorted(merged), key=lambda k: merged[k])


def fits(value_kind: str, col_type: str) -> bool:
    return value_kind == col_type or (col_type == "float" and value_kind == "int")


def outliers(numbers: List[float]) -> Optional[dict]:
    """IQR rule (1.5 x IQR outside the quartiles). Needs 4 values or more."""
    if len(numbers) < 4:
        return None
    q1, _, q3 = statistics.quantiles(numbers, n=4, method="inclusive")
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    found = [x for x in numbers if x < low or x > high]
    return {"low": low, "high": high, "count": len(found), "examples": found[:EXAMPLES]}


def read_rows(path: Path, encoding: Optional[str], delimiter: str):
    data = path.read_bytes()
    for enc in [encoding] if encoding else list(ENCODINGS):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        return enc, list(csv.reader(text.splitlines(), delimiter=delimiter))
    tried = encoding or ", ".join(ENCODINGS)
    raise ValueError(f"cannot decode {path.name} as {tried}; pass --encoding")


def profile(rows: List[List[str]], key: Optional[str], max_rows: int) -> dict:
    if not rows:
        return {"rows": 0, "columns": [], "header": []}
    header, body = rows[0], rows[1:]
    total = len(body)
    sampled = total > max_rows
    body = body[:max_rows]
    width = len(header)
    ragged = [i + 2 for i, r in enumerate(body) if len(r) != width]  # file line numbers
    seen: Dict[tuple, int] = {}
    duplicates = []
    for i, r in enumerate(body):
        t = tuple(r)
        if t in seen:
            duplicates.append({"line": i + 2, "same_as_line": seen[t]})
        else:
            seen[t] = i + 2
    columns = []
    for c, name in enumerate(header):
        values = [r[c] if c < len(r) else "" for r in body]
        present = [v for v in values if v.strip().lower() not in MISSING]
        kinds: Dict[str, int] = {}
        for v in present:
            k = kind(v)
            kinds[k] = kinds.get(k, 0) + 1
        col_type = column_type(kinds)
        bad = [
            (i + 2, v)
            for i, v in enumerate(values)
            if v.strip().lower() not in MISSING and not fits(kind(v), col_type)
        ]
        info = {
            "name": name,
            "type": col_type,
            "missing": len(values) - len(present),
            "distinct": len(set(present)),
            "mismatches": len(bad),
            "mismatch_examples": [{"line": n, "value": v} for n, v in bad[:EXAMPLES]],
        }
        if col_type in ("int", "float"):
            numbers = [float(v) for v in present if kind(v) in ("int", "float")]
            if numbers:
                info["min"], info["max"] = min(numbers), max(numbers)
            info["outliers"] = outliers(numbers)
        columns.append(info)
    result = {
        "rows": total,
        "profiled_rows": len(body),
        "sampled": sampled,
        "header": header,
        "ragged_lines": ragged[:EXAMPLES],
        "ragged": len(ragged),
        "duplicate_rows": len(duplicates),
        "duplicate_examples": duplicates[:EXAMPLES],
        "columns": columns,
    }
    if key is not None:
        result["key"] = key_conflicts(header, body, key)
    return result


def key_conflicts(header: List[str], body: List[List[str]], key: str) -> dict:
    if key not in header:
        raise ArgError(f"--key {key} is not a column; columns: {', '.join(header)}")
    k = header.index(key)
    by_key: Dict[str, set] = {}
    for r in body:
        if k < len(r):
            by_key.setdefault(r[k], set()).add(tuple(r))
    repeated = {v: rows for v, rows in by_key.items() if len(rows) > 1}
    return {
        "column": key,
        "keys_with_different_rows": len(repeated),
        "examples": sorted(repeated)[:EXAMPLES],
    }


def markdown(path: str, enc: str, p: dict) -> str:
    out = [
        f"### Data profile: {path}",
        "",
        f"- Encoding: {enc}. Rows: {p['rows']}"
        + (f" (profiled the first {p['profiled_rows']})" if p.get("sampled") else "")
        + f". Columns: {len(p['header'])}.",
    ]
    if p["rows"]:
        out.append(
            f"- Rows with a wrong number of fields: {p['ragged']}"
            + (f" (lines {', '.join(map(str, p['ragged_lines']))})" if p["ragged"] else "")
        )
        dup = ", ".join(
            f"line {d['line']} = line {d['same_as_line']}" for d in p["duplicate_examples"]
        )
        out.append(f"- Exact duplicate rows: {p['duplicate_rows']}" + (f" ({dup})" if dup else ""))
        if "key" in p:
            kc = p["key"]
            out.append(
                f"- Key {kc['column']}: {kc['keys_with_different_rows']} value(s) with "
                f"different rows" + (f" ({', '.join(kc['examples'])})" if kc["examples"] else "")
            )
        out += [
            "",
            "| Column | Type | Missing | Distinct | Type mismatches | Min | Max | "
            "Outlier candidates (IQR) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in p["columns"]:
            mism = str(c["mismatches"])
            if c["mismatch_examples"]:
                mism += (
                    " ("
                    + ", ".join(f"line {e['line']}: {e['value']!r}" for e in c["mismatch_examples"])
                    + ")"
                )
            o = c.get("outliers")
            outl = (
                "-"
                if not o
                else f"{o['count']} outside [{o['low']:g}, {o['high']:g}]"
                + (f": {', '.join(f'{x:g}' for x in o['examples'])}" if o["examples"] else "")
            )
            out.append(
                f"| {c['name']} | {c['type']} | {c['missing']} | {c['distinct']} | {mism} "
                f"| {_num(c.get('min'))} | {_num(c.get('max'))} | {outl} |"
            )
    out += ["", "These are candidates for a decision with a reason, not rows to delete."]
    return "\n".join(out) + "\n"


def _num(x) -> str:
    return "-" if x is None else f"{x:g}"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Profile a CSV file (reads only).")
    ap.add_argument("path")
    ap.add_argument("--key")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-rows", type=int, default=200000)
    ap.add_argument("--delimiter", default=",")
    ap.add_argument("--encoding")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 64
    if ns.max_rows < 1 or len(ns.delimiter) != 1:
        print("--max-rows must be 1 or more and --delimiter one character", file=sys.stderr)
        return 64
    path = Path(ns.path)
    try:
        enc, rows = read_rows(path, ns.encoding, ns.delimiter)
        result = profile(rows, ns.key, ns.max_rows)
    except ArgError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    except OSError as exc:
        print(f"cannot read {path}: {exc.strerror or exc}", file=sys.stderr)
        return 2
    except (ValueError, LookupError, csv.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):  # a cp949 console must not crash on data
        sys.stdout.reconfigure(errors="replace")
    if ns.json:
        print(
            json.dumps({"path": path.name, "encoding": enc, **result}, indent=2, ensure_ascii=False)
        )
    else:
        sys.stdout.write(markdown(path.name, enc, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
