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

*2026-10-07 · proposed (awaiting review) · evidence: `docs/spikes/M0-part-detection.md`*

1. **Scope** — the selection; nothing selected → the whole model. Then a
   **tag filter**: tags to include or exclude, remembered (user default +
   per model). Hidden objects and hidden tags are left out.
2. **A part** is a **leaf container**: a group or component instance with
   faces of its own and no child containers. Containers above it (a
   cabinet group) give it context, not a line.
3. **Groups count.** Plain groups are parts like components. A first-run
   option can restrict to components only; the default includes groups.
4. **Merge by measurement**: parts with the same material, and the same
   L × W × T within the size tolerance (default 1 mm), are one line with a
   quantity — whether they are components, groups or a mix.
5. **Materials decide the type**: *sheet*, *solid*, or *ignore* (hardware,
   glass, "not cut"). A part on an *ignore* material is left out of the
   cut list but listed in an "Excluded" section with the reason.
6. **Never silent.** Things we cannot classify are listed with a flag:
   - a container with faces of its own **and** child containers
     ("loose geometry beside parts");
   - a part thinner than 0.5 mm (a surface — `core.parts.is_surface`);
   - a part with no material;
   - a part that is not a rectangular board (bounding box used).
7. **Names**: the part's name from the model; when it has none, or only
   IngeTrazo's automatic `Group N`, it is shown as **"Group #n"**, where *n*
   is our own number, stored in `group.ext["cutlist"]` and so stable across
   saves, shared by the cut list, the diagrams and the 3D highlight.

Rejected: "a part is a direct child of a selected container" (IngeTrazo's
Parts tray rule) — real models are flat, organised by tags (model C has
391 top-level parts), so there is often no container to select.
