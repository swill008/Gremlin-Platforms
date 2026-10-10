# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fixes F4, main window side (01 S71, 03 S40).

S71: File > New with an unsaved Keyboard page pane and an unsaved profile asks
about the draft first, then the profile (as Load and Recent do).

S40: Module Setup open with unsaved ticks; Module Setup for another device
asks Save / Discard / Cancel. After Discard (or Save) the other device's
window opens; after Cancel the first stays and nothing else opens later.

Driven through the real program off-screen (the journey harness): the
Keyboard page's pane really edited (Add Key F, an action not OK'd); the
profile's unsaved flag is faked.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402

_F = 0x21  # scan code of F


def _setup_windows(j: Journey) -> list[str]:
    """The visible Module Setup windows, by device name."""
    from PySide6 import QtQuick

    names = []
    for w in j.app.topLevelWindows():
        if (
            isinstance(w, QtQuick.QQuickWindow)
            and w.isVisible()
            and "Module Setup" in w.title()
        ):
            names.append(str(j.ev("deviceName", w)))
    return sorted(names)


def _tick_first(j: Journey, setup: object) -> None:
    from gremlin.ui.module_model import DriverInputModel

    driver = j.wait_until(lambda: setup.findChild(DriverInputModel), "the controls")
    j.wait_until(lambda: driver.rowCount() > 0, "the control rows")
    names = {int(k): bytes(v).decode() for k, v in driver.roleNames().items()}
    role = next(r for r, n in names.items() if n == "claimed")
    claimed = bool(driver.data(driver.index(0, 0), role))
    driver.setClaimed(0, not claimed)
    j.settle()
    if not j.ev("claimDirty", setup):
        j.ev("claimDirty = true", setup)


def s40(j: Journey) -> None:
    out = j.out
    stick = '_moduleModel.cardMap("pjoy_pro")'
    vjoy = '_moduleModel.cardMap("vjoy_1")'
    out["s40-cards"] = [j.ev(f"{stick}.name"), j.ev(f"{vjoy}.name")]

    for answer in ("Discard", "Save", "Cancel"):
        j.ev(f'openConfigureModule("source", {stick})')
        setup = j.window("Input Module Setup")
        _tick_first(j, setup)
        j.ev(f'openConfigureModule("dest", {vjoy})')
        j.settle()
        out[f"s40-{answer}-asks"] = bool(j.ev("_saveGate.visible", setup))
        j.press_in("_saveGate", answer, setup)
        if answer == "Save":
            # The "Saved" note, then OK closes the window.
            j.wait_until(lambda: j.ev("_saveGate.visible", setup), "the Saved note")
            j.press_in("_saveGate", "OK", setup)
        if answer == "Cancel":
            j.settle()
            out["s40-Cancel-after"] = _setup_windows(j)
            # Closing it later (nothing unsaved) opens nothing else.
            j.ev("claimDirty = false; close()", setup)
            j.wait_until(lambda: not _setup_windows(j), "the window to close")
            j.settle()
            j.settle()
            out["s40-Cancel-later"] = _setup_windows(j)
            continue
        out[f"s40-{answer}-after"] = j.await_value(
            lambda: _setup_windows(j), ["vJoy 1"]
        )
        out[f"s40-{answer}-fresh"] = j.ev(
            "configureWin ? configureWin.direction : null"
        )
        j.ev("if (configureWin) configureWin.close(); true")
        j.wait_until(lambda: not _setup_windows(j), "the vJoy window to close")


def _keyboard_pane(j: Journey) -> object:
    """The Keyboard page opened, F added (Add Key, then F) and its pane
    edited but not OK'd. Returns the pane's leave question."""
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel
    from gremlin.ui.util import InputListenerModel

    state = j.backend.uiState
    j.ev('openConfigurationForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(lambda: state.currentTab == "keyboard", "the Keyboard page")
    page = j.wait_until(lambda: j.ev("keyboardPane()"), "the Keyboard page item")
    layout = j.wait_until(
        lambda: page.findChild(KeyboardLayoutModel), "the page's layout model"
    )
    add_key = j.wait_until(
        lambda: next(
            (i for i in j.walk(page) if i.objectName() == "keyboardAddKey"), None
        ),
        "the Add Key button",
    )
    listener = page.findChild(InputListenerModel)
    j.click(add_key)
    j.wait_until(lambda: listener.property("enabled"), "the Add Key popup")
    j.key(_F, True)
    j.key(_F, False)
    j.wait_until(lambda: layout.paneModel is not None, "the pane on F")
    editor = layout.paneModel
    root = editor.data(editor.index(0, 0), 0x0100 + 1).rootAction
    root.appendAction("Map to vJoy", "children")
    j.wait_until(lambda: j.ev("hasUnsaved()", page), "the pane's unsaved edit")
    pane = next(
        i for i in j.walk(page) if i.metaObject().className().startswith("ActionPane")
    )
    # Its leave question (_leave, a DismissibleDialog): code run on it sees
    # ActionPane.qml's ids.
    return next(
        c
        for c in pane.children()
        if c.metaObject().className().startswith("DismissibleDialog")
    )


def s71(j: Journey) -> None:
    out = j.out
    pane = _keyboard_pane(j)
    profile = j.profile
    profile.has_unsaved_changes = lambda: True
    j.ev('Commands.trigger("file.new")')
    j.settle()
    out["s71-first"] = [
        bool(j.ev("_leave.visible", pane)),
        bool(j.ev("_saveBeforeContinueDialog.visible")),
    ]
    if j.ev("_leave.visible", pane):
        j.press_in("_leave", "Discard", pane)
        j.wait_until(
            lambda: j.ev("_saveBeforeContinueDialog.visible"), "the profile question"
        )
        out["s71-second"] = [
            bool(j.ev("_leave.visible", pane)),
            bool(j.ev("_saveBeforeContinueDialog.visible")),
        ]
        j.press_in("_saveBeforeContinueDialog", "Cancel")
        j.settle()
    out["s71-kept"] = j.profile is profile


def story(j: Journey) -> None:
    s40(j)
    s71(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module("pJoy Pro")
        j.vjoy_module()

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("f4shell"))


def test_s40_cards(run: dict) -> None:
    assert step(run, "s40-cards") == ["pJoy Pro", "vJoy 1"]


@pytest.mark.parametrize("answer", ["Discard", "Save"])
def test_s40_other_device_opens_after_the_answer(run: dict, answer: str) -> None:
    assert step(run, f"s40-{answer}-asks") is True
    assert step(run, f"s40-{answer}-after") == ["vJoy 1"]
    assert step(run, f"s40-{answer}-fresh") == "dest"


def test_s40_cancel_keeps_the_first_and_drops_the_request(run: dict) -> None:
    assert step(run, "s40-Cancel-asks") is True
    assert step(run, "s40-Cancel-after") == ["pJoy Pro"]
    assert step(run, "s40-Cancel-later") == []


def test_s71_new_asks_about_the_keyboard_draft_first(run: dict) -> None:
    assert step(run, "s71-first") == [True, False]
    assert step(run, "s71-second") == [False, True]
    assert step(run, "s71-kept") is True


if __name__ == "__main__":
    main()
