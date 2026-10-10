# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import logging
import re
import threading
import uuid
from collections.abc import Callable
from typing import cast

import dill
from gremlin import (
    error,
    shared_state,
)

_joystick_devices: dict[uuid.UUID, dill.DeviceSummary] = collections.OrderedDict()
# vJoy devices left out because of a set-up problem (their DirectInput ids),
# and what is wrong with them; told once the main window is up, and again
# only when it changes.
_left_out: set[uuid.UUID] = set()
_vjoy_problems: list[tuple[int, str]] = []
_told: tuple = ()
_window_up = False
# Gremlin's own Xbox pads seen by the last scan (never devices of the list).
_own_pads: list[dill.DeviceSummary] = []
_joystick_init_lock = threading.Lock()
# Ids the last scan found with another layout than before (02 S143).
_layout_changed: set[uuid.UUID] = set()
SCAN_WAIT_S = 10.0


# Two connected devices with the same name (a pair of identical sticks) used
# to share one module file: claims, card, Button Map and calibration. The
# second one is now "<name> (2)" (a third "(3)"...), so it has its own of
# each. The device the existing <name> file is bound to keeps the plain name,
# and which device is which is kept in the settings (by device id), so the
# names stay the same from session to session and port to port.
TWIN_SETTING = ("global", "internal", "twin-device-names")


def _guid_key(dev: dill.DeviceSummary) -> str:
    return str(dev.device_guid.uuid).upper()


def _file_bound_guid(device_name: str) -> str:
    """The device id the module file named after device_name is bound to."""
    import json

    from gremlin.modules import store

    try:
        path = store.own_path(device_name)
        doc = json.loads(path.read_text(encoding="utf-8"))
        return str(doc.get("boundGuidLocal") or "").strip("{}").upper()
    except Exception:
        return ""


# Twin names not yet written to the settings (the write waits for the main
# thread); the next scan reads these, not the older saved ones.
_twin_lock = threading.Lock()
_twins_unsaved: dict[str, str] | None = None
_TWIN_NUMBER = re.compile(r" \((\d+)\)$")


def _stored_twins() -> dict[str, str]:
    from gremlin.config import Configuration

    with _twin_lock:
        if _twins_unsaved is not None:
            return dict(_twins_unsaved)
    try:
        return dict(Configuration().value(*TWIN_SETTING) or {})
    except Exception:
        return {}


def stored_twins() -> dict[str, str]:
    """The twin names kept for identical sticks (02 S16), {id key: name}:
    for lists that name an unplugged twin as Home does (08 S106a)."""
    return dict(_stored_twins())


def _save_twins(stored: dict[str, str]) -> None:
    """Settings are written on the main thread only: from the hot-plug
    timer thread the write is handed to it."""
    global _twins_unsaved

    with _twin_lock:
        _twins_unsaved = dict(stored)

    def write() -> None:
        global _twins_unsaved
        from gremlin.config import Configuration

        with _twin_lock:
            latest, _twins_unsaved = _twins_unsaved, None
        if latest is None:
            return
        try:
            Configuration().set(*TWIN_SETTING, latest)
        except Exception:
            logging.getLogger("system").exception("Twin device names not saved")

    _on_main_thread(write)


def _on_main_thread(job: Callable[[], None]) -> None:
    """Runs job now on the main thread; from another thread (the hot-plug
    timer) it is handed to the main thread."""
    if threading.current_thread() is threading.main_thread():
        job()
        return
    from PySide6 import QtCore

    app = QtCore.QCoreApplication.instance()
    if app is None:
        job()
        return
    QtCore.QTimer.singleShot(0, app, job)


def _base_name(twin_name: str) -> str:
    """"T.16000M (2)" -> "T.16000M"."""
    return _TWIN_NUMBER.sub("", twin_name)


