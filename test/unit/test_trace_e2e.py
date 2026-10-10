# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Control tracing end to end (D-01-TRACE): the whole program, off-screen,
in its own process with a fresh user folder (test/journeys/_harness.py:
fake joystick driver, fake vJoy behind the output module, no network).

A profile maps the fake stick's axis 1 to vJoy 1 X, button 1 to vJoy 1
button 1 and button 2 to vJoy 1 button 9, which the vJoy 1 module doesn't
claim. Run, tick the stick's controls, tracing on, and the driver's events
come in through the real listener callback:
- RAW, WIRING and OUTPUT lines for the axis and button 1, in the ring and
  in trace.log; BLOCKED for button 2.
- Out-of-step check: the driver polls a value the program never got an
  event for, and vJoy reads back other than what was written: one OUT OF
  STEP line each, and the notice.
- HidHide (faked driver, never the real one): the cloak turned off outside
  the program gives one HIDHIDE warning; HidHide in use (err 5) one line.
- Unticked and tracing off: no new lines. A second start (same folder):
  tracing is off and trace.log doesn't grow; a fresh folder has no
  trace.log until tracing is first turned on.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "journeys"))
from _harness import Journey, claim_everything, run_journey, step  # noqa: E402

# Fake driver axis values (raw, -32768..32767) by device Data1.
_PHYSICAL = 501018480
_VIRTUAL = 501018481


def _lines(trace: object) -> list[list]:
    return [list(line) for line in trace.lines()]  # type: ignore[attr-defined]


def _with(
    lines: list[list], point: str, control: str = "", text: str = ""
) -> list[list]:
    return [
        ln for ln in lines
        if ln[2] == point and control in ln[1] and text in ln[3]
    ]


def _install_axis_fake(j: Journey) -> dict[int, int]:
    """The fake driver's polled axis values, settable by the story."""
    polled: dict[int, int] = {_PHYSICAL: 0, _VIRTUAL: 0}

    def get_axis(guid: object, _index: int) -> int:
        return polled.get(getattr(guid, "Data1", 0), 0)

    j.dill_fake.get_axis = get_axis
    return polled


_STICK_PATH = "HID\\VID_5678&PID_FACE\\7&2B1C3D4E&0&0000"


def _install_hidhide_fake() -> dict:
    """A HidHide driver in this process: the control device and its calls
    (never the real driver). err is the Windows error of the next open
    (5: the HidHide window holds it). The calls above the open and the
    ioctl (the trace taps, the watch) are the program's own."""
    from gremlin import hidhide_driver as hd

    hh: dict = {
        "err": 0, "cloak": True, "inverse": True,
        "apps": ["C:\\Games\\StarCitizen.exe"], "devices": [_STICK_PATH],
    }

    def open_control() -> int | None:
        if hh["err"]:
            return hd._opened(None, hh["err"])
        return hd._opened(4242, 0)

    def ioctl(
        _handle: int, code: int, inn: bytes | None = None, out_size: int = 0
    ) -> tuple[bool, bytes]:
        code = int(code) & 0xFFFFFFFF
        flags = {hd.IOCTL_GET_ACTIVE: "cloak", hd.IOCTL_GET_INVERSE: "inverse"}
        lists = {hd.IOCTL_GET_WHITELIST: "apps", hd.IOCTL_GET_BLACKLIST: "devices"}
        if code in flags:
            return True, bytes([int(bool(hh[flags[code]]))])
        if code in lists:
            return True, hd._encode_multi_sz(hh[lists[code]])
        sets = {hd.IOCTL_SET_ACTIVE: "cloak", hd.IOCTL_SET_INVERSE: "inverse"}
        if code in sets:
            hh[sets[code]] = bool(inn and inn[0])
            return True, b""
        set_lists = {hd.IOCTL_SET_WHITELIST: "apps", hd.IOCTL_SET_BLACKLIST: "devices"}
        if code in set_lists:
            hh[set_lists[code]] = hd._decode_multi_sz(inn or b"")
            return True, b""
        return False, b""

    hd._open_control = open_control
    hd._ioctl = ioctl
    hd._close = lambda _handle: None
    hd.list_hid_devices = lambda _gaming: [
        {"instanceId": _STICK_PATH, "instanceIds": [_STICK_PATH], "name": "pJoy Pro"}
    ]
    return hh


