# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One menu style everywhere: the shared pieces in theme/Gremlin/Menus work,
and no page uses Qt's stock menus or dropdown rows instead of them."""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]

_STOCK_MENU = re.compile(
    r"(?<![\w.])(Menu|MenuItem|MenuSeparator|MenuBar|AutoSizingMenu)\s*\{"
)


def _qml_files() -> dict[str, str]:
    out = {}
    for folder in ("qml", "action_plugins"):
        for path in (_ROOT / folder).rglob("*.qml"):
            rel = path.relative_to(_ROOT).as_posix()
            out[rel] = path.read_text(encoding="utf-8")
    return out


def test_no_stock_menus_anywhere() -> None:
    # The Button Map included: it uses the shared menus too.
    found = [rel for rel, text in _qml_files().items() if _STOCK_MENU.search(text)]
    assert found == [], (
        "Use Gremlin.Menus (ContextMenu, ThemedMenu, ThemedMenuItem) instead "
        f"of Qt's stock menus in: {found}"
    )


def _blocks(text: str, opener: re.Pattern) -> list[str]:
    """The text of each block whose header matches opener (up to its brace)."""
    out = []
    for m in opener.finditer(text):
        depth = 0
        for j in range(m.end() - 1, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[m.end():j])
                    break
    return out


def test_dropdown_rows_use_the_menu_look() -> None:
    # A ComboBox with its own rows draws them with the shared row look.
    opener = re.compile(r"(?<![\w.])\w*ComboBox\s*\{")
    found = []
    for rel, text in _qml_files().items():
        for block in _blocks(text, opener):
            row = re.search(r"\bdelegate:\s*([\w.]+)", block)
            if not row or row.group(1) in ("Menus.DropdownRow", "DropdownRow"):
                continue
            # A row of its own, drawn with the shared row background.
            if "MenuRowBackground" not in text:
                found.append(rel)
    assert found == []


def test_style_dropdowns_use_the_shared_popup() -> None:
    for rel in (
        "theme/GremlinStyle/ComboBox.qml",
        "theme/Gremlin/Compact/ComboBox.qml",
        "theme/Gremlin/Base/TooltipComboBox.qml",
        "theme/Gremlin/Compact/TooltipComboBox.qml",
    ):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert "Menus.DropdownPopup" in text and "Menus.DropdownRow" in text, rel


def test_shared_menus_work(tmp_path: pathlib.Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_HERE / "menus_smoke.py"), str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        env={
            **os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, (result.stderr or "")[-2000:]
    problems = [line for line in lines if line.startswith(("ERROR", "WARN"))]
    assert problems == []
    results = {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ") and line.count(" ") >= 2
    }
    # Menu bar menus: only what can be used, shortcuts shown, no stray
    # separators, empty submenus and hidden commands left out.
    assert results["file-menu"] == "Save Profile (Ctrl+S)|-|Snap|Recent >|-|Exit"
    assert results["file-menu-paste"] == (
        "Save Profile (Ctrl+S)|-|Paste (Ctrl+V)|-|Snap|Recent >|-|Exit"
    )
    assert results["menu-item-runs"] == "save"
    # Right-click menu: quick rows, sections one at a time, remembered.
    assert results["context"] == "A sample|Open (Enter)|Snap [x]|> Look|> Name|> Remove"
    section = results["context-section"]
    assert "v Look|  Size: Small | *Medium | Large|  Count: 1" in section
    assert "*Large" in results["context-pick"]
    assert results["context-toggle"] == "false"
    assert "v Look" in results["context-remembers"]
    # Dropdown lists: long ones search.
    assert results["long-list"] == "true"
    assert results["long-search"] == "Slider 1|Slider 2"
    assert results["short-list"] == "false"
    # Command palette: what can be used, best match first; runs it.
    assert results["palette"] == "Save Profile|Paste|Snap"
    assert results["palette-search"] == "Save Profile"
    assert results["palette-ran"] == "save"
    # A device card's menu.
    assert results["card"] == (
        "Stick|Open Configuration|Button Map|> Module|> View|> Cards|> Device"
    )
    assert results["card-device"].endswith(
        "|  Hide card|  Reset card layout|  Delete Device"
    )
    assert "Unstack" not in results["card-device"]
    # A text box's menu: only the edits that can be made; none, no menu.
    assert results["text-menu"] == (
        "Cut (Ctrl+X)|Copy (Ctrl+C)|Delete|-|Select All (Ctrl+A)"
    )
    assert results["text-menu-empty"] == "false"
    assert results["tooltip"] == "true"
