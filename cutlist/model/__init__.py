# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cut list itself, in plain Python: parts, materials, grouping.

No Qt and no IngeTrazo here (NumPy is fine): the host hands in plain
records (:class:`.parts.RawPart`), this package turns them into cut-list
lines, and everything can be tested in milliseconds. Lengths are metres.
"""
