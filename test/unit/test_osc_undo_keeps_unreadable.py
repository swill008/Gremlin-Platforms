# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""An OSC entry the program can't read (held in OscRows.unreadable, AD1)
survives the OSC page's Undo: the next Save writes it back in its place.

Spec: 09 AD1 (OSC keeps unreadable rows at Save, in their places).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import shiboken6

from gremlin import history_modules, shared_state
from gremlin import osc_device_file as odf
from gremlin.modules import store
from gremlin.osc import OscDevice, OscRows, OscRuntime
from gremlin.ui.osc_layout import OscLayoutModel
from test.unit._device_folders import put_module

GOOD = {"uid": "1" * 32, "type": "button", "id": 1, "label": "/gear"}
BAD = {"uid": "9" * 32, "type": "button", "id": "abc", "label": "/broken"}
GOOD_2 = {"uid": "2" * 32, "type": "button", "id": 2, "label": "/flaps"}


def _clear() -> None:
    rows = OscDevice().rows
    rows.reset()
    rows.unreadable = []
    rows.mark_saved()
    OscRuntime().reset_live()


@pytest.fixture
def page(
    qapp: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[OscLayoutModel]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *_a, **_k: None)
    saved = shared_state.current_profile
    _clear()
    # OSC's own device folder (03 S128).
    path = put_module(folder, "OSC", json.dumps({odf.KEY: [GOOD, BAD, GOOD_2]}))
    assert path == odf.path()
    odf.load()
    assert [entry for _, entry in OscDevice().rows.unreadable] == [BAD]
    model = OscLayoutModel()
    yield model
    model.endPane()
    # Deleted here, not when pytest lets go of the test's arguments: its
    # gremlin.signal connections go with it, before the conftest check.
    shiboken6.delete(model)
    _clear()
    shared_state.current_profile = saved


def _on_file() -> list:
    return json.loads(odf.path().read_text(encoding="utf-8"))[odf.KEY]


def _edit_and_undo(page: OscLayoutModel) -> None:
    key = page.keyOfUid(GOOD_2["uid"])
    assert key
    assert page.changeAddress(key, "/slats") == ""
    assert OscDevice().find_address("/slats") is not None
    page.undo()
    # Undo put the inputs back (load_dict ran) and left OSC's file to save.
    assert OscDevice().find_address("/flaps") is not None
    assert OscDevice().find_address("/slats") is None
    assert OscDevice().rows.dirty


def test_undo_then_save_keeps_the_unreadable_entry_in_place(
    page: OscLayoutModel,
) -> None:
    _edit_and_undo(page)
    assert [entry for _, entry in OscDevice().rows.unreadable] == [BAD]
    assert odf.save()
    saved = _on_file()
    assert saved[1] == BAD
    assert [entry["label"] for entry in saved] == ["/gear", "/broken", "/flaps"]


def test_old_restore_dropped_it(
    page: OscLayoutModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proof the test above guards the fix: with the old restore line
    (load_dict without keep_unreadable) the entry is gone after Save."""
    real = OscRows.load_dict

    def old(self: OscRows, data: dict, *, keep_unreadable: bool = False) -> None:
        real(self, data)

    monkeypatch.setattr(OscRows, "load_dict", old)
    _edit_and_undo(page)
    assert OscDevice().rows.unreadable == []
    assert odf.save()
    assert BAD not in _on_file()