def _axis_event(j: Journey, device: object, index: int, value: int) -> None:
    import dill

    callback = j.dill_fake.input_event_callback
    assert callback is not None, "the event listener is not listening"
    callback(dill._JoystickInputData(
        device_guid=device.device_guid.ctypes,  # type: ignore[attr-defined]
        input_type=1, input_index=index, value=value,
    ))


def story(j: Journey) -> None:  # noqa: PLR0915
    from gremlin import plugin_manager
    from gremlin.types import InputType

    out = j.out
    polled = _install_axis_fake(j)
    hh = _install_hidhide_fake()
    stick = j.stick()
    uid = stick.device_guid.uuid

    # Profile: axis 1 -> vJoy 1 X, button 1 -> vJoy button 1, button 2 ->
    # vJoy button 9 (not claimed by the vJoy 1 module).
    pm = plugin_manager.PluginManager()
    axis_action = pm.create_instance("Map to vJoy", InputType.JoystickAxis)
    axis_action.vjoy_device_id = 1
    axis_action.vjoy_input_id = 1
    axis_action.vjoy_input_type = InputType.JoystickAxis
    item = j.profile.get_input_item(uid, InputType.JoystickAxis, 1, "Default", True)
    item.add_item_binding().root_action.insert_action(axis_action, "children")
    j.map_button(uid, 1, "Default", 1)
    j.map_button(uid, 2, "Default", 9)

    from gremlin import trace

    out["file-at-start"] = trace.file_path().exists()
    j.backend.toggleActiveState()
    out["running"] = j.backend.runner.is_running()

    # Ticked, tracing still off: nothing is traced, no file.
    trace.set_tick(uid, "axis", 1, True)
    trace.set_tick(uid, "button", 1, True)
    trace.set_tick(uid, "button", 2, True)
    j.press(stick, 1, True)
    j.press(stick, 1, False)
    j.settle()
    out["lines-before-on"] = _lines(trace)
    out["file-before-on"] = trace.file_path().exists()

    # --- 1. RAW, WIRING, OUTPUT / BLOCKED ---------------------------------------
    trace.set_enabled(True)
    out["file-after-on"] = trace.file_path().exists()
    polled[_PHYSICAL] = 16384  # the driver agrees with the event below
    _axis_event(j, stick, 1, 16384)
    j.press(stick, 1, True)
    j.press(stick, 2, True)

    def got_all() -> bool:
        ls = _lines(trace)
        return bool(
            _with(ls, trace.OUTPUT, "Axis 1")
            and _with(ls, trace.OUTPUT, "Button 1")
            and _with(ls, trace.BLOCKED, "Button 2")
        )

    try:
        j.wait_until(got_all, "the traced lines", timeout=8)
    except TimeoutError:
        pass
    out["lines-on"] = _lines(trace)

    def file_text() -> str | None:
        path = trace.file_path()
        return path.read_text(encoding="utf-8") if path.exists() else None

    def file_has_all() -> bool:
        text = file_text() or ""
        return all(
            f"  {p}  " in text for p in ("RAW", "WIRING", "OUTPUT", "BLOCKED")
        )

    try:
        j.wait_until(file_has_all, "the traced lines in trace.log", timeout=2)
    except TimeoutError:
        pass
    out["file-text"] = file_text()

    # The vJoy read-back agrees with what was written (before the check).
    written = trace.last_written(1, "axis", 1)
    out["last-written"] = written
    value = float(written[0]) if written else 0.0
    polled[_VIRTUAL] = int(round(value * 32767))

    # --- 3. Out-of-step check --------------------------------------------------
    from gremlin import trace_watch

    trace.set_oos(uid, True)
    out["watch-running"] = trace_watch.running()
    j.QTest.qWait(1500)
    out["oos-in-step"] = _with(_lines(trace), trace.OUT_OF_STEP)
    trace.clear_notice()
    # (a) the stick moved; no event came.
    polled[_PHYSICAL] = -16384
    try:
        j.wait_until(
            lambda: _with(_lines(trace), trace.OUT_OF_STEP, "Axis 1"),
            "a stick OUT OF STEP line", timeout=6,
        )
    except TimeoutError:
        pass
    j.QTest.qWait(2200)  # one line per episode
    out["oos-stick"] = _with(_lines(trace), trace.OUT_OF_STEP, "Axis 1")
    out["notice-stick"] = trace.notice()
    polled[_PHYSICAL] = 16384  # back in step
    # (b) vJoy reads back other than what was written.
    trace.clear_notice()
    polled[_VIRTUAL] = -29000
    held = j.vjoy.vjoy_devices.get(1)
    if held is not None:
        held.state[("axis", 1)] = -0.9
    try:
        j.wait_until(
            lambda: _with(_lines(trace), trace.OUT_OF_STEP, "vJoy 1"),
            "a vJoy OUT OF STEP line", timeout=6,
        )
    except TimeoutError:
        pass
    j.QTest.qWait(2200)
    out["oos-vjoy"] = _with(_lines(trace), trace.OUT_OF_STEP, "vJoy 1")
    out["notice-vjoy"] = trace.notice()
    trace.set_oos(uid, False)
    polled[_VIRTUAL] = int(round(value * 32767))
    if held is not None:
        held.state[("axis", 1)] = value

    # --- 4. HidHide (faked driver) ---------------------------------------------
    from gremlin import hidhide_watch

    period = 0.5  # the watch's 5 s, shortened for the test
    hidhide_watch.INTERVAL = period
    hidhide_watch._schedule.__defaults__ = (period,)
    trace.set_hidhide(True)

    def hh_lines(text: str) -> list[list]:
        return _with(_lines(trace), trace.HIDHIDE, "", text)

    try:
        j.wait_until(
            lambda: hh_lines("HidHide now"), "the first HidHide read", timeout=8
        )
    except TimeoutError:
        pass
    out["hh-first"] = hh_lines("HidHide now")
    out["hh-warnings-in-step"] = [
        ln for ln in _with(_lines(trace), trace.HIDHIDE) if ln[4]
    ]
    trace.clear_notice()
    hh["cloak"] = False  # turned off in the HidHide window
    try:
        j.wait_until(lambda: hh_lines("Cloak turned off"), "a cloak warning", timeout=8)
    except TimeoutError:
        pass
    j.QTest.qWait(int(period * 3000))
    out["hh-cloak"] = hh_lines("Cloak turned off")
    out["hh-notice"] = trace.notice()
    hh["devices"] = []  # the stick taken off the hidden list
    try:
        j.wait_until(lambda: hh_lines("NOT hidden"), "a not-hidden warning", timeout=8)
    except TimeoutError:
        pass
    j.QTest.qWait(int(period * 3000))
    out["hh-not-hidden"] = hh_lines("NOT hidden")
    hh["err"] = 5  # the HidHide window holds the driver
    j.QTest.qWait(int(period * 6000))
    out["hh-in-use"] = hh_lines("in use")
    hh["err"] = 0
    trace.set_hidhide(False)

    # --- 2. Unticked, then tracing off: no new lines --------------------------
    j.QTest.qWait(300)  # pending axis lines written
    trace.set_tick(uid, "button", 1, False)
    count = len(_lines(trace))
    j.press(stick, 1, False)
    j.press(stick, 1, True)
    j.press(stick, 1, False)
    j.QTest.qWait(300)
    out["after-untick"] = _lines(trace)[count:]

    trace.set_enabled(False)
    count = len(_lines(trace))
    size = trace.file_size()
    j.press(stick, 2, False)
    j.press(stick, 2, True)
    _axis_event(j, stick, 1, 0)
    j.QTest.qWait(300)
    out["after-off"] = _lines(trace)[count:]
    out["file-grew-while-off"] = trace.file_size() - size

    # Ticks kept; tracing left on at exit (the next start must be off).
    trace.set_tick(uid, "button", 1, True)
    trace.set_enabled(True)
    # Settings are written about a second after the last change (and on
    # quit, which os._exit skips here): wait until no write is waiting and
    # the file has these ticks.
    import json

    from gremlin import config as gconfig

    saved = pathlib.Path(gconfig._config_file_path)
    ticks_now = gconfig.Configuration().value(
        trace._CFG_SECTION, trace._CFG_GROUP, trace._CFG_TICKS
    )

    from gremlin import deferred_write

    def ticks_saved() -> bool:
        if deferred_write.pending("configuration"):
            return False
        try:
            data = json.loads(saved.read_text(encoding="utf-8"))
            group = data[trace._CFG_SECTION][trace._CFG_GROUP]
            return group[trace._CFG_TICKS]["value"] == ticks_now
        except (OSError, ValueError, KeyError, TypeError):
            return False

    try:
        j.wait_until(ticks_saved, "the ticks written to the settings", timeout=4)
    except TimeoutError:
        pass
    out["file-size-at-exit"] = trace.file_size()
    out["saved-ticks"] = '"trace"' in saved.read_text(encoding="utf-8") \
        if saved.exists() else None
    out["uid"] = str(uid)


