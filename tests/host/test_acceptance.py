# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""M1 acceptance: real models against hand-checked or OpenCutList lists.

Each ``samples/private/acceptance/*.json`` names a model in
``samples/private/`` and lists, per board and thickness, every part as
``[name, length mm, width mm, quantity]``. The cut list must match it
exactly: the same parts, sizes to 1 mm, the same quantities. Client
models never leave the developer's machine, so these tests are skipped
wherever the files are not (on CI, for anyone else).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = sorted((ROOT / "samples" / "private" / "acceptance")
                    .glob("*.json"))


def _cut_list(model: Path, materials: dict):
    from core.scene import Scene

    from cutlist.host.extract import extract
    from cutlist.model.grouping import build
    from cutlist.model.materials import Library, MaterialSpec, Role
    from cutlist.model.parts import read_part

    scene = Scene()
    if model.suffix.lower() == ".skp":
        from formats.skp import load_skp
        load_skp(scene, model)
    else:
        from formats.igz import load_into
        load_into(scene, model)
    library = Library({n: MaterialSpec(n, role=Role(r))
                       for n, r in materials.items()})
    parts = [read_part(r, library)
             for r in extract(scene, use_selection=False).parts]
    return build(parts, by_name=True)


@pytest.mark.skipif(not REFERENCES, reason="no private reference models")
@pytest.mark.parametrize("ref", REFERENCES, ids=lambda p: p.stem)
def test_cut_list_matches_the_reference(qt_app, ref):
    spec = json.loads(ref.read_text(encoding="utf-8"))
    model = ROOT / "samples" / "private" / spec["model"]
    if not model.exists():
        pytest.skip(f"{model.name} not here")
    cl = _cut_list(model, spec.get("materials", {}))
    leave_out = set(spec.get("not_in_reference", ()))

    ours: dict[str, Counter] = {}
    for section in cl.sections:
        key = f"{section.material}|{round(section.thickness * 1000)}"
        for line in section.lines:
            (name,) = line.display_names()
            if name in leave_out:
                continue
            ours.setdefault(key, Counter())[
                (name, round(line.length * 1000),
                 round(line.width * 1000))] += line.qty

    expected = {key: Counter({(n, ln, w): q for n, ln, w, q in rows})
                for key, rows in spec["groups"].items()}
    # Merge rows the reference lists twice (one part on two sheets).
    for key, rows in spec["groups"].items():
        c = Counter()
        for n, ln, w, q in rows:
            c[(n, ln, w)] += q
        expected[key] = c

    assert sorted(ours) == sorted(expected), "boards differ"
    for key in expected:
        missing = expected[key] - ours[key]
        extra = ours[key] - expected[key]
        assert not missing and not extra, \
            f"{key}: missing {dict(missing)}; extra {dict(extra)}"
