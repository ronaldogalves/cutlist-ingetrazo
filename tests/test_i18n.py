# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Our translations: lookup, fallback, and that every string the code
asks for is translated in every language we ship."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cutlist import i18n
from cutlist.i18n import tr

PACKAGE = Path(i18n.__file__).resolve().parent.parent


@pytest.fixture
def language():
    """Set the language for one test, then back to English."""
    def use(code):
        i18n.set_language_source(lambda: code)
    yield use
    i18n.set_language_source(lambda: "en")


def test_english_is_the_source(language):
    language("en")
    assert tr("Cut List") == "Cut List"


def test_translated(language):
    language("pt-BR")
    assert tr("Cut List") == "Lista de corte"


def test_unknown_text_and_language_fall_back_to_english(language):
    language("pt-BR")
    assert tr("No such string") == "No such string"
    language("xx")
    assert tr("Cut List") == "Cut List"


def test_kwargs_are_interpolated_after_lookup(language):
    language("en")
    assert tr("{n} parts", n=3) == "3 parts"


def test_a_broken_language_source_falls_back_to_english():
    def broken():
        raise RuntimeError("host went away")
    i18n.set_language_source(broken)
    try:
        assert tr("Cut List") == "Cut List"
    finally:
        i18n.set_language_source(lambda: "en")


def _strings_in_code() -> set[str]:
    """Every literal passed to ``tr(...)`` in the package, plus the
    module-level constants we pass to it by name (``PANEL_TITLE``)."""
    found: set[str] = set()
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = {
            t.id: node.value.value
            for node in ast.walk(tree) if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            for t in node.targets if isinstance(t, ast.Name)}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "tr" and node.args):
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.add(arg.value)
                elif isinstance(arg, ast.Name) and arg.id in constants:
                    found.add(constants[arg.id])
    return found


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_every_string_is_translated(lang):
    missing = _strings_in_code() - set(i18n.catalog(lang))
    assert not missing, f"missing in {lang}.json: {sorted(missing)}"


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_no_stale_translations(lang):
    stale = set(i18n.catalog(lang)) - _strings_in_code()
    assert not stale, f"no longer used, remove from {lang}.json: {sorted(stale)}"


@pytest.mark.parametrize("lang", i18n.LANGUAGES)
def test_placeholders_survive_translation(lang):
    import string
    fields = lambda s: {f for _, f, _, _ in string.Formatter().parse(s) if f}  # noqa: E731
    for source, translated in i18n.catalog(lang).items():
        assert fields(source) == fields(translated), (lang, source)
