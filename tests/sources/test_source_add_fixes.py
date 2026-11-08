"""`kit source add` follow-up S-1 (2026-11-08): defects found by dry runs on real repositories.
No network: the fake GitHub from test_source_add serves tarballs built in memory."""

from __future__ import annotations

import json
import urllib.error

import pytest

from kit import catalog, github_fetch, sources
from kit import source_add as sa
from kit.model import EXIT_BLOCKED, EXIT_PARTIAL, EXIT_READY
from tests.conftest import tree_digest
from tests.sources.test_source_add import (
    MIT,
    SHA1,
    FakeGitHub,
    make_tar,
    skill,
    src,
)
from tests.userscope.pc_fixture import kit_run

APACHE = "Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/\n"


@pytest.fixture
def gh(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(sa, "make_client", lambda: fake)
    return fake


def plan_json(kit, workspace, *argv):
    code, out = src(kit, workspace, "add", *argv, "--json")
    return code, json.loads(out)


def blocks(data) -> list:
    return [f["text"] for f in data.get("findings", []) if f["level"] == "BLOCK"]


# ---------------------------------------------------------------- 1. multi-line frontmatter


def test_multi_line_descriptions_pass_the_checker(kit, workspace, gh):
    folded = (
        "---\nname: lean-a\ndescription: >\n  Write the smallest correct change and a\n"
        "  reply a busy human understands in one read.\n---\n\n# lean-a\n"
    )
    plain = (
        "---\nname: lean-b\ndescription: Show the measured savings\n"
        "  from the benchmark. One-shot display.\n---\n\n# lean-b\n"
    )
    gh.add(
        "acme/lean",
        {"LICENSE": MIT, "skills/lean-a/SKILL.md": folded, "skills/lean-b/SKILL.md": plain},
    )
    code, data = plan_json(kit, workspace, "acme/lean", "--path", "skills")
    assert code == EXIT_READY, data
    assert blocks(data) == []
    assert sorted(c["name"] for c in data["catalog"]) == ["lean-a", "lean-b"]


# ---------------------------------------------------------------- 2. unpacked size, fallback


def _roomy(gh):
    """A small download that unpacks to more than the (lowered) limit."""
    gh.add(
        "acme/roomy",
        {
            "LICENSE": MIT,
            "skills/ledger-zebra/SKILL.md": skill("ledger-zebra"),
            "data/big.txt": "x" * 5000,  # compresses to almost nothing
        },
    )


def test_unpacked_size_is_exact_at_the_limit():
    data = make_tar("top", {"a.md": "x" * 2000, "b.md": "y" * 1000})
    assert len(sa.unpack(data, limit=3000).files) == 2  # exactly at the limit
    with pytest.raises(sa.ArchiveTooLarge, match="larger than 2999 bytes"):
        sa.unpack(data, limit=2999)
    assert issubclass(sa.ArchiveTooLarge, sa.SourceBlocked)  # still a block for other callers


def test_a_gzip_bomb_is_cut_before_unpacking():
    data = make_tar("top", {"zeros.md": "0" * (1024 * 1024 + 200_000)})
    assert len(data) < 50_000
    with pytest.raises(sa.ArchiveTooLarge, match="larger than 100 bytes"):
        sa.unpack(data, limit=100)


def test_unpacked_over_the_limit_falls_back_to_folders(kit, workspace, gh, monkeypatch):
    _roomy(gh)
    monkeypatch.setattr(sa.unpack, "__defaults__", (3000,))
    code, data = plan_json(kit, workspace, "acme/roomy", "--path", "skills/ledger-zebra")
    assert code == EXIT_READY, data
    assert ("tree", "acme", "roomy", SHA1) in gh.calls  # fetched folder by folder
    fetched = {gh.blobs[c[1]] for c in gh.calls if c[0] == "blob"}
    assert b"x" * 5000 not in fetched
    assert [c["name"] for c in data["catalog"]] == ["ledger-zebra"]


def test_unpacked_over_the_limit_without_path_names_the_option(kit, workspace, gh, monkeypatch):
    _roomy(gh)
    monkeypatch.setattr(sa.unpack, "__defaults__", (3000,))
    code, out = src(kit, workspace, "add", "acme/roomy")
    assert code == EXIT_PARTIAL, out
    assert "archive is larger than 3000 bytes; name the folders with --path" in out
    assert not any(c[0] == "tree" for c in gh.calls)


def test_the_kept_bytes_stay_capped_after_the_fallback(kit, workspace, gh, monkeypatch):
    _roomy(gh)
    monkeypatch.setattr(sa.unpack, "__defaults__", (3000,))
    monkeypatch.setattr(sa.sparse, "__defaults__", (50,))
    code, out = src(kit, workspace, "add", "acme/roomy", "--path", "skills/ledger-zebra")
    assert code == EXIT_PARTIAL, out
    assert "selected files are larger than 50 bytes" in out


# ---------------------------------------------------------------- 3. license per folder


def test_each_folder_keeps_its_own_license(kit, workspace, gh):
    """anthropics/skills: no license at the root, one LICENSE.txt in every skill folder."""
    gh.add(
        "acme/many",
        {
            "README.md": "# skills\n",
            "skills/alpha-zebra/SKILL.md": skill("alpha-zebra"),
            "skills/alpha-zebra/LICENSE.txt": APACHE,
            "skills/beta-zebra/SKILL.md": skill("beta-zebra", "Other yak shaving."),
            "skills/beta-zebra/LICENSE.txt": APACHE,
        },
        spdx=None,
    )
    argv = ["acme/many", "--path", "skills/alpha-zebra", "--path", "skills/beta-zebra"]
    code, data = plan_json(kit, workspace, *argv)
    assert code == EXIT_READY, data
    entry = data["source"]
    assert entry["license"] == "Apache-2.0" and entry["integration"] == "vendored-verbatim"
    base = "third_party/acme-many/skills"
    assert {f"{base}/alpha-zebra/LICENSE.txt", f"{base}/beta-zebra/LICENSE.txt"} <= set(
        entry["files"]
    )
    assert entry["license_file"] in entry["files"]
    assert all("include" not in c for c in data["catalog"])  # the license is in the folder
    code, out = src(kit, workspace, "add", *argv, "--yes")
    assert code == EXIT_READY, out
    assert sources.check(kit) == []
    catalog.load_all(kit)


def test_a_folder_without_a_license_is_not_copied(kit, workspace, gh):
    gh.add(
        "acme/half",
        {
            "skills/alpha-zebra/SKILL.md": skill("alpha-zebra"),
            "skills/alpha-zebra/LICENSE.txt": APACHE,
            "skills/beta-zebra/SKILL.md": skill("beta-zebra", "Other yak shaving."),
        },
        spdx=None,
    )
    code, data = plan_json(
        kit, workspace, "acme/half", "--path", "skills/alpha-zebra", "--path", "skills/beta-zebra"
    )
    assert code == EXIT_READY, data
    assert data["source"]["integration"] == "referenced" and data["source"]["files"] == {}
    note = next(n for n in data["notes"] if "different licenses" in n)
    assert "skills/alpha-zebra: Apache-2.0, skills/beta-zebra: none" in note
    # each folder alone: the licensed one is copied, the other recorded as referenced
    code, data = plan_json(kit, workspace, "acme/half", "--path", "skills/alpha-zebra")
    assert data["source"]["integration"] == "vendored-verbatim", data
    code, data = plan_json(kit, workspace, "acme/half", "--path", "skills/beta-zebra")
    assert data["source"]["integration"] == "referenced", data


def test_a_folder_license_is_not_overruled_by_the_root(kit, workspace, gh):
    """Root MIT, one folder Apache-2.0: copying both as MIT would be wrong."""
    gh.add(
        "acme/mixed",
        {
            "LICENSE": MIT,
            "skills/alpha-zebra/SKILL.md": skill("alpha-zebra"),
            "skills/alpha-zebra/LICENSE": APACHE,
            "skills/beta-zebra/SKILL.md": skill("beta-zebra", "Other yak shaving."),
        },
    )
    code, data = plan_json(kit, workspace, "acme/mixed", "--all")
    assert code == EXIT_READY, data
    assert data["source"]["integration"] == "referenced"
    assert any("alpha-zebra: Apache-2.0, skills/beta-zebra: MIT" in n for n in data["notes"])


def test_same_license_in_the_folder_and_at_the_root(kit, workspace, gh):
    gh.add(
        "acme/both",
        {
            "LICENSE": MIT,
            "skills/alpha-zebra/SKILL.md": skill("alpha-zebra"),
            "skills/alpha-zebra/LICENSE": MIT,
            "skills/beta-zebra/SKILL.md": skill("beta-zebra", "Other yak shaving."),
        },
    )
    code, data = plan_json(kit, workspace, "acme/both", "--all")
    assert code == EXIT_READY, data
    assert data["source"]["integration"] == "vendored-verbatim"
    items = {c["name"]: c for c in data["catalog"]}
    assert "include" not in items["alpha-zebra"]
    assert items["beta-zebra"]["include"] == {"LICENSE": "third_party/acme-both/LICENSE"}
    files = data["source"]["files"]
    assert {
        "third_party/acme-both/LICENSE",
        "third_party/acme-both/skills/alpha-zebra/LICENSE",
    } <= set(files)


# ---------------------------------------------------------------- 4. --path over several skills


def test_a_path_with_several_skills_takes_them_all(kit, workspace, gh):
    gh.add(
        "acme/ledger-skills",
        {
            "LICENSE": MIT,
            "skills/ledger-zebra/SKILL.md": skill("ledger-zebra"),
            "skills/other-zebra/SKILL.md": skill("other-zebra", "Totally separate yak shaving."),
            "extras/third-zebra/SKILL.md": skill("third-zebra", "Unrelated walrus care."),
        },
    )
    code, data = plan_json(kit, workspace, "acme/ledger-skills", "--path", "skills")
    assert code == EXIT_READY, data
    assert sorted(c["name"] for c in data["catalog"]) == ["ledger-zebra", "other-zebra"]
    assert data["source"]["kind"] == "skill-bundle"
    code, out = src(kit, workspace, "add", "acme/ledger-skills")  # no --path: still asks
    assert code == EXIT_BLOCKED and "3 skills found" in out


# ---------------------------------------------------------------- 5. same name twice


def test_two_folders_with_one_skill_name_block(kit, workspace, gh):
    gh.add(
        "acme/twice",
        {
            "LICENSE": MIT,
            "skills/twin-zebra/SKILL.md": skill("twin-zebra"),
            ".openclaw/skills/twin-zebra/SKILL.md": skill("twin-zebra"),
        },
    )
    before = tree_digest(kit)
    code, data = plan_json(kit, workspace, "acme/twice", "--all", "--yes")
    assert code == EXIT_PARTIAL, data
    assert (
        "two skills are named 'twin-zebra': .openclaw/skills/twin-zebra and "
        "skills/twin-zebra; pick one with --path"
    ) in blocks(data)
    assert tree_digest(kit) == before
    code, data = plan_json(kit, workspace, "acme/twice", "--path", "skills/twin-zebra")
    assert code == EXIT_READY and blocks(data) == [], data


# ---------------------------------------------------------------- 6. what is an MCP server


@pytest.mark.parametrize(
    "files,kind",
    [
        ({"README.md": 'Add it to "mcpServers" in your config.\n', "agents/a.md": "# a\n"}, None),
        ({"README.md": "Use @modelcontextprotocol/server-memory.\n", "x/setup.sh": "npx\n"}, None),
        ({"package.json": '{"dependencies": {"@modelcontextprotocol/sdk": "^1.0.0"}}'}, "mcp"),
        ({"pyproject.toml": '[project]\ndependencies = [\n  "mcp>=1.2",\n]\n'}, "mcp"),
        ({"requirements.txt": "fastmcp==2.0\n"}, "mcp"),
        ({"src/server.py": "from mcp.server.fastmcp import FastMCP\n"}, "mcp"),
        (
            {"src/index.ts": 'import { McpServer } from "@modelcontextprotocol/sdk/server";\n'},
            "mcp",
        ),
        ({".claude-plugin/plugin.json": "{}", "README.md": "mcpServers\n"}, "plugin"),
    ],
)
def test_kind_needs_server_code_not_a_readme_mention(files, kind):
    archive = sa.Archive({k: v.encode("utf-8") for k, v in files.items()}, [])
    assert sa.detect_kind(archive, []) == kind


def test_agent_collection_mentioning_mcp_servers_needs_a_person(kit, workspace, gh):
    gh.add(
        "acme/agents",
        {
            "LICENSE": MIT,
            "README.md": 'Configure "mcpServers" for the memory integration.\n',
            "engineering/backend.md": "---\nname: backend\n---\n# Backend\n",
            "scripts/convert.py": "print('convert agents')\n",
        },
    )
    code, out = src(kit, workspace, "add", "acme/agents")
    assert code == EXIT_BLOCKED, out
    assert "README mentions mcpServers, but there is no server code" in out
    gh.add("acme/server", {"LICENSE": MIT, "server.py": "from mcp import types\n"})
    code, data = plan_json(kit, workspace, "acme/server")
    assert code == EXIT_READY and data["source"]["kind"] == "mcp", data


# ---------------------------------------------------------------- 7. overlap by name


def test_a_catalog_name_is_always_an_overlap(kit, workspace, gh):
    gh.add("acme/bench", {"LICENSE": MIT, "skills/benchmark/SKILL.md": skill("benchmark")})
    code, data = plan_json(kit, workspace, "acme/bench")
    assert code == EXIT_BLOCKED, data
    row = next(o for o in data["overlap"] if o["with"] == "benchmark")
    assert row["skill"] == "benchmark" and row["score"] < sa.THRESHOLD
    assert row["decision"] is None
    assert any("already has a skill named 'benchmark'" in n for n in data["needs"])
    assert not any("overlaps benchmark" in n for n in data["needs"])  # asked once


def test_unrelated_names_and_words_are_no_overlap(kit, workspace, gh):
    gh.add("acme/zebra", {"LICENSE": MIT, "skills/ledger-zebra/SKILL.md": skill("ledger-zebra")})
    code, data = plan_json(kit, workspace, "acme/zebra")
    assert code == EXIT_READY and data["overlap"] == [], data


# ---------------------------------------------------------------- 8. sibling links


def _cloud(gh):
    gh.add(
        "acme/cloud",
        {
            "LICENSE": APACHE,
            "skills/cloud-main/SKILL.md": skill(
                "cloud-main", "See [workers](../cloud-workers/SKILL.md#setup) first."
            ),
            "skills/cloud-workers/SKILL.md": skill("cloud-workers", "Workers yak shaving."),
            "skills/cloud-dns/SKILL.md": skill("cloud-dns", "Name walrus records."),
        },
        spdx="Apache-2.0",
    )


def test_a_sibling_chosen_in_the_same_run_becomes_requires(kit, workspace, gh):
    _cloud(gh)
    code, data = plan_json(kit, workspace, "acme/cloud", "--all")
    assert code == EXIT_READY, data
    assert blocks(data) == []
    items = {c["name"]: c for c in data["catalog"]}
    assert items["cloud-main"]["requires"] == ["cloud-workers"]
    assert "requires" not in items["cloud-workers"] and "requires" not in items["cloud-dns"]
    code, out = src(kit, workspace, "add", "acme/cloud", "--all")
    assert "Catalog:      cloud-main (packs: none; policy: standard; requires cloud-workers)" in out
    code, out = src(kit, workspace, "add", "acme/cloud", "--all", "--pack", "web", "--yes")
    assert code == EXIT_READY, out
    assert catalog.load_all(kit)["cloud-main"][0].requires == ["cloud-workers"]
    # installed together, the link is allowed (the existing catalog rule)
    code, out = kit_run(kit, workspace, "plan", "--agent", "claude", "--profile", "core,web")
    assert code == EXIT_READY, out
    assert ".claude/skills/cloud-main/SKILL.md" in out
    assert ".claude/skills/cloud-workers/SKILL.md" in out


def test_a_sibling_not_chosen_still_blocks_and_names_the_path(kit, workspace, gh):
    _cloud(gh)
    code, data = plan_json(kit, workspace, "acme/cloud", "--path", "skills/cloud-main")
    assert code == EXIT_PARTIAL, data
    texts = blocks(data)
    assert texts and all("points outside the skill" in t for t in texts)
    assert all("add --path skills/cloud-workers to take both" in t for t in texts)
    assert data["catalog"][0].get("requires") is None
    two = ["--path", "skills/cloud-main", "--path", "skills/cloud-workers"]
    code, data = plan_json(kit, workspace, "acme/cloud", *two)
    assert code == EXIT_READY and blocks(data) == [], data


def test_a_link_to_a_missing_sibling_file_still_blocks(kit, workspace, gh):
    gh.add(
        "acme/cloud2",
        {
            "LICENSE": MIT,
            "skills/cloud-main/SKILL.md": skill("cloud-main", "See [x](../cloud-dns/nope.md)."),
            "skills/cloud-dns/SKILL.md": skill("cloud-dns", "Name walrus records."),
        },
    )
    code, data = plan_json(kit, workspace, "acme/cloud2", "--all")
    assert code == EXIT_PARTIAL, data
    assert any("'../cloud-dns/nope.md' points outside the skill" in t for t in blocks(data))
    assert "requires" not in data["catalog"][0]


# ---------------------------------------------------------------- rate limit message


def test_rate_limit_message_names_the_variable_not_the_token(monkeypatch):
    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "x", {}, None)

    monkeypatch.setattr(github_fetch.urllib.request, "urlopen", fail)
    with pytest.raises(github_fetch.NetworkError) as caught:
        github_fetch.GitHub("tok-very-secret-123").repo("a", "b")
    message = str(caught.value)
    assert "setting GITHUB_TOKEN in the environment raises the limit" in message
    assert "tok-very-secret-123" not in message
