# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Which Windows device a DirectInput device is: its HID instance path.

Twins (identical sticks) share a name, VID and PID, and DirectInput hands
out instance GUIDs per process (a program that sees only one twin may give
it the other twin's GUID). The HID instance path is the one identity both
Gremlin and the Input Tester agree on, and it is what HidHide's hidden list
holds. Asked of DirectInput (DIPROP_GUIDANDPATH) in the calling process;
"" when it can't be read. Reading only; never raises.
"""

from __future__ import annotations

import ctypes
import logging
import os
import threading
import uuid
from ctypes import wintypes

syslog = logging.getLogger("system")

_DIRECTINPUT_VERSION = 0x0800
_DIPROP_GUIDANDPATH = 12  # MAKEDIPROP(12)
_DIPH_DEVICE = 0
_MAX_PATH = 260
# IDirectInput8W / IDirectInputDevice8W vtable slots.
_RELEASE = 2
_CREATE_DEVICE = 3
_GET_PROPERTY = 5


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_uint8 * 8),
    ]

    @classmethod
    def of(cls, value: uuid.UUID) -> _GUID:
        f = value.fields
        tail = value.bytes[8:]
        return cls(f[0], f[1], f[2], (ctypes.c_uint8 * 8)(*tail))


class _DIPROPHEADER(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwHeaderSize", wintypes.DWORD),
        ("dwObj", wintypes.DWORD),
        ("dwHow", wintypes.DWORD),
    ]


class _DIPROPGUIDANDPATH(ctypes.Structure):
    _fields_ = [
        ("diph", _DIPROPHEADER),
        ("guidClass", _GUID),
        ("wszPath", ctypes.c_wchar * _MAX_PATH),
    ]


_IID_IDirectInput8W = _GUID.of(uuid.UUID("BF798031-483A-4DA2-AA99-5D64ED369700"))

_lock = threading.Lock()
_di: ctypes.c_void_p | None = None


def instance_id(interface_path: str) -> str:
    r"""HID instance path from a device interface path:
    \\?\hid#vid_045e&pid_02ff&ig_00#8&325ecaab&0&0000#{...}
    -> HID\VID_045E&PID_02FF&IG_00\8&325ECAAB&0&0000. Upper case, as
    compared everywhere; "" when it isn't one."""
    text = str(interface_path or "").strip()
    if text.startswith(("\\\\?\\", "\\\\.\\")):
        text = text[4:]
    parts = text.split("#")
    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return ""
    return "\\".join(parts[:3]).upper()


def _method(obj: ctypes.c_void_p, slot: int, *argtypes: type) -> object:
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)  # type: ignore[arg-type]
    return proto(vtable[slot])


def _directinput() -> ctypes.c_void_p | None:
    global _di
    if _di is not None:
        return _di
    if os.name != "nt":
        return None
    dinput = ctypes.WinDLL("dinput8")
    create = dinput.DirectInput8Create
    create.argtypes = [
        wintypes.HINSTANCE, wintypes.DWORD, ctypes.POINTER(_GUID),
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
    ]
    create.restype = ctypes.c_long
    module_handle = ctypes.WinDLL("kernel32").GetModuleHandleW
    module_handle.argtypes = [wintypes.LPCWSTR]
    module_handle.restype = wintypes.HMODULE  # 64-bit: never the int default
    hinst = module_handle(None)
    out = ctypes.c_void_p()
    if create(hinst, _DIRECTINPUT_VERSION, ctypes.byref(_IID_IDirectInput8W),
              ctypes.byref(out), None) != 0 or not out.value:
        return None
    _di = out
    return _di


def _real_reader() -> bool:
    """The device list comes from the real reader; with a fake one (tests)
    the GUIDs are made up and DirectInput is never asked."""
    try:
        import dill

        return dill.DILL._dll is dill._di_listener_dll
    except Exception:  # noqa: BLE001
        return False


def _read(device_guid: uuid.UUID) -> str:
    if not _real_reader():
        return ""
    di = _directinput()
    if di is None:
        return ""
    guid = _GUID.of(device_guid)
    device = ctypes.c_void_p()
    create = _method(
        di, _CREATE_DEVICE, ctypes.POINTER(_GUID),
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
    )
    if create(di, ctypes.byref(guid), ctypes.byref(device), None) != 0:  # type: ignore[operator]
        return ""
    try:
        prop = _DIPROPGUIDANDPATH()
        prop.diph.dwSize = ctypes.sizeof(prop)
        prop.diph.dwHeaderSize = ctypes.sizeof(_DIPROPHEADER)
        prop.diph.dwObj = 0
        prop.diph.dwHow = _DIPH_DEVICE
        get = _method(device, _GET_PROPERTY, ctypes.c_void_p, ctypes.c_void_p)
        if get(device, ctypes.c_void_p(_DIPROP_GUIDANDPATH), ctypes.byref(prop)) != 0:  # type: ignore[operator]
            return ""
        return instance_id(prop.wszPath)
    finally:
        _method(device, _RELEASE)(device)  # type: ignore[operator]


def hid_instance(device_guid: uuid.UUID | str) -> str:
    """The HID instance path of this DirectInput device (upper case), or ""."""
    try:
        key = device_guid if isinstance(device_guid, uuid.UUID) else uuid.UUID(
            str(device_guid).strip().strip("{}")
        )
    except ValueError:
        return ""
    # Asked every time, never remembered: after a plug or unplug DirectInput
    # may hand the same GUID to the other twin.
    with _lock:
        try:
            return _read(key)
        except Exception:  # noqa: BLE001 - reading only, never raises
            syslog.debug("DirectInput device path not read", exc_info=True)
            return ""
