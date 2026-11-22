# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Health on the toolbar (01 S197): the button after Search, its count and
colour from gremlin/health.py (backend.healthBrokenCount), and a click that
runs the command tools.health.

A journey (test/journeys/_harness.py): the real main window off-screen in
its own process, a temp USERPROFILE. Health's count is faked here
(health.broken_count) and its change listeners told, as a rebuilt index
would.
"""

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

_BUTTON = (
    "(function() { var b = _healthButton; var n = null; "
    "for (var i = 0; i < b.children.length; i++) "
    "if (b.children[i].objectName === 'healthCount') n = b.children[i]; "
    "return { caption: b.caption, glyph: b.text.charCodeAt(0), "
    "tooltip: b.tooltip, count: b.brokenCount, "
    "red: Qt.colorEqual(b.color, Style.danger), "
    "gray: Qt.colorEqual(b.color, Style.fgMuted), "
    "number: n && n.visible ? n.text : '', "
    "numberRed: n ? Qt.colorEqual(n.color, Style.danger) : false } })()"
)


def _safe(j: Journey, code: str) -> Any:  # noqa: ANN401
    try:
        return j.ev(code)
    except RuntimeError as err:
        return "ERROR " + str(err)


def _set_count(j: Journey, count: int) -> None:
    """Fakes Health's count and tells its listeners (as a rebuilt index)."""
    from gremlin import health

    health.broken_count = lambda: count
    health._notify()  # pyright: ignore[reportPrivateUsage]
    j.settle()


def story(j: Journey) -> None:
    out = j.out
    j.settle()
    out["place"] = _safe(
        j,
        "({ afterSearch: _healthButton.x > _searchButton.x, "
        "beforeEditor: _healthButton.x < _deviceMappingEditorButton.x, "
        'helpFinds: _helpToolbarButton("Health") === _healthButton, '
        "inWidth: _toolbarWidth(false) >= _healthButton.compactWidth })",
    )
    _set_count(j, 3)
    out["three"] = _safe(j, _BUTTON)
    _set_count(j, 1)
    out["one"] = _safe(j, _BUTTON)
    _set_count(j, 0)
    out["zero"] = _safe(j, _BUTTON)
    # The click runs tools.health (its run swapped for a recorder; defined
    # here when the Health window's command isn't there).
    out["click"] = _safe(
        j,
        "(function() { var c = Commands.get('tools.health'); "
        "if (!c) { Commands.define({ id: 'tools.health', owner: 'test', "
        "run: function() {} }); c = Commands.get('tools.health') } "
        "var hits = 0; var was = c.run; c.run = function() { hits++ }; "
        "_healthButton.clicked(); c.run = was; return hits })()",
    )


def main() -> None:
    Journey().run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("health_toolbar"))


def test_health_is_after_search(result: dict) -> None:
    assert result["place"] == {
        "afterSearch": True,
        "beforeEditor": True,
        "helpFinds": True,
        "inWidth": True,
    }, result


def test_broken_outputs_show_red_with_the_count(result: dict) -> None:
    three = result["three"]
    assert isinstance(three, dict), result
    assert three["caption"] == "Health"
    assert three["glyph"] == 0xF66B  # bootstrap-icons "activity": a heartbeat line
    assert three["count"] == 3
    assert three["red"] is True and three["gray"] is False
    assert three["number"] == "3" and three["numberRed"] is True
    assert three["tooltip"] == "3 binding outputs not found in this profile"
    assert result["one"]["number"] == "1"


def test_nothing_broken_is_gray_with_no_number(result: dict) -> None:
    zero = result["zero"]
    assert isinstance(zero, dict), result
    assert zero["count"] == 0
    assert zero["gray"] is True and zero["red"] is False
    assert zero["number"] == ""
    assert zero["tooltip"] == "No problems found"


def test_click_runs_tools_health(result: dict) -> None:
    assert result["click"] == 1, result


if __name__ == "__main__":
    main()