def _name_twins(devices: list[dill.DeviceSummary]) -> None:
    physical = [dev for dev in devices if not dev.is_virtual]
    stored = _stored_twins()
    changed = False
    for dev in physical:
        key = _guid_key(dev)
        if key not in stored:
            continue
        # A stored name is used only while the driver still reports its
        # base name (02 Q3); a stale one is dropped and worked out again.
        if _base_name(stored[key]) == dev.name:
            dev.name = stored[key]
        else:
            del stored[key]
            changed = True
    groups: dict[str, list[dill.DeviceSummary]] = {}
    for dev in physical:
        groups.setdefault(dev.name, []).append(dev)
    taken = {dev.name for dev in physical} | set(stored.values())
    for name, group in groups.items():
        if len(group) < 2:
            continue
        bound = _file_bound_guid(name)
        # The device the existing file is bound to first, then by id.
        group.sort(key=lambda d: (_guid_key(d) != bound, _guid_key(d)))
        for dev in group[1:]:
            number = 2
            while f"{name} ({number})" in taken:
                number += 1
            dev.name = f"{name} ({number})"
            taken.add(dev.name)
            stored[_guid_key(dev)] = dev.name
            changed = True
    if changed:
        _save_twins(stored)


def device_name(device_guid: object) -> str:
    """A device's name as Gremlin shows it (an identical second stick is
    "<name> (2)"); the driver's name for a device not in the list."""
    uid = getattr(device_guid, "uuid", device_guid)
    dev = _joystick_devices.get(uid)
    if dev is not None:
        return dev.name
    try:
        return dill.DILL.get_device_name(dill.GUID.from_uuid(uid))
    except Exception:
        return ""


def shown_name(device_guid: object) -> str:
    """The one name a screen shows for a device before any alias: the
    device name (twin name for a second identical stick) and, for a vJoy
    device, its number ("vJoy Device 2"). Aliases on top of it:
    gremlin.ui.device_names.display_name."""
    uid = cast(uuid.UUID, getattr(device_guid, "uuid", device_guid))
    dev = _joystick_devices.get(uid)
    if dev is None:
        for pad in _own_pads:
            if pad.device_guid.uuid == uid:
                dev = pad
                break
    if dev is not None and dev.is_virtual and dev.vjoy_id > 0:
        return f"{dev.name} {dev.vjoy_id}"
    if dev is not None:
        return dev.name
    return device_name(uid)


# Device Information marks the devices the program leaves out (02 Q6).
NOTE_LEFT_OUT = "left out (see message)"
NOTE_OWN_PAD = "this program's Xbox pad"


def information_devices() -> list[tuple[dill.DeviceSummary, str]]:
    """Every device Windows reports, for Device Information: the device
    list (with left-out vJoy devices), then Gremlin's own Xbox pads; each
    with its note ("" for a device the program uses)."""
    devices, left_out, pads = _joystick_devices, _left_out, _own_pads
    rows = [
        (dev, NOTE_LEFT_OUT if uid in left_out else "")
        for uid, dev in devices.items()
    ]
    rows.extend((pad, NOTE_OWN_PAD) for pad in pads)
    return rows



def joystick_devices_initialization() -> None:
    """Initializes joystick device information.

    This function retrieves information about various joystick devices and
    associates them and collates their information as required.

    Amongst other things this also ensures that each vJoy device has a correct
    windows id assigned to it.
    """
    # Always released, also when a vJoy check below raises: a lock left held
    # blocked every later device update (hot-plug) for good. A scan that is
    # still busy after SCAN_WAIT_S is reported instead of waited for forever.
    if not _joystick_init_lock.acquire(timeout=SCAN_WAIT_S):
        raise error.GremlinError(
            f"The device scan is still busy after {SCAN_WAIT_S:.0f} s."
        )
    try:
        _initialize_devices()
        # Every re-read: the stored copies (input cache) follow the layouts
        # just read, so a changed layout never leaves a stale copy (02 S142).
        from gremlin import input_cache

        input_cache.Joystick().follow_layouts(list(_joystick_devices.values()))
    finally:
        _joystick_init_lock.release()


def layout_changed() -> set[uuid.UUID]:
    """Ids of the devices the last scan found under the same id with another
    layout (02 S143): to be treated like unplug + plug-in."""
    return set(_layout_changed)


def _describe(layout: tuple[tuple[int, ...], int, int]) -> str:
    axes, buttons, hats = layout
    return f"{len(axes)} axes, {buttons} buttons, {hats} hats"


