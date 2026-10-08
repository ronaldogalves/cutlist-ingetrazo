# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Settings and the cascade (D-007 §6): user defaults → model → part.

A setting is looked up from the most specific place that has it: what the
user set on this model wins over their defaults, which win over ours.
Settings are stored as plain dicts holding only what was set, so a
default changed later still reaches every model that never overrode it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace

#: Units the cut list may use instead of the model's (IngeTrazo's codes).
UNITS = ("mm", "cm", "m", "in", "in-frac", "ft-in", "ft-in-frac")


@dataclass(frozen=True)
class Settings:
    #: ``None``: the model's units; else one of :data:`UNITS`.
    unit: str | None = None
    #: Decimals (fractional units: the denominator code); ``None``: default.
    precision: int | None = None
    #: Sizes are rounded to this step before merging and display
    #: (metres) — see ``grouping.quantize``.
    tolerance: float = 0.001
    #: Repeat the unit after every size (False: once, in the column title).
    units_in_cells: bool = False
    #: One line per size, whatever the names (False: names kept apart).
    merge_by_size: bool = True
    #: Read the selection when there is one (else always the whole model).
    use_selection: bool = True
    #: Plain groups are parts too (False: components only).
    include_groups: bool = True
    #: Tags whose parts stay out of the cut list.
    excluded_tags: tuple[str, ...] = ()
    #: The scope window was answered with "don't show again".
    scope_asked: bool = False
    #: Defaults for boards that do not set their own (metres) — for M2.
    kerf: float = 0.004
    trim: float = 0.010

    def to_dict(self) -> dict:
        d = asdict(self)
        d["excluded_tags"] = list(self.excluded_tags)
        return d


_TYPES = {f.name: f.type for f in fields(Settings)}


def _clean(raw: dict | None) -> dict:
    """Only known fields with usable values: a document from a newer (or
    broken) version must not break the cut list."""
    out: dict = {}
    for key, value in (raw or {}).items():
        if key not in _TYPES:
            continue
        default = getattr(Settings(), key)
        try:
            if key == "unit":
                if value is None or value in UNITS:
                    out[key] = value
            elif key == "precision":
                out[key] = None if value is None else int(value)
            elif key == "excluded_tags":
                out[key] = tuple(str(t) for t in value)
            elif isinstance(default, bool):
                out[key] = bool(value)
            elif isinstance(default, float):
                v = float(value)
                if v >= 0:
                    out[key] = v
        except (TypeError, ValueError):
            continue
    return out


def resolve(*layers: dict | None) -> Settings:
    """Settings from layers, broadest first (user defaults, then model)."""
    merged: dict = {}
    for layer in layers:
        merged.update(_clean(layer))
    return replace(Settings(), **merged)


def diff(settings: Settings, base: Settings) -> dict:
    """The fields of ``settings`` that differ from ``base`` — what a layer
    stores so it does not freeze the defaults below it."""
    a, b = settings.to_dict(), base.to_dict()
    return {k: v for k, v in a.items() if v != b[k]}
