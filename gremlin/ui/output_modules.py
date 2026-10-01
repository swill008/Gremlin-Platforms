# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from PySide6 import QtCore

from gremlin import common, device_initialization, event_handler
from gremlin.signal import signal
from gremlin.types import InputType
import gremlin.ui.type_aliases as ta
from gremlin.ui.hardware_profile import _maps_dir
from gremlin.modules.ids import guid_key
from gremlin.modules.claim import claim_friendly, claim_ids, kind_of, read_claim

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_AXIS_WORDS = {
    1: "X Axis",
    2: "Y Axis",
    3: "Z Axis",
    4: "X Rotation",
    5: "Y Rotation",
    6: "Z Rotation",
    7: "Slider",
    8: "Dial",
}


def _vjoy_id_from_name(name: str) -> int:
    match = re.search(r"(\d+)", str(name or ""))
    return int(match.group(1)) if match else 0


def _resolve_vjoy_id(name: str, bound_guid: str) -> int:
    want = guid_key(bound_guid)
    devices = []
    try:
        devices = list(device_initialization.output_vjoy_devices() or [])
    except Exception:
        devices = []
    if want:
        for device in devices:
            if guid_key(getattr(device, "device_guid", "")) == want:
                return int(device.vjoy_id)
    guess = _vjoy_id_from_name(name)
    ids = {int(device.vjoy_id) for device in devices}
    if guess in ids:
        return guess
    return 0


def _claimed_ints(claim: dict | None, key: str) -> list[int]:
    out: list[int] = []
    for raw in (claim or {}).get(key) or []:
        try:
            out.append(int(raw))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def _vjoy_device(vjoy_id: int) -> object | None:
    """The vJoy device Gremlin has opened for this id, or None."""
    try:
        from vjoy.vjoy import VJoyProxy

        devices = VJoyProxy.vjoy_devices or {}
    except Exception:
        return None
    for key, dev in devices.items():
        try:
            if int(key) == int(vjoy_id):
                return dev
        except (TypeError, ValueError):
            continue
    return None


def vjoy_output_state(
    vjoy_id: int, claim: dict | None
) -> dict[tuple[str, int], float]:
    """Current values of the outputs a vJoy output module claims.

    The output module is the firewall: only claimed outputs are read, and only
    ones the vJoy device actually has, so the driver is never asked for an
    output it would refuse. Empty when Gremlin has not opened that device.
    """
    dev = _vjoy_device(vjoy_id)
    if dev is None:
        return {}
    state: dict[tuple[str, int], float] = {}
    for axis_id in _claimed_ints(claim, "axes"):
        if dev.is_axis_valid(axis_id=axis_id):
            axis = dev.axis(axis_id=axis_id)
            state[("axis", axis_id)] = float(getattr(axis, "_value", 0.0))
    for button_id in _claimed_ints(claim, "buttons"):
        if dev.is_button_valid(button_id):
            pressed = bool(getattr(dev.button(button_id), "_is_pressed", False))
            state[("button", button_id)] = 1.0 if pressed else 0.0
    return state


