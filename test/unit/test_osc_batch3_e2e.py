# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 3 end to end on the real program (09 S159-S164).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and a
fake vJoy behind the output module. The listener binds 127.0.0.1 on a port
the OS picks (port 0), never a fixed one; packets go over the loopback
only. Nothing is sent out: osc_output.send is replaced by a recorder.

The journey runs twice (two processes, so neither nears the time limit):

Run "a":
1. Allow-list (S160): with allow_senders ["10.0.0.0/8"] a loopback /blk
   press fires nothing (vJoy button 3 stays up, no live value) and the
   OSC Monitor's row reads "blocked"; with ["127.0.0.1"] the same press
   holds button 3.
2. Shaping (S161): an axis input with Invert and a centre deadzone
   (-0.2, 0.2), Map to vJoy axis 1: 1.0 -> -1.0, 0.55 (0.1 after scaling)
   -> 0.0, 0.8 (0.6) -> -0.5, 0.0 -> 1.0.
3. Condition (S159): a Condition on /fire whose condition is the OSC
   button /gate pressed gates a Map to vJoy button 7 while running.

Run "b":
4. Encoder acceleration (S164): an encoder (direction, step 0.05, axis
   output, High) on vJoy axis 2, on a fake gremlin.clock: three slow ticks
   (1 s apart) move 0.15; three fast ticks (same instant) move 0.05 +
   0.15 + 0.25 = 0.45.
5. TouchOSC import (S162): a .tosc built here (zlib XML: a fader, a
   button, an XY pad, a radio and a label) through the Add Inputs model's
   previewTouchOsc / importTouchOsc adds five inputs (XY as two axes, the
   radio as Change, no label) and they show on the OSC page's layout model.
6. Scripts (S163): a user script with an OscInputVariable pointed at
   /script/press gets its callback when a loopback press arrives while
   running.

Each part records its own values, so one part failing doesn't hide the
others. A part whose code isn't in yet is xfail(strict) on that code's
presence, so the mark has to come off once it lands.

Spec: 09 (OSC) S159, S160, S161, S162, S163, S164.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
import zlib
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    JourneyIncomplete,
    run_journey,
)

BLOCKED_ADDR = "/blk"
AXIS_ADDR = "/shaped"
GATE = "/gate"
FIRE = "/fire"
ENC = "/enc"
SCRIPT_ADDR = "/script/press"
TOSC_ADDRESSES = ["/tosc/fader1", "/tosc/btn1", "/tosc/xy", "/tosc/radio"]


def _has(path: str, *needles: str) -> bool:
    file = ROOT / path
    if not file.exists():
        return False
    text = file.read_text("utf-8", errors="replace")
    return all(n in text for n in needles)


_ALLOW = _has("gremlin/osc.py", "def sender_allowed", "BLOCKED") and _has(
    "gremlin/ui/osc_monitor_model.py", '"blocked"'
)
_SHAPE = _has("gremlin/osc.py", "axis_shaping.shape(") and _has(
    "gremlin/osc_rows.py", "invert", "deadzone"
)
_COND = _has("action_plugins/condition/condition.py", "def setOscInput") and _has(
    "gremlin/osc.py", "osc_state"
)
_ACCEL = _has("gremlin/osc.py", "def _accel", "ENC_ACCEL_FACTORS")
_TOSC = _has("gremlin/osc_tosc.py", "def parse") and _has(
    "gremlin/ui/osc_device_model.py", "def importTouchOsc", "def previewTouchOsc"
)
_SCRIPT = _has("gremlin/user_script.py", "class OscInputVariable")


def _needs(present: bool, what: str) -> pytest.MarkDecorator:
    # Fails only because the named batch 3 code isn't in yet (strict: the
    # mark must come off once it lands).
    return pytest.mark.xfail(
        not present,
        reason=f"needs OSC batch 3: {what}",
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


def _record_sends() -> None:
    """Nothing leaves the PC: OSC output is recorded instead of sent."""
    from gremlin import osc_output

    osc_output.send = lambda *a, **k: True  # type: ignore[assignment]


SERVER = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 9000,
    "feedback_enabled": False,
    "announce": False,
    "find_devices": False,
}


def _server(allow: list[str]) -> None:
    from gremlin import osc_device_file

    osc_device_file.write_server({**SERVER, "allow_senders": list(allow)})


