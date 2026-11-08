"""Regenerate docs/CATALOG.md from catalog/*.json and real `kit plan` runs. No network.

The skill sets per profile and policy are what `kit plan --json` says it would install (after
the catalog, the policy and the replacements), not the profile files' own lists. Plans run in
a temporary workspace with HOME pointed at an empty temporary folder.
tests/test_catalog_doc.py fails when docs/CATALOG.md is out of date.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kit import commands  # noqa: E402

OUT = ROOT / "docs" / "CATALOG.md"
PROFILES = ("core", "python", "data", "web", "full", "hackathon", "fullstack", "ai-research")
PACK_COMBOS = (
    "core,workflow",
    "core,research",
    "core,eng-patterns",
    "core,lean",
    "core,cloudflare",
    "core,motion",
    "core,planning-extras",
)
POLICIES = ("restricted", "standard")
HOME_VARS = ("HOME", "USERPROFILE", "CODEX_HOME", "CLAUDE_CONFIG_DIR")


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _cell(text) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def _plan(ws: Path, profile: str, policy: str) -> Optional[Dict[str, List[str]]]:
    """Skill names per agent, or None when the kit refuses the combination."""
    out = io.StringIO()
    argv = ["plan", "--agent", "both", "--profile", profile, "--policy", policy]
    code = commands.run([*argv, "--offline", "--json", "--target", str(ws)], ws, ROOT, out)
    if code != 0:
        return None
    agents = json.loads(out.getvalue())["agents"]
    found = {}
    for agent, root in (("codex", ".agents/skills/"), ("claude", ".claude/skills/")):
        names = {
            c["path"][len(root) :].split("/", 1)[0]
            for c in agents[agent]["changes"]
            if c["path"].startswith(root)
        }
        found[agent] = sorted(names)
    return found


def _sets(base: Path) -> Dict[tuple, Optional[Dict[str, List[str]]]]:
    home = base / "home"
    home.mkdir()
    saved = {k: os.environ.get(k) for k in HOME_VARS}
    os.environ.update({"HOME": str(home), "USERPROFILE": str(home)})
    os.environ["CODEX_HOME"] = str(home / ".codex")
    os.environ["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
    try:
        result = {}
        for i, profile in enumerate(PROFILES + PACK_COMBOS):
            for policy in POLICIES:
                ws = base / f"ws{i}-{policy}"
                ws.mkdir()
                result[(profile, policy)] = _plan(ws, profile, policy)
        return result
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _skills(lines: List[str]) -> None:
    skills = _load("catalog/skills.json")["skills"]
    lines += [
        "## 1. 스킬 (`catalog/skills.json`)",
        "",
        f"{len(skills)}개. 출처 `kit`은 이 저장소의 스킬이고, `source:`는 `third_party/`에 고정 "
        "커밋으로 들여온 외부 스킬이다(라이선스는 `THIRD_PARTY_NOTICES.md`, 해시는 "
        "`sources.lock.json`).",
        "",
        "| 스킬 | 출처 | 에이전트 | 팩 | 정책 |",
        "|---|---|---|---|---|",
    ]
    for s in sorted(skills, key=lambda x: x["name"]):
        lines.append(
            f"| `{s['name']}` | {_cell(s.get('origin', '-'))} | {', '.join(s['agents'])} "
            f"| {', '.join(s.get('packs', [])) or '-'} | {', '.join(s['policies'])} |"
        )
    lines.append("")


def _profiles(lines: List[str], sets) -> None:
    lines += [
        "## 2. 프로필별 설치 스킬",
        "",
        "`kit plan --agent both --profile P --policy X --offline --json`이 실제로 설치하겠다고 "
        "한 스킬이다. 정책이 `restricted`이면 standard 전용 스킬이 빠지고, standard에서는 "
        "`tdd-automator`·`submission-validator` 대신 `test-driven-development`·"
        "`verification-before-completion`이 들어간다. restricted에서 standard 전용 팩"
        "(`workflow`, `research`)을 주면 거부하지 않고 그 스킬을 건너뛴다(계획의 "
        "`skipped_skills`에 `not in the restricted policy`로 나온다). `-`는 키트가 그 조합을 "
        "거부한다는 뜻이다.",
        "",
        "| 프로필 | restricted | standard |",
        "|---|---|---|",
    ]
    for profile in PROFILES + PACK_COMBOS:
        cells = []
        for policy in POLICIES:
            found = sets[(profile, policy)]
            if found is None:
                cells.append("-")
            elif found["codex"] == found["claude"]:
                cells.append(str(len(found["codex"])))
            else:
                cells.append(f"Codex {len(found['codex'])} / Claude {len(found['claude'])}")
        lines.append(f"| `{profile}` | {cells[0]} | {cells[1]} |")
    lines += ["", "목록:", ""]
    for profile in PROFILES + PACK_COMBOS:
        for policy in POLICIES:
            found = sets[(profile, policy)]
            if found is None:
                continue
            if found["codex"] == found["claude"]:
                names = ", ".join(found["codex"])
                lines.append(f"- `{profile}` / {policy}: {names}")
            else:
                for agent in ("codex", "claude"):
                    names = ", ".join(found[agent])
                    lines.append(f"- `{profile}` / {policy} / {agent}: {names}")
    lines.append("")


def _mcp(lines: List[str]) -> None:
    servers = _load("catalog/mcp.json")["servers"]
    lines += [
        "## 3. MCP 서버 (`catalog/mcp.json`)",
        "",
        "기본으로 켜진 것만 프로필에 따라 등록된다. 꺼진 서버는 `--mcp NAME`으로 켠다. "
        "버전이 고정되지 않은 서버는 목록에만 있고 켤 수 없다.",
        "",
        "| 서버 | 버전 | 정책 | 위험도 | 기본 | 네트워크 | 꺼진 이유 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in servers.items():
        lines.append(
            f"| `{name}` | {s.get('version', '고정 없음(목록만)')} | {', '.join(s['policies'])} "
            f"| {s['risk']} | {'켜짐' if s['enabled_by_default'] else '꺼짐'} "
            f"| {_cell(s.get('network_egress', '-'))} | {_cell(s.get('disabled_reason') or '-')} |"
        )
    lines.append("")


def _plugins(lines: List[str]) -> None:
    plugins = _load("catalog/plugins.json")["plugins"]
    lines += [
        "## 4. 플러그인 (`catalog/plugins.json`)",
        "",
        "모두 기본으로 꺼져 있다. `--plugin NAME`으로 켜면 선언을 쓰고, 네트워크를 허용하면 "
        "에이전트 CLI로 이 PC에 설치한다.",
        "",
        "| 플러그인 | 에이전트 | 정책 | 위험도 | 라이선스 | 꺼진 이유 |",
        "|---|---|---|---|---|---|",
    ]
    for name, p in plugins.items():
        lines.append(
            f"| `{name}` | {', '.join(p['agents'])} | {', '.join(p['policies'])} | {p['risk']} "
            f"| {p.get('license', '-')} | {_cell(p.get('disabled_reason') or '-')} |"
        )
    lines.append("")


def _manual(lines: List[str]) -> None:
    tools = _load("catalog/manual.json")["tools"]
    lines += [
        "## 5. 수동 도구 (`catalog/manual.json`)",
        "",
        "키트는 실행하지 않는다. `--manual NAME`은 절차와 위험만 출력한다.",
        "",
        "| 도구 | 에이전트 | 정책 | 위험도 | 요약 |",
        "|---|---|---|---|---|",
    ]
    for name, t in tools.items():
        lines.append(
            f"| `{name}` | {', '.join(t['agents'])} | {', '.join(t['policies'])} | {t['risk']} "
            f"| {_cell(t.get('summary', '-'))} |"
        )
    lines.append("")


def render() -> str:
    lines = [
        "# 카탈로그",
        "",
        "<!-- devtools/make_catalog_doc.py가 만든다. 손으로 고치지 않는다. -->",
        "",
        "키트가 설치할 수 있는 스킬, MCP 서버, 플러그인, 수동 도구의 목록이다. "
        "다시 만들려면 `uv run python devtools/make_catalog_doc.py`를 실행한다(네트워크 없음).",
        "",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        sets = _sets(Path(tmp))
    _skills(lines)
    _profiles(lines, sets)
    _mcp(lines)
    _plugins(lines)
    _manual(lines)
    return "\n".join(lines)


def main() -> None:
    OUT.write_bytes(render().encode("utf-8"))
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
