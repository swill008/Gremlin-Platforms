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


def swap_devices(
    profile: gremlin.profile.Profile,
    source_device_uuid: uuid.UUID,
    target_device_uuid: uuid.UUID,
) -> SwapDevicesResult:
    """Swaps two devices in the profile, from a device in the profile to a
    connected device.

    It is the caller's responsibility to ensure that the devices UUIDs are
    valid.

    Args:
        profile: The Profile to perform the swap on.
        source_device_uuid: The UUID of the source (from profile) device.
        target_device_uuid: The UUID of the target (connected) device.

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
        profile.swap_device_inputs(source_device_uuid, target_device_uuid),
        _swap_device_user_script_vars(profile, source_device_uuid, target_device_uuid),
    )
