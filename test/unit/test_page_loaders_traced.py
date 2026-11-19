# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every page Loader in Main.qml is a traced PageLoader with a page name
(01 S176, D-01-WINDOW-TRACE; design for change: a new page can't skip it).
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MAIN = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")


def _page_loader_ids() -> list[str]:
    # Main.qml's own list of its page loaders (the tray clean-up walks it).
    m = re.search(r"var loaders = \[([^\]]+)\]", _MAIN)
    assert m, "Main.qml's page loader list"
    return re.findall(r"\w+", m.group(1))


def test_every_page_loader_has_a_trace_name() -> None:
    ids = _page_loader_ids()
    assert len(ids) == 9
    names = []
    for loader in ids:
        pattern = rf"(\w+) \{{\s*id: {loader}\s*\n\s*traceName: \"([^\"]+)\""
        m = re.search(pattern, _MAIN)
        assert m, f"{loader} has no traceName"
        assert m.group(1) == "PageLoader", loader
        names.append(m.group(2))
    assert len(set(names)) == len(names)


def test_no_plain_loader_shows_a_page() -> None:
    # A page (a *Page.qml file or a known page component) in a plain Loader.
    pages = r'(source: "\w+Page\.qml"|sourceComponent: (StatusPage|OutputModuleView|' \
            r"XboxDevice|ScriptManager|ProfileSettings) \{)"
    for m in re.finditer(r"(?<![\w.])Loader \{", _MAIN):
        block = _MAIN[m.end():m.end() + 600]
        nxt = re.search(r"(?<![\w.])(Page)?Loader \{", block)
        block = block[: nxt.start()] if nxt else block
        assert not re.search(pages, block), block[:200]


def test_page_loader_reports_to_the_window_trace() -> None:
    text = (_ROOT / "qml" / "PageLoader.qml").read_text(encoding="utf-8")
    assert "property string traceName" in text
    for what in ('"loaded"', '"unloaded"', '"failed to load"'):
        assert what in text
    assert "windowTrace.page(traceName, what)" in text


def test_save_window_state_is_in_the_debug_menu() -> None:
    commands = (_ROOT / "qml" / "main_commands.js").read_text(encoding="utf-8")
    assert re.search(
        r'id: "debug.saveWindowState", text: "Save Window State", group: "Debug"',
        commands,
    )
    assert "windowTrace.saveWindowState()" in commands
    debug = _MAIN[_MAIN.index('title: qsTr("Debug")'):]
    debug = debug[: debug.index("ThemedMenu {")]
    assert 'command: "debug.saveWindowState"' in debug
