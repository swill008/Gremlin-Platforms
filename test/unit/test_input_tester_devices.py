# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester devices.py: DirectInput index base and the HID left-out list.

No real device or driver: dill.DILL and the Win32 HID calls are faked.
"""

from __future__ import annotations

import ctypes
import types

import pytest

from gremlin.input_tester import devices

GUID = "{03357CA0-0000-0000-0000-000000000001}"


class _FakeDill:
    """dill.DILL stand-in with the bundled reader's index checks.

    The bundled reader is upstream R16's dill2 (DILL v2.0, D-02-DILL2):
    values are 1-based and buttons 1-128 / hats 1-4 are accepted, as
    v1.5's source sizes them (129 / 5); anything else is rejected.
    """

    def __init__(self, pressed: set[int], hats: dict[int, int]) -> None:
        self.pressed = pressed
        self.hat_values = hats
        self.button_calls: list[int] = []
        self.hat_calls: list[int] = []
        self.invalid: list[str] = []

    def get_axis(self, _guid, index: int) -> int:  # noqa: ANN001
        if index < 1 or index > 8:
            self.invalid.append(f"axis {index}")
        return 0

    def get_button(self, _guid, index: int) -> bool:  # noqa: ANN001
        self.button_calls.append(index)
        if index < 1 or index > 128:
            self.invalid.append(f"Requested invalid button index {index}")
            return False
        return index in self.pressed

    def get_hat(self, _guid, index: int) -> int:  # noqa: ANN001
        self.hat_calls.append(index)
        if index < 1 or index > 4:
            self.invalid.append(f"Requested invalid hat index {index}")
            return -1
        return self.hat_values.get(index, -1)


def _device(buttons: int, hats: int) -> devices.SeenDevice:
    return devices.SeenDevice(
        key=f"di:{GUID}",
        kind="directinput",
        name="VKB stick",
        guid=GUID,
        axes=2,
        buttons=buttons,
        hats=hats,
        axis_ids=[1, 2],
        handle=devices.dill.GUID.from_str(GUID.strip("{}")),
    )


def test_directinput_indexes_in_range_and_button_n_is_dinput_n(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDill(pressed={1, 5, 128}, hats={1: 9000, 4: 18000})
    monkeypatch.setattr(devices.dill, "DILL", fake)

    values = devices.directinput_values(_device(buttons=128, hats=4))

    assert fake.invalid == []  # no "invalid index" line in dill_debug.log
    assert max(fake.button_calls) == 128 and min(fake.button_calls) == 1
    assert max(fake.hat_calls) == 4 and min(fake.hat_calls) == 1
    assert len(values.buttons) == 128 and len(values.hats) == 4
    # On-screen button N (list index N-1) is DirectInput button N.
    shown = {i + 1 for i, on in enumerate(values.buttons) if on}
    assert shown == {1, 5, 128}
    assert values.hats == [90, -1, -1, 180]


def test_directinput_read_noted_for_log(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeDill(pressed=set(), hats={})
    monkeypatch.setattr(devices.dill, "DILL", fake)
    monkeypatch.setattr(devices, "_open_results", {})
    devices.directinput_values(_device(buttons=4, hats=1))
    (result,) = devices.last_open_results()
    assert (result.kind, result.instance, result.ok, result.text) == (
        "directinput",
        GUID,
        True,
        "values read ok",
    )


# HID ------------------------------------------------------------------------

INVALID = ctypes.c_void_p(-1).value
DENIED = r"\\?\hid#vid_231d&pid_0200#7&1&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
STICK = r"\\?\hid#vid_231d&pid_0201#7&2&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
MOUSE = r"\\?\hid#vid_046d&pid_c077#7&3&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
BROKEN = r"\\?\hid#vid_1111&pid_2222#7&4&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"
GONE = r"\\?\hid#vid_3333&pid_4444#7&5&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"

# path -> (CreateFile last error or 0, preparsed ok, usage page, usage, name)
_PATHS = {
    DENIED: (5, True, 0x01, 0x04, ""),
    STICK: (0, True, 0x01, 0x04, "VKB Gladiator"),
    MOUSE: (0, True, 0x01, 0x02, "USB Mouse"),
    BROKEN: (0, False, 0, 0, "Odd thing"),
    GONE: (2, True, 0, 0, ""),
}


def _fake_libs():  # noqa: ANN202
    handles: dict[int, str] = {}

    def create_file(path, *_args):  # noqa: ANN001, ANN002, ANN202
        error = _PATHS[path][0]
        if error:
            ctypes.set_last_error(error)
            return INVALID
        handle = 100 + len(handles)
        handles[handle] = path
        return handle

    def deref(ref):  # noqa: ANN001, ANN202
        return ref._obj  # noqa: SLF001

    def get_preparsed(handle, ref):  # noqa: ANN001, ANN202
        if not _PATHS[handles[handle]][1]:
            ctypes.set_last_error(87)
            return False
        deref(ref).value = handle
        return True

    def get_caps(preparsed, ref):  # noqa: ANN001, ANN202
        _e, _ok, page, usage, _n = _PATHS[handles[preparsed.value]]
        caps = deref(ref)
        caps.UsagePage, caps.Usage = page, usage
        return 0x00110000

    def get_attributes(handle, ref):  # noqa: ANN001, ANN202
        path = handles[handle]
        vid, pid = devices._hid_vid_pid(path)  # noqa: SLF001
        attrs = deref(ref)
        attrs.VendorID, attrs.ProductID = vid, pid
        return True

    def get_product(handle, buf, _size):  # noqa: ANN001, ANN202
        name = _PATHS[handles[handle]][4]
        if not name:
            return False
        ctypes.memmove(buf, ctypes.create_unicode_buffer(name), (len(name) + 1) * 2)
        return True

    closed: list[int] = []
    k32 = types.SimpleNamespace(CreateFileW=create_file, CloseHandle=closed.append)
    hid = types.SimpleNamespace(
        HidD_GetPreparsedData=get_preparsed,
        HidD_FreePreparsedData=lambda _p: True,
        HidP_GetCaps=get_caps,
        HidD_GetAttributes=get_attributes,
        HidD_GetProductString=get_product,
    )
    return k32, hid, handles, closed


@pytest.fixture
def fake_hid(monkeypatch: pytest.MonkeyPatch) -> tuple:
    k32, hid, handles, closed = _fake_libs()
    monkeypatch.setattr(devices.os, "name", "nt")
    monkeypatch.setattr(devices, "_hid_libs", lambda: (None, hid, k32))
    monkeypatch.setattr(devices, "_hid_paths", lambda _s, _h: list(_PATHS))
    monkeypatch.setattr(devices, "_open_results", {})
    return handles, closed


def test_access_denied_open_is_kept_as_skip(fake_hid: tuple) -> None:
    kept, skipped = devices.hid_scan()
    by_path = {s.path: s for s in skipped}

    denied = by_path[DENIED]
    assert denied.reason == "access denied (5)"
    assert denied.code == 5 and denied.denied
    assert (denied.vid, denied.pid) == (0x231D, 0x0200)

    assert [d.path for d in kept] == [STICK]
    assert kept[0].name == "VKB Gladiator"
    assert devices.last_hid_skips() == skipped
    assert devices.hid_devices() == kept


def test_every_left_out_path_has_a_reason(fake_hid: tuple) -> None:
    _handles, closed = fake_hid
    _kept, skipped = devices.hid_scan()
    by_path = {s.path: s for s in skipped}
    assert set(by_path) == {DENIED, MOUSE, BROKEN, GONE}

    mouse = by_path[MOUSE]
    assert mouse.reason == "not a game device (usage page 0x0001, usage 0x0002)"
    assert (mouse.code, mouse.usage_page, mouse.usage) == (0, 1, 2)
    assert mouse.name == "USB Mouse" and not mouse.denied

    broken = by_path[BROKEN]
    assert broken.reason == "no preparsed data (error 87)" and broken.code == 87

    gone = by_path[GONE]
    assert gone.code == 2 and gone.reason.startswith("error 2: ")
    assert len(closed) == 3  # every opened handle is closed


def test_open_results_for_the_log(fake_hid: tuple) -> None:
    devices.hid_scan()
    results = {r.instance: r for r in devices.last_open_results()}
    assert (results[DENIED].ok, results[DENIED].code, results[DENIED].text) == (
        False,
        5,
        "access denied (5)",
    )
    assert (results[STICK].ok, results[STICK].text, results[STICK].left_out) == (
        True,
        "ok",
        "",
    )
    assert results[MOUSE].ok and results[MOUSE].left_out.startswith("not a game device")
    assert results[BROKEN].ok and results[BROKEN].left_out.startswith(
        "no preparsed data"
    )
    assert not results[GONE].ok and results[GONE].code == 2


def test_describe_open_error() -> None:
    assert devices.describe_open_error(5) == "access denied (5)"
    assert devices.describe_open_error(2).startswith("error 2: ")
