# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Home's Delete Device is one History entry, "Deleted X", holding its
"stick deleted" autosave and the module-file delete; Restore puts the file
back (03 S94a, D-10-ONE-ENTRY-TITLES). Inside a group already open (the
Device Library's Remove) it adds no entry of its own."""

from __future__ import annotations

import json
from pathlib import Path

from gremlin import history
from gremlin.ui import history_model, module_model
from test.unit import test_stage1_modules
from test.unit.test_stage1_modules import (
    settle_history,
    stick_doc,
    stick_guid,
    write_module,
)

# The shared fixtures: Qt's application, the modules folder.
_app = test_stage1_modules._app
folder = test_stage1_modules.folder


def _delete(folder: Path) -> list[dict]:
    """Delete Device on pJoy Pro the way Home does; the entries it made."""
    write_module(folder, "pjoy_pro", stick_doc())
    settle_history()
    before = {e["id"] for e in history.entries()}
    result = json.loads(
        module_model.ModuleListModel().deleteDevice("pJoy Pro", stick_guid())
    )
    assert result["ok"], result
    assert not (folder / "pjoy_pro.json").exists()
    return [e for e in history.entries() if e["id"] not in before]


def test_home_delete_device_is_one_history_entry_and_restore_puts_it_back(
    folder: Path,
) -> None:
    new = _delete(folder)
    assert [e["title"] for e in new] == ["Deleted pJoy Pro"]
    out = history_model.restore(new[0]["id"], "before")
    assert out["ok"], out
    assert (folder / "pjoy_pro.json").is_file()


def test_inside_an_open_group_only_the_outer_entry_is_made(folder: Path) -> None:
    write_module(folder, "pjoy_pro", stick_doc())
    settle_history()
    before = {e["id"] for e in history.entries()}
    outer = "Removed pJoy Pro from the Device Library"
    token = history.begin_group(outer)
    assert token
    try:
        result = json.loads(
            module_model.ModuleListModel().deleteDevice("pJoy Pro", stick_guid())
        )
        assert result["ok"], result
    finally:
        history.end_group(token)
    new = [e for e in history.entries() if e["id"] not in before]
    assert [e["title"] for e in new] == [outer]
    out = history_model.restore(new[0]["id"], "before")
    assert out["ok"], out
    assert (folder / "pjoy_pro.json").is_file()
