"""Counterexample records (P5-T5, 00_PROMPT 10.5, REQ-CE-001/002, Q7).

State lives at .kit/work/counterexamples.json: {"schema": 1, "items": [...]}, each item in the
00_PROMPT 10.5.3 shape plus "question", "decision" and "history".

States: PROPOSED -> ACCEPTED | REJECTED | NEEDS_SPEC
        NEEDS_SPEC -> ACCEPTED (only with the reviewer's words, `resolve`) | REJECTED
        ACCEPTED -> CONVERTED (the test must be in trace.json)
REJECTED and CONVERTED are final. An item without "expected" cannot be accepted: the
requirements did not decide it, so it goes to NEEDS_SPEC (no guessing, 10.5.1 step 5).

Reviewer decisions 2026-11-07: command `kit ce`; NEEDS_SPEC is resolved only with the
reviewer's words (--quote, recorded and masked like `task approve --by agent-recorded`; L1,
it records and shows, it cannot stop an invented quote); a C-grade task submit needs a record
for one of its requirements and none of them still PROPOSED.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from . import trace
from .fsops import safe_path
from .logs import mask

CE_REL = ".kit/work/counterexamples.json"
SCHEMA = 1
PROPOSED, ACCEPTED, REJECTED, NEEDS_SPEC, CONVERTED = (
    "PROPOSED",
    "ACCEPTED",
    "REJECTED",
    "NEEDS_SPEC",
    "CONVERTED",
)
STATES = (PROPOSED, ACCEPTED, REJECTED, NEEDS_SPEC, CONVERTED)
NEXT = {
    PROPOSED: (ACCEPTED, REJECTED, NEEDS_SPEC),
    NEEDS_SPEC: (ACCEPTED, REJECTED),
    ACCEPTED: (CONVERTED, REJECTED),
    REJECTED: (),
    CONVERTED: (),
}
# 00_PROMPT 10.5.2
CATEGORIES = (
    "boundary",
    "empty",
    "type",
    "missing",
    "outlier",
    "duplicate",
    "large",
    "conflict",
    "order",
    "encoding",
    "path",
)
ORIGINS = ("black-box", "white-box")
CE_ID = re.compile(r"^CE-[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")
TEXT_MAX = 2000
REQUIRED = ("target", "assumption_challenged", "category", "origin", "input", "would_catch")


class CeError(ValueError):
    """counterexamples.json cannot be used as it is (exit 65)."""


class Refused(Exception):
    """A rule refused the request; nothing was written (exit 2)."""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(target: Path) -> Path:
    return safe_path(target, CE_REL)


def empty() -> dict:
    return {"schema": SCHEMA, "items": []}


def load(target: Path) -> dict:
    p = path(target)
    if not p.is_file():
        return empty()
    try:
        raw = p.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CeError(f"{CE_REL} cannot be read: {exc}") from None
    if not raw.strip():
        return empty()
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise CeError(f"{CE_REL} is not valid JSON: {exc}") from None
    validate(data)
    return data


def save(target: Path, data: dict) -> None:
    validate(data)
    p = path(target)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, p)


def _bad(message: str) -> CeError:
    return CeError(f"{CE_REL}: {message}")


def validate(data: object) -> None:
    """The 10.5.3 record schema; a hand edit that breaks it is exit 65."""
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise _bad(f"expected an object with schema {SCHEMA}")
    items = data.get("items")
    if not isinstance(items, list):
        raise _bad("items must be a list")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise _bad("every item needs an id")
        cid = item["id"]
        if cid in seen:
            raise _bad(f"{cid} is listed twice")
        seen.add(cid)
        for key in REQUIRED:
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise _bad(f"{cid} needs {key}")
        reqs = item.get("requirements")
        if not isinstance(reqs, list) or not all(isinstance(r, str) for r in reqs):
            raise _bad(f"{cid}: requirements must be a list of REQ IDs")
        if item["category"] not in CATEGORIES:
            raise _bad(f"{cid} has category {item['category']!r}")
        if item["origin"] not in ORIGINS:
            raise _bad(f"{cid} has origin {item['origin']!r}")
        state = item.get("status")
        if state not in STATES:
            raise _bad(f"{cid} has status {state!r}")
        if state in (ACCEPTED, CONVERTED) and not item.get("expected"):
            raise _bad(f"{cid} is {state} without an expected result")
        if state == CONVERTED and not item.get("test_id"):
            raise _bad(f"{cid} is CONVERTED without test_id")
        if state in (ACCEPTED, CONVERTED) and item.get("question") and not item.get("decision"):
            raise _bad(f"{cid} left NEEDS_SPEC without a reviewer decision")


def get(data: dict, cid: str) -> dict:
    item = next((i for i in data["items"] if i["id"] == cid), None)
    if item is None:
        raise Refused(f"no counterexample {cid} (kit ce list)")
    return item


def _text(value: Optional[str], name: str, required: bool = True) -> str:
    value = (value or "").strip()
    if required and not value:
        raise ValueError(f"--{name} is needed")
    if len(value) > TEXT_MAX:
        raise ValueError(f"--{name} is longer than {TEXT_MAX} characters")
    return value


def _move(item: dict, state: str, detail: str = "") -> None:
    if state not in NEXT[item["status"]]:
        raise Refused(f"{item['id']} is {item['status']}; it cannot become {state}")
    entry = {"at": now(), "from": item["status"], "to": state}
    if detail:
        entry["detail"] = detail
    item["status"] = state
    item.setdefault("history", []).append(entry)


def add(
    data: dict,
    cid: str,
    target: str,
    requirements: List[str],
    assumption: str,
    category: str,
    origin: str,
    input_: str,
    would_catch: str,
    expected: Optional[str] = None,
    rationale: Optional[str] = None,
    trace_data: Optional[dict] = None,
) -> dict:
    if not CE_ID.match(cid):
        raise ValueError(f"counterexample ids look like CE-001; got '{cid}'")
    if category not in CATEGORIES:
        raise ValueError(f"--category must be one of {', '.join(CATEGORIES)}")
    if origin not in ORIGINS:
        raise ValueError(f"--origin must be one of {', '.join(ORIGINS)}")
    bad = [r for r in requirements if not trace.REQ_ID.match(r)]
    if bad:
        raise ValueError(f"--req takes REQ IDs like REQ-001; got '{bad[0]}'")
    if any(i["id"] == cid for i in data["items"]):
        raise Refused(f"{cid} already exists")
    if trace_data is not None and trace_data["requirements"]:
        unknown = [r for r in requirements if trace.get_req(trace_data, r) is None]
        if unknown:
            raise Refused(f"no requirement {unknown[0]} in trace.json (kit req list)")
    item = {
        "id": cid,
        "target": _text(target, "function"),
        "requirements": list(dict.fromkeys(requirements)),
        "assumption_challenged": _text(assumption, "assumption"),
        "category": category,
        "origin": origin,
        "input": _text(input_, "input"),
        "expected": _text(expected, "expected", required=False),
        "would_catch": _text(would_catch, "would-catch"),
        "rationale": _text(rationale, "rationale", required=False),
        "status": PROPOSED,
        "test_id": "",
        "result": "",
        "history": [{"at": now(), "to": PROPOSED}],
    }
    data["items"].append(item)
    return item


def accept(data: dict, cid: str) -> dict:
    item = get(data, cid)
    if item["status"] == NEEDS_SPEC:
        raise Refused(f"{cid} is NEEDS_SPEC; only the reviewer resolves it (kit ce resolve)")
    if not item.get("expected"):
        raise Refused(
            f"{cid} has no expected result; if the requirements do not decide it, "
            f"use kit ce needs-spec {cid} --question ..."
        )
    _move(item, ACCEPTED)
    return item


def reject(data: dict, cid: str, reason: str) -> dict:
    item = get(data, cid)
    reason = _text(reason, "reason")
    _move(item, REJECTED, reason)
    item["rejected_because"] = reason
    return item


def needs_spec(data: dict, cid: str, question: str) -> dict:
    item = get(data, cid)
    question = _text(question, "question")
    _move(item, NEEDS_SPEC, question)
    item["question"] = question
    return item


def resolve(data: dict, cid: str, expected: str, quote: str) -> dict:
    """The reviewer decided the expected result of a NEEDS_SPEC item."""
    item = get(data, cid)
    if item["status"] != NEEDS_SPEC:
        raise Refused(f"{cid} is {item['status']}; resolve is for NEEDS_SPEC items")
    expected = _text(expected, "expected")
    quote = mask(_text(quote, "quote"))
    _move(item, ACCEPTED, "reviewer decision")
    item["expected"] = expected
    item["decision"] = {"at": now(), "by": "agent-recorded", "quote": quote}
    return item


def convert(data: dict, cid: str, test_id: str, trace_data: dict) -> dict:
    item = get(data, cid)
    if item["status"] == NEEDS_SPEC:
        raise Refused(f"{cid} is NEEDS_SPEC; the reviewer must decide it before a test is written")
    test = trace.get_test(trace_data, test_id)
    if test is None:
        raise Refused(f"no test {test_id} in trace.json (kit trace link {test_id} ... first)")
    linked = {x["id"] for x in test["requirements"]}
    missing = [r for r in item["requirements"] if r not in linked]
    if missing:
        raise Refused(
            f"{test_id} does not check {', '.join(missing)} (kit trace link {test_id} "
            f"--req {missing[0]})"
        )
    _move(item, CONVERTED, test_id)
    item["test_id"] = test_id
    return item


def record_result(data: dict, cid: str, result: str) -> dict:
    item = get(data, cid)
    if item["status"] != CONVERTED:
        raise Refused(f"{cid} is {item['status']}; a result belongs to a CONVERTED item")
    item["result"] = mask(_text(result, "result"))
    return item


# ---------------------------------------------------------------- reading


def for_requirements(data: dict, req_ids: List[str]) -> List[dict]:
    wanted = set(req_ids)
    return [i for i in data["items"] if wanted & set(i["requirements"])]


def counts(items: List[dict]) -> Dict[str, int]:
    out = {s: 0 for s in STATES}
    for i in items:
        out[i["status"]] += 1
    return out


def submit_problems(target: Path, task: dict) -> List[str]:
    """C-grade submit (TC-HTL-15, reviewer decision 2026-11-07): a record for one of the
    task's requirements, and none of them still PROPOSED."""
    try:
        data = load(target)
    except CeError as exc:
        return [f"{CE_REL} is not valid ({exc})"]
    reqs = task["requirements"]
    mine = for_requirements(data, reqs) if reqs else list(data["items"])
    if not mine:
        return [
            f"grade C needs a counterexample record for {', '.join(reqs) or 'the task'}; "
            "follow counterexample-hunter and kit ce add"
        ]
    open_ids = [i["id"] for i in mine if i["status"] == PROPOSED]
    if open_ids:
        return [
            f"counterexample(s) still PROPOSED: {', '.join(open_ids)} "
            "(kit ce accept, reject or needs-spec)"
        ]
    return []
