# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Install the extension into a running IngeTrazo window.

Builds the side-tray panel and our submenu in Extensions. Nothing is
computed here yet: the panel is the frame later milestones fill.
"""
from __future__ import annotations

import logging

from .. import i18n
from ..i18n import tr

log = logging.getLogger("cutlist")

#: Stable panel name: IngeTrazo remembers where the user put the panel by
#: the dock's object name (``extension_<key>``), so do not change it.
PANEL_TITLE = "Cut List"


def install(app) -> None:
    """Called once from :func:`cutlist.setup` with IngeTrazo's
    ``ExtensionApp``."""
    from core.i18n import current_language
    i18n.set_language_source(current_language)

    from ..ui.panel import CutListPanel
    panel = CutListPanel()
    dock = app.add_panel(tr(PANEL_TITLE), panel)

    menu = app.add_menu(tr(PANEL_TITLE))
    if menu is not None:
        action = menu.addAction(tr("Show the cut list panel"))
        action.setStatusTip(tr("Bring the Cut List tab to the front."))
        action.triggered.connect(lambda _checked=False: app.show_panel(dock))
    log.info("Cut List installed (key %r)", app.key)
