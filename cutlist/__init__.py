# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Cut List for IngeTrazo — the extension's entry point.

IngeTrazo finds this package in its plugins folder and calls
:func:`setup` once, when the main window is built. Everything that touches
IngeTrazo lives in :mod:`.host`; this file only hands over to it, so the
entry point stays the same however the host API changes.

IngeTrazo imports the package by file path under a private name
(``ingetrazo_plugin_cutlist``), never as ``cutlist`` — so every import
inside the package is relative.
"""
from __future__ import annotations

__version__ = "0.0.1"


def setup(app) -> None:
    """Wire the extension into IngeTrazo. An exception here does not stop
    IngeTrazo: it shows us as «cutlist (load error)» in Extensions."""
    from .host.app import install
    install(app)
