# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""A real IngeTrazo main window with the extension loaded from a copy of
``cutlist/`` — and a throw-away folder for the user's defaults, so tests
never read or write the developer's own."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "cutlist"


@pytest.fixture
def user_dir(tmp_path, monkeypatch):
    folder = tmp_path / "user"
    folder.mkdir()
    monkeypatch.setenv("CUTLIST_USER_DIR", str(folder))
    return folder


@pytest.fixture
def first_run_done(user_dir):
    """The scope window was answered: tests that only Refresh skip it."""
    (user_dir / "defaults.json").write_text(
        json.dumps({"settings": {"scope_asked": True}}), encoding="utf-8")
    return user_dir


@pytest.fixture
def win(qt_app, tmp_path, monkeypatch, first_run_done):
    import core.extensions as extensions
    plugins = tmp_path / "plugins"
    shutil.copytree(PACKAGE, plugins / "cutlist",
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [plugins])
    for name in [n for n in sys.modules
                 if n.startswith("ingetrazo_plugin_cutlist")]:
        monkeypatch.delitem(sys.modules, name)
    from views.main_window import MainWindow
    w = MainWindow()
    yield w
    w._saved_version = w.viewport.scene.version
    w.close()


def panel_of(win):
    return win.extension_panels()["extension_cutlist"].widget()


def plugin(name: str):
    """A module of the loaded extension (it lives under a private name)."""
    import importlib
    return importlib.import_module(f"ingetrazo_plugin_cutlist.{name}")
