# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Edits to the open profile, counted (04 Q19, D-04-Q19).

The title's "*" reuses its last unsaved answer while this count hasn't
moved, instead of rebuilding the whole profile every 1.5 s. Save, Discard
and the other questions always compare exactly, so an edit that isn't
counted can only make the "*" late. Anything a profile saves notes its
edits here: EditNoted objects by themselves, the rest with note_edit().
"""

from __future__ import annotations

from typing import Any

_count = 0


def note_edit() -> None:
    """Something a profile saves may have changed."""
    global _count
    _count += 1


def edit_count() -> int:
    return _count


class EditNoted:
    """Setting an attribute the object already has to another value notes
    an edit; the first set (making or reading the object) doesn't."""

    __slots__ = ()

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        attrs = getattr(self, "__dict__", None)
        if attrs is not None and name in attrs:
            old = attrs[name]
            if old is value:
                # The same list or dict back, changed in place.
                if isinstance(value, (list, dict, set)):
                    note_edit()
            else:
                try:
                    changed = bool(old != value)
                except Exception:
                    changed = True
                if changed:
                    note_edit()
        super().__setattr__(name, value)
