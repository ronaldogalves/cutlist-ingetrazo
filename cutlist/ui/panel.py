# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The Cut List tab in IngeTrazo's side tray.

Shows a :class:`~..model.grouping.CutList`: one branch per board and
thickness, its lines below, then what needs a look and what was left out.
The panel holds no document state and knows nothing of IngeTrazo: the host
calls :meth:`CutListPanel.show_cut_list` and listens to its signals.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..model.grouping import CutList, CutListLine
from ..model.parts import EDGES, Excluded, Flag, Part

UIDS = Qt.ItemDataRole.UserRole
#: On rows that stand for a material (sections, "no role yet").
MATERIAL = Qt.ItemDataRole.UserRole + 1
#: On rows of real parts (lines, flagged and excluded parts).
PARTS = Qt.ItemDataRole.UserRole + 2


def flag_text(flag: Flag) -> str:
    return {
        Flag.NOT_RECTANGULAR: tr("Not a rectangular board (angled cut, "
                                 "notch or hole): its bounding box is used."),
        Flag.SEVERAL_SOLIDS: tr("Several separate solids in one group: "
                                "boards merged into one part?"),
        Flag.NO_MATERIAL: tr("No material: paint it so the cut list knows "
                             "which board it is."),
        Flag.UNASSIGNED: tr("Has a finish whose material is not set up "
                            "yet."),
    }[flag]


def flag_label(flag: Flag) -> str:
    """A few words for the Notes column (the tooltip has the long text)."""
    return {
        Flag.NOT_RECTANGULAR: tr("not rectangular"),
        Flag.SEVERAL_SOLIDS: tr("several solids"),
        Flag.NO_MATERIAL: tr("no material"),
        Flag.UNASSIGNED: tr("finish not set up"),
    }[flag]


#: Flags that deserve a ⚠ and a row under "Needs a look". A finish that is
#: not set up is reported once per material instead (and marked "?").
_LOUD = frozenset(Flag) - {Flag.UNASSIGNED}


def excluded_text(reason: Excluded) -> str:
    return {
        Excluded.BY_USER: tr("Excluded by you"),
        Excluded.IGNORED_MATERIAL: tr("Material set to ignore"),
        Excluded.SURFACE: tr("No thickness (a surface)"),
    }[reason]


def edge_label(edge: str) -> str:
    return {"length1": tr("L1"), "length2": tr("L2"),
            "width1": tr("W1"), "width2": tr("W2")}[edge]


