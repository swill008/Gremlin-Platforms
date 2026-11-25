# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode's remembered Devices list (12 S12, S27, S43): Refresh
Devices never removes a row, Remove does, rows are recognised in any USB
port, and only what is connected at the power-off goes to the disabler."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ssm_ui_fakes  # noqa: E402
import test_ssm_device_switch as _sw  # noqa: E402  # pyright: ignore

from gremlin.device_key import device_key  # noqa: E402

fakes = _sw.fakes
STEAM_3 = r"HID\VID_28DE&PID_1302&COL03\A&E40AA7B&0&0002"
STEAM_1 = r"HID\VID_28DE&PID_1302&COL01\A&E40AA7B&0&0000"
MIC = r"HID\VID_352F&PID_0104&MI_03\B&12148D1&0&0000"
VKB = r"HID\VID_231D&PID_0200\A&6B6F223&0&0000"
VKB_PORT = r"HID\VID_231D&PID_0200\7&1111111&0&0000"


def _refresh(ssm, qapp, calls, *devices) -> list[dict]:  # noqa: ANN001, ANN002
    calls.devices = [ssm_ui_fakes.DeviceRate(n, i, 1, 4, r) for n, i, r in devices]
    ssm.refreshDevices()
    assert _sw._ui._wait(qapp, lambda: not ssm.property("scanningDevices"))  # noqa: SLF001
    return ssm.property("devices")


def test_refresh_keeps_a_missing_device_choice_and_last_seen(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    assert ssm.property("devicesSummary") == "No devices yet"
    rows = _refresh(ssm, qapp, calls, ("Mic", MIC, 18.0), ("VKB", VKB, 13.0))
    assert [(r["name"], r["choice"], r["found"], r["foundText"]) for r in rows] == [
        ("Mic", "automatic", True, ""),
        ("VKB", "automatic", True, ""),
    ]
    assert set(rows[0]) == {
        "key",
        "name",
        "rate",
        "choice",
        "virtual",
        "found",
        "foundText",
    }
    assert ssm.property("devicesSummary") == "2 automatic"
    assert ssm.property("devicesMessage").endswith(" · 2 found")
    mic = device_key("Mic", MIC)
    ssm.setDeviceChoice(mic, "manual")
    seen = {r["key"]: r["last_seen"] for r in m.saved_devices()}
    assert seen[mic]
    rows = _refresh(ssm, qapp, calls, ("VKB", VKB, 9.0))
    assert [r["name"] for r in rows] == ["VKB", "Mic"]
    assert (rows[1]["choice"], rows[1]["found"], rows[1]["rate"]) == (
        "manual",
        False,
        0.0,
    )
    assert rows[1]["foundText"].startswith("Not found · last seen")
    saved = {r["key"]: r for r in m.saved_devices()}
    assert saved[mic]["last_seen"] == seen[mic]
    assert ssm.property("devicesSummary") == "1 automatic · 1 manual · 1 not found"
    assert ssm.property("devicesMessage").startswith("Checked ")
    assert ssm.property("devicesMessage").endswith(" · 1 found, 1 not found")
    # After a restart it still reads Not found.
    assert model().property("devices") == rows


def test_a_device_in_another_usb_port_updates_its_row(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))
    ssm.setDeviceChoice(device_key("VKB", VKB), "manual")
    rows = _refresh(ssm, qapp, calls, ("VKB", VKB_PORT, 7.0))
    assert [(r["choice"], r["rate"], r["found"]) for r in rows] == [
        ("manual", 7.0, True)
    ]
    assert m.saved_devices()[0]["instance_ids"] == [VKB_PORT]


def test_remove_forgets_and_found_again_is_new(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))
    key = device_key("VKB", VKB)
    ssm.setDeviceChoice(key, "manual")
    ssm.removeDevice(key)
    assert ssm.property("devices") == [] and m.saved_devices() == []
    assert ssm.property("devicesSummary") == "No devices yet"
    ssm.removeDevice(key)  # unknown: nothing happens
    assert _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))[0]["choice"] == "automatic"


