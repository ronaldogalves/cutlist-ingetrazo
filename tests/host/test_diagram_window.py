# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cutting diagrams window in a real IngeTrazo (M3): it lays out on a
worker thread, asks sheet sizes once, fixes a part from the diagram as one
undo step and lays out the same parts again, saves a layout in the model
and says what changed since, and writes the PDF."""
from __future__ import annotations

import pytest

from tests.host.conftest import panel_of, plugin
from tests.host.scenes import board


def controller(win):
    return panel_of(win)._controller


def model(win, sheets=True):
    scene = win.viewport.scene
    scene.groups += [
        board(0.7, 0.4, 0.015, name="Door"),
        board(0.7, 0.4, 0.015, at=(1, 0, 0), name="Door"),
        board(0.6, 0.3, 0.015, at=(2, 0, 0), name="Shelf",
              default="Freijo"),
    ]
    c = controller(win)
    if sheets:
        materials = plugin("model.materials")
        c.store.save_materials([
            materials.MaterialSpec("MDF Branco", stocks=((2.75, 1.84),)),
            materials.MaterialSpec("Freijo", grain=True,
                                   stocks=((2.5, 1.6),))], remember=False)
    panel_of(win).refresh_button.click()
    return c


def opened(qt_app, c, saved=None):
    c.open_diagrams(saved)
    w = c.diagram_window
    w.wait()
    qt_app.processEvents()
    return w


@pytest.fixture
def ready(first_run_done):
    return first_run_done


def test_it_lays_out_every_board(qt_app, win, ready):
    c = model(win)
    w = opened(qt_app, c)
    assert w.board_list.count() == 2
    assert all(b.layout.sheets for b in w.boards)
    assert w.canvas.blocks                      # sheets drawn
    texts = [w.board_list.item(i).text() for i in range(2)]
    assert any(t.startswith("Freijo") for t in texts)
    w.close()


def test_a_board_without_sheet_size_is_asked_once(qt_app, win, ready,
                                                  monkeypatch):
    c = model(win, sheets=False)
    dialogs = plugin("ui.dialogs")

    def answer(dlg):
        for r in range(dlg.table.rowCount()):
            dlg.table.item(r, 1).setText("2750")
            dlg.table.item(r, 2).setText("1840")
        return 1
    monkeypatch.setattr(dialogs.SheetSizesDialog, "exec", answer)
    w = opened(qt_app, c)
    lib = c.store.library()
    assert lib.get("Freijo").stocks[0].length == pytest.approx(2.75)
    assert all(not b.layout.unplaced for b in w.boards)
    w.close()


def test_switch_grain_on_the_diagram(qt_app, win, ready):
    c = model(win)
    c.store.save_plan_options({"warned_redo": True})
    w = opened(qt_app, c)
    freijo = next(p for p in w.plans if p.material == "Freijo")
    (key,) = freijo.uids
    uids = freijo.uids[key]
    before = len(win.viewport.history.undo_stack)
    w._act("switch_grain", uids)
    w.wait()
    qt_app.processEvents()
    shelf = next(g for g in win.viewport.scene.groups if g.name == "Shelf")
    assert shelf.ext["cutlist"]["grain"] == "width"
    assert len(win.viewport.history.undo_stack) == before + 1
    # Laid out again, for the same parts, with the shelf given turned.
    freijo = next(p for p in w.plans if p.material == "Freijo")
    (piece,) = freijo.job.pieces
    assert (piece.length, piece.width) == pytest.approx((0.3, 0.6))
    w.close()


def test_a_saved_layout_is_drawn_as_it_was(qt_app, win, ready):
    c = model(win)
    w = opened(qt_app, c)
    w.save_layout("Kitchen")
    assert "Kitchen" in c.store.layouts()
    layouts = [b.layout for b in w.boards]
    w.close()

    w = opened(qt_app, c, saved="Kitchen")
    assert [b.layout for b in w.boards] == layouts
    assert not w.redo_button.isVisibleTo(w)
    w.close()

    # The model changes: the saved plan says so, and offers to redo it.
    shelf = next(g for g in win.viewport.scene.groups if g.name == "Shelf")
    win.viewport.scene.groups.remove(shelf)
    w = opened(qt_app, c, saved="Kitchen")
    assert "1 gone" in w.status.text()
    assert w.redo_button.isVisibleTo(w)
    w.redo_saved()
    w.wait()
    qt_app.processEvents()
    assert [b.material for b in w.boards] == ["MDF Branco"]
    w.close()


def test_the_pdf_and_the_mouse(qt_app, win, ready, tmp_path):
    c = model(win)
    w = opened(qt_app, c)
    out = tmp_path / "plan.pdf"
    w.export_pdf(str(out))
    assert out.read_bytes()[:5] == b"%PDF-"
    sheet, _count, shapes, _y = w.canvas.blocks[0]
    key = sheet.placements[0].key
    tip, cuts = w.canvas._part_tip(sheet, key, 0)
    assert tip.startswith(key) and "×" in tip
    first = next(cut for cut in sheet.cuts if cut.stage == 1)
    assert "Can go first" in w.canvas._cut_tip(sheet, first)
    w.close()


def test_one_letter_in_the_list_and_on_the_diagrams(qt_app, win, ready):
    """D-016 §1: the panel's letter column and the diagrams agree."""
    c = model(win)
    panel = panel_of(win)
    tree = panel.tree
    assert tree.header().visualIndex(8) == 0          # shown first
    in_list = {}
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        for j in range(top.childCount()):
            line = top.child(j)
            in_list[line.text(8)] = line.text(0)
    w = opened(qt_app, c)
    on_diagrams = {k: info.name for plan in w.plans
                   for k, info in plan.parts.items()}
    assert on_diagrams == in_list
    w.close()


