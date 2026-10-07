# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The Cut List tab in IngeTrazo's side tray.

For now a placeholder, so the extension is visible and the wiring is
proven; the cut list itself arrives in M1.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..i18n import tr


class CutListPanel(QWidget):
    """The tray tab. Holds no document state: the host refreshes it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_panel")
        layout = QVBoxLayout(self)
        message = QLabel(tr("The cut list will appear here."))
        message.setObjectName("cutlist_placeholder")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch(1)
