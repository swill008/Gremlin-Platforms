# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""HidHide control device client. Does not ship or install the driver."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui

from gremlin import config
from gremlin.types import PropertyType
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_CFG_SECTION = "display"
_CFG_GROUP = "hidhide"
_CFG_GAMES = "games"
_CFG_PHOTOS = "photos"
_CFG_LINKS = "module-links"
_CFG_LIST_MODE = "list-mode"
_CFG_HIDDEN = "hidden-devices"
_CFG_CLOAK = "cloak"
_CFG_MANAGED = "managed"
_CFG_GAMING = "gaming-only"
_CFG_WINDOW_W = "window-width"
_CFG_WINDOW_H = "window-height"
_CFG_SPLIT = "split-ratio"
_DOWNLOAD = "https://github.com/nefarius/HidHide/releases"

_DEVICE_TYPE = 32769
_METHOD_BUFFERED = 0
_FILE_READ_DATA = 1


def _ctl(function: int) -> int:
    return (_DEVICE_TYPE << 16) | (_FILE_READ_DATA << 14) | (function << 2) | _METHOD_BUFFERED


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


_debug_log = False


def _hh_log(message: str) -> None:
    if not _debug_log:
        return
    print(f"Hardware Hide {message}", flush=True)

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


def _ensure_options() -> None:
    cfg = config.Configuration()
    try:
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_GAMES,
            PropertyType.String,
            "[]",
            "Hardware Hide game whitelist (name + exe path).",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_PHOTOS,
            PropertyType.String,
            "{}",
            "Hardware Hide device photos keyed by instance id.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_LINKS,
            PropertyType.String,
            "{}",
            "Hardware Hide device to input or output module.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_LIST_MODE,
            PropertyType.String,
            "",
            "Hardware Hide program list mode: allow or block.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_HIDDEN,
            PropertyType.String,
            "",
            "Hardware Hide device instance ids that stay hidden.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_CLOAK,
            PropertyType.String,
            "",
            "Hardware Hide enforcement: on or off.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_MANAGED,
            PropertyType.String,
            "",
            "Set after the user saves HiDHide Enabled. Empty means leave the driver alone.",
            {},
            False,
        )
        cfg.register(
            "global",
            "general",
            "hidhide-on-start",
            PropertyType.Bool,
            False,
            "Turn HiDHide on when Gremlin starts.",
            {},
            True,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_GAMING,
            PropertyType.String,
            "",
            "Limit the HiDHide device list to game controllers.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_WINDOW_W,
            PropertyType.Int,
            720,
            "Hardware Hide window width.",
            {"min": 480, "max": 8000},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_WINDOW_H,
            PropertyType.Int,
            640,
            "Hardware Hide window height.",
            {"min": 360, "max": 8000},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_SPLIT,
            PropertyType.Int,
            600,
            "Hardware Hide device list share of the splitter, in thousandths.",
            {"min": 150, "max": 850},
            False,
        )
    except Exception:
        logging.getLogger("system").exception("HiDHide settings not registered")


def _load_games() -> list[dict]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_GAMES) or "[]")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out = []
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "").strip()
            if not path:
                continue
            name = str(row.get("name") or Path(path).stem)
            out.append({"name": name, "path": path})
    out.sort(key=lambda r: r["name"].lower())
    return out


def _save_games(rows: list[dict]) -> None:
    _ensure_options()
    packed = json.dumps(
        [{"name": r["name"], "path": r["path"]} for r in rows],
        ensure_ascii=True,
    )
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_GAMES, packed)
        _hh_log(f"saved games count={len(rows)}")
    except Exception as exc:
        _hh_log(f"save games failed: {exc}")



def _load_photos() -> dict[str, str]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_PHOTOS) or "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def _save_photos(rows: dict[str, str]) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_PHOTOS, json.dumps(rows, ensure_ascii=True)
        )
    except Exception:
        pass