def story_restart(j: Journey) -> None:
    from gremlin import trace

    out = j.out
    stick = j.stick()
    uid = stick.device_guid.uuid
    out["enabled-at-start"] = trace.enabled()
    ticks = trace.device_ticks(uid)
    out["ticks"] = {k: sorted(v) if isinstance(v, set) else v for k, v in ticks.items()}
    size = trace.file_size()
    j.press(stick, 1, True)
    j.press(stick, 1, False)
    j.QTest.qWait(300)
    out["lines"] = _lines(trace)
    out["file-grew"] = trace.file_size() - size
    out["file-size-at-start"] = size


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        claim = claim_everything()
        claim["buttons"] = [b for b in claim["buttons"] if b != 9]
        j.write_module(
            "vjoy_1",
            {"device": "vJoy 1", "direction": "dest", "claim": claim},
        )

    restart = len(sys.argv) > 1 and sys.argv[1] == "restart"
    Journey(before).run(story_restart if restart else story)


@pytest.fixture(scope="module")
def home(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    return tmp_path_factory.mktemp("trace_e2e")


@pytest.fixture(scope="module")
def run(home: pathlib.Path) -> dict:
    return run_journey(__file__, home)


@pytest.fixture(scope="module")
def restart(run: dict, home: pathlib.Path) -> dict:
    return run_journey(__file__, home, "restart")


def _pts(lines: list[list], control: str) -> list[str]:
    return [ln[2] for ln in lines if control in ln[1]]


def test_traced_controls_give_raw_wiring_output_lines(run: dict) -> None:
    assert step(run, "running") is True
    lines = step(run, "lines-on")
    for control in ("Axis 1", "Button 1"):
        points = _pts(lines, control)
        assert "RAW" in points, (control, lines)
        assert "WIRING" in points, (control, lines)
        assert "OUTPUT" in points, (control, lines)
    wiring = _with(lines, "WIRING", "Button 1")
    assert "Map to vJoy" in wiring[0][3], wiring
    out_b1 = _with(lines, "OUTPUT", "Button 1")
    assert any(
        "vJoy 1 Button 1" in ln[3] and "written" in ln[3] for ln in out_b1
    ), out_b1
    out_axis = _with(lines, "OUTPUT", "Axis 1")
    assert any("vJoy 1" in ln[3] and "written" in ln[3] for ln in out_axis), out_axis
    assert [ln[0] for ln in lines if ln[2] == "EVENT" and ln[3] == "Tracing on"]


def test_an_unclaimed_output_gives_a_blocked_line(run: dict) -> None:
    lines = step(run, "lines-on")
    blocked = _with(lines, "BLOCKED", "Button 2")
    assert blocked, lines
    assert "vJoy 1 Button 9" in blocked[0][3] and "blocked" in blocked[0][3], blocked
    assert not _with(lines, "OUTPUT", "Button 2"), lines


def test_the_trace_file_has_the_same_lines(run: dict) -> None:
    text = step(run, "file-text")
    assert text, "no trace.log after tracing was turned on"
    for point in ("RAW", "WIRING", "OUTPUT", "BLOCKED"):
        assert f"  {point}  " in text, (point, text)
    assert "Button 1" in text and "Axis 1" in text


def test_no_file_and_no_lines_until_tracing_is_on(run: dict) -> None:
    assert step(run, "file-at-start") is False
    assert step(run, "lines-before-on") == []
    assert step(run, "file-before-on") is False
    assert step(run, "file-after-on") is True


def test_out_of_step_stick_gives_one_line_and_the_notice(run: dict) -> None:
    assert step(run, "watch-running") is True, "the out-of-step watch isn't running"
    assert step(run, "oos-in-step") == []
    found = step(run, "oos-stick")
    assert len(found) == 1, found
    assert "polled" in found[0][3] and found[0][4] is True, found
    assert step(run, "notice-stick"), "no notice"


def test_out_of_step_vjoy_read_back_gives_one_line(run: dict) -> None:
    found = step(run, "oos-vjoy")
    assert len(found) == 1, found
    assert "last written" in found[0][3] and found[0][4] is True, found
    assert step(run, "notice-vjoy"), "no notice"


def test_hidhide_cloak_turned_off_outside_gives_one_warning(run: dict) -> None:
    assert step(run, "hh-first"), "the HidHide watch never read HidHide"
    assert step(run, "hh-warnings-in-step") == []
    found = step(run, "hh-cloak")
    assert len(found) == 1, found
    assert "not by Gremlin-Platforms" in found[0][3] and found[0][4] is True, found
    assert step(run, "hh-notice"), "no notice"


def test_hidhide_a_ticked_stick_not_hidden_gives_one_warning(run: dict) -> None:
    found = step(run, "hh-not-hidden")
    assert len(found) == 1, found
    assert "pJoy Pro" in found[0][3] and "VID_5678" in found[0][3], found


def test_hidhide_in_use_gives_one_line(run: dict) -> None:
    found = step(run, "hh-in-use")
    assert len(found) == 1, found


def test_an_unticked_control_adds_no_lines(run: dict) -> None:
    after = step(run, "after-untick")
    assert not [ln for ln in after if "Button 1" in ln[1]], after


def test_tracing_off_adds_no_lines_and_no_file_text(run: dict) -> None:
    assert step(run, "after-off") == []
    assert step(run, "file-grew-while-off") == 0


def test_a_new_start_has_tracing_off_and_keeps_the_ticks(
    run: dict, restart: dict
) -> None:
    assert step(run, "saved-ticks") is True, "the ticks were never written"
    assert step(restart, "enabled-at-start") is False
    ticks = step(restart, "ticks")
    assert ticks["axis"] == [1] and ticks["button"] == [1, 2], ticks
    assert step(restart, "lines") == []
    assert step(restart, "file-grew") == 0
    assert step(restart, "file-size-at-start") > 0


if __name__ == "__main__":
    main()
