# Draft — comment on ingelibre/ingetrazo#309

*Status: DRAFT for Ronaldo's review. Not posted. Where: as a comment on
https://github.com/ingelibre/ingetrazo/issues/309 ("Cut list report and
cutting optimizer for furniture").*

---

Hi! I'm Ronaldo, a furniture designer from Brazil who has been using
SketchUp + OpenCutList for years and is moving to IngeTrazo. I've started
a cut list extension that answers this request:
**https://github.com/ronaldogalves/cutlist-ingetrazo** (GPL-3.0-or-later).

The plan, with OpenCutList as the benchmark for features and quality
(not a port — it's ~90k lines of Ruby tied to the SketchUp API):

- **v0.1:** a cut list tab grouped by material and thickness, with
  sheet/solid/ignore material types, grain, tag filters and quantities;
  2D guillotine cutting diagrams with kerf and trim; CSV, SVG and PDF
  exports. English, Spanish and Portuguese from the start.
- Pure Python on IngeTrazo's extension API (v2), nothing beyond what
  IngeTrazo already bundles. It builds on `core/parts.py` rather than
  duplicating it.

Right now it is at the skeleton stage (tab, menu, tests in CI against
0.5.7). Before going further, a few questions:

1. **Name.** We'd like to call it **"Cut List for IngeTrazo"**. Is it OK
   to use IngeTrazo's name that way, or would you prefer something else?
2. **Parts tray.** IngeTrazo already has *Copy cut list*. Is there
   anything you'd rather keep in the core — or anything from the
   extension you'd like upstream later?
3. **Undo for `group.ext`.** Per-part settings (grain, exclude, a note)
   live in `group.ext["cutlist"]`. To make each change one undo step we
   need a small command that sets `ext` on some groups — today each
   extension writes its own (like `WindowizerCommand`). Would you accept a
   PR adding a `SetGroupExtCommand` to `core.history`?
4. **#199 / Corte Certo.** I saw the `nr;nome;compr;larg;espes` export
   and the instance-name request. Corte Certo is common in Brazil, so I'd
   like the extension to offer that format as an export preset — happy to
   coordinate so we don't do the same work twice.
5. **Catalog.** When v0.1 is ready we'd like to be listed in
   ingetrazo-extensions (a release `.zip` with the `cutlist/` folder).

Two things I noticed on real furniture models, for separate issues:
two SketchUp 2020 files don't open (OpenSKP: `no reader for class
CCustomLineStyle`, and `back-ref to unwalked slot`); and the `.skp`
import flattens the instance tree, so a cabinet's boards arrive as
separate parts only when each carries its own tag — untagged boards are
merged into the cabinet, and the cabinet itself (and its name) is lost.
For a cut list, keeping the hierarchy would help a lot.

Thanks for IngeTrazo — it's a pleasure to build on.
