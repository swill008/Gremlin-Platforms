# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Health (01 S197), the window: tools.health opens one Health window in
Search's layout: Look in (default This profile only), the four checks with
counts, the lines grouped profile › device with the ⚠ (hover: why) from
SearchResultRow's showStatus, the Why panel (bold "Why", the reason in the
danger colour, the fix with its Tools › Drivers link), the right-click menu
and Ctrl/Shift picking. The fix through Change target… on the real path is
test_health_e2e.py's.

A journey (test/journeys/_harness.py): the real main window off-screen in
its own process, a temp USERPROFILE, fake vJoy 1 only."""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
)

# +-------------------------------------------------------------------------
# | Script side (the child process)

_WIN = 'Helpers.windowOf("DialogHealth.qml")'


def _safe(j: Journey, code: str, target: Any = None) -> Any:  # noqa: ANN401
    try:
        return j.ev(code, target)
    except RuntimeError as err:
        return "ERROR " + str(err)


def _first_line(j: Journey) -> Any:  # noqa: ANN401
    return _safe(
        j,
        "(function() { var w = " + _WIN + "; if (!w) return -1; "
        "for (var i = 0; i < w.health.rowCount(); i++) "
        "if (w.health.get(i).rowKind === 'result') return i; return -1 })()",
    )


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin.signal import signal

    out = j.out
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    # vJoy 3 isn't there (fake vJoy 1 only): Binding output not found.
    j.map_button(pjoy, 1, "Default", 1, vjoy=3)
    j.map_button(pjoy, 2, "Default", 2, vjoy=3)
    signal.profileChanged.emit()
    j.settle()

    out["command"] = _safe(
        j,
        "(function() { var l = MainCommands.commandList(); "
        'for (var i = 0; i < l.length; i++) if (l[i].id === "tools.health") '
        "return { text: l[i].text, group: l[i].group }; return null })()",
    )
    _safe(j, 'Commands.trigger("tools.health")')
    j.settle()
    win = j.ev(_WIN)
    if win is None or isinstance(win, str):
        out["window"] = "no window"
        return
    _safe(j, 'Commands.trigger("tools.health")')
    j.settle()
    out["one"] = _safe(j, _WIN + " === " + _WIN)
    out["title"] = win.property("title")
    j.await_value(lambda: _safe(j, "health.problemCount", win), 2, timeout=15.0)
    out["lookIn"] = _safe(j, "health.lookIn", win)
    out["checks"] = _safe(
        j,
        "health.checks.map(function(c) { return c.label + ' (' + c.count + ')' })",
        win,
    )
    out["status"] = _safe(j, "health.statusText", win)
    first = _first_line(j)
    out["first"] = first
    j.settle()
    out["line"] = _safe(
        j,
        "(function() { var it = _list.itemAtIndex(" + str(first) + "); "
        "if (!it) return null; "
        "function named(item, name) { if (item.objectName === name) return item; "
        "for (var i = 0; i < item.children.length; i++) { "
        "var f = named(item.children[i], name); if (f) return f } return null } "
        "var warn = named(it, 'searchRowWarn:' + it.index); "
        "return { showStatus: it.showStatus, notFound: it.notFound, why: it.why, "
        "warn: !!warn && warn.visible } })()",
        win,
    )
    # A click picks the line and fills Why; Ctrl+click adds the next.
    _safe(j, "pick(" + str(first) + ", 0)", win)
    j.settle()
    why = j.item(win, "healthWhy")
    title = j.item(win, "healthWhyTitle")
    reason = j.item(win, "healthWhyReason:0")
    fix = j.item(win, "healthWhyFix:0")
    out["why"] = {
        "panel": why is not None,
        "title": title.property("text") if title else None,
        "bold": bool(title.property("font").bold()) if title else None,
        "reason": reason.property("text") if reason else None,
        "danger": bool(reason)
        and _safe(j, "Qt.color(Style.danger).toString()", win).lower()
        == reason.property("color").name().lower(),
        "fix": fix.property("text") if fix else None,
    }
    second = _safe(
        j,
        "(function() { for (var i = "
        + str(first)
        + " + 1; i < health.rowCount(); i++) "
        "if (health.get(i).rowKind === 'result') return i; return -1 })()",
        win,
    )
    _safe(j, "pick(" + str(second) + ", Qt.ControlModifier)", win)
    j.settle()
    out["picked"] = _safe(j, "health.selectedCount", win)
    out["fixes"] = _safe(j, "health.fixes()", win)
    out["question"] = _safe(j, "health.removeQuestion()", win)
    menu = win.findChild(QtCore.QObject, "healthRowMenu")
    out["menu"] = _safe(
        j,
        "(function() { var t = []; for (var i = 0; i < count; i++) { "
        "var it = itemAt(i); "
        "if (it && it.text && it.objectName !== 'healthUndo') t.push(it.text) } "
        "return t })()",
        menu,
    )
    _safe(j, "escapePressed()", win)
    j.settle()
    out["closed"] = _safe(j, _WIN + " === null")


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module(buttons=[1, 2, 3, 4])

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("health_window"))


def test_tools_health_opens_one_health_window(result: dict) -> None:
    assert result["command"] == {"text": "Health…", "group": "Tools › Mapping"}
    assert result["title"] == "Health"
    assert result["one"] is True


def test_look_in_and_the_four_checks(result: dict) -> None:
    assert result["lookIn"] == "this"
    assert result["checks"][0] == "Binding output not found (2)"
    assert [c.rsplit(" (", 1)[0] for c in result["checks"]] == [
        "Binding output not found",
        "Used twice",
        "No bindings",
        "Not plugged in",
    ]
    assert result["status"].endswith("in 1 profile"), result["status"]


def test_a_line_shows_the_warning_with_its_reason(result: dict) -> None:
    line = result["line"]
    assert isinstance(line, dict), line
    assert line["showStatus"] is True and line["notFound"] is True
    assert line["warn"] is True
    assert line["why"], line


def test_why_panel_has_the_reason_in_danger_and_the_fix_link(result: dict) -> None:
    why = result["why"]
    assert why["panel"] and why["title"] == "Why" and why["bold"] is True
    assert why["reason"] and why["danger"] is True
    assert '<a href="tools.drivers">Tools › Drivers</a>' in why["fix"]


def test_ctrl_click_picks_two_and_they_are_removed_together(result: dict) -> None:
    assert result["picked"] == 2
    assert result["fixes"] == {"remove": True, "changeTarget": False}
    assert result["question"] == "Remove 2 bindings?"
    assert result["menu"] == [
        "Open",
        "Change target…",
        "Remove binding…",
        "Copy as text",
    ]


def test_esc_closes_the_window(result: dict) -> None:
    assert result["closed"] is True


if __name__ == "__main__":
    main()
