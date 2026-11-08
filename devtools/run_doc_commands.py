"""Run every command the user guides show and record the result (P7-T1, 00_PROMPT 12).

    uv run python devtools/run_doc_commands.py

Writes docs/v2/regression/P7-T1-doc-commands.md. Every kit call is a fresh
`python -I run_kit.py ...` process with no terminal and HOME pointed at a temporary folder,
in temporary workspaces; nothing outside them is written and the network is not used (the
commands that would use it are run with --offline or --dry-run, or are marked unverified in the
guides). Paths in the record are shown as <ws>, <home> and <kit>.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "v2" / "regression" / "P7-T1-doc-commands.md"
WINDOWS = os.name == "nt"

CALC = """def add(a, b):
    return a + b


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("b is 0")
    return a / b
"""
TEST_CALC = """import pytest

from calc import add, div


def test_add():
    assert add(2, 3) == 5


def test_div_by_zero():
    with pytest.raises(ZeroDivisionError):
        div(1, 0)
"""
BRIEF = "# Brief\n\n## Requirements\n- REQ-004 (should): report the median\n"


class Runner:
    def __init__(self, base: Path):
        self.base = base
        self.home = base / "home"
        self.home.mkdir()
        self.env = dict(os.environ)
        self.env.update({"HOME": str(self.home), "USERPROFILE": str(self.home)})
        self.env["CODEX_HOME"] = str(self.home / ".codex")
        self.env["CLAUDE_CONFIG_DIR"] = str(self.home / ".claude")
        self.rows: List[tuple] = []
        self.ws: Optional[Path] = None

    def workspace(self, name: str) -> Path:
        self.ws = self.base / name
        self.ws.mkdir()
        return self.ws

    def _clean(self, text: str) -> str:
        pairs = [(self.ws, "<ws>"), (self.home, "<home>"), (ROOT, "<kit>"), (self.base, "<tmp>")]
        for path, label in pairs:
            if path is None:
                continue
            for form in {str(path), str(path.resolve()), path.as_posix()}:
                text = text.replace(form, label)
        return text

    def _run(self, doc: str, shown: str, argv: List[str], expect: int) -> str:
        proc = subprocess.run(
            argv,
            cwd=str(self.ws),
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=600,
        )
        out = proc.stdout.decode("utf-8", "replace")
        status = next(
            (ln.split(":", 1)[1].strip() for ln in out.splitlines() if ln.startswith("Status:")),
            "",
        )
        if not status and proc.returncode == 64:
            status = "usage error"
        self.rows.append((doc, shown, expect, proc.returncode, status))
        return out

    def kit(self, doc: str, args: str, expect: int = 0, extra: Optional[List[str]] = None):
        argv = [sys.executable, "-I", str(ROOT / "run_kit.py"), *split(args), *(extra or [])]
        return self._run(doc, f"kit {args}", argv, expect)

    def shell(self, doc: str, shown: str, argv: List[str], expect: int = 0) -> str:
        return self._run(doc, shown, argv, expect)


def split(args: str) -> List[str]:
    import shlex

    return shlex.split(args, posix=True)


def install_docs(r: Runner) -> None:
    d = "INSTALL.md"
    r.workspace("plan")
    r.kit(d, "plan --agent both")
    r.kit(d, "install --agent both --dry-run")
    for agent in ("codex", "claude", "both"):
        r.workspace(f"install-{agent}")
        r.kit(d, f"install --agent {agent}", extra=["--offline"])
    r.kit(d, "verify --agent both")
    r.kit(d, "update --agent both --dry-run")
    r.kit(d, "update --agent both")
    r.kit(d, "uninstall --agent both --dry-run")
    r.kit(d, "uninstall --agent both")
    ws = r.workspace("restore")
    (ws / "AGENTS.md").write_bytes(b"# my rules\n")
    r.kit(d, "install --agent codex --offline")
    stamp = sorted(p.name for p in (ws / ".kit" / "backups").iterdir())[0]
    r.kit(d, f"restore --backup {stamp} --dry-run")
    r.kit(d, f"restore --backup {stamp}")
    r.kit(d, f"restore --agent codex --backup {stamp}", expect=64)
    r.workspace("offline")
    r.kit(d, "install --agent both --offline")
    r.kit(d, "doctor")
    r.kit(d, "profiles list")
    r.kit(d, "profiles show hackathon --agent codex")
    r.kit(d, "version")
    r.workspace("user")
    r.kit(d, "install --agent both --scope user --dry-run")
    r.kit(d, "install --agent both --scope user", expect=64)
    r.workspace("bootstrap-sh")
    bash = shutil.which("bash")
    if bash:
        r.shell(
            d,
            "bash <kit>/bootstrap.sh install --agent both --offline",
            [bash, (ROOT / "bootstrap.sh").as_posix(), "install", "--agent", "both", "--offline"],
        )
    if WINDOWS:
        r.workspace("bootstrap-ps1")
        ps1 = str(ROOT / "bootstrap.ps1")
        r.shell(
            d,
            "powershell -ExecutionPolicy Bypass -File <kit>\\bootstrap.ps1 install --agent both"
            " --offline",
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1]
            + ["install", "--agent", "both", "--offline"],
        )


def agent_docs(r: Runner) -> None:
    d = "CODEX.md"
    r.workspace("codex-1")
    r.kit(d, "install --agent codex", extra=["--offline"])
    r.workspace("codex-2")
    r.kit(d, "install --agent codex --policy restricted", extra=["--offline"])
    r.workspace("codex-3")
    r.kit(d, "install --agent codex --mcp context7 --hooks", extra=["--offline"])
    r.kit(d, "install --agent codex --scope user --dry-run")
    d = "CLAUDE_CODE.md"
    r.workspace("claude-1")
    r.kit(d, "install --agent claude", extra=["--offline"])
    r.workspace("claude-2")
    r.kit(d, "install --agent claude --mcp context7 --hooks", extra=["--offline"])
    r.kit(d, "install --agent claude --scope user --dry-run")
    r.kit(d, "install --agent claude --scope user --hooks --dry-run", expect=64)
    r.kit(d, "install --agent claude --scope user --plugin security-guidance --dry-run", expect=64)
    r.workspace("claude-3")
    r.kit(d, "install --agent claude --plugin security-guidance --dry-run")
    r.workspace("claude-4")
    r.kit(d, "install --agent claude --hooks", extra=["--offline"])
    r.kit(d, "uninstall --agent claude")


def hitl_doc(r: Runner) -> None:
    d = "HITL_WORKFLOW.md"
    ws = r.workspace("hitl")
    (ws / "calc.py").write_bytes(CALC.encode())
    (ws / "tests").mkdir()
    (ws / "tests" / "test_calc.py").write_bytes(TEST_CALC.encode())
    (ws / "pytest.ini").write_bytes(b"[pytest]\n")
    (ws / "TASK_BRIEF.md").write_bytes(BRIEF.encode())
    r.kit(d, 'req add REQ-001 --text "add returns the sum"')
    r.kit(d, 'req add REQ-002 --text "div refuses a zero divisor"')
    r.kit(d, 'req add REQ-003 --text "mean of a list" --priority should')
    r.kit(d, 'task add T-1 --title "calc" --requires REQ-001 --requires REQ-002')
    r.kit(d, 'task add T-2 --title "stats" --requires REQ-003 --depends-on T-1')
    r.kit(d, "task status")
    r.kit(d, "req sync --brief TASK_BRIEF.md")
    r.kit(d, "task start T-1")
    r.kit(d, 'task subtask add T-1 "zero divisor"')
    r.kit(d, "task subtask done T-1.1")
    r.kit(d, "task submit T-1", expect=2)  # no report yet
    r.kit(d, "task report T-1")
    r.kit(d, "task submit T-1", expect=2)  # the template has no test rows
    loc = "tests/test_calc.py::"
    r.kit(d, f"trace link TC-001 --req REQ-001 --locator {loc}test_add --case normal")
    r.kit(d, f"trace link TC-002 --req REQ-002 --locator {loc}test_div_by_zero --case error")
    r.shell(
        d,
        "python -m pytest --junitxml=out/junit.xml",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--junitxml=out/junit.xml",
        ],
    )
    r.kit(d, "report tests --junit out/junit.xml --out .kit/work/reports/T-1-tests.md", expect=1)
    r.kit(d, "trace check", expect=1)
    table = (ws / ".kit/work/reports/T-1-tests.md").read_text(encoding="utf-8")
    rows = "".join(ln + "\n" for ln in table.splitlines() if ln.startswith("| TC-"))
    report = ws / ".kit/work/reports/T-1.md"
    sep = "|---|---|---|---|---|---|---|\n"
    report.write_bytes(report.read_text(encoding="utf-8").replace(sep, sep + rows, 1).encode())
    r.kit(
        d,
        "ce add CE-001 --function div --req REQ-002 --category boundary --origin black-box"
        ' --assumption "the divisor is never zero" --input "div(1, 0)"'
        ' --would-catch "a ZeroDivisionError leak" --expected "ZeroDivisionError"',
    )
    r.kit(d, "ce accept CE-001")
    r.kit(d, "ce convert CE-001 --test TC-002")
    r.kit(d, 'ce result CE-001 --result "PASS (TC-002)"')
    r.kit(
        d,
        "ce add CE-002 --function div --req REQ-002 --category type --origin black-box"
        ' --assumption "the divisor is a number" --input "div(1, None)"'
        ' --would-catch "a TypeError leak"',
    )
    r.kit(d, "ce accept CE-002", expect=2)  # no expected result yet
    r.kit(d, 'ce needs-spec CE-002 --question "what should div(1, None) do?"')
    r.kit(d, 'ce resolve CE-002 --expected "ValueError" --quote "None은 ValueError로"')
    r.kit(d, "ce list")
    r.kit(d, "task submit T-1")
    r.kit(d, 'task request-changes T-1 --reason "add a test for -0.0"')
    r.kit(d, "task start T-1")
    r.kit(d, "task submit T-1")
    r.kit(d, "task approve T-1", expect=2)  # no terminal
    r.kit(d, 'task approve T-1 --by agent-recorded --evidence "승인"')
    r.kit(d, "task start T-2")
    r.kit(d, 'recover save --note "mean() half done" --command "pytest tests" --tests "2 passed"')
    r.kit(d, 'recover decide "use statistics.fmean for floats" --task T-2')
    r.kit(d, "recover")
    r.kit(d, 'req edit REQ-002 --text "div refuses zero and None divisors"')
    r.kit(d, "req impact REQ-002")


def migration_doc(r: Runner) -> None:
    d = "MIGRATION_V1_TO_V2.md"
    ws = r.workspace("v1-a")
    r.kit(d, "--offline")
    r.kit(d, "--profile python --offline --dry-run")
    r.kit(d, "--help")
    r.kit(d, "help")
    r.kit(d, "plan --agent codex --policy restricted --profile core")
    r.kit(d, "verify --agent codex", extra=["--offline"])
    r.kit(d, "doctor")
    r.kit(d, "plan --agent codex --offline")
    r.kit(d, "install --agent codex --offline")
    r.kit(d, "verify --agent codex --offline")
    skills = sorted(p.name for p in (ws / ".agents" / "skills").iterdir())
    assert len(skills) == 17, skills  # install cleans up what v1 wrote (follow-up 3)
    r.kit(d, "uninstall --agent codex")  # 4. going back
    r.kit(d, "--offline")
    ws = r.workspace("v1-b")
    r.kit(d, "--offline")
    r.kit(d, "install --agent codex --policy restricted --profile core", extra=["--offline"])
    r.kit(d, "uninstall --agent codex")
    left = [p for p in (ws / ".agents").rglob("*") if p.is_file()]
    assert left == [], left


def readme(r: Runner) -> None:
    d = "README.md"
    bash = shutil.which("bash")
    for agent in ("codex", "claude", "both"):
        r.workspace(f"readme-{agent}")
        if bash:
            r.shell(
                d,
                f"bash ../skill_kit_kch/bootstrap.sh install --agent {agent} (+ --offline)",
                [bash, (ROOT / "bootstrap.sh").as_posix(), "install", "--agent", agent]
                + ["--offline"],
            )
    if WINDOWS:
        r.workspace("readme-ps1")
        ps1 = str(ROOT / "bootstrap.ps1")
        r.shell(
            d,
            "..\\skill_kit_kch\\bootstrap.ps1 install --agent both (+ --offline)",
            ["powershell", "-NoProfile", "-Command", f"& '{ps1}' install --agent both --offline;"
             " exit $LASTEXITCODE"],
        )  # fmt: skip
        r.workspace("readme-py")
        r.kit(d, "install --agent both", extra=["--offline"])
    r.kit(d, "help")


def write(r: Runner) -> int:
    bad = [row for row in r.rows if row[2] != row[3]]
    lines = [
        "# P7-T1 문서 명령 실행 기록",
        "",
        "<!-- devtools/run_doc_commands.py가 만든다. 손으로 고치지 않는다. -->",
        "",
        f"- 환경: {platform.system()} {platform.release()}, Python {platform.python_version()}",
        "- 방식: 명령마다 새 `python -I run_kit.py` 프로세스, 터미널 없음, 임시 작업 공간과 "
        "임시 HOME(`<home>`), 네트워크 없음. 문서의 설치 명령 중 네트워크를 쓸 수 있는 것은 "
        "`--offline`을 붙여 실행했다.",
        f"- 결과: {len(r.rows)}개 실행, 기대와 다른 종료 코드 {len(bad)}개.",
        "",
        "| 문서 | 명령 | 기대 | 실제 | Status 줄 | 판정 |",
        "|---|---|---|---|---|---|",
    ]
    for doc, shown, expect, code, status in r.rows:
        verdict = "PASS" if expect == code else "FAIL"
        cell = shown.replace("|", "\\|")
        lines.append(f"| {doc} | `{cell}` | {expect} | {code} | {status or '-'} | {verdict} |")
    OUT.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(
        f"wrote {OUT.relative_to(ROOT).as_posix()}: {len(r.rows)} commands, {len(bad)} unexpected"
    )
    for row in bad:
        print("UNEXPECTED", row)
    return 1 if bad else 0


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        r = Runner(Path(tmp))
        readme(r)
        install_docs(r)
        agent_docs(r)
        hitl_doc(r)
        migration_doc(r)
        home_files = [p for p in r.home.rglob("*") if p.is_file()]
        code = write(r)
        if home_files:
            print(f"HOME was written: {len(home_files)} file(s)")
            return 1
        return code


if __name__ == "__main__":
    sys.exit(main())
