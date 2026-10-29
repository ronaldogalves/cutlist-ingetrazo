# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Plan shapes drawn with QPainter — the same drawing on screen and in the
PDF (QPdfWriter), from :mod:`..export.plan`."""
from __future__ import annotations

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPolygonF,
)

from ..export.plan import STYLES, Page, Shape, arrow_head

_ALIGN = {"left": Qt.AlignmentFlag.AlignLeft,
          "center": Qt.AlignmentFlag.AlignHCenter,
          "right": Qt.AlignmentFlag.AlignRight}


def draw_shapes(painter: QPainter, shapes, k: float, *, dx: float = 0.0,
                dy: float = 0.0, highlight: set | None = None) -> None:
    """``k``: device pixels per mm; (dx, dy) an offset in mm. Parts whose
    key is in ``highlight`` are drawn marked (the window's mouse)."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont(painter.font())
    # The same face on every machine and in every PDF.
    font.setFamilies(["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"])
    for s in shapes:
        st = STYLES.get(s.style, {})
        x, y, w, h = (s.x + dx) * k, (s.y + dy) * k, s.w * k, s.h * k
        if s.kind == "rect":
            fill = st.get("fill")
            if highlight and s.ref in highlight and s.style == "part":
                fill = "#ffe08a"
            painter.setBrush(QBrush(QColor(fill)) if fill
                             else Qt.BrushStyle.NoBrush)
            stroke = st.get("stroke")
            painter.setPen(QPen(QColor(stroke), max(st.get("width", 0.2) * k,
                                                    0.6))
                           if stroke else Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(x, y, w, h))
        elif s.kind == "line":
            colour = QColor(st.get("stroke", "#000"))
            if highlight and s.ref in highlight:
                colour = QColor("#d32f2f")
            painter.setPen(QPen(colour, max(st.get("width", 0.2) * k, 0.6)))
            painter.drawLine(QPointF(x, y), QPointF(x + w, y + h))
            if s.style == "grain":
                painter.setBrush(colour)
                painter.drawPolygon(QPolygonF([
                    QPointF((px + dx) * k, (py + dy) * k)
                    for px, py in arrow_head(s)]))
        elif s.kind == "text" and s.text:
            font.setPixelSize(max(1, round(s.size * k)))
            font.setBold(bool(st.get("bold")))
            painter.setFont(font)
            painter.setPen(QColor(st.get("color", "#000")))
            painter.drawText(QRectF(x, y, w, h),
                             _ALIGN[s.align] | Qt.AlignmentFlag.AlignVCenter,
                             s.text)


def write_pdf(path: str, pages: list[Page], size: str = "A4") -> None:
    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4 if size == "A4"
                                 else QPageSize.PageSizeId.Letter))
    writer.setPageOrientation(QPageLayout.Orientation.Portrait)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    writer.setResolution(600)
    writer.setTitle("Cut List")
    k = writer.resolution() / 25.4
    painter = QPainter(writer)
    try:
        for i, page in enumerate(pages):
            if i:
                writer.newPage()
            draw_shapes(painter, page.shapes, k)
    finally:
        painter.end()


def shape_at(shapes: list[Shape], x: float, y: float, kinds=("part",)):
    """The topmost shape of a style in ``kinds`` under (x, y) mm."""
    for s in reversed(shapes):
        if s.kind == "rect" and s.style in kinds and \
                s.x <= x <= s.x + s.w and s.y <= y <= s.y + s.h:
            return s
    return None
