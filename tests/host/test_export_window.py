# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The export window in a real IngeTrazo (D-009): preview, profiles,
problems that block, files written, custom fields."""
from __future__ import annotations

import json
from dataclasses import replace

from tests.host.conftest import panel_of, plugin
from tests.host.scenes import board


def setup_model(win):
    scene = win.viewport.scene
    scene.groups += [
        board(0.6, 0.4, 0.015, name="Side", paint={"W+": "Fita"},
              layer="QTO armario"),
        board(0.6, 0.4, 0.015, at=(1, 0, 0), name="Side",
              paint={"W+": "Fita"}, layer="QTO armario"),
        board(0.5, 0.3, 0.015, at=(2, 0, 0), name="Shelf"),
    ]
    panel = panel_of(win)
    c = panel._controller
    mats = plugin("model.materials")
    c.store.save_materials([mats.MaterialSpec("Fita",
                                              role=mats.Role.EDGE_BAND)],
                           remember=False)
    panel.refresh_button.click()
    return c


def dialog(c):
    ui = plugin("ui.export_dialog")
    return ui.ExportDialog(c.export_session())


def test_preview_shows_the_generic_profile(win):
    c = setup_model(win)
    d = dialog(c)
    text = d.preview.toPlainText().splitlines()
    assert text[0].lstrip("﻿").startswith("Qty;Name;Length")
    assert "2;Side;600;400;15;MDF Branco;Fita" in text[1]
    assert d.export_button.isEnabled()
    d.deleteLater()


def test_save_as_a_new_profile_is_remembered(win, user_dir):
    c = setup_model(win)
    d = dialog(c)
    d.header.setChecked(False)
    assert d.combo.currentText().endswith("*")
    d.save_profile_as("No header")
    saved = json.loads((user_dir / "defaults.json").read_text("utf-8"))
    assert saved["last_export_profile"] == "No header"
    assert saved["export_profiles"]["No header"]["header"] is False
    assert not d.combo.currentText().endswith("*")
    d.deleteLater()


def test_a_missing_supplier_code_blocks_the_export(win, tmp_path):
    c = setup_model(win)
    d = dialog(c)
    profile = plugin("export.profile")
    p = replace(d.profile, columns=(
        profile.Column("Code", value="material_code"),
        profile.Column("Qty", value="qty")))
    d._load(p)
    assert "MDF Branco" in d.problems.text()
    assert not d.export_button.isEnabled()
    # Fill the code in the Codes tab: unblocked, and the file is written.
    for r in range(d.codes.rowCount()):
        if d.codes.item(r, 1).text() == "MDF Branco":
            d.codes.item(r, 2).setText("1234567")
    assert d.problems.text() == ""
    out = tmp_path / "out"
    out.mkdir()
    d.export(folder=str(out))
    (written,) = list(out.iterdir())
    lines = written.read_bytes().decode("utf-8-sig").splitlines()
    assert lines == ["Code;Qty", "1234567;2", "1234567;1"]
    d.deleteLater()


def test_custom_fields_reach_the_export(win, tmp_path):
    c = setup_model(win)
    fields = plugin("model.fields")
    c.store.save_fields(fields.Fields((
        fields.FieldDef("Ambiente", "Cozinha",
                        (fields.TagRule("QTO", "Quarto"),)),)),
        remember=False)
    panel_of(win).refresh_button.click()
    d = dialog(c)
    profile = plugin("export.profile")
    d._load(replace(d.profile, split="field:Ambiente", filename="{value}",
                    columns=(profile.Column("Name", value="name"),)))
    out = tmp_path / "out"
    out.mkdir()
    d.export(folder=str(out))
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Cozinha.csv", "Quarto.csv"]
    assert "Side" in (out / "Quarto.csv").read_text("utf-8-sig")
    d.deleteLater()


def test_part_settings_set_a_field_on_many_parts(win):
    c = setup_model(win)
    fields = plugin("model.fields")
    c.store.save_fields(fields.Fields((fields.FieldDef("Ambiente",
                                                       "Cozinha"),)),
                        remember=False)
    scene = win.viewport.scene
    shelf = next(g for g in scene.groups if g.name == "Shelf")
    parts = plugin("model.parts")
    c.store.set_overrides({shelf: parts.PartOverride().with_fields(
        {"Ambiente": "Sala"})})
    panel_of(win).refresh_button.click()
    assert c.part_fields()[shelf.uid] == {"Ambiente": "Sala"}


def test_text_options_from_the_columns_table(win):
    c = setup_model(win)
    d = dialog(c)
    profile = plugin("export.profile")
    d._load(replace(d.profile, columns=(
        profile.Column("Material", value="material"),)))
    button = d.columns.cellWidget(0, 6)
    assert button.text() == "As is"
    upper = next(a for a in button.menu().actions() if a.data() == "upper")
    upper.setChecked(True)
    assert button.text() == "UPPERCASE"
    assert d.profile.columns[0].text == ("upper",)
    assert "MDF BRANCO" in d.preview.toPlainText()
    d.deleteLater()


def test_yes_no_words_only_where_they_mean_something(win):
    c = setup_model(win)
    d = dialog(c)
    profile = plugin("export.profile")
    d._load(replace(d.profile, columns=(
        profile.Column("Name", value="name"),
        profile.Column("Rotate", value="rotate", yes="S", no=""))))
    name_yes, rotate_yes = d.columns.item(0, 4), d.columns.item(1, 4)
    assert name_yes.text() == "" and not name_yes.flags() & \
        plugin("ui.export_dialog").Qt.ItemFlag.ItemIsEnabled
    assert rotate_yes.text() == "S"
    # Switching the first column to a yes/no field brings its words back.
    combo = d.columns.cellWidget(0, 3)
    combo.setCurrentIndex(combo.findData("grain"))
    assert d.columns.item(0, 4).text() == "1"
    assert [(col.yes, col.no) for col in d.profile.columns] == \
        [("1", "0"), ("S", "")]
    d.deleteLater()


def test_the_on_switch_and_moving_columns(win):
    c = setup_model(win)
    d = dialog(c)
    profile = plugin("export.profile")
    Qt = plugin("ui.export_dialog").Qt
    d._load(replace(d.profile, columns=(
        profile.Column("A", value="qty"), profile.Column("B", value="name"),
        profile.Column("C", value="length"))))
    # Off: still in the profile, out of the file, the row faded.
    d.columns.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    assert d.profile.columns[1].hidden
    assert d.preview.toPlainText().splitlines()[0].lstrip("\ufeff") == "A;C"
    assert not d.columns.cellWidget(1, 3).isEnabled()
    # A drop of row 0 below row 2, and Move up: the same reordering path.
    d._move_column_to(0, 3)
    assert [col.header for col in d.profile.columns] == ["B", "C", "A"]
    d.columns.selectRow(2)
    d._move_column(-1)
    assert [col.header for col in d.profile.columns] == ["B", "A", "C"]
    assert d.profile.columns[0].hidden          # the switch moved with it
    d.deleteLater()


def test_rows_only_take_drops_between_them(win):
    """Regression (Ronaldo, 2026-10-09): no cell accepts a drop onto it,
    so the drop indicator is always a line between rows."""
    c = setup_model(win)
    d = dialog(c)
    Qt = plugin("ui.export_dialog").Qt
    table = d.columns
    for r in range(table.rowCount()):
        for col in range(table.columnCount()):
            flags = table.model().flags(table.model().index(r, col))
            assert not flags & Qt.ItemFlag.ItemIsDropEnabled, (r, col)
    # A column switched to fixed text keeps the rule on its new cell.
    kind = table.cellWidget(0, 2)
    kind.setCurrentIndex(kind.findData("text"))
    flags = table.model().flags(table.model().index(0, 3))
    assert not flags & Qt.ItemFlag.ItemIsDropEnabled
    d.deleteLater()


def test_untick_a_board_to_leave_it_out(win, tmp_path):
    c = setup_model(win)
    win.viewport.scene.groups.append(board(0.4, 0.3, 0.006, at=(3, 0, 0),
                                           name="Back"))
    panel_of(win).refresh_button.click()
    d = dialog(c)
    profile = plugin("export.profile")
    d._load(replace(d.profile, split="board",
                    filename="{material} {thickness}",
                    columns=(profile.Column("Name", value="name"),)))
    labels = [d.boards.item(i).text() for i in range(d.boards.count())]
    assert labels == ["MDF Branco · 6 mm — 1 parts",
                      "MDF Branco · 15 mm — 3 parts"]
    assert "MDF_Branco_6.csv" in d.summary.toolTip()
    Qt = plugin("ui.export_dialog").Qt
    d.boards.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert d.summary.toolTip() == "MDF_Branco_15.csv"
    assert d.name_example.text().endswith("MDF_Branco_15.csv")
    d.deleteLater()


def test_insert_menu_puts_a_fill_in_field_in_the_name(win):
    c = setup_model(win)
    d = dialog(c)
    d.filename.setText("")
    act = next(a for a in d.insert_button.menu().actions()
               if a.text().endswith("{material}"))
    act.trigger()
    assert d.filename.text() == "{material}"
    assert d.profile.filename == "{material}"
    assert d.name_example.text().endswith("MDF_Branco.csv")
    d.deleteLater()


def test_a_long_file_name_does_not_widen_the_window(win):
    c = setup_model(win)
    d = dialog(c)
    d.resize(900, 600)
    width = d.sizeHint().width()
    d.filename.setText("{model} " + "very long name " * 30)
    d._edited()
    assert d.sizeHint().width() <= width + 5
    d.deleteLater()
