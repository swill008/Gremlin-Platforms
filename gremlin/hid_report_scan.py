# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Refresh Devices (Screen Saver Mode S12): which HID devices never go quiet.

Opens every HID interface read-only, reads its input reports for a few
seconds and lists the ones that keep sending (a throttle or a microphone
that streams reports keeps Windows' idle clock at zero). Read-only: nothing
is written to any device. Keyboards and mice, which Windows keeps to itself,
can't be opened and are skipped. Runs on the caller's thread.

All Windows calls go through _Win32Hid; tests pass a fake with the same
methods."""

from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from gremlin import clock

MIN_RATE = 2.0  # reports per second worth listing
_WAIT_MS = 50  # longest single wait between checks
_DRAIN = 256  # most reports taken from one device in one round

DONE, PENDING, ERROR = "done", "pending", "error"


@dataclass
class DeviceRate:
    name: str
    instance_id: str
    usage_page: int
    usage: int
    reports_per_s: float


class HidApi(Protocol):
    """The Windows calls scan() makes; _Win32Hid is the real one."""

    def interfaces(self) -> list[tuple[str, str, str]]: ...
    def open(self, path: str) -> object | None: ...
    def info(self, handle: object) -> tuple[int, int, int] | None: ...
    def product(self, handle: object) -> str: ...
    def new_read(self, handle: object, length: int) -> object: ...
    def submit(self, op: object) -> str: ...
    def check(self, op: object) -> str: ...
    def wait(self, ops: list, timeout_ms: int) -> None: ...
    def cancel(self, op: object) -> None: ...
    def free(self, op: object) -> None: ...
    def close(self, handle: object) -> None: ...


@dataclass
class _Device:
    handle: object
    name: str = ""
    instance_id: str = ""
    usage_page: int = 0
    usage: int = 0
    op: object = None
    state: str = ""
    count: int = 0


def scan(
    seconds: float = 4.0,
    should_stop: Callable[[], bool] | None = None,
    api: HidApi | None = None,
) -> list[DeviceRate]:
    """Devices sending at least MIN_RATE input reports a second, highest
    first. Empty when should_stop() turned true."""
    hid: HidApi = api if api is not None else cast("HidApi", _Win32Hid())
    stop = should_stop or (lambda: False)
    devices: list[_Device] = []
    try:
        for path, instance_id, description in hid.interfaces():
            if stop():
                return []
            handle = hid.open(path)
            if handle is None:
                continue
            dev = _Device(handle, instance_id=instance_id)
            devices.append(dev)
            info = hid.info(handle)
            if info is None or info[2] <= 0:
                continue
            dev.usage_page, dev.usage = info[0], info[1]
            dev.name = hid.product(handle) or description or instance_id
            dev.op = hid.new_read(handle, info[2])
        reading = [d for d in devices if d.op is not None]
        start = clock.monotonic()
        deadline = start + seconds
        for dev in reading:
            _take(hid, dev, hid.submit(dev.op))
        while not stop():
            now = clock.monotonic()
            if now >= deadline:
                break
            pending = [d.op for d in reading if d.state == PENDING]
            if not pending:
                clock.sleep(min(_WAIT_MS / 1000.0, deadline - now))
                continue
            hid.wait(pending, max(1, min(_WAIT_MS, int((deadline - now) * 1000))))
            if clock.monotonic() > deadline:
                break
            for dev in reading:
                if dev.state == PENDING:
                    _take(hid, dev, hid.check(dev.op))
        else:
            return []
        elapsed = max(clock.monotonic() - start, 1e-6)
    finally:
        for dev in devices:
            if dev.op is not None:
                if dev.state == PENDING:
                    hid.cancel(dev.op)
                hid.free(dev.op)
            hid.close(dev.handle)
    rates = [
        DeviceRate(d.name, d.instance_id, d.usage_page, d.usage, d.count / elapsed)
        for d in devices
        if d.op is not None
    ]
    rates = [r for r in rates if r.reports_per_s >= MIN_RATE]
    rates.sort(key=lambda r: r.reports_per_s, reverse=True)
    return rates


def _take(api: HidApi, dev: _Device, state: str) -> None:
    """Counts finished reads and starts the next until one is pending."""
    taken = 0
    while state == DONE and taken < _DRAIN:
        dev.count += 1
        taken += 1
        state = api.submit(dev.op)
    dev.state = state


# Windows ----------------------------------------------------------------

if os.name == "nt":
    from ctypes import wintypes

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class _SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("InterfaceClassGuid", _GUID),
            ("Flags", wintypes.DWORD),
            ("Reserved", ctypes.c_void_p),
        ]

    class _SP_DEVINFO_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("ClassGuid", _GUID),
            ("DevInst", wintypes.DWORD),
            ("Reserved", ctypes.c_void_p),
        ]

    class _HIDP_CAPS(ctypes.Structure):
        _fields_ = [
            ("Usage", wintypes.USHORT),
            ("UsagePage", wintypes.USHORT),
            ("InputReportByteLength", wintypes.USHORT),
            ("OutputReportByteLength", wintypes.USHORT),
            ("FeatureReportByteLength", wintypes.USHORT),
            ("Rest", wintypes.USHORT * 27),
        ]

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_void_p),
            ("InternalHigh", ctypes.c_void_p),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        ]


class _Read:
    """One device's read: its buffer, OVERLAPPED and event stay alive until
    free(), after any pending read has been cancelled and has finished."""

    def __init__(self, handle: object, length: int, event: object) -> None:
        self.handle = handle
        self.buffer = ctypes.create_string_buffer(length)
        self.overlapped = _OVERLAPPED()
        self.overlapped.hEvent = event
        self.event = event


class _Win32Hid:
    """The real Windows calls (SetupAPI, hid.dll, kernel32)."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("the devices check needs Windows")
        self._libs = _load()

    def interfaces(self) -> list[tuple[str, str, str]]:
        """(device path, instance id, device description) of each present
        HID interface."""
        setup, hid, _k32 = self._libs
        guid = _GUID()
        hid.HidD_GetHidGuid(ctypes.byref(guid))
        flags = 0x02 | 0x10  # DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
        info = setup.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, flags)
        if not info or info == ctypes.c_void_p(-1).value:
            return []
        out: list[tuple[str, str, str]] = []
        try:
            index = 0
            while True:
                iface = _SP_DEVICE_INTERFACE_DATA()
                iface.cbSize = ctypes.sizeof(iface)
                if not setup.SetupDiEnumDeviceInterfaces(
                    info, None, ctypes.byref(guid), index, ctypes.byref(iface)
                ):
                    break
                index += 1
                size = wintypes.DWORD(0)
                setup.SetupDiGetDeviceInterfaceDetailW(
                    info, ctypes.byref(iface), None, 0, ctypes.byref(size), None
                )
                if size.value < 8:
                    continue
                buf = ctypes.create_string_buffer(size.value)
                # cbSize of SP_DEVICE_INTERFACE_DETAIL_DATA_W: 8 on 64-bit.
                ctypes.c_uint32.from_buffer(buf).value = (
                    8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
                )
                devinfo = _SP_DEVINFO_DATA()
                devinfo.cbSize = ctypes.sizeof(devinfo)
                if not setup.SetupDiGetDeviceInterfaceDetailW(
                    info, ctypes.byref(iface), buf, size, None, ctypes.byref(devinfo)
                ):
                    continue
                path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
                id_buf = ctypes.create_unicode_buffer(512)
                instance_id = ""
                if setup.SetupDiGetDeviceInstanceIdW(
                    info, ctypes.byref(devinfo), id_buf, 512, None
                ):
                    instance_id = id_buf.value
                desc_buf = ctypes.create_unicode_buffer(512)
                description = ""
                if setup.SetupDiGetDeviceRegistryPropertyW(
                    info,
                    ctypes.byref(devinfo),
                    0,  # SPDRP_DEVICEDESC
                    None,
                    desc_buf,
                    ctypes.sizeof(desc_buf),
                    None,
                ):
                    description = desc_buf.value.strip()
                out.append((path, instance_id, description))
        finally:
            setup.SetupDiDestroyDeviceInfoList(info)
        return out

    def open(self, path: str) -> object:
        _setup, _hid, k32 = self._libs
        handle = k32.CreateFileW(
            path,
            0x80000000,  # GENERIC_READ
            0x1 | 0x2,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x40000000,  # FILE_FLAG_OVERLAPPED
            None,
        )
        if not handle or handle == ctypes.c_void_p(-1).value:
            return None
        return handle

    def info(self, handle: object) -> tuple[int, int, int] | None:
        """(usage page, usage, input report length)."""
        _setup, hid, _k32 = self._libs
        preparsed = ctypes.c_void_p()
        if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            return None
        caps = _HIDP_CAPS()
        try:
            status = hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
        finally:
            hid.HidD_FreePreparsedData(preparsed)
        if status & 0xFFFFFFFF != 0x00110000:  # HIDP_STATUS_SUCCESS
            return None
        return int(caps.UsagePage), int(caps.Usage), int(caps.InputReportByteLength)

    def product(self, handle: object) -> str:
        _setup, hid, _k32 = self._libs
        buf = ctypes.create_unicode_buffer(256)
        if hid.HidD_GetProductString(handle, buf, ctypes.sizeof(buf)):
            return buf.value.strip()
        return ""

    def new_read(self, handle: object, length: int) -> _Read:
        _setup, _hid, k32 = self._libs
        event = k32.CreateEventW(None, True, False, None)
        if not event:
            raise OSError(ctypes.get_last_error(), "CreateEventW failed")
        return _Read(handle, length, event)

    def submit(self, op: _Read) -> str:
        _setup, _hid, k32 = self._libs
        got = wintypes.DWORD(0)
        if k32.ReadFile(
            op.handle,
            op.buffer,
            len(op.buffer),
            ctypes.byref(got),
            ctypes.byref(op.overlapped),
        ):
            return DONE
        return PENDING if ctypes.get_last_error() == 997 else ERROR  # ERROR_IO_PENDING

    def check(self, op: _Read) -> str:
        _setup, _hid, k32 = self._libs
        got = wintypes.DWORD(0)
        if k32.GetOverlappedResult(
            op.handle, ctypes.byref(op.overlapped), ctypes.byref(got), False
        ):
            return DONE
        return (
            PENDING if ctypes.get_last_error() == 996 else ERROR
        )  # ERROR_IO_INCOMPLETE

    def wait(self, ops: list[_Read], timeout_ms: int) -> None:
        """Waits until one read finishes or timeout_ms passes."""
        _setup, _hid, k32 = self._libs
        if len(ops) > 64:  # MAXIMUM_WAIT_OBJECTS
            k32.Sleep(timeout_ms)
            return
        events = (wintypes.HANDLE * len(ops))(*[op.event for op in ops])
        k32.WaitForMultipleObjects(len(ops), events, False, timeout_ms)

    def cancel(self, op: _Read) -> None:
        """Cancels a pending read and waits (bounded) for it to finish, so its
        buffer isn't freed under Windows."""
        _setup, _hid, k32 = self._libs
        k32.CancelIoEx(op.handle, ctypes.byref(op.overlapped))
        k32.WaitForSingleObject(op.event, 1000)

    def free(self, op: _Read) -> None:
        _setup, _hid, k32 = self._libs
        k32.CloseHandle(op.event)

    def close(self, handle: object) -> None:
        _setup, _hid, k32 = self._libs
        k32.CloseHandle(handle)


