"""P7-T1 (00_PROMPT 12): every command in the user guides' code blocks was run.

devtools/run_doc_commands.py runs the commands and writes the record
docs/v2/regression/P7-T1-doc-commands.md. This test reads the code blocks of the guides and
the v2 part of README and fails when a command there is not in the record (rerun the script
after changing a guide), or when the record has a command whose exit code was not expected.
Commands the guides mark as not run (미검증) are listed in UNVERIFIED.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import KIT_ROOT

GUIDES = ["INSTALL.md", "CODEX.md", "CLAUDE_CODE.md", "HITL_WORKFLOW.md", "MIGRATION_V1_TO_V2.md"]
RECORD = KIT_ROOT / "docs" / "v2" / "regression" / "P7-T1-doc-commands.md"
UNVERIFIED = {
    "git clone --depth 1 https://github.com/kimcheolhui9846/skill_kit_kch ../skill_kit_kch",
    "kit install --agent both --scope user --yes",
}
STAMP = re.compile(r"\b\d{8}-\d{6}(-\d+)?\b")


def _blocks(text: str):
    for block in re.findall(r"```(?:bash|powershell)\n(.*?)```", text, re.S):
        joined = re.sub(r"\\\n\s*", " ", block)
        for line in joined.splitlines():
            line = re.sub(r"\s+#\s.*$", "", line).strip()
            if line:
                yield line


def _norm(cmd: str) -> str:
    cmd = cmd.replace(" (+ --offline)", "").replace("<kit>", "../skill_kit_kch")
    cmd = cmd.replace("\\|", "|")
    return STAMP.sub("<stamp>", re.sub(r"\s+", " ", cmd)).strip()


def _record():
    rows = []
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (\S+) \| `(.*)` \| (\d+) \| (-?\d+) \| .* \| (\w+) \|$", line)
        if m:
            rows.append((m.group(1), _norm(m.group(2)), m.group(3), m.group(4), m.group(5)))
    return rows


def _documented():
    found = []
    for name in GUIDES:
        text = (KIT_ROOT / "docs" / "guides" / name).read_text(encoding="utf-8")
        found += [(name, cmd) for cmd in _blocks(text)]
    readme = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
    v2_part = readme[: readme.index("# 기존 사용자 안내")]
    found += [("README.md", cmd) for cmd in _blocks(v2_part)]
    return found


def test_the_record_is_all_expected_exit_codes():
    rows = _record()
    assert len(rows) >= 90
    assert [r for r in rows if r[4] != "PASS" or r[2] != r[3]] == []


@pytest.mark.parametrize("doc, cmd", _documented())
def test_each_documented_command_was_run(doc, cmd):
    if cmd in UNVERIFIED:
        return
    shown = _norm(cmd)
    run = {r[1] for r in _record() if r[0] == doc}
    assert shown in run, f"{doc}: `{cmd}` is not in {RECORD.name}; rerun run_doc_commands.py"


def test_unverified_commands_are_marked_in_the_guides():
    for cmd in UNVERIFIED:
        holders = [d for d, c in _documented() if c == cmd]
        assert holders, cmd
        for doc in holders:
            path = KIT_ROOT / ("README.md" if doc == "README.md" else f"docs/guides/{doc}")
            assert "미검증" in path.read_text(encoding="utf-8"), doc
