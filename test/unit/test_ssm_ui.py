# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode's window (12 S1-S20): the Tools item in the bottom
group opens it; the switches and the two timers (Screen saver, Power off
displays: each a switch and a wait box, contract-4) save the settings and
hand them to the manager; the order warning; a countdown per timer and the
wake count (S20); the status line follows the manager's status
(with what last reset the idle time, S18, and the full-screen program, S19);
three sections, Devices, Programs and System, each with its own Refresh
button, fill their own lists (Programs and System each with their own
elevated check, split by power_requests.split); Ignore goes back when
Windows refuses. The Wake PC tab (S28-S31): only ticked keyboards and mice
count, every device starts unticked, a press ticks it while the tab is open,
nothing ticked shows the Waiting line. The core and the checks are stand-ins
(ssm_ui_fakes.py): nothing listens to the keyboard or mouse, reads HID
devices, runs powercfg or asks for administrator rights."""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ssm_ui_fakes  # noqa: E402

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_SMOKE = _HERE / "ssm_ui_smoke.py"


def _text(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


# The Tools item (S1) --------------------------------------------------------


def test_tools_item_sits_in_the_bottom_group_and_opens_the_window() -> None:
    main = _text("qml/Main.qml")
    tools = main[main.index('command: "tools.search"') :]
    tools = tools[: tools.index('title: qsTr("Debug")')]
    bottom = tools[tools.index("ThemedMenuSeparator") :]
    commands = re.findall(r'ThemedMenuItem \{ command: "([^"]+)" \}', bottom)
    assert commands == [
        "tools.oscMonitor",
        "tools.screenSaverMode",
        "tools.drivers",  # 06 S185
        "tools.history",
        "tools.options",
    ]
    js = _text("qml/main_commands.js")
    entry = js[js.index('id: "tools.screenSaverMode"') :]
    entry = entry[: entry.index("},")]
    assert 'text: "Screen Saver Mode…"' in entry
    assert 'group: "Tools"' in entry
    assert 'openTool("WindowScreenSaverMode.qml")' in entry
    assert (_ROOT / "qml" / "WindowScreenSaverMode.qml").exists()


def test_program_registers_applies_and_shuts_it_down() -> None:
    src = _text("joystick_gremlin.py")
    reg = src[src.index("def register_config_options") :]
    reg = reg[: reg.index("\ndef ")]
    assert "screen_saver_mode_model.register_options()" in reg
    main = src[src.index("def main()") :]
    assert main.index("screen_saver_mode_model.start()") < main.index("app.exec()")
    cleanup = src[src.index("def shutdown_cleanup") :]
    cleanup = cleanup[: cleanup.index("\ndef ")]
    assert "ssm.shutdown()" in cleanup


# The model, in this process ------------------------------------------------


@pytest.fixture
def fakes(qapp: object, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    from gremlin.config import Configuration
    from gremlin.ui import screen_saver_mode_model as m

    manager, calls = ssm_ui_fakes.install(monkeypatch)
    m.register_options()
    cfg = Configuration()
    before = {n: cfg.value(m.SECTION, m.GROUP, n) for n in m.NAMES}
    cfg.set(m.SECTION, m.GROUP, m.ENABLED, False)
    cfg.set(m.SECTION, m.GROUP, m.SAVER_ON, True)
    cfg.set(m.SECTION, m.GROUP, m.SAVER_WAIT, 0)
    cfg.set(m.SECTION, m.GROUP, m.OFF_ON, True)
    cfg.set(m.SECTION, m.GROUP, m.OFF_WAIT, 0)
    cfg.set(m.SECTION, m.GROUP, m.HOLD_FULLSCREEN, True)
    cfg.set(m.SECTION, m.GROUP, m.DEVICES, [])
    cfg.set(m.SECTION, m.GROUP, m.WAKE_PC, [])
    # The helper's state (S25, S26) starts fresh for each test.
    monkeypatch.setattr(m, "_helper_refused", False)
    monkeypatch.setattr(m, "_helper_starting", False)
    monkeypatch.setattr(m, "_off_timer_on", None)
    made: list = []

    def model():  # noqa: ANN202
        obj = m.ScreenSaverModeModel()
        made.append(obj)
        return obj

    yield manager, calls, model, m
    from gremlin.signal import signal

    for obj in made:
        obj.setOpen(False)
        obj.wakeTabOpen(False)
        try:
            signal.configChanged.disconnect(obj._on_config)
        except (RuntimeError, TypeError):
            pass
    for n, v in before.items():
        cfg.set(m.SECTION, m.GROUP, n, v)


def _wait(qapp: object, check, limit: float = 5.0) -> bool:  # noqa: ANN001
    import time

    from PySide6 import QtCore

    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20
        )
        if check():
            return True
    return False


def test_settings_are_registered_with_the_contract_defaults(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    _manager, _calls, _model, m = fakes
    cfg = Configuration()
    want = {
        "enabled": (PropertyType.Bool, False),
        "screen-saver-on": (PropertyType.Bool, True),
        "screen-saver-wait-s": (PropertyType.Int, 0),
        "power-off-on": (PropertyType.Bool, True),
        "power-off-wait-s": (PropertyType.Int, 0),
        "hold-fullscreen": (PropertyType.Bool, True),
        # S21: at most how long the displays wait for the devices.
        "devices-wait-s": (PropertyType.Int, 10),
        # S27: the saved Devices list.
        "devices": (PropertyType.List, []),
        # S28: the Wake PC list.
        "wake-pc": (PropertyType.List, []),
    }
    assert set(m.NAMES) == set(want)
    for name, (kind, _default) in want.items():
        assert cfg.exists("global", "screen-saver-mode", name)
        assert cfg.data_type("global", "screen-saver-mode", name) == kind
        assert cfg.description("global", "screen-saver-mode", name)
        # History records them (S10): only exposed settings are in its view.
        assert cfg.expose("global", "screen-saver-mode", name)


def test_history_names_them_as_the_window_does_and_options_leaves_them_out(
    qapp: object,
) -> None:
    from gremlin.config import settings_history_title
    from gremlin.ui import option

    keys = [
        f"global/screen-saver-mode/{n}"
        for n in (
            "enabled",
            "screen-saver-on",
            "screen-saver-wait-s",
            "power-off-on",
            "power-off-wait-s",
            "hold-fullscreen",
        )
    ]
    title = settings_history_title(keys)
    assert title == (
        "Changed Screen Saver Mode, Screen saver, Screen saver wait, "
        "Power off displays, Power off wait, "
        "Hold off during full-screen programs"
    ), title
    shown = {k for _s, groups in option.main_layout() for _g, ks in groups for k in ks}
    assert not any(k[1] == "screen-saver-mode" for k in shown)
    # Titles still read well for older entries; new changes are not recorded
    # at all (test_history_not_recorded.py).


# The saved Devices list, the helper and the device hooks (S21-S27) ---------

_SAVED_PAIRS = [
    ("PD200X Microphone (buttons)", "HID\\VID_1&PID_2\\1"),
    ("VKBSim NXT SEM THQ FSM.GA", "HID\\VID_3&PID_4\\1"),
]


def _refresh(model, qapp: object) -> None:  # noqa: ANN001
    model.refreshDevices()
    assert _wait(qapp, lambda: not model.property("scanningDevices"))


def _fill_saved(m) -> None:  # noqa: ANN001
    from gremlin.config import Configuration
    from gremlin.device_key import device_key

    Configuration().set(
        m.SECTION,
        m.GROUP,
        m.DEVICES,
        [
            {
                "key": device_key(n, i),
                "name": n,
                "instance_ids": [i],
                "rate": 1.0,
                "choice": "automatic",
                "virtual": False,
                "last_seen": "2026-11-24T16:27:00",
            }
            for n, i in _SAVED_PAIRS
        ],
    )


def test_s27_the_saved_list_is_hidden_in_options_and_named_in_history(
    qapp: object,
) -> None:
    from gremlin.config import settings_history_title
    from gremlin.ui import option

    assert ("global", "screen-saver-mode", "devices") in option._HIDDEN  # noqa: SLF001
    title = settings_history_title(["global/screen-saver-mode/devices"])
    assert title == "Changed Saved Devices list", title


def test_s27_refresh_devices_is_saved_and_fills_the_list_after_a_restart(
    fakes: tuple,
    qapp: object,  # noqa: ANN001
) -> None:
    from gremlin.config import Configuration

    _manager, _calls, model, m = fakes
    first = model()
    assert first.property("devices") == []
    _refresh(first, qapp)
    stored = Configuration().value(m.SECTION, m.GROUP, m.DEVICES)
    assert [(d["name"], *d["instance_ids"]) for d in stored] == _SAVED_PAIRS
    # A new window model (the program's next start; the real restart is
    # in test_ssm_e2e) shows it.
    again = model()
    assert [(d["name"], d["choice"]) for d in again.property("devices")] == [
        (n, "automatic") for n, _i in _SAVED_PAIRS
    ]
    assert again.property("devicesSummary") == "2 automatic"
    assert again.property("devicesMessage") == ""


def test_s27_a_failed_refresh_keeps_the_saved_list(fakes, qapp: object) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    _fill_saved(m)

    def broken(*_a: object, **_k: object) -> list:
        raise OSError("no HID")

    import gremlin

    gremlin.hid_report_scan.scan = broken  # type: ignore[attr-defined]
    ssm = model()
    _refresh(ssm, qapp)
    assert m._saved_pairs() == _SAVED_PAIRS  # noqa: SLF001


@pytest.mark.parametrize(
    ("enabled", "off_on", "filled", "starts"),
    [
        (True, True, True, 1),
        (False, True, True, 0),
        (True, False, True, 0),
        (True, True, False, 0),
    ],
)
def test_s25_the_helper_starts_only_when_mode_power_off_and_list(
    fakes: tuple,
    enabled: bool,
    off_on: bool,
    filled: bool,
    starts: int,  # noqa: ANN001
) -> None:
    from gremlin.config import Configuration

    _manager, calls, _model, m = fakes
    cfg = Configuration()
    cfg.set(m.SECTION, m.GROUP, m.ENABLED, enabled)
    cfg.set(m.SECTION, m.GROUP, m.OFF_ON, off_on)
    if filled:
        _fill_saved(m)
    m.start()
    try:
        assert calls.disabler.starts == starts
        # Running: not started again.
        m.ensure_helper()
        assert calls.disabler.starts == starts
    finally:
        m.shutdown()


def test_s25_switching_on_and_a_filling_refresh_start_the_helper(
    fakes: tuple,
    qapp: object,  # noqa: ANN001
) -> None:
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp)
    assert calls.disabler.starts == 0  # the mode is off
    ssm.setEnabled(True)
    assert calls.disabler.starts == 1
    calls.disabler.running = False
    ssm.setOffOn(False)
    assert calls.disabler.starts == 1
    ssm.setOffOn(True)
    assert calls.disabler.starts == 2
    # A Refresh that fills the list (mode and Power off on) starts it too.
    from gremlin.config import Configuration

    calls.disabler.running = False
    Configuration().set(m.SECTION, m.GROUP, m.DEVICES, [])
    _refresh(ssm, qapp)
    assert calls.disabler.starts == 3


def test_s25_s26_after_a_refusal_not_again_until_try_again(fakes) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    calls.disabler.answer = (False, "The confirmation was declined.")
    _fill_saved(m)
    ssm = model()
    ssm.setEnabled(True)
    assert calls.disabler.starts == 1
    ssm.refreshStatus()
    assert ssm.property("helperMessage") == (
        "Devices can't be disabled: the helper isn't running"
    )
    # Settings changes don't ask again.
    ssm.setOffOn(False)
    ssm.setOffOn(True)
    m.ensure_helper()
    assert calls.disabler.starts == 1
    # Try again asks once more; accepted, the message goes.
    calls.disabler.answer = (True, "")
    ssm.tryAgain()
    assert calls.disabler.starts == 2
    assert ssm.property("helperMessage") == ""


def test_s26_message_only_when_the_helper_should_run_and_doesnt(fakes) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    calls.disabler.hold = True  # the user still at the confirmation
    ssm = model()
    ssm.refreshStatus()
    assert ssm.property("helperMessage") == ""  # not wanted: mode off
    _fill_saved(m)
    ssm.setEnabled(True)
    ssm.refreshStatus()
    assert ssm.property("helperMessage") == ""  # being started
    calls.disabler.finish(False, "declined")
    ssm.refreshStatus()
    assert ssm.property("helperMessage") == (
        "Devices can't be disabled: the helper isn't running"
    )
    ssm.setEnabled(False)
    ssm.refreshStatus()
    assert ssm.property("helperMessage") == ""


def test_s21_s23_hooks_disable_the_saved_list_and_enable_on_input(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    manager, calls, _model, m = fakes
    Configuration().set(m.SECTION, m.GROUP, m.ENABLED, True)
    m.start()
    try:
        assert manager.before_power_off is not None
        assert manager.after_input is not None
        # Empty list: nothing to disable (S27).
        calls.disabler.running = True
        assert manager.before_power_off() is None
        assert calls.disabler.disabled == []
        _fill_saved(m)
        # Helper not running: nothing disabled (S26).
        calls.disabler.running = False
        assert manager.before_power_off() is None
        assert calls.disabler.disabled == []
        calls.disabler.running = True
        calls.disabler.idle = False
        wait = manager.before_power_off()
        assert calls.disabler.disabled == [_SAVED_PAIRS]
        # S21: the core waits on the probe until the disabler is idle.
        count, pending = wait
        assert count == len(_SAVED_PAIRS) and pending() is True
        calls.disabler.idle = True
        assert pending() is False
        manager.after_input()
        assert calls.disabler.enables == 1
    finally:
        m.shutdown()
    assert manager.before_power_off is None and manager.after_input is None


def test_s23_a_device_plugged_in_retries(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,  # noqa: ANN001
) -> None:
    from PySide6 import QtCore

    _manager, calls, _model, m = fakes

    class Listener(QtCore.QObject):
        device_change_event = QtCore.Signal()

    listener = Listener()
    from gremlin import event_handler

    monkeypatch.setattr(event_handler, "EventListener", lambda: listener)
    monkeypatch.setattr(m, "_arrival_signal", None)
    m.start()
    try:
        listener.device_change_event.emit()
        assert calls.disabler.arrivals == 1
    finally:
        m.shutdown()
    listener.device_change_event.emit()
    assert calls.disabler.arrivals == 1


def test_s23_switching_the_mode_or_power_off_off_enables_pending(fakes) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    ssm.setEnabled(True)
    assert calls.disabler.enables == 0
    ssm.setEnabled(False)
    assert calls.disabler.enables == 1
    ssm.setEnabled(True)
    ssm.setOffOn(False)
    assert calls.disabler.enables == 2
    # Already off: no more.
    ssm.setSaverOn(False)
    assert calls.disabler.enables == 2


def test_s24_s25_program_recovers_at_start_and_stops_the_helper_at_quit() -> None:
    src = _text("joystick_gremlin.py")
    init = src[src.index("        register_config_options()\n") :]
    assert init.index("_recover_devices()") < init.index("self.engine.load(")
    rec = src[src.index("def _recover_devices") :]
    rec = rec[: rec.index("\ndef ")]
    assert "device_disable.manager().recover_at_start()" in rec
    cleanup = src[src.index("def shutdown_cleanup") :]
    cleanup = cleanup[: cleanup.index("\ndef ")]
    assert "stop_helper()" in cleanup


def test_switching_and_choosing_write_the_settings_and_apply_them(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    manager, _calls, model, m = fakes
    cfg = Configuration()
    ssm = model()
    assert ssm.property("enabled") is False
    assert ssm.property("saverOn") is True and ssm.property("offOn") is True
    ssm.setEnabled(True)
    assert cfg.value(m.SECTION, m.GROUP, m.ENABLED) is True
    assert manager.settings().enabled is True
    ssm.setSaverOn(False)
    assert cfg.value(m.SECTION, m.GROUP, m.SAVER_ON) is False
    assert manager.settings().screen_saver_on is False
    assert manager.settings().power_off_on is True
    ssm.setOffOn(False)
    assert cfg.value(m.SECTION, m.GROUP, m.OFF_ON) is False
    assert manager.settings().power_off_on is False
    ssm.setSaverOn(True)
    assert manager.settings().screen_saver_on is True
    ssm.setHoldFullscreen(False)
    assert cfg.value(m.SECTION, m.GROUP, m.HOLD_FULLSCREEN) is False
    assert manager.settings().hold_fullscreen is False
    ssm.setEnabled(False)
    assert manager.settings().enabled is False
    assert cfg.value(m.SECTION, m.GROUP, m.ENABLED) is False


@pytest.mark.parametrize(
    ("row", "setting", "field", "windows"),
    [
        ("saver", "SAVER_WAIT", "screen_saver_wait_s", "SAVER_WINDOWS_S"),
        ("off", "OFF_WAIT", "power_off_wait_s", "OFF_WINDOWS_S"),
    ],
)
def test_each_wait_box_shows_windows_time_and_a_typed_time_overrides(
    fakes: tuple, row: str, setting: str, field: str, windows: str
) -> None:
    """S5 per timer: each row's box shows Windows' time greyed, a typed time
    overrides only that row until cleared."""
    from gremlin.config import Configuration

    manager, _calls, model, m = fakes
    key = getattr(m, setting)
    other = m.OFF_WAIT if row == "saver" else m.SAVER_WAIT
    cap = "Saver" if row == "saver" else "Off"
    cfg = Configuration()
    ssm = model()
    ssm.refreshStatus()
    assert ssm.property(f"{row}WaitText") == ""
    assert ssm.property("saverWindowsWaitText") == "10 min"
    assert (
        ssm.property("saverWindowsWaitLabel") == "Windows' screen saver wait (10 min)"
    )
    assert ssm.property("offWindowsWaitText") == "5 min"
    assert ssm.property("offWindowsWaitLabel") == "Windows' display-off time (5 min)"
    assert getattr(ssm, f"set{cap}WaitText")("12") is True
    assert cfg.value(m.SECTION, m.GROUP, key) == 720
    assert getattr(manager.settings(), field) == 720
    assert cfg.value(m.SECTION, m.GROUP, other) == 0
    assert ssm.property(f"{row}WaitText") == "12"
    assert getattr(ssm, f"set{cap}WaitText")("2.5 min") is True
    assert cfg.value(m.SECTION, m.GROUP, key) == 150
    for bad in ("abc", "0", "-3", "5000"):
        assert getattr(ssm, f"set{cap}WaitText")(bad) is False, bad
        assert cfg.value(m.SECTION, m.GROUP, key) == 150
    getattr(ssm, f"clear{cap}Wait")()
    assert cfg.value(m.SECTION, m.GROUP, key) == 0
    assert getattr(manager.settings(), field) == 0
    assert ssm.property(f"{row}WaitText") == ""
    # Windows says never: the box says so.
    setattr(manager, windows, 0)
    ssm.refreshStatus()
    assert ssm.property(f"{row}WindowsWaitText") == "Never"


def test_order_warning_when_power_off_comes_first(fakes: tuple) -> None:
    """Contract-4: both on and the power off wait not longer than the
    screen saver's: the window warns (both still work)."""
    manager, _calls, model, _m = fakes
    warning = (
        "Power off comes at or before the screen saver: the screen saver won't show."
    )
    ssm = model()
    ssm.refreshStatus()
    # Windows' times: screen saver 10 min, display off 5 min.
    assert ssm.property("orderWarning") == warning
    ssm.setOffWaitText("15")
    assert ssm.property("orderWarning") == ""
    ssm.setSaverWaitText("15")  # equal: still first
    assert ssm.property("orderWarning") == warning
    ssm.setSaverWaitText("2")
    assert ssm.property("orderWarning") == ""
    ssm.clearSaverWait()
    ssm.clearOffWait()
    assert ssm.property("orderWarning") == warning
    ssm.setSaverOn(False)
    assert ssm.property("orderWarning") == ""
    ssm.setSaverOn(True)
    ssm.setOffOn(False)
    assert ssm.property("orderWarning") == ""
    ssm.setOffOn(True)
    # Windows never starts the screen saver: nothing to come before.
    manager.SAVER_WINDOWS_S = 0
    ssm.refreshStatus()
    assert ssm.property("orderWarning") == ""


