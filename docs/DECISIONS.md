# Decisions

Short records of choices that are hard to reverse. Newest last. To change
one, add a new entry that supersedes it; do not edit history.

## D-001 — Build our own; OpenCutList is a benchmark, not a port

*2026-10-06 · accepted*

OpenCutList is ~91k lines of Ruby bound to the SketchUp API (106 files use
`Sketchup::`/`Geom::` types), with a ~21k-line JS/Twig HTML UI that would
need QtWebEngine, which IngeTrazo does not bundle. A port was estimated at
9–12+ person-months with permanent drift on both sides. IngeTrazo already
has part measurement and a basic cut list (`core/parts.py`). We build a
native IngeTrazo extension and use OpenCutList for feature ideas and as a
quality benchmark.

## D-002 — Python + Qt widgets, only IngeTrazo's bundled dependencies

*2026-10-06 · accepted*

Extensions run inside IngeTrazo's bundled Python (Flatpak, AppImage,
installers) and cannot install packages. We use PySide6, NumPy, ezdxf and
the stdlib only. Qt widgets, not HTML.

## D-003 — Own pure-Python guillotine packer first

*2026-10-06 · accepted*

Pure Python/NumPy guillotine packer behind a `Packer` protocol. Easy to
ship (no per-platform native builds), easy to test, matches how panel saws
cut. Quality is measured against OpenCutList on a benchmark set (M2); if it
falls short, OpenCutList's C++ Packy can be added as a second backend via
ctypes without UI changes.

## D-004 — English source with pt-BR and es from day one

*2026-10-06 · accepted*

Code, identifiers and docs in English. UI strings use English as the key
(IngeTrazo's convention) with our own JSON catalogs for pt-BR and es,
following IngeTrazo's current language.

## D-005 — Open source (GPL-3.0-or-later), funded by voluntary donations

*2026-10-06 · accepted*

GPL-3.0-or-later is required in practice (in-process extension importing
GPL modules) and wanted. No paid tier. Donations from v0.2: links opened
on click from a menu entry and the About dialog, optional PIX QR; no
pop-ups, nag screens or telemetry.

## D-006 — Part detection rule

*pending — decided in M0 spike*
