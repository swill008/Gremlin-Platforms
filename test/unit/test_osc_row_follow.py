# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page follows a held input (D-09-OSC-ROW-FOLLOW), end to end.

A journey (test/journeys/_harness.py): the real app off-screen with a
temporary USERPROFILE and fake hardware. The OSC listener binds the
loopback on a port the OS picks; real UDP packets press the inputs.

- A pressed button input's row tints (ControlTree's live LED tint) and
  clears on release, stopped or running.
- Stopped, with Options "Input highlighting" on and no highlight hold: a
  button press scrolls the page to the row and flashes it (showKey).
- Running (the "run" hold, 03 S114): tint only, no move.
- A fader (axis) never moves the page; Send Test (synthetic) neither.
- The setting off: no move (the row still tints).

Spec: 09 S32, S141; 05 S131 (D-09-OSC-ROW-FOLLOW).
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

COUNT = 30
LAST = f"/f/{COUNT - 1}"
FIRST = "/f/0"
MIDDLE = "/f/5"
FADER = "/fader"
TOKEN = "row-follow-test"


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _loopback_listener() -> None:
    """The listener binds 127.0.0.1 on a port the OS picks (port 0)."""
    from gremlin import osc

    real = osc.OscListener

    class LoopbackListener(real):  # type: ignore[misc, valid-type]
        def start(self) -> None:
            host, port = self.host, self.port
            self.host, self.port = "127.0.0.1", 0
            try:
                super().start()
            finally:
                self.host, self.port = host, port

    osc.OscListener = LoopbackListener  # type: ignore[misc]


def _client() -> Any:  # noqa: ANN401
    from pythonosc.udp_client import SimpleUDPClient

    from gremlin import osc

    listener = osc.OscRuntime()._listener
    assert listener is not None, "the OSC port is not open"
    return SimpleUDPClient("127.0.0.1", int(listener.bound_port()))


def _uid(address: str) -> str:
    from gremlin.osc import OscDevice

    row = OscDevice().find_address(address)
    assert row is not None, f"no OSC input {address}"
    return row.uid


def _tree(j: Journey) -> Any:  # noqa: ANN401
    for found in j.walk(j.win.contentItem()):
        if found.objectName() == "oscTree":
            return found
    return None


def _led(j: Journey, key: str) -> Any:  # noqa: ANN401
    """The row's live tint (ControlTree delegate ledOn), None when the row
    has no delegate."""
    for found in j.walk(j.win.contentItem()):
        if found.property("key") == key and found.property("ledOn") is not None:
            return bool(found.property("ledOn"))
    return None


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


def story(j: Journey) -> None:  # noqa: PLR0915 (one story, several parts)
    from gremlin import osc, osc_device_file
    from gremlin.config import Configuration
    from gremlin.ui.osc_device_model import OscDeviceManagementModel
    from gremlin.ui.osc_layout import OscLayoutModel

    _loopback_listener()
    out = j.out
    runtime = osc.OscRuntime()
    state = j.backend.uiState
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: state.currentTab == "osc", "the OSC page")
    page = j.wait_until(lambda: j.win.findChild(OscLayoutModel), "the OSC model")
    add = j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()
    for n in range(COUNT):
        assert add.createConfiguredInput({"address": f"/f/{n}", "mode": "button"})
    assert add.createConfiguredInput({"address": FADER, "mode": "axis"})
    j.settle()
    Configuration().set("ui", "general", "input-highlighting", True)
    assert runtime.hold_open(TOKEN), "the loopback port did not open"
    tree = j.wait_until(lambda: _tree(j), "the OSC page's ControlTree")
    key_of = {a: str(page.keyOfUid(_uid(a))) for a in (FIRST, MIDDLE, LAST, FADER)}

    def live(address: str) -> Any:  # noqa: ANN401
        entry = runtime.live(_uid(address)) or {}
        return entry.get("pressed") if address != FADER else entry.get("axis")

    def send(address: str, value: float) -> None:
        _client().send_message(address, value)
        want = (value > 0.5) if address != FADER else value
        j.await_value(lambda: live(address), want)
        # The page hears it after liveChanged's throttle (0.1 s at most).
        pump(300)

    with _Part(j, "stopped"):
        tree.setProperty("highlightKey", "")
        send(LAST, 1)
        out["stopped:highlight"] = str(tree.property("highlightKey"))
        out["stopped:led-pressed"] = _led(j, key_of[LAST])
        send(LAST, 0)
        out["stopped:led-released"] = _led(j, key_of[LAST])

    with _Part(j, "axis"):
        tree.setProperty("highlightKey", "")
        send(FADER, 0.5)
        out["axis:highlight"] = str(tree.property("highlightKey"))

    with _Part(j, "synthetic"):
        tree.setProperty("highlightKey", "")
        page.sendTest(key_of[MIDDLE], "press", 0.0)
        pump(400)
        out["synthetic:highlight"] = str(tree.property("highlightKey"))

    with _Part(j, "off"):
        Configuration().set("ui", "general", "input-highlighting", False)
        # Bring the row into view, then forget that move.
        j.ev(f'showKey("{key_of[MIDDLE]}")', target=tree)
        j.wait_until(lambda: _led(j, key_of[MIDDLE]) is not None, "the row")
        pump(700)
        tree.setProperty("highlightKey", "")
        send(MIDDLE, 0)
        send(MIDDLE, 1)
        out["off:highlight"] = str(tree.property("highlightKey"))
        out["off:led-pressed"] = _led(j, key_of[MIDDLE])
        send(MIDDLE, 0)
        Configuration().set("ui", "general", "input-highlighting", True)

    with _Part(j, "running"):
        osc_device_file.write_server(
            {"enabled": True, "host": "127.0.0.1", "port": 9000}
        )
        j.backend.toggleActiveState()
        out["running:running"] = j.backend.runner.is_running()
        j.wait_until(lambda: runtime._listener, "the OSC listener", 10)
        # Bring the first row into view, then forget that move.
        j.ev(f'showKey("{key_of[FIRST]}")', target=tree)
        j.wait_until(lambda: _led(j, key_of[FIRST]) is not None, "the first row")
        pump(700)
        tree.setProperty("highlightKey", "")
        send(FIRST, 1)
        out["running:highlight"] = str(tree.property("highlightKey"))
        out["running:led-pressed"] = _led(j, key_of[FIRST])
        send(FIRST, 0)
        out["running:led-released"] = _led(j, key_of[FIRST])
        j.backend.toggleActiveState()

    out["keys"] = key_of
    runtime.release_open(TOKEN)


def main() -> None:
    Journey().run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_row_follow"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def test_stopped_button_press_tints_and_follows_its_row(run: dict) -> None:
    keys = _step(run, "keys")
    assert _step(run, "stopped:highlight") == keys[LAST]
    assert _step(run, "stopped:led-pressed") is True
    assert _step(run, "stopped:led-released") is False


def test_running_button_press_only_tints(run: dict) -> None:
    assert _step(run, "running:running") is True
    assert _step(run, "running:highlight") == ""
    assert _step(run, "running:led-pressed") is True
    assert _step(run, "running:led-released") is False


def test_a_fader_does_not_move_the_page(run: dict) -> None:
    assert _step(run, "axis:highlight") == ""


def test_send_test_does_not_move_the_page(run: dict) -> None:
    assert _step(run, "synthetic:highlight") == ""


def test_input_highlighting_off_tints_without_moving(run: dict) -> None:
    assert _step(run, "off:highlight") == ""
    assert _step(run, "off:led-pressed") is True
