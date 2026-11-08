"""TC-SEC-01 (REQ-COMPAT-007): the kit runs on the Python standard library alone.

Every module the kit runs or installs (kit/, run_kit.py, and the Python files under shared/
that are copied into workspaces) may import only the standard library and the kit itself. The
imports are read with ast, so imports inside functions and try blocks count too. pyproject.toml
must keep `dependencies = []`.

Whether a name is standard library is decided without sys.stdlib_module_names (3.10+), so the
check also runs on 3.9: a built-in or frozen module, or one found under the interpreter's stdlib
folder and not under site-packages. tomllib (3.11+) is the one newer module the kit uses; it is
imported only behind a fallback, so on 3.9/3.10 it is accepted by name.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
import sysconfig
from pathlib import Path

import pytest

from tests.conftest import KIT_ROOT

NEWER_STDLIB = {"tomllib"}  # 3.11+; the kit falls back to a line scan without it
KIT_PACKAGES = {"kit"}


def runtime_files(root: Path):
    files = sorted((root / "kit").rglob("*.py")) + [root / "run_kit.py"]
    files += sorted((root / "shared").rglob("*.py"))
    return [f for f in files if "__pycache__" not in f.parts]


def imported_names(source: str):
    """Top-level names of absolute imports; relative imports (level > 0) are the kit's own."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


def _stdlib_dirs():
    paths = sysconfig.get_paths()
    return [Path(paths[k]).resolve() for k in ("stdlib", "platstdlib")]


def is_stdlib(name: str) -> bool:
    if name == "__future__" or name in sys.builtin_module_names:
        return True
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return name in names
    spec = importlib.util.find_spec(name)
    if spec is None:
        return name in NEWER_STDLIB
    if spec.origin in (None, "built-in", "frozen"):
        return True
    origin = Path(spec.origin).resolve()
    if "site-packages" in origin.parts or "dist-packages" in origin.parts:
        return False
    return any(d in origin.parents for d in _stdlib_dirs())


def foreign_imports(source: str):
    return sorted({n for n in imported_names(source) if n not in KIT_PACKAGES and not is_stdlib(n)})


@pytest.mark.parametrize(
    "path", runtime_files(KIT_ROOT), ids=lambda p: p.relative_to(KIT_ROOT).as_posix()
)
def test_runtime_file_imports_only_the_standard_library(path):
    assert foreign_imports(path.read_text(encoding="utf-8")) == []


def test_the_runtime_file_list_covers_the_kit():
    files = {p.relative_to(KIT_ROOT).as_posix() for p in runtime_files(KIT_ROOT)}
    assert {"run_kit.py", "kit/app.py", "kit/__main__.py"} <= files
    assert "shared/hooks/kit_approval.py" in files
    assert "shared/skills/data-quality-validator/scripts/profile_csv.py" in files


def test_pyproject_has_no_runtime_dependencies():
    text = (KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"^dependencies = \[\]$", text, re.M)


def test_the_checker_catches_what_it_should():
    source = (
        "import os, json\n"
        "from . import model\n"
        "from kit.fsops import State\n"
        "import xml.etree.ElementTree as ET\n"
        "def f():\n"
        "    import pytest\n"
        "try:\n"
        "    import yaml\n"
        "except ImportError:\n"
        "    yaml = None\n"
        "from requests.adapters import HTTPAdapter\n"
    )
    assert foreign_imports(source) == ["pytest", "requests", "yaml"]
    assert is_stdlib("tomllib")
    assert not is_stdlib("pytest")  # installed for the tests, yet not standard library
