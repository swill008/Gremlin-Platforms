# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Help book (01 S128, S129) matches the program and the house style
(claude/help-style.md). Every check runs over every chapter, as the program
loads them (qml/help/index.js)."""

from __future__ import annotations

import re

import pytest
from PySide6 import QtCore

from test.unit import help_book
from test.unit.help_book import ROOT as _ROOT

_CHAPTERS = [
    "getting-started", "home-devices", "configuration-actions",
    "logical-device", "osc", "modes", "button-map", "device-library", "tools",
    "options-profile",
]
# Every window whose menus the book names.
_MENU_SOURCES = [
    "qml/Main.qml", "qml/main_commands.js", "qml/DialogJoystickButtonMap.qml",
    "qml/WindowDeviceLibrary.qml", "qml/rig_menu.js",
]
_MENUS = r"File|Edit|View|Tools|Debug|Help|Device|Photo|Insert|Format|Arrange"
_LINK = re.compile(r'<a\s+href="topic:([^"]*)"')


@pytest.fixture(autouse=True)
def _book(qapp: QtCore.QCoreApplication) -> None:
    help_book.load()


def _topics() -> list[dict]:
    return help_book.load()[1]


def _menu_labels() -> set[str]:
    labels: set[str] = set()
    for rel in _MENU_SOURCES:
        source = (_ROOT / rel).read_text(encoding="utf-8")
        labels |= set(re.findall(r'(?:text|title): qsTr\("([^"]+)"\)', source))
        labels |= set(re.findall(r'(?:text|title): "([^"]+)"', source))
        labels |= set(re.findall(r'MenuModel\.action\("([^"]+)"', source))
        # The Button Map's right-click menu (rig_menu.js).
        labels |= set(re.findall(r'_act\("([^"]+)"', source))
        labels |= set(re.findall(r'_sect\("[^"]+", "([^"]+)"', source))
    return {label.rstrip("…").strip() for label in labels}


def test_the_book_has_every_chapter_in_order() -> None:
    chapters, topics = help_book.load()
    assert [c["id"] for c in chapters] == _CHAPTERS
    assert len(topics) >= 50
    for topic in topics:
        for key in ("id", "section", "title", "body"):
            assert topic.get(key), f"{topic.get('id')}: no {key}"


def test_each_chapter_ends_with_common_questions() -> None:
    missing = [
        chapter for chapter in _CHAPTERS
        if not help_book.chapter_topics(chapter)
        or help_book.chapter_topics(chapter)[-1]["section"] != "Common questions"
    ]
    assert missing == []


def test_topic_ids_and_titles_are_unique() -> None:
    """Each subject is written once (S128)."""
    ids = [t["id"] for t in _topics()]
    assert sorted({i for i in ids if ids.count(i) > 1}) == []
    titles = [
        t["title"].casefold() for t in _topics()
        if t["section"] != "Common questions"
    ]
    assert sorted({t for t in titles if titles.count(t) > 1}) == []


def test_every_link_and_related_topic_resolves() -> None:
    ids = {t["id"] for t in _topics()}
    broken = []
    for topic in _topics():
        for target in _LINK.findall(topic["body"]) + topic["related"]:
            if target not in ids:
                broken.append(f"{topic['id']} → {target}")
    assert broken == []


_FORBIDDEN = re.compile(
    r"\b(simply|just|easily|basically|please|note that|the user|we|our|bug|"
    r"to-do|todo)\b|\b[SQ]\d+\b|\bD-\d\d-",
    re.I,
)


def test_no_words_the_house_style_rules_out() -> None:
    found = []
    for topic in _topics():
        common = topic["section"] == "Common questions"
        title = topic["title"]
        for where, text in (("title", title), ("body", help_book.text(topic["body"]))):
            for match in _FORBIDDEN.finditer(text):
                found.append(f"{topic['id']} {where}: {match.group(0)!r}")
            # "I" only in a Common questions title (the reader's own words).
            if not (common and where == "title"):
                if re.search(r"\bI\b(?![/-])", text):
                    found.append(f"{topic['id']} {where}: 'I'")
            if "!" in text.replace("!=", ""):
                found.append(f"{topic['id']} {where}: '!'")
    assert found == []


def test_menu_paths_in_the_guide_exist() -> None:
    labels = _menu_labels()
    text = help_book.book_text()
    missing = []
    paths = list(re.finditer(rf"\b({_MENUS}) [→›] ", text))
    assert len(paths) >= 20  # the check really ran
    for match in paths:
        rest = text[match.end():]
        # Each step after the menu must start with a real menu label.
        while True:
            known = [label for label in labels if label and rest.startswith(label)]
            if not known:
                missing.append(f"{match.group(1)} › {rest[:30]}")
                break
            step = max(known, key=len)
            rest = rest[len(step):]
            if not re.match(r" [→›] ", rest):
                break
            rest = rest[3:]
    assert sorted(set(missing)) == []


def test_removed_or_wrong_things_are_not_in_the_help() -> None:
    text = help_book.book_text()
    for phrase in (
        "Device Viewer",
        "Help → Logical Device",
        "Help › Logical Device",
        "Claim all",  # Xbox has no claims
        "Claimed box",
        "tapped once",  # Map to Keyboard has no tap option
        "Button Map Guide",  # one Help now (S128)
        "Device Library Guide",
        "User Guide",
    ):
        assert phrase not in text, phrase
    for phrase in (
        "50%–400%", "World page", "not in yet", "Empty photo — Draw only",
    ):
        assert phrase not in text, phrase


def _known_words() -> str:
    """Every string the program can show, to check bold labels against."""
    parts = []
    for folder, pattern in (("qml", "*.qml"), ("qml", "*.js"),
                            ("gremlin", "*.py"), ("action_plugins", "*.py"),
                            ("action_plugins", "*.qml"), ("action_plugins", "*.js")):
        for path in (_ROOT / folder).rglob(pattern):
            if "help" in path.parts or path.name == "help_topics.js":
                continue
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    parts.append((_ROOT / "claude" / "glossary.md").read_text(encoding="utf-8"))
    # Options and Button Map Options show a setting's key as its label
    # (gremlin/ui/option.py), without its order prefix ("02-rotate-snap").
    keys = []
    for path in [_ROOT / "joystick_gremlin.py", *(_ROOT / "gremlin").rglob("*.py")]:
        keys += re.findall(
            r'"[a-z-]+",\s*"(?:\d+-)?([a-z0-9_-]+)",\s*PropertyType',
            path.read_text(encoding="utf-8", errors="replace"),
        )
    # The Options pages list their settings as (section, group, key) in
    # gremlin/ui/option.py; the shown label is the key made readable too.
    for path in (_ROOT / "gremlin" / "ui").glob("*option*.py"):
        keys += re.findall(
            r'\(\s*"[a-z-]+",\s*"[a-z-]+",\s*"(?:\d+-)?([a-z0-9_-]+)"\s*\)',
            path.read_text(encoding="utf-8", errors="replace"),
        )
    # Built in qml/rig_menu.js from Rotate snap (15 by default).
    parts += ["Rotate −15°", "Rotate +15°"]
    parts += [re.sub(r"[_-]+", " ", key).capitalize() for key in keys]
    # A label broken over two lines ("Save\nAppearance") reads as one.
    return "\n".join(parts).replace("\\n", " ")


_KEY = re.compile(
    r"^((Ctrl|Shift|Alt|Win)\+)*([A-Z0-9]|F\d+|Esc|Enter|Tab|Space|Delete|"
    r"Backspace|Home|End|Page Up|Page Down|Insert|Up|Down|Left|Right|"
    r"[↑↓←→]|[+\-=,./\[\]]|Plus|Minus)$"
)


def test_bold_labels_exist() -> None:
    """On-screen words are bold and spelled as on screen (help-style.md):
    each bold piece (or each step of a bold menu path) is a key or a word
    the program or the glossary has."""
    known = _known_words()
    missing = set()
    for topic in _topics():
        for bold in re.findall(r"<b>(.*?)</b>", topic["body"], re.S):
            for piece in re.split(r" [→›] ", help_book.text(bold).strip()):
                piece = piece.strip().rstrip(".:,;").strip()
                if piece in ("Good to know", "Related topics"):
                    continue  # the topic's own headings (help-style.md)
                if not piece or _KEY.match(piece) or piece in known:
                    continue
                if piece.rstrip("…") in known:
                    continue
                # A label around a box: "Keep the newest … autosaves per stick".
                if " … " in piece and all(
                    part.strip() in known for part in piece.split(" … ")
                ):
                    continue
                missing.add(f"{topic['chapterId']}: {piece}")
    assert sorted(missing) == []


def test_button_map_chapter_covers_the_editor() -> None:
    """The Button Map chapter covers every part of the editor and nothing
    else."""
    chapter = help_book.chapter_topics("button-map")
    assert len(chapter) >= 20
    section = "\n".join(t["title"] + "\n" + help_book.text(t["body"]) for t in chapter)
    for feature in (
        "Edit Mapping", "Print & Export", "Print Area", "Snap to Entities",
        "Adjust Photo",
        "Highlight on press", "Pressed Fill", "Hotspot", "spine", "Leader Ends",
        "Group Selected", "Mini hat", "Radial", "Undo", "Rounded", "Double arrow",
        "Shape Around Selection", "Arrowheads", "Swap Heads", "Dashed",
        "Rotate and Flip", "Flip Vertically", "Turn to", "Text box",
        "Scale font with box", "Paint format", "Table", "ID column",
        "Independent of table", "Spawn Empty Cell", "Import Picture",
        "Paste picture", "Crop", "Reset Crop", "snap point", "Layers",
        "Unlock all", "Properties", "Align and distribute", "Space Out",
        "Recent", "Pick from Map", "Ctrl+Shift+L", "F1", "Callout", "Freehand",
        "Rulers", "Saved styles", "Print", "Mirror layout",
        "Command palette", "Ctrl+K",
    ):
        assert feature.casefold() in section.casefold(), feature
    # One book: the chapter may say how to open it from the main window
    # (Tools › Mapping › Button Map), but not cover other features.
    for elsewhere in ("Device Pack",):
        assert elsewhere not in section, elsewhere
    # Its settings are its own (Button Map Options), not the main Options.
    assert not re.search(r"(?<!Button Map )Options [→›]", section)
    # No other chapter repeats the Button Map: one topic per subject.
    others = [
        t["id"] for t in _topics()
        if t["chapterId"] != "button-map" and t["section"] != "Common questions"
        and t["title"].casefold().startswith("button map")
    ]
    assert others == []


def test_every_action_plugin_has_a_topic() -> None:
    titles = " | ".join(
        t["title"] for t in help_book.chapter_topics("configuration-actions")
    )
    for init in sorted(_ROOT.joinpath("action_plugins").glob("*/__init__.py")):
        source = init.read_text(encoding="utf-8")
        # The plugin class's own name (class level), not a local variable.
        match = re.search(r'^    name = "([^"]+)"', source, re.M)
        if not match or match.group(1) == "Root":
            continue
        assert match.group(1) in titles, match.group(1)


def test_about_shows_the_build_version() -> None:
    about = (_ROOT / "qml" / "DialogAbout.qml").read_text(encoding="utf-8")
    assert "backend.gremlinVersion" in about
    assert not (_ROOT / "qml" / "button_map_editor_help.md").exists()