def test_two_identical_devices_share_a_row_and_both_are_switched_off(
    fakes,  # noqa: ANN001
    qapp,  # noqa: ANN001
) -> None:
    _manager, calls, model, m = fakes
    ssm = model()
    rows = _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0), ("VKB", VKB_PORT, 5.0))
    assert [(r["name"], r["rate"]) for r in rows] == [("VKB", 13.0)]
    assert m._saved_pairs() == [("VKB", VKB), ("VKB", VKB_PORT)]  # noqa: SLF001
    assert calls.name_reads == []


def test_steam_controller_parts_are_separate_rows(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    name = "Steam Controller"
    rows = _refresh(ssm, qapp, calls, (name, STEAM_1, 9.0), (name, STEAM_3, 13.0))
    assert len(rows) == 2
    ssm.setDeviceChoice(device_key(name, STEAM_1), "manual")
    assert m._saved_pairs() == [(name, STEAM_3)]  # noqa: SLF001


def test_no_maker_or_model_matches_the_full_id_only(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("Pad", r"HID\CUSTOM\1", 5.0))
    calls.present = [("Pad", r"HID\CUSTOM\2"), ("Pad", r"HID\Custom\1")]
    assert m._saved_pairs() == [("Pad", r"HID\Custom\1")]  # noqa: SLF001


def test_the_power_off_takes_the_ports_in_use_then(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0), ("Mic", MIC, 18.0))
    calls.disabler.running = True
    calls.present = [("VKB", VKB_PORT), ("Other", r"HID\VID_1&PID_2\1")]
    answer = m._before_power_off()  # noqa: SLF001
    assert answer is not None and answer.asked == 1
    assert calls.disabler.disabled == [[("VKB", VKB_PORT)]]
    calls.present = []
    assert m._before_power_off() is None  # noqa: SLF001
    assert len(calls.disabler.disabled) == 1


def test_names_are_read_only_for_rows_sharing_their_numbers(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("A", VKB, 9.0), ("B", VKB_PORT, 8.0), ("Mic", MIC, 7.0))
    ssm.setDeviceChoice(device_key("A", VKB), "manual")
    # The two swapped ports: the name decides, not the id.
    calls.present = [("B", VKB), ("A", VKB_PORT), ("C", VKB + "9"), ("Mic", MIC)]
    assert m._saved_pairs() == [("B", VKB), ("Mic", MIC)]  # noqa: SLF001
    assert calls.name_reads == [VKB, VKB_PORT, VKB + "9"]
    # A name that can't be read: the row last found with that id.
    calls.unreadable_names = True
    assert m._saved_pairs() == [("B", VKB_PORT), ("Mic", MIC)]  # noqa: SLF001


def test_a_failed_lookup_leaves_the_devices_alone(
    fakes,  # noqa: ANN001
    qapp,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin

    _manager, calls, model, m = fakes
    _refresh(model(), qapp, calls, ("VKB", VKB, 13.0))
    calls.disabler.running = True

    def broken() -> list:
        raise OSError("no HID")

    monkeypatch.setattr(gremlin.hid_report_scan, "present", broken)  # type: ignore[attr-defined]
    assert m._before_power_off() is None  # noqa: SLF001
    assert calls.disabler.disabled == []


def test_a_failed_or_stopped_scan_keeps_the_list(
    fakes,  # noqa: ANN001
    qapp,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin

    _manager, calls, model, m = fakes
    ssm = model()
    rows = _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))
    saved = m.saved_devices()

    def broken(*_a: object, **_k: object) -> list:
        raise OSError("no HID")

    with monkeypatch.context() as patch:
        patch.setattr(gremlin.hid_report_scan, "scan", broken)  # type: ignore[attr-defined]
        assert _refresh(ssm, qapp, calls) == rows
    assert ssm.property("devicesMessage") == "The devices couldn't be checked: no HID"

    def stopped(*_a: object, **_k: object) -> list:
        ssm.setOpen(False)  # the window closed during the check
        return []

    with monkeypatch.context() as patch:
        patch.setattr(gremlin.hid_report_scan, "scan", stopped)  # type: ignore[attr-defined]
        assert _refresh(ssm, qapp, calls) == rows
    assert m.saved_devices() == saved


