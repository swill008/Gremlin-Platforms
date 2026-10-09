# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Library chapter of Help (10 S42, 01 S128, D-01-ONE-HELP):
qml/help/device_library.js covers the Device Library, names only menu items,
buttons and labels the window really has, uses the glossary's words, and the
rest of the book links to it instead of repeating it."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from PySide6 import QtCore

sys.path.insert(0, str(Path(__file__).resolve().parent))
import help_book  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "qml" / "help" / "device_library.js"
_SOURCE = _SCRIPT.read_text(encoding="utf-8")

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
    start = _SOURCE.index("function topics()")
    return _SOURCE[start:]


def _text(source: str) -> str:
    """Guide text without HTML tags or JS string glue."""
    joined = re.sub(r'"\s*\+\s*"', "", source).replace('\\"', '"')
    return html.unescape(re.sub(r"<[^>]+>", "", joined))


def _topics() -> list[dict]:
    return help_book.chapter_topics("device-library")


def _body(title: str) -> str:
    return str(help_book.find(title)["body"])


def test_the_guide_builds_with_every_part(qapp: QtCore.QCoreApplication) -> None:
    topics = _topics()
    assert len(topics) >= 25
    found = {t["section"] for t in topics}
    for section in (
        "Getting started",
        "Devices and saved setups",
        "Autosaves",
        "Changing sticks",
        "Undo and Redo",
        "Finding things",
        "Sharing",
        "Settings and tidying",
        "Common questions",
    ):
        assert section in found, section
    titles = {t["title"] for t in topics}
    # S42's list of what the chapter covers.
    for title in (
        "What the Device Library is",
        "Saved setups",
        "Built-in inputs",  # 10 S6
        "When autosaves are kept",
        "Copy a setup to another stick",
        "Swap two sticks",
        "Change which vJoy a stick sends to",
        "Undo and redo a change",  # 10 S53-S54
        "See a device's changes in History",  # 10 S56
        "Profiles that aren't open",
        "Search the Device Library",
        "Filter the list",
        "Import a Device Pack",
        "Export a saved setup",
        "Device Library Settings",
        "Tidy the Device Library",
        "Delete Device and Delete File",
        "Renamed and twin sticks",
        # The right-click menus and what came with them (S43-S50).
        "Right-click menus",
        "Restore a saved setup to its stick",
        "Keep an autosave",
        "Select several rows",
        "Delete or remove from the Device Library",
    ):
        assert title in titles, title
    assert all(len(t["body"]) > 80 for t in topics)
    assert all(t["id"].startswith("device-library-") for t in topics)


def test_topics_are_unique_in_the_chapter(qapp: QtCore.QCoreApplication) -> None:
    titles = [t["title"] for t in _topics()]
    assert len(set(titles)) == len(titles), "duplicate topic"


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


def test_the_right_click_menus_named_are_the_windows(
    qapp: QtCore.QCoreApplication,
) -> None:
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
        "Show in History",  # 10 S56
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
        "Show in History",  # 10 S56
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
    topic = _body("Right-click menus")
    for words in ("Menu", "Shift+F10", "selects it first", "left out", "red"):
        assert words in str(topic), words
    assert '"Menu", "Shift+F10"' in _WINDOW
    # S53: Undo and Redo beside every menu's title, named in the guide.
    assert 'label: "Undo"' in _WINDOW and 'label: "Redo"' in _WINDOW
    assert "beside its title" in str(topic)
    assert "<b>Undo</b>" in _guide_source() and "<b>Redo</b>" in _guide_source()
    # The delete question quoted is the window's.
    assert "from the Library?" in text and '" from the Library?"' in _WINDOW


def test_the_delete_topic_follows_the_states(
    qapp: QtCore.QCoreApplication,
) -> None:
    """S15 as built: Remove from Library (not connected, Delete Device first
    for a module file still here), Clear Setup and Delete Saved Setups
    (connected), Delete… on a saved setup; the details button's labels."""
    body = _body("Delete or remove from the Device Library")
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
        "Enter",
        "F1",
        "F2",
        "Ctrl+F",
        "View Full Help",  # the Help window's button (01 S128)
        "BUILT-IN INPUTS",
        "Keep the newest … autosaves per stick",
    }
    bold = set(re.findall(r"<b>([^<]+)</b>", _guide_source()))
    assert len(bold) > 40
    # A menu path (Edit › Delete…) counts when every step of it is shown;
    # the main window's Tools menu lives in main_commands.js / Main.qml.
    shown = _SHOWN + (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
    shown += (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    shown += (_ROOT / "qml" / "DialogHistory.qml").read_text(encoding="utf-8")
    missing = [
        word
        for word in sorted(bold)
        for part in word.split(" › ")
        if part not in concepts
        and f'"{part}' not in shown
        and f'{part}"' not in shown
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


def test_the_book_links_to_the_chapter_instead_of_repeating_it(
    qapp: QtCore.QCoreApplication,
) -> None:
    """D-01-ONE-HELP: the Device Library is written once, in its chapter."""
    others = [t for t in help_book.load()[1] if t["chapterId"] != "device-library"]
    assert not [t["title"] for t in others if t["title"] == "Device Library"]
    ids = {t["id"] for t in help_book.load()[1]}
    for topic in _topics():
        for target in topic["related"]:
            assert target in ids, (topic["id"], target)
        for target in re.findall(r'href="topic:([^"]+)"', topic["body"]):
            assert target in ids, (topic["id"], target)


def test_the_new_library_features_are_in_the_chapter(
    qapp: QtCore.QCoreApplication,
) -> None:
    """10 S6, S52-S56: built-in inputs, Undo/Redo with Last change, Show in
    History, the Delete key, Remove as one History entry."""
    undo = _body("Undo and redo a change")
    for words in ("Ctrl+Z", "Ctrl+Y", "Last change:", "Undone:", "Undo</b> link"):
        assert words in undo, words
    assert '"Last change: "' in _WINDOW and '"Undone: "' in _WINDOW
    assert "Show in History" in _body("See a device's changes in History")
    delete = _body("Delete or remove from the Device Library")
    assert "<b>Delete</b> key" in delete and "built-in input" in delete
    assert "one entry in <b>Tools › History</b>" in delete
    assert "from the Device Library" in delete
    assert "BUILT-IN INPUTS" in _body("Built-in inputs")
