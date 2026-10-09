# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Where the cut list's settings live, and the cascade between them.

Three places, broadest first (D-007 §6):

- **the user's defaults** — a JSON file next to IngeTrazo's plugins
  folder, shared by every model: the material library, units, tolerance…
- **the model** — our document data (``app.document_data``), saved in
  the ``.igz``: only what this model does differently. Every write is one
  undo step.
- **the part** — ``group.ext["cutlist"]``: grain, exclude, note, face 1.
  Written through :class:`SetGroupExtCommand`, one undo step per change.

Plus the "Group #n" numbers (D-008), kept in the document beside our data
and keyed by part uid.
"""
from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import replace
from pathlib import Path

from ..model.materials import Library, MaterialSpec
from ..model.parts import PartOverride
from ..model.settings import Settings, diff, resolve

log = logging.getLogger("cutlist")

SCHEMA = 1


def _command_base():
    from core.history import Command
    return Command


def make_set_group_ext(key: str, changes: dict):
    """A command setting ``group.ext[key]`` on several groups at once — one
    undo step. ``changes`` maps a group to its new value (``None``
    removes our key). IngeTrazo has no core command for this (yet): this
    is the pattern of its Windowizer example, reduced to ``ext``."""
    Command = _command_base()

    class SetGroupExtCommand(Command):
        def __init__(self) -> None:
            self.key = key
            self.changes = {g: copy.deepcopy(v) for g, v in changes.items()}
            self.before: dict = {}

        @staticmethod
        def _put(g, k, value) -> None:
            ext = dict(getattr(g, "ext", None) or {})
            if value is None:
                ext.pop(k, None)
            else:
                ext[k] = copy.deepcopy(value)
            g.ext = ext or None

        def do(self, scene) -> None:
            self.before = {g: copy.deepcopy((g.ext or {}).get(self.key))
                           for g in self.changes}
            for g, value in self.changes.items():
                self._put(g, self.key, value)
            scene.version += 1

        def undo(self, scene) -> None:
            for g, value in self.before.items():
                self._put(g, self.key, value)
            scene.version += 1

    return SetGroupExtCommand()


def user_dir() -> Path:
    """Folder of the user's defaults: ``CUTLIST_USER_DIR`` (tests), else
    ``…/ingetrazo/cutlist`` beside IngeTrazo's plugins folder."""
    env = os.environ.get("CUTLIST_USER_DIR")
    if env:
        return Path(env)
    from core.extensions import user_plugins_dir
    return user_plugins_dir().parent / "cutlist"


