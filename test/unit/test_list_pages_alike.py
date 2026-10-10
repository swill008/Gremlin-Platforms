"""The four list pages stay alike (05 S125, 01 S58a; user decision PS1 (b)).

Configuration, Logical Device, Keyboard and OSC share one shape: the same
pane/leave functions, the same Appearance toggle, and an "Appearance…" quick
row in the right-click menu.
"""

import pathlib
import re

import pytest

QML = pathlib.Path(__file__).resolve().parents[2] / "qml"
PAGES = ["ConfigurationPage.qml", "LogicalPage.qml", "KeyboardPage.qml", "OscPage.qml"]
PANE_FUNCTIONS = [
    "requestLeave", "closePaneNow", "savePane",
    "hasUnsaved", "paneHasChanges", "closeActionPane",
]


def _source(page: str) -> str:
    return (QML / page).read_text(encoding="utf-8")


def _function_body(text: str, name: str) -> str:
    """The body of a top-level `function name(...) { ... }`, by brace count."""
    match = re.search(r"function\s+" + name + r"\s*\([^)]*\)\s*\{", text)
    assert match, f"no function {name}"
    depth = 1
    i = match.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[match.end():i - 1]


@pytest.mark.parametrize("page", PAGES)
def test_menu_has_appearance_row(page: str) -> None:
    text = _source(page)
    # The page's right-click menu builder is the first `build: _root.<name>`.
    builder = re.search(r"build:\s*_root\.(\w+)", text)
    assert builder, "no menu builder"
    body = _function_body(text, builder.group(1))
    assert re.search(r'quick\.push\(MenuModel\.action\("Appearance…"', body)


@pytest.mark.parametrize("page", PAGES)
def test_toggle_appearance_goes_through_request_close_display(page: str) -> None:
    text = _source(page)
    assert "_appear.requestClose()" in _function_body(text, "requestCloseDisplay")
    toggle = _function_body(text, "toggleAppearance")
    assert "requestCloseDisplay()" in toggle
    assert "_appear.requestClose" not in toggle


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("name", PANE_FUNCTIONS)
def test_pane_functions_present(page: str, name: str) -> None:
    _function_body(_source(page), name)
