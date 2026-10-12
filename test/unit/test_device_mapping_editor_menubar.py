# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's menu bar in the running window (07 S98-S100, S133-S135),
off-screen in its own process and user folder (device_mapping_editor_menubar_smoke.py).

- The menus in order: File, Edit, View, Insert, Arrange, Leader, Format,
  Help; Edit › Background › holds Edit Background, Add Picture to
  Background…, Clear Background.
- Every row the spec gives a key shows it; the commands from
  rig_commands.js are in their menus with their keys, greyed with no
  selection and enabled with a matching one; Crop and ID Column tick when on.
- One run per kind is one Undo step: Bring to Front, Flip Horizontally, Add
  Leader, Paste Format; Copy Format is none; Cut is Copy then Delete in one.
- Select All selects the edited plane's items (Ctrl+A too); Zoom In / Out
  (and their keys) change the zoom.
- Device Map Options opens from Edit and with Ctrl+,.
- Keyboard Shortcuts opens with Ctrl+K, lists the keys by menu plus Keys
  and Mouse, filters by its search box and runs nothing; unpinned, it closes
  when the Device Mapping Editor is activated; pinned, it stays; the pin is kept.
  Reset Panels keeps the pin and Show Print Area.
- Keys never run while a name is being typed (G38).
- No "Created graphical object was not placed in the graphics scene"
  warning (the command rows are made inside the menu's list).

The source-level key table is test_device_mapping_editor_menubar_keys.py.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

from test.unit.test_device_mapping_editor_menubar_keys import (
    SPEC_COMMAND_KEYS,
    SPEC_KEYS,
)

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_mapping_editor_menubar_smoke.py"


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("menubar")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        # Qt's warnings on the error stream, where this reads them.
        QT_FORCE_STDERR_LOGGING="1",
        QT_QPA_FONTDIR=os.environ.get(
            "QT_QPA_FONTDIR",
            os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
        ),
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(smoke_report.explain(done))
    out = json.loads(lines[-1][len("RESULT ") :])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    out["_stderr"] = (done.stderr or "") + (done.stdout or "")
    return out


def _part(seen: dict, key: str) -> object:
    """One step's result; a step that raised fails here with its traceback."""
    value = seen[key]
    if isinstance(value, dict) and "error" in value:
        raise RuntimeError(value.get("traceback") or value["error"])
    return value


def _rows(seen: dict, key: str = "rows") -> list:
    rows = _part(seen, key)
    assert isinstance(rows, list)
    return rows


def test_the_menus_in_order(seen: dict) -> None:
    # S135.
    assert _part(seen, "titles") == [
        "File",
        "Edit",
        "View",
        "Insert",
        "Arrange",
        "Leader",
        "Format",
        "Help",
    ]


def test_edit_background_holds_its_items(seen: dict) -> None:
    # S135: Background › moved into Edit.
    assert _part(seen, "background") == [
        "Edit Background",
        "Add Picture to Background…",
        "Clear Background",
    ]


def test_every_spec_key_shows_beside_its_item(seen: dict) -> None:
    # S133, S135: the hints in the running window, outside Edit.
    hints = {(r["menu"], r["text"]): r["hint"] for r in _rows(seen, "live-rows")}
    wrong = {
        f"{menu} › {text}": hints.get((menu, text), "<missing>")
        for menu, keys in SPEC_KEYS.items()
        for text, key in keys.items()
        if hints.get((menu, text)) != key
    }
    assert wrong == {}


def test_every_command_is_in_its_menu_with_its_key(seen: dict) -> None:
    # S134: each command of RigCommands.list() is a row of its menu (in
    # its submenu), its key the row's hint.
    commands = _part(seen, "commands")
    assert isinstance(commands, list) and len(commands) > 60
    rows = {
        (r["menu"], tuple(r["path"]), r["text"]): r["hint"]
        for r in _rows(seen, "live-rows")
    }
    missing = [
        c["id"]
        for c in commands
        if (c["menu"], (c["sub"],) if c["sub"] else (), c["text"]) not in rows
    ]
    assert missing == []
    wrong = {
        c["id"]: rows[(c["menu"], (c["sub"],) if c["sub"] else (), c["text"])]
        for c in commands
        if rows[(c["menu"], (c["sub"],) if c["sub"] else (), c["text"])] != c["key"]
    }
    assert wrong == {}
    keyed = {c["id"]: c["key"] for c in commands if c["id"] in SPEC_COMMAND_KEYS}
    assert keyed == SPEC_COMMAND_KEYS


def test_commands_are_greyed_until_the_selection_fits(seen: dict) -> None:
    # S134: greyed out, not hidden.
    states = _part(seen, "enabled")
    assert isinstance(states, dict)
    assert states["none"] == {
        "bringToFront": False,
        "hide": False,
        "rename": False,
        "addLeader": False,
        "flipH": False,
        "copyFormat": False,
        "editText": False,
        "importPicture": True,
    }
    chip = states["chip"]
    assert (
        chip["bringToFront"] and chip["hide"] and chip["rename"] and chip["addLeader"]
    )
    assert not chip["copyFormat"] and not chip["editText"]
    assert states["rect"]["flipH"] is True
    assert states["rect"]["addLeader"] is False
    assert states["text"]["copyFormat"] is True
    assert states["text"]["editText"] is True


@pytest.mark.parametrize(
    "name", ["bring-to-front", "flip-h", "add-leader", "paste-format"]
)
def test_one_run_is_one_undo_step(seen: dict, name: str) -> None:
    # S134: the menu row runs the command; one Undo takes it back.
    assert _part(seen, name) | {"copy-steps": 0} == {
        "changed": True,
        "steps": 1,
        "undone": True,
        "copy-steps": 0,
    }


def test_cut_is_copy_then_delete_in_one_step(seen: dict) -> None:
    # S135.
    assert _part(seen, "cut") == {
        "gone": True,
        "copied": ["b3"],
        "steps": 1,
        "undone": True,
    }


def test_select_all_selects_the_edited_planes_items(seen: dict) -> None:
    # S133.
    part = _part(seen, "select-all")
    assert isinstance(part, dict)
    assert part["menu"] == part["want"] and part["has-chips"] is True
    assert part["key"] == part["want"]


def test_zoom_in_and_out(seen: dict) -> None:
    # S133: the rows and Ctrl+= / Ctrl+-.
    assert _part(seen, "zoom") == {
        "in": True,
        "out": True,
        "back": True,
        "key-in": True,
        "key-out": True,
    }


def test_options_opens_from_edit_and_its_key(seen: dict) -> None:
    # S98.
    part = _part(seen, "options")
    assert isinstance(part, dict)
    assert [part["menu"], part["key"]] == [True, True]


def test_keys_in_the_options_window_run_nothing(seen: dict) -> None:
    part = _part(seen, "options")
    assert isinstance(part, dict)
    assert part["keys-in-it-run-nothing"] is True


def test_crop_and_id_column_tick_when_on(seen: dict) -> None:
    # S134 (lead 2026-10-11): the tick follows the state as the menu opens.
    part = _part(seen, "ticks")
    assert isinstance(part, dict)
    assert part["crop-checkable"] is True
    assert part["crop"][:3] == [False, True, False]
    assert part["table-kind"] is True
    assert part["id-col"] == [False, True, False]


def test_keys_never_run_while_typing_a_name(seen: dict) -> None:
    # S133 (G38): Ctrl+B, Ctrl+L, Ctrl+G, Ctrl+D, Ctrl+Z and Delete go to
    # the rename box, not to their commands.
    part = _part(seen, "typing")
    assert isinstance(part, dict)
    assert part["renaming"] is True
    assert part["ran-nothing"] is True
    assert part["still-renaming"] == "b1"
    assert str(part["typed"]).endswith("Qz")


def test_reset_panels_keeps_print_area_and_the_shortcuts_pin(seen: dict) -> None:
    # S99.
    assert _part(seen, "reset-panels") == {
        "print-area": [True, True],
        "pin": [True, True],
    }


def test_keyboard_shortcuts_lists_keys_by_menu(seen: dict) -> None:
    # S100: Ctrl+K; the menus' keys under their menu, then Mouse and Keys.
    part = _part(seen, "shortcuts")
    assert isinstance(part, dict)
    assert part["ctrl-k"] is True
    rows = part["described"]
    headings = [r[2:] for r in rows if r.startswith("# ")]
    assert headings == [
        "File",
        "Edit",
        "View",
        "Insert",
        "Arrange",
        "Format",
        "Help",
        "Mouse",
        "Keys",
    ]
    for wanted in (
        "File: Edit Mapping (Ctrl+E)",
        "Edit: Select All (Ctrl+A)",
        "Edit: Device Map Options… (Ctrl+,)",
        "View: Zoom In (Ctrl+=)",
        "Arrange: Bring to Front (Ctrl+Shift+])",
        "Format: Copy Format (Ctrl+Alt+C)",
        "Help: Keyboard Shortcuts… (Ctrl+K)",
        "Keys: Finish a path (Enter)",
        "Mouse: Zoom (Wheel)",
        # The Photoshop-match keys (07 S142, S143, S141, S145, S147).
        "Keys: Nudge 10 px (Shift+Arrows)",
        "Mouse: Copy (Alt+drag an item)",
        "Mouse: Skip snapping (Ctrl while dragging)",
        "Mouse: Resize from the center (Alt+drag a handle)",
        "Mouse: Skew (Ctrl+Shift+drag a side handle)",
    ):
        assert wanted in rows
    # No row without a key, and the destructive ones have none.
    assert not [r for r in rows if r.endswith("()")]
    assert not [r for r in rows if "Reset Layout" in r or "Clear Background" in r]
    assert all(
        "Zoom" in r or "zoom" in r.lower() or r.startswith("# ") for r in part["search"]
    )
    assert "View: Zoom In (Ctrl+=)" in part["search"]


def test_keyboard_shortcuts_lists_every_menu_outside_edit(seen: dict) -> None:
    # S100: the same groups while the map is live (not editing).
    rows = _part(seen, "shortcuts-live")
    assert isinstance(rows, list)
    headings = [r[2:] for r in rows if r.startswith("# ")]
    assert headings == [
        "File",
        "Edit",
        "View",
        "Insert",
        "Arrange",
        "Format",
        "Help",
        "Mouse",
        "Keys",
    ]


def test_keyboard_shortcuts_runs_nothing(seen: dict) -> None:
    # S100: a reference only: clicks and keys in it change nothing.
    part = _part(seen, "shortcuts")
    assert isinstance(part, dict)
    assert part["active"] is True
    assert part["clicks-ran-nothing"] is True
    assert part["keys-ran-nothing"] == {
        "Return": True,
        "Delete": True,
        "Ctrl+D": True,
        "Ctrl+L": True,
    }
    assert part["still-editing"] is True


def test_keyboard_shortcuts_pin(seen: dict) -> None:
    # S100: unpinned it closes when you go back to the Device Mapping Editor; pinned it
    # stays; the pin is kept for next time.
    part = _part(seen, "shortcuts")
    assert isinstance(part, dict)
    assert part["visible-before-away"] is True
    assert part["activated-map"] is True
    assert part["unpinned-closes"] is True
    assert part["pinned-stays"] is True
    assert part["pin-kept"] is True
    assert part["unpin-kept"] is False


def test_no_menu_row_warning(seen: dict) -> None:
    # The command rows are made inside the menu's list, so Qt never warns.
    assert "not placed in the graphics scene" not in seen["_stderr"]
