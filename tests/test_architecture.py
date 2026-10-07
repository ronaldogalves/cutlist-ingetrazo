# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The three-layer rule of CLAUDE.md, checked on every run:

- only ``host/`` imports IngeTrazo;
- ``model/``, ``packing/``, ``export/`` and ``i18n/`` import neither Qt nor
  IngeTrazo;
- inside the package, imports are relative (IngeTrazo loads us under a
  private module name, so ``import cutlist`` would fail there).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent / "cutlist"

INGETRAZO = {"core", "views", "tools", "formats", "plugins", "analysis",
             "georef", "materials"}
QT = {"PySide6", "shiboken6"}
PURE_LAYERS = ("model", "packing", "export", "i18n")


def _modules():
    for path in sorted(PACKAGE.rglob("*.py")):
        yield path.relative_to(PACKAGE), ast.parse(
            path.read_text(encoding="utf-8"))


def _absolute_imports(tree):
    """Top-level names of every absolute import, wherever it appears
    (deferred imports inside functions count too)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module.split(".")[0]


@pytest.mark.parametrize("rel, tree", list(_modules()),
                         ids=lambda v: str(v) if isinstance(v, Path) else "")
def test_layers(rel, tree):
    roots = set(_absolute_imports(tree))
    layer = rel.parts[0] if len(rel.parts) > 1 else ""
    assert "cutlist" not in roots, f"{rel}: use a relative import"
    if layer != "host":
        assert not roots & INGETRAZO, \
            f"{rel} imports IngeTrazo ({roots & INGETRAZO}); only host/ may"
    if layer in PURE_LAYERS:
        assert not roots & QT, f"{rel} is a pure layer but imports Qt"