def _note_layout_changes(devices: list[dill.DeviceSummary]) -> set[uuid.UUID]:
    """Devices still listed whose layout differs from the last scan's
    (an Xbox pad the reader switched from XInput to DirectInput): a
    system.log line and a Trace EVENT line each (02 S143)."""
    from gremlin import input_cache, trace

    changed: set[uuid.UUID] = set()
    for dev in devices:
        old_dev = _joystick_devices.get(dev.device_guid.uuid)
        if old_dev is None:
            continue
        old, new = input_cache.layout_of(old_dev), input_cache.layout_of(dev)
        if old == new:
            continue
        changed.add(dev.device_guid.uuid)
        text = (
            f"{dev.name} changed layout: {_describe(old)} → {_describe(new)}, "
            f"axes {', '.join(map(str, old[0]))} → {', '.join(map(str, new[0]))}, "
            f"buttons {old[1]} → {new[1]}"
        )
        logging.getLogger("system").info(text)
        trace.event(text)
    return changed


def _initialize_devices() -> None:
    global _joystick_devices, _own_pads, _layout_changed

    syslog = logging.getLogger("system")
    syslog.info("Initializing joystick devices")
    syslog.debug(f"{dill.DILL.get_device_count():d} joysticks detected")

    # Process all connected devices in order to properly initialize the
    # device registry.
    devices = []
    own_pads = []
    for i in range(dill.DILL.get_device_count()):
        info = dill.DILL.get_device_information_by_index(i)
        try:
            from vigem.ids import is_vigem_xbox_summary
            if is_vigem_xbox_summary(info):
                syslog.debug(
                    f"Ignored ViGEm Xbox pad: name={info.name} guid={info.device_guid}"
                )
                own_pads.append(info)
                continue
        except Exception:
            pass
        devices.append(info)
    # Not devices of the program, but Device Information lists them (02 Q6).
    _own_pads = own_pads
    _name_twins(devices)

    # Process all devices again to detect those that have been added and those
    # that have been removed since the last time this function ran.

    # Compare existing versus observed devices and only proceed if there
    # is a change to avoid unnecessary work.
    # By device id: DeviceSummary objects are new on every scan, so comparing
    # them found every device "removed" and every event was a change.
    seen = {dev.device_guid.uuid for dev in devices}
    device_added = False
    device_removed = False
    for new_dev in devices:
        if new_dev.device_guid.uuid not in _joystick_devices:
            device_added = True
            syslog.debug(f"Added: name={new_dev.name} guid={new_dev.device_guid}")
    for old_dev in _joystick_devices.values():
        if old_dev.device_guid.uuid not in seen:
            device_removed = True
            syslog.debug(f"Removed: name={old_dev.name} guid={old_dev.device_guid}")

    # A device under the same id with another layout counts as a change
    # too (unplug + plug-in, 02 S143): the list used to keep its old copy.
    _layout_changed = _note_layout_changes(devices)

    # Terminate if no change occurred.
    if not device_added and not device_removed and not _layout_changed:
        return
    vjoy_before = {
        uid for uid, dev in _joystick_devices.items() if dev.is_virtual
    }

    # In order to associate vJoy devices and their ids correctly with DILL
    # device ids a hash is constructed from the number of axes, buttons, and
    # hats. This information is used to attempt to find unambiguous mappings
    # between vJoy and Direct Input devices. If this is not possible Gremlin
    # will terminate as this is a non-recoverable error.

    # A vJoy device with a problem is left out (the rest work); it used to
    # stop the whole program.
    virtual = [dev for dev in devices if dev.is_virtual]
    vjoy_lookup: dict[tuple, dill.DeviceSummary] = {}
    same: set[tuple] = set()
    for dev in virtual:
        hash_value = (dev.axis_count, dev.button_count, dev.hat_count)
        syslog.debug(f"vJoy guid={dev.device_guid}: {hash_value}")
        # Only unique combinations of axes, buttons, and hats can be told
        # apart.
        if hash_value in vjoy_lookup or hash_value in same:
            same.add(hash_value)
            vjoy_lookup.pop(hash_value, None)
            continue
        vjoy_lookup[hash_value] = dev

    problems: list[tuple[int, str]] = []
    alike: dict[tuple, list[int]] = {}
    linked: dict[tuple, int] = {}
    # The vJoy driver is asked through the output module (the layer rule).
    from gremlin.modules import output

    for i in output.vjoy_ids():
        hash_value = output.vjoy_layout(i)
        if hash_value in same:
            alike.setdefault(hash_value, []).append(i)
            continue
        if hash_value in linked:
            # Set up alike, but only one of them listed: which one it is
            # can't be told (it used to go to the last one silently).
            first = linked.pop(hash_value)
            vjoy_lookup.pop(hash_value).set_vjoy_id(-1)
            same.add(hash_value)
            alike.setdefault(hash_value, []).extend([first, i])
            continue
        if not output.vjoy_hats_continuous(i):
            problems.append((i, (
                f"vJoy {i}: its hats are set to discrete; Gremlin-Platforms "
                "needs continuous hats. Change them in Configure vJoy."
            )))
            continue
        if hash_value in vjoy_lookup:
            vjoy_lookup[hash_value].set_vjoy_id(i)
            linked[hash_value] = i
            syslog.debug(f"vjoy id {i}: {hash_value} - MATCH")
        else:
            problems.append((i, (
                f"vJoy {i} is set up, but Windows doesn't list it as a game "
                "controller. Turn it off and on in Configure vJoy, or restart "
                "the PC."
            )))
    for ids in alike.values():
        names = " and ".join(f"vJoy {i}" for i in ids)
        for i in ids:
            problems.append((i, (
                f"{names} have the same number of axes, buttons and hats, so "
                "they can't be told apart. Give one of them a different "
                "number in Configure vJoy."
            )))
    _note_vjoy_problems(
        problems, {dev.device_guid.uuid for dev in virtual if dev.vjoy_id < 1}
    )

    # Reset the vJoy devices so we don't hog the ones we aren't using: only
    # when the vJoy devices themselves changed (and at start). A stick being
    # plugged in no longer releases every vJoy device in the middle of play.
    vjoy_after = {dev.device_guid.uuid for dev in devices if dev.is_virtual}
    if vjoy_after != vjoy_before:
        from gremlin.modules import output

        output.reset_vjoy()

    # Update device list which will be used when queries for joystick devices
    # are made. Order the devices such that vJoy devices are last and the
    # physical devices are ordered by name.
    sorted_devices = sorted(
        [dev for dev in devices if not dev.is_virtual], key=lambda x: x.name
    )
    sorted_devices.extend(
        sorted([dev for dev in devices if dev.is_virtual], key=lambda x: x.vjoy_id)
    )
    # Built aside and swapped in one step: the main and driver threads read
    # the list while a hot-plug scan runs, and used to see it empty or half
    # filled (it was cleared and refilled in place).
    _joystick_devices = collections.OrderedDict(
        (dev.device_guid.uuid, dev) for dev in sorted_devices
    )
    _forget_unplugged(devices + own_pads)


