# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Materials and their roles (D-007).

IngeTrazo's materials say how a face looks; a cut list needs to know what
the face *is*: the board that gets cut, a laminate or veneer on it, an edge
band, a texture that only shows something (a plywood edge), or a thing not
cut at all. That is the material's **role**, set once per material name.
A material nobody has set up yet has no role (``None``) and is read as a
board — the common case — while the cut list says it is not set up.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Role(StrEnum):
    BOARD = "board"             # the core that is cut (sheet or solid)
    COVERING = "covering"       # laminate, HPL, veneer on a face
    EDGE_BAND = "edge_band"     # band on an edge
    APPEARANCE = "appearance"   # only shows something; nothing to order
    IGNORE = "ignore"           # glass, hardware, "not cut"


class BoardKind(StrEnum):
    SHEET = "sheet"
    SOLID = "solid"             # its own anatomy, after v0.1 (D-007 §7)


@dataclass(frozen=True)
class MaterialSpec:
    """Everything the cut list knows about one material, by its name.

    Lengths are metres. Fields that do not apply to the role are kept
    anyway (switching a role back and forth must not lose them).
    ``None`` in ``kerf``/``trim`` means "use the model's or the user's
    setting" (the cascade, D-007 §6)."""

    name: str
    role: Role = Role.BOARD
    kind: BoardKind = BoardKind.SHEET
    grain: bool = False
    #: Nominal board thicknesses; a part's thickness is checked against them.
    thicknesses: tuple[float, ...] = ()
    #: Stock sheets (length, width) for boards and coverings.
    stocks: tuple[tuple[float, float], ...] = ()
    kerf: float | None = None
    trim: float | None = None
    #: Coverings and bands: their own thickness.
    thickness: float = 0.0
    #: Coverings: per side; bands: per edge length.
    oversize: float = 0.0
    #: Bands: cut the board shorter by the band thickness.
    deduct: bool = False
    #: Coverings: the board they go on when no face shows one.
    applied_over: str | None = None
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["role"] = str(self.role)
        d["kind"] = str(self.kind)
        d["stocks"] = [list(s) for s in self.stocks]
        d["thicknesses"] = list(self.thicknesses)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> MaterialSpec:
        """Lenient: unknown keys are ignored and bad values fall back, so a
        document written by a newer version still opens."""
        def num(key, default):
            try:
                v = d.get(key, default)
                return default if v is None else float(v)
            except (TypeError, ValueError):
                return default

        def opt(key):
            v = d.get(key)
            try:
                return None if v is None else float(v)
            except (TypeError, ValueError):
                return None

        try:
            role = Role(d.get("role", Role.BOARD))
        except ValueError:
            role = Role.BOARD
        try:
            kind = BoardKind(d.get("kind", BoardKind.SHEET))
        except ValueError:
            kind = BoardKind.SHEET
        stocks = []
        for s in d.get("stocks") or ():
            try:
                stocks.append((float(s[0]), float(s[1])))
            except (TypeError, ValueError, IndexError):
                continue
        thicknesses = []
        for t in d.get("thicknesses") or ():
            try:
                thicknesses.append(float(t))
            except (TypeError, ValueError):
                continue
        return cls(
            name=str(d.get("name", "")), role=role, kind=kind,
            grain=bool(d.get("grain", False)),
            thicknesses=tuple(thicknesses), stocks=tuple(stocks),
            kerf=opt("kerf"), trim=opt("trim"),
            thickness=num("thickness", 0.0), oversize=num("oversize", 0.0),
            deduct=bool(d.get("deduct", False)),
            applied_over=d.get("applied_over") or None,
            note=str(d.get("note", "")))


@dataclass
class Library:
    """Material specs by name. A name missing here is "not set up"."""

    specs: dict[str, MaterialSpec] = field(default_factory=dict)

    def get(self, name: str | None) -> MaterialSpec | None:
        return None if name is None else self.specs.get(name)

    def role(self, name: str | None) -> Role | None:
        spec = self.get(name)
        return None if spec is None else spec.role

    def is_board_like(self, name: str | None) -> bool:
        """Could be the core: a board, or a material not set up yet."""
        return name is not None and self.role(name) in (None, Role.BOARD)

    def to_dict(self) -> dict:
        return {n: s.to_dict() for n, s in sorted(self.specs.items())}

    @classmethod
    def from_dict(cls, d: dict | None) -> Library:
        specs = {}
        for name, raw in (d or {}).items():
            if isinstance(raw, dict):
                spec = MaterialSpec.from_dict({**raw, "name": name})
                specs[spec.name] = spec
        return cls(specs)