def _bound_port(listener: Any) -> int:  # noqa: ANN401
    method: Any = getattr(listener, "bound_port", None)
    if callable(method):
        return int(method())  # pyright: ignore[reportArgumentType]
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


def _osc_row(address: str, source: int | None = None) -> Any:  # noqa: ANN401
    from gremlin.osc import OscDevice

    for row in OscDevice().rows.rows():
        if row.label == address and (source is None or row.source == source):
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


def _device_model(j: Journey) -> Any:  # noqa: ANN401
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    return j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()


def _add(j: Journey, settings: dict) -> bool:
    made = bool(_device_model(j).createConfiguredInput(settings))
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


def _monitor_rows(j: Journey, address: str) -> list[dict]:
    """The OSC Monitor's rows for address (opened, read, closed)."""
    from gremlin.ui.osc_monitor_model import OscMonitorModel

    model = OscMonitorModel()
    model.setProperty("active", True)
    j.settle()
    try:
        return [r for r in _rows(model) if r.get("address") == address]
    finally:
        model.setProperty("active", False)
        j.settle()


# --- run "a" ------------------------------------------------------------------


def _part_allow(j: Journey) -> None:
    """1: a sender off the allow-list fires nothing; on it, it fires."""
    from gremlin import osc

    out = j.out
    page = _open_osc_page(j)
    out["1:added"] = _add(j, {"address": BLOCKED_ADDR, "mode": "button"})
    _bind(j, page, BLOCKED_ADDR, _vjoy_action("button", 3))
    uid = _osc_row(BLOCKED_ADDR).uid

    _server(["10.0.0.0/8"])
    client = _run(j)
    out["1:allowed-loopback"] = osc.sender_allowed("127.0.0.1")
    client.send_message(BLOCKED_ADDR, 1)
    # Nothing is expected to change: give the packet time to arrive.
    j.wait_until(
        lambda: any(e.get("address") == BLOCKED_ADDR for e in _traffic()),
        "the blocked message in the Monitor's record",
        5,
    )
    j.QTest.qWait(300)
    out["1:blocked-held"] = j.vjoy.held_buttons()
    out["1:blocked-live"] = osc.OscRuntime().live(uid)
    rows = _monitor_rows(j, BLOCKED_ADDR)
    out["1:monitor-matched"] = [r.get("matched") for r in rows]
    out["1:monitor-blocked"] = [r.get("blocked") for r in rows]
    client.send_message(BLOCKED_ADDR, 0)
    _stop(j)

    _server(["127.0.0.1"])
    client = _run(j)
    client.send_message(BLOCKED_ADDR, 1)
    out["1:allowed-held"] = j.await_value(j.vjoy.held_buttons, [3])
    rows = _monitor_rows(j, BLOCKED_ADDR)
    out["1:allowed-monitor-blocked"] = [r.get("blocked") for r in rows][-1:]
    client.send_message(BLOCKED_ADDR, 0)
    out["1:allowed-released"] = j.await_value(j.vjoy.held_buttons, [])
    _stop(j)
    _server([])


def _traffic() -> list[dict]:
    from gremlin import osc_traffic

    return osc_traffic.recent()


def _part_shaping(j: Journey) -> None:
    """2: Invert and a centre deadzone shape the axis before Map to vJoy."""
    from gremlin import osc_device_file
    from gremlin.osc import OscDevice

    out = j.out
    page = _open_osc_page(j)
    out["2:added"] = _add(
        j, {"address": AXIS_ADDR, "mode": "axis", "range_min": 0.0, "range_max": 1.0}
    )
    row = _osc_row(AXIS_ADDR)
    OscDevice().rows.update(row.uid, invert=True, deadzone=(-0.2, 0.2))
    osc_device_file.save()
    row = _osc_row(AXIS_ADDR)
    out["2:settings"] = [bool(row.invert), list(row.deadzone)]
    _bind(j, page, AXIS_ADDR, _vjoy_action("axis", 1))
    client = _run(j)
    readings = []
    for sent, want in ((1.0, -1.0), (0.55, 0.0), (0.8, -0.5), (0.0, 1.0)):
        client.send_message(AXIS_ADDR, sent)
        readings.append(j.await_value(lambda: _axis(j, 1), want))
    out["2:readings"] = readings
    _stop(j)


