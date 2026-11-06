"""P1-T3: record install snapshots of the current kit (offline only).

Usage: python snapshot.py <kit_root> <out_dir>
Each case runs `python -I run_kit.py ...` in a fresh temp workspace with HOME redirected.
Normalisation: target path -> <TARGET>, kit path -> <KIT>, timestamps YYYYmmdd-HHMMSS -> <STAMP>,
.kit/logs/* excluded from the tree (content is the masked report).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
PROFILES = ["core", "python", "data", "web", "full"]
MODES = {"default": [], "dry-run": ["--dry-run"], "verify-only": ["--verify-only"],
         "no-mcp": ["--no-mcp"]}
STAMP = re.compile(r"\d{8}-\d{6}")


def norm(text: str, target: Path) -> str:
    for p in {str(target), str(target.resolve()), target.as_posix()}:
        text = text.replace(p, "<TARGET>")
    text = text.replace(str(KIT), "<KIT>")
    return STAMP.sub("<STAMP>", text)


def tree(root: Path) -> dict[str, str]:
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(".kit/logs/"):
            out[STAMP.sub("<STAMP>", rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def run(target: Path, args: list[str], home: Path) -> tuple[int, str, str]:
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    proc = subprocess.run([sys.executable, "-I", str(KIT / "run_kit.py"), *args],
                          cwd=target, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    return proc.returncode, proc.stdout, proc.stderr


def case(name: str, steps, setup=None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        target = Path(tmp) / "ws"
        target.mkdir()
        if setup:
            setup(target)
        results = []
        for args in steps:
            code, out, err = run(target, args, home)
            results.append({"args": args, "exit": code, "stdout": norm(out, target),
                            "stderr": norm(err, target)})
        record = {"case": name, "runs": results, "tree": tree(target),
                  "home_untouched": not any(home.rglob("*"))}
    (OUT / f"{name}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    return record


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for prof in PROFILES:
        for mode, extra in MODES.items():
            r = case(f"{prof}__{mode}", [["--profile", prof, "--offline", *extra]])
            rows.append((r["case"], [x["exit"] for x in r["runs"]], len(r["tree"]),
                         r["home_untouched"]))
    base = ["--profile", "python", "--offline"]
    r = case("python__rerun-x3", [base, base, base])
    rows.append((r["case"], [x["exit"] for x in r["runs"]], len(r["tree"]), r["home_untouched"]))

    def user_agents(t: Path):
        (t / "AGENTS.md").write_text("# My rules\n\nkeep me\n", encoding="utf-8")
    r = case("core__existing-agents-md", [["--offline"]], user_agents)
    rows.append((r["case"], [x["exit"] for x in r["runs"]], len(r["tree"]), r["home_untouched"]))

    def edited_block(t: Path):
        body = (KIT / "AGENTS.md").read_text(encoding="utf-8").strip()
        (t / "AGENTS.md").write_text(
            f"<!-- hackathon-kit:begin -->\n{body}\n- user edit\n<!-- hackathon-kit:end -->\n",
            encoding="utf-8")
    r = case("core__conflict-edited-block", [["--offline"]], edited_block)
    rows.append((r["case"], [x["exit"] for x in r["runs"]], len(r["tree"]), r["home_untouched"]))

    r = case("self-target", [["--offline", "--target", str(KIT)]])
    rows.append((r["case"], [x["exit"] for x in r["runs"]], len(r["tree"]), r["home_untouched"]))

    lines = ["| case | exit codes | files in tree | HOME untouched |", "|---|---|---|---|"]
    lines += [f"| {c} | {e} | {n} | {h} |" for c, e, n, h in rows]
    (OUT / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


main()
