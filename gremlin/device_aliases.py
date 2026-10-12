# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The names the user gives devices (the Home card name, 10 S7): kept in the
settings, read by every screen. Not UI: gremlin/modules (the Device Library)
reads and renames through it. A rename renames the device's folder first
and is refused, unsaved, when that fails (03 S131). It owns the "device
names changed" notice (signal.deviceNamesChanged, D-01-OWNER-NOTICES): a
rename, a forget, a History put-back of the names and a device scan send it,
once per burst, on the main thread."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from gremlin.config import Configuration
from gremlin.notice import BurstNotice, NoticeTimer
from gremlin.types import PropertyType

SECTION = "devices"
GROUP = "display"
NAME = "aliases"

_CACHE: dict[str, str] | None = None
# The stored list _CACHE was read from: a value put back from outside
# (Tools > History Restore) is read again.
_CACHE_RAW: list | None = None


def _ensure() -> Configuration:
    cfg = Configuration()
    if not cfg.exists(SECTION, GROUP, NAME):
        cfg.register(
            SECTION,
            GROUP,
            NAME,
            PropertyType.List,
            [],
            "Friendly display names for devices and inputs.",
            {},
            False,
        )
    return cfg


def _load() -> dict[str, str]:
    global _CACHE, _CACHE_RAW
    raw = _ensure().value(SECTION, GROUP, NAME) or []
    if _CACHE is not None and raw == _CACHE_RAW:
        return _CACHE
    names: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, list) and len(entry) >= 2:
            key = str(entry[0]).strip()
            value = str(entry[1]).strip()
            if key:
                names[key] = value
    _CACHE = names
    _CACHE_RAW = [list(e) if isinstance(e, list) else e for e in raw]
    return names


def _save(names: dict[str, str]) -> None:
    global _CACHE, _CACHE_RAW, _ANNOUNCED_RAW
    _CACHE = dict(names)
    rows = [[key, value] for key, value in names.items() if value]
    _CACHE_RAW = [list(row) for row in rows]
    _ANNOUNCED_RAW = [list(row) for row in rows]
    _ensure().set(SECTION, GROUP, NAME, rows)


def _same_key(key: object) -> str:
    """Device ids match without braces or case ({ABC-1} == abc-1); other
    keys ("keyboard", "xbox") as they are, trimmed."""
    text = str(key or "").strip()
    bare = text.strip("{}")
    try:
        return str(uuid.UUID(bare)).upper()
    except ValueError:
        return text


def _stored_key(names: dict[str, str], key: object) -> str | None:
    want = _same_key(key)
    for stored in names:
        if _same_key(stored) == want:
            return stored
    return None


def display_name(key: str, default: str) -> str:
    """The alias the user gave (Home device list, Device Mapping Editor), else default.
    A reader of the names: the notice is started, so it hears a History
    put-back and a device scan."""
    watch_names()
    return _alias_or(key, default)


def _alias_or(key: str, default: str) -> str:
    names = _load()
    stored = _stored_key(names, key)
    alias = names.get(stored, "").strip() if stored is not None else ""
    return alias or default


# --- the "device names changed" notice (D-01-OWNER-NOTICES) ------------------

# The stored names as last announced: a list put back from outside (Tools >
# History Restore, then configChanged) that differs is announced.
_ANNOUNCED_RAW: list | None = None


def _stored_raw() -> list:
    raw = _ensure().value(SECTION, GROUP, NAME) or []
    return [list(e) if isinstance(e, list) else e for e in raw]


def _settings_changed() -> None:
    global _ANNOUNCED_RAW
    raw = _stored_raw()
    if raw != _ANNOUNCED_RAW:
        before, _ANNOUNCED_RAW = _ANNOUNCED_RAW, raw
        _sync_folders(before or [], raw)
        notify_names()


# The shown names of the plugged-in devices at the last device scan.
_SCAN_NAMES: dict[str, str] = {}


def _scan_names() -> dict[str, str]:
    from gremlin import device_initialization

    names: dict[str, str] = {}
    for dev in device_initialization.joystick_devices():
        uid = getattr(dev.device_guid, "uuid", dev.device_guid)
        names[str(uid)] = _alias_or(str(uid), device_initialization.shown_name(uid))
    return names


def _scanned() -> None:
    """After a device scan: announced only when a device plugged in before
    and after shows another name (a twin's number); a device plugged in or
    out is the device list's own news (device_change_event)."""
    global _SCAN_NAMES
    try:
        now = _scan_names()
    except Exception:  # noqa: BLE001 - a scan never fails on a name
        logging.getLogger("system").exception("Device names: scan not read")
        return
    before, _SCAN_NAMES = _SCAN_NAMES, now
    if any(before[uid] != name for uid, name in now.items() if uid in before):
        notify_names()


def _send_names() -> None:
    from gremlin.signal import signal

    signal.deviceNamesChanged.emit()


