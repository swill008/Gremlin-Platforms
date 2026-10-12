# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

# ruff: noqa: E501  (the stand-in editor is JavaScript, one function a line)

"""The Device Mapping Editor's command list for Favourites and Repeat (07 S136 S137,
D-07-RIGHTCLICK-ANSWERS): the Edit commands have ids, every id has a label,
a command run is remembered for Repeat (not Copy, Select All or Stop
Drawing), and Repeat runs it again only when it applies. Drives
qml/rig_commands.js itself in a JavaScript engine with a stand-in editor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6 import QtQml

_JS = (Path(__file__).parents[2] / "qml" / "rig_commands.js").read_text(
    encoding="utf-8"
)

# A stand-in for the editor: records the editor functions called.
_ED = r"""
var calls = []
var ed = {
    interactive: true, selectedId: "", selectedIds: [], copiedNodes: [],
    lastCommandId: "", rotateSnap: 90, drawTool: "", groupEditId: "",
    nodes: [{ id: "a", rot: 0 }, { id: "b", rot: 0 }, { id: "h", hidden: true }],
    nodeAt: function(id) { for (var i = 0; i < this.nodes.length; i++) if (this.nodes[i].id === id) return this.nodes[i]; return null },
    isSelected: function(id) { return this.selectedIds.indexOf(id) >= 0 || this.selectedId === id },
    isDraw: function(n) { return false }, isGroup: function(n) { return false },
    isRotatable: function(n) { return !!n }, canTurnTogether: function() { return false },
    isHidden: function(n) { return !!n.hidden }, isLocked: function(n) { return false },
    inEditPlane: function(n) { return true },
    setSelection: function(ids) { calls.push("setSelection:" + ids.join(",")); this.selectedIds = ids; this.selectedId = ids.length ? ids[ids.length - 1] : "" },
    setRotation: function(r) { calls.push("setRotation:" + r); this.nodeAt(this.selectedId).rot = r },
    copySelection: function() { calls.push("copySelection"); this.copiedNodes = [1] },
    pasteClipboard: function() { calls.push("pasteClipboard") },
    duplicateSelection: function() { calls.push("duplicateSelection") },
    deleteSelected: function() { calls.push("deleteSelected") },
    cutSelection: function() { calls.push("cutSelection") }
}
"""


@pytest.fixture(autouse=True)
def _app(qapp: object) -> None:  # a QJSEngine needs the application
    del qapp


def _run(body: str) -> Any:  # noqa: ANN401 (whatever the script returns)
    engine = QtQml.QJSEngine()
    out = cast(QtQml.QJSValue, engine.evaluate(_JS + "\n" + _ED + "\n" + body))
    assert not out.isError(), out.toString()
    return json.loads(
        cast(QtQml.QJSValue, engine.evaluate("JSON.stringify(result)")).toString()
    )


def test_edit_ids_have_labels_and_stay_out_of_the_menu_bar_list() -> None:
    r = _run("""
        var ids = ["edit.cut", "edit.copy", "edit.paste", "edit.duplicate", "edit.delete", "edit.selectAll"]
        var result = { info: ids.map(function(i) { return info(i) }),
                       withEd: info(ed, "rotatePlus"), unknown: info("nope"),
                       inList: list(ed).filter(function(c) { return c.id.indexOf("edit.") === 0 }).length }
    """)
    assert [(c["id"], c["text"], c["key"]) for c in r["info"]] == [
        ("edit.cut", "Cut", "Ctrl+X"),
        ("edit.copy", "Copy", "Ctrl+C"),
        ("edit.paste", "Paste", "Ctrl+V"),
        ("edit.duplicate", "Duplicate", "Ctrl+D"),
        ("edit.delete", "Delete", "Delete"),
        ("edit.selectAll", "Select All", "Ctrl+A"),
    ]
    assert r["withEd"] == {
        "id": "rotatePlus",
        "text": "Rotate +90°",
        "key": "Ctrl+Alt+Right",
    }
    assert r["unknown"] is None
    assert r["inList"] == 0


def test_applies_follows_the_selection() -> None:
    r = _run("""
        var before = ["edit.cut", "edit.copy", "edit.paste", "edit.delete", "edit.selectAll", "rotatePlus"]
            .map(function(i) { return applies(ed, i) })
        ed.selectedId = "a"; ed.selectedIds = ["a"]
        var after = ["edit.cut", "edit.copy", "edit.delete", "edit.duplicate", "rotatePlus"]
            .map(function(i) { return applies(ed, i) })
        var result = { before: before, after: after }
    """)
    assert r["before"] == [False, False, False, False, True, False]
    assert r["after"] == [True, True, True, True, True]


def test_edit_commands_call_the_editor_functions() -> None:
    r = _run("""
        ed.selectedId = "a"; ed.selectedIds = ["a"]
        run(ed, "edit.copy"); run(ed, "edit.paste"); run(ed, "edit.duplicate")
        run(ed, "edit.cut"); run(ed, "edit.delete"); run(ed, "edit.selectAll")
        var result = calls
    """)
    assert r == [
        "copySelection",
        "pasteClipboard",
        "duplicateSelection",
        "cutSelection",
        "deleteSelected",
        "setSelection:a,b",
    ]


def test_repeat_remembers_the_last_command_and_runs_it_again() -> None:
    r = _run("""
        ed.selectedId = "a"; ed.selectedIds = ["a"]
        var none = [repeatLabel(ed), canRepeat(ed)]
        run(ed, "rotatePlus")
        var label = repeatLabel(ed)
        run(ed, "edit.copy"); run(ed, "edit.selectAll")
        var kept = ed.lastCommandId
        ed.selectedId = "a"; ed.selectedIds = ["a"]
        var can = canRepeat(ed)
        repeat(ed)
        var rot = ed.nodeAt("a").rot
        ed.selectedId = ""; ed.selectedIds = []
        var canNone = canRepeat(ed)
        repeat(ed)
        noteRun(ed, "stopDrawing"); noteRun(ed, "edit.duplicate")
        var result = { none: none, label: label, kept: kept, can: can, rot: rot,
                       canNone: canNone, rotAfter: ed.nodeAt("a").rot, last: ed.lastCommandId }
    """)
    assert r["none"] == ["", False]
    assert r["label"] == 'Repeat "Rotate +90°"'
    assert r["kept"] == "rotatePlus"  # Copy and Select All are not repeated
    assert r["can"] is True
    assert r["rot"] == 180
    assert r["canNone"] is False  # nothing selected: does not apply
    assert r["rotAfter"] == 180
    assert r["last"] == "edit.duplicate"
