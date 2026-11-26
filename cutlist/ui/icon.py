# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The Cut List logo, drawn in code: a sheet cut into pieces, one of them
filled — a cutting diagram, which is what the extension makes.

IngeTrazo draws its own tab icons with QPainter in the theme's ink, so
they read on light and dark themes alike; an image of ours would be the
one tab that does not. So the logo is drawn the same way, and drawn
**each time it is painted** (a :class:`QIconEngine`), with the ink and
accent asked for then: a change of theme or accent colour shows at once,
with nothing for IngeTrazo to redraw. No image files, no QtSvg.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPen, QPixmap

#: The logo's red, when the host gives no accent colour.
LOGO_RED = QColor(230, 0, 0)
_FALLBACK_INK = QColor(128, 128, 128)

# The drawing, as fractions of the sheet: the long top piece, two short
# ones below it on the left, the filled piece on the right.
_TOP = 0.42           # where the first rip ends the top piece
_SPLIT = 0.66         # where the crosscut ends the two left pieces


def draw_logo(p: QPainter, rect: QRectF, ink: QColor,
              accent: QColor) -> None:
    """The logo in ``rect``: outlines in ``ink``, the cut piece in
    ``accent``. The line weight follows the size, as IngeTrazo's own icons
    (about 1 px at the tray's 20 px)."""
    side = min(rect.width(), rect.height())
    w = max(1.0, side * 0.065)
    m = w / 2 + side * 0.04
    s = QRectF(rect.center().x() - side / 2 + m,
               rect.center().y() - side / 2 + m, side - 2 * m, side - 2 * m)
    y_rip = s.top() + s.height() * _TOP
    x_cross = s.left() + s.width() * _SPLIT
    y_mid = (y_rip + s.bottom()) / 2
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    p.fillRect(QRectF(QPointF(x_cross, y_rip), s.bottomRight()), accent)
    pen = QPen(ink, w)
    pen.setJoinStyle(Qt.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRect(s)
    p.drawLine(QPointF(s.left(), y_rip), QPointF(s.right(), y_rip))
    p.drawLine(QPointF(x_cross, y_rip), QPointF(x_cross, s.bottom()))
    p.drawLine(QPointF(s.left(), y_mid), QPointF(x_cross, y_mid))
    p.restore()


class _LogoEngine(QIconEngine):
    """Paints the logo with the colours in force at paint time."""

    def __init__(self, ink: Callable[[], QColor] | None,
                 accent: Callable[[], QColor] | None) -> None:
        super().__init__()
        self._ink, self._accent = ink, accent

    def _colours(self) -> tuple[QColor, QColor]:
        try:
            ink = QColor(self._ink()) if self._ink else _FALLBACK_INK
        except Exception:           # never break a tab over its icon
            ink = _FALLBACK_INK
        try:
            accent = QColor(self._accent()) if self._accent else LOGO_RED
        except Exception:
            accent = LOGO_RED
        return ink, accent

    def paint(self, painter, rect, mode, state) -> None:
        ink, accent = self._colours()
        if mode == QIcon.Mode.Disabled:
            ink.setAlphaF(0.4)
            accent.setAlphaF(0.4)
        draw_logo(painter, QRectF(rect), ink, accent)

    def pixmap(self, size, mode, state) -> QPixmap:
        pm = QPixmap(size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        self.paint(p, pm.rect(), mode, state)
        p.end()
        return pm

    def actualSize(self, size, mode, state) -> QSize:
        return size

    def clone(self) -> QIconEngine:
        return _LogoEngine(self._ink, self._accent)


def logo_icon(ink: Callable[[], QColor] | None = None,
              accent: Callable[[], QColor] | None = None) -> QIcon:
    """The logo as a :class:`QIcon`. ``ink`` and ``accent`` are asked for
    the colours each time it is painted (the host's theme); without them,
    grey and the logo's red."""
    return QIcon(_LogoEngine(ink, accent))


__all__ = ["LOGO_RED", "draw_logo", "logo_icon"]
