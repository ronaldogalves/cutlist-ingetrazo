# Roadmap

Estimates assume one developer working with Claude Code, part-time.
Each milestone ends with its acceptance criteria met and ticked here.

## M0 — Foundations and spike (≈1 week)

- [x] Repository created: GPL-3.0-or-later `LICENSE`, `README.md`,
      `CLAUDE.md`, `docs/`, `.gitignore`, `pyproject.toml` (pytest config,
      ruff), GitHub Actions running `pytest` on Linux.
- [x] Dev setup works as in `CLAUDE.md`: plugin symlinked into the user
      plugins folder, IngeTrazo starts, "CutList" appears in Extensions.
- [x] `setup(app)` adds an empty tray panel and a submenu; a deliberately
      raised error shows IngeTrazo's "load error" entry, not a crash.
- [x] Spike: a throwaway script prints parts from IngeTrazo's
      `examples/*.igz` and ~~two hand-built furniture models~~ six real
      furniture jobs from SketchUp (one built nested; one checked against
      OpenCutList). Part-detection rule decided and recorded as D-006
      (and D-007). Not covered: a splayed-leg table — solid wood, after
      v0.1. Notes: `docs/spikes/M0-part-detection.md`.
- [x] `tests/conftest.py` puts `$INGETRAZO_SRC` on `sys.path`; the `host`
      marker separates tests that need IngeTrazo.
- [x] Issue/discussion opened with IngeTrazo maintainers (comment on ingelibre/ingetrazo#309).

## M1 — Cut list (≈2–3 weeks)

Scope drawn 2026-10-07 after D-006/D-007: the **board** cut list, read
through material roles, with coverings and bands **listed** per part (not
yet deducted, totalled or laid out). Built in three visible steps.

**Step A — read the model and show the list**
- [x] `model/`: `Part` (core, face 1/2, four edges, flags), `MaterialSpec`
      with roles, `CutListLine`/`Section`/`CutList`, measurement on the
      part's own axes — with unit tests (cases from the M0 spike).
- [x] `host/extract.py`: selection or whole model → raw parts (D-006 leaf
      rule, visibility, tags, paint inheritance), loose-geometry notices.
- [x] Tray panel: sections by board + thickness, lines merged by
      measurement within tolerance, "Needs a look" and "Excluded";
      Refresh; out-of-date notice after edits; tag filter; clicking a
      line highlights its parts in the viewport.

**Step B — settings that stay**
- [x] `host/store.py`: document data and `group.ext` with `schema: 1`;
      every write one undo step (our own `Command`, D-007).
- [x] User defaults outside the document (material library, tolerance,
      tag choices) and the cascade user → model → material → part.
- [x] Material library dialog: role per material, thicknesses, stock
      sheets, grain, kerf, trim; covering/band thickness, oversize,
      deduction (stored, used later).
- [x] Per-part settings (right-click and from the list): grain, may
      rotate, exclude, note, flip face 1.
- [x] Stable "Group #n" numbers stored in the document by uid (D-008).
- [x] Settings window: **units** ("use the model's units" by default, or
      the cut list's own unit and precision — an architectural model in
      metres still lists in mm), size tolerance, merge same size by
      default (Ronaldo, 2026-10-08).
- [x] Scope window on first use ("don't show again"), reachable from the
      panel; components-only option.

**Step C — export** (design: D-009)
- [x] `export/`: profiles (to/from dict), rows from the cut list (grain
      first, bands relative to face 1, numbers, yes/no values, code
      table, fixed text and templates, one per piece or merged), split
      and file names; problems reported, never blanks.
- [x] Writers: delimited text (separator, encoding, line endings,
      quoting, trailing separator, header), `.xlsx` with the stdlib,
      clipboard.
- [x] Both real supplier templates reproduced byte for byte in tests.
- [x] Custom fields: defined in Settings, model values, tag rules,
      per-part overrides.
- [x] Export window: profile combo (save, save as, rename, delete,
      import/export file, `*` when changed), columns editor, file and
      number options, code table, live preview.
- [x] All strings through `tr()`; pt-BR and es catalogs complete.

**Accept:** on the reference models the cut list matches a hand-checked
list exactly (sizes to 1 mm, quantities, materials) — model D against its
OpenCutList diagrams first (all 86 sheet parts).

## Pre-release v0.0.x — the cut list and its exports

*Planned 2026-10-09 (Ronaldo).* Once M1's acceptance check passes, publish
a **pre-release** before the diagrams exist: for woodworkers who order
pre-cut boards, the supplier makes the cutting plan, so the cut list and
the export are what they need. A GitHub pre-release with the `cutlist/`
zip, a short CHANGELOG and the README's known limitations; feedback from
a few trusted woodworkers before M2–M3.

## M2 — 2D packer (≈1–2 weeks)

- [ ] `packing/base.py`: `Packer` protocol, `Stock`, `Placement`, `Layout`.
- [ ] `packing/guillotine.py`: kerf, trim, grain/rotation, several stock
      sizes, multi-start with seed and time budget.
- [ ] Property tests: no overlaps (kerf included), every part inside the
      usable area, grain respected, every part placed or reported as not
      fitting any stock.
- [ ] `benchmarks/`: 10+ cases (real cabinet jobs and synthetic ones) with
      sheet count and waste; where possible, OpenCutList's results for the
      same parts recorded for comparison.

**Accept:** all property tests pass; on the benchmark set, sheet count is
never worse than OpenCutList's by more than one sheet and average waste is
within 10 %; a 200-part job packs in under 2 s.

## M3 — Diagrams and exports (≈1–2 weeks)

- [ ] Diagram window: one sheet per page, parts numbered and labelled
      (name, size), grain arrows, waste hatched, totals per material.
- [ ] Packing runs on a worker thread; UI stays responsive; result relayed
      per the threading rule in `CLAUDE.md`.
- [ ] One layout description drawn by QPainter for screen and PDF
      (QPdfWriter, A4/Letter), and written as SVG by `export/svg.py`
      (stdlib only — IngeTrazo builds may not ship QtSvg).
- [ ] Part numbers consistent between cut list, diagrams and viewport
      highlight.

**Accept:** a printed PDF of a kitchen-cabinet job is usable at the saw
without the model open.

## M4 — Release v0.1 (≈1 week)

- [ ] README with screenshots, install steps for Linux/Windows/macOS, the
      tested IngeTrazo version, and the scope ("what v0.1 does not do").
- [ ] User guide (`docs/user-guide.md`) in English, pt-BR and es.
- [ ] Release zip (the `cutlist/` folder) attached to a GitHub release;
      `CHANGELOG.md`.
- [ ] Tested on a clean IngeTrazo Flatpak and on Windows.
- [ ] Announced to IngeTrazo maintainers; listing requested.

## v0.2 — Support and first feedback

- [ ] Donation platform chosen (BRIEF §10.5); `.github/FUNDING.yml`.
- [ ] "Support CutList" menu entry + About dialog section (links, optional
      PIX QR). No pop-ups, no network calls.
- [ ] Fixes and the top requests from v0.1 users.
- [ ] Pick the next feature from the candidates list in BRIEF §4.

## Later (unordered candidates)

1D diagrams for solid wood · edge banding · labels · cost estimate ·
DXF export (ezdxf) · panel-supplier formats · XLSX · optional native
packer backend · OpenCutList-style part drawings.
