# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import logging
import threading
import uuid

import dill
from gremlin import (
    error,
    shared_state,
)
from vjoy import vjoy

_joystick_devices: dict[uuid.UUID, dill.DeviceSummary] = collections.OrderedDict()
# vJoy devices left out because of a set-up problem (their DirectInput ids),
# and what is wrong with them; told once the main window is up, and again
# only when it changes.
_left_out: set[uuid.UUID] = set()
_vjoy_problems: list[tuple[int, str]] = []
_told: tuple = ()
_window_up = False
_joystick_init_lock = threading.Lock()
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

    from gremlin.modules.registry import plain_slug
    from gremlin.util import modules_dir

    try:
        path = modules_dir() / f"{plain_slug(device_name)}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        return str(doc.get("boundGuidLocal") or "").strip("{}").upper()
    except Exception:
        return ""


def _name_twins(devices: list[dill.DeviceSummary]) -> None:
    from gremlin.config import Configuration

    physical = [dev for dev in devices if not dev.is_virtual]
    try:
        stored = dict(Configuration().value(*TWIN_SETTING) or {})
    except Exception:
        stored = {}
    for dev in physical:
        if _guid_key(dev) in stored:
            dev.name = stored[_guid_key(dev)]
    groups: dict[str, list[dill.DeviceSummary]] = {}
    for dev in physical:
        groups.setdefault(dev.name, []).append(dev)
    taken = {dev.name for dev in physical} | set(stored.values())
    changed = False
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
        try:
            Configuration().set(*TWIN_SETTING, stored)
        except Exception:
            pass


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
    finally:
        _joystick_init_lock.release()


def _initialize_devices() -> None:
    global _joystick_devices

    syslog = logging.getLogger("system")
    syslog.info("Initializing joystick devices")
    syslog.debug(f"{dill.DILL.get_device_count():d} joysticks detected")

    # Process all connected devices in order to properly initialize the
    # device registry.
    devices = []
    for i in range(dill.DILL.get_device_count()):
        info = dill.DILL.get_device_information_by_index(i)
        try:
            from vigem.ids import is_vigem_xbox_summary
            if is_vigem_xbox_summary(info):
                syslog.debug(
                    f"Ignored ViGEm Xbox pad: name={info.name} guid={info.device_guid}"
                )
                continue
        except Exception:
            pass
        devices.append(info)
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

    # Terminate if no change occurred.
    if not device_added and not device_removed:
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
    for i in range(1, 17):
        if not vjoy.device_exists(i):
            continue
        hash_value = (vjoy.axis_count(i), vjoy.button_count(i), vjoy.hat_count(i))
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
        if not vjoy.hat_configuration_valid(i):
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
    # This is an ordered dict, that allows access via device uuid but its
    # values are enumerate in insertion order.
    _joystick_devices.clear()
    for dev in sorted_devices:
        _joystick_devices[dev.device_guid.uuid] = dev


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
        "\n\n".join(texts) + "\n\nThen restart Gremlin-Platforms.",
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
