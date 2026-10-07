# Ideas

A parking lot: ideas worth keeping that are not scheduled yet. When a
milestone is planned, we pull from here into `ROADMAP.md`. Newest at the
bottom of each section; note who raised it and when.

## Scope and part detection

- **Scope window on first use.** When the user runs the cut list, a window
  asks what to include: the selection, by layer/tag, and a checkbox
  "also include geometry in groups (not only components)". It has a
  "don't show again" checkbox; the same options stay reachable from the
  panel so the user can change their mind. *(Ronaldo, 2026-10-07)*
- **Unnamed groups listed, not lost**, as "Group #n" with a short, stable
  number shared by the cut list, diagrams and 3D highlight. *(Ronaldo,
  2026-10-07 — goes into D-006)*
- **Warnings instead of silence** for geometry we cannot classify (loose
  faces in a cabinet group, non-rectangular parts). *(2026-10-07 — goes
  into D-006)*

## Settings that persist

- **User defaults that outlive the document.** Kerf, trim, stock sheets,
  the material library, CSV separator, scope choices: set once, used by
  every new model; each model can still override. *(Ronaldo, 2026-10-07)*
- **Size tolerance / rounding** as a setting (e.g. 0.1, 0.5, 1 mm, or a
  fraction of an inch), used both to merge identical parts and to absorb
  sloppy or imported geometry (17.98 mm read as 18). *(Ronaldo,
  2026-10-07)*

## Beyond the cut list ("the best woodworking plugin")

- **Hardware list:** hinges, drawer slides, handles, screws — counted from
  the model instead of by hand. *(Ronaldo, 2026-10-07)*
- **Profiles and rails** (aluminium profiles, profiled rails) as 1D stock
  with lengths and totals. *(Ronaldo, 2026-10-07)*

## From the M0 spike (2026-10-07)

- **Corte Certo export preset**: `nr;nome;compr;larg;espes`, one line per
  piece (not merged), whole mm, L ≥ W ≥ T — the Brazilian panel-cutting
  software a real IngeTrazo user feeds by hand (IngeTrazo issue #199).
  Strong candidate for M1's CSV export.
- **Cut list per phase**: models tag parts by job phase (`FASE 1`,
  `FASE 2`, `CORTE EXTRA`); a saved tag filter per phase gives one cut
  list per delivery.
- **Group lines by piece of furniture** using the name prefix (`GR`,
  `COZ`, `QTO`…) or the parent container — a "module" column.
- **Mirrored parts**: OpenCutList marks a mirrored copy of a part (left
  vs right side) in its lists; worth matching for edge banding and grain.
- **Defaults from real use**: Ronaldo's OpenCutList runs used
  2740 × 1830 mm MDF sheets, 3 mm blade, 10 mm trim — the brief's
  2750 × 1840 / 4 mm defaults may need to change (and are only defaults).
