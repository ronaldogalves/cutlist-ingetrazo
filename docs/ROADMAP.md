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

## M1 — Cut list (≈1–2 weeks)

- [ ] `model/` dataclasses (`Part`, `MaterialSpec`, `CutListLine`) with
      unit tests.
- [ ] `host/extract.py`: selection or whole model → `[Part]`, component
      instances counted as quantity, surfaces separated, non-rectangular
      parts flagged.
- [ ] `host/store.py`: document data and `group.ext` read/write with
      `schema: 1`; every write is one undo step.
- [ ] Material settings dialog (type, thicknesses, stock sheets, grain,
      kerf, trim) with sensible defaults (e.g. 2750 × 1840 mm sheets,
      4 mm kerf, 10 mm trim — editable).
- [ ] Per-part settings via right-click (grain, may rotate, exclude, note).
- [ ] Tray panel: lines grouped by material + thickness; Refresh; stale
      indicator after edits; clicking a line highlights its parts.
- [ ] CSV export through configurable **supplier profiles** (columns,
      numbers and rounding, edge-band flags, encoding) with a Corte Certo
      preset — designed at M1 planning from `docs/IDEAS.md`.
- [ ] All strings through `tr()`; pt-BR and es catalogs complete.

**Accept:** on the two reference furniture models the cut list matches a
hand-checked list exactly (sizes to 1 mm, quantities, materials).

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
