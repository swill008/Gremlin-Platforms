# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library, agent DD: the ways in (10 S2; 03 S88; 09 S31) and Swap
Devices gone (04, replaced by the Device Library; D-10-SWAP); the Delete
Device steps say an autosave is kept (03 S90) and the Help follows."""

from __future__ import annotations

import sys

sys.path.append(".")

import json
from pathlib import Path
from typing import cast

import pytest
from PySide6 import QtCore, QtQml

_ROOT = Path(__file__).resolve().parents[2]
_LIBRARY_ITEMS = (
    "Copy Setup to Another Stick…",
    "Swap with Another Stick…",
    "Change vJoy Output…",
)


def _text(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def _function_source(text: str, name: str) -> str:
    start = text.index(f"function {name}(")
    depth = 0
    for index in range(text.index("{", start), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"{name} has no end")


def _card_menu(slug: str, name: str, direction: str, bus: str, tab: str) -> dict:
    """StatusCard.qml's own menuModel() on a stand-in MenuModel: each item's
    text, and what its action asked the card for when run."""
    script = (
        """
        var opened = []
        var MenuModel = {
            action: function(text, run) { return {text: text, run: run} },
            section: function(id, title, items) { return items },
            menu: function(kind, title, quick, sections) {
                var out = quick.filter(function(i) { return i !== null })
                sections.forEach(function(items) {
                    items.forEach(function(i) { if (i !== null) out.push(i) })
                })
                return out
            }
        }
        """
        + f"var slug = {json.dumps(slug)}; var cardName = {json.dumps(name)};"
        + f" var rawName = cardName; var direction = {json.dumps(direction)};"
        + f" var bus = {json.dumps(bus)}; var tab = {json.dumps(tab)};"
        + " var stacked = false;"
        + " var _card = { damaged: '', canStackSelected: false,"
        + " openDeviceLibrary: function(action) { opened.push(action) } };"
        + _function_source(_text("qml/StatusCard.qml"), "menuModel")
        + """
        function run() {
            var out = {}
            menuModel().forEach(function(item) {
                opened = []
                if (/Another Stick|vJoy Output/.test(item.text))
                    item.run()
                out[item.text] = opened.slice()
            })
            return JSON.stringify(out)
        }
        """
    )
    engine = QtQml.QJSEngine()
    loaded = cast(QtQml.QJSValue, engine.evaluate(script))
    assert not loaded.isError(), loaded.toString()
    result = cast(QtQml.QJSValue, engine.evaluate("run()"))
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


def test_a_stick_card_opens_the_device_library_three_ways(
    qapp: QtCore.QCoreApplication,
) -> None:
    menu = _card_menu("pjoy_pro", "pJoy Pro", "source", "DirectInput", "physical")
    assert "Swap Device…" not in menu
    assert menu["Copy Setup to Another Stick…"] == ["copy"]
    assert menu["Swap with Another Stick…"] == ["swap"]
    assert menu["Change vJoy Output…"] == ["output"]


@pytest.mark.parametrize(
    "card",
    [
        ("vjoy_1", "vJoy 1", "dest", "DirectInput", "physical"),
        ("xbox", "Xbox 360 Controller", "dest", "XInput", "xbox"),
        ("keyboard", "Keyboard", "source", "HID", "keyboard"),
        ("osc", "OSC", "source", "HID", "osc"),
        ("logical", "Logical Device", "source", "Logical", "logical"),
    ],
    ids=["vjoy", "xbox", "keyboard", "osc", "logical"],
)
def test_cards_that_are_not_sticks_leave_them_out(
    qapp: QtCore.QCoreApplication, card: tuple
) -> None:
    # 03 S88, 09 S31.
    menu = _card_menu(*card)
    assert not set(_LIBRARY_ITEMS) & set(menu), menu
    assert "Swap Device…" not in menu


def test_the_card_routes_to_main_s_open_device_library() -> None:
    card = _text("qml/StatusCard.qml")
    page = _text("qml/StatusPage.qml")
    main = _text("qml/Main.qml")
    assert "signal openDeviceLibrary(string action)" in card
    assert "assignHardware" not in card and "assignHardware" not in page
    assert "signal openDeviceLibrary(var card, string action)" in page
    assert "_page.openDeviceLibrary(_page.pack(card), action)" in page
    # Main hands it to the Device Library's opener (LU's script).
    assert 'import "device_library_open.js" as DeviceLibraryOpen' in main
    assert "onOpenDeviceLibrary: function(card, action)" in main
    assert "DeviceLibraryOpen.openDeviceLibrary(" in main


def test_the_toolbar_has_the_device_library_button_not_home() -> None:
    # 01 S58, S58a; 10 S2: the toolbar button (moved from Home 2026-10-09).
    page = _text("qml/StatusPage.qml")
    main = _text("qml/Main.qml")
    assert "homeDeviceLibraryButton" not in page
    assert 'text: "Device Library…"' not in page
    block = main[main.index("id: _deviceLibraryButton"):]
    block = block[: block.index("}") + 1]
    assert 'caption: "Device Library"' in block
    assert r'text: "\uF1A5"' in block  # Bootstrap Icons bookshelf
    assert 'qsTr("Every device and its saved setups")' in block
    assert '_root.openDeviceLibrary("", "", "")' in block


def test_tools_device_setup_has_device_library_not_swap_devices() -> None:
    commands = _text("qml/main_commands.js")
    main = _text("qml/Main.qml")
    assert "tools.swapDevices" not in commands and "tools.swapDevices" not in main
    entry = commands[commands.index('id: "tools.deviceLibrary"'):]
    entry = entry[: entry.index("} },") + 4]
    assert 'text: "Device Library…"' in entry
    assert 'group: "Tools › Device Setup"' in entry
    assert 'openDeviceLibrary("", "", "")' in entry
    setup = main[main.index('title: qsTr("Device Setup")'):]
    setup = setup[: setup.index("ThemedMenu {")]
    assert 'ThemedMenuItem { command: "tools.deviceLibrary" }' in setup


def test_swap_devices_window_and_slot_are_gone() -> None:
    from gremlin.ui.tools import Tools

    assert not (_ROOT / "qml" / "DialogSwapDevices.qml").exists()
    assert not hasattr(Tools, "swapDevices")
    for rel in ("qml/Main.qml", "qml/main_commands.js", "qml/StatusCard.qml"):
        assert "DialogSwapDevices" not in _text(rel), rel


def test_delete_device_steps_say_an_autosave_is_kept() -> None:
    page = _text("qml/StatusPage.qml")
    # 03 S90: no "Save a copy" question.
    assert "Save a copy" not in page and "_saveCopyBox" not in page
    assert "_deleteSaveCopy" not in page
    explain = _function_source(page, "explainBody")
    assert "autosave of this device is kept in the Device Library" in explain
    assert "model.deleteDevice(raw, guid)" in page
    assert "deleted devices" not in page


def test_help_follows_the_device_library(qapp: QtCore.QCoreApplication) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import help_book

    guide = help_book.book_html()
    titles = [t["title"] for t in help_book.load()[1]]
    assert "Swap Devices" not in titles
    assert "Open the Device Library" in titles
    assert "Swap Device…" not in guide and "<b>Swap Devices</b>" not in guide
    assert "deleted devices folder" not in guide
    assert "Save a copy" not in guide
    assert "history, deleted devices and plugins" not in guide
    for words in (*_LIBRARY_ITEMS, "Autosave: stick deleted",
                  "Autosave: module file deleted",
                  "<b>Tools › Device Setup › Device Library…</b>"):
        assert words in guide, words
