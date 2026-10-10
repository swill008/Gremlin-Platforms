# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""What this process sees: DirectInput (dill), XInput pads 1-4 and the HID
game devices. Read only: no device is opened for writing."""

from __future__ import annotations

import ctypes
import os
import re
from ctypes import wintypes
from dataclasses import dataclass, field

import dill
from gremlin import device_paths
from gremlin.axis_names import AXIS_SHORT

VJOY_VID = 0x1234
VJOY_PID = 0xBEAD

AXIS_NAMES = AXIS_SHORT  # the program's one axis name table


@dataclass
class SeenDevice:
    """One device this process sees."""

    key: str  # "di:<GUID>" or "xi:<pad>"
    kind: str  # "directinput" | "xinput"
    name: str
    vid: int = 0
    pid: int = 0
    guid: str = ""  # "{XXXXXXXX-...}" upper case, DirectInput only
    axes: int = 0
    buttons: int = 0
    hats: int = 0
    axis_ids: list[int] = field(default_factory=list)
    pad: int = 0  # XInput pad 1-4
    # HID instance path (upper case) DirectInput gives for it; "" unknown.
    # What it is matched on: twins share a name and may swap GUIDs.
    instance_id: str = ""
    handle: object = field(default=None, compare=False, repr=False)  # dill.GUID

    @property
    def is_vjoy(self) -> bool:
        return self.vid == VJOY_VID and self.pid == VJOY_PID


@dataclass
class LiveValues:
    axes: list[float]
    buttons: list[bool]
    hats: list[int]  # -1 centred, else degrees

    def signature(self) -> tuple:
        return (
            tuple(round(a, 3) for a in self.axes),
            tuple(self.buttons),
            tuple(self.hats),
        )


def normalise_guid(value: str) -> str:
    text = value.strip().strip("{}").upper()
    return "{" + text + "}" if text else ""


def _axis_value(raw: int) -> float:
    if raw >= 0:
        return min(1.0, raw / 32767.0)
    return max(-1.0, raw / 32768.0)


def _hat_degrees(raw: int) -> int:
    if raw < 0 or raw > 36000:
        return -1
    return int(raw // 100) % 360


# DirectInput ---------------------------------------------------------------


@dataclass
class OpenResult:
    """How opening (HID) or reading (DirectInput) one device went, for the log."""

    kind: str  # "hid" | "directinput"
    name: str
    instance: str  # HID path, or DirectInput GUID "{...}"
    ok: bool
    code: int = 0  # Win32 error of a failed HID open
    text: str = ""  # "ok", "listed", "values read ok", "access denied (5)", ...
    left_out: str = ""  # HID: why an opened path was left out ("" when kept)


_open_results: dict[str, OpenResult] = {}  # key: kind + instance


def last_open_results() -> list[OpenResult]:
    """HID opens of the last scan, then DirectInput devices of the last list."""
    return [
        OpenResult(**vars(r))
        for r in sorted(_open_results.values(), key=lambda r: r.kind != "hid")
    ]


def _note_open(result: OpenResult) -> None:
    _open_results[f"{result.kind}:{result.instance}"] = result


def _note_di_read(device: SeenDevice, ok: bool, text: str) -> None:
    prev = _open_results.get(f"directinput:{device.guid}")
    if prev is not None and prev.text == text:
        return  # only the first read (or a change) is worth a line
    _note_open(OpenResult("directinput", device.name, device.guid, ok, text=text))


def directinput_devices() -> list[SeenDevice]:
    """Every DirectInput game controller dill lists."""
    dill.DILL.init()
    for key in [k for k in _open_results if k.startswith("directinput:")]:
        del _open_results[key]
    seen: list[SeenDevice] = []
    for index in range(int(dill.DILL.get_device_count())):
        info = dill.DILL.get_device_information_by_index(index)
        guid = normalise_guid(str(info.device_guid))
        axis_ids = [
            entry.axis_index
            for entry in info.axis_map[: info.axis_count]
            if entry.axis_index
        ]
        seen.append(
            SeenDevice(
                key=f"di:{guid}",
                kind="directinput",
                name=info.name.strip(),
                vid=int(info.vendor_id),
                pid=int(info.product_id),
                guid=guid,
                axes=len(axis_ids),
                buttons=int(info.button_count),
                hats=int(info.hat_count),
                axis_ids=axis_ids,
                handle=info.device_guid,
                instance_id=device_paths.hid_instance(guid),
            )
        )
        _note_open(OpenResult("directinput", seen[-1].name, guid, True, text="listed"))
    return seen


# Button N is DILL index N (1-based), as in DILL's own events, which the
# main program uses as the button number. The bundled reader is upstream
# R16's dill2 (DILL v2.0, 02 S139): it accepts buttons 1-128 and hats 1-4
# (v1.3 rejected 128 / 4 and flooded dill_debug.log).
DILL_MAX_BUTTON = 128
DILL_MAX_HAT = 4


def directinput_values(device: SeenDevice) -> LiveValues:
    guid = device.handle
    if not isinstance(guid, dill.GUID):
        guid = device.handle = dill.GUID.from_str(device.guid.strip("{}"))
    try:
        values = LiveValues(
            axes=[
                _axis_value(int(dill.DILL.get_axis(guid, i))) for i in device.axis_ids
            ],
            buttons=[
                bool(dill.DILL.get_button(guid, n)) if n <= DILL_MAX_BUTTON else False
                for n in range(1, device.buttons + 1)
            ],
            hats=[
                _hat_degrees(int(dill.DILL.get_hat(guid, n)))
                if n <= DILL_MAX_HAT
                else -1
                for n in range(1, device.hats + 1)
            ],
        )
    except OSError as err:
        _note_di_read(device, ok=False, text=f"values not read: {err}")
        raise
    _note_di_read(device, ok=True, text="values read ok")
    return values


# XInput --------------------------------------------------------------------


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


XINPUT_AXES = ["LX", "LY", "RX", "RY", "LT", "RT"]
# wButtons bits in order, d-pad (bits 0-3) shown as a hat.
XINPUT_BUTTON_BITS = [
    0x1000,
    0x2000,
    0x4000,
    0x8000,  # A B X Y
    0x0100,
    0x0200,  # LB RB
    0x0020,
    0x0010,  # Back Start
    0x0040,
    0x0080,  # LS RS
]
_DPAD = {0x1: 0, 0x9: 45, 0x8: 90, 0xA: 135, 0x2: 180, 0x6: 225, 0x4: 270, 0x5: 315}

_xinput_fn = None


def _load_xinput():  # noqa: ANN202
    global _xinput_fn
    if _xinput_fn is None and os.name == "nt":
        for name in ("xinput1_4", "xinput9_1_0"):
            try:
                fn = ctypes.WinDLL(name).XInputGetState
            except (OSError, AttributeError):
                continue
            fn.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
            fn.restype = wintypes.DWORD
            _xinput_fn = fn
            break
    return _xinput_fn


def xinput_state(pad: int) -> XINPUT_STATE | None:
    """XInputGetState for pad 1-4; None when no pad is connected there."""
    fn = _load_xinput()
    if fn is None:
        return None
    state = XINPUT_STATE()
    if fn(pad - 1, ctypes.byref(state)) != 0:
        return None
    return state


def xinput_values(state: XINPUT_STATE) -> LiveValues:
    g = state.Gamepad
    return LiveValues(
        axes=[
            _axis_value(g.sThumbLX),
            _axis_value(g.sThumbLY),
            _axis_value(g.sThumbRX),
            _axis_value(g.sThumbRY),
            g.bLeftTrigger / 255.0,
            g.bRightTrigger / 255.0,
        ],
        buttons=[bool(g.wButtons & bit) for bit in XINPUT_BUTTON_BITS],
        hats=[_DPAD.get(g.wButtons & 0xF, -1)],
    )


def xinput_devices() -> list[SeenDevice]:
    return [
        SeenDevice(
            key=f"xi:{pad}",
            kind="xinput",
            name=f"Xbox pad {pad}",
            axes=len(XINPUT_AXES),
            buttons=len(XINPUT_BUTTON_BITS),
            hats=1,
            pad=pad,
        )
        for pad in range(1, 5)
        if xinput_state(pad) is not None
    ]


# HID (list only) -------------------------------------------------------------


@dataclass
class HidDevice:
    path: str
    vid: int
    pid: int
    name: str = ""


_VID_PID = re.compile(r"vid_([0-9a-f]{4}).*?pid_([0-9a-f]{4})", re.IGNORECASE)


def _hid_vid_pid(path: str) -> tuple[int, int]:
    match = _VID_PID.search(path)
    if not match:
        return 0, 0
    return int(match.group(1), 16), int(match.group(2), 16)


ACCESS_DENIED = 5


@dataclass
class HidSkip:
    """One HID path left out of the list, and why."""

    path: str
    name: str = ""
    vid: int = 0
    pid: int = 0
    reason: str = ""
    code: int = 0  # Win32 error of the failed step; 0 for "not a game device"
    usage_page: int = 0
    usage: int = 0

    @property
    def denied(self) -> bool:
        """Refused at open: HidHide hides it from this process."""
        return self.code == ACCESS_DENIED


def describe_open_error(code: int) -> str:
    if code == ACCESS_DENIED:
        return f"access denied ({ACCESS_DENIED})"
    text = ""
    format_error = getattr(ctypes, "FormatError", None)
    if format_error is not None:
        text = format_error(code).strip()
    return f"error {code}: {text or os.strerror(code)}"


_hid_skips: list[HidSkip] = []


def last_hid_skips() -> list[HidSkip]:
    """Paths the last HID scan left out."""
    return list(_hid_skips)


def hid_devices() -> list[HidDevice]:
    """HID game devices (joystick, gamepad, game controls usage page).

    Each interface is opened with no access rights (query only) to read its
    usage; one this process can't open (e.g. hidden by HidHide) is left out,
    with the reason kept in last_hid_skips().
    """
    return hid_scan()[0]


def hid_scan() -> tuple[list[HidDevice], list[HidSkip]]:
    """One HID scan: (kept game devices, left-out paths with reasons)."""
    global _hid_skips
    kept: list[HidDevice] = []
    skipped: list[HidSkip] = []
    if os.name == "nt":
        try:
            kept, skipped = _hid_enumerate()
        except OSError:
            kept, skipped = [], []
    _hid_skips = list(skipped)
    return kept, skipped


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


class _HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class _HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("Rest", wintypes.USHORT * 32),
    ]


def _is_game_usage(page: int, usage: int) -> bool:
    return page == 0x05 or (page == 0x01 and usage in (0x04, 0x05))


def _hid_libs():  # noqa: ANN202
    """setupapi, hid and kernel32 with their argument types set."""
    setup = ctypes.WinDLL("setupapi", use_last_error=True)
    hid = ctypes.WinDLL("hid", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    setup.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setup.SetupDiGetClassDevsW.argtypes = [
        ctypes.POINTER(_GUID),
        wintypes.LPCWSTR,
        wintypes.HWND,
        wintypes.DWORD,
    ]
    setup.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setup.SetupDiEnumDeviceInterfaces.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(_GUID),
        wintypes.DWORD,
        ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA),
    ]
    setup.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_SP_DEVICE_INTERFACE_DATA),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    setup.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    hid.HidD_GetAttributes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_HIDD_ATTRIBUTES),
    ]
    hid.HidD_GetPreparsedData.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
    hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(_HIDP_CAPS)]
    hid.HidD_GetProductString.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.ULONG,
    ]

    return setup, hid, k32


def _hid_paths(setup, hid) -> list[str]:  # noqa: ANN001
    """Device paths of every present HID interface."""
    hid_guid = _GUID()
    hid.HidD_GetHidGuid(ctypes.byref(hid_guid))
    digcf = 0x02 | 0x10  # DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    info = setup.SetupDiGetClassDevsW(ctypes.byref(hid_guid), None, None, digcf)
    if not info or info == ctypes.c_void_p(-1).value:
        return []
    paths: list[str] = []
    try:
        index = 0
        while True:
            iface = _SP_DEVICE_INTERFACE_DATA()
            iface.cbSize = ctypes.sizeof(iface)
            if not setup.SetupDiEnumDeviceInterfaces(
                info, None, ctypes.byref(hid_guid), index, ctypes.byref(iface)
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
            if not setup.SetupDiGetDeviceInterfaceDetailW(
                info, ctypes.byref(iface), buf, size, None, None
            ):
                continue
            paths.append(ctypes.wstring_at(ctypes.addressof(buf) + 4))
    finally:
        setup.SetupDiDestroyDeviceInfoList(info)
    return paths


def _hid_enumerate() -> tuple[list[HidDevice], list[HidSkip]]:
    setup, hid, k32 = _hid_libs()
    for key in [k for k in _open_results if k.startswith("hid:")]:
        del _open_results[key]
    kept: list[HidDevice] = []
    skipped: list[HidSkip] = []
    for path in _hid_paths(setup, hid):
        entry = _hid_query(k32, hid, path)
        if isinstance(entry, HidSkip):
            skipped.append(entry)
            opened = entry.code == 0 or entry.reason.startswith("no preparsed")
            _note_open(
                OpenResult(
                    "hid",
                    entry.name,
                    path,
                    ok=opened,
                    code=0 if opened else entry.code,
                    text="ok" if opened else entry.reason,
                    left_out=entry.reason if opened else "",
                )
            )
        else:
            kept.append(entry)
            _note_open(OpenResult("hid", entry.name, path, ok=True, text="ok"))
    return kept, skipped


def _hid_query(k32, hid, path: str) -> HidDevice | HidSkip:  # noqa: ANN001
    share = 0x1 | 0x2  # FILE_SHARE_READ | FILE_SHARE_WRITE
    handle = k32.CreateFileW(path, 0, share, None, 3, 0, None)  # OPEN_EXISTING
    if not handle or handle == ctypes.c_void_p(-1).value:
        code = int(ctypes.get_last_error())
        vid, pid = _hid_vid_pid(path)
        return HidSkip(path, "", vid, pid, describe_open_error(code), code)
    try:
        attrs = _HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(attrs)
        if hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
            vid, pid = int(attrs.VendorID), int(attrs.ProductID)
        else:
            vid, pid = _hid_vid_pid(path)
        name_buf = ctypes.create_unicode_buffer(256)
        name = ""
        if hid.HidD_GetProductString(handle, name_buf, ctypes.sizeof(name_buf)):
            name = name_buf.value.strip()
        preparsed = ctypes.c_void_p()
        if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            code = int(ctypes.get_last_error())
            reason = f"no preparsed data (error {code})"
            return HidSkip(path, name, vid, pid, reason, code)
        caps = _HIDP_CAPS()
        try:
            hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
        finally:
            hid.HidD_FreePreparsedData(preparsed)
        page, usage = int(caps.UsagePage), int(caps.Usage)
        if not _is_game_usage(page, usage):
            reason = f"not a game device (usage page 0x{page:04X}, usage 0x{usage:04X})"
            return HidSkip(path, name, vid, pid, reason, 0, page, usage)
        return HidDevice(path=path, vid=vid, pid=pid, name=name)
    finally:
        k32.CloseHandle(handle)


def snapshot() -> list[SeenDevice]:
    """DirectInput devices then connected XInput pads."""
    return directinput_devices() + xinput_devices()


def poll(device: SeenDevice) -> LiveValues:
    """Live values of one seen device (empty when it has gone)."""
    if device.kind == "xinput":
        state = xinput_state(device.pad)
        if state is None:
            return LiveValues([], [], [])
        return xinput_values(state)
    return directinput_values(device)
