# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""
Auto-mapping from input modules to output modules.
"""

from __future__ import annotations

import dataclasses
import itertools
import uuid
from typing import Any, Self

import dill
from action_plugins import map_to_vjoy
from gremlin import (
    device_initialization,
    profile,
    shared_state,
    types,
)
from gremlin.modules import auto_map, output, store
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
    # The toolbar's mode (the one being edited); the result says when the
    # actions went into another (08 S108). Empty: not known, not said.
    toolbar_mode: str = ""


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
# After Create 1:1 Actions changed the open profile (08 S97).
NOT_SAVED_NOTE = (
    "The new actions are in the open profile and not saved yet. "
    "Use File › Save Profile to keep them, or load the profile again to undo."
)
_NOT_CLAIMED = "not claimed by the output module"
_USED = "already used by another input in this mode"


class AutoMapper:
    """Generates Map to vJoy actions from an input module onto an output module."""

    def __init__(self, profile: profile.Profile) -> None:
        self._profile = profile
        self._created_mappings: list[map_to_vjoy.MapToVjoyData] = []
        self._num_retained_bindings = 0
        # Overwrite removed actions, even where none could be made after.
        self._removed_actions = False
        self._skipped: dict[tuple[str, str, str], list[int]] = {}

    @classmethod
    def from_current_profile(cls) -> Self:
        return cls(shared_state.current_profile)

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
        self._removed_actions = False
        self._skipped = {}
        if options.repeat_vjoy_inputs:
            dest_cycle = itertools.cycle(dests)
            pairs = [(source, next(dest_cycle)) for source in sources]
        else:
            pairs = list(zip(sources, dests))
        # More input modules than outputs: the rest get nothing (said, not
        # silently dropped).
        unpaired = [
            str(source.get("name") or source.get("slug") or "")
            for source in sources[len(pairs):]
        ]
        used = set(self._get_used_vjoy_inputs(options.mode))
        for source, dest in pairs:
            guid = self._source_uuid(source)
            if guid is None:
                continue
            claim = source.get("claim") or {}
            if not any(claim_ids(claim, kind) for kind in ("axis", "button", "hat")):
                continue
            vjoy_id = int(dest["vjoyId"])
            as_input = f"vJoy {vjoy_id} is used as an input"
            limits = self._vjoy_limits(vjoy_id)
            if limits is None:
                # Read back as an input (Options): it can't be sent to, and
                # a Map to vJoy action can't be made for it (GL-313).
                for kind in ("axis", "button", "hat"):
                    for hid in claim_ids(claim, kind):
                        self._skip(dest, kind, as_input, hid)
                continue
            if options.claim_outputs:
                auto_map.merge_claim_into_output(dest, claim)
            out_claim = dest.get("claim") or {}
            jobs = (
                (types.InputType.JoystickAxis, "axis", limits["axes"]),
                (types.InputType.JoystickButton, "button", limits["buttons"]),
                (types.InputType.JoystickHat, "hat", limits["hats"]),
            )
            for input_type, kind, on_driver in jobs:
                claimed_out = set(claim_ids(out_claim, kind))
                for hid in claim_ids(claim, kind):
                    # The output module is the limit; the driver must have it.
                    if hid not in on_driver:
                        self._skip(dest, kind, "not on the vJoy device", hid)
                        continue
                    if hid not in claimed_out:
                        self._skip(dest, kind, _NOT_CLAIMED, hid)
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
                        roots = self._profile.roots_of(
                            [item] if item is not None else []
                        )
                        if item is not None and item.action_sequences:
                            self._removed_actions = True
                        item.action_sequences.clear()
                        self._profile.library.release(roots)
                        used.discard(target)
                    if item.action_sequences:
                        self._num_retained_bindings += 1
                        continue
                    # S94: not used again; a skip, not an input that kept
                    # its actions (08 S109).
                    if target in used:
                        self._skip(dest, kind, _USED, hid)
                        continue
                    if not self._create_new_mapping(item, target):
                        self._skip(dest, kind, as_input, hid)
                        continue
                    used.add(target)
        left_out = (
            [
                "No output module left for "
                + ", ".join(unpaired)
                + ": select more outputs, or turn on Combine onto selected outputs."
            ]
            if unpaired
            else []
        )
        nothing = not self._created_mappings and not self._num_retained_bindings
        if nothing and not self._skipped:
            first = [
                "Input module has no selected buttons or axes that this "
                "output module can take."
            ]
        elif nothing and {reason for _n, _k, reason in self._skipped} == {
            _NOT_CLAIMED
        }:
            # Every output skipped as the output module claims none (S109).
            names = sorted({name for name, _k, _r in self._skipped})
            first = [
                f"The output module {' and '.join(names)} claims none of these "
                "outputs: turn on Also claim the matching outputs on the output "
                "module, or claim them in its Module Setup."
            ]
        else:
            first = [
                self._create_mappings_report(options.mode),
                *self._toolbar_note(options),
            ]
        return " ".join(
            [
                *first,
                *self._skipped_report(),
                *left_out,
                *self._not_saved_note(),
            ]
        )

    def _toolbar_note(self, options: AutoMapperOptions) -> list[str]:
        """The new actions are in a mode the toolbar doesn't show (S108)."""
        toolbar = options.toolbar_mode
        if not self._created_mappings or not toolbar or toolbar == options.mode:
            return []
        return [f"The toolbar shows {toolbar}: switch to {options.mode} to see them."]

    def _not_saved_note(self) -> list[str]:
        """The profile changed in memory only (08 S97, D-08-AUTOMAP-NOTE)."""
        if not self._created_mappings and not self._removed_actions:
            return []
        return [NOT_SAVED_NOTE]

    def _skip(self, dest: dict, kind: str, reason: str, hid: int) -> None:
        key = (str(dest.get("name") or f"vJoy {dest.get('vjoyId')}"), kind, reason)
        self._skipped.setdefault(key, []).append(int(hid))

    def _skipped_report(self) -> list[str]:
        """ "Skipped vJoy 3 buttons 57-126: not claimed by the output module." """
        return [
            f"Skipped {name} {_PLURAL.get(kind, kind)} {_ranges(ids)}: {reason}."
            for (name, kind, reason), ids in sorted(self._skipped.items())
        ]

    def _source_uuid(self, source: dict) -> uuid.UUID | None:
        """The input module's device by id, never by its name: twins share a
        name (03 S90a). Its bound id; else the one plugged-in device whose
        file (chosen for its id, S6) is this module's. None when there is
        no such id, or more than one device uses the file."""
        text = str(source.get("guid") or "").strip()
        if text:
            try:
                return dill.GUID.from_str(text).uuid
            except Exception:  # noqa: BLE001 - an id that can't be read is none
                return None
        slug = str(source.get("slug") or "")
        if not slug:
            return None
        users = [
            device.device_guid.uuid
            for device in device_initialization.physical_devices() or []
            if store.slug_for(
                str(getattr(device, "name", "") or ""),
                store.guid_text(device.device_guid),
            )
            == slug
        ]
        return users[0] if len(users) == 1 else None

    def _vjoy_limits(self, vjoy_id: int) -> dict | None:
        """What the vJoy device has; empty when it isn't there. None: it is
        read back as an input, so it is no output (GL-313)."""
        outputs = {
            int(device.vjoy_id)
            for device in device_initialization.output_vjoy_devices()
        }
        listed = {
            int(device.vjoy_id) for device in device_initialization.vjoy_devices() or []
        }
        if int(vjoy_id) in listed and int(vjoy_id) not in outputs:
            return None
        # The one "driver has it" check (05 S118).
        return output.vjoy_driver_ids(int(vjoy_id))

    def _get_used_vjoy_inputs(self, mode: str) -> list[types.VjoyInput]:
        """The vJoy outputs inputs already send to in this mode: every input
        of the profile (sticks not plugged in, the Logical Device), and Map
        to vJoy actions inside others (Condition, Chain, Tempo...) too
        (08 Q7, GL-189). A binding without a root action has none (GL-190)."""
        return self._profile.vjoy_outputs_used(mode)

    def _create_new_mapping(
        self, physical_input: profile.InputItem, vjoy_input: types.VjoyInput
    ) -> bool:
        """False: no Map to vJoy action can be made here (no vJoy output)."""
        # In the library of the input it goes on (GL-102).
        vjoy_action: Any = physical_input.library.create(
            map_to_vjoy.MapToVjoyData.name,
            physical_input.input_type,
            item=physical_input,
        )
        if vjoy_action is None:
            return False
        vjoy_action.vjoy_device_id = vjoy_input.vjoy_id
        vjoy_action.vjoy_input_id = vjoy_input.input_id
        vjoy_action.vjoy_input_type = vjoy_input.input_type
        binding = physical_input.add_item_binding()
        binding.root_action.insert_action(vjoy_action, "children")
        self._created_mappings.append(vjoy_action)
        return True

    def _create_mappings_report(self, mode: str) -> str:
        """In glossary words, naming the mode (08 Q8, S103, S108)."""
        return (
            f"Made {len(self._created_mappings)} actions in {mode}; "
            f"{self._num_retained_bindings} inputs kept their actions."
        )