class CutListPanel(QWidget):
    """The tray tab. Signals carry what the user asked for; the host does
    the work and calls back with the result."""

    refresh_requested = Signal()
    #: Part uids to highlight in the viewport (empty: none).
    highlight_requested = Signal(object)
    #: The set of tags to leave out changed.
    tags_changed = Signal(object)
    #: True: one line per size (cutting); False: names kept apart.
    merge_changed = Signal(bool)
    #: Open the material library, on this material name (or None).
    materials_requested = Signal(object)
    settings_requested = Signal()
    #: Open the part settings for these part uids.
    part_settings_requested = Signal(object)

    #: Where the column widths are remembered (a per-user convenience).
    HEADER_KEY = "cutlist/panel_header"

    COLUMNS = ("name", "qty", "length", "width", "thickness", "edges",
               "faces", "notes")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_panel")
        self._fmt_len: Callable[[float], str] = lambda m: f"{m * 1000:.0f}"
        self._fmt_full: Callable[[float], str] = \
            lambda m: f"{m * 1000:.0f} mm"
        self._fmt_area: Callable[[float], str] = lambda a: f"{a:.2f} m²"
        self._tags: list[str] = []
        self._excluded_tags: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        bar = QHBoxLayout()
        self.refresh_button = QPushButton(tr("Refresh"))
        self.refresh_button.setObjectName("cutlist_refresh")
        self.refresh_button.setToolTip(tr("Read the model again."))
        self.refresh_button.clicked.connect(self.refresh_requested)
        bar.addWidget(self.refresh_button)
        self.tags_button = QToolButton()
        self.tags_button.setObjectName("cutlist_tags")
        self.tags_button.setText(tr("Tags"))
        self.tags_button.setToolTip(tr("Choose which tags go in the cut "
                                       "list."))
        self.tags_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self.tags_button.setMenu(QMenu(self.tags_button))
        bar.addWidget(self.tags_button)
        self.merge_button = QToolButton()
        self.merge_button.setObjectName("cutlist_merge")
        self.merge_button.setText(tr("Merge same size"))
        self.merge_button.setCheckable(True)
        self.merge_button.setChecked(True)
        self.merge_button.setToolTip(tr(
            "On: parts of the same board and size are one line whatever "
            "their names (how they are cut). Off: different names stay on "
            "different lines."))
        self.merge_button.toggled.connect(self.merge_changed)
        bar.addWidget(self.merge_button)
        bar.addStretch(1)
        self.materials_button = QPushButton(tr("Materials…"))
        self.materials_button.setObjectName("cutlist_materials")
        self.materials_button.setToolTip(tr("Say what each material is: "
                                            "board, covering, edge band…"))
        self.materials_button.clicked.connect(
            lambda: self.materials_requested.emit(None))
        bar.addWidget(self.materials_button)
        self.settings_button = QPushButton(tr("Settings…"))
        self.settings_button.setObjectName("cutlist_settings")
        self.settings_button.clicked.connect(self.settings_requested)
        bar.addWidget(self.settings_button)
        layout.addLayout(bar)

        self.scope_label = QLabel()
        self.scope_label.setObjectName("cutlist_scope")
        self.scope_label.setWordWrap(True)
        layout.addWidget(self.scope_label)

        self.stale_label = QLabel(tr("The model changed — press Refresh."))
        self.stale_label.setObjectName("cutlist_stale")
        self.stale_label.setStyleSheet("color: #b35c00;")
        self.stale_label.setWordWrap(True)
        self.stale_label.hide()
        layout.addWidget(self.stale_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName("cutlist_tree")
        self._set_headers("mm")
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(
            QTreeWidget.SelectionMode.ExtendedSelection)
        header = self.tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(28)
        self._widths_restored = self._restore_header()
        header.sectionResized.connect(self._save_header)
        self.tree.itemSelectionChanged.connect(self._on_selection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        layout.addWidget(self.tree, 1)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("cutlist_summary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.placeholder = QLabel(tr("Press Refresh to read the model."))
        self.placeholder.setObjectName("cutlist_placeholder")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)

    # ---- column widths: the user's, remembered ---------------------------
    def _settings(self):
        from PySide6.QtCore import QSettings
        return QSettings()

    def _restore_header(self) -> bool:
        try:
            state = self._settings().value(self.HEADER_KEY)
            return bool(state) and self.tree.header().restoreState(state)
        except Exception:                           # noqa: BLE001 — cosmetic
            return False

    def _save_header(self, *_args) -> None:
        if getattr(self, "_filling", False):
            return
        try:
            self._settings().setValue(self.HEADER_KEY,
                                      self.tree.header().saveState())
        except Exception:                           # noqa: BLE001 — cosmetic
            pass

    def _fit_columns_once(self) -> None:
        """First fill ever: size columns to their content, the name a
        sensible width. After that the widths are the user's."""
        if self._widths_restored:
            return
        self._filling = True
        try:
            for c in range(1, len(self.COLUMNS)):
                self.tree.resizeColumnToContents(c)
            self.tree.setColumnWidth(0, max(160, min(
                self.tree.sizeHintForColumn(0), 280)))
        finally:
            self._filling = False
        self._widths_restored = True
        self._save_header()

    # ---- set up by the host --------------------------------------------
    def set_formatters(self, fmt_cell, fmt_full, unit, fmt_area) -> None:
        """``fmt_cell`` writes sizes in the table, ``fmt_full`` in titles
        and text; ``unit`` goes in the column titles (``None``: the cells
        carry their own)."""
        self._fmt_len, self._fmt_full, self._fmt_area = \
            fmt_cell, fmt_full, fmt_area
        self._set_headers(unit)

    def _set_headers(self, unit: str | None) -> None:
        def sized(title):
            return tr("{title} ({unit})", title=title, unit=unit) \
                if unit else title
        self.tree.setHeaderLabels([
            tr("Name"), tr("Qty"), sized(tr("Length")), sized(tr("Width")),
            sized(tr("Thickness")), tr("Edges"), tr("Faces"), tr("Notes")])

    def set_merge(self, on: bool) -> None:
        """Show the setting without emitting ``merge_changed``."""
        self.merge_button.blockSignals(True)
        self.merge_button.setChecked(on)
        self.merge_button.blockSignals(False)

    def set_stale(self, stale: bool) -> None:
        self.stale_label.setVisible(stale)

    def set_tags(self, tags, excluded) -> None:
        """Offer ``tags`` in the filter menu; ``excluded`` are unchecked."""
        self._tags = sorted(set(tags) | set(excluded), key=str.lower)
        self._excluded_tags = set(excluded)
        menu = self.tags_button.menu()
        menu.clear()
        if not self._tags:
            menu.addAction(tr("(no tags on parts)")).setEnabled(False)
        for tag in self._tags:
            act = menu.addAction(tag)
            act.setCheckable(True)
            act.setChecked(tag not in self._excluded_tags)
            act.toggled.connect(
                lambda on, t=tag: self._toggle_tag(t, on))
        n = len(self._excluded_tags)
        self.tags_button.setText(
            tr("Tags") if not n else tr("Tags ({n} hidden)", n=n))

    def _toggle_tag(self, tag: str, on: bool) -> None:
        if on:
            self._excluded_tags.discard(tag)
        else:
            self._excluded_tags.add(tag)
        self.tags_changed.emit(frozenset(self._excluded_tags))

    # ---- the list ------------------------------------------------------
    def show_cut_list(self, cl: CutList, *, scope: str, filtered_out: int = 0,
                      not_components: int = 0, notices=()) -> None:
        self.placeholder.hide()
        self.set_stale(False)
        fa = self._fmt_area
        if scope == "selection":
            text = tr("Selection: {n} parts", n=cl.qty)
        else:
            text = tr("Whole model: {n} parts", n=cl.qty)
        if filtered_out:
            text += " · " + tr("{n} left out by tag", n=filtered_out)
        if not_components:
            text += " · " + tr("{n} groups left out (components only)",
                               n=not_components)
        self.scope_label.setText(text)

        self.tree.clear()
        for section in cl.sections:
            title = tr("{material} · {thickness} — {n} parts · {area}",
                       material=section.material or tr("(no material)"),
                       thickness=self._fmt_full(section.thickness),
                       n=section.qty,
                       area=fa(section.area))
            top = self._header(title)
            top.setData(0, UIDS, [u for ln in section.lines for u in ln.uids])
            top.setData(0, MATERIAL, section.material)
            for line in section.lines:
                top.addChild(self._line_item(line))
            top.setExpanded(True)

        loud = [p for p in cl.flagged if p.flags & _LOUD]
        if notices or loud or cl.unassigned:
            top = self._header(tr("Needs a look"))
            top.setForeground(0, Qt.GlobalColor.darkYellow)
            for name, count in sorted(cl.unassigned.items()):
                item = QTreeWidgetItem([
                    tr("Material “{name}” has no role yet", name=name),
                    str(count), "", "", "", "", "", "?"])
                item.setToolTip(0, tr("Set it up: board, covering, edge "
                                      "band, appearance only or ignore."))
                item.setData(0, MATERIAL, name)
                top.addChild(item)
            for n in notices:
                item = QTreeWidgetItem([n.name, "", "", "", "", "", "",
                                        tr("loose faces")])
                item.setToolTip(7, tr("Loose faces beside parts in this "
                                      "group."))
                item.setData(0, UIDS, [n.uid])
                top.addChild(item)
            for p in loud:
                flags = sorted(p.flags & _LOUD)
                top.addChild(self._part_item(
                    p, ", ".join(flag_label(f) for f in flags),
                    "\n".join(flag_text(f) for f in flags)))
            top.setExpanded(True)

        if cl.excluded:
            top = self._header(tr("Excluded — {n} parts", n=len(cl.excluded)))
            for p in cl.excluded:
                why = excluded_text(p.excluded)
                top.addChild(self._part_item(p, why, why))

        self._fit_columns_once()
        total = sum(s.area for s in cl.sections)
        self.summary_label.setText(tr(
            "{n} parts in {lines} lines · {area}", n=cl.qty,
            lines=sum(len(s.lines) for s in cl.sections), area=fa(total)))

    def _header(self, title: str) -> QTreeWidgetItem:
        """A bold row spanning the whole width (a section)."""
        item = QTreeWidgetItem([title])
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        self.tree.addTopLevelItem(item)
        item.setFirstColumnSpanned(True)
        return item

    def _line_item(self, line: CutListLine) -> QTreeWidgetItem:
        fl = self._fmt_len
        names = line.display_names()
        shown = ", ".join(names[:3]) + (" …" if len(names) > 3 else "")
        banded = [edge_label(e) for e, b in zip(EDGES, line.edges, strict=True)
                  if b]
        faces = [f"F{i}: {m}" for i, m in ((1, line.face1), (2, line.face2))
                 if m]
        loud = sorted(line.flags & _LOUD)
        marks = ["⚠ " + ", ".join(flag_label(f) for f in loud)] if loud else []
        if Flag.UNASSIGNED in line.flags:
            marks.append("?")
        item = QTreeWidgetItem([
            shown, str(line.qty), fl(line.length), fl(line.width),
            fl(line.thickness), " ".join(banded), " · ".join(faces),
            " ".join(marks)])
        item.setToolTip(0, "\n".join(names))
        if banded:
            item.setToolTip(5, "\n".join(
                f"{edge_label(e)}: {b}"
                for e, b in zip(EDGES, line.edges, strict=True) if b))
        if line.flags:
            item.setToolTip(7, "\n".join(flag_text(f)
                                          for f in sorted(line.flags)))
        for c in (1, 2, 3, 4):
            item.setTextAlignment(c, Qt.AlignmentFlag.AlignRight
                                  | Qt.AlignmentFlag.AlignVCenter)
        item.setData(0, UIDS, list(line.uids))
        item.setData(0, PARTS, True)
        if len(names) > 1:
            by_name: dict[str, list[str]] = {}
            for name, uid in zip(line.names, line.uids, strict=True):
                by_name.setdefault(name, []).append(uid)
            for name in names:
                child = QTreeWidgetItem([name, str(len(by_name[name]))])
                child.setTextAlignment(1, Qt.AlignmentFlag.AlignRight
                                       | Qt.AlignmentFlag.AlignVCenter)
                child.setForeground(0, Qt.GlobalColor.darkGray)
                child.setData(0, UIDS, by_name[name])
                child.setData(0, PARTS, True)
                item.addChild(child)
            item.setText(0, tr("{first} + {n} more names", first=names[0],
                               n=len(names) - 1))
        return item

    def _part_item(self, p: Part, label: str, why: str) -> QTreeWidgetItem:
        fl = self._fmt_len
        item = QTreeWidgetItem([p.name, "1", fl(p.length), fl(p.width),
                                fl(p.thickness), "", "", label])
        item.setToolTip(7, why)
        item.setData(0, UIDS, [p.uid])
        item.setData(0, PARTS, True)
        if p.core:
            item.setData(0, MATERIAL, p.core)
        return item

    def _selected_part_uids(self) -> list[str]:
        uids: list[str] = []
        for item in self.tree.selectedItems():
            if item.data(0, PARTS):
                uids.extend(item.data(0, UIDS) or [])
        return list(dict.fromkeys(uids))

    def _context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        if not item.isSelected():
            self.tree.setCurrentItem(item)
        menu = QMenu(self.tree)
        uids = self._selected_part_uids()
        if uids:
            act = menu.addAction(tr("Part settings…"))
            act.triggered.connect(
                lambda: self.part_settings_requested.emit(uids))
        material = item.data(0, MATERIAL)
        if material:
            act = menu.addAction(tr("Set up material “{name}”…",
                                    name=material))
            act.triggered.connect(
                lambda: self.materials_requested.emit(material))
        if not menu.isEmpty():
            menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _double_clicked(self, item, _column) -> None:
        """A line opens its part settings; a material row its material."""
        if item.data(0, PARTS):
            self.part_settings_requested.emit(item.data(0, UIDS) or [])
        elif item.data(0, MATERIAL) and item.parent() is not None:
            self.materials_requested.emit(item.data(0, MATERIAL))

    def _on_selection(self) -> None:
        uids: list[str] = []
        for item in self.tree.selectedItems():
            uids.extend(item.data(0, UIDS) or [])
        self.highlight_requested.emit(list(dict.fromkeys(uids)))