def _part_condition(j: Journey) -> None:
    """3: a Condition on the OSC button /gate gates /fire's Map to vJoy."""
    from action_plugins.condition import condition as cond_mod
    from gremlin import plugin_manager
    from gremlin.types import InputType

    out = j.out
    page = _open_osc_page(j)
    out["3:added"] = [
        _add(j, {"address": GATE, "mode": "button"}),
        _add(j, {"address": FIRE, "mode": "button"}),
    ]
    action = plugin_manager.PluginManager().create_instance(
        "Condition", InputType.JoystickButton
    )
    cond = cond_mod.JoystickCondition()
    cond.setOscInput(_osc_row(GATE).uid)
    action.conditions.append(cond)
    action.insert_action(_vjoy_action("button", 7), "true")
    _bind(j, page, FIRE, action)
    client = _run(j)
    client.send_message(FIRE, 1)
    j.wait_until(lambda: _seen(FIRE, 1), "the first /fire press", 5)
    j.QTest.qWait(200)
    out["3:gate-up-held"] = j.vjoy.held_buttons()
    client.send_message(FIRE, 0)
    client.send_message(GATE, 1)
    j.wait_until(lambda: _seen(GATE, 1), "the /gate press", 5)
    j.QTest.qWait(100)
    client.send_message(FIRE, 1)
    out["3:gate-down-held"] = j.await_value(j.vjoy.held_buttons, [7])
    client.send_message(FIRE, 0)
    out["3:released"] = j.await_value(j.vjoy.held_buttons, [])
    client.send_message(GATE, 0)
    _stop(j)


def _seen(address: str, count: int) -> bool:
    return sum(1 for e in _traffic() if e.get("address") == address) >= count


# --- run "b" ------------------------------------------------------------------


class _FakeClock:
    """gremlin.clock.monotonic on a time the test steps."""

    def __init__(self) -> None:
        from gremlin import clock

        self.clock = clock
        self.real = clock.monotonic
        self.t = self.real()
        clock.monotonic = lambda: self.t  # type: ignore[assignment]

    def close(self) -> None:
        self.clock.monotonic = self.real  # type: ignore[assignment]


def _part_encoder(j: Journey) -> None:
    """4: fast ticks move an accelerated encoder further than slow ones."""
    from gremlin import osc_device_file
    from gremlin.osc import OscDevice

    out = j.out
    page = _open_osc_page(j)
    out["4:added"] = _add(
        j,
        {
            "address": ENC,
            "mode": "encoder",
            "enc_format": "direction",
            "enc_step": 0.05,
            "enc_output": "axis",
        },
    )
    row = _osc_row(ENC)
    OscDevice().rows.update(row.uid, enc_accel="high")
    osc_device_file.save()
    out["4:accel"] = _osc_row(ENC).enc_accel
    _bind(j, page, ENC, _vjoy_action("axis", 2))
    fake = _FakeClock()
    try:
        client = _run(j)
        slow = []
        for _ in range(3):
            fake.t += 1.0
            client.send_message(ENC, 1)
            j.wait_until(
                lambda n=len(slow) + 1: _seen(ENC, n), "a slow encoder tick", 5
            )
            j.QTest.qWait(50)
            slow.append(_axis(j, 2))
        out["4:slow"] = slow
        fake.t += 1.0
        for _ in range(3):
            client.send_message(ENC, 1)
        j.wait_until(lambda: _seen(ENC, 6), "the fast encoder ticks", 5)
        out["4:fast"] = j.await_value(lambda: _axis(j, 2), 0.6)
        _stop(j)
    finally:
        fake.close()


def _tosc_node(kind: str, name: str, path: str | None, values: list[str]) -> str:
    props = (
        "<properties><property type='s'><key>name</key>"
        f"<value>{name}</value></property></properties>"
    )
    if path is None:
        return f"<node type='{kind}'>{props}</node>"
    args = "".join(
        "<partial><type>VALUE</type>"
        f"<value>{v}</value><scaleMin>0</scaleMin><scaleMax>1</scaleMax></partial>"
        for v in values
    )
    message = (
        "<messages><osc><enabled>1</enabled><send>1</send><receive>1</receive>"
        f"<path><partial><type>CONSTANT</type><value>{path}</value></partial></path>"
        f"<arguments>{args}</arguments></osc></messages>"
    )
    return f"<node type='{kind}'>{props}{message}</node>"


