# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The release zip installs the way IngeTrazo's Extension manager installs
a catalog entry: unpacked by its own code, one ``cutlist`` package, no
caches, and the same bytes every build (the catalog pins a SHA-256)."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_release", ROOT / "tools" / "build_release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_release_zip_installs(tmp_path):
    from core.extension_manager import _extract_plugin_zip

    builder = _builder()
    first = builder.build().read_bytes()
    again = builder.build().read_bytes()
    assert hashlib.sha256(first).digest() == hashlib.sha256(again).digest()

    stage = tmp_path / "stage"
    stage.mkdir()
    _extract_plugin_zip(first, stage, "cutlist")
    assert (stage / "__init__.py").is_file()
    assert (stage / "i18n" / "pt-BR.json").is_file()
    assert not list(stage.rglob("__pycache__"))

    # It imports the way IngeTrazo imports a plugin: by path, privately.
    spec = importlib.util.spec_from_file_location(
        "ingetrazo_plugin_cutlist_release", stage / "__init__.py",
        submodule_search_locations=[str(stage)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        assert callable(mod.setup) and mod.__version__ == builder.version()
    finally:
        sys.modules.pop(spec.name, None)
