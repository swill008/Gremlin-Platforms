# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode's per-device Switch off (12 S12, S21, S27): on for a new
device, kept by instance id across a Refresh, off leaves the device alone,
virtual devices (vJoy, ViGEm) are never switched off."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_ssm_ui as _ui  # noqa: E402  # pyright: ignore

fakes = _ui.fakes

_REAL = {"name": "VKBSim NXT", "instanceId": r"HID\VID_3&PID_4\1", "rate": 2.0}
_VJOY = {
    "name": "vJoy - Virtual Joystick",
    "instanceId": r"HID\HIDCLASS\1",
    "rate": 1.0,
}
_VJOY_ID = {"name": "Joystick", "instanceId": r"HID\VID_1234&PID_BEAD\2", "rate": 1.0}


def _by_id(rows: list[dict]) -> dict:
    return {r["instanceId"]: r for r in rows}


def test_new_device_defaults_on_and_virtual_is_locked_off(fakes) -> None:  # noqa: ANN001
    _manager, _calls, _model, m = fakes
    m.save_devices([_REAL, _VJOY, _VJOY_ID])
    rows = _by_id(m.saved_devices())
    assert rows[_REAL["instanceId"]]["switchOff"] is True
    assert rows[_REAL["instanceId"]]["virtual"] is False
    for v in (_VJOY, _VJOY_ID):
        assert rows[v["instanceId"]]["virtual"] is True
        assert rows[v["instanceId"]]["switchOff"] is False
    assert m._saved_pairs() == [(_REAL["name"], _REAL["instanceId"])]  # noqa: SLF001


def test_choice_kept_across_refresh_and_off_leaves_device_alone(fakes) -> None:  # noqa: ANN001
    _manager, _calls, model, m = fakes
    m.save_devices([_REAL])
    ssm = model()
    ssm.setSwitchOff(_REAL["instanceId"], False)
    assert m._saved_pairs() == []  # noqa: SLF001
    assert ssm.property("devices")[0]["switchOff"] is False
    m.save_devices([_REAL, {**_VJOY_ID}])  # a Refresh: rows carry no choice
    rows = _by_id(m.saved_devices())
    assert rows[_REAL["instanceId"]]["switchOff"] is False
    ssm.setSwitchOff(_REAL["instanceId"], True)
    assert m._saved_pairs() == [(_REAL["name"], _REAL["instanceId"])]  # noqa: SLF001


def test_virtual_row_ignores_set_switch_off(fakes) -> None:  # noqa: ANN001
    _manager, _calls, model, m = fakes
    m.save_devices([_VJOY])
    ssm = model()
    ssm.setSwitchOff(_VJOY["instanceId"], True)
    assert m._saved_pairs() == []  # noqa: SLF001
    row = ssm.property("devices")[0]
    assert row["virtual"] is True and row["switchOff"] is False


def test_nothing_switched_off_means_no_helper(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    _manager, _calls, _model, m = fakes
    cfg = Configuration()
    cfg.set(m.SECTION, m.GROUP, m.ENABLED, True)
    cfg.set(m.SECTION, m.GROUP, m.OFF_ON, True)
    m.save_devices([_REAL, _VJOY])
    assert m.helper_wanted() is True
    m.save_devices([{**_REAL, "switchOff": False}, _VJOY])
    assert m.helper_wanted() is False
    m.save_devices([_VJOY])
    assert m.helper_wanted() is False


def test_old_saved_rows_without_the_key_read_as_on(fakes) -> None:  # noqa: ANN001
    from gremlin.config import Configuration

    _manager, _calls, _model, m = fakes
    Configuration().set(
        m.SECTION,
        m.GROUP,
        m.DEVICES,
        [
            {"name": _REAL["name"], "instance_id": _REAL["instanceId"], "rate": 1.0},
            {"name": _VJOY["name"], "instance_id": _VJOY["instanceId"], "rate": 1.0},
        ],
    )
    rows = _by_id(m.saved_devices())
    assert rows[_REAL["instanceId"]]["switchOff"] is True
    assert rows[_VJOY["instanceId"]]["switchOff"] is False
    assert m._saved_pairs() == [(_REAL["name"], _REAL["instanceId"])]  # noqa: SLF001
