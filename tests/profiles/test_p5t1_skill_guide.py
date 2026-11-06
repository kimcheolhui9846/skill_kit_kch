"""P5-T1: the standard policy says when to use which skill (00_PROMPT §10.1, REQ-POL-001).

The guide names skills by hand, so these tests keep it honest: every name is a real catalog
skill, and every profile installs every named skill with --policy standard, for both agents.
"""

from __future__ import annotations

import io
import json
import re

import pytest

from kit import catalog, commands, policy_render, profile_resolver
from kit.adapters import registry
from kit.model import EXIT_READY
from tests.conftest import KIT_ROOT

GUIDE = KIT_ROOT / policy_render.POLICY_DIR / "skills.md"
HEADING = "## When to use which skill"
NAME = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b")


def guide_skills() -> list:
    text = GUIDE.read_text(encoding="utf-8")
    known = set(catalog.load(KIT_ROOT, "standard"))
    return sorted({w for w in NAME.findall(text) if w in known})


def installed(profile: str, agent: str, workspace) -> set:
    out = io.StringIO()
    argv = ["plan", "--agent", agent, "--profile", profile, "--policy", "standard", "--offline"]
    code = commands.run(argv + ["--json"], workspace, KIT_ROOT, out)
    assert code == EXIT_READY, out.getvalue()
    root = registry.get(agent).skill_root + "/"
    changes = json.loads(out.getvalue())["agents"][agent]["changes"]
    return {c["path"][len(root) :].split("/")[0] for c in changes if c["path"].startswith(root)}


def test_guide_is_rendered_once_in_both_agents_and_not_in_restricted():
    texts = {
        a: policy_render.render(KIT_ROOT, "standard", registry.get(a)) for a in ("codex", "claude")
    }
    for text in texts.values():
        assert text.count(HEADING) == 1
        assert text.index("## Light path") < text.index(HEADING) < text.index("## Approval")
    guide = GUIDE.read_text(encoding="utf-8")
    assert all(guide in text for text in texts.values())
    restricted = policy_render.render(KIT_ROOT, "restricted", registry.get("codex"))
    assert HEADING not in restricted


def test_every_hyphenated_word_in_the_guide_is_a_skill():
    """A typo in a skill name would otherwise pass silently."""
    known = set(catalog.load(KIT_ROOT, "standard"))
    text = GUIDE.read_text(encoding="utf-8")
    words = {w for w in NAME.findall(text) if "-" in w}
    assert words - known == set()
    assert len(guide_skills()) == 15  # +task-approval (P5-T2)


@pytest.mark.parametrize(
    "profile", [n for n, kind in profile_resolver.list_entries(KIT_ROOT) if kind == "profile"]
)
@pytest.mark.parametrize("agent", ["codex", "claude"])
def test_every_profile_installs_every_skill_the_guide_names(profile, agent, workspace):
    missing = set(guide_skills()) - installed(profile, agent, workspace)
    assert missing == set(), f"{profile}/{agent}: the policy names skills it does not install"


def test_standard_policy_stays_short():
    """§10.1: details live in the skills; the policy only says when."""
    text = policy_render.render(KIT_ROOT, "standard", registry.get("codex"))
    assert len(text.encode("utf-8")) < 4 * 1024
    assert len(GUIDE.read_text(encoding="utf-8").splitlines()) <= 12
