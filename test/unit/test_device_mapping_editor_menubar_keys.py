# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's menu bar keys against the spec, read from the source
files (no Qt): 07 S133 (every action command has a key, the keys named
there; list picks and destructive one-shot commands have none), S134 (the
Insert, Arrange, Leader and Format commands from qml/rig_commands.js and
their keys) and S135 (the menus, in order, and their keys).

- Every menu-bar item in qml/DialogDeviceMappingEditor.qml with a key in the
  spec shows that key as its hint; the no-key items show none.
- Every command in rig_commands.js list() that S134 gives a key has it.
- Every hint is a key that works: a Shortcut in the window has it, or the
  window makes one from the command list.

The running window (the hints as shown, the Keyboard Shortcuts window) is
test_device_mapping_editor_menubar.py.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_WINDOW = _ROOT / "qml" / "DialogDeviceMappingEditor.qml"
_COMMANDS = _ROOT / "qml" / "rig_commands.js"

# The spec's keys, menu by menu (07 S133, S134, S135). "→"/"←" are written
# Right/Left and "Enter" is Return, as Qt names them. Undo, Redo, Copy,
# Paste, Paste Picture, Duplicate, Delete, Group, Break Group, Lock / Unlock
# and Unlock All keep the keys they already had (S133 "besides the keys it
# already has").
SPEC_KEYS: dict[str, dict[str, str]] = {
    "File": {
        "Edit Mapping": "Ctrl+E",
        "Save": "Ctrl+S",
        "Cancel": "Ctrl+Shift+W",
        "History": "Ctrl+H",
        "Save Layout as Template…": "Ctrl+Shift+S",
        "Manage Templates…": "Ctrl+Shift+T",
        "Print & Export…": "Ctrl+P",
        "Close": "Ctrl+W",
    },
    "Edit": {
        "Undo": "Ctrl+Z",
        "Redo": "Ctrl+Y",
        "Cut": "Ctrl+X",
        "Copy": "Ctrl+C",
        "Paste": "Ctrl+V",
        "Paste Picture": "Ctrl+Shift+V",
        "Duplicate": "Ctrl+D",
        "Delete": "Delete",
        "Select All": "Ctrl+A",
        "Edit Background": "Ctrl+B",
        "Add Picture to Background…": "Ctrl+I",
        "Mirror Layout": "Ctrl+M",
        "Device Map Options…": "Ctrl+,",
    },
    "View": {
        "Zoom In": "Ctrl+=",
        "Zoom Out": "Ctrl+-",
        "Zoom to Fit Page": "Ctrl+1",
        "Zoom to Selection": "Ctrl+2",
        "Fit to Photo Frame": "Ctrl+3",
        "Reset View": "Ctrl+0",
        "Chips": "F6",
        "Layers": "F7",
        "Properties": "F4",
        "Search layers…": "Ctrl+F",
        "Rulers": "Ctrl+R",
        "Show Guides": "Ctrl+;",
        "Show Grid": "Ctrl+'",
        "Snap to Grid": "Ctrl+Shift+'",
        "Snap to Entities": "Ctrl+Shift+;",
    },
    "Help": {"Help": "F1", "Keyboard Shortcuts…": "Ctrl+K"},
}

# S133: destructive one-shot commands and list picks have no key.
SPEC_NO_KEY: dict[str, set[str]] = {
    "Edit": {"Reset Layout", "Clear Background"},
    "View": {"Clear Guides", "Clear Print Area", "Reset Panels"},
}

# S134: the commands from rig_commands.js with a key (by id).
SPEC_COMMAND_KEYS: dict[str, str] = {
    "bringToFront": "Ctrl+Shift+]",
    "bringForward": "Ctrl+]",
    "sendBackward": "Ctrl+[",
    "sendToBack": "Ctrl+Shift+[",
    "moveToBackground": "Ctrl+Shift+B",
    "moveToForeground": "Ctrl+Shift+B",
    "flipH": "Shift+H",
    "flipV": "Shift+V",
    "rotatePlus": "Ctrl+Alt+Right",
    "rotateMinus": "Ctrl+Alt+Left",
    "hide": "Ctrl+Shift+H",
    "rename": "F2",
    "copyFormat": "Ctrl+Alt+C",
    "pasteFormat": "Ctrl+Alt+V",
    "editText": "Return",
    "group": "Ctrl+G",
    "breakGroup": "Ctrl+Shift+G",
    "lock": "Ctrl+L",
    "unlockAll": "Ctrl+Shift+L",
    "stopDrawing": "Esc",
}

