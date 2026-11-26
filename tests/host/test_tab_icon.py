# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The tray tab shows our logo, drawn in IngeTrazo's ink and accent."""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor

from tests.host.conftest import plugin


def _colours(icon, size=48):
    img = icon.pixmap(QSize(size, size)).toImage()
    return {img.pixelColor(x, y).rgb() for x in range(size)
            for y in range(size) if img.pixelColor(x, y).alpha() == 255}


def test_the_tab_shows_the_logo(qt_app, win):
    dock = win.extension_panels()["extension_cutlist"]
    icon = dock.windowIcon()
    assert not icon.isNull()
    from views.theme import accent_color
    assert accent_color().rgb() in _colours(icon)   # the cut piece


def test_the_logo_follows_the_colours_at_paint_time(qt_app, win):
    ink = [QColor(10, 20, 30)]
    icon = plugin("ui.icon").logo_icon(lambda: ink[0],
                                       lambda: QColor(200, 0, 0))
    assert QColor(10, 20, 30).rgb() in _colours(icon)
    ink[0] = QColor(220, 220, 220)                  # the theme changed
    assert QColor(220, 220, 220).rgb() in _colours(icon)
