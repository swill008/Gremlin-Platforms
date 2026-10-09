# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC device page's input list (D-09-OSC-INPUT, D-09-OSC-FAULTS).

Works on the one shared address list, OscDevice().rows; rows are keyed by
their permanent uid."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

from PySide6 import QtCore

import gremlin.osc_persist  # noqa: F401  OSC labels on InputIdentifier
import gremlin.ui.type_aliases as ta
from gremlin import shared_state
from gremlin.config import Configuration
from gremlin.error import GremlinError
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime, guess_input_type
from gremlin.osc_rows import OscRow, OscRows
from gremlin.profile import InputItem
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui.device import (
    QML_IMPORT_MAJOR_VERSION,
    QML_IMPORT_NAME,
    InputIdentifier,
    _description_from_item,
    _generate_action_sequence_descriptor,
)

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

TYPE_LOCKED = (
    "Remove this input's actions first: an axis and a button use different "
    "actions."
)
MODES = ("button", "axis", "change")
SETTING_KEYS = (
    "mode", "cmd_mode", "data", "source",
    "range_min", "range_max", "trigger", "delay_ms",
)

_IMPORT_LINE = re.compile(r"^(?P<addr>/[^\s,]+)\s*(?:[,\s]\s*(?P<rest>.*))?$")

# Import suffix -> (settings, note); None note = no note.
_SUFFIXES: dict[str, tuple[dict[str, Any], str | None]] = {
    "": ({"mode": "button"}, None),
    "A": ({"mode": "axis"}, None),
    "B": ({"mode": "button"}, None),
    "BNP": ({"mode": "button", "trigger": True}, None),
    "C": ({"mode": "change"}, None),
    "E": ({"mode": "button"}, "encoder not supported yet, added as a button"),
}


def parse_import_line(line: str) -> tuple[str, dict[str, Any], str | None] | None:
    """Return (address, settings, note) for one import line, None if it
    holds no address. Separator is a space or a comma."""
    text = line.strip()
    match = _IMPORT_LINE.match(text)
    if match is None:
        return None
    suffix = (match.group("rest") or "").strip().strip(",").strip()
    known = _SUFFIXES.get(suffix.upper())
    if known is None:
        return (
            match.group("addr"),
            {"mode": "button"},
            f"unknown type '{suffix}', added as a button",
        )
    settings, note = known
    return match.group("addr"), dict(settings), note


def _opt_float(value: object, default: float) -> float:
    try:
        return float(cast("float | str", value))
    except (TypeError, ValueError):
        return default


def normalize_settings(raw: object) -> dict[str, Any]:
    """Clean a QVariantMap from QML into the row's settings fields.
    Keys left out are not returned, so an update only touches what was sent."""
    src: dict[str, Any] = dict(cast("dict[str, Any]", raw or {}))
    out: dict[str, Any] = {}
    if "mode" in src:
        mode = str(src["mode"] or "button").strip().lower()
        out["mode"] = mode if mode in MODES else "button"
    if "cmd_mode" in src:
        is_data = str(src["cmd_mode"]).lower() == "data"
        out["cmd_mode"] = "data" if is_data else "message"
    if "data" in src:
        data = src["data"]
        if data is None:
            data = []
        elif isinstance(data, str):
            data = [part.strip() for part in data.split(",") if part.strip()]
        out["data"] = [str(item) for item in data]
    if "source" in src:
        try:
            out["source"] = max(int(src["source"]), 0)
        except (TypeError, ValueError):
            out["source"] = 0
    if "range_min" in src:
        out["range_min"] = _opt_float(src["range_min"], 0.0)
    if "range_max" in src:
        out["range_max"] = _opt_float(src["range_max"], 1.0)
    if "trigger" in src:
        value = src["trigger"]
        out["trigger"] = None if value is None or value == "" else bool(value)
    if "delay_ms" in src:
        value = src["delay_ms"]
        try:
            out["delay_ms"] = (
                None if value is None or value == "" else max(int(value), 0)
            )
        except (TypeError, ValueError):
            out["delay_ms"] = None
    return out


def _type_for_mode(mode: str) -> InputType:
    return InputType.JoystickAxis if mode == "axis" else InputType.JoystickButton


def _address_error(address: str) -> str:
    if not address:
        return "Enter an address."
    if not address.startswith("/"):
        return "An OSC address starts with /."
    return ""


@dataclass
class _RowView:
    """What action_label and the roles read: type, id, label, uid."""

    uid: str
    type: InputType
    id: int
    label: str


