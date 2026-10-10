# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Redo's keys work on the Logical page and the Configuration page
(no behaviour change).

Both Redo Shortcuts listed StandardKey.Redo and "Ctrl+Shift+Z". On Windows
StandardKey.Redo is Ctrl+Y and Ctrl+Shift+Z, so Ctrl+Shift+Z was there
twice, the Shortcut was ambiguous for it and it never fired. Each now lists
StandardKey.Redo alone.

The real program runs off-screen in its own process (this file run as a
journey script): an edit, then Ctrl+Z, Ctrl+Y, Ctrl+Z, Ctrl+Shift+Z as real
Qt key events on the main window.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey  # noqa: E402

_KEYS = ("ctrl-z", "ctrl-y", "ctrl-z-2", "ctrl-shift-z")


def _check(out: dict) -> None:
    assert "error" not in out, out
    assert out["edited"] == [True, False], out
    assert out["ctrl-z"] == [False, True], out
    assert out["ctrl-y"] == [True, False], out
    assert out["ctrl-z-2"] == [False, True], out
    assert out["ctrl-shift-z"] == [True, False], out


def test_redo_keys_on_the_logical_page(tmp_path: pathlib.Path) -> None:
    _check(run_journey(__file__, tmp_path / "home", "logical"))


def test_redo_keys_on_the_configuration_page(tmp_path: pathlib.Path) -> None:
    out = run_journey(__file__, tmp_path / "home", "configuration")
    _check(out)
    # Undo took the group away, Redo put it back (Ctrl+Y and Ctrl+Shift+Z).
    assert out["played"] == ["before", "after", "before", "after"], out


def _keys(j: Journey, model: object, out: dict, after_key: object = None) -> None:
    from PySide6 import QtCore, QtGui

    j.win.requestActivate()
    j.wait_until(
        lambda: QtGui.QGuiApplication.focusWindow() is not None, "the window active"
    )

    def state() -> list:
        j.settle()
        return [bool(model.property("canUndo")), bool(model.property("canRedo"))]

    ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
    shift = QtCore.Qt.KeyboardModifier.ShiftModifier
    z, y = QtCore.Qt.Key.Key_Z, QtCore.Qt.Key.Key_Y
    out["edited"] = state()
    for name, key, mods in zip(
        _KEYS, (z, y, z, z), (ctrl, ctrl, ctrl, ctrl | shift), strict=True
    ):
        j.QTest.keyClick(j.win, key, mods)
        out[name] = state()
        if after_key is not None:
            after_key()


def _logical(j: Journey) -> None:
    from gremlin.ui.logical_layout import LogicalLayoutModel

    state = j.backend.uiState
    state.setCurrentRoom("configuration")
    state.setCurrentTab("logical")
    model = j.wait_until(
        lambda: j.win.findChild(LogicalLayoutModel), "the Logical page's model"
    )
    model.addGroup("Redo keys")
    _keys(j, model, j.out)


def _configuration(j: Journey) -> None:
    layout = j.open_configuration("pjoy_pro")
    played: list = []
    # A real Undo step (a new group): Undo plays "before" (no group), Redo
    # "after" (the group is back).
    layout.addGroup("Redo keys")

    def side() -> None:
        names = [group["name"] for group in layout.groups]
        played.append("after" if "Redo keys" in names else "before")

    _keys(j, layout, j.out, side)
    j.out["played"] = played


def _main() -> None:
    part = sys.argv[1] if len(sys.argv) > 1 else "logical"

    def before(j: Journey) -> None:
        j.input_module()

    Journey(before).run(_logical if part == "logical" else _configuration)


if __name__ == "__main__":
    _main()
