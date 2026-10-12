# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Search window's results (to-do 9, D-01-SEARCH): one row per use of
an input, output, mode or action type in the current profile, read through
gremlin.usages, plus the window's pickers (choices). Rebuilt on profile
notices while a query is set."""

from __future__ import annotations

import enum
from collections.abc import Callable
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import shared_state
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

KINDS = ("input", "output", "mode", "action")
ROLE_NAMES = (
    "group",
    "groupTitle",
    "deviceGuid",
    "deviceName",
    "mode",
    "inputType",
    "inputId",
    "inputLabel",
    "bindingIndex",
    "text",
    "notFound",
    "path",
)
_CONTROL_TYPES = (
    InputType.JoystickAxis,
    InputType.JoystickButton,
    InputType.JoystickHat,
)
_KIND_OF_TYPE = {
    InputType.JoystickAxis: "axis",
    InputType.JoystickButton: "button",
    InputType.JoystickHat: "hat",
}


def _type_int(value: object) -> int:
    """An InputType (or its number) as its number; -1 for none."""
    if value is None:
        return -1
    if isinstance(value, InputType):
        return int(value.value)
    return int(value)  # type: ignore[arg-type]


def _plain_id(value: object) -> object:
    """An input id from QML (a key's [scan code, extended] comes as a list)."""
    if isinstance(value, list):
        return tuple(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _qml_id(value: object) -> object:
    """An input id for QML: a key's (scan code, extended) as a list."""
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, enum.Enum):
        return value.value  # an Xbox control
    return value


def _input_label(input_type: InputType, input_id: object) -> str:
    from gremlin import common

    try:
        return common.input_to_ui_string(input_type, input_id)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - an input type with no ui string
        return f"{InputType.to_string(input_type).capitalize()} {input_id}"


def _choice(label: str, value: object) -> dict:
    return {"label": label, "value": value}


def _control(input_type: InputType, input_id: object, label: str) -> dict:
    return _choice(
        label, {"inputType": _type_int(input_type), "inputId": _qml_id(input_id)}
    )


def device_choices(profile: Any) -> list[dict]:  # noqa: ANN401
    """Devices with bindings in the profile and every connected device, by
    shown name."""
    from gremlin import device_initialization
    from gremlin.ui.input_pairing import device_label

    guids: list[str] = []
    if profile is not None:
        guids.extend(str(guid) for guid, items in profile.inputs.items() if items)
    try:
        connected = device_initialization.physical_devices()
    except Exception:  # noqa: BLE001 - no device list yet
        connected = []
    guids.extend(str(dev.device_guid.uuid) for dev in connected)
    seen: dict[str, str] = {}
    for guid in guids:
        if guid not in seen:
            seen[guid] = device_label(guid)
    rows = [_choice(name, guid) for guid, name in seen.items()]
    return sorted(rows, key=lambda row: (row["label"].casefold(), row["value"]))


def input_choices(profile: Any, device_guid: str) -> list[dict]:  # noqa: ANN401
    """A device's controls: its hardware axes, buttons and hats when it is
    connected, and every input it has in the profile."""
    from gremlin import device_initialization

    found: dict[tuple[int, object], str] = {}
    try:
        connected = device_initialization.physical_devices()
    except Exception:  # noqa: BLE001 - no device list yet
        connected = []
    for dev in connected:
        if str(dev.device_guid.uuid) != str(device_guid):
            continue
        for axis in dev.axis_map:
            key = (_type_int(InputType.JoystickAxis), axis.axis_index)
            found[key] = _input_label(InputType.JoystickAxis, axis.axis_index)
        for n in range(1, dev.button_count + 1):
            found[(_type_int(InputType.JoystickButton), n)] = _input_label(
                InputType.JoystickButton, n
            )
        for n in range(1, dev.hat_count + 1):
            found[(_type_int(InputType.JoystickHat), n)] = _input_label(
                InputType.JoystickHat, n
            )
    if profile is not None:
        for guid, items in profile.inputs.items():
            if str(guid) != str(device_guid):
                continue
            for item in items:
                if item.input_type is None:
                    continue
                key = (_type_int(item.input_type), item.input_id)
                found.setdefault(key, _input_label(item.input_type, item.input_id))

    def order(entry: tuple[tuple[int, object], str]) -> tuple:
        (kind, ident), label = entry
        return (kind, ident if isinstance(ident, int) else 0, label.casefold())

    return [
        _control(InputType(kind), ident, label)
        for (kind, ident), label in sorted(found.items(), key=order)
    ]


def xbox_pad_name(pad: int) -> str:
    """Pad 1 is "Xbox 360 Controller", pad N "Xbox 360 N" (glossary)."""
    return "Xbox 360 Controller" if int(pad) == 1 else f"Xbox 360 {int(pad)}"


def _output(label: str, kind: str, output_id: int = 0, key: str = "") -> dict:
    return _choice(label, {"output": kind, "outputId": output_id, "outputKey": key})


def _osc_target_rows() -> list[dict]:
    """The OSC targets in OSC Setup, then Reply to sender (Send OSC's
    choices); value outputKey: the target id."""
    from gremlin import osc_device_file, osc_output

    try:
        targets = osc_device_file.read_targets()
    except Exception:  # noqa: BLE001 - no OSC file readable
        targets = []
    rows = []
    for target in targets:
        name = target.get("name") or f"{target.get('host')}:{target.get('port')}"
        rows.append(_output(f"OSC target {name}", "osc", key=str(target["id"])))
    rows.append(_output("OSC Reply to sender", "osc", key=osc_output.REPLY))
    return rows


def output_choices() -> list[dict]:
    """vJoy devices that have an output module, the Xbox pads that are on,
    the OSC targets, then Mouse. Value: {"output": "vjoy"|"xbox"|"osc"|
    "mouse", "outputId": n (vJoy, Xbox), "outputKey": OSC target id}."""
    from gremlin.modules import output

    rows: list[dict] = []
    try:
        vjoys = [vjoy_id for vjoy_id, _ in output.vjoy_modules()]
    except Exception:  # noqa: BLE001 - modules not read yet
        vjoys = []
    for vjoy_id in vjoys:
        rows.append(_output(f"vJoy {vjoy_id}", "vjoy", vjoy_id))
    try:
        pads = output.xbox_pads_on()
    except Exception:  # noqa: BLE001 - modules not read yet
        pads = [1]
    for pad in pads:
        rows.append(_output(xbox_pad_name(pad), "xbox", pad))
    rows.extend(_osc_target_rows())
    rows.append(_output("Mouse", "mouse"))
    return rows


def mouse_choices() -> list[dict]:
    """Map to Mouse's buttons and wheel, then Motion; inputId as the
    ("mouse", control) target names them."""
    from gremlin.types import MouseButton

    names = [(MouseButton.to_string(button), button.name) for button in MouseButton]
    names.append(("Motion", "Motion"))
    return [_choice(label, {"inputType": -1, "inputId": name}) for label, name in names]


def osc_address_choices(profile: Any, target_id: str) -> list[dict]:  # noqa: ANN401
    """The addresses the profile sends to one OSC target, sorted."""
    from gremlin import usages

    if profile is None or not target_id:
        return []
    addresses = {
        ref.target[2]
        for ref in usages.iter_usages(profile)
        if ref.target[:2] == ("osc-out", target_id) and ref.target[2]
    }
    return [
        _choice(address, {"inputType": -1, "inputId": address})
        for address in sorted(addresses, key=str.casefold)
    ]


def output_input_choices(
    kind: str,
    output_id: int,
    output_key: str = "",
    profile: Any = None,  # noqa: ANN401
) -> list[dict]:
    """The controls of one output: a vJoy's from its output module (named as
    Map to vJoy names them), an Xbox pad's in pad order, the mouse's, an OSC
    target's addresses in the profile."""
    from gremlin.modules import output

    if kind == "mouse":
        return mouse_choices()
    if kind == "osc":
        return osc_address_choices(profile, output_key)
    if kind == "xbox":
        from vigem.xbox import XboxTarget

        return [
            _choice(target.label, {"inputType": -1, "inputId": target.value})
            for target in XboxTarget
        ]
    if kind != "vjoy":
        return []
    from gremlin.modules.claim import claim_ids

    claim = output.vjoy_claim(int(output_id))
    rows: list[dict] = []
    for input_type in _CONTROL_TYPES:
        word = _KIND_OF_TYPE[input_type]
        for ident in claim_ids(claim, word):
            label = output.control_label(claim, word, ident)
            rows.append(_control(input_type, ident, label))
    return rows


def mode_choices(profile: Any) -> list[dict]:  # noqa: ANN401
    if profile is None:
        return []
    return [
        _choice(name, name)
        for name in sorted(profile.modes.mode_names(), key=str.casefold)
    ]


def action_choices() -> list[dict]:
    """Every action type by name; value is its tag."""
    from gremlin.plugin_manager import PluginManager

    rows = [
        _choice(str(plugin.name), str(tag))
        for tag, plugin in PluginManager().tag_map.items()
    ]
    return sorted(rows, key=lambda row: row["label"].casefold())


def _text(value: object) -> str:
    return str(value or "")


def _query_property(
    kind: type | str,
    field: str,
    cast: Callable[[Any], object],
    notify: QtCore.Signal,
    shown: Callable[[Any], object] | None = None,
) -> QtCore.Property:
    """A settable query property kept in self.<field>."""

    def get(self: UsagesModel) -> object:
        value = getattr(self, field)
        return shown(value) if shown else value

    def put(self: UsagesModel, value: object) -> None:
        value = cast(value)
        if getattr(self, field) != value:
            setattr(self, field, value)
            self.queryChanged.emit()

    # "QVariant" is a type name Qt takes; the stub only knows Python types.
    return QtCore.Property(
        kind,  # pyright: ignore[reportArgumentType]
        fget=get,
        fset=put,
        notify=notify,
    )


@ta.QmlElement
class UsagesModel(QtCore.QAbstractListModel):
    """Rows of the Search window, grouped by role (ROLES order)."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1 + i: QtCore.QByteArray(name.encode())
        for i, name in enumerate(ROLE_NAMES)
    }

    queryChanged = QtCore.Signal()
    resultsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._kind = ""
        self._device_guid = ""
        self._input_type = -1
        self._input_id: object = None
        self._output = ""
        self._output_id = 0
        self._output_key = ""
        self._mode = ""
        self._action_tag = ""
        self._rows: list[dict] = []
        self._groups: list[dict] = []
        self._searched = False
        # One search for a burst of notices (an edit sends several).
        self._soon = QtCore.QTimer(self)
        self._soon.setSingleShot(True)
        self._soon.setInterval(0)
        self._soon.timeout.connect(self._research)
        for notice in self._notices():
            notice.connect(self._research_soon)

    @staticmethod
    def _notices() -> tuple:
        return (
            signal.profileChanged,
            signal.bindingsChanged,
            signal.actionsChanged,
            signal.modesChanged,
        )

    def disconnect_notices(self) -> None:
        """Stop listening (tests; the window's model lives with it)."""
        for notice in self._notices():
            try:
                notice.disconnect(self._research_soon)
            except (RuntimeError, TypeError):
                pass

    # Query properties (all notify queryChanged).

    kind = _query_property(str, "_kind", _text, queryChanged)
    deviceGuid = _query_property(str, "_device_guid", _text, queryChanged)
    inputType = _query_property(int, "_input_type", int, queryChanged)
    inputId = _query_property(
        "QVariant", "_input_id", _plain_id, queryChanged, shown=_qml_id
    )
    output = _query_property(str, "_output", _text, queryChanged)
    outputId = _query_property(int, "_output_id", int, queryChanged)
    outputKey = _query_property(str, "_output_key", _text, queryChanged)
    mode = _query_property(str, "_mode", _text, queryChanged)
    actionTag = _query_property(str, "_action_tag", _text, queryChanged)

    # Results.

    @QtCore.Property(int, notify=resultsChanged)
    def count(self) -> int:
        return len(self._rows)

    @QtCore.Property(list, notify=resultsChanged)
    def groups(self) -> list:
        return list(self._groups)

    def query(self) -> Any:  # noqa: ANN401 - a gremlin.usages.Query
        from gremlin import usages

        input_type = self._input_type if self._input_type >= 0 else None
        return usages.Query(
            kind=self._kind,
            device_guid=self._device_guid,
            input_type=input_type,
            input_id=self._input_id,
            output=self._output,
            output_id=self._output_id,
            output_key=self._output_key,
            mode=self._mode,
            action_tag=self._action_tag,
        )

    def _ready(self) -> bool:
        if self._kind == "input":
            return bool(self._device_guid)  # no control: any of its controls
        if self._kind == "output":
            if self._output == "mouse":
                return True  # no control: every mouse use
            if self._output == "osc":
                return bool(self._output_key)
            return bool(self._output) and self._output_id > 0
        if self._kind == "mode":
            return bool(self._mode)
        if self._kind == "action":
            return bool(self._action_tag)
        return False

    @QtCore.Slot()
    def search(self) -> None:
        """Run the query on the current profile ("No uses found." when the
        query is not complete)."""
        from gremlin import usages

        profile = shared_state.current_profile
        found = []
        if profile is not None and self._ready():
            found = usages.find(profile, self.query())
        titles = getattr(usages, "ROLE_TITLES", {})
        rows: list[dict] = []
        groups: dict[str, dict] = {}
        for use in found:
            title = titles.get(use.role, use.role)
            rows.append(
                {
                    "group": use.role,
                    "groupTitle": title,
                    "deviceGuid": str(use.device_guid),
                    "deviceName": use.device_name,
                    "mode": use.mode,
                    "inputType": _type_int(use.input_type),
                    "inputId": _qml_id(use.input_id),
                    "inputLabel": use.input_label,
                    "bindingIndex": int(use.binding_index),
                    "text": use.text,
                    "notFound": bool(use.not_found),
                    "path": list(use.path),
                }
            )
            group = groups.setdefault(
                use.role, {"role": use.role, "title": title, "count": 0}
            )
            group["count"] += 1
        self.beginResetModel()
        self._rows = rows
        self._groups = list(groups.values())
        self._searched = True
        self.endResetModel()
        self.resultsChanged.emit()

    @QtCore.Slot()
    def _research_soon(self) -> None:
        if self._searched:
            self._soon.start()

    @QtCore.Slot()
    def _research(self) -> None:
        if self._searched:
            self.search()

    @QtCore.Slot()
    def clear(self) -> None:
        self._kind = self._device_guid = self._output = ""
        self._output_key = self._mode = self._action_tag = ""
        self._input_type, self._input_id, self._output_id = -1, None, 0
        self.queryChanged.emit()
        self.beginResetModel()
        self._rows, self._groups, self._searched = [], [], False
        self.endResetModel()
        self.resultsChanged.emit()

    def _fill(self, **fields: object) -> None:
        self._kind = self._device_guid = self._output = ""
        self._output_key = self._mode = self._action_tag = ""
        self._input_type, self._input_id, self._output_id = -1, None, 0
        for name, value in fields.items():
            setattr(self, f"_{name}", value)
        self.queryChanged.emit()
        self.search()

    @QtCore.Slot(str, int, "QVariant")
    def setFromInput(self, guid: str, input_type: int, input_id: object) -> None:
        self._fill(
            kind="input",
            device_guid=str(guid or ""),
            input_type=int(input_type),
            input_id=_plain_id(input_id),
        )

    @QtCore.Slot(list)
    def setFromListened(self, inputs: list) -> None:
        """Search's Listen: the first input pressed fills an Input search."""
        if not inputs:
            return
        event = inputs[0]
        kind = getattr(event, "event_type", None)
        self.setFromInput(
            str(getattr(event, "device_guid", "") or ""),
            int(getattr(kind, "value", kind) or 0),
            getattr(event, "identifier", None),
        )

    @QtCore.Slot(str, int, int, "QVariant")
    def setFromOutput(
        self, kind: str, output_id: int, input_type: int, input_id: object
    ) -> None:
        self._fill(
            kind="output",
            output=str(kind or ""),
            output_id=int(output_id),
            input_type=int(input_type),
            input_id=_plain_id(input_id),
        )

    @QtCore.Slot(str, str, "QVariant")
    def setFromOutputKey(self, kind: str, key: str, input_id: object) -> None:
        """An output named by a key, not a number: "osc" (key: the OSC target
        id, input_id: an address) or "mouse" (input_id: "Left" … "Motion");
        input_id None: every use of that output."""
        self._fill(
            kind="output",
            output=str(kind or ""),
            output_key=str(key or ""),
            input_id=_plain_id(input_id),
        )

    @QtCore.Slot(str)
    def setFromMode(self, name: str) -> None:
        self._fill(kind="mode", mode=str(name or ""))

    @QtCore.Slot(str)
    def setFromAction(self, tag: str) -> None:
        self._fill(kind="action", action_tag=str(tag or ""))

    @QtCore.Slot(str, result=list)
    def choices(self, kind: str) -> list:
        """Picker rows {label, value}: "device", "input" (of deviceGuid),
        "output", "outputInput" (of output/outputId), "mode", "action"."""
        profile = shared_state.current_profile
        if kind == "device":
            return device_choices(profile)
        if kind == "input":
            return input_choices(profile, self._device_guid)
        if kind == "output":
            return output_choices()
        if kind == "outputInput":
            return output_input_choices(
                self._output, self._output_id, self._output_key, profile
            )
        if kind == "mode":
            return mode_choices(profile)
        if kind == "action":
            return action_choices()
        return []

    # Model.

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:  # noqa: ANN401
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        name = self.roles.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.toStdString())

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles
