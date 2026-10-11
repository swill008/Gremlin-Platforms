# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Logical Device and Keyboard pages follow a held input like the
Device Bindings page (D-05-FOLLOW-ALL-PAGES, 05 S131), end to end.

A journey (test/journeys/_harness.py): the real app off-screen with a
temporary USERPROFILE and fake hardware.

- Logical Device: its own input events (as Map to Logical Device sends
  them) tint the row while held; a button press while stopped moves the
  page to its row (showKey); an axis gets the live bar and never moves the
  page; while running (03 S114) only the tint; a synthetic event (macro
  step) and Options "Input highlighting" off: no move.
- Keyboard: a key pressed on the PC's keyboard (through the keyboard hook's
  callbacks and the Keyboard input module) tints its row; stopped: the page
  moves to it; running: tint only; setting off or synthetic: no move.

Spec: 05 S131 (D-05-FOLLOW-ALL-PAGES).
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, pump, run_journey  # noqa: E402

KEYS = (0x1E, 0x30, 0x2E, 0x20)  # A, B, C, D


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _tree(j: Journey, name: str) -> Any:  # noqa: ANN401
    for found in j.walk(j.win.contentItem()):
        if found.objectName() == name:
            return found
    return None


def _delegate(j: Journey, tree: Any, key: str) -> Any:  # noqa: ANN401
    for found in j.walk(tree):
        if found.property("key") == key and found.property("ledOn") is not None:
            return found
    return None


def _led(j: Journey, tree: Any, key: str) -> Any:  # noqa: ANN401
    row = _delegate(j, tree, key)
    return None if row is None else bool(row.property("ledOn"))


class _Part:
    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _logical(j: Journey) -> None:  # noqa: PLR0915 (one page, several parts)
    from gremlin.config import Configuration
    from gremlin.event_handler import Event, EventListener
    from gremlin.logical_device import LogicalDevice
    from gremlin.types import InputType
    from gremlin.ui.logical_layout import LogicalLayoutModel

    out = j.out
    state = j.backend.uiState
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("logical"))')
    j.wait_until(lambda: state.currentTab == "logical", "the Logical Device page")
    page = j.wait_until(
        lambda: j.win.findChild(LogicalLayoutModel), "the Logical Device model"
    )
    page.addMany("button", 3, "", "")
    page.addMany("axis", 1, "", "")
    j.settle()
    tree = j.wait_until(lambda: _tree(j, "logicalTree"), "the Logical Device tree")
    guid = LogicalDevice().device_guid
    buttons = [i for i in LogicalDevice().inputs_of_type([InputType.JoystickButton])]
    axis = LogicalDevice().inputs_of_type([InputType.JoystickAxis])[0]
    first, last = buttons[0].id, buttons[-1].id
    key = {
        "first": f"parent:button:{first}",
        "last": f"parent:button:{last}",
        "axis": f"parent:axis:{axis.id}",
    }
    out["ld:keys"] = key

    def button(
        ident: int, pressed: bool, synthetic: bool = False, wait: int = 200
    ) -> None:
        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickButton,
                identifier=ident,
                device_guid=guid,
                mode="Default",
                is_pressed=pressed,
                synthetic=synthetic,
            )
        )
        if wait:
            pump(wait)

    with _Part(j, "ld-tap"):
        # D-05-QUICK-TAP: pressed and let go before the page updates.
        tree.setProperty("highlightKey", "")
        button(first, True, wait=0)
        button(first, False, wait=0)
        pump(300)
        out["ld-tap:highlight"] = str(tree.property("highlightKey"))

    with _Part(j, "ld-stopped"):
        tree.setProperty("highlightKey", "")
        button(last, True)
        out["ld-stopped:highlight"] = str(tree.property("highlightKey"))
        out["ld-stopped:led-pressed"] = _led(j, tree, key["last"])
        button(last, False)
        out["ld-stopped:led-released"] = _led(j, tree, key["last"])

    with _Part(j, "ld-axis"):
        tree.setProperty("highlightKey", "")
        EventListener().joystick_event.emit(
            Event(
                event_type=InputType.JoystickAxis,
                identifier=axis.id,
                device_guid=guid,
                mode="Default",
                value=0.5,
            )
        )
        pump(300)
        out["ld-axis:highlight"] = str(tree.property("highlightKey"))
        row = _delegate(j, tree, key["axis"])
        out["ld-axis:kind"] = "" if row is None else str(row.property("liveKind"))
        out["ld-axis:value"] = None if row is None else float(row.property("liveValue"))

    with _Part(j, "ld-synthetic"):
        tree.setProperty("highlightKey", "")
        button(first, True, synthetic=True)
        out["ld-synthetic:highlight"] = str(tree.property("highlightKey"))
        button(first, False, synthetic=True)

    with _Part(j, "ld-off"):
        Configuration().set("ui", "general", "input-highlighting", False)
        tree.setProperty("highlightKey", "")
        button(first, True)
        out["ld-off:highlight"] = str(tree.property("highlightKey"))
        out["ld-off:led-pressed"] = _led(j, tree, key["first"])
        button(first, False)
        Configuration().set("ui", "general", "input-highlighting", True)

    with _Part(j, "ld-running"):
        j.backend.toggleActiveState()
        out["ld-running:running"] = j.backend.runner.is_running()
        pump(300)
        tree.setProperty("highlightKey", "")
        button(first, True)
        out["ld-running:highlight"] = str(tree.property("highlightKey"))
        out["ld-running:led-pressed"] = _led(j, tree, key["first"])
        button(first, False)
        out["ld-running:led-released"] = _led(j, tree, key["first"])
        j.backend.toggleActiveState()
        pump(300)


def _keyboard(j: Journey) -> None:
    from gremlin.config import Configuration
    from gremlin.event_handler import Event, EventListener
    from gremlin.types import InputType
    from gremlin.ui.keyboard_layout import GUID, KeyboardLayoutModel, key_row

    out = j.out
    state = j.backend.uiState
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(lambda: state.currentTab == "keyboard", "the Keyboard page")
    page = j.wait_until(
        lambda: j.win.findChild(KeyboardLayoutModel), "the Keyboard model"
    )
    for scan in KEYS:
        assert page.addKey([(scan, False)], "Default"), f"key {scan} not added"
    j.settle()
    tree = j.wait_until(lambda: _tree(j, "keyboardTree"), "the Keyboard tree")
    first, last = key_row((KEYS[0], False)), key_row((KEYS[-1], False))
    out["kb:keys"] = {"first": first, "last": last}

    def key(scan: int, pressed: bool) -> None:
        j.key(scan, pressed)
        pump(200)

    with _Part(j, "kb-tap"):
        # D-05-QUICK-TAP: pressed and let go before the page updates.
        tree.setProperty("highlightKey", "")
        j.key(KEYS[1], True)
        j.key(KEYS[1], False)
        pump(300)
        out["kb-tap:highlight"] = str(tree.property("highlightKey"))
        out["kb:keys"]["tap"] = key_row((KEYS[1], False))

    with _Part(j, "kb-stopped"):
        tree.setProperty("highlightKey", "")
        key(KEYS[-1], True)
        out["kb-stopped:highlight"] = str(tree.property("highlightKey"))
        out["kb-stopped:led-pressed"] = _led(j, tree, last)
        key(KEYS[-1], False)
        out["kb-stopped:led-released"] = _led(j, tree, last)

    with _Part(j, "kb-synthetic"):
        tree.setProperty("highlightKey", "")
        EventListener().keyboard_event.emit(
            Event(
                event_type=InputType.Keyboard,
                device_guid=GUID,
                mode="Default",
                identifier=(KEYS[0], False),
                is_pressed=True,
                synthetic=True,
            )
        )
        pump(200)
        out["kb-synthetic:highlight"] = str(tree.property("highlightKey"))
        key(KEYS[0], False)

    with _Part(j, "kb-off"):
        Configuration().set("ui", "general", "input-highlighting", False)
        tree.setProperty("highlightKey", "")
        key(KEYS[0], True)
        out["kb-off:highlight"] = str(tree.property("highlightKey"))
        out["kb-off:led-pressed"] = _led(j, tree, first)
        key(KEYS[0], False)
        Configuration().set("ui", "general", "input-highlighting", True)

    with _Part(j, "kb-running"):
        j.backend.toggleActiveState()
        out["kb-running:running"] = j.backend.runner.is_running()
        pump(300)
        tree.setProperty("highlightKey", "")
        key(KEYS[0], True)
        out["kb-running:highlight"] = str(tree.property("highlightKey"))
        out["kb-running:led-pressed"] = _led(j, tree, first)
        key(KEYS[0], False)
        out["kb-running:led-released"] = _led(j, tree, first)
        j.backend.toggleActiveState()
        pump(300)


