# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Test setup shared by the whole suite.

Two kinds of tests:

- **pure** (default): ``model/``, ``packing/``, ``export/``, i18n. No Qt
  application, no IngeTrazo. ``pytest`` runs only these.
- **host** (``@pytest.mark.host``, or anything under ``tests/host/``): they
  build a real IngeTrazo main window, offscreen. ``pytest -m host`` runs
  them; they need IngeTrazo's source, found at ``$INGETRAZO_SRC`` or
  ``./ingetrazo`` (see CLAUDE.md, Development setup).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INGETRAZO_SRC = Path(os.environ.get("INGETRAZO_SRC") or ROOT / "ingetrazo")
HAVE_INGETRAZO = (INGETRAZO_SRC / "core" / "extensions.py").is_file()

if HAVE_INGETRAZO and str(INGETRAZO_SRC) not in sys.path:
    sys.path.insert(0, str(INGETRAZO_SRC))


def pytest_collection_modifyitems(config, items):
    host_dir = ROOT / "tests" / "host"
    skip = pytest.mark.skip(
        reason=f"IngeTrazo source not found at {INGETRAZO_SRC} "
               "(set INGETRAZO_SRC)")
    for item in items:
        if host_dir in Path(item.fspath).parents:
            item.add_marker(pytest.mark.host)
        if "host" in item.keywords and not HAVE_INGETRAZO:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def qt_app():
    """One offscreen QApplication for the session, with a throw-away
    QSettings store: building IngeTrazo's main window reads and writes
    preferences, and a test must never touch the developer's real ones."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    settings_dir = tempfile.mkdtemp(prefix="cutlist-tests-settings-")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.IniFormat, scope, settings_dir)
    return QApplication.instance() or QApplication(sys.argv[:1])
