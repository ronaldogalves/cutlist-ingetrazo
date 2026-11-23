# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""A layout that wraps its widgets onto as many rows as the width needs.

The panel's buttons used to sit in one row, so the panel asked for about
a thousand pixels of width — and the side tray, whose tabs share one
width, could not shrink for any of them (issue #3). Here they wrap, and
the panel is as narrow as its widest button.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing: int = 4) -> None:
        super().__init__(parent)
        self._items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:                # noqa: N802 — Qt API
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):                        # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):                        # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) \
            else None

    def expandingDirections(self):                  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:            # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:    # noqa: N802
        return self._arrange(QRect(0, 0, width, 0), move=False)

    def setGeometry(self, rect) -> None:            # noqa: N802
        super().setGeometry(rect)
        self._arrange(rect, move=True)

    def sizeHint(self) -> QSize:                    # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:                 # noqa: N802
        """The widest single item: the layout wraps everything else."""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _arrange(self, rect: QRect, move: bool) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, row = area.x(), area.y(), 0
        gap = self.spacing()
        for item in self._items:
            if item.widget() is not None and item.widget().isHidden():
                continue
            hint = item.sizeHint()
            if x > area.x() and x + hint.width() > area.right() + 1:
                x, y, row = area.x(), y + row + gap, 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + gap
            row = max(row, hint.height())
        return y + row - rect.y() + m.bottom()