def _dest_modules() -> list[dict]:
    folder = _maps_dir()
    if not folder.is_dir():
        return []
    rows: list[dict] = []
    seen: set[int] = set()
    for path in sorted(folder.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        direction = str(doc.get("direction") or "").strip().lower()
        slug = path.stem.lower()
        if direction not in ("dest", "target", "output") and not slug.startswith("vjoy"):
            continue
        name = str(doc.get("device") or doc.get("boundName") or path.stem).strip()
        if not name:
            continue
        vjoy_id = _resolve_vjoy_id(name, str(doc.get("boundGuidLocal") or ""))
        if not vjoy_id or vjoy_id in seen:
            continue
        seen.add(vjoy_id)
        rows.append(
            {
                "name": name,
                "vjoy_id": int(vjoy_id),
                "claim": read_claim(doc),
            }
        )
    rows.sort(key=lambda row: (row["vjoy_id"], row["name"].lower()))
    return rows


@ta.QmlElement
class OutputModuleDevices(QtCore.QObject):
    """Map to vJoy combos: output modules and the controls they pass."""

    @dataclass
    class InputOption:
        vjoy_id: int
        input_type: InputType
        input_id: int
        module_name: str = ""
        input_label: str = ""
        # A saved wire to an output its output module does not claim.
        unclaimed: bool = False

        def vjoy_str(self) -> str:
            return self.module_name or f"vJoy {self.vjoy_id}"

        def input_str(self) -> str:
            if self.input_label:
                return self.input_label
            if self.input_type == InputType.Invalid or self.input_id == 0:
                return ""
            return common.input_to_ui_string(self.input_type, self.input_id)

    choicesChanged = QtCore.Signal()
    validTypesChanged = QtCore.Signal()
    currentSelectionChanged = QtCore.Signal(int, str, int)
    currentValuesChanged = QtCore.Signal(str, str)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._valid_types: list[InputType] = []
        self._current_selection = OutputModuleDevices.InputOption(
            0, InputType.Invalid, 0
        )
        self._choices: dict[int, list[OutputModuleDevices.InputOption]] = {}
        self._modules: dict[int, dict] = {}
        # The flagged saved output, listed so the combos can show it.
        self._unclaimed: OutputModuleDevices.InputOption | None = None
        self._update_choices()
        event_handler.EventListener().device_change_event.connect(self._update_choices)
        signal.profileChanged.connect(self._update_choices)
        signal.configChanged.connect(self._update_choices)

    def _input_label(self, claim: dict, input_type: InputType, input_id: int) -> str:
        custom = claim_friendly(claim, kind_of(input_type), input_id)
        if custom:
            return custom
        if input_type == InputType.JoystickAxis:
            return _AXIS_WORDS.get(int(input_id), f"Axis {int(input_id)}")
        if input_type == InputType.JoystickHat:
            return f"Hat {int(input_id)}"
        return f"Button {int(input_id)}"

    def _update_choices(self) -> None:
        self._modules = {}
        self._choices = {}
        for module in _dest_modules():
            vjoy_id = int(module["vjoy_id"])
            claim = module["claim"]
            self._modules[vjoy_id] = module
            options: list[OutputModuleDevices.InputOption] = []
            for input_type in self._valid_types:
                for input_id in claim_ids(claim, kind_of(input_type)):
                    options.append(
                        OutputModuleDevices.InputOption(
                            vjoy_id,
                            input_type,
                            input_id,
                            module["name"],
                            self._input_label(claim, input_type, input_id),
                        )
                    )
            self._choices[vjoy_id] = options
        if self._current_selection.input_type != InputType.Invalid:
            self._transfer_current_selection_if_possible(self._current_selection)
        else:
            self.choicesChanged.emit()

    @QtCore.Slot(str, str)
    def setState(self, vjoy_name: str, input_name: str) -> None:
        new_selection = self._parse_state_string(vjoy_name, input_name)
        if (
            new_selection.input_type == InputType.Invalid
            or new_selection.input_id == 0
            or new_selection.vjoy_id == 0
        ):
            return
        self._transfer_current_selection_if_possible(new_selection)

    @QtCore.Slot(int, str, int)
    def setInitialState(self, vjoy_id: int, input_type_str: str, input_id: int) -> None:
        self._unclaimed = None
        self._transfer_current_selection_if_possible(
            OutputModuleDevices.InputOption(
                int(vjoy_id),
                InputType.to_enum(input_type_str),
                int(input_id),
            ),
            False,
        )

    def _parse_state_string(
        self, vjoy_name: str, input_name: str
    ) -> OutputModuleDevices.InputOption:
        flagged = self._unclaimed
        if (
            flagged is not None
            and flagged.vjoy_str() == vjoy_name
            and flagged.input_str() == input_name
        ):
            return flagged
        for vjoy_id, options in self._choices.items():
            if not options:
                module = self._modules.get(vjoy_id) or {}
                if str(module.get("name") or "") == vjoy_name:
                    return OutputModuleDevices.InputOption(
                        vjoy_id, InputType.Invalid, 0, str(module.get("name") or "")
                    )
            for option in options:
                if option.vjoy_str() == vjoy_name and option.input_str() == input_name:
                    return option
        return OutputModuleDevices.InputOption(0, InputType.Invalid, 0)

    def _transfer_current_selection_if_possible(
        self, selection: OutputModuleDevices.InputOption, allow_invalid: bool = True
    ) -> None:
        new_selection = OutputModuleDevices.InputOption(0, InputType.Invalid, 0)
        options = self._choices.get(selection.vjoy_id) or []
        match = next(
            (
                option
                for option in options
                if option.input_type == selection.input_type
                and option.input_id == selection.input_id
            ),
            None,
        )
        if match is not None:
            new_selection = match
        elif self._keeps_unclaimed(selection):
            # Never re-point a saved wire: keep it and flag it.
            new_selection = self._flag_unclaimed(selection)
        elif options:
            new_selection = options[0]
        elif allow_invalid:
            module = self._modules.get(selection.vjoy_id) or {}
            new_selection = OutputModuleDevices.InputOption(
                int(selection.vjoy_id or 0),
                InputType.Invalid,
                0,
                str(module.get("name") or ""),
            )
        else:
            for options in self._choices.values():
                if options:
                    new_selection = options[0]
                    break
        self._current_selection = new_selection
        self.choicesChanged.emit()
        self.currentValuesChanged.emit(
            new_selection.vjoy_str(), new_selection.input_str()
        )
        if new_selection.unclaimed:
            # Unchanged wire: nothing to write back.
            return
        if new_selection.vjoy_id and new_selection.input_id:
            self.currentSelectionChanged.emit(
                new_selection.vjoy_id,
                InputType.to_string(new_selection.input_type),
                new_selection.input_id,
            )

    def _keeps_unclaimed(self, selection: OutputModuleDevices.InputOption) -> bool:
        """A complete saved output of a type this action uses."""
        return bool(
            selection.vjoy_id
            and selection.input_id
            and selection.input_type in self._valid_types
        )

    def _flag_unclaimed(
        self, selection: OutputModuleDevices.InputOption
    ) -> OutputModuleDevices.InputOption:
        module = self._modules.get(selection.vjoy_id)
        if module is None:
            name = f"vJoy {selection.vjoy_id} (no output module)"
            label = common.input_to_ui_string(selection.input_type, selection.input_id)
        else:
            name = str(module.get("name") or f"vJoy {selection.vjoy_id}")
            claim = module.get("claim") or {}
            label = self._input_label(claim, selection.input_type, selection.input_id)
        flagged = OutputModuleDevices.InputOption(
            selection.vjoy_id,
            selection.input_type,
            selection.input_id,
            name,
            f"{label} (not claimed)",
            True,
        )
        self._unclaimed = flagged
        return flagged

    def _get_vjoy_devices(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for vjoy_id, options in self._choices.items():
            name = options[0].vjoy_str() if options else str(
                (self._modules.get(vjoy_id) or {}).get("name") or f"vJoy {vjoy_id}"
            )
            if name not in seen:
                seen.add(name)
                names.append(name)
        flagged = self._unclaimed
        if flagged is not None and flagged.vjoy_str() not in seen:
            names.append(flagged.vjoy_str())
        return names

    def _get_input_choices(self) -> list[str]:
        options = self._choices.get(self._current_selection.vjoy_id) or []
        labels = [option.input_str() for option in options if option.input_str()]
        flagged = self._unclaimed
        if (
            flagged is not None
            and flagged.vjoy_id == self._current_selection.vjoy_id
            and flagged.input_type in self._valid_types
        ):
            labels.append(flagged.input_str())
        return labels

    def _get_current_unclaimed(self) -> bool:
        return bool(self._current_selection.unclaimed)

    def _get_valid_types(self) -> list[str]:
        return [InputType.to_string(item) for item in self._valid_types]

    def _set_valid_types(self, valid_types: list[str]) -> None:
        types = [InputType.to_enum(item) for item in valid_types]
        if types == self._valid_types:
            return
        self._valid_types = types
        self.validTypesChanged.emit()
        self._update_choices()

    def _get_has_valid(self) -> bool:
        return bool(self._modules)

    vjoyDevices = QtCore.Property(
        "QVariantList", fget=_get_vjoy_devices, notify=choicesChanged
    )
    inputChoices = QtCore.Property(
        "QVariantList", fget=_get_input_choices, notify=choicesChanged
    )
    validTypes = QtCore.Property(
        "QVariantList",
        fget=_get_valid_types,
        fset=_set_valid_types,
        notify=validTypesChanged,
    )
    hasValidVJoyDevices = QtCore.Property(bool, fget=_get_has_valid, notify=choicesChanged)
    currentUnclaimed = QtCore.Property(
        bool, fget=_get_current_unclaimed, notify=choicesChanged
    )
