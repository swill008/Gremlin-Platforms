# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library Guide content (10 S42, D-10-GUIDE): deviceLibraryTopics()
in qml/help_topics.js covers the Device Library, names only menu items,
buttons and labels the window really has, uses the glossary's words, and
the User Guide's Device Library topic points to it."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import cast

from PySide6 import QtCore, QtQml

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "qml" / "help_topics.js"
_SOURCE = _SCRIPT.read_text(encoding="utf-8")
_TOPIC = re.compile(r'topic\("([^"]+)", "([^"]+)",')

# What the Device Library shows: its window, its dialogs, the model's text,
# and the Home card and button that open it.
_SHOWN = "\n".join(
    (_ROOT / path).read_text(encoding="utf-8")
    for path in (
        "qml/WindowDeviceLibrary.qml",
        "qml/DialogLibraryCopy.qml",
        "qml/DialogLibrarySwap.qml",
        "qml/DialogLibraryOutput.qml",
        "qml/DialogLibrarySettings.qml",
        "qml/DialogLibraryTidy.qml",
        "gremlin/ui/device_library_model.py",
        "qml/StatusCard.qml",
        "qml/StatusPage.qml",
    )
)
_WINDOW = (_ROOT / "qml" / "WindowDeviceLibrary.qml").read_text(encoding="utf-8")


def _guide_source() -> str:
    start = _SOURCE.index("function deviceLibraryTopics()")
    end = _SOURCE.find("\nfunction ", start + 1)
    return _SOURCE[start:] if end < 0 else _SOURCE[start:end]


def _text(source: str) -> str:
    """Guide text without HTML tags or JS string glue."""
    joined = re.sub(r'"\s*\+\s*"', "", source).replace('\\"', '"')
    return html.unescape(re.sub(r"<[^>]+>", "", joined))


def _user_guide_library_topic() -> str:
    start = _SOURCE.index('topic("Tools", "Device Library"')
    end = _SOURCE.index("topic(", start + 1)
    return _SOURCE[start:end]


def _run(call: str) -> object:
    """The call's value, read while its engine is alive (a string from a
    dead engine reads as "undefined")."""
    source = "\n".join(
        "" if line.startswith(".") else line for line in _SOURCE.splitlines()
    )
    engine = QtQml.QJSEngine()
    result = cast(QtQml.QJSValue, engine.evaluate(source + "\n" + call, str(_SCRIPT)))
    assert not result.isError(), result.toString()
    return result.toVariant()


def test_the_guide_builds_with_every_part(qapp: QtCore.QCoreApplication) -> None:
    names = "deviceLibraryTopics().map(t => t.section + '|' + t.title)"
    sections = json.loads(str(_run(f"JSON.stringify({names})")))
    assert len(sections) >= 25
    found = {line.split("|")[0] for line in sections}
    for section in (
        "Getting started",
        "Devices and saved setups",
        "Autosaves",
        "Changing sticks",
        "Undo and Redo",
        "Finding things",
        "Sharing",
        "Settings and tidying",
        "Renamed and twin sticks",
        "Common questions",
    ):
        assert section in found, section
    titles = {line.split("|")[1] for line in sections}
    # S42's list of what the guide covers.
    for title in (
        "What the Device Library is",
        "Saved setups",
        "When autosaves are kept",
        "Copy to Another Stick",
        "Swap with Another Stick",
        "Change vJoy Output",
        "Undo and Redo",
        "Profiles that aren't open",
        "Search",
        "Filters and the list",
        "Import a Device Pack",
        "Export a saved setup",
        "Device Library Settings",
        "Tidy Library",
        "Delete Device and Delete File",
        "Renamed and twin sticks",
        # The right-click menus and what came with them (S43-S50).
        "Right-click menus",
        "Restore to This Stick",
        "Keep This Autosave",
        "Selecting several rows",
        "Delete and Remove from Library",
    ):
        assert title in titles, title
    every_body = _run("deviceLibraryTopics().every(t => t.body.length > 80)")
    assert every_body


def test_topics_are_unique_across_the_guides() -> None:
    topics = _TOPIC.findall(_SOURCE)
    assert len(set(topics)) == len(topics), "duplicate topic"


