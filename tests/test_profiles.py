import json

import pytest

from kit.model import UsageError
from kit.profiles import ProfileError, available_profiles, load_profile

ALL_SKILLS = [
    "task-router",
    "tdd-automator",
    "algorithm-optimizer",
    "submission-validator",
    "implementation-review",
    "benchmark",
    "systematic-debugging",
    "codebase-explorer",
    "counterexample-hunter",
    "algorithm-options",
    "design-review",
]

PYTEST = {
    "name": "pytest",
    "kind": "python-tool",
    "package": "pytest",
    "version": "1",
    "command": "pytest",
}
RUFF = {"name": "ruff", "kind": "python-tool", "package": "ruff", "version": "1", "command": "ruff"}


def _write(root, name, data):
    folder = root / "profiles"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def test_core_profile(kit_root):
    profile = load_profile(kit_root, "core")
    assert profile.skills == ALL_SKILLS
    assert profile.required_skills == ALL_SKILLS[:4]
    assert profile.tools == [] and profile.mcp == []


def test_extends_merges_lists_base_first(tmp_path):
    _write(
        tmp_path,
        "base",
        {"name": "base", "description": "b", "skills": ["a", "b"], "tools": [PYTEST]},
    )
    _write(
        tmp_path,
        "child",
        {
            "name": "child",
            "description": "c",
            "extends": "base",
            "skills": ["b", "c"],
            "tools": [RUFF],
        },
    )
    profile = load_profile(tmp_path, "child")
    assert profile.skills == ["a", "b", "c"]
    assert profile.tools == [PYTEST, RUFF]
    assert profile.description == "c"


def test_cycle_is_rejected(tmp_path):
    _write(tmp_path, "a", {"name": "a", "extends": "b"})
    _write(tmp_path, "b", {"name": "b", "extends": "a"})
    with pytest.raises(UsageError, match="cycle"):
        load_profile(tmp_path, "a")


def test_unknown_profile_lists_available(tmp_path):
    _write(tmp_path, "base", {"name": "base"})
    with pytest.raises(UsageError, match="available: base"):
        load_profile(tmp_path, "nope")


def test_available_profiles_sorted(tmp_path):
    _write(tmp_path, "web", {"name": "web"})
    _write(tmp_path, "core", {"name": "core"})
    assert available_profiles(tmp_path) == ["core", "web"]


def test_all_profiles_available(kit_root):
    assert available_profiles(kit_root) == ["core", "data", "full", "python", "web"]


def test_python_profile(kit_root):
    profile = load_profile(kit_root, "python")
    assert profile.skills == ALL_SKILLS
    assert [(t["name"], t["version"]) for t in profile.tools] == [
        ("pytest", "8.4.2"),
        ("ruff", "0.17.3"),
    ]
    assert profile.mcp == ["sequential-thinking"]
    assert profile.report_only is False


def test_data_profile_only_advises_libraries(kit_root):
    profile = load_profile(kit_root, "data")
    kinds = {t["name"]: t["kind"] for t in profile.tools}
    assert kinds == {
        "pytest": "python-tool",
        "ruff": "python-tool",
        "numpy": "python-lib",
        "pandas": "python-lib",
    }


def test_web_profile(kit_root):
    profile = load_profile(kit_root, "web")
    assert [t["kind"] for t in profile.tools] == ["node-project"]
    assert profile.mcp == ["sequential-thinking"]


def test_full_profile_is_report_only(kit_root):
    profile = load_profile(kit_root, "full")
    assert profile.report_only is True
    assert {t["kind"] for t in profile.tools} == {"python-tool", "python-lib", "node-project"}
    assert profile.mcp == ["sequential-thinking"]


def test_report_only_is_not_inherited(tmp_path):
    _write(tmp_path, "base", {"name": "base", "report_only": True})
    _write(tmp_path, "child", {"name": "child", "extends": "base"})
    assert load_profile(tmp_path, "child").report_only is False


def test_malformed_json_is_profile_error(tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "bad.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ProfileError, match="not valid JSON"):
        load_profile(tmp_path, "bad")


@pytest.mark.parametrize(
    "data, message",
    [
        ({"name": "x", "extends": 3}, "extends"),
        ({"name": "x", "skills": "task-router"}, "skills"),
        ({"name": "x", "mcp": [1]}, "mcp"),
        ({"name": "x", "tools": [{"name": "t"}]}, "kind"),
        ({"name": "x", "tools": [{"name": "t", "kind": "python-tool", "package": "t"}]}, "version"),
        ({"name": "x", "tools": [{"name": "t", "kind": "python-lib"}]}, "package"),
        ({"name": "x", "report_only": "yes"}, "report_only"),
        (["not", "an", "object"], "object"),
    ],
)
def test_schema_errors_are_profile_errors(tmp_path, data, message):
    _write(tmp_path, "x", data)
    with pytest.raises(ProfileError, match=message):
        load_profile(tmp_path, "x")
