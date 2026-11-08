"""Regenerate docs/examples/*.log from real kit runs in temporary workspaces. No network.

install/rerun/failure/offline/conflict are the legacy installer (`bootstrap` with no command).
v2-* are the new commands (`kit install --agent ...`, task, recover), run with HOME pointed at
an empty temporary folder.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kit.app import run  # noqa: E402

OUT = ROOT / "docs" / "examples"


def _run(target: Path, *argv: str) -> str:
    out = io.StringIO()
    code = run(["--target", str(target), *argv], cwd=target, out=out)
    text = out.getvalue()
    for path in {str(target), str(target.resolve())}:
        text = text.replace(path, "<target>")
    text = text.replace(str(Path.home()), "<home>")
    return f"$ bootstrap {' '.join(argv)}\n{text}(exit {code})\n"


def _run_v2(target: Path, *argv: str, at_target: bool = True) -> str:
    """A new-path command (`kit <command> ...`, ADR-002). The command comes first."""
    out = io.StringIO()
    args = [*argv, "--target", str(target)] if at_target else list(argv)
    code = run(args, cwd=target, out=out)
    text = out.getvalue()
    for path in {str(target), str(target.resolve())}:
        text = text.replace(path, "<target>")
    text = text.replace(str(Path.home()), "<home>")
    return f"$ kit {' '.join(argv)}\n{text}(exit {code})\n"


def _hitl(ws: Path) -> str:
    """Two tasks, a refused submit, an approval recorded by the agent, then recover."""
    log = [_run_v2(ws, "req", "add", "REQ-001", "--text", "parse a CSV line")]
    log.append(_run_v2(ws, "task", "add", "T-1", "--title", "csv parser", "--requires", "REQ-001"))
    log.append(_run_v2(ws, "task", "add", "T-2", "--title", "report", "--depends-on", "T-1"))
    log.append(_run_v2(ws, "task", "start", "T-1"))
    log.append(_run_v2(ws, "task", "submit", "T-1"))  # refused: no report
    log.append(_run_v2(ws, "task", "report", "T-1"))
    report = ws / ".kit" / "work" / "reports" / "T-1.md"
    text = report.read_text(encoding="utf-8")
    sep = "|---|---|---|---|---|---|---|\n"
    row = "| TC-001 | REQ-001 | normal | 'a,b' | 2 fields | 2 fields | PASS |\n"
    report.write_bytes(text.replace(sep, sep + row, 1).encode("utf-8"))
    log.append(_run_v2(ws, "task", "submit", "T-1"))
    log.append(_run_v2(ws, "task", "start", "T-2"))  # refused: T-1 not approved
    log.append(
        _run_v2(ws, "task", "approve", "T-1", "--by", "agent-recorded", "--evidence", "승인")
    )
    log.append(_run_v2(ws, "task", "status"))
    log.append(_run_v2(ws, "task", "start", "T-2"))
    log.append(_run_v2(ws, "recover", "save", "--note", "report layout half done"))
    log.append(_run_v2(ws, "recover"))  # a new session: approved state and WIP apart
    return "\n".join(log)


def _v2(base: Path) -> dict:
    """New-path examples with HOME pointed at an empty folder (nothing of this PC shows)."""
    home = base / "home"
    home.mkdir()
    saved = {k: os.environ.get(k) for k in HOME_VARS}
    os.environ.update({k: str(home) for k in ("HOME", "USERPROFILE")})
    os.environ["CODEX_HOME"] = str(home / ".codex")
    os.environ["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
    try:
        for name in ("v2-codex", "v2-both", "v2-hitl"):
            (base / name).mkdir()
        logs = {
            "v2-plan": _run_v2(base / "v2-both", "plan", "--agent", "claude"),
            "v2-install-codex": _run_v2(
                base / "v2-codex", "install", "--agent", "codex", "--offline"
            ),
            "v2-install-both": _run_v2(base / "v2-both", "install", "--agent", "both", "--offline"),
            "v2-verify": _run_v2(base / "v2-both", "verify", "--agent", "both", "--offline"),
            "v2-uninstall": _run_v2(base / "v2-both", "uninstall", "--agent", "both"),
            "v2-hitl": _hitl(base / "v2-hitl"),
        }
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return logs


HOME_VARS = ("HOME", "USERPROFILE", "CODEX_HOME", "CLAUDE_CONFIG_DIR")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for name in ("install", "rerun", "failure", "offline", "conflict"):
            (base / name).mkdir()
        logs = {
            "install": _run(base / "install"),
        }
        _run(base / "rerun")
        logs["rerun"] = _run(base / "rerun", "--verbose")
        (base / "failure" / "AGENTS.md").write_text(
            "<!-- hackathon-kit:begin -->\n<!-- hackathon-kit:begin -->\n", encoding="utf-8"
        )
        logs["failure"] = _run(base / "failure")
        logs["offline"] = _run(base / "offline", "--profile", "python", "--offline")
        _run(base / "conflict")
        skill = base / "conflict" / ".agents" / "skills" / "benchmark" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nmy note\n", encoding="utf-8")
        logs["conflict"] = _run(base / "conflict")
        logs.update(_v2(base))
    for name, text in logs.items():
        (OUT / f"{name}.log").write_bytes(text.encode("utf-8"))
        print(f"wrote docs/examples/{name}.log")


if __name__ == "__main__":
    main()
