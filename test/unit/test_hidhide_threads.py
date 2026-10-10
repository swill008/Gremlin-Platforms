# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hardware Hide's device walk makes no new ctypes classes per call
(SHAKE-STRESS-05).

ctypes keeps every structure class it has made a pointer type for, so a
class defined inside a function stays alive after each call: every open of
Hardware Hide used to leave five structure classes behind, plus one per
listed device and two per name lookup. The Windows calls are faked here;
no real SetupAPI, HID or HidHide call is made.
"""

from __future__ import annotations

import ctypes
import gc
import os
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from gremlin import hidhide_driver as hh

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows ctypes types")

_INSTANCE = "HID\\VID_1234&PID_5678\\7&1&0"
_LINK = "\\\\?\\hid#vid_1234&pid_5678#7&1&0#{4d1e55b2-f16f-11cf-88cb-001111000030}"


class _Fn:
    def __init__(self, impl: Callable[..., Any]) -> None:
        self._impl = impl
        self.argtypes = None
        self.restype = None

    def __call__(self, *args: Any) -> Any:  # noqa: ANN401
        return self._impl(*args)


def _size(ref: Any, _cls: str, _flags: int) -> int:  # noqa: ANN401
    ref._obj.value = len(_INSTANCE) + 2
    return 0


def _id_list(_cls: str, buf: Any, _n: int, _flags: int) -> int:  # noqa: ANN401
    for i, ch in enumerate(_INSTANCE):
        buf[i] = ch
    return 0


def _detail(*args: Any) -> int:  # noqa: ANN401
    _devs, _iface, detail, _size, needed, _x = args
    if detail is None:
        needed._obj.value = 4 + 2 * (len(_LINK) + 1)
        return 0
    src = ctypes.create_unicode_buffer(_LINK)
    ctypes.memmove(ctypes.addressof(detail._obj) + 4, src, ctypes.sizeof(src))
    return 1


_IMPLS = {
    "CM_Get_Device_ID_List_SizeW": _size,
    "CM_Get_Device_ID_ListW": _id_list,
    "SetupDiGetClassDevsW": lambda *a: 1234,
    "SetupDiEnumDeviceInterfaces": lambda *a: 1,
    "SetupDiGetDeviceInterfaceDetailW": _detail,
    "SetupDiDestroyDeviceInfoList": lambda *a: 1,
    "HidD_GetHidGuid": lambda *a: None,
    "CreateFileW": lambda *a: -1,
}


class _Dll:
    def __init__(self, *_a: object, **_k: object) -> None:
        self._fns: dict[str, _Fn] = {}

    def __getattr__(self, name: str) -> _Fn:
        if name.startswith("_"):
            raise AttributeError(name)
        fns = self.__dict__["_fns"]
        if name not in fns:
            # Anything else fails (CM_* calls: 1 is not CR_SUCCESS).
            fns[name] = _Fn(_IMPLS.get(name, lambda *a: 1))
        return fns[name]


@pytest.fixture
def fake_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ctypes, "WinDLL", _Dll)
    ctypes.set_last_error(0)


@pytest.fixture
def no_gc() -> Iterator[None]:
    # Classes made per call are counted before the collector could free one.
    gc.collect()
    gc.disable()
    yield
    gc.enable()


def _structure_classes() -> int:
    return len(ctypes.Structure.__subclasses__())


def test_device_walk_makes_no_new_structure_classes(
    fake_windows: None, no_gc: None
) -> None:
    rows = hh._list_hidhide_class_enum(False)
    assert [r["instanceId"] for r in rows] == [_INSTANCE]
    before = _structure_classes()
    for _ in range(5):
        rows = hh._list_hidhide_class_enum(False)
        assert [r["instanceId"] for r in rows] == [_INSTANCE]
    assert _structure_classes() == before


def test_property_lookups_make_no_new_structure_classes(
    fake_windows: None, no_gc: None
) -> None:
    hh._device_description(_INSTANCE)
    hh._container_id(_INSTANCE)
    before = _structure_classes()
    for _ in range(5):
        assert hh._device_description(_INSTANCE) == ""
        assert hh._container_id(_INSTANCE) == hh.GUID_NULL
    assert _structure_classes() == before
