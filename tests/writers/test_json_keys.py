"""P3-T3 JSON key ownership (ADR-005, REQ-SAFE-001/003). TC-WRT-02."""

from __future__ import annotations

import json

import pytest

from kit.model import Outcome
from kit.writers.json_keys import (
    JsonKeyError,
    detect_format,
    parse_pointer,
    plan_merge,
    plan_remove,
    value_hash,
)

SEQ = {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@1.0.0"]}
USER_FILE = (
    '{\n    "mcpServers": {\n        "mine": {"command": "my-server"}\n    },\n'
    '    "zeta": 1,\n    "alpha": [1, 2]\n}\n'
)


def test_pointer_parsing_and_escapes():
    assert parse_pointer("/a/b~1c/d~0e") == ["a", "b/c", "d~e"]
    with pytest.raises(JsonKeyError):
        parse_pointer("a/b")


def test_creates_new_file_with_kit_key():
    plan = plan_merge(None, {"/mcpServers/seq": SEQ})
    assert plan.outcome == Outcome.CREATE
    assert json.loads(plan.text) == {"mcpServers": {"seq": SEQ}}
    assert plan.records == {"/mcpServers/seq": value_hash(SEQ)}
    assert plan.text.endswith("\n")


def test_user_keys_order_indent_preserved():
    plan = plan_merge(USER_FILE, {"/mcpServers/seq": SEQ})
    assert plan.outcome == Outcome.UPDATE
    doc = json.loads(plan.text)
    assert list(doc) == ["mcpServers", "zeta", "alpha"]
    assert list(doc["mcpServers"]) == ["mine", "seq"]
    assert doc["mcpServers"]["mine"] == {"command": "my-server"}
    assert plan.text.startswith('{\n    "mcpServers"')  # 4-space indent kept


def test_crlf_and_tab_indent_detected():
    assert detect_format('{\r\n\t"a": 1\r\n}\r\n') == ("\t", "\r\n")
    plan = plan_merge('{\r\n\t"a": 1\r\n}\r\n', {"/b": 2})
    assert plan.text == '{\r\n\t"a": 1,\r\n\t"b": 2\r\n}\r\n'


def test_rerun_is_unchanged():
    first = plan_merge(USER_FILE, {"/mcpServers/seq": SEQ})
    second = plan_merge(first.text, {"/mcpServers/seq": SEQ}, first.records)
    assert second.outcome == Outcome.UNCHANGED and second.text is None


def test_existing_user_key_is_conflict_and_nothing_written():
    plan = plan_merge(USER_FILE, {"/mcpServers/mine": SEQ})
    assert plan.outcome == Outcome.CONFLICT and plan.text is None
    assert "not owned" in plan.detail


def test_kit_key_edited_by_user_is_conflict():
    first = plan_merge(None, {"/mcpServers/seq": SEQ})
    edited = first.text.replace("npx", "my-npx")
    plan = plan_merge(edited, {"/mcpServers/seq": {**SEQ, "args": ["new"]}}, first.records)
    assert plan.outcome == Outcome.CONFLICT and plan.text is None


def test_kit_key_updated_when_hash_matches():
    first = plan_merge(None, {"/mcpServers/seq": SEQ})
    newer = {**SEQ, "args": ["-y", "pkg@2.0.0"]}
    plan = plan_merge(first.text, {"/mcpServers/seq": newer}, first.records)
    assert plan.outcome == Outcome.UPDATE
    assert json.loads(plan.text)["mcpServers"]["seq"] == newer


@pytest.mark.parametrize("bad", ["{not json", "[1, 2]", '"text"'])
def test_broken_or_non_object_json_blocks_without_writing(bad):
    plan = plan_merge(bad, {"/a": 1})
    assert plan.outcome == Outcome.CONFLICT and plan.text is None


def test_parent_that_is_not_an_object_is_conflict():
    plan = plan_merge('{"mcpServers": []}', {"/mcpServers/seq": SEQ})
    assert plan.outcome == Outcome.CONFLICT and plan.text is None


def test_array_elements_owned_individually():
    user = '{"permissions": {"allow": ["Bash(git status)"]}}'
    first = plan_merge(user, elements={"/permissions/allow": ["Bash(pytest)", "Bash(git status)"]})
    allow = json.loads(first.text)["permissions"]["allow"]
    assert allow == ["Bash(git status)", "Bash(pytest)"]
    # the user's identical element is not claimed by the kit
    assert first.element_records == {"/permissions/allow": [value_hash("Bash(pytest)")]}
    removed = plan_remove(first.text, {}, first.element_records)
    assert json.loads(removed.text)["permissions"]["allow"] == ["Bash(git status)"]


def test_stale_kit_element_dropped_on_update():
    first = plan_merge(None, elements={"/allow": ["a", "b"]})
    second = plan_merge(
        first.text, elements={"/allow": ["a"]}, recorded_elements=first.element_records
    )
    assert json.loads(second.text)["allow"] == ["a"]


def test_remove_only_unmodified_kit_keys():
    first = plan_merge(USER_FILE, {"/mcpServers/seq": SEQ, "/kitFlag": True})
    edited = json.loads(first.text)
    edited["kitFlag"] = False  # user changed a kit key
    text = json.dumps(edited, indent=4) + "\n"
    removed = plan_remove(text, first.records)
    doc = json.loads(removed.text)
    assert "seq" not in doc["mcpServers"] and doc["mcpServers"]["mine"]
    assert doc["kitFlag"] is False
    assert removed.conflicts == ["/kitFlag"]
    assert removed.outcome == Outcome.UPDATE


def test_remove_on_missing_file_is_unchanged():
    assert plan_remove(None, {"/a": value_hash(1)}).outcome == Outcome.UNCHANGED
