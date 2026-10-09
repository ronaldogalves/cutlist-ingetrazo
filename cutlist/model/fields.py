# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Custom fields: client, room ("Ambiente")… defined by the user (D-009 §10).

IngeTrazo has no "project → room → part" hierarchy, and suppliers ask for
exactly that (a client name to sort deliveries, a room to sort the pieces).
A custom field gives every part a value without one:

1. the part's own value (Part settings, set on many parts at once);
2. else the value of the first **tag rule** that matches the part's tag
   (every part tagged "QTO…" is in the bedroom);
3. else the **model's** value for the field.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TagRule:
    """Parts whose tag starts with ``prefix`` get ``value``."""

    prefix: str
    value: str

    def matches(self, tag: str | None) -> bool:
        return bool(tag) and tag.lower().startswith(self.prefix.lower())


@dataclass(frozen=True)
class FieldDef:
    name: str
    #: The value for every part of this model (unless a rule or the part
    #: says otherwise).
    model_value: str = ""
    rules: tuple[TagRule, ...] = ()

    def to_dict(self) -> dict:
        return {"name": self.name, "model_value": self.model_value,
                "rules": [[r.prefix, r.value] for r in self.rules]}

    @classmethod
    def from_dict(cls, d) -> FieldDef | None:
        if not isinstance(d, dict) or not str(d.get("name", "")).strip():
            return None
        rules = []
        for r in d.get("rules") or ():
            try:
                rules.append(TagRule(str(r[0]), str(r[1])))
            except (TypeError, IndexError):
                continue
        return cls(str(d["name"]).strip(), str(d.get("model_value") or ""),
                   tuple(rules))


@dataclass(frozen=True)
class Fields:
    """The custom fields of a model."""

    defs: tuple[FieldDef, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.defs)

    def values(self, tag: str | None, own: dict | None = None) -> dict:
        """Every field's value for a part with ``tag`` and its own values."""
        own = own or {}
        out = {}
        for f in self.defs:
            if own.get(f.name):
                out[f.name] = str(own[f.name])
                continue
            rule = next((r for r in f.rules if r.matches(tag)), None)
            out[f.name] = rule.value if rule else f.model_value
        return out

    def to_list(self) -> list:
        return [f.to_dict() for f in self.defs]

    @classmethod
    def from_list(cls, raw) -> Fields:
        defs = [FieldDef.from_dict(d) for d in (raw or ())]
        seen, unique = set(), []
        for d in defs:
            if d is not None and d.name not in seen:
                seen.add(d.name)
                unique.append(d)
        return cls(tuple(unique))



def parse_rules(text: str) -> tuple[TagRule, ...]:
    """``"QTO = Quarto; BNH = Banheiro"`` → two rules (bad items skipped)."""
    rules = []
    for item in (text or "").replace("\n", ";").split(";"):
        if "=" not in item:
            continue
        prefix, value = (s.strip() for s in item.split("=", 1))
        if prefix and value:
            rules.append(TagRule(prefix, value))
    return tuple(rules)


def format_rules(rules) -> str:
    return "; ".join(f"{r.prefix} = {r.value}" for r in rules)
