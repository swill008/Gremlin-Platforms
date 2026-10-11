# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""An OSC fader's row shows the live bar the Device Bindings page shows for a
stick axis (D-05-FOLLOW-ALL-PAGES, "standard on every screen"), end to end.

A journey (test/journeys/_harness.py): the real app off-screen with a
temporary USERPROFILE and fake hardware. The OSC listener binds the
loopback on a port the OS picks; a real UDP fader message moves the bar.

A quick tap (press and release inside the live throttle's 0.1 s) still
moves the page to the button's row (D-05-QUICK-TAP).

Spec: 09 S141; 05 S131 (D-05-FOLLOW-ALL-PAGES, D-05-QUICK-TAP).
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, pump, run_journey, step  # noqa: E402

FADER = "/bar/fader"
BUTTON = "/bar/button"
TOKEN = "row-bar-test"


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


def _row(j: Journey, key: str) -> Any:  # noqa: ANN401
    """The ControlTree delegate of a row (None when it has none)."""
    for found in j.walk(j.win.contentItem()):
        if found.property("key") == key and found.property("liveKind") is not None:
            return found
    return None


def story(j: Journey) -> None:
    from pythonosc.udp_client import SimpleUDPClient

    from gremlin import osc
    from gremlin.config import Configuration
    from gremlin.osc import OscDevice
    from gremlin.ui.osc_device_model import OscDeviceManagementModel
    from gremlin.ui.osc_layout import OscLayoutModel

    _loopback_listener()
    out = j.out
    runtime = osc.OscRuntime()
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")
    page = j.wait_until(lambda: j.win.findChild(OscLayoutModel), "the OSC model")
    add = j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()
    assert add.createConfiguredInput({"address": FADER, "mode": "axis"})
    assert add.createConfiguredInput({"address": BUTTON, "mode": "button"})
    j.settle()
    assert runtime.hold_open(TOKEN), "the loopback port did not open"
    tree = next(f for f in j.walk(j.win.contentItem()) if f.objectName() == "oscTree")
    out["liveBars"] = bool(tree.property("liveBars"))
    uid = {a: OscDevice().find_address(a).uid for a in (FADER, BUTTON)}
    key = {a: str(page.keyOfUid(uid[a])) for a in (FADER, BUTTON)}
    client = SimpleUDPClient("127.0.0.1", int(runtime._listener.bound_port()))
    j.wait_until(lambda: _row(j, key[FADER]), "the fader's row")

    def fader(value: float) -> tuple[str, float]:
        client.send_message(FADER, value)
        j.wait_until(
            lambda: (runtime.live(uid[FADER]) or {}).get("value") == value,
            "the fader message",
        )
        pump(300)  # liveChanged's throttle (0.1 s at most)
        row = _row(j, key[FADER])
        return str(row.property("liveKind")), float(row.property("liveValue"))

    # Range 0..1 -> -1..1, as the stick's bar (0.75 -> 0.5, 0.25 -> -0.5).
    out["fader:0.75"] = fader(0.75)
    out["fader:0.25"] = fader(0.25)
    client.send_message(BUTTON, 1.0)
    j.wait_until(
        lambda: (runtime.live(uid[BUTTON]) or {}).get("pressed") is True,
        "the button message",
    )
    pump(300)
    out["button"] = str(_row(j, key[BUTTON]).property("liveKind"))
    client.send_message(BUTTON, 0.0)
    j.wait_until(
        lambda: (runtime.live(uid[BUTTON]) or {}).get("pressed") is False,
        "the release",
    )
    # A quick tap (D-05-QUICK-TAP): press and release within 50 ms, right
    # after the release's live update, so the throttle (0.1 s) passes on
    # only the release; the page still follows the press.
    Configuration().set("ui", "general", "input-highlighting", True)
    tree.setProperty("highlightKey", "")
    client.send_message(BUTTON, 1.0)
    client.send_message(BUTTON, 0.0)
    pump(400)
    out["tap:pressed"] = (runtime.live(uid[BUTTON]) or {}).get("pressed")
    out["tap:highlight"] = str(tree.property("highlightKey"))
    out["tap:key"] = key[BUTTON]
    runtime.release_open(TOKEN)


def main() -> None:
    Journey().run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_row_bar"))


def test_the_osc_page_turns_the_live_bars_on(run: dict) -> None:
    assert step(run, "liveBars") is True


def test_a_fader_row_bar_follows_a_loopback_message(run: dict) -> None:
    kind, value = step(run, "fader:0.75")
    assert kind == "axis"
    assert value == pytest.approx(0.5, abs=0.01)
    kind, value = step(run, "fader:0.25")
    assert kind == "axis"
    assert value == pytest.approx(-0.5, abs=0.01)


def test_a_button_row_still_reports_a_button(run: dict) -> None:
    assert step(run, "button") == "button"


def test_a_quick_tap_still_follows_its_row(run: dict) -> None:
    assert step(run, "tap:pressed") is False
    assert step(run, "tap:highlight") == step(run, "tap:key")