class Store:
    """Reads and writes all three places for one IngeTrazo window."""

    def __init__(self, app) -> None:
        self.app = app

    # ---- the user's defaults (a file) -----------------------------------
    @property
    def user_file(self) -> Path:
        return user_dir() / "defaults.json"

    def user_data(self) -> dict:
        try:
            data = json.loads(self.user_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            log.exception("could not read %s", self.user_file)
            return {}

    def write_user_data(self, data: dict) -> None:
        data = {**data, "schema": SCHEMA}
        path = self.user_file
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                  sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    # ---- the model (document data) --------------------------------------
    def doc_data(self) -> dict:
        data = self.app.document_data(default=None)
        return data if isinstance(data, dict) else {}

    def write_doc_data(self, data: dict) -> None:
        """One undo step; the document becomes unsaved."""
        self.app.set_document_data({**data, "schema": SCHEMA})

    # ---- materials ---------------------------------------------------------
    def library(self) -> Library:
        """The user's library, overridden material by material by the
        model's."""
        user = Library.from_dict(self.user_data().get("materials"))
        doc = Library.from_dict(self.doc_data().get("materials"))
        return Library({**user.specs, **doc.specs})

    def save_materials(self, specs: list[MaterialSpec], *,
                       remember: bool) -> None:
        """Store ``specs`` in the model (one undo step) and, with
        ``remember``, in the user's defaults for every model."""
        doc = self.doc_data()
        mats = dict(doc.get("materials") or {})
        for spec in specs:
            mats[spec.name] = spec.to_dict()
        self.write_doc_data({**doc, "materials": mats})
        if remember:
            user = self.user_data()
            umats = dict(user.get("materials") or {})
            for spec in specs:
                umats[spec.name] = spec.to_dict()
            self.write_user_data({**user, "materials": umats})

    # ---- custom fields (D-009 §10) ----------------------------------------------
    def fields(self):
        """The model's custom fields; a model that has none yet starts from
        the user's (their usual Cliente/Ambiente and tag rules)."""
        from ..model.fields import Fields
        doc = self.doc_data()
        if "fields" in doc:
            return Fields.from_list(doc.get("fields"))
        return Fields.from_list(self.user_data().get("fields"))

    def save_fields(self, fields, *, remember: bool) -> None:
        doc = self.doc_data()
        if doc.get("fields") != fields.to_list():
            self.write_doc_data({**doc, "fields": fields.to_list()})
        if remember:
            self.write_user_data({**self.user_data(),
                                  "fields": fields.to_list()})

    # ---- export profiles (D-009 §1) --------------------------------------------
    def profiles(self) -> dict:
        """name → Profile; the generic one when the user has none."""
        from ..export.profile import Profile, generic
        raw = self.user_data().get("export_profiles")
        out = {}
        if isinstance(raw, dict):
            for name, d in raw.items():
                p = Profile.from_dict(d)
                out[str(name)] = replace(p, name=str(name))
        if not out:
            g = generic()
            out[g.name] = g
        return out

    def last_profile(self) -> str | None:
        name = self.user_data().get("last_export_profile")
        return name if isinstance(name, str) else None

    def save_profiles(self, profiles: dict, last: str | None) -> None:
        self.write_user_data({
            **self.user_data(),
            "export_profiles": {n: p.to_dict() for n, p in profiles.items()},
            "last_export_profile": last})

    # ---- settings ------------------------------------------------------------
    def settings(self) -> Settings:
        return resolve(self.user_data().get("settings"),
                       self.doc_data().get("settings"))

    def user_settings(self) -> Settings:
        return resolve(self.user_data().get("settings"))

    #: How the user works, not what a model is: always in their defaults.
    USER_ONLY = ("scope_asked", "merge_by_size", "use_selection",
                 "units_in_cells")

    def save_settings(self, settings: Settings, *, remember: bool) -> None:
        """The model keeps what differs from the user's defaults (one undo
        step, only when that changes); with ``remember`` the defaults
        become these settings. Personal preferences (:data:`USER_ONLY`)
        always go to the defaults."""
        user = self.user_data()
        current = resolve(user.get("settings"))
        if remember:
            new_user = settings
        else:
            new_user = replace(current, **{k: getattr(settings, k)
                                           for k in self.USER_ONLY})
        if new_user != current:
            self.write_user_data({**user,
                                  "settings": diff(new_user, Settings())})
        model = diff(settings, new_user)
        for k in self.USER_ONLY:
            model.pop(k, None)
        doc = self.doc_data()
        if model != (doc.get("settings") or {}):
            self.write_doc_data({**doc, "settings": model})

    def save_user_setting(self, **values) -> None:
        """A preference that is not part of the model (no undo step)."""
        user = self.user_data()
        current = resolve(user.get("settings"))
        new = replace(current, **values)
        self.write_user_data({**user, "settings": diff(new, Settings())})

    def save_model_setting(self, **values) -> None:
        """One setting of this model (one undo step)."""
        current = self.settings()
        self.save_settings(replace(current, **values), remember=False)

    # ---- parts -----------------------------------------------------------------
    def overrides(self, groups) -> dict:
        key = self.app.key
        return {g.uid: PartOverride.from_dict((g.ext or {}).get(key))
                for g in groups}

    def set_overrides(self, changes: dict) -> bool:
        """``{group: PartOverride}`` → ``group.ext``, one undo step.
        False (and a status message upstream) when IngeTrazo refused it."""
        key = self.app.key
        values = {g: None if o.is_empty else o.to_dict()
                  for g, o in changes.items()}
        vp = self.app.viewport
        vp.history.execute(make_set_group_ext(key, values))
        if getattr(vp.history, "last_error", None):
            log.error("part settings not applied: %s", vp.history.last_error)
            return False
        notify = getattr(vp, "notify_scene_changed", None)
        if callable(notify):
            notify()
        vp.update()
        return True

    # ---- Group #n (D-008) ----------------------------------------------------
    @property
    def _numbers_key(self) -> str:
        return f"{self.app.key}.numbers"

    def numbers(self, uids) -> dict[str, int]:
        """A stable number for each uid, giving new ones as needed.

        Kept in the document beside our data, keyed by uid, so a copied
        part (new uid) gets its own number. Handing out a number is
        bookkeeping, not an edit: it is written without an undo step and
        without marking the document unsaved; it is saved with the next
        save."""
        data = self.app.scene.plugin_data
        table = data.get(self._numbers_key)
        if not isinstance(table, dict):
            table = {}
        changed = False
        top = max((n for n in table.values() if isinstance(n, int)),
                  default=0)
        for uid in uids:                         # model order
            if not isinstance(table.get(uid), int):
                top += 1
                table[uid] = top
                changed = True
        if changed:
            data[self._numbers_key] = table
        return {uid: table[uid] for uid in uids}
