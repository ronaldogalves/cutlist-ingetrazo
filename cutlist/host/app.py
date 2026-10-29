# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Install the extension into a running IngeTrazo window.

Builds the side-tray panel and our submenu in Extensions, and wires the
panel to the scene through :class:`Controller`: Refresh reads the model
with the settings in force, the dialogs change those settings, a click on
a line highlights its parts in the viewport, an edit marks the list out of
date. Recompute is on demand, never on every edit.
"""
from __future__ import annotations

import logging
from dataclasses import replace

import numpy as np

from .. import i18n
from ..i18n import tr
from ..model.grouping import build
from ..model.parts import RawPart, read_part
from ..model.settings import Settings
from .extract import extract
from .store import Store

log = logging.getLogger("cutlist")

#: Stable panel name: IngeTrazo remembers where the user put the panel by
#: the dock's object name (``extension_<key>``), so do not change it.
PANEL_TITLE = "Cut List"

#: Highlight colour for the parts of the selected lines.
_HIGHLIGHT = (0, 150, 255)

_IMPERIAL = ("in", "ft", "ft-in", "in-frac", "ft-in-frac")


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
    app.add_context_menu(controller.viewport_menu)
    # Keep the controller alive as long as the panel.
    panel._controller = controller

    menu = app.add_menu(tr(PANEL_TITLE))
    if menu is not None:
        action = menu.addAction(tr("Show the cut list panel"))
        action.setStatusTip(tr("Bring the Cut List tab to the front."))
        action.triggered.connect(lambda _checked=False: app.show_panel(dock))
        menu.addAction(tr("Materials…")).triggered.connect(
            lambda _c=False: controller.open_materials(None))
        menu.addAction(tr("Settings…")).triggered.connect(
            lambda _c=False: controller.open_settings())
        menu.addAction(tr("Export…")).triggered.connect(
            lambda _c=False: controller.open_export())
        menu.addAction(tr("Cutting diagrams…")).triggered.connect(
            lambda _c=False: controller.open_diagrams())
        menu.addAction(tr("Labels…")).triggered.connect(
            lambda _c=False: controller.open_labels())
    log.info("Cut List installed (key %r)", app.key)


def fmt_sheet_area(square_metres: float) -> str:
    """Board area the way it is bought: m² (ft² in imperial models) —
    never mm², whatever the model's length unit."""
    from core.units import model_unit
    if model_unit() in _IMPERIAL:
        return f"{square_metres / 0.09290304:.2f} ft²"
    return f"{square_metres:.2f} m²"


def fmt_run_length(metres: float) -> str:
    """Band to buy: metres (feet in imperial models), one decimal."""
    from core.units import model_unit
    if model_unit() in _IMPERIAL:
        return f"{metres / 0.3048:.1f} ft"
    return f"{metres:.1f} m"


#: Units whose numbers read fine bare, and metres per unit. Feet-and-inch
#: and fractional forms keep their marks: they are part of the number.
_BARE = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254, "ft": 0.3048}


def length_formats(settings: Settings):
    """``(cell, full, unit)``: how a size is written in a table cell, how
    it is written in running text, and the unit for the column titles
    (``None`` when the cells carry it themselves).

    The unit is the model's (at least to the millimetre, as IngeTrazo's
    ``fmt_len_fine``) or the one set in Settings."""
    from core.units import fine_precision, format_length, model_unit
    unit = settings.unit or model_unit()
    precision = settings.precision
    if precision is None and settings.unit is None:
        precision = fine_precision()
    if precision is None:
        fine = settings.tolerance < 0.001
        precision = {"mm": 1 if fine else 0, "cm": 2 if fine else 1,
                     "m": 3, "in": 2, "ft": 3, "in-frac": 3, "ft-in": 2,
                     "ft-in-frac": 3}.get(unit, 2)

    def full(metres):
        return format_length(float(metres), unit, precision)
    if settings.units_in_cells or unit not in _BARE:
        return full, full, None
    per = _BARE[unit]

    def cell(metres):
        return f"{float(metres) / per:.{precision}f}"
    return cell, full, unit