def test_found_text_today_and_by_date(fakes) -> None:  # noqa: ANN001
    _manager, _calls, _model, m = fakes
    now = datetime(2026, 11, 24, 18, 0)
    row = {"rate": 0.0, "last_seen": "2026-11-24T16:27:05"}
    assert m.found_text(row, now) == "Not found · last seen today 16:27"
    row["last_seen"] = "2026-11-20T16:27:05"
    assert m.found_text(row, now) == "Not found · last seen 2026-11-20"
    assert m.found_text({**row, "last_seen": ""}, now) == "Not found"
    assert m.found_text({**row, "rate": 3.0}, now) == ""


def _rows(automatic: int, manual: int, missing: int) -> list[dict]:
    rows = [{"choice": "automatic", "rate": 5.0} for _ in range(automatic)]
    rows += [{"choice": "manual", "rate": 5.0} for _ in range(manual)]
    for r in rows[:missing]:
        r["rate"] = 0.0
    return rows


@pytest.mark.parametrize(
    ("counts", "text"),
    [
        ((4, 1, 1), "4 automatic · 1 manual · 1 not found"),
        ((4, 0, 0), "4 automatic"),
        ((0, 2, 0), "2 manual"),
        ((0, 1, 1), "1 manual · 1 not found"),
        ((0, 0, 0), "No devices yet"),
    ],
)
def test_summary(fakes, counts: tuple, text: str) -> None:  # noqa: ANN001
    assert fakes[3].devices_summary(_rows(*counts)) == text


def test_virtual_devices_do_not_count(fakes: tuple) -> None:
    virtual = {**_rows(0, 1, 0)[0], "virtual": True}
    text = fakes[3].devices_summary([*_rows(2, 1, 0), virtual])
    assert text == "2 automatic · 1 manual"


def test_checked_text_when_nothing_is_found(fakes, qapp) -> None:  # noqa: ANN001
    _manager, calls, model, _m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls)
    assert ssm.property("devicesMessage").endswith(
        " · No device is sending reports all the time."
    )
    _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))
    _refresh(ssm, qapp, calls)
    assert ssm.property("devicesMessage").endswith(" · 1 not found")


class _Hid:
    """HidApi stand-in: records what is opened."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.closed: list[object] = []

    def interfaces(self) -> list[tuple[str, str, str]]:
        return [("path1", VKB, "HID device"), ("path2", MIC, "Mic part")]

    def open(self, path: str) -> object | None:
        self.opened.append(path)
        return path if path == "path1" else None

    def product(self, handle: object) -> str:
        return ""

    def close(self, handle: object) -> None:
        self.closed.append(handle)


def test_the_real_lookup_opens_nothing_and_refuses_under_pytest() -> None:
    import importlib

    scan = importlib.import_module("gremlin.hid_report_scan")
    api = _Hid()
    found = scan.present(api)
    assert [d.instance_id for d in found] == [VKB, MIC]
    assert api.opened == []
    assert scan.device_name(found[0], api) == "HID device"
    assert scan.device_name(found[1], api) == ""
    assert api.closed == ["path1"]
    with pytest.raises(RuntimeError, match="tests never read"):
        scan.present()


def test_removing_the_last_automatic_row_ends_the_need_for_the_helper(
    fakes,  # noqa: ANN001
    qapp,  # noqa: ANN001
) -> None:
    _manager, calls, model, m = fakes
    ssm = model()
    _refresh(ssm, qapp, calls, ("VKB", VKB, 13.0))
    ssm.setEnabled(True)
    assert m.helper_wanted() is True
    ssm.removeDevice(device_key("VKB", VKB))
    assert m.helper_wanted() is False


def test_the_setting_is_not_recorded_in_history_as_before(fakes, qapp) -> None:  # noqa: ANN001
    from gremlin import config

    assert (
        "global",
        "screen-saver-mode",
    ) in config.Configuration._NOT_IN_HISTORY_GROUPS  # noqa: SLF001
