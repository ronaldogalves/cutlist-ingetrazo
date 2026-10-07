# CLAUDE.md

Guidance for Claude Code when working in this repository. Read
`docs/BRIEF.md` for the why, `docs/ROADMAP.md` for what is next, and
`docs/DECISIONS.md` before changing anything those decisions cover.

## What this is

A **cut list generator extension for IngeTrazo** (a free, GPL, Python/Qt
push-pull 3D modeler: https://github.com/ingelibre/ingetrazo). It turns the
parts of a furniture model into a cut list, grouped by material and
thickness, and lays sheet-goods parts out on stock sheets (cutting
diagrams). OpenCutList (the SketchUp extension) is the **benchmark** for
features and output quality — **not** a codebase to port. We build our own
implementation on IngeTrazo's own architecture. We study OpenCutList's
structure and methods freely, but we are not cloning it: where a different
choice serves our users or IngeTrazo better, we take it and record why in
`docs/DECISIONS.md`.

Working name: **CutList** (package `cutlist`). The final name is still
open — see `docs/BRIEF.md` § Open questions.

## Stack and hard constraints

- **Python 3.12+ (IngeTrazo's minimum), PySide6, NumPy, stdlib.** An extension cannot install
  packages into a user's IngeTrazo (Flatpak, AppImage, Windows installer
  all bundle their own Python). We may only import what IngeTrazo itself
  ships: PySide6, numpy, ezdxf, manifold3d, openskp and the stdlib. Any new
  dependency needs a decision in `docs/DECISIONS.md` first.
- **No native code** in the MVP (see D-003).
- **License: GPL-3.0-or-later.** Every source file starts with:
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  # Copyright (C) 2026 <author> and CutList contributors.
  ```
- **IngeTrazo's plugin API is 0.x and changes between minor versions.**
  Pin the IngeTrazo version we test against in `README.md` and keep all
  IngeTrazo imports inside the adapter layer (below).

## Architecture rule: three layers

```
cutlist/
  __init__.py      setup(app) — entry point; wires UI to the host
  host/            ADAPTER: the ONLY place that imports IngeTrazo
                   (core.*, views.*, tools.*). Turns the scene into our
                   plain data classes and applies our changes as commands.
  model/           PURE: parts, materials, grouping, settings. No Qt, no
                   IngeTrazo imports. Dataclasses in, dataclasses out.
  packing/         PURE: Packer protocol + guillotine packer. No Qt.
  export/          CSV and SVG with the stdlib (no QtSvg: IngeTrazo does
                   not use it, so its builds may not ship it); PDF via
                   Qt's QPdfWriter in ui/.
  ui/              Qt widgets: tray panel, diagram window, dialogs.
  i18n/            en.json (empty identity), pt-BR.json, es.json
```

`model/` and `packing/` must stay importable and testable **without Qt and
without IngeTrazo**. That keeps tests fast and limits the blast radius when
IngeTrazo's API changes to `host/`.

## IngeTrazo facts we rely on (verified at IngeTrazo 0.5.7, commit 6be29fe)

- Plugin entry: a package in the user plugins folder
  (`~/.local/share/ingetrazo/plugins/` on Linux) with a module-level
  `setup(app)`; `app` is an `ExtensionApp`, API_VERSION 2
  (`views/extension_api.py`, documented in `docs/plugins.md`).
- `app.key` is our plugin name (the package directory name).
- Per-document data: `app.document_data(default=...)` /
  `app.set_document_data(value)` — ONE JSON-safe value per plugin, saved in
  the `.igz`, each set is one undo step. `app.on_document_changed(fn)`.
- Per-part data: `group.ext[app.key]` — survives copies, saved in `.igz`.
- UI: `app.add_panel`, `app.show_panel`, `app.add_menu`,
  `app.add_menu_action`, `app.add_context_menu`, `app.add_overlay`,
  `app.world_to_pixels`.
- Geometry: read `scene.loose_mesh` and `scene.groups` (NOT `scene.mesh`).
  Lengths are **metres** internally.
- Existing cut-list code to build on: `core/parts.py` — `part_points`,
  `part_size` (L × W × T along the part's own axes when tighter),
  `part_material`, `part_rows`, `is_surface`, `cut_list`, `cut_list_text`.
  The Parts tray (`views/tray.py`) already has "Copy cut list".
- Iterating instances: `core.group.iter_placements(group)`; component
  instances share a prototype mesh (`group.xform` is set on instances).
- Materials registry: `scene.materials`, faces carry `attrs["mat"]`;
  `core.materials.Material` has `name, color, texture, opacity, finish` —
  nothing woodworking-specific, so our material data lives in our
  document data, keyed by material name.
- Display lengths: `core.units.fmt_len_fine(metres)` (model units, mm
  precision).
- Mutations go through the command layer:
  `viewport.history.execute(SnapshotImport(mutate))` then
  `viewport.notify_scene_changed()`.
- i18n: `core.i18n.tr("English source", **kw)`; English is the key. Its
  catalog is IngeTrazo's own, so we keep **our own** catalogs in
  `cutlist/i18n/` and follow `core.i18n.current_language()`.
- Threading: never touch the document off the main thread; relay worker
  results with `Signal(object)` on a queued connection to a bound method.

When any of these turns out wrong, fix this section in the same change.

## Development setup

```bash
# Side by side:
git clone https://github.com/ingelibre/ingetrazo ../ingetrazo
python -m venv .venv && . .venv/bin/activate
pip install -r ../ingetrazo/requirements.txt
# Load the plugin from this checkout (re-run after moving folders):
ln -sfn "$PWD/cutlist" ~/.local/share/ingetrazo/plugins/cutlist
python ../ingetrazo/main.py
```

Tests: `pytest` (fast, pure layers) and `pytest -m host` (needs
`INGETRAZO_SRC=../ingetrazo` on the path; `tests/conftest.py` adds it).
Fixtures: `.igz` models in `tests/fixtures/`; IngeTrazo's `examples/*.igz`
are useful real-world inputs.

## Conventions

- Follow IngeTrazo's code style: `from __future__ import annotations`,
  docstrings that explain *why* in plain words, small modules.
- All user-facing strings go through our `tr()`; English is the source.
  Add pt-BR and es entries in the same change.
- Every model change the user makes is **one undo step**.
- A failure in our extension must never break IngeTrazo: catch at UI
  boundaries, log to the `cutlist` logger, show a status message.
- Unit tests for every pure function; a regression fixture for every bug.
- No network access, telemetry or nag screens. Donation links open the
  browser only when the user clicks them (D-005).

## Working agreements

- Before a milestone starts, re-read its acceptance criteria in
  `docs/ROADMAP.md`; tick them off in the same PR that meets them.
- Record any decision that is hard to reverse in `docs/DECISIONS.md`.
- When OpenCutList behaviour is the reference, cite the feature, not its
  code. Copying OpenCutList code is allowed by license (both GPL-3) but
  needs attribution in the file header and a note in DECISIONS.