# S134: which menu each command is in.
SPEC_COMMAND_MENUS: dict[str, str] = {
    "importPicture": "Insert",
    "stopDrawing": "Insert",
    "bringToFront": "Arrange",
    "flipH": "Arrange",
    "resetShape": "Arrange",
    "resetCrop": "Arrange",
    "group": "Arrange",
    "breakGroup": "Arrange",
    "editGroup": "Arrange",
    "hide": "Arrange",
    "rename": "Arrange",
    "lock": "Arrange",
    "unlockAll": "Arrange",
    "moveToBackground": "Arrange",
    "moveToForeground": "Arrange",
    "addLeader": "Leader",
    "addCallout": "Leader",
    "addPointer": "Leader",
    "addStraightSpine": "Leader",
    "addCurvedSpine": "Leader",
    "ends.detachChip": "Leader",
    "ends.detachHot": "Leader",
    "ends.toChip": "Leader",
    "ends.toHot": "Leader",
    "ends.branch": "Leader",
    "ends.clearSpines": "Leader",
    "ends.deleteLeader": "Leader",
    "callout.detach": "Leader",
    "callout.remove": "Leader",
    "detachFromChips": "Leader",
    "copyFormat": "Format",
    "pasteFormat": "Format",
    "clearFormatting": "Format",
    "saveStyle": "Format",
    "editText": "Format",
    "table.rowAbove": "Format",
    "cell.free": "Format",
}

_TOKEN = re.compile(
    r'"(?:[^"\\]|\\.)*"(?!\s*\{)'  # a string on its own (skipped)
    r'|\b(text|hint|title)\s*:\s*"((?:[^"\\]|\\.)*)"'
    r"|([A-Za-z_][\w.]*)\s*\{"
    r"|\{|\}"
)


def _menu_bar() -> list[dict]:
    """The menu bar's items in order: {menu, path, text, hint}; path is the
    submenu titles below the top menu."""
    source = _WINDOW.read_text(encoding="utf-8")
    start = source.index("ThemedMenuBar {")
    stack: list[dict] = []
    items: list[dict] = []
    for m in _TOKEN.finditer(source, start):
        prop, value, name = m.group(1), m.group(2), m.group(3)
        token = m.group(0)
        if prop:
            if stack and stack[-1]["depth"] == len(stack):
                stack[-1][prop] = value.replace('\\"', '"')
            continue
        if name or token == "{":
            stack.append({"type": name or "", "depth": len(stack) + 1})
            continue
        if token == "}":
            frame = stack.pop()
            if frame["type"] == "ThemedMenuItem":
                menus = [f.get("title", "") for f in stack if f["type"] == "ThemedMenu"]
                items.append(
                    {
                        "menu": menus[0] if menus else "",
                        "path": menus[1:],
                        "text": frame.get("text", ""),
                        "hint": frame.get("hint", ""),
                    }
                )
            if not stack:
                break
    return items


def _menu_titles() -> list[str]:
    source = _WINDOW.read_text(encoding="utf-8")
    start = source.index("ThemedMenuBar {")
    stack: list[dict] = []
    titles: list[str] = []
    for m in _TOKEN.finditer(source, start):
        prop, value, name = m.group(1), m.group(2), m.group(3)
        token = m.group(0)
        if prop == "title" and len(stack) == 2 and stack[-1]["type"] == "ThemedMenu":
            titles.append(value)
        elif name or token == "{":
            stack.append({"type": name or ""})
        elif token == "}":
            stack.pop()
            if not stack:
                break
    return titles


_C = re.compile(
    r'_c\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*("(?:[^"\\]|\\.)*"[^,)]*)'
    r'(?:\s*,\s*"([^"]*)")?(?:\s*,\s*(true|false))?\s*\)'
)


def _commands() -> dict[str, dict]:
    """rig_commands.js list(): {id: {menu, sub, key, hintOnly}}."""
    source = _COMMANDS.read_text(encoding="utf-8")
    body = source[
        source.index("function list(ed)") : source.index("function _pictureShaped")
    ]
    out: dict[str, dict] = {}
    for m in _C.finditer(body):
        cid, menu, sub, _text, key, hint_only = m.groups()
        if cid == "-":
            continue
        out[cid] = {
            "menu": menu,
            "sub": sub,
            "key": key or "",
            "hintOnly": hint_only == "true",
        }
    return out


