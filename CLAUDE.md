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
                   not use it, so not every build is sure to ship it —
                   the Windows 0.5.7 installer does); PDF via Qt's
                   QPdfWriter in ui/.
  ui/              Qt widgets: tray panel, diagram window, dialogs.
  i18n/            en.json (empty identity), pt-BR.json, es.json
```

`model/` and `packing/` must stay importable and testable **without Qt and
without IngeTrazo**. That keeps tests fast and limits the blast radius when
IngeTrazo's API changes to `host/`.

## IngeTrazo facts we rely on (verified at IngeTrazo 0.5.7, tag v0.5.7, commit 4ad32ed — 2026-10-07)

- Plugin entry: a package (`cutlist/__init__.py`) in the user plugins
  folder — `%APPDATA%\ingetrazo\plugins\` on Windows,
  `~/.local/share/ingetrazo/plugins/` on Linux (`$XDG_DATA_HOME`
  honoured) — with a module-level `setup(app)`; `app` is an
  `ExtensionApp`, API_VERSION 2 (`views/extension_api.py`, documented in
  `docs/plugins.md`). Discovery is `core/extensions.py`; app-bundled
  plugins win a name clash, and names starting with `_` or `.` are skipped.
- The package is imported by file path as `ingetrazo_plugin_cutlist`, not
  as `cutlist`: inside the package use **relative imports only**
  (`from .model import parts`). A load error is caught by IngeTrazo and
  shown as a load-error entry; it never stops the app.
- `app.key` is our plugin name (the package directory name).
- Per-document data: `app.document_data(default=...)` returns a copy;
  `app.set_document_data(value)` is ONE JSON-safe value per plugin, saved
  in the `.igz`, each set one undo step (`SetPluginDataCommand`), and it
  already calls `notify_scene_changed`. `app.on_document_changed(fn)`
  fires on every edit, undo, New and Open (`sceneVersionChanged`).
- Per-part data: `group.ext[app.key]` — survives copies, saved in `.igz`.
  Replace the whole dict (`ext = dict(group.ext or {}); ext[key] = …;
  group.ext = ext`). There is **no core command** for it: to make it one
  undo step we need our own `core.history.Command` subclass that captures
  and restores the touched groups' `ext` and bumps `scene.version` — the
  pattern of `WindowizerCommand` in `examples/extensions/windowizer.py`.
  After `history.execute(cmd)`, check `history.last_error`.
- Every group has a stable `group.uid` (16 hex chars), saved in the file —
  use it for part identity and highlighting.
- UI: `app.add_panel`, `app.show_panel`, `app.add_menu`,
  `app.add_menu_action`, `app.add_context_menu` (open dialogs with
  `QTimer.singleShot(0, …)`), `app.add_overlay`, `app.world_to_pixels`.
  Also available, not yet planned: `add_pickable`, `add_file_opener`,
  `enter_workspace` (shows our own document in the viewport instead of
  the model — a possible home for cutting diagrams).
- Geometry: `scene.groups` (top level), `scene.loose_mesh` (a property: the
  real loose mesh whatever the edit context), `scene.placements()` (every
  visible group and nested placement with its world matrix). Lengths are
  **metres** internally.
- Existing cut-list code to build on: `core/parts.py` — `part_points`,
  `part_size` (L × W × T along the part's own axes when tighter),
  `part_material` (dominant material by face area), `part_rows(container)`
  (one row per DIRECT child of one container), `is_surface` (thinner than
  0.5 mm), `cut_list` (merge by size to 1 mm and material),
  `cut_list_text`. The Parts tray (`views/tray.py`) has "Copy cut list".
  Deciding what counts as a part across a whole model is ours (D-006).
- Iterating instances: `core.group.iter_placements(group)` yields
  `(group, world_matrix_or_None)` depth first; component instances share a
  prototype mesh (`group.xform` is set on instances).
- Materials registry: `scene.materials`, faces carry `attrs["mat"]`;
  `core.materials.Material` has `name, color, texture, opacity, finish` —
  nothing woodworking-specific, so our material data lives in our
  document data, keyed by material name.
- Display lengths: `core.units.fmt_len_fine(metres)` (model units, mm
  precision).
- Geometry mutations go through `viewport.history.execute(command)` then
  `viewport.notify_scene_changed()`. (`SnapshotImport` is for file imports
  that add groups — not a general-purpose wrapper.)
- i18n: `core.i18n.tr("English source", **kw)`; English is the key. Its
  catalog is IngeTrazo's own, so we keep **our own** catalogs in
  `cutlist/i18n/` and follow `core.i18n.current_language()`.
- Threading: never touch the document off the main thread; relay worker
  results with `Signal(object)` on a queued connection to a bound method.
- Runtime: the Windows installer bundles **Python 3.12**, PySide6, NumPy
  2.5, ezdxf, manifold3d, openskp; its Qt includes QtSvg and
  QtPrintSupport. IngeTrazo's own README says 3.11+ should work and it is
  developed on 3.14 — so 3.12 is our floor and we avoid 3.13+ features.

When any of these turns out wrong, fix this section in the same change.

## Development setup

The IngeTrazo source lives **inside** this folder as `ingetrazo/`
(git-ignored, a shallow clone of the tested tag) — read it for the real
API; `host` tests import it. Virtual environments live **outside**
OneDrive.

### Windows (main dev machine)

```powershell
# IngeTrazo source at the tested tag (update: delete the folder, re-clone)
git clone --depth 1 --branch v0.5.7 https://github.com/ingelibre/ingetrazo.git ingetrazo
# Environment outside OneDrive (3.12 is what IngeTrazo bundles; 3.13 is fine for tests)
py -m venv $HOME\.venvs\cutlist
& $HOME\.venvs\cutlist\Scripts\python.exe -m pip install -r ingetrazo\requirements.txt ruff
# Load the plugin from this checkout: a junction (no admin rights needed)
New-Item -ItemType Junction -Path "$env:APPDATA\ingetrazo\plugins\cutlist" -Target "$PWD\cutlist"
# Run IngeTrazo from source (daily work)…
& $HOME\.venvs\cutlist\Scripts\python.exe ingetrazo\main.py
# …or the installed app (release check): it reads the same plugins folder
& "$env:LOCALAPPDATA\Programs\IngeTrazo\ingetrazo.exe"
```

Note: Claude Code's desktop app runs sandboxed, and new folders it creates
under `%LOCALAPPDATA%` are redirected to its private storage — that is why
the venv is in `%USERPROFILE%\.venvs`. `%APPDATA%\ingetrazo` is not
redirected (verified).

### Linux

```bash
git clone --depth 1 --branch v0.5.7 https://github.com/ingelibre/ingetrazo.git ingetrazo
python3 -m venv ~/.venvs/cutlist && . ~/.venvs/cutlist/bin/activate
pip install -r ingetrazo/requirements.txt ruff
ln -sfn "$PWD/cutlist" ~/.local/share/ingetrazo/plugins/cutlist
python ingetrazo/main.py
```

Tests: `pytest` (fast, pure layers) and `pytest -m host` (needs
`INGETRAZO_SRC` — default `./ingetrazo` — on the path; `tests/conftest.py`
adds it). Keep `ingetrazo/` out of pytest and ruff discovery.
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