def _load_links() -> dict[str, str]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_LINKS) or "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def _save_links(rows: dict[str, str]) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_LINKS, json.dumps(rows, ensure_ascii=True)
        )
    except Exception:
        pass


def _saved_block_list() -> bool | None:
    """True is Block list, False is Allow list, None if the user has not chosen."""
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_LIST_MODE) or "").strip().lower()
    if raw == "block":
        return True
    if raw == "allow":
        return False
    return None


def _save_list_mode(block: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_LIST_MODE, "block" if block else "allow"
        )
    except Exception:
        pass


def _apply_saved_list_mode() -> bool:
    """Write Allow list until the user picks Block list."""
    choice = _saved_block_list()
    if choice is None:
        choice = False
        _save_list_mode(False)
    if bool(get_inverse()) != choice:
        if not set_inverse(choice):
            return bool(get_inverse())
    return choice


def _saved_hidden() -> list[str] | None:
    """None means this install has not stored a device list yet."""
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN) or "")
    if not raw.strip():
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, list):
        return None
    return [str(item) for item in loaded if str(item).strip()]


def _save_hidden(ids: list[str]) -> None:
    _ensure_options()
    kept: list[str] = []
    seen: set[str] = set()
    for item in ids:
        text = str(item).strip()
        key = text.upper()
        if not text or key in seen:
            continue
        seen.add(key)
        kept.append(text)
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN, json.dumps(kept, ensure_ascii=True)
        )
    except Exception:
        pass


def _apply_saved_hidden() -> None:
    """Write the saved device list. A new install hides nothing."""
    saved = _saved_hidden()
    if saved is None:
        saved = []
        _save_hidden(saved)
    set_blacklist(saved)


def _saved_cloak() -> bool | None:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_CLOAK) or "").strip().lower()
    if raw == "on":
        return True
    if raw == "off":
        return False
    return None


def _save_cloak(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_CLOAK, "on" if on else "off")
    except Exception:
        pass


def _start_enabled() -> bool:
    _ensure_options()
    return bool(config.Configuration().value("global", "general", "hidhide-on-start"))


def _save_start(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set("global", "general", "hidhide-on-start", bool(on))
    except Exception:
        pass


def _saved_gaming_only() -> bool:
    _ensure_options()
    return str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_GAMING) or "").strip().lower() == "on"


def _save_gaming_only(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_GAMING, "on" if on else "off")
    except Exception:
        pass


def _hidhide_managed() -> bool:
    _ensure_options()
    return str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_MANAGED) or "").strip().lower() == "yes"


def _mark_managed() -> None:
    _set_managed(True)


def _clear_managed() -> None:
    _set_managed(False)


def _set_managed(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_MANAGED, "yes" if on else "")
    except Exception:
        pass


def _apply_saved_cloak() -> bool:
    """Write HiDHide Enabled. The unset value is off, and it is not taken from the driver."""
    choice = _saved_cloak()
    if choice is None:
        choice = False
        _save_cloak(False)
    if bool(get_active()) != choice:
        set_active(choice)
    return choice


def _module_label(dev) -> str:
    if getattr(dev, "is_virtual", False):
        return f"vJoy {int(getattr(dev, 'vjoy_id', 0) or 0)}"
    return str(getattr(dev, "name", "") or "")


def _collection_index(instance: str) -> int | None:
    import re
    text = (instance or "").upper()
    match = re.search(r"&([0-9A-F]{4})$", text)
    if match:
        return int(match.group(1), 16)
    match = re.search(r"COL(\d+)", text)
    if match:
        return max(0, int(match.group(1)) - 1)
    return None


def _module_photo(hw, name: str) -> str:
    if hw is None or not name:
        return ""
    try:
        url = hw.profilePhotoUrl(name) or ""
    except Exception:
        url = ""
    if url:
        return url
    if name.lower().startswith("vjoy"):
        try:
            return hw.profilePhotoUrl("vJoy") or ""
        except Exception:
            return ""
    return ""


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


