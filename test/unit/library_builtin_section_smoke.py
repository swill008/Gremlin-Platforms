# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S6 (D-10-BUILTIN-SECTION): runs the real Device Library window off-screen
with the stand-in Library of device_library_CU_menus_smoke.py plus the two
built-in inputs (Keyboard, OSC) listed last, and prints what the list shows:
the "Built-in inputs" heading and where it sits, the rows with the state
filter chips off (real clicks) and under a search, and a built-in's
right-click menu and details buttons. test_library_builtin_section.py runs it.

    python test/unit/library_builtin_section_smoke.py <out_dir>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "device_library_CU_menus_smoke", _HERE / "device_library_CU_menus_smoke.py"
)
assert _spec and _spec.loader
menus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(menus)
fake_mod = menus.fake_mod


class BuiltInLibrary(menus.MenuLibrary):
    """The stand-in Library with Keyboard and OSC after the devices, as
    device_library.devices() lists them (contract: builtIn, state builtin)."""

    def __init__(self) -> None:
        super().__init__()
        self.devs.append(
            {
                "key": "dev-0000000b",
                "name": "Keyboard",
                "description": "",
                "state": "builtin",
                "builtIn": True,
                "guid": "{6F1D2B61-D5A0-11CF-BFC7-444553540000}",
                "module": "keyboard",
                "setups": [
                    fake_mod._setup(
                        "set-0000000b",
                        "dev-0000000b",
                        "Keyboard keys",
                        "2026-10-02T10:00:00",
                    )
                ],
            }
        )
        self.devs.append(
            {
                "key": "dev-0000000c",
                "name": "OSC",
                "description": "",
                "state": "builtin",
                "builtIn": True,
                "guid": "{a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70}",
                "module": "osc",
                "setups": [],
            }
        )


menus.MenuLibrary = BuiltInLibrary

# The visible "Built-in inputs" headings: their y and text in the list.
_HEADINGS = (
    "(function() { var out = []; var kids = _list.contentItem.children;"
    " for (var i = 0; i < kids.length; i++) { var c = kids[i];"
    " for (var j = 0; j < c.children.length; j++) { var g = c.children[j];"
    " if (g.objectName === 'libraryBuiltInHeading' && c.visible && c.height > 0)"
    " out.push({y: c.y, text: g.text}); } } return out })()"
)
_KEYS = "deviceLibrary.rows.filter(r => r.kind === 'device').map(r => r.key)"


def _y(key: str) -> str:
    return f"_bridge.item('libraryRow_{key}').y"


def _visible(name: str) -> str:
    return f"(_bridge.item('{name}') !== null && _bridge.item('{name}').visible)"


menus.STEPS = [
    (
        "list",
        "deviceLibrary.setAllOpen(false)",
        "",
        "JSON.stringify({keys: " + _KEYS + ", headings: " + _HEADINGS + ","
        " lastStick: " + _y("dev-00000005") + ", keyboard: " + _y("dev-0000000b") + ","
        " osc: " + _y("dev-0000000c") + "})",
    ),
    (
        "chips-off",
        "_bridge.clickIn('libraryFilter_connected', 'left', 8, -1);"
        " _bridge.clickIn('libraryFilter_not_connected', 'left', 8, -1);"
        " _bridge.clickIn('libraryFilter_deleted', 'left', 8, -1)",
        "",
        "JSON.stringify({filters: deviceLibrary.filters, keys: " + _KEYS + ","
        " headings: " + _HEADINGS + "})",
    ),
    (
        "search-none",
        "_bridge.clickIn('libraryFilter_connected', 'left', 8, -1);"
        " _bridge.clickIn('libraryFilter_not_connected', 'left', 8, -1);"
        " _bridge.clickIn('libraryFilter_deleted', 'left', 8, -1);"
        " _search.text = 'Warthog'",
        "",
        "JSON.stringify({keys: " + _KEYS + ", headings: " + _HEADINGS + "})",
    ),
    (
        "search-keyboard",
        "_search.text = 'Keyboard'",
        "",
        "JSON.stringify({keys: " + _KEYS + ", headings: " + _HEADINGS + "})",
    ),
    (
        "rc-keyboard",
        "_search.text = ''; _bridge.click('libraryRow_dev-0000000b', 'right', '')",
        "_rowMenu.opened",
        "JSON.stringify({selected: deviceLibrary.selected, menu: " + menus._menu() + ","
        " buttons: {save: " + _visible("librarySaveButton") + ","
        " restore: " + _visible("libraryRestoreButton") + ","
        " copy: " + _visible("libraryCopyButton") + ","
        " swap: " + _visible("librarySwapButton") + ","
        " output: " + _visible("libraryOutputButton") + ","
        " exportOn: _bridge.item('libraryExportButton').enabled,"
        " remove: " + _visible("libraryDeleteButton") + "}})",
    ),
    (
        "rc-osc",
        "_rowMenu.close(); _bridge.click('libraryRow_dev-0000000c', 'right', '')",
        "_rowMenu.opened",
        menus._menu(),
    ),
]
menus.SHOTS = {"list": "builtin_section", "rc-keyboard": "builtin_menu"}

if __name__ == "__main__":
    sys.argv = sys.argv[:2]
    menus.main()
