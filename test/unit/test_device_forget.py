# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Remove from Library forgets the device's friendly name, Home card
settings and calibration (10 S52, D-10-REMOVE-ALL); other devices' stay,
and the History entry's Restore puts them back. Every setting a test
changes is put back."""

from __future__ import annotations

import sys

sys.path.append(".")

from collections.abc import Iterator

import pytest
from PySide6 import QtCore

from gremlin.config import Configuration

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_GONE = "11111111-2222-3333-4444-555555555555"
_OTHER = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
_CARD_KEYS = ["hidden-slugs", "card-order", "card-sizes", "card-stacks", "kept-stubs"]


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple]]:
    """Two devices with an alias, card settings and calibration; the
    History entries recorded are collected, not written."""
    from gremlin import device_aliases, history
    from gremlin.ui import module_model

    cfg = Configuration()
    device_aliases._ensure()
    module_model._ensure_display_options()
    for guid in (_GONE, _OTHER):
        for axis in (1, 2):
            cfg.init_calibration(guid, axis)
    keys = [(device_aliases.SECTION, device_aliases.GROUP, device_aliases.NAME)]
    keys += [("display", "status", name) for name in _CARD_KEYS]
    keys += [("calibration", g, str(a)) for g in (_GONE, _OTHER) for a in (1, 2)]
    before = [cfg.value(*key) for key in keys]

    recorded: list[tuple] = []
    monkeypatch.setattr(history, "record", lambda *a, **k: recorded.append(a))

    device_aliases.set_alias(_GONE, "Old throttle")
    device_aliases.set_alias(_OTHER, "Main stick")
    cfg.set("display", "status", "hidden-slugs", "old_throttle,main_stick")
    cfg.set("display", "status", "card-order", "main_stick,old_throttle,pedals")
    sizes = "old_throttle=300x200,main_stick=400x300"
    cfg.set("display", "status", "card-sizes", sizes)
    stacks = "old_throttle+main_stick|pedals+main_stick+old_throttle"
    cfg.set("display", "status", "card-stacks", stacks)
    cfg.set("display", "status", "kept-stubs", "old_throttle,main_stick")
    for guid in (_GONE, _OTHER):
        cfg.set_calibration(guid, 1, (-1000, -10, 10, 1000, True))
        cfg.set_calibration(guid, 2, (-500, 0, 0, 500, False))
    recorded.clear()
    yield recorded
    for key, value in zip(keys, before):
        cfg.set(*key, value)
    device_aliases._CACHE = None


def _state() -> dict:
    from gremlin import device_aliases

    cfg = Configuration()
    out = {name: cfg.value("display", "status", name) for name in _CARD_KEYS}
    out["aliases"] = dict(device_aliases._load())
    out["cal"] = {
        (g, a): list(cfg.value("calibration", g, str(a)))
        for g in (_GONE, _OTHER) for a in (1, 2)
    }
    return out


def test_forget_device_clears_its_settings_only(setup: list[tuple]) -> None:
    from gremlin.device_forget import forget_device

    forget_device("Old Throttle", "{" + _GONE.lower() + "}")

    state = _state()
    assert state["aliases"].get(_GONE) is None
    assert state["aliases"][_OTHER] == "Main stick"
    assert state["hidden-slugs"] == "main_stick"
    assert state["card-order"] == "main_stick,pedals"
    assert state["card-sizes"] == "main_stick=400x300"
    assert state["card-stacks"] == "pedals+main_stick"
    assert state["kept-stubs"] == "main_stick"
    assert state["cal"][(_GONE, 1)] == [-32768, 0, 0, 32767, True]
    assert state["cal"][(_GONE, 2)] == [-32768, 0, 0, 32767, True]
    assert state["cal"][(_OTHER, 1)] == [-1000, -10, 10, 1000, True]
    assert state["cal"][(_OTHER, 2)] == [-500, 0, 0, 500, False]
    assert len(setup) == 1 and setup[0][0] == "settings"


def test_history_restore_puts_the_settings_back(setup: list[tuple]) -> None:
    from gremlin.device_forget import forget_device
    from gremlin.ui import history_model

    old = _state()
    forget_device("Old Throttle", _GONE)
    assert _state() != old
    area, title, subject, before, after = setup[0][:5]
    entry = {
        "area": area, "kind": "save", "title": title,
        "subject": subject, "before": before, "after": after,
    }

    ok, _message = history_model._restore_one(entry, "before")

    assert ok
    assert _state() == old
