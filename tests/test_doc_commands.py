"""P7-T1 (00_PROMPT 12): every command in the user guides' code blocks was run.

devtools/run_doc_commands.py runs the commands and writes the record
docs/v2/regression/P7-T1-doc-commands.md. This test reads the code blocks of the guides and
README and fails when a command there is not in the record (rerun the script
after changing a guide), or when the record has a command whose exit code was not expected.
Commands the guides mark as not run (미검증) are listed in UNVERIFIED.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import KIT_ROOT

GUIDES = [
    "INSTALL.md",
    "CODEX.md",
    "CLAUDE_CODE.md",
    "HITL_WORKFLOW.md",
    "MIGRATION_V1_TO_V2.md",
    "EXAM_V1.md",
]
RECORD = KIT_ROOT / "docs" / "v2" / "regression" / "P7-T1-doc-commands.md"
KIT_URL = "https://github.com/kimcheolhui9846/skill_kit_kch"
PS_ONE_LINE = (
    r"""$k='..\skill_kit_kch'; if (Test-Path "$k\.git") { git -C $k pull --ff-only } """
    """elseif (Test-Path $k) { Write-Error "$k 폴더가 있지만 git 저장소가 아닙니다. """
    f"""지우거나 옮긴 뒤 다시 실행하세요." }} else {{ git clone --depth 1 {KIT_URL}.git $k }}; """
    "if ($? -and $LASTEXITCODE -eq 0) "
)
SH_ONE_LINE = (
    'k=../skill_kit_kch; if [ -d "$k/.git" ]; then git -C "$k" pull --ff-only; '
    'elif [ -e "$k" ]; then echo "$k 폴더가 있지만 git 저장소가 아닙니다.{advice}" '
    f'>&2; false; else git clone --depth 1 {KIT_URL}.git "$k"; fi && bash "$k/bootstrap.sh"'
)
UNVERIFIED = {
    # Public clone uses the network. INSTALL.md carries the note for README's clone.
    f"git clone {KIT_URL}.git": "INSTALL.md",
    "kit install --agent both --scope user --yes": "INSTALL.md",
    PS_ONE_LINE + r'{ powershell -NoProfile -ExecutionPolicy Bypass -File "$k\bootstrap.ps1"'
    " install --agent both }": "INSTALL.md",
    SH_ONE_LINE.format(advice=" 지우거나 옮긴 뒤 다시 실행하세요.")
    + " install --agent both": "INSTALL.md",
    PS_ONE_LINE + r'{ & "$k\bootstrap.ps1" }': "EXAM_V1.md",
    SH_ONE_LINE.format(advice=""): "EXAM_V1.md",
    rf"git clone {KIT_URL} C:\kit": "EXAM_V1.md",
    r"function kit { python C:\kit\run_kit.py @args }": "EXAM_V1.md",
    r"function kit-update { git -C C:\kit pull --ff-only }": "EXAM_V1.md",
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
    found += [("README.md", cmd) for cmd in _blocks(readme)]
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
    documented = {cmd for _, cmd in _documented()}
    for cmd, guide in UNVERIFIED.items():
        assert cmd in documented
        assert "미검증" in (KIT_ROOT / "docs" / "guides" / guide).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "docs/guides/INSTALL.md",
        "docs/guides/EXAM_V1.md",
        "docs/guides/DEVELOPMENT.md",
        "docs/guides/MIGRATION_V1_TO_V2.md",
        "user/workflow/README.md",
    ],
)
def test_quick_start_guide_links_exist(path):
    doc = KIT_ROOT / path
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
        if "://" not in link:
            assert (doc.parent / link.split("#", 1)[0]).exists(), (path, link)
