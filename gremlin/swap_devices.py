# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""
Performs a simple swap of two devices in the profile.
"""

from __future__ import annotations

import dataclasses
import uuid

import gremlin.profile
from gremlin import error
from gremlin.modules import ids
from gremlin.modules.claim import kind_of

# What a stick has: {"button": {1, 2, ...}, "axis": {...}, "hat": {...}}.
Controls = dict[str, set[int]]

# Ids in a profile that are not a stick: their bindings can't be moved onto
# one (the keyboard's would all land on a joystick).
NOT_SWAPPABLE: frozenset[uuid.UUID] = frozenset(
    {ids.KEYBOARD, ids.LOGICAL_DEVICE, ids.OSC, ids.XBOX}
)


class SameDevice(error.GremlinError):
    """Swap refused: From and To are the same device (04 Q20)."""


@dataclasses.dataclass
class ProfileDeviceInfo:
    device_uuid: uuid.UUID
    name: str = ""
    num_bindings: int = 0


@dataclasses.dataclass
class SwapDevicesResult:
    action_swaps: int = 0
    input_swaps: int = 0
    user_script_swaps: int = 0

    def as_string(self) -> str:
        return (
            f"Swapped {self.input_swaps} input(s), {self.action_swaps} "
            f"actions, and {self.user_script_swaps} user script variables."
        )


def get_profile_devices(profile: gremlin.profile.Profile) -> list[ProfileDeviceInfo]:
    """Returns ProfileDeviceInfo for all devices present in the profile.

    Args:
        profile: The Profile to analyze.

    Returns:
        A list of ProfileDeviceInfo objects for all devices present in the
        profile.
    """
    # Count the number of non-empty bindings.
    profile_devices = {}
    for device_uuid, inputs in profile.inputs.items():
        if device_uuid in NOT_SWAPPABLE:
            continue
        if device_uuid not in profile_devices:
            profile_devices[device_uuid] = ProfileDeviceInfo(device_uuid)

        binding_count = sum(1 for e in inputs if e.action_sequences)
        profile_devices[device_uuid].num_bindings += binding_count

    # Attempt to retrieve device name from the database.
    for dev_info in profile.device_database.devices.values():
        if dev_info.device_uuid in profile_devices:
            profile_devices[dev_info.device_uuid].name = dev_info.name

    return list(profile_devices.values())


# Where a device reference is kept: a device id and an input on one object
# (a Condition's state, Merge Axis's AxisRef, a macro's joystick step...).
_DEVICE_FIELDS = ("device_guid", "device_uuid")
_SKIP_FIELDS = frozenset({"library", "joystick", "device_lookup", "input_item"})


def _refs_in(
    value: object, found: list[tuple[uuid.UUID, str, int]], seen: set[int], depth: int
) -> None:
    if depth > 6 or id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, (list, tuple, set, frozenset)):
        for entry in value:
            _refs_in(entry, found, seen, depth + 1)
        return
    if isinstance(value, dict):
        for entry in value.values():
            _refs_in(entry, found, seen, depth + 1)
        return
    module = type(value).__module__ or ""
    if not module.startswith(("gremlin", "action_plugins")):
        return
    try:
        fields = vars(value)
    except TypeError:
        return
    device = next(
        (fields[k] for k in _DEVICE_FIELDS if isinstance(fields.get(k), uuid.UUID)),
        None,
    )
    if device is not None and "input_type" in fields:
        kind = kind_of(fields.get("input_type"))
        try:
            number = int(fields.get("input_id"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            number = 0
        if kind in ("button", "axis", "hat") and number > 0:
            found.append((device, kind, number))
    for key, entry in fields.items():
        if key in _SKIP_FIELDS or key.startswith("__"):
            continue
        _refs_in(entry, found, seen, depth + 1)


def device_references(
    profile: gremlin.profile.Profile,
) -> list[tuple[str, uuid.UUID, str, int]]:
    """Every button, axis and hat an action (nested ones too) or a script
    variable refers to: (what holds it, device id, kind, number). These are
    the references swap_devices moves with the device (10 S27)."""
    found: list[tuple[str, uuid.UUID, str, int]] = []
    holders: list[tuple[str, object]] = [
        (str(getattr(a, "name", "") or type(a).__name__), a)
        for a in profile.library.actions_by_predicate(lambda _: True)
    ]
    holders += [
        (f"Script {getattr(s, 'name', '') or ''}".strip(), s)
        for s in getattr(profile.scripts, "scripts", [])
    ]
    for label, holder in holders:
        refs: list[tuple[uuid.UUID, str, int]] = []
        _refs_in(holder, refs, set(), 0)
        for ref in dict.fromkeys(refs):
            found.append((label, *ref))
    return found


def _swap_device_actions(
    profile: gremlin.profile.Profile,
    source_device_uuid: uuid.UUID,
    target_device_uuid: uuid.UUID,
) -> int:
    # Both ways, as the inputs are: through a third id, so a reference
    # already moved isn't moved back.
    middle = uuid.uuid4()
    actions = profile.library.actions_by_predicate(lambda _: True)
    count = [a.swap_uuid(source_device_uuid, middle) for a in actions].count(True)
    count += [
        a.swap_uuid(target_device_uuid, source_device_uuid) for a in actions
    ].count(True)
    for a in actions:
        a.swap_uuid(middle, target_device_uuid)
    return count


def _swap_device_user_script_vars(
    profile: gremlin.profile.Profile,
    source_device_uuid: uuid.UUID,
    target_device_uuid: uuid.UUID,
) -> int:
    middle = uuid.uuid4()
    scripts = profile.scripts.scripts
    count = [s.swap_uuid(source_device_uuid, middle) for s in scripts].count(True)
    count += [
        s.swap_uuid(target_device_uuid, source_device_uuid) for s in scripts
    ].count(True)
    for s in scripts:
        s.swap_uuid(middle, target_device_uuid)
    return count


def stays(item: object, first_has: Controls, second_has: Controls) -> bool:
    """True when an input's control is missing on one of the two sticks: its
    bindings stay where they were (10 S27). Inputs that aren't a button, axis
    or hat always move."""
    kind = kind_of(getattr(item, "input_type", None))
    if kind not in ("button", "axis", "hat"):
        return False
    try:
        number = int(getattr(item, "input_id", 0))
    except (TypeError, ValueError):
        return False
    return number not in first_has.get(kind, set()) or number not in second_has.get(
        kind, set()
    )


def _put_back(
    profile: gremlin.profile.Profile, items: list, home: uuid.UUID, away: uuid.UUID
) -> int:
    """Moves items (moved from home to away) back to home; how many have
    actions."""
    if not items:
        return 0
    return profile.move_inputs(items, away, home)


def _swap_inputs(
    profile: gremlin.profile.Profile,
    first: uuid.UUID,
    second: uuid.UUID,
    limits: tuple[Controls, Controls] | None,
) -> int:
    if limits is None:
        return profile.swap_device_inputs(first, second)
    first_stay = [i for i in profile.inputs.get(first, []) if stays(i, *limits)]
    second_stay = [i for i in profile.inputs.get(second, []) if stays(i, *limits)]
    moved = profile.swap_device_inputs(first, second)
    moved -= _put_back(profile, first_stay, first, second)
    moved -= _put_back(profile, second_stay, second, first)
    return moved


def swap_devices(
    profile: gremlin.profile.Profile,
    source_device_uuid: uuid.UUID,
    target_device_uuid: uuid.UUID,
    limits: tuple[Controls, Controls] | None = None,
) -> SwapDevicesResult:
    """Swaps two devices in the profile, from a device in the profile to a
    connected device.

    It is the caller's responsibility to ensure that the devices UUIDs are
    valid.

    Args:
        profile: The Profile to perform the swap on.
        source_device_uuid: The UUID of the source (from profile) device.
        target_device_uuid: The UUID of the target (connected) device.
        limits: The controls each stick has (source's, target's). Given, an
            input for a control one of them lacks stays where it was
            (Device Library Swap, 10 S27); None moves every input.

    Returns:
        The SwapDevicesResult object containing stats on the swaps performed.

    Raises:
        GremlinError: If either device is not a stick (keyboard, logical
            device, OSC or Xbox).
        SameDevice: If both are the same device.
    """
    for device_uuid in (source_device_uuid, target_device_uuid):
        if device_uuid in NOT_SWAPPABLE:
            raise error.GremlinError(
                f"Device {device_uuid} is not a stick and can't be swapped"
            )
    if source_device_uuid == target_device_uuid:
        raise SameDevice(f"Device {source_device_uuid} can't be swapped with itself")
    return SwapDevicesResult(
        _swap_device_actions(profile, source_device_uuid, target_device_uuid),
        _swap_inputs(profile, source_device_uuid, target_device_uuid, limits),
        _swap_device_user_script_vars(profile, source_device_uuid, target_device_uuid),
    )
