"""The four list pages stay alike (05 S125, 01 S58a; user decision PS1 (b);
to-do 91, Method B: shared parts the pages use).

Configuration, Logical Device, Keyboard and OSC share one shape through
three shared parts, each written once:
- the pane/leave functions live in ActionPane.qml; each page exposes its
  pane as `actionPane`;
- the Appearance toggle lives in PageAppearance.qml, which each page uses;
- the right-click menu comes from ControlMenu.standardMenu (control_menu.js),
  which gives every page an "Appearance…" quick row.
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


# --- the menu: ControlMenu.standardMenu --------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_menu_comes_from_the_standard_menu(page: str) -> None:
    text = _source(page)
    assert 'import "control_menu.js" as ControlMenu' in text
    # The page's right-click menu builder is the first `build: _root.<name>`.
    builder = re.search(r"build:\s*_root\.(\w+)", text)
    assert builder, "no menu builder"
    body = _function_body(text, builder.group(1))
    assert "ControlMenu.standardMenu(_root," in body
    # No page builds its own Appearance… row any more.
    assert '"Appearance…"' not in body


def test_standard_menu_has_appearance_row() -> None:
    body = _function_body(_source("control_menu.js"), "standardMenu")
    assert re.search(r'quick\.push\(M\.action\("Appearance…"', body)


# --- the Appearance: PageAppearance ------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_page_uses_page_appearance(page: str) -> None:
    text = _source(page)
    part = text[text.index("PageAppearance {"):]
    part = part[: part.index("}")]
    assert "id: _appear" in part
    assert "pageKey:" in part and "buttonName:" in part
    # The panel comes only through the shared part.
    assert "ListAppearancePanel {" not in text
    assert "property Component pageBar: Component" not in text
    assert "setDisplayPanelOpen" not in text
    close = _function_body(text, "requestCloseDisplay")
    assert "_appear.requestCloseDisplay()" in close
    assert "_appear.toggleAppearance()" in _function_body(text, "toggleAppearance")


def test_toggle_appearance_goes_through_request_close_display() -> None:
    text = _source("PageAppearance.qml")
    assert re.match(r"(?s).*^ListAppearancePanel \{", text, re.M)
    assert "requestClose()" in _function_body(text, "requestCloseDisplay")
    toggle = _function_body(text, "toggleAppearance")
    assert "requestCloseDisplay()" in toggle
    assert "requestClose(" not in toggle.replace("requestCloseDisplay(", "")


# --- the pane/leave functions: ActionPane ------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_page_exposes_action_pane(page: str) -> None:
    assert "property alias actionPane: _pane" in _source(page)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("name", PANE_FUNCTIONS)
def test_pane_functions_not_in_page(page: str, name: str) -> None:
    # Written once, in ActionPane.qml.
    assert not re.search(r"function\s+" + name + r"\s*\(", _source(page))


@pytest.mark.parametrize("name", PANE_FUNCTIONS)
def test_pane_functions_in_action_pane(name: str) -> None:
    text = _source("ActionPane.qml")
    _function_body(text, name)
    assert len(re.findall(r"function\s+" + name + r"\s*\(", text)) == 1
