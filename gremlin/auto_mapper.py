# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""
Auto-mapping from input modules to output modules.
"""

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Iterable
from typing import Self

import dill
from action_plugins import (
    map_to_vjoy,
    root,
)
from gremlin import (
    device_initialization,
    plugin_manager,
    profile,
    shared_state,
    types,
)
from gremlin.modules import auto_map
from gremlin.modules.claim import claim_ids


@dataclasses.dataclass
class AutoMapperOptions:
    """Options for the auto-mapper."""

    mode: str = "Default"
    repeat_vjoy_inputs: bool = False
    overwrite_used_inputs: bool = False
    # Claim the matching outputs on the output module first. Off by default:
    # the user claims outputs; the Auto Mapper maps within what is claimed.
    claim_outputs: bool = False


def _ranges(numbers: list[int]) -> str:
    """1, 2, 3, 7 -> "1-3, 7"."""
    out: list[str] = []
    values = sorted(set(numbers))
    start = prev = None
    for value in values + [None]:
        if start is None:
            start = prev = value
            continue
        if value is not None and value == prev + 1:
            prev = value
            continue
        out.append(f"{start}" if start == prev else f"{start}-{prev}")
        start = prev = value
    return ", ".join(out)


_PLURAL = {"axis": "axes", "button": "buttons", "hat": "hats"}


class AutoMapper:
    """Generates Map to vJoy actions from an input module onto an output module."""

    def __init__(self, profile: profile.Profile) -> None:
        self._profile = profile
        self._created_mappings: list[map_to_vjoy.MapToVjoyData] = []
        self._num_retained_bindings = 0
        self._skipped: dict[tuple[str, str, str], list[int]] = {}

    @classmethod
    def from_current_profile(cls) -> Self:
        return cls(shared_state.current_profile)

    def generate_mappings(
        self,
        input_devices_guids: list[dill.GUID],
        output_vjoy_ids: list[int],
        options: AutoMapperOptions,
    ) -> str:
        """Legacy HID path. Prefer generate_module_mappings."""
        if not input_devices_guids:
            return "No input devices selected"
        if not output_vjoy_ids:
            return "No vJoy devices selected"
        input_devices = [
            dev
            for dev in device_initialization.physical_devices()
            if dev.device_guid in input_devices_guids
        ]

        self._prepare_profile(input_devices, options)
        self._num_retained_bindings = 0
        used_vjoy_inputs = set(self._get_used_vjoy_inputs(options.mode))
        vjoy_axes = self._iter_unused_vjoy_axes(output_vjoy_ids, used_vjoy_inputs)
        vjoy_buttons = self._iter_unused_vjoy_buttons(output_vjoy_ids, used_vjoy_inputs)
        vjoy_hats = self._iter_unused_vjoy_hats(output_vjoy_ids, used_vjoy_inputs)
        if options.repeat_vjoy_inputs:
            vjoy_axes = itertools.cycle(vjoy_axes)
            vjoy_buttons = itertools.cycle(vjoy_buttons)
            vjoy_hats = itertools.cycle(vjoy_hats)
        for physical_axis, vjoy_axis in zip(
            self._iter_physical_axes(input_devices, options), vjoy_axes
        ):
            self._create_new_mapping(physical_axis, vjoy_axis)
        for physical_button, vjoy_button in zip(
            self._iter_physical_buttons(input_devices, options), vjoy_buttons
        ):
            self._create_new_mapping(physical_button, vjoy_button)
        for physical_hat, vjoy_hat in zip(
            self._iter_physical_hats(input_devices, options), vjoy_hats
        ):
            self._create_new_mapping(physical_hat, vjoy_hat)
        return self._create_mappings_report()

    def generate_module_mappings(
        self,
        source_slugs: list[str],
        dest_slugs: list[str],
        options: AutoMapperOptions,
    ) -> str:
        sources = [
            row
            for row in auto_map.input_modules()
            if row["slug"] in set(source_slugs)
        ]
        dests = [
            row
            for row in auto_map.output_modules()
            if row["slug"] in set(dest_slugs)
        ]
        if not sources:
            return "No input module selected"
        if not dests:
            return "No output module selected"
        self._created_mappings = []
        self._num_retained_bindings = 0
        self._skipped = {}
        if options.repeat_vjoy_inputs:
            dest_cycle = itertools.cycle(dests)
            pairs = [(source, next(dest_cycle)) for source in sources]
        else:
            pairs = list(zip(sources, dests))
        used = set(self._get_used_vjoy_inputs(options.mode))
        for source, dest in pairs:
            guid = self._source_uuid(source)
            if guid is None:
                continue
            claim = source.get("claim") or {}
            if not (claim.get("buttons") or claim.get("axes") or claim.get("hats")):
                continue
            if options.claim_outputs:
                auto_map.merge_claim_into_output(dest, claim)
            limits = self._vjoy_limits(int(dest["vjoyId"]))
            vjoy_id = int(dest["vjoyId"])
            out_claim = dest.get("claim") or {}
            jobs = (
                (types.InputType.JoystickAxis, "axis", limits["axes"]),
                (types.InputType.JoystickButton, "button", limits["buttons"]),
                (types.InputType.JoystickHat, "hat", limits["hats"]),
            )
            for input_type, kind, on_driver in jobs:
                claimed_out = set(claim_ids(out_claim, kind))
                for hid in claim_ids(claim, kind):
                    # The output module is the limit; the driver must have it too.
                    if hid not in on_driver:
                        self._skip(dest, kind, "not on the vJoy device", hid)
                        continue
                    if hid not in claimed_out:
                        self._skip(dest, kind, "not claimed by the output module", hid)
                        continue
                    item = self._profile.get_input_item(
                        guid,
                        input_type,
                        int(hid),
                        options.mode,
                        create_if_missing=True,
                    )
                    target = types.VjoyInput(vjoy_id, input_type, int(hid))
                    if options.overwrite_used_inputs:
                        item.action_sequences.clear()
                        used.discard(target)
                    if item.action_sequences:
                        self._num_retained_bindings += 1
                        continue
                    if target in used:
                        self._num_retained_bindings += 1
                        continue
                    self._create_new_mapping(item, target)
                    used.add(target)
        if not self._created_mappings and not self._num_retained_bindings:
            return " ".join(
                [
                    "Input module has no selected buttons or axes that this "
                    "output module can take.",
                    *self._skipped_report(),
                ]
            )
        return " ".join([self._create_mappings_report(), *self._skipped_report()])

    def _skip(self, dest: dict, kind: str, reason: str, hid: int) -> None:
        key = (str(dest.get("name") or f"vJoy {dest.get('vjoyId')}"), kind, reason)
        self._skipped.setdefault(key, []).append(int(hid))

    def _skipped_report(self) -> list[str]:
        """ "Skipped vJoy 3 buttons 57-126: not claimed by the output module." """
        return [
            f"Skipped {name} {_PLURAL.get(kind, kind)} {_ranges(ids)}: {reason}."
            for (name, kind, reason), ids in sorted(self._skipped.items())
        ]

    def _source_uuid(self, source: dict):
        text = str(source.get("guid") or "").strip()
        if text:
            try:
                return dill.GUID.from_str(text).uuid
            except Exception:
                pass
        want = str(source.get("boundName") or source.get("name") or "").strip().lower()
        for device in device_initialization.physical_devices() or []:
            if str(getattr(device, "name", "") or "").strip().lower() == want:
                return device.device_guid.uuid
        return None

    def _vjoy_limits(self, vjoy_id: int) -> dict:
        empty = {"axes": set(), "buttons": set(), "hats": set()}
        for device in device_initialization.vjoy_devices() or []:
            if int(device.vjoy_id) != int(vjoy_id):
                continue
            axes = {int(axis.axis_index) for axis in device.axis_map}
            buttons = set(range(1, int(device.button_count) + 1))
            hats = set(range(1, int(device.hat_count) + 1))
            return {"axes": axes, "buttons": buttons, "hats": hats}
        return empty

    def _prepare_profile(
        self, input_devices: list[dill.DeviceSummary], options: AutoMapperOptions
    ) -> None:
        if options.overwrite_used_inputs:
            for dev in input_devices:
                self._profile.inputs.pop(dev.device_guid.uuid, None)

    def _iter_physical_axes(
        self,
        input_devices: list[dill.DeviceSummary],
        options: AutoMapperOptions,
    ) -> Iterable[profile.InputItem]:
        for dev in input_devices:
            for linear_index in range(dev.axis_count):
                axis_index = dev.axis_map[linear_index].axis_index
                input_item = self._profile.get_input_item(
                    dev.device_guid.uuid,
                    types.InputType.JoystickAxis,
                    axis_index,
                    options.mode,
                    create_if_missing=True,
                )
                if not input_item.action_sequences:
                    yield input_item
                else:
                    self._num_retained_bindings += 1

    def _iter_physical_buttons(
        self,
        input_devices: list[dill.DeviceSummary],
        options: AutoMapperOptions,
    ) -> Iterable[profile.InputItem]:
        for dev in input_devices:
            for button in range(1, dev.button_count + 1):
                input_item = self._profile.get_input_item(
                    dev.device_guid.uuid,
                    types.InputType.JoystickButton,
                    button,
                    options.mode,
                    create_if_missing=True,
                )
                if not input_item.action_sequences:
                    yield input_item
                else:
                    self._num_retained_bindings += 1

    def _iter_physical_hats(
        self,
        input_devices: list[dill.DeviceSummary],
        options: AutoMapperOptions,
    ) -> Iterable[profile.InputItem]:
        for dev in input_devices:
            for hat in range(1, dev.hat_count + 1):
                input_item = self._profile.get_input_item(
                    dev.device_guid.uuid,
                    types.InputType.JoystickHat,
                    hat,
                    options.mode,
                    create_if_missing=True,
                )
                if not input_item.action_sequences:
                    yield input_item
                else:
                    self._num_retained_bindings += 1

    def _get_used_vjoy_inputs(self, mode: str) -> list[types.VjoyInput]:
        used_vjoy_inputs = []
        connected_device_uuids = [
            dev.device_guid.uuid for dev in device_initialization.physical_devices()
        ]
        for device_uuid, input_items in self._profile.inputs.items():
            if device_uuid not in connected_device_uuids:
                continue
            for input_item in input_items:
                if input_item.mode != mode:
                    continue
                for binding in input_item.action_sequences:
                    assert isinstance(binding.root_action, root.RootData)
                    for child_action in binding.root_action.children:
                        if isinstance(child_action, map_to_vjoy.MapToVjoyData):
                            used_vjoy_inputs.append(
                                types.VjoyInput(
                                    child_action.vjoy_device_id,
                                    child_action.vjoy_input_type,
                                    child_action.vjoy_input_id,
                                )
                            )
        return used_vjoy_inputs

    def _iter_unused_vjoy_axes(
        self, vjoy_ids: list[int], used_vjoy_inputs: set[types.VjoyInput]
    ) -> Iterable[types.VjoyInput]:
        for vjoy_dev in device_initialization.vjoy_devices():
            if vjoy_dev.vjoy_id not in vjoy_ids:
                continue
            for linear_index in range(vjoy_dev.axis_count):
                axis_index = vjoy_dev.axis_map[linear_index].axis_index
                vjoy_axis = types.VjoyInput(
                    vjoy_dev.vjoy_id, types.InputType.JoystickAxis, axis_index
                )
                if vjoy_axis not in used_vjoy_inputs:
                    yield vjoy_axis

    def _iter_unused_vjoy_buttons(
        self, vjoy_ids: list[int], used_vjoy_inputs: set[types.VjoyInput]
    ) -> Iterable[types.VjoyInput]:
        for vjoy_dev in device_initialization.vjoy_devices():
            if vjoy_dev.vjoy_id not in vjoy_ids:
                continue
            for button_id in range(1, vjoy_dev.button_count + 1):
                vjoy_button = types.VjoyInput(
                    vjoy_dev.vjoy_id, types.InputType.JoystickButton, button_id
                )
                if vjoy_button not in used_vjoy_inputs:
                    yield vjoy_button

    def _iter_unused_vjoy_hats(
        self, vjoy_ids: list[int], used_vjoy_inputs: set[types.VjoyInput]
    ) -> Iterable[types.VjoyInput]:
        for vjoy_dev in device_initialization.vjoy_devices():
            if vjoy_dev.vjoy_id not in vjoy_ids:
                continue
            for hat_id in range(1, vjoy_dev.hat_count + 1):
                vjoy_hat = types.VjoyInput(
                    vjoy_dev.vjoy_id, types.InputType.JoystickHat, hat_id
                )
                if vjoy_hat not in used_vjoy_inputs:
                    yield vjoy_hat

    def _create_new_mapping(
        self, physical_input: profile.InputItem, vjoy_input: types.VjoyInput
    ) -> None:
        vjoy_action = plugin_manager.PluginManager().create_instance(
            map_to_vjoy.MapToVjoyData.name, physical_input.input_type
        )
        vjoy_action.vjoy_device_id = vjoy_input.vjoy_id
        vjoy_action.vjoy_input_id = vjoy_input.input_id
        vjoy_action.vjoy_input_type = vjoy_input.input_type
        binding = physical_input.add_item_binding()
        binding.root_action.insert_action(vjoy_action, "children")
        self._created_mappings.append(vjoy_action)

    def _create_mappings_report(self) -> str:
        return (
            f"Created {len(self._created_mappings)} mappings, "
            f"retained {self._num_retained_bindings} previous bindings."
        )