def write_tosc(path: pathlib.Path) -> pathlib.Path:
    """A small TouchOSC layout: zlib-compressed XML (NOT VERIFIED against
    Hexler's documentation; the shape tosclib reads)."""
    children = "".join(
        [
            _tosc_node("FADER", "fader1", "/tosc/fader1", ["x"]),
            _tosc_node("BUTTON", "btn1", "/tosc/btn1", ["x"]),
            _tosc_node("XY", "xy", "/tosc/xy", ["x", "y"]),
            _tosc_node("RADIO", "radio", "/tosc/radio", ["x"]),
            _tosc_node("LABEL", "title", None, []),
        ]
    )
    xml = (
        "<?xml version='1.0' encoding='UTF-8'?><lexml version='3'>"
        "<node type='GROUP'><properties><property type='s'><key>name</key>"
        "<value>root</value></property></properties>"
        f"<children>{children}</children></node></lexml>"
    )
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    return path


def _part_tosc(j: Journey) -> None:
    """5: a TouchOSC layout adds its inputs; they show on the page."""
    import os

    from gremlin.types import InputType

    out = j.out
    page = _open_osc_page(j)
    file = write_tosc(pathlib.Path(os.environ["USERPROFILE"]) / "layout.tosc")
    model = _device_model(j)
    preview = dict(model.previewTouchOsc(str(file)))
    out["5:preview-error"] = preview.get("error")
    rows = list(preview.get("rows") or [])
    out["5:preview"] = [(r.get("address"), r.get("kindText")) for r in rows]
    chosen = [int(r.get("index")) for r in rows if r.get("ticked")]
    out["5:result"] = model.importTouchOsc(str(file), chosen)
    j.settle()
    made = []
    for address in TOSC_ADDRESSES:
        for row in _osc_rows_at(address):
            kind = "axis" if row.input_type == InputType.JoystickAxis else "button"
            made.append((address, row.mode, kind, row.source))
    out["5:inputs"] = sorted(made)
    page = _open_osc_page(j)
    j.settle()
    shown = " | ".join(str(v) for r in _rows(page) for v in r.values())
    out["5:on-page"] = [a for a in TOSC_ADDRESSES if a in shown]


def _osc_rows_at(address: str) -> list[Any]:
    from gremlin.osc import OscDevice

    return [r for r in OscDevice().rows.rows() if r.label == address]


SCRIPT = """\
import pathlib

from gremlin.user_script import OscInputVariable

HITS = pathlib.Path(__file__).with_suffix(".hits")


class _Mode:
    value = "Default"


press = OscInputVariable("Press", "The OSC input", False)


@press.decorator(_Mode())
def on_press(event):
    with HITS.open("a", encoding="utf-8") as out:
        out.write(f"{int(bool(event.is_pressed))}\\n")
"""


def _part_script(j: Journey) -> None:
    """6: a script's OSC input variable gets its callback while running."""
    import os

    out = j.out
    _open_osc_page(j)
    out["6:added"] = _add(j, {"address": SCRIPT_ADDR, "mode": "button"})
    uid = _osc_row(SCRIPT_ADDR).uid
    folder = pathlib.Path(os.environ["USERPROFILE"]) / "scripts"
    folder.mkdir(exist_ok=True)
    path = folder / "osc_press.py"
    path.write_text(SCRIPT, encoding="utf-8")
    hits = path.with_suffix(".hits")
    j.profile.scripts.add_script(path)
    script = next(s for s in j.profile.scripts.scripts if s.path == path)
    out["6:load-error"] = script.load_error
    variable = script.get_variable("Press")
    variable.uid = uid
    out["6:valid"] = bool(variable.is_valid())
    client = _run(j)
    client.send_message(SCRIPT_ADDR, 1)
    client.send_message(SCRIPT_ADDR, 0)

    def read() -> list[str]:
        return hits.read_text("utf-8").split() if hits.exists() else []

    out["6:hits"] = j.await_value(read, ["1", "0"])
    _stop(j)


def story_a(j: Journey) -> None:
    _loopback_listener()
    _record_sends()
    _server([])
    with _Part(j, "1"):
        _part_allow(j)
    with _Part(j, "2"):
        _stop(j)
        _part_shaping(j)
    with _Part(j, "3"):
        _stop(j)
        _part_condition(j)


