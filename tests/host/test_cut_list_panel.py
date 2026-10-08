# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cut list inside a real IngeTrazo window: boards built in the scene,
Refresh, and what the panel shows."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "cutlist"


@pytest.fixture
def win(qt_app, tmp_path, monkeypatch):
    import core.extensions as extensions
    shutil.copytree(PACKAGE, tmp_path / "cutlist",
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [tmp_path])
    for name in [n for n in sys.modules
                 if n.startswith("ingetrazo_plugin_cutlist")]:
        monkeypatch.delitem(sys.modules, name)
    from views.main_window import MainWindow
    w = MainWindow()
    yield w
    w._saved_version = w.viewport.scene.version
    w.close()


def board(lx, ly, lz, at=(0, 0, 0), paint=None, default="MDF Branco",
          name=None, layer=None):
    """A painted box as an IngeTrazo group (classic group: world coords)."""
    from core.group import Group
    from core.mesh import Mesh
    from PySide6.QtGui import QVector3D as V
    x0, y0, z0 = at
    x1, y1, z1 = x0 + lx, y0 + ly, z0 + lz
    p = [V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0),
         V(x0, y0, z1), V(x1, y0, z1), V(x1, y1, z1), V(x0, y1, z1)]
    sides = {"T-": (0, 3, 2, 1), "T+": (4, 5, 6, 7), "W-": (0, 1, 5, 4),
             "L+": (1, 2, 6, 5), "W+": (2, 3, 7, 6), "L-": (3, 0, 4, 7)}
    mesh = Mesh()
    paint = paint or {}
    for loop in sides.values():
        mesh.add_face([p[i] for i in loop])
    for f in mesh.faces:
        n = f.normal()
        side = ("L" if abs(n.x()) > 0.5 else "W" if abs(n.y()) > 0.5
                else "T") + ("+" if n.x() + n.y() + n.z() > 0 else "-")
        mat = paint.get(side, default)
        f.attrs = {"mat": mat, "color": (0.5, 0.5, 0.5)}
    g = Group(mesh, name)
    g.layer = layer
    return g


def panel_of(win):
    return win.extension_panels()["extension_cutlist"].widget()


def rows(item):
    return [[item.child(i).text(c) for c in range(8)]
            for i in range(item.childCount())]


def test_refresh_lists_the_boards(win):
    scene = win.viewport.scene
    scene.groups += [
        board(0.6, 0.4, 0.018, name="Side"),
        board(0.6, 0.4, 0.018, at=(1, 0, 0), name="Side"),
        board(0.5, 0.3, 0.015, at=(2, 0, 0), name="Shelf",
              paint={"W+": "Fita"}),
        board(0.3, 0.3, 0.004, at=(3, 0, 0), default="Vidro", name="Glass",
              layer="Hardware"),
    ]
    panel = panel_of(win)
    panel.refresh_button.click()

    tree = panel.tree
    titles = [tree.topLevelItem(i).text(0)
              for i in range(tree.topLevelItemCount())]
    assert titles[0].startswith("MDF Branco") and "15" in titles[0]
    assert titles[1].startswith("MDF Branco") and "18" in titles[1]
    (side_row,) = rows(tree.topLevelItem(1))
    assert side_row[0] == "Side" and side_row[1] == "2"
    (shelf_row,) = rows(tree.topLevelItem(0))
    # "Fita" has no role yet, so it is not read as a band: it is reported.
    assert shelf_row[5] == "" and shelf_row[7] == "?"
    assert "Needs a look" in titles
    assert "Whole model" in panel.scope_label.text()


def test_tag_filter_leaves_parts_out(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Side", layer="Carcass"),
                     board(0.5, 0.3, 0.018, name="Door", layer="Doors")]
    panel = panel_of(win)
    panel.refresh_button.click()
    assert "2 parts" in panel.scope_label.text()
    menu = panel.tags_button.menu()
    doors = next(a for a in menu.actions() if a.text() == "Doors")
    doors.setChecked(False)
    assert "1 parts" in panel.scope_label.text()
    assert "1 left out by tag" in panel.scope_label.text()


def test_clicking_a_line_highlights_its_parts(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Side")]
    panel = panel_of(win)
    panel.refresh_button.click()
    controller = panel._controller
    line = panel.tree.topLevelItem(0).child(0)
    panel.tree.setCurrentItem(line)
    assert controller.highlight == [scene.groups[-1].uid]
    assert len(controller.outlines[scene.groups[-1].uid]) == 12


def test_an_edit_marks_the_list_out_of_date(win):
    panel = panel_of(win)
    panel.refresh_button.click()
    assert panel.stale_label.isHidden()
    win.viewport.scene.groups.append(board(0.6, 0.4, 0.018))
    win.viewport.notify_scene_changed()
    assert not panel.stale_label.isHidden()


def test_auto_named_groups_get_a_group_number(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018)]        # IngeTrazo names it
    panel = panel_of(win)
    panel.refresh_button.click()
    assert panel.tree.topLevelItem(0).child(0).text(0) == "Group #1"


def test_different_names_show_as_sub_rows_and_can_be_kept_apart(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Door left"),
                     board(0.6, 0.4, 0.018, at=(1, 0, 0), name="Door right"),
                     board(0.6, 0.4, 0.018, at=(2, 0, 0), name="Door left")]
    panel = panel_of(win)
    panel.refresh_button.click()
    line = panel.tree.topLevelItem(0).child(0)
    assert line.text(1) == "3"
    assert [(line.child(i).text(0), line.child(i).text(1))
            for i in range(line.childCount())] == [("Door left", "2"),
                                                   ("Door right", "1")]
    panel.tree.setCurrentItem(line.child(1))
    right = next(g.uid for g in scene.groups if g.name == "Door right")
    assert panel._controller.highlight == [right]

    panel.merge_button.setChecked(False)
    section = panel.tree.topLevelItem(0)
    assert sorted((section.child(i).text(0), section.child(i).text(1))
                  for i in range(section.childCount())) == \
        [("Door left", "2"), ("Door right", "1")]


def test_column_widths_are_remembered(win):
    panel = panel_of(win)
    panel.refresh_button.click()
    panel.tree.setColumnWidth(0, 333)
    from PySide6.QtCore import QSettings
    from views.main_window import MainWindow  # noqa: F401 — same settings
    state = QSettings().value(panel.HEADER_KEY)
    assert state is not None
    other = type(panel)()
    assert other.tree.columnWidth(0) == 333