def test_cancel_on_sheet_sizes_stops(qt_app, win, ready, monkeypatch):
    """Ronaldo, 2026-10-21: Cancel went on into the diagrams."""
    c = model(win, sheets=False)
    dialogs = plugin("ui.dialogs")
    monkeypatch.setattr(dialogs.SheetSizesDialog, "exec", lambda self: 0)
    c.open_diagrams()
    assert c.diagram_window is None
    assert not c.store.library().get("Freijo")


def test_a_board_left_without_size_is_said_not_drawn(qt_app, win, ready,
                                                     monkeypatch):
    c = model(win, sheets=False)
    dialogs = plugin("ui.dialogs")

    def only_mdf(dlg):
        for r in range(dlg.table.rowCount()):
            if dlg.table.item(r, 0).text() == "MDF Branco":
                dlg.table.item(r, 1).setText("2750")
                dlg.table.item(r, 2).setText("1840")
        return 1
    monkeypatch.setattr(dialogs.SheetSizesDialog, "exec", only_mdf)
    w = opened(qt_app, c)
    assert [b.material for b in w.boards] == ["MDF Branco"]
    assert "Freijo (no sheet size" in w.status.text()
    w.close()


def test_two_way_highlight(qt_app, win, ready):
    """A part hovered on the diagram lights up in the model; a part
    selected in the model lights up on the diagram."""
    c = model(win)
    w = opened(qt_app, c)
    w.show()
    row = next(i for i, b in enumerate(w.boards) if b.material == "MDF Branco")
    w.board_list.setCurrentRow(row)
    (key,) = w.plans[row].uids
    doors = set(w.plans[row].uids[key])
    w.canvas.hovered.emit(key)
    assert set(c.highlight) == doors
    w.canvas.hovered.emit("")
    assert c.highlight == []

    scene = win.viewport.scene
    scene.selection.clear()
    scene.selection.add(next(g for g in scene.groups if g.name == "Door"))
    w._follow_selection()
    assert w.canvas.selected == {key}
    scene.selection.clear()
    w._follow_selection()
    assert w.canvas.selected == set()
    w.close()
    assert c.highlight == []
