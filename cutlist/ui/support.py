# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Support Cut List: how to donate, and what this extension is (D-005).

Opened only from the menu or the panel's link: no pop-up ever opens it by
itself, and nothing here touches the network — a link opens the browser
only when the user clicks it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..i18n import tr

#: A PIX random key (chave aleatória): no personal data in it.
PIX_KEY = "5cebc350-88a6-4bb2-b2e9-08e82b33f36a"
PIX_QR = Path(__file__).with_name("pix.png")
SPONSORS_URL = "https://github.com/sponsors/ronaldogalves"
REPOSITORY_URL = "https://github.com/ronaldogalves/cutlist-ingetrazo"
ISSUES_URL = REPOSITORY_URL + "/issues"


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class SupportDialog(QDialog):
    def __init__(self, version: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_support")
        self.setWindowTitle(tr("Support Cut List"))
        box = QVBoxLayout(self)

        about = QLabel(tr(
            "<b>Cut List for IngeTrazo</b> {version}<br>Free software "
            "(GPL-3.0-or-later), made by a woodworker and furniture "
            "designer in Brazil.<br><br>If it saves you "
            "time in the shop, you can help keep it going. Every "
            "contribution counts; nothing changes in the extension "
            "either way.", version=version))
        about.setWordWrap(True)
        box.addWidget(about)

        pix = QGroupBox(tr("PIX (Brazil)"))
        pbox = QHBoxLayout(pix)
        self.qr = QLabel()
        self.qr.setObjectName("cutlist_support_qr")
        image = QPixmap(str(PIX_QR))
        if not image.isNull():
            self.qr.setPixmap(image.scaled(
                200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        pbox.addWidget(self.qr)
        right = QVBoxLayout()
        right.addWidget(QLabel(tr("Scan the code in your bank's app, or "
                                  "copy the key:")))
        self.key = QLineEdit(PIX_KEY)
        self.key.setObjectName("cutlist_support_key")
        self.key.setReadOnly(True)
        self.key.setMinimumWidth(280)
        right.addWidget(self.key)
        self.copy_button = QPushButton(tr("Copy the key"))
        self.copy_button.clicked.connect(lambda _c=False: self.copy_key())
        right.addWidget(self.copy_button)
        self.copied = QLabel()
        right.addWidget(self.copied)
        right.addStretch(1)
        pbox.addLayout(right)
        box.addWidget(pix)

        abroad = QGroupBox(tr("From anywhere"))
        abox = QVBoxLayout(abroad)
        abox.addWidget(QLabel(tr("Once or monthly, by card, through GitHub "
                                 "Sponsors:")))
        sponsor = QPushButton(tr("Open GitHub Sponsors"))
        sponsor.setObjectName("cutlist_support_sponsors")
        sponsor.setToolTip(SPONSORS_URL)
        sponsor.clicked.connect(lambda _c=False: open_url(SPONSORS_URL))
        abox.addWidget(sponsor)
        box.addWidget(abroad)

        other = QLabel(tr(
            "Other ways to help: tell other woodworkers, send a profile for "
            "your supplier, report a problem."))
        other.setWordWrap(True)
        box.addWidget(other)
        links = QHBoxLayout()
        for text, url in ((tr("The project's page"), REPOSITORY_URL),
                          (tr("Report a problem"), ISSUES_URL)):
            b = QPushButton(text)
            b.setToolTip(url)
            b.clicked.connect(lambda _c=False, u=url: open_url(u))
            links.addWidget(b)
        links.addStretch(1)
        box.addLayout(links)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)

    def copy_key(self) -> None:
        QGuiApplication.clipboard().setText(PIX_KEY)
        self.copied.setText(tr("Copied."))