def story(j: Journey) -> None:
    from gremlin.config import Configuration

    Configuration().set("ui", "general", "input-highlighting", True)
    with _Part(j, "ld"):
        _logical(j)
    with _Part(j, "kb"):
        _keyboard(j)
    j.out["done"] = True


def main() -> None:
    Journey().run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("page_follow_ld_kb"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    page = part.split("-", 1)[0]
    error = out.get(part + ":error", out.get(page + ":error", out.get("error")))
    trace = out.get(part + ":traceback", out.get(page + ":traceback", ""))
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {error or '(none)'}\n"
        f"{trace or out.get('traceback', '')}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


# Logical Device page.


def test_ld_stopped_button_press_tints_and_follows_its_row(run: dict) -> None:
    keys = _step(run, "ld:keys")
    assert _step(run, "ld-stopped:highlight") == keys["last"]
    assert _step(run, "ld-stopped:led-pressed") is True
    assert _step(run, "ld-stopped:led-released") is False


def test_ld_quick_tap_still_follows_its_row(run: dict) -> None:
    assert _step(run, "ld-tap:highlight") == _step(run, "ld:keys")["first"]


def test_ld_axis_shows_its_bar_and_does_not_move_the_page(run: dict) -> None:
    assert _step(run, "ld-axis:highlight") == ""
    assert _step(run, "ld-axis:kind") == "axis"
    assert _step(run, "ld-axis:value") == pytest.approx(0.5)


def test_ld_synthetic_press_does_not_move_the_page(run: dict) -> None:
    assert _step(run, "ld-synthetic:highlight") == ""


def test_ld_setting_off_tints_without_moving(run: dict) -> None:
    assert _step(run, "ld-off:highlight") == ""
    assert _step(run, "ld-off:led-pressed") is True


def test_ld_running_only_tints(run: dict) -> None:
    assert _step(run, "ld-running:running") is True
    assert _step(run, "ld-running:highlight") == ""
    assert _step(run, "ld-running:led-pressed") is True
    assert _step(run, "ld-running:led-released") is False


# Keyboard page.


def test_kb_stopped_key_press_tints_and_follows_its_row(run: dict) -> None:
    keys = _step(run, "kb:keys")
    assert _step(run, "kb-stopped:highlight") == keys["last"]
    assert _step(run, "kb-stopped:led-pressed") is True
    assert _step(run, "kb-stopped:led-released") is False


def test_kb_quick_tap_still_follows_its_row(run: dict) -> None:
    assert _step(run, "kb-tap:highlight") == _step(run, "kb:keys")["tap"]


def test_kb_synthetic_key_does_not_move_the_page(run: dict) -> None:
    assert _step(run, "kb-synthetic:highlight") == ""


def test_kb_setting_off_tints_without_moving(run: dict) -> None:
    assert _step(run, "kb-off:highlight") == ""
    assert _step(run, "kb-off:led-pressed") is True


def test_kb_running_only_tints(run: dict) -> None:
    assert _step(run, "kb-running:running") is True
    assert _step(run, "kb-running:highlight") == ""
    assert _step(run, "kb-running:led-pressed") is True
    assert _step(run, "kb-running:led-released") is False
