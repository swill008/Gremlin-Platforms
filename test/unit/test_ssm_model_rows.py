# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode model, batch SSM2 (contract-SSM2.md, items 1-3, 5, 8, 9,
10, 12, 13): the status table rows, the devices wait setting, Test now, the
tray's three calls, the Devices trace and the state snapshot.
The core, the disabler and the trace are stand-ins; no real device is touched."""

from __future__ import annotations

import pathlib
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ssm_ui_fakes  # noqa: E402

LABELS = [
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


@pytest.fixture
def fakes(qapp: object, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    from gremlin.config import Configuration
    from gremlin.ui import screen_saver_mode_model as m

    manager, calls = ssm_ui_fakes.install(monkeypatch)
    m.register_options()
    cfg = Configuration()
    before = {n: cfg.value(m.SECTION, m.GROUP, n) for n in m.NAMES}
    for name, value in (
        (m.ENABLED, False),
        (m.SAVER_ON, True),
        (m.SAVER_WAIT, 0),
        (m.OFF_ON, True),
        (m.OFF_WAIT, 0),
        (m.DEVICES_WAIT, 10),
        (m.DEVICES, []),
        (m.WAKE_PC, []),
    ):
        cfg.set(m.SECTION, m.GROUP, name, value)
    monkeypatch.setattr(m, "_helper_refused", False)
    monkeypatch.setattr(m, "_helper_starting", False)
    monkeypatch.setattr(m, "_off_timer_on", None)
    # Module cache of the Ignore lists; Refresh Programs/System in other
    # tests fills it (chrome.exe, FxSound), which the snapshot would show.
    monkeypatch.setattr(m, "_ignored", {"programs": [], "system": []})
    made: list = []

    def model():  # noqa: ANN202
        obj = m.ScreenSaverModeModel()
        made.append(obj)
        return obj

    yield manager, model, m
    from gremlin.signal import signal

    for obj in made:
        obj.setOpen(False)
        try:
            signal.configChanged.disconnect(obj._on_config)
        except (RuntimeError, TypeError):
            pass
    for n, v in before.items():
        cfg.set(m.SECTION, m.GROUP, n, v)


def _rows(ssm) -> dict:  # noqa: ANN001
    ssm.refreshStatus()
    return {r["label"]: r for r in ssm.property("statusRows")}


def test_status_rows_come_in_the_contract_order(fakes: tuple) -> None:
    manager, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    manager.extra = {"idle_s": 161.0, "windows_idle_s": 5.0, "saver_remaining_s": 80.0}
    ssm.refreshStatus()
    rows = ssm.property("statusRows")
    assert [r["label"] for r in rows] == LABELS
    assert all(set(r) == {"label", "value", "detail", "tone"} for r in rows)
    by = {r["label"]: r for r in rows}
    assert by["Listener"]["tone"] == "ok"
    assert by["Your idle time"]["value"] == "2 min 41 s"
    assert by["Windows' idle time"]["value"] == "5 s"
    assert by["Screen saver"]["value"] == "in 1 min 20 s"
    assert by["Hold"]["value"] == "none"
    assert by["Devices back on"]["value"] == "all back on"


def test_power_off_row_says_switching_devices_off_while_waiting(fakes: tuple) -> None:
    manager, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    manager.extra = {"off_remaining_s": 30.0}
    assert _rows(ssm)["Power off displays"]["value"] == "in 30 s"
    manager.extra = {"off_remaining_s": 30.0, "waiting_for_devices": True}
    assert _rows(ssm)["Power off displays"]["value"] == "switching devices off…"


def test_wakeups_row_hints_at_automatic_only_from_three(fakes: tuple) -> None:
    manager, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    assert _rows(ssm)["Wake-ups"]["value"] == "none this time"
    manager.extra = {"wakes": 1}
    row = _rows(ssm)["Wake-ups"]
    assert row["value"] == "Windows turned the displays back on once"
    assert row["detail"] == ""
    manager.extra = {"wakes": 2}
    assert _rows(ssm)["Wake-ups"]["detail"] == ""
    manager.extra = {"wakes": 3}
    row = _rows(ssm)["Wake-ups"]
    assert row["value"] == "Windows turned the displays back on 3 times"
    assert row["detail"] == "a device may need to be Automatic (see Devices)"


def test_hold_row_shows_the_hold_text(fakes: tuple) -> None:
    manager, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    manager.extra = {"hold": "fullscreen", "hold_program": "game.exe"}
    row = _rows(ssm)["Hold"]
    assert "full-screen program is in front (game.exe)" in row["value"]


def test_last_time_away_row_and_the_freeze_from_the_trace_ring(fakes: tuple) -> None:
    from gremlin import trace

    manager, model, _m = fakes
    ssm = model()
    ssm.setEnabled(True)
    now = time.time()
    away = {
        "off_s": 766.0,
        "wakes": 1,
        "devices_off": 2,
        "devices_back": 2,
        "start": now - 100,
        "end": now - 10,
    }
    manager.extra = {"last_away": away}
    trace.recent("Main window", "stall began: no main-loop tick for 6 s", t=now - 60)
    trace.recent("Main window", "stall ended after 9 s", t=now - 50)
    row = _rows(ssm)["Last time away"]
    assert row["value"] == "Displays off 12 min 46 s"
    assert row["detail"] == (
        "1 wake-up · 2 devices switched off and back on · window not responding 9 s"
    )
    # Outside the away: no freeze.
    manager.extra = {"last_away": {**away, "start": now - 5000, "end": now - 4000}}
    assert _rows(ssm)["Last time away"]["detail"].endswith("no freeze")
    manager.extra = {}
    assert _rows(ssm)["Last time away"]["value"] == "none yet"


class _Disabler:
    def __init__(self, entries: dict) -> None:
        self.entries = entries
        self.enables = 0

    def journal(self) -> SimpleNamespace:
        entries = self.entries
        return SimpleNamespace(
            entries=entries,
            not_enabled=lambda: [
                i for i, e in entries.items() if e["state"] != "enabled"
            ],
        )

    def enable_pending(self) -> None:
        self.enables += 1

    def helper_running(self) -> bool:
        return True

    def status_text(self) -> str:
        return ""


def test_devices_back_on_row_and_try_again(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _manager, model, m = fakes
    disabler = _Disabler({"A": {"name": "VKB Gladiator", "state": "to be enabled"}})
    monkeypatch.setattr(m, "_disabler", lambda: disabler)
    ssm = model()
    row = _rows(ssm)["Devices back on"]
    assert row["value"] == "VKB Gladiator is still switched off"
    assert row["tone"] == "warn"
    assert ssm.property("devicesBackRetry") is True
    ssm.retryDevices()
    assert disabler.enables == 1
    disabler.entries["A"]["state"] = "enabled"
    row = _rows(ssm)["Devices back on"]
    assert (row["value"], row["tone"]) == ("all back on", "ok")
    assert ssm.property("devicesBackRetry") is False


def test_devices_wait_is_clamped_and_saved(fakes: tuple) -> None:
    from gremlin import config

    _manager, model, m = fakes
    ssm = model()
    assert ssm.property("devicesWaitS") == 10
    ssm.setDevicesWaitS(25)
    assert ssm.property("devicesWaitS") == 25
    assert config.Configuration().value(m.SECTION, m.GROUP, "devices-wait-s") == 25
    ssm.setDevicesWaitS(500)
    assert ssm.property("devicesWaitS") == 60
    ssm.setDevicesWaitS(0)
    assert ssm.property("devicesWaitS") == 1


def test_devices_wait_reaches_the_core_settings(fakes: tuple) -> None:
    manager, model, m = fakes
    settings_cls = m._core().Settings
    if "devices_wait_s" not in settings_cls.__dataclass_fields__:
        pytest.skip("stand-in Settings has no devices_wait_s")
    ssm = model()
    ssm.setEnabled(True)
    ssm.setDevicesWaitS(7)
    assert manager.settings().devices_wait_s == 7


def test_devices_wait_change_is_traced(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import trace

    _manager, model, _m = fakes
    lines: list[str] = []
    monkeypatch.setattr(trace, "screen_saver", lambda text, *a, **k: lines.append(text))
    model().setDevicesWaitS(20)
    assert "Wait for devices to switch off: 20 s" in lines


def test_test_now_calls_the_core_and_the_countdown_is_polled(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, model, _m = fakes
    calls: list = []
    left = [0]
    monkeypatch.setattr(
        manager,
        "start_test",
        lambda d=5.0: (calls.append(d), left.__setitem__(0, 5)),
        raising=False,
    )
    monkeypatch.setattr(
        manager, "cancel_test", lambda: left.__setitem__(0, 0), raising=False
    )
    monkeypatch.setattr(manager, "test_remaining", lambda: left[0], raising=False)
    ssm = model()
    assert ssm.property("testCountdown") == 0
    ssm.testNow()
    assert calls == [5.0]
    assert ssm.property("testCountdown") == 5
    ssm.cancelTest()
    assert ssm.property("testCountdown") == 0


def test_tray_functions(fakes, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    manager, model, m = fakes
    ssm = model()
    assert m.ssm_enabled() is False
    m.set_ssm_enabled(True)
    assert m.ssm_enabled() is True
    assert ssm.property("enabled") is True
    assert manager.settings().enabled is True
    m.set_ssm_enabled(False)
    assert m.ssm_enabled() is False
    done: list = []
    monkeypatch.setattr(manager, "turn_off_now", lambda: done.append(1), raising=False)
    m.turn_displays_off_now()
    assert done == [1]


def test_snapshot_provider_lines_and_change_notice(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import trace

    _manager, model, m = fakes
    registered: dict = {}
    changed: list[str] = []
    monkeypatch.setattr(
        trace,
        "register_snapshot",
        lambda s, fn: registered.__setitem__(s, fn),
        raising=False,
    )
    monkeypatch.setattr(trace, "snapshot_changed", changed.append, raising=False)
    m.save_devices(
        m.merge_devices(
            [],
            [
                ("VKB Gladiator", "HID\\A", 1.0),
                ("Mic", "HID\\B", 1.0),
                ("vJoy Device", "ROOT\\V", 1.0),
            ],
        )
    )
    m.save_wake_rows(
        [
            {
                "id": "K1",
                "name": "Logitech G815",
                "kinds": ["keyboard"],
                "ticked": True,
                "how": "you",
            }
        ]
    )
    ssm = model()
    ssm.setDeviceChoice("HID\\B", "manual")
    assert "Screen Saver Mode" in changed
    assert "Screen Saver Mode" in registered
    ssm.setDevicesWaitS(15)
    assert "Screen Saver Mode" in changed
    text = "\n".join(registered["Screen Saver Mode"]())
    assert "Screen Saver Mode: off" in text
    assert "Wait for devices to switch off: 15 s" in text
    assert "Devices: VKB Gladiator, automatic" in text
    assert "Devices: Mic, manual" in text
    assert "Devices: vJoy Device (virtual), manual" in text
    assert "Switch off" not in text
    assert "Wake PC ticked: Logitech G815" in text
    assert "Ignore Programs: none" in text
    assert "Ignore System: none" in text


def test_can_test_follows_the_mode(fakes: tuple) -> None:
    _manager, model, _m = fakes
    ssm = model()
    assert ssm.property("canTest") is False
    ssm.setEnabled(True)
    assert ssm.property("canTest") is True


@pytest.mark.parametrize(
    ("off", "back", "still_off", "text"),
    [
        (3, 1, 0, "3 devices switched off, 1 back on"),
        (1, 0, 0, "1 device switched off, 0 back on"),
        (2, 2, 0, "2 devices switched off and back on"),
        # A device left from an older time away is S39's row only.
        (2, 2, 1, "2 devices switched off and back on"),
        (3, 1, 1, "3 devices switched off, 1 back on"),
        (0, 0, 1, "0 wake-ups · "),
    ],
)
def test_last_time_away_device_counts_are_the_cores(
    fakes: tuple,
    monkeypatch: pytest.MonkeyPatch,
    off: int,
    back: int,
    still_off: int,
    text: str,
) -> None:
    manager, model, m = fakes
    entries = {
        str(n): {"name": f"VKB {n}", "state": "to be enabled"} for n in range(still_off)
    }
    monkeypatch.setattr(m, "_disabler", lambda: _Disabler(entries))
    ssm = model()
    now = time.time()
    manager.extra = {
        "last_away": {
            "off_s": 60.0,
            "wakes": 0,
            "devices_off": off,
            "devices_back": back,
            "start": now - 90,
            "end": now - 30,
        }
    }
    detail = _rows(ssm)["Last time away"]["detail"]
    assert text in detail and ("device" in detail) is bool(off)
    assert ssm.property("devicesBackRetry") is bool(still_off)
