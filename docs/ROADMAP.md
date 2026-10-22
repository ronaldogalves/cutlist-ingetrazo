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

- [x] Model D: all 86 sheet parts match OpenCutList by name, size and
      quantity, per board and thickness (`tests/host/test_acceptance.py`,
      run locally: the model is private). It found one real difference
      on the way — a part name with a trailing space — now tidied.
- [x] Ronaldo's hand checks: exports opened in Excel and accepted by the
      supplier's site; the windows used on real work. Done 2026-10-20:
      CorteCloud (clipboard paste, and an .xlsx opened in Excel then
      pasted) and Leo Madeiras' new web import both accepted, edge bands
      included. Found on the way and fixed: Export wrote nothing (a
      click's checked flag), workbooks named .csv, one-by-one profile
      import, Leo's retired SAP-code layout.

## Pre-release v0.0.x — the cut list and its exports

*Planned 2026-10-09 (Ronaldo).* Once M1's acceptance check passes, publish
a **pre-release** before the diagrams exist: for woodworkers who order
pre-cut boards, the supplier makes the cutting plan, so the cut list and
the export are what they need. A GitHub pre-release with the `cutlist/`
zip, a short CHANGELOG and the README's known limitations; feedback from
a few trusted woodworkers before M2–M3.
- [x] Ship the **CorteCloud** and **Leo Madeiras** profiles (D-011), each
  reproduced exactly in a test. Leo's is its **new web import**
  (2026-10: header row required, free names, no SAP codes), checked
  byte for byte against a file Leo's site accepted. Offered once to
  every user; a deleted one does not come back.
- [x] A part not as thick as its board comes is flagged (antrrax's 14 mm
  part on a 15 mm board, IngeTrazo #199), when the board's thicknesses
  are set up.
- [x] CHANGELOG, README install steps and known limitations;
  `tools/build_release.py` builds a reproducible zip, tested to install
  through IngeTrazo's own Extension manager code. No `extension.json`
  is needed: the manager writes it when it installs.
- [x] Publish the GitHub pre-release: tag `v0.0.1`, the zip attached
  (2026-10-20, approved by Ronaldo).
- [x] Note on IngeTrazo #199 (2026-10-20, approved by Ronaldo).
- [x] Catalog entry in `ingelibre/ingetrazo-extensions`: pull request
  #128 opened 2026-10-20, updated to 0.1.0, **merged 2026-10-21** —
  listed at ingetrazo.com/extensiones as 0.1.0 ("Community" until a
  maintainer reviews the code). Later versions sent from Ronaldo's
  account publish on their own. Add a screenshot later.
- When listed on IngeTrazo's website (catalog entry, README, release
  notes): say that profile feedback is welcome and that profiles for
  other suppliers can join the shipped set (D-011).

## M2 — 2D packer (≈1–2 weeks)

*Done 2026-10-21.* Decisions D-012 to D-016.

- [x] `packing/base.py`: `Packer` protocol, `Piece`, `Stock`, `SawSettings`,
      `Placement`, `Cut`, `Sheet`, `Layout` — plain and JSON-safe, so a
      layout can be saved in the model (D-012).
- [x] `packing/guillotine.py`: staged guillotine (2, 3 or 4 stages), kerf,
      trim on 4 or 2 edges, grain/rotation, first cuts lengthwise,
      crosswise or the better of both, several stock sizes, shop
      leftovers first and untrimmed, leftovers as the real pieces the cuts
      make, multi-start with a seed (deterministic).
- [x] `packing/jobs.py`: a cut list to one job per board — part letters
      A…Z, AA… across the job (D-016), grain and rotation from the part
      and its board, the board's kerf and trim.
- [x] Property tests (`tests/test_packing.py`) with an independent
      checker: no overlaps (kerf included), every part inside the trimmed
      sheet, grain respected, cuttable with straight cuts, every part
      placed or reported — on 150 random jobs and the special cases.
- [x] `benchmarks/run.py`: 14 jobs — 10 synthetic (`benchmarks/cases/`)
      and Cozinha 03's four boards (private) against OpenCutList's PDFs.

**Accept:** all property tests pass; on the benchmark set, sheet count is
never worse than OpenCutList's by more than one sheet and average waste is
within 10 %; a 200-part job packs in under 2 s.

**Result (2026-10-21):** Cozinha 03 — the same sheet count as OpenCutList
on all four boards (plywood with grain: 5 = 5; MDF: 1 = 1 ×3) and the same
cut counts within one (57/57, 47/48, 20/20, 11/11). Efficiency equal (ours
is measured on the whole sheet, OpenCutList's on the trimmed one: 0.982 ×).
197 parts in 0.3 s. Synthetic jobs: 4 of 10 one sheet above the area
lower bound (which ignores the blade and the shapes); more attempts do not
change them — a smarter second pass is a later improvement, not a bug.

## M3 — Diagrams and exports (≈1–2 weeks)

*Done 2026-10-21* (D-012 to D-016). Released as 0.1.0 at Ronaldo's call.

- [x] Diagram window: one sheet per page, parts lettered and labelled
      (letter, size), grain arrows, leftovers drawn as the real pieces the
      cuts make (D-013), totals per material; the totals page is
      optional when printing (D-014).
- [x] Hover a part: its cuts, stage by stage; hover a cut: its fence
      distance; first-stage cuts marked as "can go first" (D-016 §8).
- [x] Packing runs on a worker thread; UI stays responsive; result relayed
      per the threading rule in `CLAUDE.md`.
- [x] One layout description (`export/plan.py`) drawn by QPainter for
      screen and PDF (QPdfWriter, A4/Letter), and written as SVG by
      `export/svg.py` (stdlib only).
- [x] Right-click a part on the diagram: switch grain (line or one piece),
      allow/forbid rotation, part settings (oversize), leave out of this
      layout, show in model; written to the model, layout redone (D-014).
- [x] Save a layout in the document and reopen it as it was; say what
      changed in the model since, and offer to redo it (D-012).
- [x] Part letters consistent between cut list (the panel's first
      column), diagrams and viewport highlight (D-016 §1).
- [x] Also: sheet sizes per thickness and size templates (D-013 §2–3),
      oversize per board and per part (D-013 §4), sheet sizes asked once.

**Accept:** a printed PDF of a kitchen-cabinet job is usable at the saw
without the model open.
- [x] Ronaldo's check (2026-10-21): "everything looks awesome", after two
      fixes found on the way — Cancel on sheet sizes went on, and save
      windows opened in System32 for an unsaved model.

## M4 — Release v0.1 (≈1 week)

*0.1.0 published 2026-10-21 at Ronaldo's call* —
https://github.com/ronaldogalves/cutlist-ingetrazo/releases/tag/v0.1.0 —
with three items below still open; they go in the next release.

- [ ] README with screenshots, install steps for Linux/Windows/macOS, the
      tested IngeTrazo version, and the scope ("what v0.1 does not do").
      *Screenshot, Windows steps, tested version and limitations are in;
      Linux/macOS steps wait for a real test there.*
- [x] User guide (`docs/user-guide.md`) in English, pt-BR and es
      (2026-10-22, linked from the README).
- [x] Release zip (the `cutlist/` folder) attached to a GitHub release;
      `CHANGELOG.md` (v0.1.0, built reproducibly by
      `tools/build_release.py`).
- [ ] Tested on a clean IngeTrazo Flatpak and on Windows. *Windows: done
      (Ronaldo, installed 0.5.9). Linux: the test suite only.*
- [x] Announced to IngeTrazo maintainers; listing requested — listed in
      the catalog (ingelibre/ingetrazo-extensions#128, merged 2026-10-21).

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
