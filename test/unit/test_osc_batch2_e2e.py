# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 2 end to end on the real program (09 S147-S158).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and a
fake vJoy behind the output module. The listener binds 127.0.0.1 on a port
the OS picks (port 0), never a fixed one; packets go over the loopback
only. Nothing is sent out: osc_output.send is replaced by a recorder.

1. Patterns (S147, S148): the OSC input /fader/* (axis) with Map to vJoy
   axis 1. While running, /fader/1 then /fader/2 move axis 1 to each last
   value.
2. Exact wins (Q3): /fader/2 added as its own input with Map to vJoy axis
   2. Running again, /fader/2 moves axis 2 only; /fader/3 still reaches the
   pattern's axis 1.
3. Action state (S157): a Smart Toggle on the OSC button /tog and a
   feedback row with an action_state source on it. Pressing /tog (press and
   release: the toggle latches) makes the feedback runtime's value the on
   value and the recorder sees it sent; a second press turns it off.
4. The page (S153): that feedback row shows under /tog on the OSC page's
   layout model (key feedback:<id>, the input's parent key).

Each part records its own values, so one part failing doesn't hide the
others. Part 4 needs the batch 2 wave 2 page code (feedback rows on
OscLayoutModel and its Feedback editor): xfail(strict) while
gremlin/ui/osc_layout.py has no beginFeedback, so it turns into an
ordinary test once that lands.

Spec: 09 (OSC) S147, S148, S153, S157, S158.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

PATTERN = "/fader/*"
EXACT = "/fader/2"
TOGGLE = "/tog"
FB_ADDRESS = "/fb/tog"
FB_ID = "b2" * 16
ON, OFF = 7, 0

_LAYOUT = ROOT / "gremlin" / "ui" / "osc_layout.py"
_PAGE_FEEDBACK = _LAYOUT.exists() and "def beginFeedback" in _LAYOUT.read_text("utf-8")

# Fails only because the wave 2 page code (feedback rows under an input)
# is not in yet (strict: the mark must come off once it lands).
needs_page_feedback = pytest.mark.xfail(
    not _PAGE_FEEDBACK,
    reason="needs OSC batch 2 wave 2: feedback rows on the OSC page "
    "(gremlin/ui/osc_layout.py has no beginFeedback yet)",
    raises=(AssertionError, JourneyIncomplete),
    strict=True,
)


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
    next part still runs."""

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


def _loopback_listener() -> None:
    """The listener binds 127.0.0.1 on an OS-picked port (port 0)."""
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


_SENT: list[tuple] = []


def _record_sends() -> None:
    """Nothing leaves the PC: OSC output is recorded instead of sent."""
    from gremlin import osc_output

    def send(target: Any, address: str, values: Any, types: Any = None) -> bool:  # noqa: ANN401
        _SENT.append((str(target), str(address), list(values or [])))
        return True

    osc_output.send = send  # type: ignore[assignment]


def _bound_port(listener: Any) -> int:  # noqa: ANN401
    method = getattr(listener, "bound_port", None)
    if callable(method):
        return int(method())
    return int(listener._server.server_address[1])


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {}
        for role, name in names.items():
            value = model.data(index, role)
            plain = isinstance(value, (str, int, float, bool, type(None)))
            row[name] = value if plain else str(value)
        out.append(row)
    return out


def _osc_row(address: str) -> Any:  # noqa: ANN401
    from gremlin.osc import OscDevice

    for row in OscDevice().rows.rows():
        if row.label == address:
            return row
    raise AssertionError(f"no OSC input {address}")


def _parent_key(address: str) -> str:
    from gremlin.types import InputType

    row = _osc_row(address)
    word = {InputType.JoystickAxis: "axis", InputType.JoystickHat: "hat"}.get(
        row.input_type, "button"
    )
    return f"parent:{word}:{row.input_id}"


def _open_osc_page(j: Journey) -> Any:  # noqa: ANN401
    from gremlin.ui.osc_layout import OscLayoutModel

    j.ev('openConfigurationForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")
    return j.wait_until(
        lambda: j.win.findChild(OscLayoutModel), "the OSC page's layout model"
    )


def _add(j: Journey, settings: dict) -> bool:
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    model = j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()
    made = bool(model.createConfiguredInput(settings))
    j.settle()
    return made


def _vjoy_action(kind: str, number: int) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    itype = InputType.JoystickAxis if kind == "axis" else InputType.JoystickButton
    action = plugin_manager.PluginManager().create_instance("Map to vJoy", itype)
    action.vjoy_device_id = 1
    action.vjoy_input_id = number
    action.vjoy_input_type = itype
    return action


def _bind(j: Journey, page: Any, address: str, action: Any) -> None:  # noqa: ANN401
    """Adds an action in the shared pane and presses OK, as the page does."""
    page.beginNewAction(_parent_key(address))
    page._pane_shadow.action_sequences[0].root_action.insert_action(action, "children")
    page.commitPane()
    page.endPane()
    j.settle()


def _axis(j: Journey, number: int) -> Any:  # noqa: ANN401
    device = j.vjoy.vjoy_devices.get(1)
    value = device.state.get(("axis", number)) if device else None
    return None if value is None else round(float(value), 3)


def _run(j: Journey) -> Any:  # noqa: ANN401
    """Run; a client on the loopback to the listener's OS-picked port."""
    from pythonosc.udp_client import SimpleUDPClient

    from gremlin import osc

    j.backend.toggleActiveState()
    runtime = osc.OscRuntime()
    listener = j.wait_until(lambda: runtime._listener, "the OSC listener", 10)
    return SimpleUDPClient("127.0.0.1", _bound_port(listener))


def _stop(j: Journey) -> None:
    if j.backend.runner.is_running():
        j.backend.toggleActiveState()
    j.settle()


def _part_pattern(j: Journey, page: Any) -> None:  # noqa: ANN401
    """1: /fader/* moves axis 1 to the last value of any matching address."""
    out = j.out
    out["1:added"] = _add(
        j, {"address": PATTERN, "mode": "axis", "range_min": 0.0, "range_max": 1.0}
    )
    out["1:is-pattern"] = bool(_osc_row(PATTERN).is_pattern)
    _bind(j, page, PATTERN, _vjoy_action("axis", 1))
    client = _run(j)
    out["1:running"] = j.backend.runner.is_running()
    client.send_message("/fader/1", 1.0)
    out["1:after-fader-1"] = j.await_value(lambda: _axis(j, 1), 1.0)
    client.send_message("/fader/2", 0.0)
    out["1:after-fader-2"] = j.await_value(lambda: _axis(j, 1), -1.0)
    client.send_message("/fader/2", 0.5)
    out["1:after-fader-2-half"] = j.await_value(lambda: _axis(j, 1), 0.0)
    _stop(j)


def _part_exact(j: Journey, page: Any) -> None:  # noqa: ANN401
    """2: an exact /fader/2 takes /fader/2 from the pattern."""
    out = j.out
    out["2:added"] = _add(
        j, {"address": EXACT, "mode": "axis", "range_min": 0.0, "range_max": 1.0}
    )
    _bind(j, page, EXACT, _vjoy_action("axis", 2))
    client = _run(j)
    client.send_message(EXACT, 1.0)
    out["2:exact-axis-2"] = j.await_value(lambda: _axis(j, 2), 1.0)
    j.QTest.qWait(200)
    out["2:pattern-axis-1-untouched"] = _axis(j, 1)
    client.send_message("/fader/3", 1.0)
    out["2:other-address-axis-1"] = j.await_value(lambda: _axis(j, 1), 1.0)
    _stop(j)


def _toggle_id(j: Journey) -> str:
    from gremlin.osc import OSC_DEVICE_UUID
    from gremlin.profile import reachable

    row = _osc_row(TOGGLE)
    for item in j.profile.inputs.get(OSC_DEVICE_UUID, []):
        if item.input_type != row.input_type or item.input_id != row.input_id:
            continue
        for binding in item.action_sequences:
            for action in reachable([binding.root_action]):
                if action.name == "Smart Toggle":
                    return str(action.id)
    raise AssertionError("no Smart Toggle on /tog")


def _part_action_state(j: Journey, page: Any) -> None:  # noqa: ANN401
    """3: a Smart Toggle's state drives a feedback row."""
    from gremlin import osc_device_file, osc_feedback, plugin_manager
    from gremlin.types import InputType

    out = j.out
    out["3:added"] = _add(j, {"address": TOGGLE, "mode": "button"})
    toggle = plugin_manager.PluginManager().create_instance(
        "Smart Toggle", InputType.JoystickButton
    )
    toggle.insert_action(_vjoy_action("button", 5), "children")
    _bind(j, page, TOGGLE, toggle)
    action_id = _toggle_id(j)
    out["3:action-id"] = action_id
    osc_device_file.write_feedback(
        [
            {
                "id": FB_ID,
                "enabled": True,
                "source": {"kind": "action_state", "action": action_id},
                "target": "reply",
                "address": FB_ADDRESS,
                "min": float(OFF),
                "max": float(ON),
                "type": "int",
            }
        ]
    )
    j.settle()
    feedback = osc_feedback.instance()

    def value() -> Any:  # noqa: ANN401
        rows = [r for r in osc_device_file.read_feedback() if r["id"] == FB_ID]
        return feedback.value_of(rows[0]) if rows else "no row"

    def sent() -> list:
        return [v for _t, a, v in _SENT if a == FB_ADDRESS]

    out["3:value-not-running"] = value()
    client = _run(j)
    out["3:value-running"] = j.await_value(value, [OFF])
    client.send_message(TOGGLE, 1)
    client.send_message(TOGGLE, 0)
    out["3:value-after-press"] = j.await_value(value, [ON])
    out["3:held-after-press"] = j.await_value(j.vjoy.held_buttons, [5])
    out["3:sent-after-press"] = j.await_value(
        lambda: sent()[-1:] if sent() else [], [[ON]]
    )
    client.send_message(TOGGLE, 1)
    client.send_message(TOGGLE, 0)
    out["3:value-after-second-press"] = j.await_value(value, [OFF])
    out["3:sent-after-second-press"] = j.await_value(
        lambda: sent()[-1:] if sent() else [], [[OFF]]
    )
    out["3:sent-targets"] = sorted({t for t, a, _v in _SENT if a == FB_ADDRESS})
    _stop(j)
    out["3:value-after-stop"] = value()


def _part_page(j: Journey) -> None:
    """4: the feedback row shows under /tog on the page."""
    out = j.out
    page = _open_osc_page(j)
    j.settle()
    parent = _parent_key(TOGGLE)
    found = [r for r in _rows(page) if r.get("key") == f"feedback:{FB_ID}"]
    out["4:rows"] = len(found)
    out["4:parent"] = found[0].get("parentKey") if found else None
    out["4:want-parent"] = parent
    out["4:title"] = found[0].get("title") if found else None
    out["4:all-keys"] = [
        (r.get("key"), r.get("parentKey"), r.get("rowKind")) for r in _rows(page)
    ]


def story(j: Journey) -> None:
    from gremlin import osc_device_file

    _loopback_listener()
    _record_sends()
    # The port is only what the file says: the listener binds port 0.
    osc_device_file.write_server(
        {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 9000,
            "feedback_enabled": True,
            "feedback_rate": 0,
            "announce": False,
            "find_devices": False,
        }
    )
    page = None
    with _Part(j, "1"):
        page = _open_osc_page(j)
        _part_pattern(j, page)
    with _Part(j, "2"):
        _stop(j)
        page = _open_osc_page(j)
        _part_exact(j, page)
    with _Part(j, "3"):
        _stop(j)
        page = _open_osc_page(j)
        _part_action_state(j, page)
    with _Part(j, "4"):
        _stop(j)
        _part_page(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_batch2_e2e"))


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


def test_a_pattern_input_moves_its_axis_to_each_matching_address_s_value(
    run: dict,
) -> None:
    assert _step(run, "1:added") is True
    assert _step(run, "1:is-pattern") is True
    assert _step(run, "1:running") is True
    assert _step(run, "1:after-fader-1") == 1.0
    assert _step(run, "1:after-fader-2") == -1.0
    assert _step(run, "1:after-fader-2-half") == 0.0


def test_an_exact_input_takes_its_address_from_the_pattern(run: dict) -> None:
    assert _step(run, "2:added") is True
    assert _step(run, "2:exact-axis-2") == 1.0
    # A fresh vJoy device after Stop: the pattern's axis was never written.
    assert _step(run, "2:pattern-axis-1-untouched") is None
    assert _step(run, "2:other-address-axis-1") == 1.0


def test_a_smart_toggle_s_state_drives_its_feedback_row(run: dict) -> None:
    assert _step(run, "3:added") is True
    assert _step(run, "3:value-not-running") is None
    assert _step(run, "3:value-running") == [OFF]
    assert _step(run, "3:value-after-press") == [ON]
    assert _step(run, "3:held-after-press") == [5]
    assert _step(run, "3:sent-after-press") == [[ON]]
    assert _step(run, "3:value-after-second-press") == [OFF]
    assert _step(run, "3:sent-after-second-press") == [[OFF]]
    assert _step(run, "3:sent-targets") == ["reply"]
    assert _step(run, "3:value-after-stop") is None


@needs_page_feedback
def test_the_feedback_row_shows_under_its_action_s_input_on_the_page(
    run: dict,
) -> None:
    keys = " | ".join(map(str, _step(run, "4:all-keys")))
    assert _step(run, "4:rows") == 1, keys
    assert _step(run, "4:parent") == _step(run, "4:want-parent")
    assert FB_ADDRESS in str(_step(run, "4:title"))


if __name__ == "__main__":
    main()
