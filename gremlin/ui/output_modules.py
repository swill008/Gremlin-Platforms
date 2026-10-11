# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import common, event_handler
from gremlin.modules import output
from gremlin.modules.claim import claim_ids, kind_of
from gremlin.signal import signal
from gremlin.types import InputType

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _dest_modules() -> list[dict]:
    """vJoy output modules, one per vJoy device, by vJoy number; each claim
    cut to the ids the vJoy device has (05 S118, the Auto Mapper check). A
    saved wire to one it lacks is kept and flagged, not re-pointed. A vJoy
    the driver doesn't list (turned off in the vJoy configuration tool) is
    "available": False and keeps its output module's own claim; anything
    picked on it can't be sent (D-05-CANT-SEND)."""
    modules = []
    for vjoy_id, module in output.vjoy_modules():
        available = any(output.vjoy_driver_ids(vjoy_id).values())
        modules.append(
            {
                "name": module.name,
                "vjoy_id": vjoy_id,
                "claim": output.driver_claim(vjoy_id, module.claim)
                if available
                else dict(module.claim or {}),
                "available": available,
            }
        )
    return modules


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
        # A binding that can't be sent (D-05-CANT-SEND): shown "⚠ <Control>"
        # in red; `reason` is its tooltip.
        unclaimed: bool = False
        reason: str = ""

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
        # The flagged binding that can't be sent, listed so the combos show it.
        self._unclaimed: OutputModuleDevices.InputOption | None = None
        self._update_choices()
        event_handler.EventListener().device_change_event.connect(self._update_choices)
        signal.profileChanged.connect(self._update_choices)
        signal.configChanged.connect(self._update_choices)

    def _input_label(self, claim: dict, input_type: InputType, input_id: int) -> str:
        return output.control_label(claim, kind_of(input_type), input_id)

    def _reason(self, selection: OutputModuleDevices.InputOption) -> str:
        """Why this binding can't be sent; "" when it can (D-05-CANT-SEND).
        Judged on this picker's own list, so the flag and the list agree."""
        module = self._modules.get(selection.vjoy_id)
        available = bool(module and module.get("available", True))
        claim = (module or {}).get("claim") or {}
        kind = kind_of(selection.input_type)
        ids = claim_ids(claim, kind) if available else []
        off = module is not None and not available
        text = output.cant_send_words(
            selection.vjoy_id, kind, selection.input_id, claim, ids, off
        )
        return text or ""

    def _update_choices(self) -> None:
        self._modules = {}
        self._choices = {}
        for module in _dest_modules():
            vjoy_id = int(module["vjoy_id"])
            claim = module["claim"]
            self._modules[vjoy_id] = module
            options: list[OutputModuleDevices.InputOption] = []
            # A vJoy that is off: its claimed controls; picking one saves a
            # binding flagged as can't be sent, blocked at Run (06 S47).
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
        if new_selection.vjoy_id == 0:
            return
        if not new_selection.unclaimed:
            # The user moved off the flagged saved wire (D-05-VJOY-SWITCH).
            self._unclaimed = None
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
        for options in self._choices.values():
            for option in options:
                if option.vjoy_str() == vjoy_name and option.input_str() == input_name:
                    return option
        # Another vJoy picked while the input box still shows the old one's
        # output: the same control there (its label can differ), else that
        # vJoy, same type, id 0 so the transfer picks for it (S136).
        current = self._current_selection
        for vjoy_id, module in self._modules.items():
            name = str(module.get("name") or "")
            if (name or f"vJoy {vjoy_id}") == vjoy_name:
                same = next(
                    (
                        option
                        for option in self._choices.get(vjoy_id) or []
                        if option.input_type == current.input_type
                        and option.input_id == current.input_id
                    ),
                    None,
                )
                if same is not None:
                    return same
                return OutputModuleDevices.InputOption(
                    vjoy_id, current.input_type, 0, name
                )
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
        previous = self._current_selection
        if match is not None:
            new_selection = match
        elif self._keeps_unclaimed(selection):
            # Never re-point a saved wire: keep it and flag it.
            new_selection = self._flag_unclaimed(selection)
        elif options:
            # Same control type first (D-05-VJOY-SWITCH).
            new_selection = next(
                (o for o in options if o.input_type == selection.input_type),
                options[0],
            )
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
        if (
            not new_selection.unclaimed
            and self._keeps_unclaimed(new_selection)
            and self._reason(new_selection)
        ):
            # Listed, but its vJoy is turned off.
            new_selection = self._flag_unclaimed(new_selection)
        self._unclaimed = new_selection if new_selection.unclaimed else None
        self._current_selection = new_selection
        self.choicesChanged.emit()
        self.currentValuesChanged.emit(
            new_selection.vjoy_str(), new_selection.input_str()
        )
        if new_selection.unclaimed and (
            not allow_invalid or self._same_target(previous, new_selection)
        ):
            # The saved binding as it is: nothing to write back.
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

    @staticmethod
    def _same_target(
        a: OutputModuleDevices.InputOption, b: OutputModuleDevices.InputOption
    ) -> bool:
        return (a.vjoy_id, a.input_type, a.input_id) == (
            b.vjoy_id,
            b.input_type,
            b.input_id,
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
            f"⚠ {label}",
            True,
            self._reason(selection),
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
        flagged = self._unclaimed
        if not (
            flagged is not None
            and flagged.vjoy_id == self._current_selection.vjoy_id
            and flagged.input_type in self._valid_types
        ):
            return [option.input_str() for option in options if option.input_str()]
        # The flagged binding once, in place of its plain entry.
        labels = [
            option.input_str()
            for option in options
            if option.input_str() and not self._same_target(option, flagged)
        ]
        labels.append(flagged.input_str())
        return labels

    def _get_current_unclaimed(self) -> bool:
        return bool(self._current_selection.unclaimed)

    def _get_current_reason(self) -> str:
        current = self._current_selection
        return current.reason if current.unclaimed else ""

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
    hasValidVJoyDevices = QtCore.Property(
        bool, fget=_get_has_valid, notify=choicesChanged
    )
    currentUnclaimed = QtCore.Property(
        bool, fget=_get_current_unclaimed, notify=choicesChanged
    )
    # The tooltip of a binding that can't be sent ("" when it can).
    currentReason = QtCore.Property(
        str, fget=_get_current_reason, notify=choicesChanged
    )
