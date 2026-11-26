# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Laminate and band drawn as 2D objects over stacked boards (D-019), in
a real IngeTrazo window."""
from __future__ import annotations

from tests.host.conftest import panel_of, plugin
from tests.host.scenes import board, surface


def titles(tree):
    return [tree.topLevelItem(i).text(0)
            for i in range(tree.topLevelItemCount())]


def test_drawn_laminate_and_band_are_listed(win):
    scene = win.viewport.scene
    # Two 18 mm boards glued into a 36 mm top: one laminate sheet on top,
    # one band strip along the front of the stack.
    scene.groups += [
        board(1.2, 0.6, 0.018, default="Ply", name="Top low"),
        board(1.2, 0.6, 0.018, at=(0, 0, 0.018), default="Ply",
              name="Top high"),
        surface([(0, 0, 0.036), (1.2, 0, 0.036), (1.2, 0.6, 0.036),
                 (0, 0.6, 0.036)], "Formica", name="Top laminate"),
        surface([(0, 0, 0), (1.2, 0, 0), (1.2, 0, 0.036), (0, 0, 0.036)],
                "Fita", name="Front band"),
    ]
    panel = panel_of(win)
    mats = plugin("model.materials")
    panel._controller.store.save_materials([
        mats.MaterialSpec("Ply"),
        mats.MaterialSpec("Formica", role=mats.Role.COVERING,
                          thickness=0.0008),
        mats.MaterialSpec("Fita", role=mats.Role.EDGE_BAND)],
        remember=False)
    panel.refresh_button.click()

    shown = titles(panel.tree)
    assert shown[0].startswith("Ply")
    assert any(t.startswith("Covering Formica") for t in shown)
    assert any(t.startswith("Edge band pieces") for t in shown)
    assert not any(t.startswith("Excluded") for t in shown)
    bands = panel.bands.topLevelItem(0)
    assert bands.text(0) == "Fita" and bands.text(2) == "1"
