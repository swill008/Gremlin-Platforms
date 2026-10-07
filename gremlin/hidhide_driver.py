# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""HidHide driver client and HID device enumeration.

HidHide is a driver of its own (D-02-Q10): the control device calls
(IOCTLs), the HID device list (SetupAPI, cfgmgr32, hid.dll) and the program
image paths live here; gremlin.ui.hidhide is the screen. Does not ship or
install the driver.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from gremlin import util

_DEVICE_TYPE = 32769
_METHOD_BUFFERED = 0
_FILE_READ_DATA = 1


def _ctl(function: int) -> int:
    return (
        (_DEVICE_TYPE << 16)
        | (_FILE_READ_DATA << 14)
        | (function << 2)
        | _METHOD_BUFFERED
    )


IOCTL_GET_WHITELIST = _ctl(2048)
IOCTL_SET_WHITELIST = _ctl(2049)
IOCTL_GET_BLACKLIST = _ctl(2050)
IOCTL_SET_BLACKLIST = _ctl(2051)
IOCTL_GET_ACTIVE = _ctl(2052)
IOCTL_SET_ACTIVE = _ctl(2053)
IOCTL_GET_INVERSE = _ctl(2054)
IOCTL_SET_INVERSE = _ctl(2055)
IOCTL_ADD_SESSION_BLACKLIST = _ctl(2056)
IOCTL_CLR_SESSION_BLACKLIST = _ctl(2057)

_IOCTL_NAMES = {
    IOCTL_GET_WHITELIST: "GET_WHITELIST",
    IOCTL_SET_WHITELIST: "SET_WHITELIST",
    IOCTL_GET_BLACKLIST: "GET_BLACKLIST",
    IOCTL_SET_BLACKLIST: "SET_BLACKLIST",
    IOCTL_GET_ACTIVE: "GET_ACTIVE",
    IOCTL_SET_ACTIVE: "SET_ACTIVE",
    IOCTL_GET_INVERSE: "GET_INVERSE",
    IOCTL_SET_INVERSE: "SET_INVERSE",
    IOCTL_ADD_SESSION_BLACKLIST: "ADD_SESSION_BLACKLIST",
    IOCTL_CLR_SESSION_BLACKLIST: "CLR_SESSION_BLACKLIST",
}


def _hh_log(message: str, level: int = logging.DEBUG) -> None:
    """HidHide line in the system log. Options > Debug sets which levels are kept."""
    logging.getLogger("system").log(level, "HidHide %s", message)


DEVPROP_TYPE_EMPTY = 0x00000000
DEVPROP_TYPE_GUID = 0x0000000D
DEVPROP_TYPE_STRING = 0x00000012
GUID_NULL = "00000000-0000-0000-0000-000000000000"
GUID_CONTAINER_ID_SYSTEM = "00000000-0000-0000-FFFF-FFFFFFFFFFFF"
CM_LOCATE_DEVNODE_NORMAL = 0
CM_LOCATE_DEVNODE_PHANTOM = 1
_WALK_STATS = {}

# Hardware Hide list = HidHide HidDevices() in HidHideCLI/src/HID.cpp.

_GENERIC_READ = 0x80000000
_SHARE = 0x00000007
_OPEN_EXISTING = 3
_INVALID = 0xFFFFFFFFFFFFFFFF


def _vid_pid(instance: str) -> tuple[int | None, int | None]:
    up = (instance or "").upper()
    vid = pid = None
    if "VID_" in up:
        try:
            vid = int(up.split("VID_", 1)[1][:4], 16)
        except ValueError:
            vid = None
    if "PID_" in up:
        try:
            pid = int(up.split("PID_", 1)[1][:4], 16)
        except ValueError:
            pid = None
    return vid, pid


def _gremlin_exe() -> str:
    # HidHide matches the process image, not the script. Ask Windows for this process.
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetModuleFileNameW.argtypes = [
            wintypes.HMODULE,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        k32.GetModuleFileNameW.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        if k32.GetModuleFileNameW(None, buf, len(buf)):
            return buf.value
    return str(Path(sys.executable).resolve())


def _nt_image_path(path: str) -> str:
    """Same NT path HidHide stores: GetFinalPathNameByHandleW(VOLUME_NAME_NT)."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    k32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    handle = k32.CreateFileW(path, 0x80, _SHARE, None, _OPEN_EXISTING, 0, None)
    if not handle or int(handle) in (0, -1, _INVALID, 0xFFFFFFFF):
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        wrote = k32.GetFinalPathNameByHandleW(handle, buf, len(buf), 2)
        if not wrote or wrote >= len(buf):
            return ""
        image = buf.value.strip()
        if image.startswith("\\\\?\\"):
            image = image[4:]
        return image if image.lower().startswith("\\device\\") else ""
    finally:
        k32.CloseHandle(handle)


def _full_image_name(path: str) -> str:
    """Dos path to the volume path HidHide compares. Existing volume paths
    pass through."""
    text = str(path or "").strip().replace("/", "\\")
    if text.startswith("\\\\?\\") and not text.startswith("\\\\?\\Volume{"):
        text = text[4:]
    if text.lower().startswith("\\device\\"):
        return text
    if not text or os.name != "nt":
        return ""
    image = _nt_image_path(text)
    if image:
        _hh_log(f"image {text} -> {image}")
        return image
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetVolumePathNameW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    k32.GetVolumePathNameW.restype = wintypes.BOOL
    k32.GetVolumeNameForVolumeMountPointW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    k32.GetVolumeNameForVolumeMountPointW.restype = wintypes.BOOL
    k32.QueryDosDeviceW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    k32.QueryDosDeviceW.restype = wintypes.DWORD
    mount_buf = ctypes.create_unicode_buffer(32768)
    if not k32.GetVolumePathNameW(text, mount_buf, len(mount_buf)):
        _hh_log(f"volume path failed {text} err={ctypes.get_last_error()}")
        return ""
    mount = mount_buf.value
    if not text.lower().startswith(mount.lower()):
        _hh_log(f"volume mount {mount!r} does not prefix {text}")
        return ""
    vol_buf = ctypes.create_unicode_buffer(512)
    if not k32.GetVolumeNameForVolumeMountPointW(mount, vol_buf, len(vol_buf)):
        _hh_log(f"volume name failed {mount} err={ctypes.get_last_error()}")
        return ""
    volume = vol_buf.value
    if not (volume.startswith("\\\\?\\") and volume.endswith("\\")):
        _hh_log(f"unexpected volume name {volume!r}")
        return ""
    dev_buf = ctypes.create_unicode_buffer(1024)
    if not k32.QueryDosDeviceW(volume[4:-1], dev_buf, len(dev_buf)):
        _hh_log(f"dos device failed {volume} err={ctypes.get_last_error()}")
        return ""
    device = dev_buf.value.rstrip("\\")
    rest = text[len(mount) :].lstrip("\\")
    image = device if not rest else f"{device}\\{rest}"
    _hh_log(f"image {text} -> {image}")
    return image


def _open_control() -> int | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
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
    handle = k32.CreateFileW(
        "\\\\.\\HidHide",
        _GENERIC_READ,
        _SHARE,
        None,
        _OPEN_EXISTING,
        0,
        None,
    )
    if not handle or int(handle) in (0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
        _hh_log(
            f"open \\\\.\\HidHide failed err={ctypes.get_last_error()} "
            f"handle={handle!r}",
            logging.WARNING,
        )
        return None
    return handle


def _close(handle: int | None) -> None:
    if handle:
        __import__("ctypes").windll.kernel32.CloseHandle(handle)


_ioctl_error = ""


def _ioctl(
    handle: int, code: int, inn: bytes | None = None, out_size: int = 0
) -> tuple[bool, bytes]:
    import ctypes
    from ctypes import wintypes

    global _ioctl_error
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.DeviceIoControl.restype = wintypes.BOOL
    k32.DeviceIoControl.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    returned = wintypes.DWORD(0)
    in_buf = ctypes.create_string_buffer(inn) if inn else None
    in_len = len(inn) if inn else 0
    out_buf = ctypes.create_string_buffer(out_size) if out_size else None
    ok = k32.DeviceIoControl(
        handle,
        int(code) & 0xFFFFFFFF,
        in_buf,
        in_len,
        out_buf,
        out_size,
        ctypes.byref(returned),
        None,
    )
    if not ok:
        _ioctl_error = f"HidHide driver call failed ({ctypes.get_last_error()})."
    name = _IOCTL_NAMES.get(int(code) & 0xFFFFFFFF, "OTHER")
    _hh_log(
        f"ioctl {name} code=0x{int(code) & 0xFFFFFFFF:08X} in={in_len} out={out_size} "
        f"ok={bool(ok)} returned={int(returned.value)} "
        f"err={0 if ok else ctypes.get_last_error()}",
        logging.DEBUG if ok else logging.WARNING,
    )
    data = out_buf.raw[: returned.value] if out_buf else b""
    return bool(ok), data


def _decode_multi_sz(raw: bytes) -> list[str]:
    if not raw:
        return []
    text = raw.decode("utf-16-le", errors="ignore")
    parts = text.split("\x00")
    return [p for p in parts if p]


def _encode_multi_sz(items: list[str]) -> bytes:
    body = "\x00".join(items) + "\x00\x00"
    raw = body.encode("utf-16-le")
    if len(raw) % 2:
        raw += b"\x00"
    return raw


def _get_multi(code: int) -> list[str]:
    handle = _open_control()
    if handle is None:
        return []
    try:
        size = 4096
        for _ in range(6):
            ok, data = _ioctl(handle, code, None, size)
            if ok:
                return _decode_multi_sz(data)
            size *= 2
        return []
    finally:
        _close(handle)


def _set_multi(code: int, items: list[str]) -> bool:
    handle = _open_control()
    if handle is None:
        return False
    try:
        payload = _encode_multi_sz(items)
        ok, _ = _ioctl(handle, code, payload, 0)
        return ok
    finally:
        _close(handle)


def driver_version() -> str:
    """Installer version, then HidHide.sys file version if the registry key
    is absent."""
    if os.name != "nt":
        return ""
    import winreg

    for name in (
        r"SOFTWARE\Classes\Installer\Dependencies\NSS.Drivers.HidHide.x64",
        r"SOFTWARE\Classes\Installer\Dependencies\NSS.Drivers.HidHide.arm64",
    ):
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                name,
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "Version")
        except OSError:
            continue
        text = str(value or "").strip()
        if text:
            return text
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return util.file_version(os.path.join(root, "System32", "drivers", "HidHide.sys"))


def driver_present() -> bool:
    handle = _open_control()
    if handle is None:
        return False
    _close(handle)
    return True


def get_active() -> bool:
    handle = _open_control()
    if handle is None:
        return False
    try:
        ok, data = _ioctl(handle, IOCTL_GET_ACTIVE, None, 1)
        return ok and bool(data and data[0])
    finally:
        _close(handle)


def set_active(on: bool) -> bool:
    handle = _open_control()
    if handle is None:
        return False
    try:
        ok, _ = _ioctl(handle, IOCTL_SET_ACTIVE, bytes([1 if on else 0]), 0)
        if not ok:
            return False
    finally:
        _close(handle)
    return bool(get_active()) == bool(on)


def get_inverse() -> bool:
    handle = _open_control()
    if handle is None:
        return False
    try:
        ok, data = _ioctl(handle, IOCTL_GET_INVERSE, None, 1)
        return ok and bool(data and data[0])
    finally:
        _close(handle)


def set_inverse(on: bool) -> bool:
    handle = _open_control()
    if handle is None:
        return False
    try:
        ok, _ = _ioctl(handle, IOCTL_SET_INVERSE, bytes([1 if on else 0]), 0)
        if not ok:
            return False
    finally:
        _close(handle)
    return bool(get_inverse()) == bool(on)


def get_blacklist() -> list[str]:
    return _get_multi(IOCTL_GET_BLACKLIST)


def set_blacklist(ids: list[str]) -> bool:
    return _set_multi(IOCTL_SET_BLACKLIST, ids)


def set_whitelist(paths: list[str]) -> bool:
    return _set_multi(IOCTL_SET_WHITELIST, paths)


def list_hid_devices(gaming_only: bool) -> list[dict]:
    """HidHide HidDevices(). Tools → Hardware Hide only."""
    if os.name != "nt":
        return []
    return _list_hidhide_class_enum(gaming_only)


def _is_gaming(vid: int, pid: int, usage_page: int, usage: int) -> bool:
    if vid == 0x28DE and pid in (0x1142, 0x1205):
        return True
    if usage_page == 0x05:
        return True
    if usage_page == 0x01 and usage in (0x04, 0x05):
        return True
    return False


def _list_hidhide_class_enum(gaming_only: bool) -> list[dict]:
    """HidHide HidDevices: GUID_DEVCLASS_HIDCLASS list + HID symbolic link."""
    import ctypes
    from ctypes import wintypes

    setup = ctypes.WinDLL("setupapi", use_last_error=True)
    hid = ctypes.WinDLL("hid", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)

    cfg.CM_Get_Device_ID_List_SizeW.argtypes = [
        ctypes.POINTER(wintypes.ULONG),
        wintypes.LPCWSTR,
        wintypes.ULONG,
    ]
    cfg.CM_Get_Device_ID_List_SizeW.restype = wintypes.DWORD
    cfg.CM_Get_Device_ID_ListW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.ULONG,
        wintypes.ULONG,
    ]
    cfg.CM_Get_Device_ID_ListW.restype = wintypes.DWORD

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class SP_DEVINFO_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("ClassGuid", GUID),
            ("DevInst", wintypes.DWORD),
            ("Reserved", ctypes.c_void_p),
        ]

    class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("InterfaceClassGuid", GUID),
            ("Flags", wintypes.DWORD),
            ("Reserved", ctypes.c_void_p),
        ]

    class HIDD_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("Size", wintypes.ULONG),
            ("VendorID", wintypes.USHORT),
            ("ProductID", wintypes.USHORT),
            ("VersionNumber", wintypes.USHORT),
        ]

    class HIDP_CAPS(ctypes.Structure):
        _fields_ = [
            ("Usage", wintypes.USHORT),
            ("UsagePage", wintypes.USHORT),
            ("InputReportByteLength", wintypes.USHORT),
            ("OutputReportByteLength", wintypes.USHORT),
            ("FeatureReportByteLength", wintypes.USHORT),
            ("Reserved", wintypes.USHORT * 17),
            ("NumberLinkCollectionNodes", wintypes.USHORT),
            ("NumberInputButtonCaps", wintypes.USHORT),
            ("NumberInputValueCaps", wintypes.USHORT),
            ("NumberInputDataIndices", wintypes.USHORT),
            ("NumberOutputButtonCaps", wintypes.USHORT),
            ("NumberOutputValueCaps", wintypes.USHORT),
            ("NumberOutputDataIndices", wintypes.USHORT),
            ("NumberFeatureButtonCaps", wintypes.USHORT),
            ("NumberFeatureValueCaps", wintypes.USHORT),
            ("NumberFeatureDataIndices", wintypes.USHORT),
        ]

    setup.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setup.SetupDiGetClassDevsW.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.LPCWSTR,
        wintypes.HWND,
        wintypes.DWORD,
    ]
    setup.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setup.SetupDiEnumDeviceInterfaces.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    setup.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    setup.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
    setup.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]

    hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
    hid.HidD_GetHidGuid.restype = None
    hid_guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(hid_guid))
    import uuid

    raw = uuid.UUID("4D1E55B2-F16F-11CF-88CB-001111000030").bytes_le
    hid_guid.Data1 = int.from_bytes(raw[0:4], "little")
    hid_guid.Data2 = int.from_bytes(raw[4:6], "little")
    hid_guid.Data3 = int.from_bytes(raw[6:8], "little")
    for i, b in enumerate(raw[8:16]):
        hid_guid.Data4[i] = b
    CR_SUCCESS = 0
    CM_GETIDLIST_FILTER_CLASS = 0x00000200  # cfgmgr32.h, not 0x8 (REMOVALRELATIONS)
    # {745A17A0-74D3-11D0-B6FE-00A0C90F57DA} HIDClass
    class_s = "{745A17A0-74D3-11D0-B6FE-00A0C90F57DA}"
    size = wintypes.ULONG(0)
    # HidHide DeviceInstancePathsPresentOrNot: no FILTER_PRESENT
    flags = CM_GETIDLIST_FILTER_CLASS
    global _WALK_STATS
    if (
        cfg.CM_Get_Device_ID_List_SizeW(ctypes.byref(size), class_s, flags)
        != CR_SUCCESS
    ):
        _WALK_STATS = {
            "error": "CM_Get_Device_ID_List_SizeW",
            "cmSize": int(size.value),
        }
        return []
    if size.value < 2:
        _WALK_STATS = {"error": "cm size < 2", "cmSize": int(size.value)}
        return []
    buf = ctypes.create_unicode_buffer(size.value)
    if cfg.CM_Get_Device_ID_ListW(class_s, buf, size.value, flags) != CR_SUCCESS:
        _WALK_STATS = {"error": "CM_Get_Device_ID_ListW", "cmSize": int(size.value)}
        return []
    instances = [
        p
        for p in ctypes.wstring_at(ctypes.addressof(buf), size.value).split(chr(0))
        if p
    ]
    stats = {
        "cm": int(size.value),
        "classIds": len(instances),
        "enumOk": 0,
        "links": 0,
        "opened": 0,
        "denied": 0,
        "rows": 0,
        "cmSize": 0,
        "cmList": 0,
        "sample": instances[:3],
    }
    stats["cmSize"] = 1
    stats["cmList"] = 1
    groups: dict[str, dict] = {}
    DIGCF_DEVICEINTERFACE = 0x00000010
    setup.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    GENERIC_READ = 0x80000000
    FILE_SHARE = 0x00000007
    FILE_ATTRIBUTE_NORMAL = 0x80
    for instance in instances:
        if instance.upper().startswith("USB"):
            continue
        # SymbolicLink(hidGuid, instance) — SetupDi scoped to this instance
        # HidHide SymbolicLink: DIGCF_DEVICEINTERFACE only (no DIGCF_PRESENT)
        devs = setup.SetupDiGetClassDevsW(
            ctypes.byref(hid_guid), instance, None, DIGCF_DEVICEINTERFACE
        )
        if not devs or int(devs) in (0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            continue
        link = ""
        try:
            iface = SP_DEVICE_INTERFACE_DATA()
            iface.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not setup.SetupDiEnumDeviceInterfaces(
                devs, None, ctypes.byref(hid_guid), 0, ctypes.byref(iface)
            ):
                continue
            stats["enumOk"] += 1
            needed = wintypes.DWORD(0)
            setup.SetupDiGetDeviceInterfaceDetailW(
                devs, ctypes.byref(iface), None, 0, ctypes.byref(needed), None
            )
            if needed.value < 8:
                continue
            path_chars = max(2, needed.value // 2)

            class DETAIL(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("DevicePath", ctypes.c_wchar * path_chars),
                ]

            detail = DETAIL()
            # sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W) is 8 on x64, 6 on x86
            detail.cbSize = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if not setup.SetupDiGetDeviceInterfaceDetailW(
                devs,
                ctypes.byref(iface),
                ctypes.byref(detail),
                int(needed.value),
                None,
                None,
            ):
                continue
            link = detail.DevicePath or ""
        finally:
            setup.SetupDiDestroyDeviceInfoList(devs)
        if not link or not link.startswith("\\"):
            continue
        stats["links"] += 1
        handle = k32.CreateFileW(
            link, GENERIC_READ, FILE_SHARE, None, 3, FILE_ATTRIBUTE_NORMAL, None
        )
        vid = pid = 0
        parsed = _vid_pid(instance)
        if parsed[0] is not None:
            vid = parsed[0]
        if parsed[1] is not None:
            pid = parsed[1]
        usage_page = usage = 0
        product = vendor = ""
        denied = False
        opened = bool(handle) and int(handle) not in (0, -1, _INVALID, 0xFFFFFFFF)
        if opened:
            stats["opened"] += 1
            try:
                attrs = HIDD_ATTRIBUTES()
                attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
                if hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
                    vid = int(attrs.VendorID)
                    pid = int(attrs.ProductID)
                preparsed = ctypes.c_void_p()
                if (
                    hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed))
                    and preparsed
                ):
                    caps = HIDP_CAPS()
                    hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
                    usage_page = int(caps.UsagePage)
                    usage = int(caps.Usage)
                    hid.HidD_FreePreparsedData(preparsed)
                prod = ctypes.create_unicode_buffer(127)
                manu = ctypes.create_unicode_buffer(127)
                if hid.HidD_GetProductString(handle, prod, 254):
                    product = (prod.value or "").strip()
                if hid.HidD_GetManufacturerString(handle, manu, 254):
                    vendor = (manu.value or "").strip()
            finally:
                k32.CloseHandle(handle)
        else:
            err = ctypes.get_last_error()
            denied = err in (5, 32)
            if denied:
                stats["denied"] += 1
        description = _device_description(instance)
        gaming = _is_gaming(vid, pid, usage_page, usage)
        if gaming_only and not gaming and not denied:
            continue
        container = _group_key(instance, vid, pid)
        label = _display_name(vendor, product, description, "")
        if opened and (vendor or product):
            _remember_name(instance, label)
        elif denied:
            cached = _cached_name(instance)
            if cached:
                label = cached
        group = groups.setdefault(
            container,
            {
                "instanceId": instance,
                "instanceIds": [],
                "name": label,
                "canHide": True,
                "photo": "",
                "gaming": False,
                "openDenied": False,
                "sawOpen": False,
            },
        )
        if instance not in group["instanceIds"]:
            group["instanceIds"].append(instance)
        group["gaming"] = group["gaming"] or gaming
        if opened:
            group["sawOpen"] = True
            group["openDenied"] = False
        elif denied and not group["sawOpen"]:
            group["openDenied"] = True
        if _usable_name(label) and (
            _looks_like_instance(group["name"])
            or len(_usable_name(label)) > len(group["name"])
        ):
            group["name"] = label
    out = list(groups.values())
    for row in out:
        current = row.get("name") or ""
        if current.lower() == "hid-compliant game controller":
            for inst in row.get("instanceIds") or []:
                cached = _cached_name(inst)
                if cached:
                    row["name"] = cached
                    break
        else:
            for inst in row.get("instanceIds") or []:
                _remember_name(inst, row["name"])
        row.pop("sawOpen", None)
    stats["rows"] = len(out)
    _WALK_STATS = dict(stats)
    return out


def _guid_text(raw: bytes) -> str:
    if len(raw) < 16:
        return GUID_NULL
    d1 = int.from_bytes(raw[0:4], "little")
    d2 = int.from_bytes(raw[4:6], "little")
    d3 = int.from_bytes(raw[6:8], "little")
    d4 = raw[8:16]
    return f"{d1:08X}-{d2:04X}-{d3:04X}-{d4[0]:02X}{d4[1]:02X}-{d4[2:8].hex().upper()}"


def _guid_le(text: str) -> bytes:
    import uuid

    u = uuid.UUID(text)
    return u.bytes_le[:4] + u.bytes_le[4:6] + u.bytes_le[6:8] + u.bytes[8:]


def _device_description(instance: str) -> str:
    """HidHide DeviceDescription: DEVPKEY_Device_DeviceDesc via
    CM_Get_DevNode_PropertyW."""
    if not instance or os.name != "nt":
        return ""
    import ctypes
    from ctypes import wintypes

    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    CR_SUCCESS = 0
    DEVPROP_TYPE_STRING = 0x00000012

    class DEVPROPKEY(ctypes.Structure):
        _fields_ = [("fmtid", ctypes.c_ubyte * 16), ("pid", wintypes.ULONG)]

    key = DEVPROPKEY()
    raw = _guid_le("A45C254E-DF1C-4EFD-8020-67D146A850E0")
    for i, b in enumerate(raw):
        key.fmtid[i] = b
    key.pid = 2
    devinst = wintypes.DWORD(0)
    if cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), instance, 1) != CR_SUCCESS:
        return ""
    ptype = wintypes.ULONG(0)
    size = wintypes.ULONG(0)
    cfg.CM_Get_DevNode_PropertyW(
        devinst, ctypes.byref(key), ctypes.byref(ptype), None, ctypes.byref(size), 0
    )
    if size.value < 4:
        return ""
    buf = ctypes.create_unicode_buffer(max(2, size.value // 2))
    if (
        cfg.CM_Get_DevNode_PropertyW(
            devinst, ctypes.byref(key), ctypes.byref(ptype), buf, ctypes.byref(size), 0
        )
        != CR_SUCCESS
    ):
        return ""
    if ptype.value != DEVPROP_TYPE_STRING:
        return ""
    return (buf.value or "").strip()


def _parent_instance(instance: str) -> str:

    if not instance or os.name != "nt":
        return ""
    import ctypes
    from ctypes import wintypes

    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    CR_SUCCESS = 0
    devinst = wintypes.DWORD(0)
    parent = wintypes.DWORD(0)
    if cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), instance, 1) != CR_SUCCESS:
        return ""
    if cfg.CM_Get_Parent(ctypes.byref(parent), devinst, 0) != CR_SUCCESS:
        return ""
    buf = ctypes.create_unicode_buffer(512)
    if cfg.CM_Get_Device_IDW(parent, buf, 512, 0) != CR_SUCCESS:
        return ""
    return buf.value or ""


CM_LOCATE_DEVNODE_PHANTOM = 1


def _container_id(instance: str) -> str:
    """DEVPKEY_Device_ContainerId as GUID text. HidHide BaseContainerId."""
    if not instance or os.name != "nt":
        return GUID_NULL
    import ctypes
    from ctypes import wintypes

    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    CR_SUCCESS = 0
    CR_NO_SUCH_VALUE = 37
    DEVPROP_TYPE_GUID = 0x0000000D

    class DEVPROPKEY(ctypes.Structure):
        _fields_ = [("fmtid", ctypes.c_ubyte * 16), ("pid", wintypes.ULONG)]

    key = DEVPROPKEY()
    raw = _guid_le("8C7ED206-3F8A-4827-B3AB-AE9E1FAEFC6C")
    for i, b in enumerate(raw):
        key.fmtid[i] = b
    key.pid = 2
    devinst = wintypes.DWORD(0)
    if (
        cfg.CM_Locate_DevNodeW(
            ctypes.byref(devinst), instance, CM_LOCATE_DEVNODE_PHANTOM
        )
        != CR_SUCCESS
    ):
        return GUID_NULL
    ptype = wintypes.ULONG(0)
    size = wintypes.ULONG(16)
    buf = (ctypes.c_ubyte * 16)()
    rc = cfg.CM_Get_DevNode_PropertyW(
        devinst, ctypes.byref(key), ctypes.byref(ptype), buf, ctypes.byref(size), 0
    )
    if rc == CR_NO_SUCH_VALUE or rc != CR_SUCCESS:
        return GUID_NULL
    if ptype.value != DEVPROP_TYPE_GUID:
        return GUID_NULL
    return _guid_text(bytes(buf))


def _base_container_path(instance: str) -> str:
    """HidHide BaseContainerDeviceInstancePath."""
    cid = _container_id(instance)
    # HidHide treats an unreadable container id as GUID_NULL: the device stands alone.
    if not cid or cid in (GUID_NULL, GUID_CONTAINER_ID_SYSTEM):
        return ""
    it = instance
    for _ in range(12):
        parent = _parent_instance(it)
        if not parent:
            return it
        if _container_id(parent) == cid:
            it = parent
            continue
        return it
    return it


def _group_key(instance: str, vid: int | None = None, pid: int | None = None) -> str:
    base = _base_container_path(instance)
    if base:
        return "base:" + base.upper()
    return "id:" + (instance or "").upper()


def _looks_like_instance(text: str) -> bool:
    u = (text or "").strip().upper()
    return u.startswith("HID" + chr(92)) or u.startswith("USB" + chr(92))


_name_cache: dict[str, str] = {}


def _remember_name(instance: str, label: str) -> None:
    if (
        instance
        and _usable_name(label)
        and label.lower() != "hid-compliant game controller"
    ):
        _name_cache[instance.upper()] = label


def _cached_name(instance: str) -> str:
    return _name_cache.get((instance or "").upper(), "")


def _usable_name(text: str) -> str:
    value = (text or "").strip()
    if not value or _looks_like_instance(value):
        return ""
    return value


def _display_name(
    vendor: str, product: str, description: str, dill_name: str = ""
) -> str:
    """HidHide friendly name: vendor + product, else DeviceDescription,
    never the instance path."""
    parts = []
    for part in (vendor, product):
        part = _usable_name(part)
        if part and part not in parts:
            parts.append(part)
    merged = " ".join(parts).strip()
    if merged:
        return merged
    named = _usable_name(dill_name)
    if named:
        return named
    desc = _usable_name(description)
    if desc and desc.lower() != "hid-compliant game controller":
        return desc
    return desc or "HID-compliant game controller"


def last_error() -> str:
    """Why the last driver call failed ("" before any failed)."""
    return _ioctl_error