def normalize_raw(settings: object) -> dict[str, Any]:
    """A QVariantMap (or None) as a plain dict."""
    return dict(cast("dict[str, Any]", settings or {}))


def _rows() -> OscRows:
    return OscDevice().rows


def _emit_modified() -> None:
    sig = getattr(signal, "oscDeviceModified", None)
    if sig is not None:
        sig.emit()


@ta.QmlElement
class OscDeviceManagementModel(QtCore.QAbstractListModel):
    listenChanged = QtCore.Signal()
    listenBound = QtCore.Signal(int)
    commandCaptured = QtCore.Signal(str, str)

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"actionSequenceCount"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(
            b"actionSequenceDescriptor"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(
            b"actionSequenceDisplayMode"
        ),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"description"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"uid"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"mode"),
    }

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._osc = OscDevice()
        self._mode: str = "Default"
        self._capture_only = False
        self._capture: dict[str, Any] = {}
        self._sort_alpha = False
        runtime = OscRuntime()
        runtime.learned.connect(self._on_learned)
        runtime.listenChanged.connect(self.listenChanged)
        signal.profileChanged.connect(self._profile_changed_cb)
        signal.inputItemChanged.connect(self.refreshInput)
        modified = getattr(signal, "oscDeviceModified", None)
        if modified is not None:
            modified.connect(self._full_refresh)
        reloaded = getattr(signal, "oscDeviceReloaded", None)
        if reloaded is not None:
            reloaded.connect(self._full_refresh)

    # -- rows -----------------------------------------------------------

    def _ordered(self) -> list[OscRow]:
        rows = list(_rows().rows())
        if self._sort_alpha:
            return sorted(rows, key=lambda r: (r.label.casefold(), r.input_id))
        return sorted(rows, key=lambda r: (r.input_type.name, r.input_id))

    def _row_of_uid(self, uid: str) -> int:
        for index, row in enumerate(self._ordered()):
            if row.uid == uid:
                return index
        return -1

    def _find_row(self, key: str) -> OscRow | None:
        """A row by uid, else by address when only one row has it."""
        rows = _rows()
        row = rows.by_uid(key) if key else None
        if row is not None:
            return row
        hits = [r for r in rows.rows() if r.label.casefold() == (key or "").casefold()]
        return hits[0] if len(hits) == 1 else None

    def _duplicate(
        self, address: str, settings: dict[str, Any], skip_uid: str = ""
    ) -> OscRow | None:
        """The row that would answer the same messages (OscRow.match_key)."""
        probe = OscRow(
            uid="", input_type=InputType.JoystickButton, input_id=0,
            label=address,
            cmd_mode=settings.get("cmd_mode", "message"),
            data=list(settings.get("data", [])),
            source=int(settings.get("source", 0)),
        )
        key = probe.match_key()
        for row in _rows().rows():
            if row.uid != skip_uid and row.match_key() == key:
                return row
        return None

    def _settings_of(self, row: OscRow) -> dict[str, Any]:
        return {
            "mode": row.mode,
            "cmd_mode": row.cmd_mode,
            "data": list(row.data),
            "source": row.source,
            "range_min": row.range_min,
            "range_max": row.range_max,
            "trigger": row.trigger,
            "delay_ms": row.delay_ms,
        }

    @staticmethod
    def _has_actions(row: OscRow) -> bool:
        """True when the open profile has actions on this input in any mode
        (its type can't change then: axis and button actions differ)."""
        profile = shared_state.current_profile
        if profile is None:
            return False
        return any(
            item.input_type == row.input_type
            and item.input_id == row.input_id
            and item.action_sequences
            for item in profile.inputs.get(OSC_DEVICE_UUID, [])
        )

    def _drop_profile_mappings(self, uid: str) -> None:
        """Remove the open profile's bindings on the input with this uid."""
        profile = shared_state.current_profile
        row = _rows().by_uid(uid)
        if profile is None or row is None:
            return
        items = profile.inputs.get(OSC_DEVICE_UUID, [])
        profile.drop_inputs(
            OSC_DEVICE_UUID,
            [
                item
                for item in items
                if item.input_type == row.input_type
                and item.input_id == row.input_id
            ],
        )

    def _changed(self, select_uid: str = "") -> None:
        self.beginResetModel()
        self.endResetModel()
        _emit_modified()
        if select_uid:
            self.listenBound.emit(self._row_of_uid(select_uid))

    # -- adding ---------------------------------------------------------

    def _add(self, settings: dict[str, Any]) -> tuple[OscRow | None, str]:
        """Add one row; return (row, "") or (existing row or None, error)."""
        address = str(settings.get("address") or "").strip()
        fields = normalize_settings(settings)
        fields.setdefault("mode", "button")
        error = _address_error(address)
        if error:
            return None, error
        existing = self._duplicate(address, fields)
        if existing is not None:
            return existing, f"{address} is already in the list."
        try:
            row = _rows().create(_type_for_mode(fields["mode"]), address, **fields)
        except GremlinError as err:
            return None, str(err)
        return row, ""

    @QtCore.Slot("QVariantMap", result=bool)
    def createConfiguredInput(self, settings: object) -> bool:
        """Add an input with the Add window's settings; selects it (or the
        existing one with the same address and data)."""
        row, error = self._add(normalize_raw(settings))
        if row is None:
            if error:
                signal.showError.emit("Could not add the OSC input.", error)
            return False
        if error:
            self.listenBound.emit(self._row_of_uid(row.uid))
            return False
        self._changed(row.uid)
        return True

    @QtCore.Slot(str)
    def createInput(self, type_str: str) -> None:
        self.createMappedInput(type_str, "")

    @QtCore.Slot(str, str)
    def createMappedInput(self, type_str: str, label: str) -> None:
        input_type = InputType.to_enum(type_str)
        address = (label or "").strip()
        if not address:
            used = {
                r.input_id for r in _rows().rows() if r.input_type == input_type
            }
            number = 1
            while number in used:
                number += 1
            kind = "axis" if input_type == InputType.JoystickAxis else "button"
            address = f"/osc/{kind}/{number}"
        self.createConfiguredInput({
            "address": address,
            "mode": "axis" if input_type == InputType.JoystickAxis else "button",
        })

    @QtCore.Slot(str, result=str)
    def importInputs(self, text: str) -> str:
        """Add one input per line; returns "Added N, skipped M" plus notes."""
        added: list[OscRow] = []
        skipped = 0
        notes: list[str] = []
        for raw in (text or "").splitlines():
            if not raw.strip():
                continue
            parsed = parse_import_line(raw)
            if parsed is None:
                skipped += 1
                notes.append(f"'{raw.strip()}': not an OSC address, skipped")
                continue
            address, settings, note = parsed
            row, error = self._add({"address": address, **settings})
            if row is None or error:
                skipped += 1
                continue
            added.append(row)
            if note:
                notes.append(f"'{raw.strip()}': {note}")
        if added:
            self._changed(added[-1].uid)
        return "\n".join([f"Added {len(added)}, skipped {skipped}"] + notes)

    # -- capture --------------------------------------------------------

    def capture_settings(self) -> dict[str, Any]:
        """The Add window's settings used by Listen and Bulk capture."""
        return dict(self._capture)

    @QtCore.Slot("QVariantMap")
    def setCaptureSettings(self, settings: object) -> None:
        self._capture = normalize_settings(settings)

    @QtCore.Slot()
    def listenForInput(self) -> None:
        self._capture_only = False
        OscRuntime().listen_once()

    @QtCore.Slot()
    @QtCore.Slot("QVariantMap")
    def listenForCommand(self, settings: object = None) -> None:
        if settings is not None:
            self.setCaptureSettings(settings)
        self._capture_only = True
        OscRuntime().listen_once()

    @QtCore.Slot()
    def cancelListen(self) -> None:
        self._capture_only = False
        OscRuntime().cancel_listen()

    def learned_settings(self, address: str, args: tuple) -> dict[str, Any]:
        """The capture settings applied to a captured message."""
        settings = self.capture_settings()
        if "mode" not in settings:
            settings["mode"] = (
                "axis" if guess_input_type(args) == InputType.JoystickAxis else "button"
            )
        settings["address"] = address
        settings["data"] = (
            [str(item) for item in args] if settings.get("cmd_mode") == "data" else []
        )
        return settings

    def _on_learned(self, address: str, args: object) -> None:
        payload = args if isinstance(args, tuple) else ()
        if self._capture_only:
            self._capture_only = False
            shown = ", ".join(str(item) for item in payload)
            self.commandCaptured.emit(address, shown)
            return
        if self.createConfiguredInput(self.learned_settings(address, payload)):
            signal.showNotification.emit(
                f"Bound OSC input {address}",
                "Map it to vJoy on the right, then run the profile.",
            )

    def _get_listening(self) -> bool:
        return OscRuntime().is_listening()

    # -- editing --------------------------------------------------------

    @QtCore.Slot(str, result="QVariantMap")
    def inputSettings(self, uid: str) -> dict[str, Any]:
        row = _rows().by_uid(uid)
        if row is None:
            return {}
        return {
            "uid": row.uid,
            "address": row.label,
            "locked": self._has_actions(row),
            **self._settings_of(row),
        }

    @QtCore.Slot(str, "QVariantMap", result=str)
    def updateInputSettings(self, uid: str, settings: object) -> str:
        """Apply edited settings (and address) to one input; "" or the error."""
        rows = _rows()
        row = rows.by_uid(uid)
        if row is None:
            return "That input no longer exists."
        src = normalize_raw(settings)
        fields = normalize_settings(src)
        address = str(src.get("address", row.label) or "").strip()
        error = _address_error(address)
        if error:
            return error
        new_type = _type_for_mode(fields.get("mode", row.mode))
        if new_type != row.input_type and self._has_actions(row):
            return TYPE_LOCKED
        merged = {**self._settings_of(row), **fields}
        if self._duplicate(address, merged, skip_uid=uid) is not None:
            return f"{address} is already in the list."
        try:
            if address != row.label:
                rows.set_label(uid, address)
            if fields:
                rows.update(uid, **fields)
        except GremlinError as err:
            return str(err)
        self._changed()
        return ""

    @QtCore.Slot(str, str, result=str)
    def changeName(self, key: str, new_address: str) -> str:
        """Change an input's address (key: uid, or an address held by one
        row); returns "" or the error to show."""
        row = self._find_row(key)
        if row is None:
            return "That input no longer exists."
        return self.updateInputSettings(row.uid, {"address": new_address})

    @QtCore.Slot()
    def clearAllInputs(self) -> None:
        rows = _rows()
        for row in list(rows.rows()):
            self._drop_profile_mappings(row.uid)
            rows.delete(row.uid)
        self._changed()

    @QtCore.Slot()
    def sortInputs(self) -> None:
        self._sort_alpha = True
        self.beginResetModel()
        self.endResetModel()

    @QtCore.Slot(str)
    def deleteInput(self, key: str) -> None:
        """Delete an input (key: uid, or an address held by one row) and its
        bindings in the open profile. QML asks first."""
        row = self._find_row(key)
        if row is None:
            return
        self._drop_profile_mappings(row.uid)
        _rows().delete(row.uid)
        self._changed()

    # -- model ----------------------------------------------------------

    @QtCore.Slot(str)
    def setMode(self, mode: str) -> None:
        self._mode = mode
        self.dataChanged.emit(
            self.createIndex(0, 0), self.createIndex(self.rowCount() - 1, 0)
        )

    @QtCore.Slot(int)
    def refreshInput(self, index: int) -> None:
        self.dataChanged.emit(self.createIndex(index, 0), self.createIndex(index, 0))

    def _full_refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def _get_guid(self) -> str:
        return str(self._osc.device_guid)

    def _profile_changed_cb(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(list(_rows().rows()))

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str | int:
        if role not in self.roles:
            return "Unknown"
        ordered = self._ordered()
        if not 0 <= index.row() < len(ordered):
            return ""
        row = ordered[index.row()]
        input_item: InputItem | None = None
        if shared_state.current_profile is not None:
            input_item = shared_state.current_profile.get_input_item(
                self._osc.device_guid, row.input_type, row.input_id, self._mode
            )
        match bytes(self.roles[role].data()).decode():
            case "name":
                return (
                    f"{InputType.to_string(row.input_type).capitalize()} "
                    f"{row.input_id} - {row.label}"
                )
            case "label":
                return row.label
            case "uid":
                return row.uid
            case "mode":
                return row.mode
            case "actionSequenceCount":
                return len(input_item.action_sequences) if input_item else 0
            case "actionSequenceDescriptor":
                return (
                    _generate_action_sequence_descriptor(input_item)
                    if input_item
                    else ""
                )
            case "actionSequenceDisplayMode":
                return Configuration().value(
                    "global", "general", "action-sequence-information"
                )
            case "description":
                return _description_from_item(input_item) if input_item else ""
            case _:
                return ""

    @QtCore.Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        identifier = InputIdentifier(parent=self)
        if index < 0 or index >= self.rowCount():
            return identifier
        item = self._index_to_input(index)
        identifier.device_guid = self._osc.device_guid
        identifier.input_type = item.type
        identifier.input_id = item.id
        return identifier

    def _index_to_input(self, index: int) -> _RowView:
        row = self._ordered()[index]
        return _RowView(row.uid, row.input_type, row.input_id, row.label)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    guid = QtCore.Property(str, fget=_get_guid)
    listening = QtCore.Property(bool, fget=_get_listening, notify=listenChanged)