def _listen_names(_timer: NoticeTimer) -> None:
    global _ANNOUNCED_RAW, _SCAN_NAMES
    from gremlin.signal import signal

    _ANNOUNCED_RAW = _stored_raw()
    signal.configChanged.connect(_settings_changed)
    try:
        from gremlin import event_handler

        # A device scan can change a shown name (a twin's short id).
        _SCAN_NAMES = _scan_names()
        event_handler.EventListener().device_change_event.connect(_scanned)
    except Exception:  # noqa: BLE001 - no device listener (some tests)
        logging.getLogger("system").debug(
            "Device names notice: no device listener", exc_info=True
        )


_names = BurstNotice(_send_names, _listen_names)


def watch_names() -> NoticeTimer | None:
    """Starts the notice (once, on the main thread); every reader of the
    shown names calls it."""
    return _names.watch()


def notify_names() -> None:
    """A device's shown name may have changed: signal.deviceNamesChanged
    goes out once for a burst, on the main thread. Any thread may call it."""
    _names.notify()


def _device_id(key: object) -> uuid.UUID | None:
    """The device id of an alias key whose device has a folder named after
    its shown name: a stick or other external device. None for the
    built-ins ("keyboard", "osc", ... and their ids: fixed folder names) and
    vJoy devices (their folder is "vJoy N")."""
    try:
        uid = uuid.UUID(str(key or "").strip().strip("{}"))
    except ValueError:
        return None
    from gremlin import device_initialization
    from gremlin.modules import device_class

    if device_class.is_fixed_id(uid):
        return None
    try:
        if device_initialization.device_for_uuid(uid).is_virtual:
            return None
    except KeyError:
        pass
    return uid


def _rename_folder(key: object, alias: str) -> str:
    """Renames the device's folder to its new shown name (03 S131): "" when
    done or there is nothing to rename, else why it was refused."""
    uid = _device_id(key)
    if uid is None:
        return ""
    from gremlin import device_initialization
    from gremlin.modules import store

    own = device_initialization.shown_name(uid)
    device_name = device_initialization.device_name(uid) or own
    shown = alias or own
    if not shown:
        return ""
    try:
        ok, reason = store.rename_device_dir(device_name or shown, str(uid), shown)
    except Exception as exc:  # noqa: BLE001 - a failed rename is refused
        logging.getLogger("system").exception(f"Device folder of {shown} not renamed")
        return f"The device's folder could not be renamed to {shown} ({exc})."
    if ok:
        return ""
    return reason or f"The device's folder could not be renamed to {shown}."


def set_alias(key: str, value: str) -> str:
    """Gives a device its shown name (an empty value takes the alias away).
    Its folder is renamed first (03 S131); when that is refused nothing
    changes and the reason is returned. "" when done."""
    names = dict(_load())
    stored = _stored_key(names, key)
    text = str(value or "").strip()
    current = names.get(stored, "").strip() if stored is not None else ""
    if text != current:
        reason = _rename_folder(key, text)
        if reason:
            logging.getLogger("system").warning(f"Rename refused: {reason}")
            return reason
    if stored is not None:
        names.pop(stored)
    key = str(key).strip()
    if text:
        names[key] = text
    _save(names)
    notify_names()
    return ""


def _sync_folders(before: list, after: list) -> None:
    """Names put back from outside (History Restore): the folders of the
    devices whose alias changed follow (store.sync_dir_name logs a folder
    it can't rename; no message)."""

    def as_dict(rows: list) -> dict[str, str]:
        return {
            _same_key(row[0]): str(row[1]).strip()
            for row in rows
            if isinstance(row, list) and len(row) >= 2
        }

    old, new = as_dict(before or []), as_dict(after)
    from gremlin import device_initialization
    from gremlin.modules import store

    for key in old.keys() | new.keys():
        if old.get(key) == new.get(key):
            continue
        uid = _device_id(key)
        if uid is None:
            continue
        name = device_initialization.device_name(uid)
        name = name or device_initialization.shown_name(uid)
        try:
            store.sync_dir_name(name, str(uid))
        except Exception:  # noqa: BLE001 - logged; the names still change
            logging.getLogger("system").exception(
                f"Device folder of {name} not checked"
            )


def forget(gone: Callable[[str], bool]) -> bool:
    """Drops the alias of every device gone(id) says is forgotten (no
    module file, not plugged in: D-02-GL243-FORGET); keys that aren't device
    ids ("keyboard", "xbox") stay. True when one was dropped."""
    names = _load()
    kept: dict[str, str] = {}
    for key, value in names.items():
        try:
            uid = str(uuid.UUID(str(key).strip().strip("{}"))).upper()
        except ValueError:
            kept[key] = value
            continue
        if not gone(uid):
            kept[key] = value
    if len(kept) == len(names):
        return False
    _save(kept)
    notify_names()
    return True
