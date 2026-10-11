# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Live tint and follow for the Logical Device and Keyboard pages (05 S131,
D-05-FOLLOW-ALL-PAGES): each input's held value by its row's liveIndex
(ControlTree's liveState reads kindAt / valueAt), and when a press moves
the page to its row."""

from __future__ import annotations

from collections.abc import Hashable

from gremlin import shared_state
from gremlin.config import Configuration


def may_follow() -> bool:
    """Options "Input highlighting" is on and nothing holds highlighting
    (Run holds it, 03 S114): a press may move the page."""
    if not Configuration().value("ui", "general", "input-highlighting"):
        return False
    return not (
        shared_state.suspend_input_highlighting() or shared_state.runtime_active()
    )


def follows(kind: str, value: float, was: float, synthetic: bool) -> bool:
    """A new press of a button, or a hat leaving centre (not an axis, not a
    program-made event), that may move the page to its row, as on the
    Device Bindings page."""
    if kind not in ("button", "hat") or value <= 0.5 or was > 0.5 or synthetic:
        return False
    return may_follow()


class LiveInputs:
    """Inputs' live values by index: index() gives a parent row its
    liveIndex; set() records an event's value."""

    def __init__(self) -> None:
        self._keys: list[Hashable] = []
        self._at: dict[Hashable, int] = {}
        self._kinds: dict[int, str] = {}
        self._values: dict[int, float] = {}

    def index(self, key: Hashable, kind: str = "") -> int:
        """The input's liveIndex; kind ("axis", "button", "hat") shows its
        bar or tint at rest before any event."""
        if key not in self._at:
            self._at[key] = len(self._keys)
            self._keys.append(key)
        index = self._at[key]
        if kind:
            self._kinds.setdefault(index, kind)
        return index

    def known(self, key: Hashable) -> bool:
        return key in self._at

    def value_of(self, key: Hashable) -> float:
        return self._values.get(self._at.get(key, -1), 0.0)

    def set(self, key: Hashable, kind: str, value: float) -> None:
        index = self.index(key)
        self._kinds[index] = kind
        self._values[index] = float(value)

    def kind_at(self, index: int) -> str:
        return self._kinds.get(index, "")

    def value_at(self, index: int) -> float:
        return self._values.get(index, 0.0)
