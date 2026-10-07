# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The extension inside a real IngeTrazo main window (offscreen): it loads
from a plugins folder the way a user installs it, adds its tab and its
submenu — and when it is broken, IngeTrazo still starts and shows it as a
load error."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "cutlist"


def _install(plugins_dir: Path) -> Path:
    target = plugins_dir / "cutlist"
    shutil.copytree(PACKAGE, target,
                    ignore=shutil.ignore_patterns("__pycache__"))
    return target


@pytest.fixture
def window_with(qt_app, tmp_path, monkeypatch):
    """Build a MainWindow whose only user plugins folder is ``tmp_path``.

    Each test gets a fresh import of the package: IngeTrazo imports it
    once per run, but one test session builds several windows, and a
    cached ``ingetrazo_plugin_cutlist.*`` would hide a test's changes."""
    import sys

    import core.extensions as extensions
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [tmp_path])
    for name in [n for n in sys.modules
                 if n.startswith("ingetrazo_plugin_cutlist")]:
        monkeypatch.delitem(sys.modules, name)
    windows = []

    def build():
        from views.main_window import MainWindow
        w = MainWindow()
        windows.append(w)
        return w
    yield build
    for w in windows:
        w._saved_version = w.viewport.scene.version     # no "save?" modal
        w.close()


def _extensions_menu(win):
    return win._ext_menu


def test_loads_with_tab_and_submenu(tmp_path, window_with):
    _install(tmp_path)
    win = window_with()

    panels = win.extension_panels()
    assert "extension_cutlist" in panels
    dock = panels["extension_cutlist"]
    assert dock.widget().objectName() == "cutlist_panel"

    titles = [a.text() for a in _extensions_menu(win).actions()]
    assert "Cut List" in titles
    assert not any("load error" in t for t in titles)


def test_the_submenu_brings_the_tab_to_the_front(tmp_path, window_with):
    _install(tmp_path)
    win = window_with()
    sub = next(a.menu() for a in _extensions_menu(win).actions()
               if a.text() == "Cut List")
    show = sub.actions()[0]
    dock = win.extension_panels()["extension_cutlist"]
    dock.hide()
    show.trigger()
    assert not dock.isHidden()


def test_a_broken_extension_does_not_stop_ingetrazo(tmp_path, window_with):
    target = _install(tmp_path)
    init = target / "__init__.py"
    init.write_text(init.read_text(encoding="utf-8")
                    + "\nraise RuntimeError('deliberately broken')\n",
                    encoding="utf-8")
    win = window_with()

    errors = [a for a in _extensions_menu(win).actions()
              if "load error" in a.text()]
    assert len(errors) == 1
    assert "cutlist" in errors[0].text()
    assert "deliberately broken" in errors[0].toolTip()
    assert "extension_cutlist" not in win.extension_panels()


def test_a_failing_setup_does_not_stop_ingetrazo(tmp_path, window_with):
    target = _install(tmp_path)
    app_py = target / "host" / "app.py"
    app_py.write_text(app_py.read_text(encoding="utf-8").replace(
        "    from core.i18n import current_language",
        "    raise RuntimeError('setup failed on purpose')\n"
        "    from core.i18n import current_language"), encoding="utf-8")
    win = window_with()

    errors = [a for a in _extensions_menu(win).actions()
              if "load error" in a.text()]
    assert len(errors) == 1
    assert "setup failed on purpose" in errors[0].toolTip()