def test_the_menu_items_named_are_the_windows() -> None:
    text = _text(_guide_source())
    menu_items = (
        "Import Device Pack…",
        "Export Saved Setup…",
        "Open Library Folder",
        "Close",
        "Rename…",
        "Delete…",
        "Tidy Library…",
        "Save to Device Library…",
        "Copy to Another Stick…",
        "Swap with Another Stick…",
        "Change vJoy Output…",
        "Connected",
        "Not Connected",
        "Deleted",
        "Autosaves",
        "Expand All",
        "Collapse All",
        "Search…",
        "Device Library Settings…",
    )
    for item in menu_items:
        assert item in text, item
        assert f'text: "{item}"' in _WINDOW or f'"{item}"]' in _WINDOW, item


def _row_menu_items() -> set[str]:
    """The labels of the window's right-click menus (rowMenuModel)."""
    start = _WINDOW.index("function rowMenuModel()")
    end = _WINDOW.index("\n    }\n", start)
    body = _WINDOW[start:end]
    items = set(re.findall(r'MenuModel\.action\("([^"]+)"', body))
    items.update(re.findall(r'"(Collapse|Expand)"', body))
    return items


def test_the_right_click_menus_named_are_the_windows() -> None:
    """S43-S47: the guide names every item of the three right-click menus,
    with the window's exact labels, and the keys that open them."""
    text = _text(_guide_source())
    built = _row_menu_items()
    device = (
        "Copy to Another Stick…",
        "Swap with Another Stick…",
        "Change vJoy Output…",
        "Save to Device Library…",
        "Export Current Setup…",
        "Rename…",
        "Edit Description",
        "Open Module Setup…",
        "Open Button Map",
        "Show on Home",
        "Expand",
        "Collapse",
        "Remove from Library…",
        "Clear Setup…",
        "Delete Saved Setups…",
    )
    setup = (
        "Copy to Another Stick…",
        "Restore to This Stick…",
        "Export…",
        "Rename…",
        "Edit Description",
        "Keep This Autosave",
        "Delete…",
    )
    builtin = ("Restore…",)  # Built-in inputs (10 S6, D-10-BUILTIN-SECTION)
    space = (
        "Import Device Pack…",
        "Expand All",
        "Collapse All",
        "Device Library Settings…",
    )
    for item in (*device, *setup, *builtin, *space):
        assert item in built, item
        assert f"<b>{item}</b>" in _guide_source(), item
    known = {*device, *setup, *builtin, *space}
    assert built <= known, built - known
    topic = _run(
        "deviceLibraryTopics().filter(t => t.title === 'Right-click menus')[0].body"
    )
    for words in ("Menu", "Shift+F10", "selects it first", "left out", "red"):
        assert words in str(topic), words
    assert '"Menu", "Shift+F10"' in _WINDOW
    # The delete question quoted is the window's.
    assert "from the Library?" in text and '" from the Library?"' in _WINDOW


def test_the_delete_topic_follows_the_states() -> None:
    """S15 as built: Remove from Library (not connected, Delete Device first
    for a module file still here), Clear Setup and Delete Saved Setups
    (connected), Delete… on a saved setup; the details button's labels."""
    body = str(
        _run(
            "deviceLibraryTopics().filter(t => t.title === "
            "'Delete and Remove from Library')[0].body"
        )
    )
    for words in (
        "Remove from Library…",
        "Clear Setup…",
        "Delete Saved Setups…",
        "Delete…",
        "Delete Device",
        "autosave is kept",
        "stays plugged in with no setup",
        "keeps its settings",
        "Tools › History can put it back",  # D-10-IN-HISTORY
        "Restore to This Stick…",
    ):
        assert words in body, words
    assert '"Delete Saved Setups…" : "Remove from Library…"' in _WINDOW
    for gone in (
        "deleted with Delete Device on Home. The stick itself",
        "can't be undone",
    ):
        assert gone not in body


