# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The User Guide and the Button Map help match the program."""

from __future__ import annotations

import html
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_GUIDE = (_ROOT / "qml" / "help_topics.js").read_text(encoding="utf-8")
_MAIN = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
_BUTTON_MAP = (_ROOT / "qml" / "DialogJoystickButtonMap.qml").read_text(
    encoding="utf-8"
)

_TOPIC = re.compile(r'topic\("([^"]+)", "([^"]+)",')


def _text(source: str) -> str:
    """Guide text without HTML tags or JS string glue."""
    joined = re.sub(r'"\s*\+\s*"', "", source)
    return html.unescape(re.sub(r"<[^>]+>", "", joined))


def _menu_labels() -> set[str]:
    labels: set[str] = set()
    for source in (_MAIN, _BUTTON_MAP):
        labels |= set(re.findall(r'(?:text|title): qsTr\("([^"]+)"\)', source))
        labels |= set(re.findall(r'(?:text|title): "([^"]+)"', source))
    return {label.rstrip("…").strip() for label in labels}


def test_every_topic_has_a_section_title_and_body() -> None:
    topics = _TOPIC.findall(_GUIDE)
    assert len(topics) >= 50
    assert len(set(topics)) == len(topics), "duplicate topic"
    sections = [section for section, _title in topics]
    for section in ("Getting Started", "Devices and Modules", "Troubleshooting"):
        assert section in sections


def test_menu_paths_in_the_guide_exist() -> None:
    labels = _menu_labels()
    text = _text(_GUIDE)
    missing = []
    paths = list(re.finditer(r"\b(File|View|Tools|Debug|Help) → ", text))
    assert len(paths) >= 20  # the check really ran
    for match in paths:
        rest = text[match.end():]
        # Each step after the menu must start with a real menu label.
        while True:
            known = [label for label in labels if label and rest.startswith(label)]
            if not known:
                missing.append(f"{match.group(1)} → {rest[:30]}")
                break
            step = max(known, key=len)
            rest = rest[len(step):]
            if not rest.startswith(" → "):
                break
            rest = rest[3:]
    assert missing == []


def test_removed_or_wrong_things_are_not_in_the_help() -> None:
    text = _text(_GUIDE)
    for phrase in (
        "Device Viewer",
        "Help → Logical Device",
        "Claim all",  # Xbox has no claims
        "Claimed box",
        "tapped once",  # Map to Keyboard has no tap option
    ):
        assert phrase not in text, phrase
    for phrase in ("50%–400%", "World page", "not in yet", "Empty photo — Draw only"):
        assert phrase not in text, phrase


def test_button_map_help_is_the_guide_section() -> None:
    """Button Map's Help menu and F1 open the User Guide at its own section,
    which covers every part of the editor."""
    assert "Button Map — Help" not in _BUTTON_MAP
    assert _BUTTON_MAP.count('openGuide("Button Map")') == 2  # menu and F1
    found = _TOPIC.findall(_GUIDE)
    titles = [title for section, title in found if section == "Button Map"]
    assert len(titles) >= 15
    start = _GUIDE.index('topic("Button Map", ')
    end = _GUIDE.index('topic("Options and Profile", ')
    section = _text(_GUIDE[start:end])
    for feature in (
        "Edit Mapping", "Export size", "Snap to entities", "Adjust photo",
        "Highlight on press", "Pressed fill", "Hotspot", "spine", "Leader ends",
        "Group selected", "Mini hat", "Radial", "Undo", "Rounded", "Double arrow",
        "Shape around selection", "Arrowheads", "Swap heads", "Dashed",
        "Rotate and flip", "Flip vertically", "Turn to", "Text box",
        "Scale font with box", "Paint format", "Table", "ID column",
        "Independent of table", "Spawn empty cell", "Import picture",
        "Paste picture", "Crop", "Reset crop", "snap point", "Layers",
        "Unlock all", "Properties", "Align and distribute", "Space out",
        "Recent", "Pick from map", "Ctrl+Shift+L", "F1", "Device Pack",
    ):
        assert feature in section, feature


def test_every_action_plugin_has_a_topic() -> None:
    found = _TOPIC.findall(_GUIDE)
    topics = {title for section, title in found if section == "Actions"}
    for init in sorted(_ROOT.joinpath("action_plugins").glob("*/__init__.py")):
        source = init.read_text(encoding="utf-8")
        match = re.search(r'^\s+name = "([^"]+)"', source, re.M)
        if not match or match.group(1) == "Root":
            continue
        assert match.group(1) in topics, match.group(1)


def test_about_shows_the_build_version() -> None:
    about = (_ROOT / "qml" / "DialogAbout.qml").read_text(encoding="utf-8")
    assert "backend.gremlinVersion" in about
    assert not (_ROOT / "qml" / "button_map_editor_help.md").exists()
