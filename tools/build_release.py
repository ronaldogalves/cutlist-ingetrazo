# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Build the release zip: ``dist/cutlist-<version>.zip``.

The zip holds ONE folder, ``cutlist/``, with forward-slash paths and no
caches — what IngeTrazo's Extension manager installs from a catalog entry
and what a user unzips into the plugins folder by hand. Entries are
written in a fixed order with a fixed date, so the same source gives the
same bytes and the same SHA-256 (the catalog pins it).

    python tools/build_release.py
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "cutlist"
STAMP = (2026, 1, 1, 0, 0, 0)


def version() -> str:
    text = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def files() -> list[Path]:
    return sorted(p for p in PACKAGE.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix != ".pyc")


def build() -> Path:
    out = ROOT / "dist" / f"cutlist-{version()}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files():
            name = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes())
    return out


if __name__ == "__main__":
    zip_path = build()
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"{zip_path.relative_to(ROOT)}  sha256 {digest}")
    sys.exit(0)