def test_every_bold_label_is_on_screen() -> None:
    """Every bold word in the guide is a menu item, button or label the
    Device Library shows, or one of the few words the guide explains."""
    concepts = {
        "Device Library",
        "Devices",
        "Saved setups",
        "autosaves",
        "Filters",
        "search box",
        "list",
        "details",
        "status bar",
        "description",
        "open profile",
        "File",
        "Edit",
        "Device",
        "View",
        "Settings",
        "Help",
        "Not connected",
        "Copy",
        "Swap",
        "Change vJoy Output",
        "Delete Device",
        "Delete File",
        "Device Pack",
        "Undo",
        "Esc",
        "F1",
        "F2",
        "Ctrl+F",
        "Device Library Guide",  # the Help menu (agent GW's wiring)
        "Keep the newest … autosaves per stick",
    }
    bold = set(re.findall(r"<b>([^<]+)</b>", _guide_source()))
    assert len(bold) > 40
    missing = [
        word
        for word in sorted(bold)
        if word not in concepts
        and f'"{word}' not in _SHOWN
        and f'{word}"' not in _SHOWN
    ]
    assert missing == []


def test_the_words_match_the_program() -> None:
    text = _text(_guide_source())
    # Autosave names, as the program writes them.
    code = "\n".join(
        (_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "gremlin/library_copy.py",
            "gremlin/library_swap.py",
            "gremlin/ui/hardware_profile.py",
        )
    )
    for name in (
        "Autosave: stick deleted",
        "Autosave: module file deleted",
        "Autosave: before Undo",
    ):
        assert name in text and name in code, name
    for start in (
        "Autosave: before Restore of ",
        "Autosave: before Copy from ",
        "Autosave: before Swap with ",
        "Autosave: before Change vJoy Output (",
        "Autosave: before Device Pack ",
    ):
        assert start in text and start in code, start
    # Window and dialog text quoted in the guide.
    for words in (
        "Setup (damaged file, kept as is)",
        "Was an autosave, now yours",
        "Kept automatically",
        "Saved by you",
        "Add a description",
        "(open)",
        "Some settings have nowhere to go",
        "Check these",
        "Library: ",
        "(swap them)",
        "current settings",
        "Remove Old Warthog stick and its 4 saved setups from the Library?",
    ):
        assert words in text, words
        if words.startswith("Remove "):
            assert '"Remove " + details.name' in _WINDOW
            assert '" from the Library?"' in _WINDOW
        else:
            assert words in _SHOWN, words
    # Keep This Autosave's History line, as the library writes it.
    library = (_ROOT / "gremlin" / "device_library.py").read_text(encoding="utf-8")
    assert "Kept as your own" in text and '"Kept as your own"' in library


def test_glossary_words_and_nothing_removed() -> None:
    text = _text(_guide_source())
    for words in (
        "Device Library",
        "saved setup",
        "autosave",
        "Copy to Another Stick…",
        "Swap with Another Stick…",
        "Change vJoy Output…",
        "Tidy Library…",
        "Copy Setup to Another Stick…",
    ):
        assert words in text, words
    for gone in (
        "deleted devices folder",
        "Swap Devices",
        "Swap Device…",
        "Shared",
        "Save a copy",
        # "Edit Description" (no dots) is a right-click item now (S44, S45).
        "Edit Description…",
        "backup",
    ):
        assert gone not in text, gone
    # No internal names: files, settings keys, spec references.
    for internal in ("library.json", ".py", "device-library-folder", "D-10", "dill"):
        assert internal not in text, internal
    assert not re.search(r"\bS\d+\b", text)


def test_the_user_guide_points_to_the_guide() -> None:
    topic = _user_guide_library_topic()
    assert "Device Library Guide" in topic
    assert "F1" in topic
    # The User Guide keeps its one Device Library topic (S42).
    main = _SOURCE[: _SOURCE.index("function buttonMapTopics()")]
    titles = [title for _s, title in _TOPIC.findall(main)]
    assert titles.count("Device Library") == 1


def test_the_guide_is_outside_the_button_map_guide() -> None:
    """test_help_guide reads the Button Map Guide as the text from
    buttonMapTopics() to topic(): the Device Library's must not land there."""
    start = _SOURCE.index("function buttonMapTopics()")
    end = _SOURCE.index("function topic(section, title, body)")
    assert "deviceLibraryTopics" not in _SOURCE[start:end]
