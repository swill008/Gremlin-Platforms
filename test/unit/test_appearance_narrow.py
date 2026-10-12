# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""05 D-05-APPEARANCE-NARROW (A1): the Appearance panel closes when the
list (min 360), the action pane (min 420) and the panel (360) don't fit.

The Device Bindings page off-screen (journey harness: temporary home, fakes):

- at 200 % in a 1600 px window, opening the pane closes the Appearance
  panel and OK is inside the window;
- the user can reopen it from the page bar while the window is still too
  narrow; it stays until the next resize that leaves too little room;
- at 100 % in a 1600 px window it stays open beside the pane.

The panel is PageAppearance.qml, shared by the four list pages.

Run as a script, this file is the child process and prints RESULT.

    python test/unit/test_appearance_narrow.py <scale>
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]


# +-------------------------------------------------------------------------
# | Child process


def _story(j) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    scale = int(sys.argv[1])

    def panel() -> object:
        for it in j.walk(j.win.contentItem()):
            if it.objectName() == "deviceBindingsAppearance":
                return it
        return None

    def ok_right() -> float | None:
        right = None
        for it in j.walk(j.win.contentItem()):
            if (
                it.metaObject().className().startswith("Button")
                and it.isVisible()
                and it.property("text") == "OK"
            ):
                right = it.mapToScene(QtCore.QPointF(0, 0)).x() + it.width()
        return right

    def shown() -> bool:
        return bool(panel().isVisible())

    def size(width: int) -> None:
        j.win.setWidth(width)
        j.win.setHeight(round(950 * scale / 100))
        j.settle()
        j.QTest.qWait(200)

    size(1600 * scale // 100)
    catalog = j.open_device_bindings("pjoy_pro")
    j.wait_until(panel, "the Appearance panel")
    j.out["wide"] = shown()
    size(1600)
    j.out["narrow_no_pane"] = shown()
    j.open_input(catalog, "button", 1)
    j.QTest.qWait(300)
    j.out["with_pane"] = shown()
    j.out["ok_right"] = ok_right()
    j.out["window"] = j.win.contentItem().width()
    # The user reopens it from the page bar while still too narrow.
    if not shown():
        j.ev("toggleAppearance(); true", j.ev("deviceBindingsPane()"))
        j.wait_until(shown, "the reopened Appearance panel")
        j.out["reopened"] = shown()
        size(1590)
        j.out["after_resize"] = shown()


def _main() -> None:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import Journey  # pyright: ignore[reportMissingImports]

    scale = int(sys.argv[1])

    def before(j) -> None:  # noqa: ANN001
        from gremlin.ui import ui_scale_option

        ui_scale_option.active_scale = lambda: scale  # type: ignore[assignment]
        j.input_module()
        j.vjoy_module()

    Journey(before).run(_story)


# +-------------------------------------------------------------------------
# | The tests


def _run(scale: int, tmp_path: pathlib.Path) -> dict:
    sys.path.insert(0, str(_ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    out = run_journey(
        pathlib.Path(__file__), pathlib.Path(tempfile.mkdtemp(dir=tmp_path)), str(scale)
    )
    assert not out.get("error"), out.get("traceback")
    return out


@pytest.fixture(scope="module")
def at_200(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run(200, tmp_path_factory.mktemp("narrow-200"))


def test_panel_closes_when_the_pane_leaves_too_little_room(at_200: dict) -> None:
    """Spec: 05 D-05-APPEARANCE-NARROW (A1). At 200 % in a 1600 px window
    the list, pane and Appearance minimums don't fit: the panel closes and
    OK is inside the window. Without the pane it fits and stays."""
    assert at_200["wide"] is True
    assert at_200["narrow_no_pane"] is True
    assert at_200["with_pane"] is False
    assert at_200["ok_right"] is not None
    assert at_200["ok_right"] <= at_200["window"] + 0.5


def test_reopened_panel_stays_until_the_next_resize(at_200: dict) -> None:
    """Spec: 05 D-05-APPEARANCE-NARROW (A1). Appearance… reopens it while
    the window is too narrow (the user's click wins); the next resize that
    leaves too little room closes it again."""
    assert at_200.get("reopened") is True
    assert at_200.get("after_resize") is False


def test_panel_stays_when_everything_fits(tmp_path: pathlib.Path) -> None:
    """Spec: 05 D-05-APPEARANCE-NARROW (A1). At 100 % in a 1600 px window
    the list, pane and Appearance fit side by side: the panel stays."""
    out = _run(100, tmp_path)
    assert out["wide"] is True
    assert out["with_pane"] is True
    assert out["ok_right"] <= out["window"] + 0.5


if __name__ == "__main__":
    _main()
