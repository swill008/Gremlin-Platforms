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
Windows refuses. The core and the checks are stand-ins
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
    made: list = []

    def model():  # noqa: ANN202
        obj = m.ScreenSaverModeModel()
        made.append(obj)
        return obj

    yield manager, calls, model, m
    from gremlin.signal import signal

    for obj in made:
        obj.setOpen(False)
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
    assert "Screen Saver Mode ignores these." in ssm.property("devicesMessage")


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
    assert s["ssmListening"] == "Screen Saver Mode is off."
    assert not s["ssmHoldTextVisible"] and not s["ssmProblemTextVisible"]
    assert not s["ssmSaverCountdownVisible"] and not s["ssmOffCountdownVisible"]
    assert not s["ssmWakeCountVisible"]
    assert not s["ssmSaverProblemVisible"] and not s["ssmOffProblemVisible"]


def test_window_controls_write_the_settings(window: dict) -> None:
    assert window["on"]["cfgEnabled"] is True and window["on"]["applied"] is True
    assert window["on"]["ssmListening"] == "Listening to the keyboard and mouse"
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


def test_window_status_texts(window: dict) -> None:
    held = window["held"]
    assert held["ssmHoldText"] == (
        "On hold: a program is keeping the display on (chrome.exe). "
        "The countdown starts again when it stops."
    )
    assert held["ssmIdleText"] == "Your idle time: 2 min 41 s"
    assert held["ssmWindowsIdleText"].startswith("Windows' idle time: 0 s")
    fs = window["fullscreen"]
    assert fs["ssmHoldText"] == (
        "On hold: a full-screen program is in front (StarCitizen.exe). "
        "The countdown starts again when it ends."
    )
    assert fs["ssmLastReset"] == (
        "last reset by: input sent by a program, 8 times a minute"
    )
    assert fs["ssmLastResetVisible"]
    assert window["keyboardReset"]["ssmLastReset"] == (
        "last reset by: Logitech G915 (keyboard), just now"
    )
    # Nothing before the first input.
    assert window["start"]["ssmLastReset"] == ""
    assert not window["start"]["ssmLastResetVisible"]
    ns = window["noScreenSaver"]
    assert ns["ssmSaverProblem"] == "No screen saver is chosen in Windows."
    assert ns["ssmSaverProblemVisible"] and not ns["ssmOffProblemVisible"]
    assert not ns["ssmSaverCountdownVisible"]
    assert ns["ssmOffCountdown"] == "Power off displays in 3 min 20 s"
    on = window["offNever"]
    assert on["ssmOffProblem"] == (
        "Windows never turns the display off: type a time to use this timer."
    )
    assert not on["ssmSaverProblemVisible"] and not on["ssmOffCountdownVisible"]
    assert on["ssmSaverCountdown"] == "Screen saver in 1 min 20 s"
    nl = window["notListening"]
    assert nl["ssmListening"] == "Not listening to the keyboard and mouse"
    assert "can't be listened to" in nl["ssmProblemText"]
    cd = window["countdown"]
    assert cd["ssmSaverCountdown"] == "Screen saver in 1 min 20 s"
    assert cd["ssmOffCountdown"] == "Power off displays in 3 min 20 s"
    assert not cd["ssmHoldTextVisible"] and not cd["ssmWakeCountVisible"]
    ko = window["keepingOff"]
    done = "done. Nothing more until the keyboard or mouse is used."
    assert ko["ssmSaverCountdown"] == f"Screen saver {done}"
    assert ko["ssmOffCountdown"] == f"Power off displays {done}"
    assert ko["ssmWakeCount"] == (
        "Windows turned the displays back on 136 times: devices that never "
        "go quiet (see Refresh Devices)."
    )
    assert ko["ssmWakeCountVisible"]


def test_window_refresh_devices(window: dict) -> None:
    assert window["devicesBefore"] == 0
    assert window["devicesBusy"] == {"text": "Checking… (4 s)", "enabled": False}
    d = window["devices"]
    assert d["scans"] == [4.0] and d["count"] == 2 and d["text"] == "Refresh Devices"
    assert d["rows"] == [
        "PD200X Microphone (buttons) · 18",
        "VKBSim NXT SEM THQ FSM.GA · 13",
    ]


def test_window_three_sections_stacked_each_with_its_button(window: dict) -> None:
    """Contract-3: Devices, Programs, System, stacked; each section holds its
    own Refresh button, list and message; the texts as the mock-up."""
    sec = window["sections"]
    assert sec["order"] == [
        "ssmSectionDevices",
        "ssmSectionPrograms",
        "ssmSectionSystem",
    ]
    assert sec["homes"] == {
        "ssmRefreshDevices": "ssmSectionDevices",
        "ssmDeviceList": "ssmSectionDevices",
        "ssmRefreshPrograms": "ssmSectionPrograms",
        "ssmProgramList": "ssmSectionPrograms",
        "ssmProgramsMessage": "ssmSectionPrograms",
        "ssmRefreshSystem": "ssmSectionSystem",
        "ssmSystemList": "ssmSectionSystem",
        "ssmSystemMessage": "ssmSectionSystem",
    }
    t = sec["texts"]
    assert t["ssmSectionDevices"][:3] == [
        "Devices",
        "Refresh Devices",
        "Devices that never go quiet and keep Windows' idle time at 0. "
        "Screen Saver Mode ignores them.",
    ]
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