# --- forgetting devices (02 S13, S15; decision D-02-GL243-FORGET) -----------
# A device that has no module file and isn't plugged in at a scan is
# forgotten: its twin name, its alias and its HidHide photo and link. Only
# the program's own settings change (never the HidHide driver); the input
# cache's script objects stay.


def _has_module_file(name: str, guid: str) -> bool:
    """True when the device has a module file (read only; True when it
    can't be told, so nothing is forgotten by mistake)."""
    from gremlin.modules import store

    try:
        if name:
            return store.exists(name, guid)
        # By id only (an alias of a device whose name isn't known): the
        # file chosen for it or bound to it, not the "device" fallback.
        slug = store.slug_for("", guid)
        return slug != store.own_slug("") and store.path_of(slug).is_file()
    except Exception:
        logging.getLogger("system").exception("Module file check failed")
        return True


def _profile_names() -> dict[str, str]:
    """Device id -> name for the devices the open profile has seen."""
    try:
        profile = shared_state.current_profile
        if profile is None:
            return {}
        return {
            str(info.device_uuid).upper(): str(info.name or "")
            for info in profile.device_database.devices.values()
        }
    except Exception:
        return {}


def _forget_unplugged(seen: list[dill.DeviceSummary]) -> None:
    present = {_guid_key(dev) for dev in seen}
    labels = set()
    for dev in seen:
        if dev.is_virtual:
            if dev.vjoy_id > 0:
                labels.add(f"vJoy {dev.vjoy_id}")
        elif dev.name:
            labels.add(dev.name)

    stored = _stored_twins()
    names = {**_profile_names(), **stored}
    kept = {
        key: name for key, name in stored.items()
        if key in present or _has_module_file(name, key)
    }
    if kept != stored:
        for key in stored.keys() - kept.keys():
            logging.getLogger("system").info(f"Forgot twin name {stored[key]}")
        _save_twins(kept)

    def device_gone(uid: str) -> bool:
        key = uid.upper()
        return key not in present and not _has_module_file(names.get(key, ""), key)

    def label_gone(label: str) -> bool:
        return label not in labels and not _has_module_file(label, "")

    def forget_settings() -> None:
        try:
            from gremlin.ui import device_names

            device_names.forget(device_gone)
        except Exception:
            logging.getLogger("system").exception("Aliases not cleaned up")
        try:
            from gremlin.ui import hidhide

            hidhide.forget_devices(label_gone)
        except Exception:
            logging.getLogger("system").exception("HidHide photos not cleaned up")

    _on_main_thread(forget_settings)