def _window_sequences() -> set[str]:
    """Every key a Shortcut in the window has (sequence or sequences)."""
    source = _WINDOW.read_text(encoding="utf-8")
    keys = set(re.findall(r'\bsequence:\s*"((?:[^"\\]|\\.)*)"', source))
    for group in re.findall(r"\bsequences:\s*\[([^\]]*)\]", source):
        keys.update(
            k.replace('\\"', '"') for k in re.findall(r'"((?:[^"\\]|\\.)*)"', group)
        )
    return keys


def test_the_menus_in_order() -> None:
    # S135: View right after Edit; Insert, Arrange, Leader, Format (S134).
    assert _menu_titles() == [
        "File",
        "Edit",
        "View",
        "Insert",
        "Arrange",
        "Leader",
        "Format",
        "Help",
    ]


def test_the_parsers_read_the_files() -> None:
    # A guard: the readers above found the menus and the commands.
    assert len(_menu_bar()) > 40
    assert len(_commands()) > 60


@pytest.mark.parametrize("menu", sorted(SPEC_KEYS))
def test_every_spec_key_is_the_items_hint(menu: str) -> None:
    hints = {i["text"]: i["hint"] for i in _menu_bar() if i["menu"] == menu}
    wrong = {
        text: hints.get(text, "<missing>")
        for text, key in SPEC_KEYS[menu].items()
        if hints.get(text) != key
    }
    assert wrong == {}


def test_destructive_and_pick_items_have_no_key() -> None:
    items = _menu_bar()
    keyed = [
        (i["menu"], i["text"], i["hint"])
        for i in items
        if i["text"] in SPEC_NO_KEY.get(i["menu"], set()) and i["hint"]
    ]
    assert keyed == []
    # The grid sizes and Labels Mode / Chip Text picks.
    picks = [
        (i["path"], i["text"], i["hint"])
        for i in items
        if i["path"]
        and i["path"][-1] in ("Size", "Chip Text", "Labels Mode")
        and i["hint"]
    ]
    assert picks == []


def test_every_command_s134_gives_a_key_has_it() -> None:
    commands = _commands()
    wrong = {
        cid: commands.get(cid, {}).get("key", "<missing>")
        for cid, key in SPEC_COMMAND_KEYS.items()
        if commands.get(cid, {}).get("key") != key
    }
    assert wrong == {}


def test_every_command_is_in_its_spec_menu() -> None:
    commands = _commands()
    wrong = {
        cid: commands.get(cid, {}).get("menu", "<missing>")
        for cid, menu in SPEC_COMMAND_MENUS.items()
        if commands.get(cid, {}).get("menu") != menu
    }
    assert wrong == {}
    # Editing a table is under Format › Table, not Insert (S134).
    tables = {
        c["menu"] + "/" + c["sub"]
        for cid, c in commands.items()
        if cid.startswith("table.")
    }
    assert tables == {"Format/Table"}


def test_every_hint_is_a_key_that_works() -> None:
    # A menu row's hint has a Shortcut in the window; a command's key has
    # one too: the window's own (hintOnly) or one made from the list.
    keys = _window_sequences()
    menu_missing = sorted(
        (i["menu"], i["text"], i["hint"])
        for i in _menu_bar()
        if i["hint"] and i["hint"] not in keys and "drag" not in i["hint"]
    )
    assert menu_missing == []
    command_missing = sorted(
        (cid, c["key"])
        for cid, c in _commands().items()
        if c["key"] and c["hintOnly"] and c["key"] not in keys
    )
    assert command_missing == []


def test_no_key_is_given_to_two_commands() -> None:
    # Except Move to Background / Foreground, one key for both (S134).
    seen: dict[str, list[str]] = {}
    for i in _menu_bar():
        if i["hint"] and "drag" not in i["hint"]:
            seen.setdefault(i["hint"], []).append(i["menu"] + " › " + i["text"])
    for cid, c in _commands().items():
        if c["key"]:
            seen.setdefault(c["key"], []).append(cid)
    shared = {k: v for k, v in seen.items() if len(v) > 1}
    assert shared == {"Ctrl+Shift+B": ["moveToBackground", "moveToForeground"]}
