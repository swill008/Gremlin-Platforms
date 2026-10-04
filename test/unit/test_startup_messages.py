# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Start-up and device messages (3 Oct review, APP17, DEV15).

- A vJoy set-up problem (two vJoy devices alike, discrete hats, a vJoy
  device Windows doesn't list) stopped the whole program; now that vJoy
  device is left out and the program says which and how to fix it (DEV15,
  user's choice).
- With Diagnostic logs Off an error left no trace; system.log keeps errors
  (APP17, user's choice).
- The last profile that won't open can be forgotten (APP17).
- The second-copy question says the other copy's unsaved changes are lost,
  the DEBUG badge follows the UI scale, a missing ViGEmBus says what to
  install (APP17, DEV15).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import collections
import ctypes
import logging
import pathlib
from types import SimpleNamespace
from unittest import mock

import pytest

import dill
from gremlin import device_initialization as di
from vjoy import vjoy

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture
def fresh_scan(monkeypatch: pytest.MonkeyPatch) -> list:
    """A first scan, with the program's state put back afterwards."""
    monkeypatch.setattr(di, "_joystick_devices", collections.OrderedDict())
    monkeypatch.setattr(di, "_left_out", set())
    monkeypatch.setattr(di, "_vjoy_problems", [])
    monkeypatch.setattr(di, "_told", ())
    monkeypatch.setattr(di, "_window_up", False)
    monkeypatch.setattr("gremlin.modules.output.reset_vjoy", lambda: None)
    told: list = []
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: told.append(a))
    return told


def _vjoy(monkeypatch: pytest.MonkeyPatch, ids: set[int], hats_ok: bool = True) -> None:
    monkeypatch.setattr(vjoy, "device_exists", lambda i: i in ids)
    monkeypatch.setattr(vjoy, "hat_configuration_valid", lambda i: hats_ok)


def _second_vjoy_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Another vJoy device in DirectInput, alike in axes, buttons and hats."""
    fake = dill.DILL._dll
    twin = dill._DeviceSummary()
    size = ctypes.sizeof(twin)
    ctypes.memmove(ctypes.byref(twin), ctypes.byref(fake.devices[1]), size)
    twin.device_guid.Data1 = twin.device_guid.Data1 ^ 0x5A5A
    monkeypatch.setattr(fake, "devices", [*fake.devices, twin])


def test_discrete_hats_leave_that_vjoy_out(
    monkeypatch: pytest.MonkeyPatch, fresh_scan: list
) -> None:
    _vjoy(monkeypatch, {1}, hats_ok=False)
    di.joystick_devices_initialization()  # used to raise and stop the program
    assert di.vjoy_devices() == []
    assert [d.name for d in di.physical_devices()] == ["pJoy Pro"]
    di.announce_vjoy_problems()
    title, details = fresh_scan[0]
    assert title == "Gremlin-Platforms is running without vJoy 1."
    assert "continuous hats" in details and "restart" in details


def test_a_vjoy_windows_doesnt_list_is_left_out_the_rest_work(
    monkeypatch: pytest.MonkeyPatch, fresh_scan: list
) -> None:
    _vjoy(monkeypatch, {1, 2})
    # vJoy 2 is set up differently, so it can't be mistaken for vJoy 1.
    monkeypatch.setattr(vjoy, "button_count", lambda i: 64 if i == 1 else 32)
    di.joystick_devices_initialization()
    assert [d.vjoy_id for d in di.vjoy_devices()] == [1]
    di.announce_vjoy_problems()
    assert "running without vJoy 2" in fresh_scan[0][0]
    assert "doesn't list it" in fresh_scan[0][1]


def test_vjoy_devices_alike_are_both_left_out(
    monkeypatch: pytest.MonkeyPatch, fresh_scan: list
) -> None:
    _second_vjoy_device(monkeypatch)
    _vjoy(monkeypatch, {1, 2})
    di.joystick_devices_initialization()
    assert di.vjoy_devices() == []
    di.announce_vjoy_problems()
    title, details = fresh_scan[0]
    assert title == "Gremlin-Platforms is running without vJoy 1, vJoy 2."
    assert "vJoy 1 and vJoy 2 have the same number" in details


def test_alike_but_only_one_listed_is_not_guessed(
    monkeypatch: pytest.MonkeyPatch, fresh_scan: list
) -> None:
    _vjoy(monkeypatch, {1, 2})  # alike; Windows lists one vJoy device
    di.joystick_devices_initialization()
    assert di.vjoy_devices() == []  # not linked to whichever came last
    di.announce_vjoy_problems()
    assert "vJoy 1 and vJoy 2 have the same number" in fresh_scan[0][1]


def test_told_once_then_again_only_when_it_changes(
    monkeypatch: pytest.MonkeyPatch, fresh_scan: list
) -> None:
    _vjoy(monkeypatch, {1}, hats_ok=False)
    di.joystick_devices_initialization()
    di.announce_vjoy_problems()
    di.announce_vjoy_problems()
    assert len(fresh_scan) == 1
    # A new problem on a later scan (a device plugged in) is told at once.
    di._note_vjoy_problems([(3, "vJoy 3: something")], set())
    assert len(fresh_scan) == 2 and "vJoy 3" in fresh_scan[1][0]


def test_logs_off_still_keeps_errors_in_system_log() -> None:
    from gremlin.ui.log_option import apply_log_level

    try:
        apply_log_level("Off")
        system = logging.getLogger("system")
        assert not system.disabled and system.level == logging.ERROR
        assert logging.getLogger("user").disabled
        assert logging.getLogger("event").disabled
    finally:
        apply_log_level("Warning")


def test_a_last_profile_that_wont_open_is_offered_to_forget() -> None:
    from gremlin.ui.backend import Backend

    failed: list = []
    fake = SimpleNamespace(
        _load_problem="",
        lastProfileFailed=SimpleNamespace(emit=lambda *a: failed.append(a)),
        profileChanged=SimpleNamespace(emit=lambda: None),
        _record_profile_use=lambda path: failed.append("recorded"),
    )

    def load(path: str, report: bool = True) -> bool:
        assert report is False  # said once, by the offer, not twice
        fake._load_problem = "The file isn't there any more."
        return False

    fake._load_profile = load
    with mock.patch("gremlin.ui.backend.signal"):
        Backend.klass.openLastProfile(fake, "C:/gone/flight.xml")
    path = str(pathlib.Path("C:/gone/flight.xml"))
    assert failed == [(path, "The file isn't there any more.")]


def test_forget_takes_it_off_the_start_and_recent_lists(tmp_path: pathlib.Path) -> None:
    from gremlin.ui.backend import Backend

    gone, other = tmp_path / "gone.xml", tmp_path / "other.xml"
    values = {
        "last-profile": str(gone),
        "recent-profiles": [str(gone), str(other)],
    }
    fake = SimpleNamespace(
        config=SimpleNamespace(
            value=lambda s, g, key: values[key],
            set=lambda s, g, key, v: values.__setitem__(key, v),
        ),
        recentProfilesChanged=SimpleNamespace(emit=lambda: None),
    )
    Backend.klass.forgetProfile(fake, str(gone))
    assert values == {"last-profile": "", "recent-profiles": [str(other)]}


def test_wording_and_scaling() -> None:
    main = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8").replace("\r", "")
    assert "Changes not \"\n        \"saved in the other copy are lost." in main
    badge = (_ROOT / "qml" / "DebugFrame.qml").read_text(encoding="utf-8")
    assert "font.pixelSize: Style.dp(12)" in badge
    xbox = (_ROOT / "vigem" / "xbox.py").read_text(encoding="utf-8")
    assert "Install ViGEmBus 1.22" in xbox and "github.com/nefarius/ViGEmBus" in xbox