def renamed(parts: list[RawPart], numbers: dict[str, int]) -> list[RawPart]:
    """Parts that only have IngeTrazo's automatic name become "Group #n",
    with the number stored for them (D-008)."""
    return [replace(p, name=tr("Group #{n}", n=numbers[p.uid]))
            if p.uid in numbers else p for p in parts]


def leaf_parts(groups) -> list:
    """The parts (leaf containers with faces) in or under ``groups``."""
    out, seen = [], set()

    def walk(g):
        kids = list(getattr(g, "children", None) or ())
        if kids:
            for c in kids:
                walk(c)
        elif getattr(g, "mesh", None) is not None and g.mesh.faces \
                and id(g) not in seen:
            seen.add(id(g))
            out.append(g)
    for g in groups:
        walk(g)
    return out


class Controller:
    """Between the panel and the scene. Every entry point is guarded: a
    failure here is logged and shown, never raised into IngeTrazo."""

    def __init__(self, app, panel) -> None:
        self.app = app
        self.panel = panel
        self.store = Store(app)
        self.highlight: list[str] = []
        self.outlines: dict = {}
        self.groups: dict = {}
        self.materials_seen: set[str] = set()
        self.tags_seen: set[str] = set()
        # The last list read, for the export window and the dialogs.
        self.cut_list = None
        self.parts: dict = {}
        self.overrides: dict = {}
        self.library = None
        self.stale = True
        self.diagram_window = None
        # While IngeTrazo builds its window the panel may "show": no
        # reading (and no questions) until the app is actually running.
        self._starting = True
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._started)
        panel.set_formatters(*length_formats(Settings()), fmt_sheet_area)
        panel.refresh_requested.connect(lambda: self.refresh(ask=True))
        panel.highlight_requested.connect(self.set_highlight)
        panel.tags_changed.connect(self.set_excluded_tags)
        panel.merge_changed.connect(self.set_merge)
        panel.materials_requested.connect(self.open_materials)
        panel.settings_requested.connect(self.open_settings)
        panel.part_settings_requested.connect(self.open_part_settings)
        panel.export_requested.connect(self.open_export)
        panel.diagrams_requested.connect(self.open_diagrams)
        panel.labels_requested.connect(lambda: self.open_labels())
        app.on_document_changed(self.document_changed)
        app.add_overlay(self.draw)

    def _started(self) -> None:
        self._starting = False

    # ---- reading the model ---------------------------------------------
    def refresh(self, ask: bool = False) -> None:
        try:
            settings = self.store.settings()
            if ask and not settings.scope_asked:
                self.open_settings(first_run=True, then_refresh=False)
                settings = self.store.settings()
            ex = extract(self.app.scene,
                         use_selection=settings.use_selection,
                         excluded_tags=frozenset(settings.excluded_tags),
                         include_groups=settings.include_groups)
            library = self.store.library()
            overrides = self.store.overrides(ex.groups.values())
            numbers = self.store.numbers(
                [r.uid for r in ex.parts if r.auto_named])
            parts = [read_part(r, library, overrides.get(r.uid))
                     for r in renamed(ex.parts, numbers)]
            cut_list = build(parts, settings.tolerance,
                             by_name=not settings.merge_by_size)
            self.panel.set_formatters(*length_formats(settings),
                                      fmt_sheet_area)
            self.panel.set_library(library)
            self.panel.set_run_format(fmt_run_length)
        except Exception as exc:                # noqa: BLE001 — UI boundary
            self._failed(exc, tr("Cut List could not read the model: "
                                 "{error}", error=f"{type(exc).__name__}: "
                                                  f"{exc}"))
            return
        self.outlines = ex.outlines
        self.groups = ex.groups
        self.cut_list = cut_list
        self.parts = {p.uid: p for p in parts}
        self.overrides = overrides
        self.library = library
        self.materials_seen = ex.materials
        self.tags_seen = ex.tags
        self.highlight = []
        self.panel.set_tags(ex.tags, settings.excluded_tags)
        self.panel.set_merge(settings.merge_by_size)
        self.panel.show_cut_list(cut_list, scope=ex.scope,
                                 filtered_out=ex.filtered_out,
                                 not_components=ex.not_components,
                                 notices=ex.notices)
        self.stale = False
        self.app.viewport.update()

    def set_excluded_tags(self, tags) -> None:
        self._guard(lambda: self.store.save_model_setting(
            excluded_tags=tuple(sorted(tags))))
        self.refresh()

    def set_merge(self, by_size: bool) -> None:
        self._guard(lambda: self.store.save_user_setting(
            merge_by_size=bool(by_size)))
        self.refresh()

    def document_changed(self) -> None:
        self.stale = True
        self.panel.set_stale(True)
        if self.highlight:
            self.highlight = []
            self.app.viewport.update()

    def panel_shown(self, visible: bool) -> None:
        if visible and self.stale and not self._starting:
            self.refresh(ask=True)

    # ---- dialogs ---------------------------------------------------------
    def open_materials(self, focus=None) -> None:
        from ..ui.dialogs import MaterialsDialog

        def run():
            library = self.store.library()
            templates = self.store.sheet_templates()
            dlg = MaterialsDialog(set(self.materials_seen), library, focus,
                                  sources=self.store.material_sources(),
                                  templates=templates,
                                  parent=self.app.window)
            if not dlg.exec():
                return False
            if dlg.result_templates() != templates:
                self.store.save_sheet_templates(dlg.result_templates())
            remember = dlg.remember.isChecked()
            changed = False
            if dlg.result_specs():
                self.store.save_materials(dlg.result_specs(),
                                          remember=remember)
                changed = True
            if dlg.result_cleared():
                self.store.clear_materials(dlg.result_cleared(),
                                           remember=remember)
                changed = True
            return changed
        if self._guard(run):
            self.refresh()

    def open_settings(self, first_run: bool = False,
                      then_refresh: bool = True) -> None:
        from ..ui.dialogs import SettingsDialog

        def run():
            dlg = SettingsDialog(self.store.settings(), self.tags_seen,
                                 first_run=first_run,
                                 fields=self.store.fields(),
                                 parent=self.app.window)
            if dlg.exec():
                remember = dlg.remember.isChecked()
                self.store.save_settings(dlg.result(), remember=remember)
                if not first_run:
                    self.store.save_fields(dlg.result_fields(),
                                           remember=remember)
                return True
            return False
        if self._guard(run) and then_refresh:
            self.refresh()

    def open_part_settings(self, uids) -> None:
        self.open_part_settings_for([self.groups[u] for u in uids
                                     if u in self.groups])

    def open_part_settings_for(self, groups) -> bool:
        """True when the parts changed."""
        if not groups:
            return False
        from ..ui.dialogs import PartDialog

        def run():
            overrides = self.store.overrides(groups)
            first = overrides[groups[0].uid]
            fields = self.store.fields()
            part = self.parts.get(groups[0].uid)
            inherited = fields.values(part.tag if part else groups[0].layer)
            dlg = PartDialog(first, len(groups), title=groups[0].name,
                             fields=inherited, parent=self.app.window)
            if dlg.exec():
                result = dlg.result()
                typed = dlg.field_values()
                changes = {}
                for g in groups:
                    own = {} if dlg.clear_fields.isChecked() else \
                        overrides[g.uid].field_values
                    changes[g] = result.with_fields({**own, **typed})
                return self.store.set_overrides(changes)
            return False
        if self._guard(run):
            self.refresh()
            return True
        return False

    # ---- export (D-009) -------------------------------------------------------
    def model_path(self):
        """The open document's file, if it was saved (IngeTrazo keeps it on
        the window; read defensively, the attribute is not public API)."""
        from pathlib import Path
        path = getattr(self.app.window, "_current_path", None)
        return Path(path) if path else None

    def export_folder(self) -> str:
        """Where save windows open: the model's folder; for a model not
        saved yet, the folder last written to; else Documents — never the
        folder IngeTrazo runs from (System32 for the installed app,
        Ronaldo 2026-10-21)."""
        from pathlib import Path

        from PySide6.QtCore import QStandardPaths
        path = self.model_path()
        if path is not None:
            return str(path.parent)
        last = self.store.user_data().get("last_folder")
        if isinstance(last, str) and Path(last).is_dir():
            return last
        docs = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation)
        return docs if docs and Path(docs).is_dir() else str(Path.home())

    def folder_used(self, folder) -> None:
        """Remember where the user writes files (for unsaved models)."""
        from pathlib import Path
        folder = str(Path(folder))
        if self.store.user_data().get("last_folder") != folder:
            self.store.write_user_data({**self.store.user_data(),
                                        "last_folder": folder})

    def part_fields(self) -> dict:
        fields = self.store.fields()
        return {uid: fields.values(p.tag, self.overrides.get(uid).field_values
                                   if uid in self.overrides else None)
                for uid, p in self.parts.items()}

    def export_session(self):
        from datetime import date

        from ..export.rows import boards as board_list
        from ..export.rows import make_rows
        from ..ui.export_dialog import ExportSession
        path = self.model_path()
        context = {"model": path.stem if path else tr("cut list"),
                   "date": date.today().isoformat()}
        fields = self.part_fields()
        bands = sorted({b for p in self.parts.values() for b in p.edges if b},
                       key=str.lower)
        materials = sorted({s.material for s in self.cut_list.sections
                            if s.material}, key=str.lower)
        return ExportSession(
            rows=lambda profile, skip_boards=frozenset(): make_rows(
                self.cut_list, self.parts, self.library, profile,
                part_fields=fields, context=context,
                skip_boards=skip_boards),
            boards=[(key, f"{material or tr('(no material)')} · "
                          f"{self._fmt_mm(thickness)} — "
                          + tr("{n} parts", n=qty))
                    for key, material, thickness, qty
                    in board_list(self.cut_list)],
            profiles=self.store.profiles(), last=self.store.last_profile(),
            save=self.store.save_profiles, materials=materials, bands=bands,
            fields=list(self.store.fields().names),
            write=self.write_files, copy=self.copy_text,
            suggested_folder=self.export_folder())

    @staticmethod
    def _fmt_mm(metres: float) -> str:
        mm = round(metres * 1000, 1)
        return f"{mm:g} mm"

    def open_export(self) -> None:
        if self.cut_list is None or self.stale:
            self.refresh(ask=True)
        if self.cut_list is None:
            return
        from ..ui.export_dialog import ExportDialog

        def run():
            ExportDialog(self.export_session(), parent=self.app.window).exec()
            return True
        self._guard(run)

    def write_files(self, folder: str, files: dict) -> None:
        """Write ``{name: bytes}`` into ``folder``; ask before replacing."""
        from pathlib import Path

        from PySide6.QtWidgets import QMessageBox
        target = Path(folder)
        existing = [n for n in files if (target / n).exists()]
        if existing and QMessageBox.question(
                self.app.window, tr("Cut List — Export"),
                tr("Replace these files?\n{names}",
                   names="\n".join(existing))
        ) != QMessageBox.StandardButton.Yes:
            return
        for name, data in files.items():
            (target / name).write_bytes(data)
        self.folder_used(target)

    def copy_text(self, text: str) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def viewport_menu(self, menu, selection) -> None:
        """Right-click in the viewport: part settings for the selected
        parts (the boards inside a selected cabinet too)."""
        from core.group import Group
        parts = leaf_parts([e for e in selection if isinstance(e, Group)])
        if not parts:
            return
        from PySide6.QtCore import QTimer
        menu.addSeparator()
        act = menu.addAction(tr("Cut List: part settings…"))
        act.triggered.connect(lambda _c=False: QTimer.singleShot(
            0, lambda: self.open_part_settings_for(parts)))

    # ---- cutting diagrams (M3) ------------------------------------------------
    def model_parts(self) -> dict:
        """Every part of the model by uid, whatever the selection and the
        tag filter: a saved layout is checked against all of them, and a
        layout covers the parts it was made for, not today's selection."""
        ex = extract(self.app.scene, use_selection=False,
                     excluded_tags=frozenset(),
                     include_groups=True)
        library = self.store.library()
        overrides = self.store.overrides(ex.groups.values())
        numbers = self.store.numbers([r.uid for r in ex.parts
                                      if r.auto_named])
        self.groups = {**self.groups, **ex.groups}
        self.outlines = {**self.outlines, **ex.outlines}
        return {p.uid: p for p in (read_part(r, library, overrides.get(r.uid))
                                   for r in renamed(ex.parts, numbers))}

    def diagram_session(self):
        from datetime import date

        from ..export.diagrams import changes, prepare, snapshot
        from ..ui.diagram_window import DiagramSession
        path = self.model_path()
        scope = [u for line in self.cut_list.lines() for u in line.uids]

        def prep(scope, leftovers, left_out):
            parts = self.model_parts()
            settings = self.store.settings()
            return prepare([parts[u] for u in scope if u in parts],
                           self.store.library(), settings,
                           by_name=not settings.merge_by_size,
                           leftovers=leftovers, left_out=left_out)

        def snap(plans, leftovers, left_out, bands=()):
            parts = self.model_parts()
            uids = {u for plan in plans for us in plan.uids.values()
                    for u in us}
            from datetime import datetime
            return snapshot(plans, [parts[u] for u in sorted(uids)
                                    if u in parts],
                            created=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            leftovers=leftovers, left_out=left_out,
                            bands=bands)

        def names(uids):
            parts = self.model_parts()
            return [parts[u].name if u in parts else u for u in uids]

        return DiagramSession(
            model=path.stem if path else tr("cut list"),
            date=date.today().isoformat(), scope=scope, prepare=prep,
            settings=self.store.settings,
            save_settings=self.store.save_model_setting,
            part_action=self.diagram_part_action,
            show_in_model=self.set_highlight, ask_sizes=self.ask_sheet_sizes,
            options=self.store.plan_options(),
            save_options=self.store.save_plan_options,
            layouts=self.store.layouts, save_layout=self.store.save_layout,
            snapshot=snap,
            changes=lambda data: changes(data, self.model_parts()),
            names=names, folder_used=self.folder_used,
            selected=self.selected_uids,
            open_labels=self.open_labels,
            suggested_folder=self.export_folder())

    def selected_uids(self) -> set:
        """The parts selected in the model: the boards inside a selected
        cabinet count too."""
        from core.group import Group
        chosen = [e for e in self.app.scene.selection if isinstance(e, Group)]
        return {g.uid for g in leaf_parts(chosen)}

    def open_diagrams(self, saved: str | None = None) -> None:
        if self.cut_list is None or self.stale:
            self.refresh(ask=True)
        if self.cut_list is None:
            return
        from ..ui.diagram_window import DiagramWindow

        def run():
            if self.diagram_window is not None:
                self.diagram_window.close()
            window = DiagramWindow(self.diagram_session(), saved=saved,
                                   parent=self.app.window)
            if window.cancelled:            # sheet sizes not given: stop
                window.deleteLater()
                self.diagram_window = None
                return False
            self.diagram_window = window
            window.show()
            return True
        self._guard(run)

    def diagram_part_action(self, action: str, uids) -> bool:
        """A part fixed on the diagram (D-014 §2): written to the part in
        the model, one undo step; True when something changed."""
        from ..packing.jobs import grain_of

        def run():
            parts = self.model_parts()
            groups = [self.groups[u] for u in uids if u in self.groups]
            if not groups:
                return False
            if action == "settings":
                return bool(self.open_part_settings_for(groups))
            library = self.store.library()
            overrides = self.store.overrides(groups)
            changed = {}
            for g in groups:
                part, over = parts.get(g.uid), overrides[g.uid]
                if part is None:
                    continue
                grain = grain_of(part, library)
                if action == "switch_grain":
                    if grain == "none":
                        continue
                    changed[g] = replace(over, grain="width"
                                         if grain == "length" else "length")
                elif action == "toggle_rotation":
                    now = part.can_rotate if part.can_rotate is not None \
                        else grain == "none"
                    changed[g] = replace(over, can_rotate=not now)
            if not changed:
                self._failed(None, tr("Cut List: these parts have no grain "
                                      "to switch."))
                return False
            return self.store.set_overrides(changed)
        done = bool(self._guard(run))
        if done:
            self.refresh()
        return done

    def ask_sheet_sizes(self, names) -> bool:
        """Ask the sheet sizes of these boards once; True when saved."""
        from ..model.materials import MaterialSpec, Role
        from ..ui.dialogs import SheetSizesDialog

        def run():
            dlg = SheetSizesDialog(names, self.store.sheet_templates(),
                                   parent=self.app.window)
            if not dlg.exec() or not dlg.result_sizes():
                return False
            library = self.store.library()
            specs = []
            for name, sizes in dlg.result_sizes().items():
                spec = library.get(name) or MaterialSpec(name, role=Role.BOARD)
                specs.append(replace(spec, stocks=sizes))
            self.store.save_materials(specs,
                                      remember=dlg.remember.isChecked())
            return True
        return bool(self._guard(run))

    # ---- labels (D-018) ------------------------------------------------------
    def make_labels(self, entries) -> list:
        """``entries``: ``(uid, letter, index, count, sheet)`` per piece →
        :class:`Label` objects, read from the model as it is now."""
        from ..export.labels import Label
        from ..packing.jobs import grain_of
        parts = self.model_parts()
        library = self.store.library()
        fields = self.store.fields()
        groups = [self.groups[u] for u, *_ in entries if u in self.groups]
        overrides = self.store.overrides(groups)
        path = self.model_path()
        model = path.stem if path else ""
        out = []
        for uid, letter, index, count, sheet in entries:
            p = parts.get(uid)
            if p is None:
                continue
            over = overrides.get(uid)
            values = fields.values(p.tag, over.field_values if over else None)
            info = " · ".join(v for v in [model, *values.values()] if v)
            cut = None
            if p.extra_length or p.extra_width:
                cut = (p.length + p.extra_length, p.width + p.extra_width)
            out.append(Label(letter, p.name, p.length, p.width,
                             p.core or "", p.thickness,
                             tuple(bool(e) for e in p.edges),
                             grain_of(p, library), cut, info, index, count,
                             sheet))
        return out

    def cut_list_labels(self) -> list:
        """One label per piece, in the cut list's order."""
        from ..packing.jobs import letters
        names = letters(self.cut_list)
        entries = []
        for line in self.cut_list.lines():
            for i, uid in enumerate(line.uids, 1):
                entries.append((uid, names[id(line)], i, len(line.uids),
                                None))
        return self.make_labels(entries)

    def open_labels(self, entries=None, title: str | None = None) -> None:
        """The labels window: from the cut list, or from ``entries`` (the
        diagrams, sorted by sheet)."""
        if entries is None and (self.cut_list is None or self.stale):
            self.refresh(ask=True)
        if entries is None and self.cut_list is None:
            return
        from ..ui.labels_dialog import LabelsDialog

        def run():
            labels = self.make_labels(entries) if entries is not None \
                else self.cut_list_labels()
            path = self.model_path()
            from ..export.rows import safe_stem
            LabelsDialog(labels, title=title or tr("From the cut list"),
                         options=self.store.label_options(),
                         save_options=self.store.save_label_options,
                         folder=self.export_folder(),
                         stem=safe_stem(f"{path.stem if path else 'cut list'}"
                                        f" {tr('labels')}"),
                         folder_used=self.folder_used,
                         parent=self.app.window).exec()
            return True
        self._guard(run)

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

    # ---- failures ----------------------------------------------------------
    def _guard(self, fn):
        try:
            return fn()
        except Exception as exc:                # noqa: BLE001 — UI boundary
            self._failed(exc, tr("Cut List: something went wrong: {error}",
                                 error=f"{type(exc).__name__}: {exc}"))
            return None

    def _failed(self, exc, message: str) -> None:
        if exc is None:
            log.info("%s", message)
        else:
            log.error("%s", message, exc_info=exc)
        flash = getattr(self.app.viewport, "flash_status", None)
        if callable(flash):
            flash(message, 6000)
