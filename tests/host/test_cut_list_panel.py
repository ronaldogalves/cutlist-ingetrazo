# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cut list inside a real IngeTrazo window: boards built in the scene,
Refresh, and what the panel shows."""
from __future__ import annotations

from tests.host.scenes import board


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


def test_a_new_document_has_no_parts(win):
    """The scale figure of a new document is a billboard, not a part."""
    panel = panel_of(win)
    panel.refresh_button.click()
    assert "0 parts" in panel.scope_label.text()
