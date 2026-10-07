# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 2, devices and HidHide (spec pages 02 and 03).

GL-035 the device list is swapped in whole, GL-045 twin names are written
on the main thread, GL-124 one shown name, GL-132 stale twin names, GL-133
a refused HidHide tick is not saved, GL-134 HidHide reloads only while its
window is open, GL-136 Device Information lists left-out devices, GL-148
Calibration marks unclaimed axes. Fake driver only: nothing here touches
real HidHide, vJoy or ViGEm.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import collections
import ctypes
import json
import pathlib
import threading
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest
from PySide6 import QtCore

import dill
from gremlin import device_initialization as di
from gremlin.config import Configuration
from vjoy import vjoy


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    yield QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture
def scan(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A first scan from an empty list; settings and state put back after."""
    monkeypatch.setattr(di, "_joystick_devices", collections.OrderedDict())
    monkeypatch.setattr(di, "_left_out", set())
    monkeypatch.setattr(di, "_vjoy_problems", [])
    monkeypatch.setattr(di, "_told", ())
    monkeypatch.setattr(di, "_window_up", False)
    monkeypatch.setattr(di, "_own_pads", [], raising=False)
    monkeypatch.setattr("gremlin.modules.output.reset_vjoy", lambda: None)
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: None)
    stored = Configuration().value(*di.TWIN_SETTING)
    Configuration().set(*di.TWIN_SETTING, {})
    yield
    Configuration().set(*di.TWIN_SETTING, stored)


def _extra_device(
    monkeypatch: pytest.MonkeyPatch, name: bytes, data1: int, of: int = 0
) -> dill._DeviceSummary:
    """Another device in the fake driver, a copy of device `of` with its own
    id and name."""
    fake = dill.DILL._dll
    dev = dill._DeviceSummary()
    ctypes.memmove(
        ctypes.byref(dev), ctypes.byref(fake.devices[of]), ctypes.sizeof(dev)
    )
    dev.device_guid.Data1 = data1
    dev.name = name
    monkeypatch.setattr(fake, "devices", [*fake.devices, dev])
    return dev


def _key(dev: dill._DeviceSummary) -> str:
    return str(dill.GUID(dev.device_guid).uuid).upper()


# --- GL-035: the list is built aside and swapped in -------------------------


def test_a_reader_holding_the_list_sees_it_whole_while_a_scan_runs(
    monkeypatch: pytest.MonkeyPatch, scan: None
) -> None:
    di.joystick_devices_initialization()
    before = list(di._joystick_devices.keys())
    seen_mid_scan: list[int] = []
    armed = False

    class Watched(collections.OrderedDict):
        # A reader on another thread, at the moment the scan writes.
        def __setitem__(self, key: object, value: object) -> None:
            super().__setitem__(key, value)
            if armed:
                seen_mid_scan.append(len(di.joystick_devices()))

        def clear(self) -> None:
            super().clear()
            if armed:
                seen_mid_scan.append(len(di.joystick_devices()))

    held = Watched(di._joystick_devices)
    armed = True
    monkeypatch.setattr(di, "_joystick_devices", held)
    _extra_device(monkeypatch, b"Other Stick", 0x7F000000)
    di.joystick_devices_initialization()

    assert seen_mid_scan == []  # never seen empty or half filled
    assert list(held.keys()) == before  # the old list stays whole
    assert "Other Stick" in [d.name for d in di.physical_devices()]


def test_scans_and_reads_in_parallel_never_see_a_partial_list(
    monkeypatch: pytest.MonkeyPatch, scan: None
) -> None:
    di.joystick_devices_initialization()
    full = len(di.joystick_devices())
    fake = dill.DILL._dll
    base = list(fake.devices)
    extra = _extra_device(monkeypatch, b"Other Stick", 0x7F000001)
    stop = threading.Event()
    bad: list[object] = []

    def read() -> None:
        while not stop.is_set():
            try:
                count = len(di.joystick_devices())
            except RuntimeError as exc:  # changed size during iteration
                bad.append(exc)
                return
            if count < full:
                bad.append(count)
                return

    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    reader = threading.Thread(target=read, name="test reader")
    reader.start()
    try:
        for i in range(300):
            fake.devices = [*base, extra] if i % 2 == 0 else list(base)
            di.joystick_devices_initialization()
            if bad:
                break
    finally:
        stop.set()
        reader.join(5)
        sys.setswitchinterval(old)
    assert bad == []


# --- GL-045: twin names are written on the main thread ----------------------


def test_twin_names_from_the_hot_plug_thread_are_written_on_the_main_thread(
    monkeypatch: pytest.MonkeyPatch, scan: None
) -> None:
    twin = _extra_device(monkeypatch, b"pJoy Pro", 0x7F000002)
    writes: list[tuple[bool, object]] = []
    real_set = Configuration.set

    def watched_set(self: Configuration, *args: object) -> None:
        if tuple(args[:3]) == di.TWIN_SETTING:
            main = threading.current_thread() is threading.main_thread()
            writes.append((main, args[3]))
        real_set(self, *args)

    monkeypatch.setattr(Configuration, "set", watched_set)
    worker = threading.Thread(
        target=di.joystick_devices_initialization, name="device list update"
    )
    worker.start()
    worker.join(10)
    assert writes == []  # not from the timer thread
    # The next scan already uses the name, before the write lands.
    assert di._stored_twins() == {_key(twin): "pJoy Pro (2)"}
    for _ in range(20):
        QtCore.QCoreApplication.processEvents()
        if writes:
            break
    assert writes == [(True, {_key(twin): "pJoy Pro (2)"})]
    assert Configuration().value(*di.TWIN_SETTING) == {_key(twin): "pJoy Pro (2)"}


# --- GL-132: a stored twin name only while the driver's name matches --------


def test_a_stale_twin_name_is_dropped(
    monkeypatch: pytest.MonkeyPatch, scan: None, tmp_path: pathlib.Path
) -> None:
    from gremlin.modules import store

    first = _key(dill.DILL._dll.devices[0])
    gone = "{00000000-0000-0000-0000-0000000000AA}".strip("{}")
    # Kept while it has a module file (D-02-GL243-FORGET).
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    (tmp_path / "away_stick_2.json").write_text(
        '{"device": "Away Stick (2)"}', encoding="utf-8"
    )
    Configuration().set(
        *di.TWIN_SETTING, {first: "Old Firmware Name (2)", gone: "Away Stick (2)"}
    )
    di.joystick_devices_initialization()
    assert [d.name for d in di.physical_devices()] == ["pJoy Pro"]
    # The stale entry is gone; a stick that isn't plugged in keeps its own
    # while it has a module file.
    assert Configuration().value(*di.TWIN_SETTING) == {gone: "Away Stick (2)"}


def test_a_matching_twin_name_is_kept_when_the_stick_is_alone(
    scan: None,
) -> None:
    first = _key(dill.DILL._dll.devices[0])
    Configuration().set(*di.TWIN_SETTING, {first: "pJoy Pro (2)"})
    di.joystick_devices_initialization()
    assert [d.name for d in di.physical_devices()] == ["pJoy Pro (2)"]  # S15
    assert Configuration().value(*di.TWIN_SETTING) == {first: "pJoy Pro (2)"}


# --- GL-124: one shown name -------------------------------------------------


@pytest.fixture
def aliases() -> Iterator[None]:
    from gremlin.ui import device_names

    device_names._ensure()
    before = Configuration().value(
        device_names.SECTION, device_names.GROUP, device_names.NAME
    )
    device_names._CACHE = None
    yield
    Configuration().set(
        device_names.SECTION, device_names.GROUP, device_names.NAME, before
    )
    device_names._CACHE = None


def test_one_shown_name_twin_vjoy_number_and_alias(
    monkeypatch: pytest.MonkeyPatch, scan: None, aliases: None
) -> None:
    from gremlin.ui import device_names

    twin = _extra_device(monkeypatch, b"pJoy Pro", 0x7F000003)
    di.joystick_devices_initialization()
    twin_id = dill.GUID(twin.device_guid)
    vjoy_dev = di.vjoy_devices()[0]
    assert di.shown_name(twin_id) == "pJoy Pro (2)"
    assert di.shown_name(vjoy_dev.device_guid) == f"vJoy Device {vjoy_dev.vjoy_id}"
    # An alias saved by the Home list ({ID} form) is found by any id form.
    device_names.set_alias(str(twin_id), "Left Stick")
    assert device_names.shown_name(twin_id.uuid) == "Left Stick"
    assert device_names.display_name(str(twin_id.uuid).lower(), "x") == "Left Stick"
    device_names.set_alias(str(twin_id.uuid), "")
    assert device_names.shown_name(twin_id) == "pJoy Pro (2)"


def test_the_device_list_model_names_come_from_the_one_owner(
    monkeypatch: pytest.MonkeyPatch, scan: None
) -> None:
    from gremlin.ui.device import DeviceListModel

    di.joystick_devices_initialization()
    model = DeviceListModel()
    role = next(k for k, v in model.roles.items() if bytes(v.data()) == b"name")
    with mock.patch.object(di, "shown_name", return_value="shown") as owner:
        name = model.data(model.index(0, 0), role)
    assert name == "shown" and owner.called
    model.deleteLater()


# --- GL-136: Device Information lists every device --------------------------


def test_device_information_lists_left_out_vjoy_and_own_xbox_pads(
    monkeypatch: pytest.MonkeyPatch, scan: None
) -> None:
    from gremlin.ui.device import DeviceListModel

    pad = _extra_device(monkeypatch, b"Controller (XBOX 360 For Windows)", 0x7F000004)
    pad_key = _key(pad)
    monkeypatch.setattr(
        "vigem.ids.is_vigem_xbox_summary",
        lambda info: str(info.device_guid.uuid).upper() == pad_key,
    )
    monkeypatch.setattr(vjoy, "hat_configuration_valid", lambda i: False)
    di.joystick_devices_initialization()
    assert di.vjoy_devices() == []  # left out of the program

    model = DeviceListModel()
    model.deviceType = "information"
    roles = {bytes(v.data()).decode(): k for k, v in model.roles.items()}
    rows = [
        (
            model.data(model.index(i, 0), roles["name"]),
            model.data(model.index(i, 0), roles["note"]),
        )
        for i in range(model.rowCount())
    ]
    model.deleteLater()
    assert ("pJoy Pro", "") in rows
    assert ("vJoy Device", "left out (see message)") in rows
    assert ("Controller (XBOX 360 For Windows)", "this program's Xbox pad") in rows


# --- GL-133: a refused HidHide tick is not saved ----------------------------


def test_a_hidhide_tick_the_driver_refuses_is_not_saved() -> None:
    from gremlin.ui import hidhide as hh

    page = SimpleNamespace(
        _present=True, _devices=[], _last_error="", reload=lambda: None
    )
    saved: list[list[str]] = []
    with mock.patch.object(hh, "_hidhide_managed", return_value=True), \
            mock.patch.object(hh, "_saved_hidden", return_value=[]), \
            mock.patch.object(hh, "_save_hidden", side_effect=saved.append), \
            mock.patch.object(hh, "set_blacklist", return_value=False):
        ok = hh.HidHideModel.setDeviceHidden(page, r"HID\VID_1&PID_2\1", True)
    assert ok is False and saved == []
    assert page._last_error

    with mock.patch.object(hh, "_hidhide_managed", return_value=True), \
            mock.patch.object(hh, "_saved_hidden", return_value=[]), \
            mock.patch.object(hh, "_save_hidden", side_effect=saved.append), \
            mock.patch.object(hh, "set_blacklist", return_value=True):
        ok = hh.HidHideModel.setDeviceHidden(page, r"HID\VID_1&PID_2\1", True)
    assert ok is True and saved == [[r"HID\VID_1&PID_2\1"]]


# --- GL-134: HidHide reloads on a device change only while its window is open


def test_hidhide_stops_reloading_when_its_window_is_closed() -> None:
    import shiboken6

    from gremlin import event_handler
    from gremlin.ui import hidhide as hh

    scans: list[bool] = []
    with mock.patch.object(hh, "driver_present", return_value=False), \
            mock.patch.object(
                hh, "list_hid_devices", side_effect=lambda g: scans.append(g) or []
            ):
        page = hh.HidHideModel()
        assert len(scans) == 1
        event_handler.EventListener().device_change_event.emit()
        assert len(scans) == 2  # open: re-reads its list (S34)
        shiboken6.delete(page)  # the window (and its model) closed
        event_handler.EventListener().device_change_event.emit()
        assert len(scans) == 2


# --- GL-148: Calibration marks unclaimed axes -------------------------------


def test_calibration_lists_every_axis_and_marks_unclaimed_ones(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, scan: None
) -> None:
    from pathlib import Path

    from gremlin.ui import device as ui_device

    di.joystick_devices_initialization()
    stick = di.physical_devices()[0]
    path = Path(str(tmp_path)) / "pjoy_pro.json"
    path.write_text(json.dumps({
        "device": "pJoy Pro", "direction": "source",
        "boundGuidLocal": str(stick.device_guid.uuid).upper(),
        "claim": {"buttons": [], "axes": [1, 3], "hats": [], "keys": []},
    }), encoding="utf-8")
    row = {"key": "pjoy_pro", "slug": "pjoy_pro", "guid": str(stick.device_guid),
           "path": path, "name": "pJoy Pro", "rebind": False}
    monkeypatch.setattr(
        "gremlin.modules.calibration.module_for_slug",
        lambda slug: row if slug == "pjoy_pro" else None,
    )
    model = ui_device.AxisCalibration()
    model.moduleSlug = "pjoy_pro"
    roles = {bytes(v.data()).decode(): k for k, v in model.roles.items()}
    marks = {
        stick.axis_map[i].axis_index: model.data(model.index(i, 0), roles["claimed"])
        for i in range(model.rowCount())
    }
    model.deleteLater()
    assert len(marks) == stick.axis_count  # every axis listed
    assert {axis for axis, claimed in marks.items() if claimed} == {1, 3}


def test_ids_compare_without_braces_or_case() -> None:
    from gremlin.ui import device_names

    uid = uuid.uuid4()
    assert device_names._same_key("{" + str(uid).upper() + "}") == (
        device_names._same_key(str(uid))
    )
    assert device_names._same_key("keyboard") == "keyboard"
