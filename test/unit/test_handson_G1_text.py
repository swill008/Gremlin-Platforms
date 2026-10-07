# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fixes G1: window text that said the wrong thing.

04 S49: a mode rename or delete reaches the running profile at once
(ModeManager.rename_mode / drop_mode); added modes and new parents wait for
the next Run (the lookup is built at Run). Manage Modes' running note said
everything waits.

03 (Keyboard Module Setup): the Keyboard's window showed the stick hint
("Press a control on the device… 5-way hats"); it now says to press a key.

01 S105: the Config log's copy button is "Copy All".

Driven through the real program off-screen (the journey harness).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "journeys"))
from _harness import Journey, run_journey, step  # noqa: E402


def _texts(j: Journey, window: object) -> list[str]:
    out = []
    for item in j.walk(window.contentItem()):
        value = item.property("text")
        if isinstance(value, str) and value:
            out.append(value)
    return out


def _close(j: Journey, window: object) -> None:
    j.ev("close(); true", window)
    j.settle()


def story(j: Journey) -> None:
    out = j.out

    j.ev('Helpers.createComponent("DialogManageModes.qml"); true')
    modes = j.window("Manage Modes")
    out["modes-note"] = [
        t for t in _texts(j, modes) if t.startswith("The profile is running.")
    ]
    _close(j, modes)

    j.ev('openConfigureModule("source", _moduleModel.cardMap("keyboard"))')
    keyboard = j.window("Input Module Setup")
    out["keyboard-name"] = j.ev("deviceName", keyboard)
    out["keyboard-texts"] = _texts(j, keyboard)
    j.ev("claimDirty = false; true", keyboard)
    _close(j, keyboard)
    j.wait_until(lambda: not j.ev("configureWin !== null && configureWin.visible"),
                 "the Keyboard window to close")

    j.ev('openConfigureModule("source", _moduleModel.cardMap("pjoy_pro"))')
    stick = j.window("Input Module Setup")
    out["stick-texts"] = _texts(j, stick)
    j.ev("claimDirty = false; true", stick)
    _close(j, stick)

    j.ev('Helpers.createComponent("DialogLiveLog.qml"); true')
    log = j.window("Live Log Reader")
    out["log-texts"] = [t for t in _texts(j, log) if t.startswith("Copy All")]
    _close(j, log)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module("pJoy Pro")

    Journey(before).run(story)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("g1text"))


def test_manage_modes_note_says_what_applies_now(run: dict) -> None:
    assert step(run, "modes-note") == [
        "The profile is running. Renamed and deleted modes change at once; "
        "added modes and new parents take effect the next time it starts."
    ]


def test_keyboard_module_setup_asks_for_a_key(run: dict) -> None:
    assert step(run, "keyboard-name").lower() == "keyboard"
    texts = step(run, "keyboard-texts")
    assert not any("5-way hats" in t or "Press a control" in t for t in texts)
    assert (
        "Press a key to find it and claim it for this module; "
        "clear its check box to let it go."
    ) in texts


def test_stick_module_setup_keeps_its_hint(run: dict) -> None:
    texts = step(run, "stick-texts")
    assert any(
        t.startswith("Press a control on the device to claim it") for t in texts
    )


def test_the_log_copy_button_is_copy_all(run: dict) -> None:
    assert set(step(run, "log-texts")) == {"Copy All"}


if __name__ == "__main__":
    main()
