# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode's Automatic / Manual per device (12 S21, S25, S35):
Automatic for a new device, Manual leaves the device alone, virtual devices
(vJoy, ViGEm) are locked and never switched off."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_ssm_ui as _ui  # noqa: E402  # pyright: ignore

fakes = _ui.fakes

_REAL = ("VKBSim NXT", r"HID\VID_231D&PID_0200\A&6B6F223&0&0000", 2.0)
_VJOY = ("vJoy - Virtual Joystick", r"HID\HIDCLASS\1", 1.0)
_VJOY_ID = ("Joystick", r"HID\VID_1234&PID_BEAD\2", 1.0)


def _save(m, *found: tuple) -> None:  # noqa: ANN001
    m.save_devices(m.merge_devices(m.saved_devices(), found))


def _connect(calls, *found: tuple) -> None:  # noqa: ANN001
    calls.present = [(n, i) for n, i, _r in found]


def _by_name(rows: list[dict]) -> dict:
    return {r["name"]: r for r in rows}


def test_new_device_is_automatic_and_virtual_is_locked(fakes) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    _save(m, _REAL, _VJOY, _VJOY_ID)
    _connect(calls, _REAL, _VJOY, _VJOY_ID)
    ssm = model()
    rows = _by_name(ssm.property("devices"))
    assert rows[_REAL[0]]["choice"] == "automatic"
    assert rows[_REAL[0]]["virtual"] is False
    for v in (_VJOY, _VJOY_ID):
        assert rows[v[0]]["virtual"] is True
        ssm.setDeviceChoice(rows[v[0]]["key"], "automatic")
    assert m._saved_pairs() == [_REAL[:2]]  # noqa: SLF001
    assert all(r["choice"] == "manual" for r in ssm.property("devices") if r["virtual"])


def test_manual_is_left_alone_and_kept_across_refresh(fakes) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    _save(m, _REAL)
    _connect(calls, _REAL)
    ssm = model()
    key = ssm.property("devices")[0]["key"]
    ssm.setDeviceChoice(key, "manual")
    assert m._saved_pairs() == []  # noqa: SLF001
    assert ssm.property("devices")[0]["choice"] == "manual"
    _save(m, _REAL, _VJOY_ID)
    assert _by_name(m.saved_devices())[_REAL[0]]["choice"] == "manual"
    ssm.setDeviceChoice(key, "nonsense")
    ssm.setDeviceChoice("no such key", "automatic")
    assert m._saved_pairs() == []  # noqa: SLF001
    ssm.setDeviceChoice(key, "automatic")
    assert m._saved_pairs() == [_REAL[:2]]  # noqa: SLF001


def test_helper_is_wanted_only_with_an_automatic_row(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    _manager, calls, model, m = fakes
    ssm = model()
    ssm.setEnabled(True)
    cfg = Configuration()
    assert cfg.value(m.SECTION, m.GROUP, m.OFF_ON) is True
    _save(m, _VJOY)
    m.ensure_helper()
    assert calls.disabler.starts == 0 and m.helper_wanted() is False
    _save(m, _REAL)
    key = _by_name(m.saved_devices())[_REAL[0]]["key"]
    calls.disabler.answer = (False, "declined")
    ssm.setDeviceChoice(key, "manual")
    assert calls.disabler.starts == 0 and m.helper_wanted() is False
    # Automatic again starts it, connected or not.
    calls.present = []
    ssm.setDeviceChoice(key, "automatic")
    assert calls.disabler.starts == 1 and m.helper_wanted() is True


def test_rows_of_the_old_form_are_dropped(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    _manager, calls, model, m = fakes
    Configuration().set(
        m.SECTION,
        m.GROUP,
        m.DEVICES,
        [{"name": _REAL[0], "instance_id": _REAL[1], "rate": 1.0, "switch_off": True}],
    )
    _connect(calls, _REAL)
    assert m.saved_devices() == [] and m._saved_pairs() == []  # noqa: SLF001
    assert model().property("devices") == []
    assert m.helper_wanted() is False


def test_choice_and_remove_are_traced_by_name(
    fakes,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import trace

    _manager, _calls, model, m = fakes
    _save(m, _REAL)
    ssm = model()
    key = ssm.property("devices")[0]["key"]
    lines: list[str] = []
    monkeypatch.setattr(trace, "screen_saver", lambda text, *a, **k: lines.append(text))
    ssm.setDeviceChoice(key, "manual")
    ssm.setDeviceChoice(key, "automatic")
    ssm.removeDevice(key)
    assert [t for t in lines if t.startswith("Devices: ")] == [
        "Devices: VKBSim NXT, manual",
        "Devices: VKBSim NXT, automatic",
        "Devices: VKBSim NXT, removed",
    ]
