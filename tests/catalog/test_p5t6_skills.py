"""P5-T6 (00_PROMPT 10.6, REQ-ALGO-001, REQ-DATA-001, Q7).

TC-SKL-03 the standard algorithm-options overlay has the eight review items and a report
template; restricted keeps the original. TC-SKL-04 data-quality-validator: frontmatter, the
eight checks and "never drop by default"; its helper script on a small CSV with missing values,
duplicates and outliers (reviewer decisions 2026-11-07: core pack, standard library script).
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
from pathlib import Path

import pytest

from kit import catalog, commands
from kit.model import EXIT_READY
from kit.skill_check import check as skill_check
from tests.conftest import KIT_ROOT, tree_digest

SKILL_DIR = KIT_ROOT / "shared/skills/data-quality-validator"
SCRIPT = SKILL_DIR / "scripts/profile_csv.py"

CSV = """id,age,city,joined,score
1,34,Seoul,2024-01-02,0.5
2,,Busan,2024-01-03,0.7
3,29,Seoul,2024/01/04,0.6
4,31,NA,2024-01-05,0.55
5,thirty,Seoul,2024-01-06,0.65
5,40,Daegu,2024-01-07,0.6
6,33,Seoul,2024-01-08,9.9
7,35,Seoul,2024-01-09,0.58
7,35,Seoul,2024-01-09,0.58
8,30,Seoul,not a date,0.62
9,28
"""


def install(ws: Path, *argv):
    out = io.StringIO()
    code = commands.run(["install", *argv, "--offline", "--target", str(ws)], ws, KIT_ROOT, out)
    return code, out.getvalue()


# ---------------------------------------------------------------- TC-SKL-03


def test_standard_algorithm_options_has_the_review_and_restricted_does_not(tmp_path):
    original = (KIT_ROOT / ".agents/skills/algorithm-options/SKILL.md").read_bytes()
    std, res = tmp_path / "std", tmp_path / "res"
    std.mkdir()
    res.mkdir()
    assert install(std, "--agent", "claude")[0] == EXIT_READY
    assert install(res, "--agent", "codex", "--policy", "restricted")[0] == EXIT_READY
    text = (std / ".claude/skills/algorithm-options/SKILL.md").read_text(encoding="utf-8")
    assert text.startswith(original.decode("utf-8").rstrip("\n"))
    items = re.findall(r"^\d\. \*\*(.+?)\*\*", text.split("## Kit additions")[1], re.M)
    assert items == [
        "Problem and objective.",
        "Constraints.",
        "Reason for the choice.",
        "Time and space complexity",
        "Two alternatives or more",
        "Expected failure conditions.",
        "How correctness will be checked.",
        "Trade-offs of any optimisation.",
    ]
    assert "### Algorithm decision review" in text and "algorithm-optimizer" in text
    assert (res / ".agents/skills/algorithm-options/SKILL.md").read_bytes() == original
    assert not (res / ".agents/skills/data-quality-validator").exists()  # standard only


# ---------------------------------------------------------------- TC-SKL-04


def test_data_quality_validator_is_a_clean_standard_core_skill(tmp_path):
    files = {
        p.relative_to(SKILL_DIR).as_posix(): p.read_bytes()
        for p in SKILL_DIR.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert set(files) == {"SKILL.md", "scripts/profile_csv.py"}
    for agent in ("codex", "claude"):
        report = skill_check("data-quality-validator", sorted(files.items()), agent)
        assert report.errors == [] and report.warnings == []
    entry = catalog.load(KIT_ROOT, "standard")["data-quality-validator"]
    assert entry.packs == ["core"] and entry.policies == ["standard"]
    text = files["SKILL.md"].decode("utf-8")
    steps = re.findall(r"^\d\. \*\*(.+?)\*\*", text, re.M)
    assert steps == [
        "Profile first, change nothing.",
        "Missing values.",
        "Outliers.",
        "Duplicates.",
        "Type mismatches.",
        "Leakage.",
        "Assumptions of the processing.",
        "Before and after.",
    ]
    for must in (
        "Never drop missing values or outliers by default.",
        "time order",
        "target in disguise",
        "what that may change in the",
        "Limit |",
        "Keep the raw data unchanged",
    ):
        assert must in text, must
    ws = tmp_path / "ws"
    ws.mkdir()
    assert install(ws, "--agent", "codex")[0] == EXIT_READY
    assert (ws / ".agents/skills/data-quality-validator/scripts/profile_csv.py").read_bytes() == (
        SCRIPT.read_bytes()
    )


def test_the_policy_says_when_to_use_it():
    text = (KIT_ROOT / "shared/policies/skills.md").read_text(encoding="utf-8")
    assert "data-quality-validator" in text


# ---------------------------------------------------------------- the helper script


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("profile_csv", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def data(tmp_path):
    p = tmp_path / "data" / "people.csv"
    p.parent.mkdir()
    p.write_bytes(CSV.encode("utf-8"))
    return p


def run(script, capsys, *argv):
    code = script.main([str(a) for a in argv])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_profile_finds_missing_duplicates_outliers_and_mismatches(script, capsys, data):
    before = tree_digest(data.parent)
    code, out, _ = run(script, capsys, data, "--json", "--key", "id")
    assert code == 0
    assert tree_digest(data.parent) == before  # reads only
    p = json.loads(out)
    assert (p["rows"], p["encoding"], p["sampled"]) == (11, "utf-8-sig", False)
    assert (p["ragged"], p["ragged_lines"]) == (1, [12])
    assert p["duplicate_rows"] == 1 and p["duplicate_examples"] == [{"line": 10, "same_as_line": 9}]
    assert p["key"]["keys_with_different_rows"] == 1 and p["key"]["examples"] == ["5"]
    cols = {c["name"]: c for c in p["columns"]}
    assert (cols["age"]["type"], cols["age"]["missing"], cols["age"]["mismatches"]) == ("int", 1, 1)
    assert cols["age"]["mismatch_examples"] == [{"line": 6, "value": "thirty"}]
    assert cols["city"]["missing"] == 2  # "NA" and the short last row
    assert cols["joined"]["type"] == "date" and cols["joined"]["mismatch_examples"] == [
        {"line": 11, "value": "not a date"}
    ]
    assert cols["score"]["type"] == "float"
    assert cols["score"]["outliers"]["count"] == 1 and cols["score"]["outliers"]["examples"] == [
        9.9
    ]
    assert (cols["score"]["min"], cols["score"]["max"]) == (0.5, 9.9)
    assert cols["id"]["outliers"]["count"] == 0
    assert "outliers" not in cols["city"]


def test_markdown_report(script, capsys, data):
    code, out, _ = run(script, capsys, data, "--key", "id")
    assert code == 0
    assert out.startswith("### Data profile: people.csv")
    assert "- Exact duplicate rows: 1 (line 10 = line 9)" in out
    assert "- Rows with a wrong number of fields: 1 (lines 12)" in out
    assert "- Key id: 1 value(s) with different rows (5)" in out
    assert "| age | int | 1 | 9 | 1 (line 6: 'thirty') | 28 | 40 | 0 outside [22.5, 42.5] |" in out
    assert (
        "| score | float | 1 | 8 | 0 | 0.5 | 9.9 | 1 outside [0.48625, 0.73625]: 9.9 |" in out
        and ": 9.9 |" in out
    )
    assert "candidates for a decision with a reason, not rows to delete" in out


def test_cp949_and_sampling(script, capsys, tmp_path):
    p = tmp_path / "kr.csv"
    p.write_bytes("이름,나이\n홍길동,30\n김철수,\n이영희,25\n".encode("cp949"))
    code, out, _ = run(script, capsys, p, "--json", "--max-rows", "2")
    payload = json.loads(out)
    assert code == 0 and payload["encoding"] == "cp949"
    assert payload["header"] == ["이름", "나이"]
    assert (payload["rows"], payload["profiled_rows"], payload["sampled"]) == (3, 2, True)
    code, out, _ = run(script, capsys, p, "--max-rows", "2")
    assert "Rows: 3 (profiled the first 2)" in out


def test_empty_file_and_semicolons(script, capsys, tmp_path):
    empty = tmp_path / "e.csv"
    empty.write_bytes(b"")
    code, out, _ = run(script, capsys, empty)
    assert code == 0 and "Rows: 0. Columns: 0." in out
    semi = tmp_path / "s.csv"
    semi.write_bytes(b"a;b\n1;2\n3;x\n")
    code, out, _ = run(script, capsys, semi, "--delimiter", ";", "--json")
    cols = json.loads(out)["columns"]
    assert [c["name"] for c in cols] == ["a", "b"] and cols[1]["mismatches"] == 1


@pytest.mark.parametrize(
    "argv, code, message",
    [
        (["missing.csv"], 2, "cannot read"),
        (["{data}", "--key", "nope"], 64, "--key nope is not a column"),
        (["{data}", "--encoding", "ascii"], 2, "cannot decode people.csv as ascii"),
        (["{data}", "--encoding", "no-such-codec"], 2, "unknown encoding"),
        (["{data}", "--max-rows", "0"], 64, "--max-rows must be 1 or more"),
        (["{data}", "--delimiter", ";;"], 64, "one character"),
        (["{data}", "--max-rows", "x"], 64, ""),
    ],
)
def test_errors(script, capsys, data, tmp_path, argv, code, message):
    data.write_bytes(CSV.replace("Seoul", "Séoul").encode("utf-8"))
    argv = [
        str(data) if a == "{data}" else str(tmp_path / a) if a.endswith(".csv") else a for a in argv
    ]
    got, _, err = run(script, capsys, *argv)
    assert got == code and message in err


def test_mixed_numbers_low_outliers_and_too_few_values(script, capsys, tmp_path):
    p = tmp_path / "m.csv"
    p.write_bytes(b"x,few\n1,1\n2.5,2\n3,3\n4,\n5,\n-100,\n")  # 5 ints, 1 float
    code, out, _ = run(script, capsys, p, "--json")
    cols = {c["name"]: c for c in json.loads(out)["columns"]}
    assert (cols["x"]["type"], cols["x"]["mismatches"]) == ("float", 0)  # ints fit a float column
    assert cols["x"]["outliers"]["count"] == 1 and cols["x"]["outliers"]["examples"] == [-100.0]
    assert cols["few"]["outliers"] is None  # fewer than 4 values: no IQR rule


def test_bytecode_next_to_a_bundled_script_is_never_installed(kit, workspace):
    """Running scripts/profile_csv.py inside the kit leaves __pycache__ behind."""
    scripts = kit / "shared/skills/data-quality-validator/scripts"
    (scripts / "__pycache__").mkdir(exist_ok=True)
    (scripts / "__pycache__" / "profile_csv.cpython-312.pyc").write_bytes(b"\x00pyc")
    (scripts / "stray.pyc").write_bytes(b"\x00pyc")
    out = io.StringIO()
    code = commands.run(
        ["install", "--agent", "codex", "--offline", "--target", str(workspace)],
        workspace,
        kit,
        out,
    )
    assert code == EXIT_READY, out.getvalue()
    installed = workspace / ".agents/skills/data-quality-validator"
    assert sorted(
        p.relative_to(installed).as_posix() for p in installed.rglob("*") if p.is_file()
    ) == ["SKILL.md", "scripts/profile_csv.py"]