def _load() -> tuple:
    """setupapi, hid and kernel32 with their argument types set."""
    setup = ctypes.WinDLL("setupapi", use_last_error=True)
    hid = ctypes.WinDLL("hid", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    vp, dword = ctypes.c_void_p, wintypes.DWORD

    setup.SetupDiGetClassDevsW.restype = vp
    setup.SetupDiGetClassDevsW.argtypes = [
        ctypes.POINTER(_GUID),
        wintypes.LPCWSTR,
        wintypes.HWND,
        dword,
    ]
    setup.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setup.SetupDiEnumDeviceInterfaces.argtypes = [
        vp,
        vp,
        ctypes.POINTER(_GUID),
        dword,
        ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA),
    ]
    setup.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        vp,
        ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA),
        vp,
        dword,
        ctypes.POINTER(dword),
        vp,
    ]
    setup.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInstanceIdW.argtypes = [vp, vp, vp, dword, vp]
    setup.SetupDiGetDeviceRegistryPropertyW.restype = wintypes.BOOL
    setup.SetupDiGetDeviceRegistryPropertyW.argtypes = [
        vp,
        vp,
        dword,
        vp,
        vp,
        dword,
        vp,
    ]
    setup.SetupDiDestroyDeviceInfoList.argtypes = [vp]

    hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(_GUID)]
    hid.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
    hid.HidD_GetPreparsedData.argtypes = [vp, ctypes.POINTER(vp)]
    hid.HidD_FreePreparsedData.argtypes = [vp]
    hid.HidP_GetCaps.restype = ctypes.c_long
    hid.HidP_GetCaps.argtypes = [vp, ctypes.POINTER(_HIDP_CAPS)]
    hid.HidD_GetProductString.restype = wintypes.BOOLEAN
    hid.HidD_GetProductString.argtypes = [vp, vp, wintypes.ULONG]

    k32.CreateFileW.restype = vp
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, dword, dword, vp, dword, dword, vp]
    k32.CreateEventW.restype = vp
    k32.CreateEventW.argtypes = [vp, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    k32.ReadFile.restype = wintypes.BOOL
    k32.ReadFile.argtypes = [vp, vp, dword, ctypes.POINTER(dword), vp]
    k32.GetOverlappedResult.restype = wintypes.BOOL
    k32.GetOverlappedResult.argtypes = [vp, vp, ctypes.POINTER(dword), wintypes.BOOL]
    k32.WaitForMultipleObjects.restype = dword
    k32.WaitForMultipleObjects.argtypes = [dword, vp, wintypes.BOOL, dword]
    k32.WaitForSingleObject.restype = dword
    k32.WaitForSingleObject.argtypes = [vp, dword]
    k32.CancelIoEx.restype = wintypes.BOOL
    k32.CancelIoEx.argtypes = [vp, vp]
    k32.Sleep.argtypes = [dword]
    k32.CloseHandle.argtypes = [vp]
    return setup, hid, k32
