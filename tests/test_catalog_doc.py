"""P7-T1: docs/CATALOG.md is generated from the catalogs and real plans and must be current."""

from __future__ import annotations

import importlib.util

from tests.conftest import KIT_ROOT


def _generator():
    spec = importlib.util.spec_from_file_location(
        "make_catalog_doc", KIT_ROOT / "devtools" / "make_catalog_doc.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_doc_is_current():
    text = (KIT_ROOT / "docs" / "CATALOG.md").read_bytes().decode("utf-8")
    assert text == _generator().render(), (
        "docs/CATALOG.md is out of date: uv run python devtools/make_catalog_doc.py"
    )


def test_default_install_matches_the_catalog_doc():
    """The default (core,hitl, standard) is what README promises: 17 skills for each agent."""
    text = (KIT_ROOT / "docs" / "CATALOG.md").read_text(encoding="utf-8")
    assert "| `core` | 11 | 17 |" in text
