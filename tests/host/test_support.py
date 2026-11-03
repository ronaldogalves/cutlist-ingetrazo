# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Support Cut List (D-005): opened only on request, the PIX key copies,
the QR code ships in the zip, nothing reaches the network by itself."""
from __future__ import annotations

from tests.host.conftest import panel_of, plugin


def test_the_support_window(qt_app, win, monkeypatch):
    support = plugin("ui.support")
    opened = []
    monkeypatch.setattr(support, "open_url", opened.append)
    dlg = support.SupportDialog("0.2.1")
    assert not dlg.qr.pixmap().isNull()             # the QR code ships
    assert dlg.key.text() == support.PIX_KEY
    dlg.copy_button.click()
    from PySide6.QtGui import QGuiApplication
    assert QGuiApplication.clipboard().text() == support.PIX_KEY
    assert not opened                               # nothing by itself
    from PySide6.QtWidgets import QPushButton
    dlg.findChild(QPushButton, "cutlist_support_sponsors").click()
    assert opened == [support.SPONSORS_URL]
    dlg.deleteLater()


def test_the_panel_link_opens_it(qt_app, win, monkeypatch):
    panel = panel_of(win)
    calls = []
    monkeypatch.setattr(panel._controller, "open_support",
                        lambda: calls.append(1))
    panel.support_requested.disconnect()
    panel.support_requested.connect(panel._controller.open_support)
    panel.support_link.linkActivated.emit("#support")
    assert calls == [1]