def story_b(j: Journey) -> None:
    _loopback_listener()
    _record_sends()
    _server([])
    with _Part(j, "4"):
        _part_encoder(j)
    with _Part(j, "5"):
        _stop(j)
        _part_tosc(j)
    with _Part(j, "6"):
        _stop(j)
        _part_script(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    which = sys.argv[1] if len(sys.argv) > 1 else "a"
    Journey(before).run(story_b if which == "b" else story_a)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run_a(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_batch3_e2e_a"), "a")


@pytest.fixture(scope="module")
def run_b(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_batch3_e2e_b"), "b")


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


@_needs(_ALLOW, "the sender allow-list (osc.sender_allowed, Monitor 'blocked')")
def test_a_sender_off_the_allow_list_fires_nothing_and_shows_blocked(
    run_a: dict,
) -> None:
    assert _step(run_a, "1:added") is True
    assert _step(run_a, "1:allowed-loopback") is False
    assert _step(run_a, "1:blocked-held") == []
    assert _step(run_a, "1:blocked-live") is None
    assert _step(run_a, "1:monitor-matched") == ["blocked"]
    assert _step(run_a, "1:monitor-blocked") == [True]


@_needs(_ALLOW, "the sender allow-list (osc.sender_allowed, Monitor 'blocked')")
def test_a_sender_on_the_allow_list_fires(run_a: dict) -> None:
    assert _step(run_a, "1:allowed-held") == [3]
    assert _step(run_a, "1:allowed-monitor-blocked") == [False]
    assert _step(run_a, "1:allowed-released") == []


@_needs(_SHAPE, "Invert and deadzone on OSC axis inputs (osc.shape_axis)")
def test_an_inverted_axis_with_a_deadzone_reaches_vjoy_shaped(run_a: dict) -> None:
    assert _step(run_a, "2:added") is True
    assert _step(run_a, "2:settings") == [True, [-0.2, 0.2]]
    assert _step(run_a, "2:readings") == [-1.0, 0.0, -0.5, 1.0]


@_needs(_COND, "OSC conditions (JoystickCondition.setOscInput, osc_state)")
def test_a_condition_on_an_osc_button_gates_a_map_to_vjoy(run_a: dict) -> None:
    assert _step(run_a, "3:added") == [True, True]
    assert _step(run_a, "3:gate-up-held") == []
    assert _step(run_a, "3:gate-down-held") == [7]
    assert _step(run_a, "3:released") == []


@_needs(_ACCEL, "encoder acceleration (OscRuntime._accel)")
def test_an_accelerated_encoder_moves_further_on_fast_ticks(run_b: dict) -> None:
    assert _step(run_b, "4:added") is True
    assert _step(run_b, "4:accel") == "high"
    assert _step(run_b, "4:slow") == [0.05, 0.1, 0.15]
    # 0.15 + 0.05 * (1 + 3 + 5): High (factor 2) on three ticks at once.
    assert _step(run_b, "4:fast") == 0.6


@_needs(_TOSC, "TouchOSC import (gremlin/osc_tosc.py, importTouchOsc)")
def test_a_touchosc_layout_adds_its_inputs_to_the_page(run_b: dict) -> None:
    assert _step(run_b, "5:preview-error") == ""
    assert [tuple(r) for r in _step(run_b, "5:preview")] == [
        ("/tosc/fader1", "Axis"),
        ("/tosc/btn1", "Button"),
        ("/tosc/xy", "Axis"),
        ("/tosc/xy", "Axis"),
        ("/tosc/radio", "Change"),
    ]
    assert str(_step(run_b, "5:result")).startswith("Added 5"), _step(run_b, "5:result")
    assert [tuple(r) for r in _step(run_b, "5:inputs")] == sorted(
        [
            ("/tosc/fader1", "axis", "axis", 0),
            ("/tosc/btn1", "button", "button", 0),
            ("/tosc/xy", "axis", "axis", 0),
            ("/tosc/xy", "axis", "axis", 1),
            ("/tosc/radio", "change", "button", 0),
        ]
    )
    assert _step(run_b, "5:on-page") == TOSC_ADDRESSES


@_needs(_SCRIPT, "script OSC input variables (user_script.OscInputVariable)")
def test_a_script_s_osc_input_variable_gets_its_callback(run_b: dict) -> None:
    assert _step(run_b, "6:added") is True
    assert _step(run_b, "6:load-error") == ""
    assert _step(run_b, "6:valid") is True
    assert _step(run_b, "6:hits") == ["1", "0"]


if __name__ == "__main__":
    main()
