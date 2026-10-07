# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Install the extension into a running IngeTrazo window.

Builds the side-tray panel and our submenu in Extensions, and wires the
panel to the scene through :class:`Controller`: Refresh reads the model,
a click on a line highlights its parts in the viewport, an edit marks the
list out of date. Recompute is on demand, never on every edit.
"""
from __future__ import annotations

import logging

import numpy as np

from .. import i18n
from ..i18n import tr
from ..model.grouping import build
from ..model.materials import Library
from ..model.parts import RawPart, read_part
from .extract import extract

log = logging.getLogger("cutlist")

#: Stable panel name: IngeTrazo remembers where the user put the panel by
#: the dock's object name (``extension_<key>``), so do not change it.
PANEL_TITLE = "Cut List"

#: Highlight colour for the parts of the selected lines.
_HIGHLIGHT = (0, 150, 255)


def install(app) -> None:
    """Called once from :func:`cutlist.setup` with IngeTrazo's
    ``ExtensionApp``."""
    from core.i18n import current_language
    i18n.set_language_source(current_language)

    from ..ui.panel import CutListPanel
    panel = CutListPanel()
    dock = app.add_panel(tr(PANEL_TITLE), panel)
    controller = Controller(app, panel)
    dock.visibilityChanged.connect(controller.panel_shown)
    # Keep the controller alive as long as the panel.
    panel._controller = controller

    menu = app.add_menu(tr(PANEL_TITLE))
    if menu is not None:
        action = menu.addAction(tr("Show the cut list panel"))
        action.setStatusTip(tr("Bring the Cut List tab to the front."))
        action.triggered.connect(lambda _checked=False: app.show_panel(dock))
    log.info("Cut List installed (key %r)", app.key)


def number_auto_named(parts: list[RawPart]) -> list[RawPart]:
    """Give parts that only have IngeTrazo's automatic name a "Group #n".

    For now the numbers follow the parts' uids, so they hold while the
    same parts exist; storing them in the document (D-006 §8) comes with
    the per-part settings."""
    from dataclasses import replace
    auto = sorted(p.uid for p in parts if p.auto_named)
    number = {uid: i for i, uid in enumerate(auto, start=1)}
    return [replace(p, name=tr("Group #{n}", n=number[p.uid]))
            if p.uid in number else p for p in parts]


def fmt_sheet_area(square_metres: float) -> str:
    """Board area the way it is bought: m² (ft² in imperial models) —
    never mm², whatever the model's length unit."""
    from core.units import model_unit
    if model_unit() in ("in", "ft", "ft-in", "in-frac", "ft-in-frac"):
        return f"{square_metres / 0.09290304:.2f} ft²"
    return f"{square_metres:.2f} m²"


class Controller:
    """Between the panel and the scene. Every entry point is guarded: a
    failure here is logged and shown, never raised into IngeTrazo."""

    def __init__(self, app, panel) -> None:
        self.app = app
        self.panel = panel
        self.excluded_tags: frozenset[str] = frozenset()
        self.highlight: list[str] = []
        self.outlines: dict = {}
        self.stale = True
        from core.units import fmt_len_fine
        panel.set_formatters(fmt_len_fine, fmt_sheet_area)
        panel.refresh_requested.connect(self.refresh)
        panel.highlight_requested.connect(self.set_highlight)
        panel.tags_changed.connect(self.set_excluded_tags)
        app.on_document_changed(self.document_changed)
        app.add_overlay(self.draw)

    # ---- reading the model ---------------------------------------------
    def refresh(self) -> None:
        try:
            ex = extract(self.app.scene, excluded_tags=self.excluded_tags)
            library = Library()
            parts = [read_part(r, library)
                     for r in number_auto_named(ex.parts)]
            cut_list = build(parts)
        except Exception as exc:                # noqa: BLE001 — UI boundary
            log.exception("reading the model failed")
            self._status(tr("Cut List could not read the model: {error}",
                            error=f"{type(exc).__name__}: {exc}"))
            return
        self.outlines = ex.outlines
        self.highlight = []
        self.panel.set_tags(ex.tags, self.excluded_tags)
        self.panel.show_cut_list(cut_list, scope=ex.scope,
                                 filtered_out=ex.filtered_out,
                                 notices=ex.notices)
        self.stale = False
        self.app.viewport.update()

    def set_excluded_tags(self, tags) -> None:
        self.excluded_tags = frozenset(tags)
        self.refresh()

    def document_changed(self) -> None:
        self.stale = True
        self.panel.set_stale(True)
        if self.highlight:
            self.highlight = []
            self.app.viewport.update()

    def panel_shown(self, visible: bool) -> None:
        if visible and self.stale:
            self.refresh()

    # ---- the viewport highlight ----------------------------------------
    def set_highlight(self, uids) -> None:
        self.highlight = list(uids)
        self.app.viewport.update()

    def draw(self, viewport, painter) -> None:
        if not self.highlight:
            return
        segs = [self.outlines[u] for u in self.highlight
                if u in self.outlines and len(self.outlines[u])]
        if not segs:
            return
        from PySide6.QtCore import QLineF
        from PySide6.QtGui import QColor, QPen
        pts = np.concatenate(segs).reshape(-1, 3)
        px, py, front = (np.asarray(a) for a in self.app.world_to_pixels(pts))
        keep = front[0::2] & front[1::2]
        x0, y0 = px[0::2][keep], py[0::2][keep]
        x1, y1 = px[1::2][keep], py[1::2][keep]
        pen = QPen(QColor(*_HIGHLIGHT))
        pen.setWidthF(2.5)
        painter.setPen(pen)
        painter.drawLines([QLineF(a, b, c, d)
                           for a, b, c, d in zip(x0, y0, x1, y1, strict=True)])

    def _status(self, message: str) -> None:
        flash = getattr(self.app.viewport, "flash_status", None)
        if callable(flash):
            flash(message, 6000)
