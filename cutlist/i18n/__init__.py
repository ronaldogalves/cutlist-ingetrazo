# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Our own UI translations, the IngeTrazo way.

English is the source: ``tr("Cut List")`` looks the English text up in
``<lang>.json`` next to this file and falls back to the English itself.
IngeTrazo's catalog is IngeTrazo's, so we keep ours here and only follow
its *current language*, which the host hands in with
:func:`set_language_source`. Pure Python: no Qt, no IngeTrazo, so the
model and the tests can use it too.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger("cutlist")

_DIR = Path(__file__).parent

#: Languages we ship a catalog for (English needs none).
LANGUAGES = ("pt-BR", "es")

_language_source: Callable[[], str] = lambda: "en"  # noqa: E731
_catalogs: dict[str, dict[str, str]] = {}


def set_language_source(fn: Callable[[], str]) -> None:
    """Follow ``fn()`` — IngeTrazo's current language code — from now on."""
    global _language_source
    _language_source = fn


def current_language() -> str:
    try:
        return _language_source() or "en"
    except Exception:                           # noqa: BLE001 — never fail a label
        log.exception("could not read the current language")
        return "en"


def catalog(lang: str) -> dict[str, str]:
    """The ``{english: translation}`` map for ``lang`` (empty for English or
    a missing/broken file — a broken catalog must not break the UI)."""
    if lang in _catalogs:
        return _catalogs[lang]
    data: dict[str, str] = {}
    path = _DIR / f"{lang}.json"
    if lang != "en" and path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            data = {str(k): str(v) for k, v in raw.items()}
        except (OSError, ValueError):
            log.exception("could not read the %s catalog", lang)
    _catalogs[lang] = data
    return data


def tr(text: str, /, **kwargs) -> str:
    """``text`` in the current language; ``kwargs`` are interpolated after
    the lookup, so a translation may reorder them."""
    out = catalog(current_language()).get(text, text)
    if kwargs:
        try:
            out = out.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            out = text.format(**kwargs)
    return out
