# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Settings that stay (M1 step B): materials, part settings, numbers, the
first-use window — stored where D-007/D-008 say, each change one undo
step, the user's defaults in their own file."""
from __future__ import annotations

import json

from tests.host.conftest import panel_of, plugin
from tests.host.scenes import board


def refresh(win):
    panel_of(win).refresh_button.click()
    return panel_of(win)


def lines(panel):
    tree = panel.tree
    out = []
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        for j in range(top.childCount()):
            out.append((top.text(0), [top.child(j).text(c)
                                      for c in range(8)]))
    return out


def store(win):
    return panel_of(win)._controller.store


def spec(name, role, **kw):
    materials = plugin("model.materials")
    return materials.MaterialSpec(name, role=materials.Role(role), **kw)


def test_a_material_role_changes_the_list_and_undoes(win, user_dir):
    win.viewport.scene.groups.append(
        board(0.6, 0.4, 0.018, name="Side", paint={"W+": "Fita"}))
    panel = refresh(win)
    assert lines(panel)[0][1][7] == "?"                     # Fita: no role

    store(win).save_materials([spec("Fita", "edge_band")], remember=True)
    panel = refresh(win)
    side = lines(panel)[0][1]
    assert side[5] == "L1" and side[7] == ""
    saved = json.loads((user_dir / "defaults.json").read_text("utf-8"))
    assert saved["materials"]["Fita"]["role"] == "edge_band"

    # The model's copy is one undo step; the user's default stays.
    win.viewport.history.undo()
    store(win).write_user_data({"settings": {"scope_asked": True}})
    panel = refresh(win)
    assert lines(panel)[0][1][7] == "?"


def test_part_settings_are_one_undo_step(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Side"),
                     board(0.5, 0.3, 0.018, at=(1, 0, 0), name="Shelf")]
    panel = refresh(win)
    controller = panel._controller
    shelf = next(g for g in scene.groups if g.name == "Shelf")
    over = plugin("model.parts").PartOverride(exclude=True, note="stock")
    assert controller.store.set_overrides({shelf: over})
    assert shelf.ext["cutlist"] == {"schema": 1, "exclude": True,
                                    "note": "stock"}
    panel = refresh(win)
    titles = [panel.tree.topLevelItem(i).text(0)
              for i in range(panel.tree.topLevelItemCount())]
    assert any(t.startswith("Excluded") for t in titles)

    win.viewport.history.undo()
    assert not (shelf.ext or {}).get("cutlist")


def test_group_numbers_stay_with_their_parts(win):
    scene = win.viewport.scene
    a = board(0.6, 0.4, 0.018)
    b = board(0.5, 0.3, 0.015, at=(1, 0, 0))
    scene.groups += [a, b]
    panel = refresh(win)
    names = sorted(row[1][0] for row in lines(panel))
    assert names == ["Group #1", "Group #2"]
    number_b = store(win).numbers([b.uid])[b.uid]

    # Only b selected: it keeps its number, it does not become #1.
    scene.selection.clear()
    scene.selection.add(b)
    panel = refresh(win)
    assert [row[1][0] for row in lines(panel)] == [f"Group #{number_b}"]
    # Handing out numbers is bookkeeping: no undo step was added for it.
    assert not win.viewport.history.undo_stack


def test_components_only(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Side")]
    s = store(win)
    s.save_model_setting(include_groups=False)
    panel = refresh(win)
    assert "1 groups left out" in panel.scope_label.text()


def test_units_of_the_cut_list(win):
    scene = win.viewport.scene
    scene.groups += [board(0.6, 0.4, 0.018, name="Side")]
    store(win).save_model_setting(unit="mm")
    panel = refresh(win)
    side = lines(panel)[0][1]
    assert side[2:5] == ["600 mm", "400 mm", "18 mm"]


def test_first_use_asks_once(qt_app, tmp_path, monkeypatch, user_dir):
    """Without the scope answered, Refresh shows the scope window first;
    "don't show again" (on by default there) stores the answer."""
    import shutil
    import sys

    import core.extensions as extensions

    from tests.host.conftest import PACKAGE
    plugins = tmp_path / "plugins"
    shutil.copytree(PACKAGE, plugins / "cutlist")
    monkeypatch.setattr(extensions, "plugin_dirs", lambda: [plugins])
    for name in [n for n in sys.modules
                 if n.startswith("ingetrazo_plugin_cutlist")]:
        monkeypatch.delitem(sys.modules, name)
    from views.main_window import MainWindow
    w = MainWindow()
    try:
        shown = []
        dialogs = plugin("ui.dialogs")
        monkeypatch.setattr(dialogs.SettingsDialog, "exec",
                            lambda self: shown.append(self) or 1)
        refresh(w)
        assert len(shown) == 1 and shown[0].dont_ask.isChecked()
        saved = json.loads((user_dir / "defaults.json").read_text("utf-8"))
        assert saved["settings"]["scope_asked"] is True
        refresh(w)
        assert len(shown) == 1                      # not asked again
    finally:
        w._saved_version = w.viewport.scene.version
        w.close()


def test_materials_dialog_edits(qt_app, win):
    dialogs = plugin("ui.dialogs")
    materials = plugin("model.materials")
    dlg = dialogs.MaterialsDialog({"MDF", "Fita"}, materials.Library(),
                                  focus="Fita")
    dlg.role.setCurrentIndex(dlg.role.findData(materials.Role.EDGE_BAND))
    dlg.thickness.setText("1")
    dlg.thickness.textEdited.emit("1")
    (result,) = dlg.result_specs()
    assert result.name == "Fita" and result.role is materials.Role.EDGE_BAND
    assert abs(result.thickness - 0.001) < 1e-12