def _note_vjoy_problems(
    problems: list[tuple[int, str]], left_out: set[uuid.UUID]
) -> None:
    global _vjoy_problems, _left_out
    for _vid, text in problems:
        logging.getLogger("system").error(f"vJoy left out: {text}")
    _vjoy_problems, _left_out = problems, left_out
    if _window_up:
        _tell_vjoy_problems()


def announce_vjoy_problems() -> None:
    """Once the main window is up: say which vJoy devices were left out
    and why (and from now on whenever that changes)."""
    global _window_up
    _window_up = True
    _tell_vjoy_problems()


def _tell_vjoy_problems() -> None:
    global _told
    key = tuple(_vjoy_problems)
    if key == _told:
        return
    _told = key
    if not key:
        return
    from gremlin.signal import display_error

    ids = sorted({vid for vid, _text in key})
    names = ", ".join(f"vJoy {i}" for i in ids)
    texts = list(dict.fromkeys(text for _vid, text in key))
    display_error(
        f"Gremlin-Platforms is running without {names}.",
        "\n\n".join(texts) + "\n\nThen restart the program.",
    )


def joystick_devices() -> list[dill.DeviceSummary]:
    """Returns the list of joystick like devices.

    Returns:
        List containing information about all joystick devices
    """
    return [
        d for d in _joystick_devices.values() if d.device_guid.uuid not in _left_out
    ]


def vjoy_devices() -> list[dill.DeviceSummary]:
    """Returns the list of vJoy devices.

    Returns:
        List of vJoy devices
    """
    return [
        dev for dev in _joystick_devices.values()
        if dev.is_virtual and dev.device_guid.uuid not in _left_out
    ]


def physical_devices() -> list[dill.DeviceSummary]:
    """Returns the list of physical devices.

    Returns:
        List of physical devices
    """
    return [dev for dev in _joystick_devices.values() if not dev.is_virtual]


def input_devices() -> list[dill.DeviceSummary]:
    """Returns the list of input devices, that is physical and vJoy devices
    that are marked as inputs.

    Returns:
        List of input devices
    """
    vjoy_as_input = {}
    if shared_state.current_profile:
        vjoy_as_input = shared_state.current_profile.settings.vjoy_as_input

    return [
        dev
        for dev in _joystick_devices.values()
        if not dev.is_virtual or vjoy_as_input.get(dev.vjoy_id, False)
    ]


def output_vjoy_devices() -> list[dill.DeviceSummary]:
    """Returns the list of vJoy devices that can be used as outputs.

    Returns:
        List of output vJoy devices
    """
    vjoy_as_input = {}
    if shared_state.current_profile:
        vjoy_as_input = shared_state.current_profile.settings.vjoy_as_input

    return [dev for dev in vjoy_devices() if not vjoy_as_input.get(dev.vjoy_id, False)]


def device_for_uuid(device_uuid: uuid.UUID) -> dill.DeviceSummary:
    return _joystick_devices[device_uuid]
