# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Labels in a real IngeTrazo (D-018): one per piece, from the cut list or
from the diagrams (by sheet), written as a PDF on the chosen sheet."""
from __future__ import annotations

from tests.host.conftest import panel_of, plugin
from tests.host.test_diagram_window import model, opened


def test_from_the_cut_list_one_per_piece(qt_app, win, first_run_done):
    c = model(win)
    labels = c.cut_list_labels()
    assert len(labels) == 3                        # two doors, one shelf
    doors = [lb for lb in labels if lb.name == "Door"]
    assert [(lb.index, lb.count) for lb in doors] == [(1, 2), (2, 2)]
    tree = panel_of(win).tree
    letters = {tree.topLevelItem(i).child(j).text(0):
               tree.topLevelItem(i).child(j).text(8)
               for i in range(tree.topLevelItemCount())
               for j in range(tree.topLevelItem(i).childCount())}
    assert doors[0].letter == letters["Door"]
    assert all(lb.sheet is None for lb in labels)
    shelf = next(lb for lb in labels if lb.name == "Shelf")
    assert shelf.grain == "length"                 # Freijo has grain


def test_from_the_diagrams_by_sheet(qt_app, win, first_run_done):
    c = model(win)
    w = opened(qt_app, c)
    entries = w.label_entries()
    assert len(entries) == 3 and all(e[4] == 1 for e in entries)
    labels = c.make_labels(entries)
    assert {lb.sheet for lb in labels} == {1}
    w.close()


def test_the_window_writes_the_pdf(qt_app, win, first_run_done, tmp_path):
    c = model(win)
    ui = plugin("ui.labels_dialog")
    saved = {}
    dlg = ui.LabelsDialog(c.cut_list_labels(), title="t", options={},
                          save_options=saved.update)
    dlg.start.setValue(5)
    out = tmp_path / "labels.pdf"
    assert dlg.export_pdf(str(out)) == str(out)
    assert out.read_bytes()[:5] == b"%PDF-"
    assert saved["sheet"] == dlg.sheet.currentData()

    dlg.sheet.setCurrentIndex(dlg.sheet.findData(ui.CUSTOM))
    dlg.cols.setValue(2)
    dlg.rows.setValue(3)
    assert dlg.label_sheet().per_page == 6 and dlg.start.maximum() == 6
    dlg.export_pdf(str(out))
    assert saved["custom"]["cols"] == 2
    dlg.deleteLater()