def _dill_matches() -> list:
    try:
        from gremlin.device_initialization import joystick_devices
        return list(joystick_devices())
    except Exception:
        return []


def _photo_dir() -> Path:
    root = Path(sys.argv[0]).resolve().parent
    folder = root / "qml" / "maps" / "hidhide_photos"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _file_url(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.resolve().as_uri()


def _gremlin_exe() -> str:
    # HidHide matches the process image, not the script. Ask Windows for this process.
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        k32.GetModuleFileNameW.restype = wintypes.DWORD
        buf = ctypes.create_unicode_buffer(32768)
        if k32.GetModuleFileNameW(None, buf, len(buf)):
            return buf.value
    return str(Path(sys.executable).resolve())


def _nt_image_path(path: str) -> str:
    """Same NT path HiDHide stores: GetFinalPathNameByHandleW(VOLUME_NAME_NT)."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
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
    """Dos path to the volume path HidHide compares. Existing volume paths pass through."""
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
    k32.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    k32.GetVolumePathNameW.restype = wintypes.BOOL
    k32.GetVolumeNameForVolumeMountPointW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
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
    rest = text[len(mount):].lstrip("\\")
    image = device if not rest else f"{device}\\{rest}"
    _hh_log(f"image {text} -> {image}")
    return image


def _open_control():
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
        _hh_log(f"open \\\\.\\HidHide failed err={ctypes.get_last_error()} handle={handle!r}")
        return None
    return handle
def _close(handle) -> None:
    if handle:
        __import__("ctypes").windll.kernel32.CloseHandle(handle)


_ioctl_error = ""


def _ioctl(handle, code: int, inn: bytes | None = None, out_size: int = 0) -> tuple[bool, bytes]:
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
        _ioctl_error = f"HiDHide driver call failed ({ctypes.get_last_error()})."
    name = _IOCTL_NAMES.get(int(code) & 0xFFFFFFFF, "OTHER")
    _hh_log(
        f"ioctl {name} code=0x{int(code) & 0xFFFFFFFF:08X} in={in_len} out={out_size} "
        f"ok={bool(ok)} returned={int(returned.value)} err={0 if ok else ctypes.get_last_error()}"
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
    """Installer version, then HidHide.sys file version if the registry key is absent."""
    if os.name != "nt":
        return ""
    import winreg
    for name in (
        r"SOFTWARE\Classes\Installer\Dependencies\NSS.Drivers.HidHide.x64",
        r"SOFTWARE\Classes\Installer\Dependencies\NSS.Drivers.HidHide.arm64",
    ):
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, name, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ) as key:
                value, _ = winreg.QueryValueEx(key, "Version")
        except OSError:
            continue
        text = str(value or "").strip()
        if text:
            return text
    root = os.environ.get("SystemRoot", r"C:\Windows")
    path = os.path.join(root, "System32", "drivers", "HidHide.sys")
    if not os.path.isfile(path):
        return ""
    import ctypes
    from ctypes import wintypes
    ver = ctypes.WinDLL("version", use_last_error=True)
    ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    ver.GetFileVersionInfoW.restype = wintypes.BOOL
    ver.VerQueryValueW.argtypes = [
        ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)
    ]
    ver.VerQueryValueW.restype = wintypes.BOOL
    ignored = wintypes.DWORD(0)
    size = ver.GetFileVersionInfoSizeW(path, ctypes.byref(ignored))
    if not size:
        return ""
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return ""

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wintypes.DWORD),
            ("dwStrucVersion", wintypes.DWORD),
            ("dwFileVersionMS", wintypes.DWORD),
            ("dwFileVersionLS", wintypes.DWORD),
            ("dwProductVersionMS", wintypes.DWORD),
            ("dwProductVersionLS", wintypes.DWORD),
            ("dwFileFlagsMask", wintypes.DWORD),
            ("dwFileFlags", wintypes.DWORD),
            ("dwFileOS", wintypes.DWORD),
            ("dwFileType", wintypes.DWORD),
            ("dwFileSubtype", wintypes.DWORD),
            ("dwFileDateMS", wintypes.DWORD),
            ("dwFileDateLS", wintypes.DWORD),
        ]

    ptr = ctypes.c_void_p()
    length = wintypes.UINT(0)
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)):
        return ""
    info = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    ms, ls = int(info.dwFileVersionMS), int(info.dwFileVersionLS)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


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


def get_whitelist() -> list[str]:
    return _get_multi(IOCTL_GET_WHITELIST)


def set_whitelist(paths: list[str]) -> bool:
    return _set_multi(IOCTL_SET_WHITELIST, paths)


def _is_virtual(instance: str, name: str) -> bool:
    blob = f"{instance} {name}".upper()
    return any(
        tag in blob
        for tag in (
            "VID_1234",
            "VJOY",
            "VIGEM",
            "XBOX 360 CONTROLLER",
            "VIRTUAL HID",
            "ROOT\\SYSTEM",
        )
    )


def _is_keyboard_mouse(instance: str, name: str) -> bool:
    blob = f"{instance} {name}".upper()
    return "KEYBOARD" in blob or "MOUSE" in blob or "&MI_01" in blob and "KBD" in blob



def list_hid_devices(gaming_only: bool) -> list[dict]:
    """HidHide HidDevices(). Tools → Hardware Hide only."""
    if os.name != "nt":
        return []
    return _list_hidhide_class_enum(gaming_only)


def _hid_guid():
    import ctypes
    hid = ctypes.WinDLL("hid")
    guid = (ctypes.c_ubyte * 16)()
    hid.HidD_GetHidGuid(ctypes.byref(guid))
    return guid


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
        ctypes.POINTER(wintypes.ULONG), wintypes.LPCWSTR, wintypes.ULONG
    ]
    cfg.CM_Get_Device_ID_List_SizeW.restype = wintypes.DWORD
    cfg.CM_Get_Device_ID_ListW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.ULONG, wintypes.ULONG
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
        ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD
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
    flags = CM_GETIDLIST_FILTER_CLASS  # HidHide DeviceInstancePathsPresentOrNot: no FILTER_PRESENT
    global _WALK_STATS
    if cfg.CM_Get_Device_ID_List_SizeW(ctypes.byref(size), class_s, flags) != CR_SUCCESS:
        _WALK_STATS = {"error": "CM_Get_Device_ID_List_SizeW", "cmSize": int(size.value)}
        return []
    if size.value < 2:
        _WALK_STATS = {"error": "cm size < 2", "cmSize": int(size.value)}
        return []
    buf = ctypes.create_unicode_buffer(size.value)
    if cfg.CM_Get_Device_ID_ListW(class_s, buf, size.value, flags) != CR_SUCCESS:
        _WALK_STATS = {"error": "CM_Get_Device_ID_ListW", "cmSize": int(size.value)}
        return []
    instances = [p for p in ctypes.wstring_at(ctypes.addressof(buf), size.value).split(chr(0)) if p]
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
    DIGCF_PRESENT = 0x00000002
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
        handle = k32.CreateFileW(link, GENERIC_READ, FILE_SHARE, None, 3, FILE_ATTRIBUTE_NORMAL, None)
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
                if hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)) and preparsed:
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
            _looks_like_instance(group["name"]) or len(_usable_name(label)) > len(group["name"])
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
    """HidHide DeviceDescription: DEVPKEY_Device_DeviceDesc via CM_Get_DevNode_PropertyW."""
    if not instance or os.name != "nt":
        return ""
    import ctypes
    from ctypes import wintypes
    cfg = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    CR_SUCCESS = 0
    CR_BUFFER_SMALL = 26
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
    if cfg.CM_Get_DevNode_PropertyW(
        devinst, ctypes.byref(key), ctypes.byref(ptype), buf, ctypes.byref(size), 0
    ) != CR_SUCCESS:
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
    if cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), instance, CM_LOCATE_DEVNODE_PHANTOM) != CR_SUCCESS:
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
    if instance and _usable_name(label) and label.lower() != "hid-compliant game controller":
        _name_cache[instance.upper()] = label


def _cached_name(instance: str) -> str:
    return _name_cache.get((instance or "").upper(), "")


def _usable_name(text: str) -> str:
    value = (text or "").strip()
    if not value or _looks_like_instance(value):
        return ""
    return value


def _display_name(vendor: str, product: str, description: str, dill_name: str = "") -> str:
    """HidHide friendly name: vendor + product, else DeviceDescription, never the instance path."""
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


def _friendly_name(instance: str) -> str:
    return _usable_name(_device_description(instance))



def _enrich_devices(rows: list[dict]) -> list[dict]:
    photos = _load_photos()
    links = _load_links()
    dill_devs = _dill_matches()
    hw = None
    try:
        from gremlin.ui.hardware_profile import HardwareProfile
        hw = HardwareProfile()
    except Exception:
        hw = None
    physical = [dev for dev in dill_devs if not getattr(dev, "is_virtual", False)]
    virtual = [dev for dev in dill_devs if getattr(dev, "is_virtual", False)]
    by_vjoy = {}
    for dev in virtual:
        try:
            by_vjoy[int(dev.vjoy_id)] = dev
        except (TypeError, ValueError, AttributeError):
            continue
    known = {_module_label(dev) for dev in dill_devs if _module_label(dev)}
    present = {str(row.get("instanceId") or "").upper() for row in rows}
    used = {
        name for key, name in links.items()
        if str(key).upper() in present and name in known
    }
    changed = False
    for row in rows:
        instance = row["instanceId"]
        vid, pid = _vid_pid(instance)
        match = None
        if vid is not None and pid is not None:
            hits = []
            for dev in physical:
                try:
                    if int(dev.vendor_id) == vid and int(dev.product_id) == pid:
                        hits.append(dev)
                except Exception:
                    continue
            if len(hits) == 1:
                match = hits[0]
        if match and match.name:
            row["name"] = _display_name("", "", row.get("name") or "", match.name)
        else:
            row["name"] = _display_name("", "", row.get("name") or "", "")
        module = links.get(instance) or links.get(instance.upper(), "")
        if module not in known:
            module = ""
            if match is not None:
                module = _module_label(match)
            elif _looks_vjoy(row):
                index = _collection_index(instance)
                dev = by_vjoy.get((index + 1) if index is not None else -1)
                if dev is not None and _module_label(dev) not in used:
                    module = _module_label(dev)
                else:
                    for candidate in sorted(by_vjoy):
                        label = _module_label(by_vjoy[candidate])
                        if label and label not in used:
                            module = label
                            break
            if module:
                links[instance] = module
                used.add(module)
                changed = True
                _hh_log(f"module link {instance} -> {module}")
        elif instance not in links:
            links[instance] = module
            changed = True
        photo = photos.get(instance) or photos.get(instance.upper(), "")
        override = Path(photo) if photo and not str(photo).startswith("file:") else None
        if override is not None and override.is_file():
            row["photo"] = _file_url(override)
            row["photoSource"] = "override"
        elif photo and str(photo).startswith("file:"):
            row["photo"] = photo
            row["photoSource"] = "override"
        else:
            row["photo"] = _module_photo(hw, module)
            row["photoSource"] = "module" if row["photo"] else ""
    if changed:
        _save_links(links)
    return rows


def _sorted_devices(rows: list[dict]) -> list[dict]:
    """By name like HidHide's device list.

    The instance id keeps equal names in a fixed order.
    """
    def key(row: dict) -> tuple[str, str]:
        name = str(row.get("name") or "").lower()
        return name, str(row.get("instanceId") or "").upper()

    return sorted(rows, key=key)


def _looks_vjoy(row: dict) -> bool:
    name = str(row.get("name") or "").lower()
    instance = str(row.get("instanceId") or "").upper()
    return "vjoy" in name or "HIDCLASS" in instance

@ta.QmlElement
class HidHideModel(QtCore.QObject):
    """System-wide HidHide panel. Persistent cloak, devices, and game list."""

    changed = QtCore.Signal()
    debugChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._present = False
        self._active = False
        self._driver_active = False
        self._devices: list[dict] = []
        self._games: list[dict] = []
        self._gaming_only = _saved_gaming_only()
        self._generation = 0
        self._last_error = ""
        self._inverse = False
        self._version = ""
        _ensure_options()
        self.reload()

    def reload(self) -> None:
        self._present = driver_present()
        self._driver_active = get_active() if self._present else False
        saved_cloak = _saved_cloak()
        self._active = bool(saved_cloak) if saved_cloak is not None else False
        saved_block = _saved_block_list()
        self._inverse = bool(saved_block) if saved_block is not None else False
        self._version = driver_version() if self._present else ""
        saved_ids = {i.upper() for i in (_saved_hidden() or [])}
        driver_ids = {i.upper() for i in get_blacklist()} if self._present else set()
        self._devices = []
        try:
            rows = list_hid_devices(self._gaming_only)
        except Exception:
            import traceback
            traceback.print_exc()
            rows = []
        built = []
        for row in _enrich_devices(rows):
            item = dict(row)
            ids = [str(x).upper() for x in (item.get("instanceIds") or [item.get("instanceId")]) if x]
            item["session"] = any(i in saved_ids for i in ids)
            item["clientBlocked"] = any(i in driver_ids for i in ids)
            item["hidden"] = item["clientBlocked"]
            item["confirmed"] = bool(self._driver_active and item["clientBlocked"])
            built.append(item)
        self._devices = _sorted_devices(built)
        self._games = _load_games()
        self._generation += 1
        _hh_log(
            f"reload present={self._present} version={self._version} cloak={self._active} "
            f"driver={self._driver_active} inverse={self._inverse} "
            f"client={len(driver_ids)} rows={len(self._devices)}"
        )
        self.changed.emit()

    @QtCore.Property(bool, notify=changed)
    def installed(self) -> bool:
        return self._present

    @QtCore.Property(str, notify=changed)
    def driverVersion(self) -> str:
        return self._version

    @QtCore.Property(int, constant=True)
    def windowWidth(self) -> int:
        _ensure_options()
        try:
            return max(480, int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_W)))
        except (TypeError, ValueError):
            return 720

    @QtCore.Property(int, constant=True)
    def windowHeight(self) -> int:
        _ensure_options()
        try:
            return max(360, int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_H)))
        except (TypeError, ValueError):
            return 640

    @QtCore.Slot(int, int)
    def saveWindowSize(self, width: int, height: int) -> None:
        _ensure_options()
        cfg = config.Configuration()
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_W, max(480, min(8000, int(width))))
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_H, max(360, min(8000, int(height))))

    @QtCore.Property(int, constant=True)
    def splitRatio(self) -> int:
        _ensure_options()
        try:
            return max(150, min(850, int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT))))
        except (TypeError, ValueError):
            return 600

    @QtCore.Slot(int)
    def saveSplitRatio(self, ratio: int) -> None:
        _ensure_options()
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_SPLIT, max(150, min(850, int(ratio)))
        )

    @QtCore.Property(str, constant=True)
    def downloadUrl(self) -> str:
        return _DOWNLOAD

    @QtCore.Property(bool, notify=changed)
    def cloakOn(self) -> bool:
        return self._active

    @QtCore.Property(bool, notify=changed)
    def inverseOn(self) -> bool:
        return self._inverse

    @QtCore.Slot(bool, result=bool)
    def setInverse(self, on: bool) -> bool:
        if not self._present or not _hidhide_managed():
            return False
        if not set_inverse(bool(on)):
            self._last_error = _ioctl_error or "HiDHide driver call failed."
            self.reload()
            return False
        _save_list_mode(bool(on))
        self._inverse = bool(on)
        self._last_error = ""
        self._sync_whitelist()
        self.reload()
        return True

    @QtCore.Property(bool, notify=changed)
    def gamingOnly(self) -> bool:
        return self._gaming_only

    @QtCore.Slot(bool)
    def setGamingOnly(self, on: bool) -> None:
        self._gaming_only = bool(on)
        _save_gaming_only(self._gaming_only)
        self.reload()

    @QtCore.Property(int, notify=changed)
    def generation(self) -> int:
        return self._generation

    @QtCore.Property(str, notify=changed)
    def lastError(self) -> str:
        return self._last_error

    @QtCore.Property(int, notify=changed)
    def deviceCount(self) -> int:
        return len(self._devices)

    
    @QtCore.Property(int, notify=changed)
    def gameCount(self) -> int:
        return len(self._games)

    @QtCore.Slot(int, result="QVariant")
    def deviceAt(self, index: int):
        if 0 <= index < len(self._devices):
            return self._devices[index]
        return {}

    @QtCore.Slot(int, result="QVariant")
    def gameAt(self, index: int):
        if 0 <= index < len(self._games):
            return self._games[index]
        return {}

    @QtCore.Property(bool, notify=changed)
    def gremlinControl(self) -> bool:
        return _hidhide_managed()

    @QtCore.Slot(bool, result=bool)
    def setGremlinControl(self, on: bool) -> bool:
        if not self._present:
            return False
        if on:
            _mark_managed()
            apply_saved_list()
        else:
            _clear_managed()
        self.reload()
        return True

    @QtCore.Property(bool, notify=changed)
    def startOn(self) -> bool:
        return _start_enabled()

    @QtCore.Slot(bool, result=bool)
    def setStartOn(self, on: bool) -> bool:
        _save_start(bool(on))
        self.changed.emit()
        return True

    @QtCore.Slot(bool, result=bool)
    def setCloak(self, on: bool) -> bool:
        if not self._present or not _hidhide_managed():
            return False
        if not set_active(bool(on)):
            return False
        _save_cloak(bool(on))
        self.reload()
        return True

    @QtCore.Slot(str, bool, result=bool)
    def setDeviceHidden(self, instance_id: str, hidden: bool) -> bool:
        if not self._present or not instance_id or not _hidhide_managed():
            return False
        group_ids = [instance_id]
        for row in self._devices:
            ids = row.get("instanceIds") or [row.get("instanceId")]
            if instance_id.upper() in {str(x).upper() for x in ids}:
                group_ids = [str(x) for x in ids if x]
                break
        drop = {x.upper() for x in group_ids}
        base = _saved_hidden()
        if base is None:
            base = []
        kept = [i for i in base if i.upper() not in drop]
        if hidden:
            have = {i.upper() for i in kept}
            for group_id in group_ids:
                if group_id.upper() not in have:
                    kept.append(group_id)
                    have.add(group_id.upper())
        _hh_log(f"set hidden={bool(hidden)} id={instance_id} group={group_ids} blacklist={kept}")
        _save_hidden(kept)
        if not set_blacklist(kept):
            self._last_error = _ioctl_error or "HiDHide driver call failed."
            _hh_log(f"set blacklist failed: {self._last_error}")
            self.reload()
            return False
        self._last_error = ""
        self.reload()
        return True

    @QtCore.Slot(str, str, result=bool)
    def addGame(self, name: str, path: str) -> bool:
        path = str(Path(path).resolve()) if path else ""
        if not path:
            return False
        label = (name or "").strip() or Path(path).stem
        rows = [r for r in self._games if Path(r["path"]).resolve().as_posix().lower() != Path(path).as_posix().lower()]
        rows.append({"name": label, "path": path})
        rows.sort(key=lambda r: r["name"].lower())
        _save_games(rows)
        self._games = rows
        self._sync_whitelist()
        self.changed.emit()
        return True

    @QtCore.Slot(str, result=bool)
    def removeGame(self, path: str) -> bool:
        rows = [r for r in self._games if r["path"] != path]
        _save_games(rows)
        self._games = rows
        self._sync_whitelist()
        self.changed.emit()
        return True

    @QtCore.Slot(str, str, result=bool)
    def setDevicePhoto(self, instance_id: str, path: str) -> bool:
        if not instance_id or not path:
            return False
        src = Path(path)
        if not src.is_file():
            # QML file url
            text = path
            if text.startswith("file:///"):
                text = text[8:]
            src = Path(text)
        if not src.is_file():
            return False
        dest = _photo_dir() / f"{abs(hash(instance_id)) & 0xFFFFFFFF:08x}{src.suffix.lower() or '.jpg'}"
        try:
            from gremlin.ui.hardware_profile import limit_image_file
            limit_image_file(src, dest)
        except OSError:
            return False
        photos = _load_photos()
        photos[instance_id] = str(dest)
        _save_photos(photos)
        self.reload()
        return True

    @QtCore.Slot()
    def refresh(self) -> None:
        self.reload()

    @QtCore.Property(bool, notify=debugChanged)
    def debugLog(self) -> bool:
        return _debug_log

    @QtCore.Slot(bool)
    def setDebugLog(self, enabled: bool) -> None:
        global _debug_log
        _debug_log = bool(enabled)
        self.debugChanged.emit()

    @QtCore.Slot()
    def openDownload(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(_DOWNLOAD))

    @QtCore.Slot()
    def openGameControllers(self) -> None:
        if os.name != "nt":
            return
        import subprocess
        try:
            subprocess.Popen(
                ["rundll32.exe", "shell32.dll,Control_RunDLL", "joy.cpl"],
                close_fds=True,
            )
        except OSError as exc:
            _hh_log(f"joy.cpl failed: {exc}")

    def _ensure_gremlin_whitelisted(self) -> None:
        self._sync_whitelist()

    def _sync_whitelist(self) -> None:
        if not self._present:
            return
        apply_saved_list()


def apply_on_start() -> None:
    """If Automatically Start is on, turn on Gremlin control and HiDHide Enabled."""
    _ensure_options()
    if not _start_enabled():
        _hh_log("start skipped, Automatically Start is off")
        return
    if not driver_present():
        _hh_log("start skipped, driver not present")
        return
    _hh_log("Automatically Start")
    _mark_managed()
    _save_cloak(True)
    apply_saved_list()


def apply_saved_list() -> None:
    """Write Gremlin's saved HiDHide settings after the user has saved HiDHide Enabled."""
    if not driver_present():
        _hh_log("apply skipped, driver not present")
        return
    if not _hidhide_managed():
        _hh_log("apply skipped, Gremlin control is off")
        return
    _hh_log("apply saved list")
    inverse = _apply_saved_list_mode()
    _hh_log(f"list mode block={inverse}")
    gremlin = _gremlin_exe()
    gremlin_image = _full_image_name(gremlin)
    drop = set()
    if inverse:
        if gremlin:
            drop.add(gremlin.lower())
        if gremlin_image:
            drop.add(gremlin_image.lower())
    wanted = []
    for row in _load_games():
        image = _full_image_name(row["path"])
        if image:
            wanted.append(image)
        else:
            _hh_log(f"game path not converted {row['path']}")
    if not inverse and gremlin_image:
        wanted.append(gremlin_image)
    elif not inverse and not gremlin_image:
        _hh_log(f"gremlin path not converted {gremlin}")
    merged = []
    seen = set()
    for item in wanted:
        key = item.lower()
        if key in seen or not item or key in drop:
            continue
        seen.add(key)
        merged.append(item)
    _hh_log(f"whitelist count={len(merged)} inverse={inverse}")
    set_whitelist(merged)
    _apply_saved_hidden()
    cloak = _apply_saved_cloak()
    _hh_log(f"cloak={cloak}")