def test_history_restore_is_followed_by_the_manager(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration
    from gremlin.signal import signal

    manager, _calls, _model, m = fakes
    m.start()
    try:
        Configuration().set(m.SECTION, m.GROUP, m.ENABLED, True)
        signal.configChanged.emit()
        assert manager.settings().enabled is True
    finally:
        m.shutdown()
    assert manager.shut is True


@pytest.mark.parametrize(
    ("extra", "field", "want"),
    [
        (
            {"hold": "display_request", "hold_program": ""},
            "holdText",
            "On hold: a program is keeping the display on. "
            "The countdown starts again when it stops.",
        ),
        (
            {"hold": "fullscreen"},
            "holdText",
            "On hold: a full-screen program is in front. "
            "The countdown starts again when it ends.",
        ),
        # S19: the full-screen hold names the program when Windows gives it.
        (
            {"hold": "fullscreen", "hold_program": "StarCitizen.exe"},
            "holdText",
            "On hold: a full-screen program is in front (StarCitizen.exe). "
            "The countdown starts again when it ends.",
        ),
        # S18: what last reset the idle time; nothing before the first input.
        ({}, "lastResetText", ""),
        (
            {"last_reset_kind": "program", "program_input_per_min": 8},
            "lastResetText",
            "last reset by: input sent by a program, 8 times a minute",
        ),
        (
            {"last_reset_kind": "program", "program_input_per_min": 1},
            "lastResetText",
            "last reset by: input sent by a program, once a minute",
        ),
        (
            {
                "last_reset_kind": "program",
                "program_input_per_min": 0,
                "last_reset_age_s": 75.0,
            },
            "lastResetText",
            "last reset by: input sent by a program, 1 min 15 s ago",
        ),
        (
            {
                "last_reset_kind": "keyboard",
                "last_reset_by": "Logitech G915",
                "last_reset_age_s": 0.4,
            },
            "lastResetText",
            "last reset by: Logitech G915 (keyboard), just now",
        ),
        (
            {
                "last_reset_kind": "mouse",
                "last_reset_by": "Razer Basilisk",
                "last_reset_age_s": 42.0,
            },
            "lastResetText",
            "last reset by: Razer Basilisk (mouse), 42 s ago",
        ),
        (
            {"last_reset_kind": "mouse", "last_reset_age_s": 5.0},
            "lastResetText",
            "last reset by: a mouse, 5 s ago",
        ),
        # Per row (S5, S8): the screen saver row's and the power off row's.
        (
            {"saver_problem": "no_screen_saver"},
            "saverProblemText",
            "No screen saver is chosen in Windows.",
        ),
        ({"saver_problem": "no_screen_saver"}, "offProblemText", ""),
        (
            {"saver_problem": "windows_never"},
            "saverProblemText",
            "Windows never starts the screen saver: type a time to use this timer.",
        ),
        (
            {"off_problem": "windows_never"},
            "offProblemText",
            "Windows never turns the display off: type a time to use this timer.",
        ),
        ({"off_problem": "windows_never"}, "saverProblemText", ""),
        # A row's problem stops only its own countdown.
        (
            {"off_problem": "windows_never", "saver_remaining_s": 80.0},
            "saverCountdownText",
            "Screen saver in 1 min 20 s",
        ),
        (
            {"off_problem": "windows_never", "off_remaining_s": 80.0},
            "offCountdownText",
            "",
        ),
        (
            {"problem": "not_listening"},
            "problemText",
            "The keyboard and mouse can't be listened to, so Screen Saver Mode "
            "does nothing.",
        ),
        (
            {"problem": "not_listening", "listening": False},
            "listeningText",
            "Not listening to the keyboard and mouse",
        ),
        # S6: a countdown per timer, then done.
        (
            {"saver_remaining_s": 80.0, "off_remaining_s": 200.0},
            "saverCountdownText",
            "Screen saver in 1 min 20 s",
        ),
        (
            {"saver_remaining_s": 80.0, "off_remaining_s": 200.0},
            "offCountdownText",
            "Power off displays in 3 min 20 s",
        ),
        (
            {"saver_fired": True, "off_remaining_s": 120.0},
            "saverCountdownText",
            "Screen saver done. Nothing more until the keyboard or mouse is used.",
        ),
        (
            {"off_fired": True},
            "offCountdownText",
            "Power off displays done. "
            "Nothing more until the keyboard or mouse is used.",
        ),
        # A hold holds both.
        (
            {"hold": "fullscreen", "saver_remaining_s": 80.0},
            "saverCountdownText",
            "",
        ),
        (
            {"hold": "fullscreen", "off_remaining_s": 80.0},
            "offCountdownText",
            "",
        ),
        # S20: the wake count, while keeping the displays off and after.
        ({"keeping_off": True, "wakes": 0}, "wakeText", ""),
        (
            {"keeping_off": True, "off_fired": True, "wakes": 136},
            "wakeText",
            "Windows turned the displays back on 136 times: devices that never "
            "go quiet (see Refresh Devices).",
        ),
        (
            {"keeping_off": False, "wakes": 1},
            "wakeText",
            "Windows turned the displays back on once: devices that never "
            "go quiet (see Refresh Devices).",
        ),
        (
            {"idle_s": 161.0, "windows_idle_s": 0.0},
            "windowsIdleText",
            "Windows' idle time: 0 s · devices are keeping Windows awake",
        ),
        ({"idle_s": 161.0}, "idleText", "Your idle time: 2 min 41 s"),
    ],
)
def test_status_texts_follow_the_manager(
    fakes: tuple, extra: dict, field: str, want: str
) -> None:  # noqa: ANN001
    manager, _calls, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    manager.extra = dict(extra)
    ssm.refreshStatus()
    assert ssm.property(field) == want


def test_status_is_polled_once_a_second_only_while_open(fakes, qapp: object) -> None:  # noqa: ANN001
    manager, _calls, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    ssm.setOpen(True)
    manager.extra = {"idle_s": 75.0}
    assert _wait(
        qapp, lambda: ssm.property("idleText") == "Your idle time: 1 min 15 s", 3.0
    )
    ssm.setOpen(False)
    manager.extra = {"idle_s": 5.0}
    assert not _wait(
        qapp, lambda: ssm.property("idleText") == "Your idle time: 5 s", 1.6
    )


def test_refresh_devices_calls_the_scan_and_fills_the_list(fakes, qapp: object) -> None:  # noqa: ANN001
    _manager, calls, model, _m = fakes
    ssm = model()
    assert ssm.property("devices") == []
    ssm.refreshDevices()
    assert ssm.property("scanningDevices") is True
    assert _wait(qapp, lambda: not ssm.property("scanningDevices"))
    assert calls.scans == [4.0]
    rows = ssm.property("devices")
    assert [r["name"] for r in rows] == [
        "PD200X Microphone (buttons)",
        "VKBSim NXT SEM THQ FSM.GA",
    ]
    assert round(rows[0]["rate"]) == 18
    assert re.fullmatch(r"Checked \d\d:\d\d · 2 found", ssm.property("devicesMessage"))


def test_refresh_programs_and_ignore_goes_back_on_failure(fakes, qapp: object) -> None:  # noqa: ANN001
    _manager, calls, model, _m = fakes
    ssm = model()
    ssm.refreshPrograms()
    assert _wait(qapp, lambda: not ssm.property("scanningPrograms"))
    assert calls.lists == 1
    # Only the Display half (S13): the System list is left alone.
    assert [
        (r["name"], r["kinds"], r["ignored"], r["alsoAwake"])
        for r in ssm.property("programs")
    ] == [
        ("RustDesk.exe", "Display, System", False, True),
        ("chrome.exe", "Display", True, False),
    ]
    assert ssm.property("system") == [] and ssm.property("systemMessage") == ""
    assert "ignored programs no longer keep the display on." in ssm.property(
        "programsMessage"
    )
    seen: list[bool] = []
    ssm.programsChanged.connect(lambda: seen.append(True))
    calls.ignore_answer = (False, "Administrator rights were refused.")
    ssm.setIgnored("RustDesk.exe", True)
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert calls.ignores == [("RustDesk.exe", True, "PROCESS")]
    assert ssm.isIgnored("RustDesk.exe") is False and seen
    assert ssm.property("programsMessage") == "Administrator rights were refused."
    calls.ignore_answer = (True, "")
    ssm.setIgnored("RustDesk.exe", True)
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert ssm.property("programsMessage") == (
        "RustDesk.exe is ignored: it no longer keeps the display on."
    )
    ssm.setIgnored("chrome.exe", False)
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert ssm.isIgnored("chrome.exe") is False
    assert ssm.property("programsMessage") == "chrome.exe is no longer ignored."
    # Refused list: says so, the old list stays.
    calls.requests = ssm_ui_fakes.RequestsResult(
        False, "Administrator rights were refused.", []
    )
    ssm.refreshPrograms()
    assert _wait(qapp, lambda: not ssm.property("scanningPrograms"))
    assert len(ssm.property("programs")) == 2
    assert ssm.property("programsMessage") == "Administrator rights were refused."


def test_refresh_system_runs_its_own_check_and_fills_only_its_list(
    fakes: tuple, qapp: object
) -> None:  # noqa: ANN001
    """S17 (contract-3, user 3 a): Refresh System runs its own
    list_requests() (its own administrator prompt) and keeps the System
    half: callers without Display, and ignored callers not asking now whose
    override types have no DISPLAY. The Programs list is left alone."""
    _manager, calls, model, _m = fakes
    ssm = model()
    ssm.refreshSystem()
    assert ssm.property("scanningSystem") is True
    assert ssm.property("scanningPrograms") is False
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    assert calls.lists == 1
    assert [(r["name"], r["kind"], r["ignored"]) for r in ssm.property("system")] == [
        ("claude.exe", "PROCESS", False),
        (ssm_ui_fakes.DRIVER_NAME, "DRIVER", False),
        ("FxSound Audio Enhancer", "DRIVER", True),
    ]
    assert ssm.property("programs") == [] and ssm.property("programsMessage") == ""
    assert "ignored ones no longer keep the PC awake." in ssm.property("systemMessage")
    # Then Refresh Programs: a second, separate check; System stays.
    ssm.refreshPrograms()
    assert _wait(qapp, lambda: not ssm.property("scanningPrograms"))
    assert calls.lists == 2
    assert len(ssm.property("system")) == 3
    assert [r["name"] for r in ssm.property("programs")] == [
        "RustDesk.exe",
        "chrome.exe",
    ]
    # An ignored caller not asking now with DISPLAY goes in Programs.
    calls.requests = ssm_ui_fakes.RequestsResult(
        True,
        "",
        [
            ssm_ui_fakes.ProgramRequest(
                "vlc.exe", "", [], True, override_types=["DISPLAY", "SYSTEM"]
            )
        ],
    )
    ssm.refreshSystem()
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    assert ssm.property("system") == []
    assert "Nothing is asking Windows to keep the PC awake." in ssm.property(
        "systemMessage"
    )
    ssm.refreshPrograms()
    assert _wait(qapp, lambda: not ssm.property("scanningPrograms"))
    assert [r["name"] for r in ssm.property("programs")] == ["vlc.exe"]
    # Refused: said in the System section only.
    calls.requests = ssm_ui_fakes.RequestsResult(
        False, "Administrator rights were refused.", []
    )
    ssm.refreshSystem()
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    assert ssm.property("systemMessage") == "Administrator rights were refused."
    assert ssm.property("programsMessage") != "Administrator rights were refused."


def test_driver_rows_show_their_kind_and_detail_and_can_be_ignored(
    fakes: tuple, qapp: object
) -> None:  # noqa: ANN001
    """S14 widened (user, 28 a): a driver's row (in System now, S17) has
    the switch and passes its kind on; its message says the PC."""
    _manager, calls, model, _m = fakes
    ssm = model()
    ssm.refreshSystem()
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    rows = ssm.property("system")
    assert [(r["kind"], r["kindWord"], r["detail"]) for r in rows] == [
        ("PROCESS", "", "Electron"),
        ("DRIVER", "driver", ssm_ui_fakes.DRIVER_DETAIL),
        ("DRIVER", "driver", ""),
    ]
    seen: list[str] = []
    ssm.systemChanged.connect(lambda: seen.append("system"))
    ssm.programsChanged.connect(lambda: seen.append("programs"))
    ssm.setIgnored(ssm_ui_fakes.DRIVER_NAME, True, "DRIVER")
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert calls.ignores == [(ssm_ui_fakes.DRIVER_NAME, True, "DRIVER")]
    assert ssm.isIgnored(ssm_ui_fakes.DRIVER_NAME, "DRIVER") is True
    assert ssm.property("systemMessage") == (
        f"{ssm_ui_fakes.DRIVER_NAME} is ignored: it no longer keeps the PC awake."
    )
    assert ssm.property("programsMessage") == ""
    assert seen == ["system"]
    ssm.setIgnored("FxSound Audio Enhancer", False, "DRIVER")
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert ssm.property("systemMessage") == (
        "FxSound Audio Enhancer is no longer ignored."
    )
    # A service row is the same (the form is not verified on a real PC).
    calls.requests = ssm_ui_fakes.RequestsResult(
        True,
        "",
        [ssm_ui_fakes.ProgramRequest("Spooler", "", ["System"], False, kind="SERVICE")],
    )
    ssm.refreshSystem()
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    assert ssm.property("system")[0]["kindWord"] == "service"
    ssm.setIgnored("Spooler", True, "SERVICE")
    assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert calls.ignores[-1] == ("Spooler", True, "SERVICE")


def test_windows_time_shows_while_screen_saver_mode_is_off(fakes: tuple) -> None:
    """S5: with Screen Saver Mode off, status() carries Windows' wait (the
    core's 'never' fix), and the window shows it greyed: 5 min, not never."""
    manager, _calls, model, _m = fakes
    ssm = model()
    manager.extra = {
        "enabled": False,
        "listening": False,
        "off_windows_wait_s": 300,
        "saver_windows_wait_s": 420,
    }
    ssm.refreshStatus()
    assert ssm.property("enabled") is False
    assert ssm.property("offWaitText") == "" and ssm.property("saverWaitText") == ""
    assert ssm.property("offWindowsWaitText") == "5 min"
    assert ssm.property("offWindowsWaitLabel") == "Windows' display-off time (5 min)"
    assert ssm.property("saverWindowsWaitText") == "7 min"
    assert ssm.property("saverWindowsWaitLabel") == "Windows' screen saver wait (7 min)"
    # Off: no countdown, no wake count.
    manager.extra["off_remaining_s"] = 60.0
    manager.extra["wakes"] = 3
    ssm.refreshStatus()
    assert ssm.property("offCountdownText") == "" and ssm.property("wakeText") == ""
    manager.extra = {"enabled": False, "off_windows_wait_s": 0}
    ssm.refreshStatus()
    assert ssm.property("offWindowsWaitText") == "Never"


def test_presses_and_messages_are_traced_and_failures_logged(
    fakes: tuple,
    qapp: object,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:  # noqa: ANN001
    """S16: button presses (with name and kind for Ignore) and every message
    shown go to the Screen Saver Mode trace; failures also to the normal log
    even with tracing off."""
    import logging

    from gremlin import trace

    _manager, calls, model, _m = fakes
    lines: list[str] = []
    monkeypatch.setattr(trace, "screen_saver", lines.append, raising=False)
    ssm = model()
    ssm.refreshDevices()
    assert _wait(qapp, lambda: not ssm.property("scanningDevices"))
    ssm.refreshPrograms()
    assert _wait(qapp, lambda: not ssm.property("scanningPrograms"))
    ssm.refreshSystem()
    assert _wait(qapp, lambda: not ssm.property("scanningSystem"))
    calls.ignore_answer = (False, "Administrator rights were refused.")
    with caplog.at_level(logging.WARNING, logger="system"):
        ssm.setIgnored(ssm_ui_fakes.DRIVER_NAME, True, "DRIVER")
        assert _wait(qapp, lambda: not ssm.property("pendingIgnore"))
    assert lines[0] == "Refresh Devices pressed"
    assert lines[1].startswith("Message shown: Checked ")
    assert "Refresh Programs pressed" in lines
    assert "Refresh System pressed" in lines
    assert lines.index("Refresh System pressed") > lines.index(
        "Refresh Programs pressed"
    )
    assert f"Ignore on pressed: {ssm_ui_fakes.DRIVER_NAME} (DRIVER)" in lines
    assert lines[-1] == "Message shown: Administrator rights were refused."
    assert any(
        "failed: Administrator rights were refused." in r.getMessage()
        and ssm_ui_fakes.DRIVER_NAME in r.getMessage()
        for r in caplog.records
    )
    # A problem shown in the window is traced once, when it appears.
    ssm.setEnabled(True)
    _manager.extra = {"saver_problem": "no_screen_saver", "wakes": 4}
    ssm.refreshStatus()
    ssm.refreshStatus()
    assert lines.count("Message shown: No screen saver is chosen in Windows.") == 1
    assert (
        sum(ln.startswith("Message shown: Windows turned the displays") for ln in lines)
        == 1
    )


# Wake PC (S28-S31) -----------------------------------------------------------

_G815 = ssm_ui_fakes.INPUT_DEVICES[0].physical_id
_STEAM = ssm_ui_fakes.INPUT_DEVICES[1].physical_id
_GONE = r"USB\VID_1234&PID_0001\9"


def _saved_wake(m) -> list:  # noqa: ANN001
    from gremlin.config import Configuration

    return list(Configuration().value(m.SECTION, m.GROUP, m.WAKE_PC) or [])


def _set_wake(m, rows: list) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    Configuration().set(m.SECTION, m.GROUP, m.WAKE_PC, rows)


def _open_wake(model, calls, qapp: object) -> None:  # noqa: ANN001
    reads = len(calls.input_reads)
    model.wakeTabOpen(True)
    assert _wait(
        qapp,
        lambda: len(calls.input_reads) > reads and not model._reading_inputs,  # noqa: SLF001
    )


def _rows(model) -> list[dict]:  # noqa: ANN001
    return [dict(r) for r in model.property("wakeRows")]


def test_s28_wake_pc_list_is_hidden_in_options_and_named_in_history(
    qapp: object,
) -> None:
    from gremlin.config import settings_history_title
    from gremlin.ui import option

    assert ("global", "screen-saver-mode", "wake-pc") in option._HIDDEN  # noqa: SLF001
    title = settings_history_title(["global/screen-saver-mode/wake-pc"])
    assert title == "Changed Wake PC list", title


def test_s28_apply_saved_hands_only_the_ticked_ids_to_the_core(fakes) -> None:  # noqa: ANN001
    manager, _calls, _model, m = fakes
    _set_wake(
        m,
        [
            {
                "id": _G815,
                "name": "G815",
                "kinds": ["keyboard"],
                "ticked": True,
                "how": "you",
            },
            {
                "id": _STEAM,
                "name": "Steam",
                "kinds": ["mouse"],
                "ticked": False,
                "how": "untick",
            },
            {
                "id": _GONE,
                "name": "Old",
                "kinds": ["mouse"],
                "ticked": True,
                "how": "click",
            },
        ],
    )
    manager.wake_sets.clear()
    m.apply_saved()
    assert manager.wake_sets == [[_G815, _GONE]]
    # Nothing ticked: an empty set (the core holds, S31).
    _set_wake(m, [])
    m.apply_saved()
    assert manager.wake_sets[-1] == []


def test_s28_s29_rows_merge_saved_with_found_read_off_the_main_thread(
    fakes: tuple,
    qapp: object,
) -> None:
    import threading

    _manager, calls, model, m = fakes
    _set_wake(
        m,
        [
            {
                "id": _GONE,
                "name": "Old Mouse",
                "kinds": ["mouse"],
                "ticked": True,
                "how": "click",
            }
        ],
    )
    ssm = model()
    # Before the tab opens nothing is read; the saved row shows.
    assert calls.input_reads == []
    assert [r["id"] for r in _rows(ssm)] == [_GONE]
    _open_wake(ssm, calls, qapp)
    main = threading.current_thread().name
    assert calls.input_reads and main not in calls.input_reads
    rows = _rows(ssm)
    assert rows == [
        {
            "id": _G815,
            "name": "Logitech G815",
            "kinds": "keyboard",
            "ticked": False,
            "note": "",
            "connected": True,
            "inUse": False,
        },
        {
            "id": _STEAM,
            "name": "Steam Controller",
            "kinds": "keyboard, mouse",
            "ticked": False,
            "note": "",
            "connected": True,
            "inUse": False,
        },
        # S28: unplugged, its tick kept.
        {
            "id": _GONE,
            "name": "Old Mouse",
            "kinds": "mouse",
            "ticked": True,
            "note": "ticked when you clicked",
            "connected": False,
            "inUse": False,
        },
    ]
    # S29: new devices are not saved as ticked; the saved list is unchanged.
    assert [r["id"] for r in _saved_wake(m)] == [_GONE]


def test_s30_detection_runs_only_while_the_tab_is_open(fakes, qapp: object) -> None:  # noqa: ANN001
    manager, calls, model, _m = fakes
    ssm = model()
    ssm.setOpen(True)
    assert manager.detection == [] and manager.press_listener is None
    _open_wake(ssm, calls, qapp)
    assert manager.detection == ["start"] and manager.press_listener is not None
    ssm.wakeTabOpen(True)
    assert manager.detection == ["start"]
    ssm.wakeTabOpen(False)
    assert manager.detection == ["start", "stop"] and manager.press_listener is None
    # Closing the window with the tab open stops it too.
    _open_wake(ssm, calls, qapp)
    ssm.setOpen(False)
    assert manager.detection[-1] == "stop" and manager.press_listener is None


def test_s30_a_press_ticks_says_how_saves_and_reaches_the_core(
    fakes: tuple,
    qapp: object,
) -> None:
    manager, calls, model, m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    manager.wake_sets.clear()
    manager.press(_G815, "keyboard")
    manager.press(_STEAM, "mouse")
    notes = {r["id"]: (r["ticked"], r["note"]) for r in _rows(ssm)}
    assert notes == {
        _G815: (True, "ticked when you pressed a key"),
        _STEAM: (True, "ticked when you clicked"),
    }
    saved = {r["id"]: (r["ticked"], r["how"], r["name"]) for r in _saved_wake(m)}
    assert saved == {
        _G815: (True, "key", "Logitech G815"),
        _STEAM: (True, "click", "Steam Controller"),
    }
    assert set(manager.wake_sets[-1]) == {_G815, _STEAM}
    # A device not read yet is listed and ticked at once.
    manager.press(_GONE, "keyboard")
    assert _saved_wake(m)[-1]["id"] == _GONE and _saved_wake(m)[-1]["how"] == "key"


def test_s30_presses_do_nothing_while_the_tab_is_closed(fakes, qapp: object) -> None:  # noqa: ANN001
    manager, calls, model, m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    listener = manager.press_listener
    ssm.wakeTabOpen(False)
    assert listener is not None
    listener(_G815, "keyboard")  # a late one, after the tab closed
    assert not any(r["ticked"] for r in _rows(ssm))
    assert _saved_wake(m) == []


def test_s30_ticks_by_hand_and_an_untick_stays_through_presses(
    fakes: tuple,
    qapp: object,
) -> None:
    manager, calls, model, m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    ssm.setWakeTicked(_G815, True)
    ssm.setWakeTicked(_STEAM, True)
    ssm.setWakeTicked(_STEAM, False)
    notes = {r["id"]: (r["ticked"], r["note"]) for r in _rows(ssm)}
    assert notes == {
        _G815: (True, "ticked by you"),
        _STEAM: (False, "you unticked it"),
    }
    assert manager.wake_sets[-1] == [_G815]
    # The click that unticked the mouse doesn't tick it again.
    manager.press(_STEAM, "mouse")
    assert {r["id"]: r["ticked"] for r in _rows(ssm)}[_STEAM] is False
    saved = {r["id"]: (r["ticked"], r["how"]) for r in _saved_wake(m)}
    assert saved == {_G815: (True, "you"), _STEAM: (False, "untick")}


class _Clock:
    """clock.monotonic stepped by the test (S33's 2 s)."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def stepped(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    from gremlin import clock

    c = _Clock()
    monkeypatch.setattr(clock, "monotonic", c)
    return c


def _in_use(model) -> dict:  # noqa: ANN001
    return {r["id"]: r["inUse"] for r in _rows(model)}


def test_s33_movement_lights_a_row_without_ticking_it(
    fakes: tuple,
    qapp: object,
    stepped: _Clock,
) -> None:
    manager, calls, model, m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    assert manager.activity_listener is not None
    assert _in_use(ssm) == {_G815: False, _STEAM: False}
    seen: list[int] = []
    ssm.wakeRowsChanged.connect(lambda: seen.append(1))
    manager.activity(_STEAM)  # mouse movement: not a press
    assert _in_use(ssm) == {_G815: False, _STEAM: True}
    assert not any(r["ticked"] for r in _rows(ssm))
    assert _saved_wake(m) == []
    # Input every 0.5 s keeps it lit without rebuilding the rows each time.
    manager.activity(_STEAM)
    assert seen == [1]
    # An unknown id lights nothing and adds no row.
    manager.activity(r"USB\VID_DEAD&PID_BEEF\1")
    assert set(_in_use(ssm)) == {_G815, _STEAM}


def test_s33_a_press_lights_and_ticks_as_before(
    fakes: tuple,
    qapp: object,
    stepped: _Clock,
) -> None:
    manager, calls, model, _m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    manager.press(_G815, "keyboard")
    row = next(r for r in _rows(ssm) if r["id"] == _G815)
    assert (row["ticked"], row["note"], row["inUse"]) == (
        True,
        "ticked when you pressed a key",
        True,
    )


def test_s33_the_highlight_goes_2_s_after_the_last_input(
    fakes: tuple,
    qapp: object,
    stepped: _Clock,
) -> None:
    manager, calls, model, _m = fakes
    ssm = model()
    _open_wake(ssm, calls, qapp)
    timer = ssm._in_use_timer  # noqa: SLF001
    manager.activity(_G815)
    assert timer.isActive() and 1900 <= timer.interval() <= 2100
    stepped.t += 1.0
    manager.activity(_STEAM)
    stepped.t += 0.5
    manager.activity(_G815)  # last G815 input at +1.5 s
    # One timer for all rows, still set for the first row to end.
    stepped.t = 1002.0
    ssm._expire_in_use()  # noqa: SLF001
    assert _in_use(ssm) == {_G815: True, _STEAM: True}
    stepped.t = 1003.0
    ssm._expire_in_use()  # noqa: SLF001
    # The mouse's 2 s are up; the keyboard's last input was later.
    assert _in_use(ssm) == {_G815: True, _STEAM: False}
    assert timer.isActive() and timer.interval() <= 600
    stepped.t = 1003.6
    ssm._expire_in_use()  # noqa: SLF001
    assert _in_use(ssm) == {_G815: False, _STEAM: False}
    assert not timer.isActive()


def test_s33_the_real_timer_ends_the_highlight(
    fakes: tuple,
    qapp: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, calls, model, m = fakes
    monkeypatch.setattr(m, "IN_USE_S", 0.2)
    ssm = model()
    _open_wake(ssm, calls, qapp)
    manager.activity(_G815)
    assert _in_use(ssm)[_G815] is True
    assert _wait(qapp, lambda: _in_use(ssm)[_G815] is False, limit=3.0)


def test_s33_nothing_lights_while_the_tab_is_closed(
    fakes: tuple,
    qapp: object,
    stepped: _Clock,
) -> None:
    manager, calls, model, _m = fakes
    ssm = model()
    ssm.setOpen(True)
    assert manager.activity_listener is None
    _open_wake(ssm, calls, qapp)
    listener = manager.activity_listener
    manager.activity(_G815)
    assert _in_use(ssm)[_G815] is True
    ssm.wakeTabOpen(False)
    # Leaving the tab clears the listener and the highlight at once.
    assert manager.activity_listener is None
    assert _in_use(ssm) == {_G815: False, _STEAM: False}
    assert not ssm._in_use_timer.isActive()  # noqa: SLF001
    assert listener is not None
    listener(_STEAM)  # a late one, after the tab closed
    assert _in_use(ssm) == {_G815: False, _STEAM: False}
    # Closing the window with the tab open clears it too.
    _open_wake(ssm, calls, qapp)
    manager.activity(_G815)
    ssm.setOpen(False)
    assert manager.activity_listener is None
    assert _in_use(ssm)[_G815] is False


def test_s28_ticks_kept_after_a_restart_and_history_restore(
    fakes: tuple,
    qapp: object,
) -> None:
    _manager, calls, model, m = fakes
    first = model()
    _open_wake(first, calls, qapp)
    first.setWakeTicked(_G815, True)
    first.wakeTabOpen(False)
    again = model()
    assert [(r["id"], r["ticked"], r["connected"]) for r in _rows(again)] == [
        (_G815, True, True)
    ]
    # History puts an empty list back: the rows follow.
    _set_wake(m, [])
    from gremlin.signal import signal

    signal.configChanged.emit()
    assert _rows(again) == []


def test_s31_nothing_ticked_shows_the_waiting_line(fakes) -> None:  # noqa: ANN001
    manager, _calls, model, m = fakes
    ssm = model()
    ssm.setEnabled(True)
    manager.extra = {
        "hold": ssm_ui_fakes.HOLD_NO_WAKE_DEVICE,
        "saver_remaining_s": 80.0,
    }
    ssm.refreshStatus()
    assert ssm.property("holdText") == (
        "Waiting: tick at least one keyboard or mouse on Wake PC."
    )
    assert ssm.property("onHold") is True
    assert ssm.property("saverCountdownText") == ""
    assert m.HOLD_NO_WAKE_DEVICE == ssm_ui_fakes.HOLD_NO_WAKE_DEVICE


# The window, off-screen ------------------------------------------------------


@pytest.fixture(scope="module")
def window(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("ssm") / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in (done.stdout or "").splitlines() if ln.startswith("{")]
    assert lines, (done.stdout, done.stderr)
    result = json.loads(lines[-1])
    assert "errors" not in result, result
    return result


_WARNING = "Power off comes at or before the screen saver: the screen saver won't show."


def test_window_opens_off_with_windows_time(window: dict) -> None:
    assert window["title"] == "Screen Saver Mode"
    assert window["objectName"] == "screenSaverModeWindow" and window["visible"]
    s = window["start"]
    assert (s["enabled"], s["hold"], s["cfgEnabled"], s["cfgHold"]) == (
        False,
        True,
        False,
        True,
    )
    # Two timers, both on, each showing Windows' time greyed (contract-4).
    assert s["saver"] == {
        "on": True,
        "waitText": "",
        "placeholder": "10 min",
        "clearVisible": False,
        "cfgOn": True,
        "cfgWait": 0,
    }
    assert s["off"] == {
        "on": True,
        "waitText": "",
        "placeholder": "5 min",
        "clearVisible": False,
        "cfgOn": True,
        "cfgWait": 0,
    }
    assert s["ssmSaverWindowsWait"] == "Windows' screen saver wait (10 min)"
    assert s["ssmOffWindowsWait"] == "Windows' display-off time (5 min)"
    # The one Action choice and its single wait box are gone.
    assert s["oldNames"] == []
    # Windows' display-off time comes before its screen saver wait.
    assert s["ssmOrderWarning"] == _WARNING and s["ssmOrderWarningVisible"]
    assert not s["ssmProblemTextVisible"]
    assert not s["ssmSaverProblemVisible"] and not s["ssmOffProblemVisible"]


def test_window_controls_write_the_settings(window: dict) -> None:
    assert window["on"]["cfgEnabled"] is True and window["on"]["applied"] is True
    assert "listening to the keyboard" in _row_text(window["on"], "Listener")
    so = window["saverOff"]
    assert so["cfgOn"] is False and so["on"] is False
    assert so["applied"] == [False, True]
    assert not so["ssmOrderWarningVisible"]
    oo = window["offOff"]
    assert oo["cfgOn"] is False and oo["on"] is False
    assert oo["applied"] == [True, False]
    assert not oo["ssmOrderWarningVisible"]
    assert window["holdOff"] == {"cfgHold": False, "applied": False}


def test_window_wait_boxes_type_and_clear_per_row(window: dict) -> None:
    ot = window["offTyped"]
    assert (ot["cfgWait"], ot["applied"], ot["saverWait"]) == (900, 900, 0)
    assert ot["waitText"] == "15" and ot["clearVisible"]
    # 15 min power off after Windows' 10 min screen saver: no warning.
    assert not ot["ssmOrderWarningVisible"]
    st = window["saverTyped"]
    assert (st["cfgWait"], st["applied"], st["waitText"]) == (1200, 1200, "20")
    assert st["ssmOrderWarning"] == _WARNING
    assert window["badTyped"]["cfgWait"] == 1200
    assert window["badTyped"]["waitText"] == "20"
    sc = window["saverCleared"]
    assert (sc["cfgWait"], sc["applied"], sc["offWait"]) == (0, 0, 900)
    assert sc["waitText"] == "" and not sc["clearVisible"]
    assert sc["placeholder"] == "10 min"
    assert not sc["ssmOrderWarningVisible"]
    oc = window["offCleared"]
    assert (oc["cfgWait"], oc["applied"], oc["waitText"]) == (0, 0, "")
    assert not oc["clearVisible"] and oc["placeholder"] == "5 min"
    assert oc["ssmOrderWarning"] == _WARNING


def _row(snap: dict, label: str) -> dict:
    return next(r for r in snap["statusRows"] if r["label"] == label)


def _row_text(snap: dict, label: str) -> str:
    r = _row(snap, label)
    return r["value"] + r["detail"]


_STATUS_LABELS = [
    "Listener",
    "Your idle time",
    "Windows' idle time",
    "Screen saver",
    "Power off displays",
    "Wake-ups",
    "Hold",
    "Last time away",
    "Devices back on",
]


def test_window_status_texts(window: dict) -> None:
    # The rows' exact wording belongs to the model; these check what the
    # window shows for each scenario.
    held = window["held"]
    assert "chrome.exe" in _row_text(held, "Hold")
    assert "2 min 41 s" in _row_text(held, "Your idle time")
    fs = window["fullscreen"]
    assert "StarCitizen.exe" in _row_text(fs, "Hold")
    rows = window["keyboardReset"]["statusRows"]
    assert "G915" in "".join(r["value"] + r["detail"] for r in rows)
    ns = window["noScreenSaver"]
    assert ns["ssmSaverProblem"] == "No screen saver is chosen in Windows."
    assert ns["ssmSaverProblemVisible"] and not ns["ssmOffProblemVisible"]
    assert "3 min 20 s" in _row_text(ns, "Power off displays")
    on = window["offNever"]
    assert on["ssmOffProblem"] == (
        "Windows never turns the display off: type a time to use this timer."
    )
    assert not on["ssmSaverProblemVisible"]
    assert "1 min 20 s" in _row_text(on, "Screen saver")
    nl = window["notListening"]
    assert "can't be listened to" in nl["ssmProblemText"]
    assert "not listening" in _row_text(nl, "Listener")
    cd = window["countdown"]
    assert "1 min 20 s" in _row_text(cd, "Screen saver")
    assert "3 min 20 s" in _row_text(cd, "Power off displays")
    ko = window["keepingOff"]
    assert "136" in _row_text(ko, "Wake-ups")


def test_window_status_grid_has_the_nine_rows_in_order(window: dict) -> None:
    rows = window["ssm2"]["gridRows"]
    assert [r["label"] for r in rows] == _STATUS_LABELS


def test_window_test_now_button_and_countdown(window: dict) -> None:
    t = window["ssm2"]
    assert t["testText"] == "Test now"
    after = t["afterTestClick"]
    assert after["countdown"] > 0
    assert after["text"] == f"Cancel test ({after['countdown']})"
    cancelled = t["afterCancel"]
    assert cancelled["countdown"] == 0 and cancelled["text"] == "Test now"


def test_window_wait_for_devices_box(window: dict) -> None:
    t = window["ssm2"]
    assert t["waitText"] == "10 s"
    typed = t["waitTyped"]
    assert typed["model"] == 25 and typed["cfg"] == 25
    assert typed["text"] == "25 s"


def test_window_refresh_devices(window: dict) -> None:
    assert window["devicesBefore"] == 0
    assert window["devicesBusy"] == {"text": "Checking… (4 s)", "enabled": False}
    d = window["devices"]
    assert d["scans"] == [4.0] and d["count"] == 2 and d["text"] == "Refresh Devices"
    assert d["rows"] == [
        "PD200X Microphone (buttons) · 18",
        "VKBSim NXT SEM THQ FSM.GA · 13",
    ]


_PD = "PD200X Microphone (buttons)"
_VKB = "VKBSim NXT SEM THQ FSM.GA"
_VJOY = "vJoy Device"


def test_window_settings_devices_is_one_line_and_opens_the_tab(window: dict) -> None:
    """S12: the counts and Open Devices; the list is on the Devices tab."""
    assert window["summaryEmpty"] == "No devices yet"
    assert window["openDevices"] == 1
    assert window["detectionOnDevices"] == [], "S30: presses tick on Devices"
    assert window["devices"]["summary"] == "2 automatic"
    d = window["devices"]
    assert d["message"] == d["modelMessage"] != ""


def test_window_s28_header_and_tab_bar_on_every_tab(window: dict) -> None:
    """The switch, Test now and the description stay on top; the bar below
    them is full width in three equal parts, the open tab filled, its text
    larger."""
    for index, lay in enumerate(window["layouts"]):
        bar = lay["bar"]
        assert bar[0] == 0 and bar[2] == lay["width"]
        for name, (shown, _x, y, _w, h) in lay["header"].items():
            assert shown, (index, name)
            assert y + h <= bar[1], (index, name)
        xs = [t[0] for t in lay["tabs"]]
        widths = [t[2] for t in lay["tabs"]]
        assert max(widths) - min(widths) <= 1 and sum(widths) >= lay["width"] - 2
        assert xs == sorted(xs) and xs[0] == 0
        others = [i for i in range(3) if i != index]
        assert all(lay["fills"][i] != lay["fills"][index] for i in others)
        assert all(lay["sizes"][i] < lay["sizes"][index] for i in others)
    # Nothing above the pages moves from tab to tab.
    assert len({json.dumps(lay["header"]) for lay in window["layouts"]}) == 1
    assert len({json.dumps(lay["bar"]) for lay in window["layouts"]}) == 1


def test_window_devices_tab_texts_and_columns(window: dict) -> None:
    t = window["devicesTab"]
    assert t["heading"] == "Devices that never go quiet"
    assert t["description"] == (
        "Automatic devices are switched off while the displays are off. "
        "Manual devices stay on the list and are left alone."
    )
    assert t["header"] == [
        "Device",
        "Reports per second",
        "Automatic",
        "Manual",
        "Remove",
    ]


def test_window_devices_tab_rows_at_the_minimum_width(window: dict) -> None:
    """S35: a new device is Automatic; a virtual one is locked, with its
    note; a long name elides and nothing leaves the window."""
    t = window["devicesTab"]
    rows = t["start"]
    assert len(rows) == 4
    for name, r in rows.items():
        virtual = name == _VJOY
        assert (r["automatic"], r["manual"]) == (not virtual, virtual), name
        assert r["enabled"] == [not virtual] * 2, name
        assert r["virtualNote"] == virtual
        assert r["virtualText"] == "(virtual: never switched off)"
        assert r["found"] == "" and not r["foundVisible"]
        assert r["right"] <= t["width"], name
    assert rows[_PD]["rate"] == "18"
    long = next(r for n, r in rows.items() if n.startswith("A very long"))
    assert long["truncated"]


def test_window_devices_tab_one_choice_per_row(window: dict) -> None:
    """S35: clicking one clears the other, in that row only, and is saved;
    the locked virtual row doesn't answer."""
    t = window["devicesTab"]

    def picked(step: str) -> dict:
        return {n: (r["automatic"], r["manual"]) for n, r in t[step]["rows"].items()}

    start = {n: (r["automatic"], r["manual"]) for n, r in t["start"].items()}
    assert picked("manual") == {**start, _PD: (False, True)}
    assert t["manual"]["stored"][_PD] == "manual"
    assert t["manual"]["stored"][_VKB] == "automatic"
    # A virtual device doesn't count (S12).
    assert t["manualSummary"] == "2 automatic · 1 manual"
    assert picked("automatic") == start
    assert t["automatic"]["stored"][_PD] == "automatic"
    assert picked("locked")[_VJOY] == (False, True)


def test_window_devices_tab_not_found_and_remove(window: dict) -> None:
    """S27: not found keeps the row and its choice, without a rate, in the
    warning color; Remove forgets it."""
    t = window["devicesTab"]
    row = t["gone"]["rows"][_PD]
    assert row["foundVisible"] and row["found"].startswith(
        "Not found · last seen today "
    )
    assert row["foundColor"] == t["warnColor"]
    assert row["rate"] == "" and row["manual"] and not row["automatic"]
    assert t["gone"]["rows"][_VKB]["rate"] == "13"
    assert "1 not found" in t["goneSummary"]
    assert t["goneMessage"].endswith("3 found, 1 not found")
    assert len(t["removed"]["rows"]) == 3 and _PD not in t["removed"]["rows"]
    assert _PD not in t["removed"]["stored"]


def test_window_has_no_console_warnings(window: dict) -> None:
    assert [w for w in window["warnings"] if ".qml" in w] == []


def test_window_three_sections_stacked_each_with_its_button(window: dict) -> None:
    """Contract-3: Devices, Programs, System, stacked; each section holds its
    own button and texts; Devices' list is on its own tab (S12)."""
    sec = window["sections"]
    assert sec["order"] == [
        "ssmSectionDevices",
        "ssmSectionPrograms",
        "ssmSectionSystem",
    ]
    assert sec["homes"] == {
        "ssmOpenDevices": "ssmSectionDevices",
        "ssmDevicesSummary": "ssmSectionDevices",
        "ssmRefreshDevices": "ssmDevicesPage",
        "ssmDeviceList": "ssmDevicesPage",
        "ssmRefreshPrograms": "ssmSectionPrograms",
        "ssmProgramList": "ssmSectionPrograms",
        "ssmProgramsMessage": "ssmSectionPrograms",
        "ssmRefreshSystem": "ssmSectionSystem",
        "ssmSystemList": "ssmSectionSystem",
        "ssmSystemMessage": "ssmSectionSystem",
    }
    t = sec["texts"]
    assert t["ssmSectionDevices"] == ["Devices", "Open Devices", "2 automatic"]
    assert t["ssmSectionPrograms"][:3] == [
        "Programs",
        "🛡 Refresh Programs",
        "Programs keeping the display on. These hold Screen Saver Mode off "
        "until they stop. Needs administrator rights.",
    ]
    assert t["ssmSectionSystem"][:3] == [
        "System",
        "🛡 Refresh System",
        "Programs, drivers and services keeping the PC awake. They stop "
        "sleep, not the screens. Needs administrator rights.",
    ]
    assert sec["systemText"] == "🛡 Refresh System"


def test_window_refresh_programs_and_ignore_switch(window: dict) -> None:
    p = window["programs"]
    # Its own check; only the Display half; System is still empty.
    assert p["lists"] == 1 and p["count"] == 2 and p["systemCount"] == 0
    assert p["checked"] == [False, True]
    assert p["names"] == ["RustDesk.exe", "chrome.exe"]
    assert [a["visible"] for a in p["alsoAwake"]] == [True, False]
    assert p["alsoAwake"][0]["text"] == "also keeps the PC awake"
    assert [k["visible"] for k in p["kinds"]] == [False, False]
    assert [d["visible"] for d in p["details"]] == [False, True]
    assert p["details"][1]["text"] == "a video is playing"
    r = window["refused"]
    assert r["ignores"] == [["RustDesk.exe", True, "PROCESS"]]
    # The switch went back.
    assert r["checked"] == [False, True]
    assert r["message"] == "Administrator rights were refused."
    a = window["accepted"]
    assert a["ignores"][-1] == ["RustDesk.exe", True, "PROCESS"]
    assert a["checked"] == [True, True]
    assert a["message"] == "RustDesk.exe is ignored: it no longer keeps the display on."
    lr = window["listRefused"]
    assert lr["count"] == 2 and lr["message"] == "Administrator rights were refused."
    assert window["closed"] is True


def test_window_refresh_system_and_its_ignore_switch(window: dict) -> None:
    s = window["system"]
    # A second, separate check, filling only the System list.
    assert s["lists"] == 2 and s["count"] == 3 and s["programCount"] == 2
    assert s["names"] == [
        "claude.exe",
        ssm_ui_fakes.DRIVER_NAME,
        "FxSound Audio Enhancer",
    ]
    assert [k["visible"] for k in s["kinds"]] == [False, True, True]
    assert s["kinds"][1]["text"] == "(driver)"
    assert [d["text"] for d in s["details"] if d["visible"]] == [
        "Electron",
        ssm_ui_fakes.DRIVER_DETAIL,
    ]
    assert not any(a["visible"] for a in s["alsoAwake"])
    assert s["checked"] == [False, False, True]
    assert "ignored ones no longer keep the PC awake." in s["message"]
    d = window["driver"]
    assert d["ignores"][-1] == [ssm_ui_fakes.DRIVER_NAME, True, "DRIVER"]
    assert d["checked"] == [False, True, True]
    assert d["programsChecked"] == [True, True]
    assert d["message"] == (
        f"{ssm_ui_fakes.DRIVER_NAME} is ignored: it no longer keeps the PC awake."
    )
    assert d["programsMessage"] == (
        "RustDesk.exe is ignored: it no longer keeps the display on."
    )


def test_window_s26_helper_message_and_try_again_in_devices(window: dict) -> None:
    h = window["helper"]
    assert h["saved"] == [[r"HID\VID_1&PID_2\1"], [r"HID\VID_3&PID_4\1"]]
    assert h["text"] == "Devices can't be disabled: the helper isn't running"
    assert h["visible"] and h["buttonVisible"]
    assert h["buttonText"] == "Try again"
    assert h["section"] == ["ssmDevicesPage", "ssmDevicesPage"]
    assert h["starts"] == 1
    after = window["helperAfter"]
    assert after == {"visible": False, "starts": 2}


def test_window_s28_three_tabs_and_the_wake_pc_list(window: dict) -> None:
    w = window["wake"]
    assert w["tabs"] == ["Settings", "Devices", "Wake PC"]
    assert w["detectionOnDevices"] == [], "S30: detection on the Devices tab"
    assert w["startIndex"] == 0 and w["settingsShown"] and not w["wakeShown"]
    # Settings shows everything it did before.
    assert w["settingsHome"] == ["ssmEnabled", "ssmSectionDevices", "ssmStatusGrid"]
    assert w["heading"] == "Allow this device to wake the PC"
    assert w["programsNote"] == (
        "Input sent by programs (RustDesk, remote desktop) always counts."
    )
    assert w["openDetection"] == ["start"] and w["wakeVisible"]
    assert w["rows"] == [
        {
            "name": "Logitech G815",
            "kinds": "keyboard",
            "ticked": False,
            "note": "",
            "lit": False,
        },
        {
            "name": "Steam Controller",
            "kinds": "keyboard, mouse",
            "ticked": False,
            "note": "",
            "lit": False,
        },
    ]
    # S30, S33: a press ticks and lights the row ("in use now" after its note).
    assert w["pressed"] == [
        {
            "name": "Logitech G815",
            "kinds": "keyboard",
            "ticked": True,
            "note": "ticked when you pressed a key · in use now",
            "lit": True,
        },
        {
            "name": "Steam Controller",
            "kinds": "keyboard, mouse",
            "ticked": False,
            "note": "",
            "lit": False,
        },
    ]
    # S33: movement lights a row without ticking it; no note, just the words.
    assert [(r["ticked"], r["note"], r["lit"]) for r in w["moved"]] == [
        (True, "ticked when you pressed a key · in use now", True),
        (False, "in use now", True),
    ]
    # S33: the highlight goes after its time; the ticks stay as they were.
    assert [(r["ticked"], r["note"], r["lit"]) for r in w["faded"]] == [
        (True, "ticked when you pressed a key", False),
        (False, "", False),
    ]
    assert w["clicked"]["ticked"] == [True, True]
    assert w["clicked"]["cfg"] == [[True, "key"], [True, "you"]]
    assert w["back"]["detection"] == ["start", "stop"]
    assert w["back"]["settingsShown"]
