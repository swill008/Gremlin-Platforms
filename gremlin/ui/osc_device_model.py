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
from gremlin import osc_pattern, shared_state
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
MODES = ("button", "axis", "change", "encoder")
SETTING_KEYS = (
    "mode", "cmd_mode", "data", "source",
    "range_min", "range_max", "trigger", "delay_ms",
    "enc_format", "enc_step", "enc_output",
)
# Encoder settings (D-09-OSC-ENCODER).
ENC_FORMATS = ("auto", "direction", "signed")
ENC_OUTPUTS = ("axis", "pulse_cw", "pulse_ccw")
ENC_DEFAULTS: dict[str, Any] = {
    "enc_format": "auto", "enc_step": 0.05, "enc_output": "axis",
}

_IMPORT_LINE = re.compile(r"^(?P<addr>/[^\s,]+)\s*(?:[,\s]\s*(?P<rest>.*))?$")

# Import suffix -> (settings, note); None note = no note.
_SUFFIXES: dict[str, tuple[dict[str, Any], str | None]] = {
    "": ({"mode": "button"}, None),
    "A": ({"mode": "axis"}, None),
    "B": ({"mode": "button"}, None),
    "BNP": ({"mode": "button", "trigger": True}, None),
    "C": ({"mode": "change"}, None),
    "E": ({"mode": "encoder", "enc_format": "auto", "enc_output": "axis"}, None),
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
    if "enc_format" in src:
        fmt = str(src["enc_format"] or "").strip().lower()
        out["enc_format"] = fmt if fmt in ENC_FORMATS else "auto"
    if "enc_step" in src:
        step = _opt_float(src["enc_step"], ENC_DEFAULTS["enc_step"])
        out["enc_step"] = step if step > 0 else ENC_DEFAULTS["enc_step"]
    if "enc_output" in src:
        output = str(src["enc_output"] or "").strip().lower()
        out["enc_output"] = output if output in ENC_OUTPUTS else "axis"
    return out


def _type_for_mode(mode: str, enc_output: str = "axis") -> InputType:
    """Axis for axis mode and an encoder that drives an axis; else button."""
    if mode == "axis" or (mode == "encoder" and enc_output == "axis"):
        return InputType.JoystickAxis
    return InputType.JoystickButton


def _address_error(address: str) -> str:
    # One owner of address checks (09 S148): patterns are checked too.
    return osc_pattern.check(address)


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


# The last edit made through the Add / Import / Listen windows: the OSC
# page (gremlin.ui.osc_layout) turns it into a page Undo step (S131).
_EDIT: dict[str, Any] = {"serial": 0, "label": ""}


def note_edit(label: str) -> None:
    """Names the edit the next oscDeviceModified announces."""
    _EDIT["serial"] = int(_EDIT["serial"]) + 1
    _EDIT["label"] = str(label or "")


def last_edit() -> tuple[int, str]:
    return int(_EDIT["serial"]), str(_EDIT["label"])


# -- the edits both the management model and the OSC page make -------------


def find_duplicate(
    address: str, settings: dict[str, Any], skip_uid: str = ""
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


def settings_of(row: OscRow) -> dict[str, Any]:
    return {
        "mode": row.mode,
        "cmd_mode": row.cmd_mode,
        "data": list(row.data),
        "source": row.source,
        "range_min": row.range_min,
        "range_max": row.range_max,
        "trigger": row.trigger,
        "delay_ms": row.delay_ms,
        **{key: getattr(row, key, value) for key, value in ENC_DEFAULTS.items()},
    }


def has_actions(row: OscRow) -> bool:
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


def add_input(settings: dict[str, Any]) -> tuple[OscRow | None, str]:
    """Add one row; return (row, "") or (existing row or None, error)."""
    address = str(settings.get("address") or "").strip()
    fields = normalize_settings(settings)
    fields.setdefault("mode", "button")
    error = _address_error(address)
    if error:
        return None, error
    existing = find_duplicate(address, fields)
    if existing is not None:
        return existing, f"{address} is already in the list."
    try:
        input_type = _type_for_mode(fields["mode"], fields.get("enc_output", "axis"))
        row = _rows().create(input_type, address, **fields)
    except GremlinError as err:
        return None, str(err)
    return row, ""


def import_text(text: str) -> tuple[list[OscRow], str]:
    """Add one input per line; returns the rows added and "Added N,
    skipped M" plus notes."""
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
        row, error = add_input({"address": address, **settings})
        if row is None or error:
            skipped += 1
            continue
        added.append(row)
        if note:
            notes.append(f"'{raw.strip()}': {note}")
    return added, "\n".join([f"Added {len(added)}, skipped {skipped}"] + notes)


def update_settings(uid: str, src: dict[str, Any]) -> str:
    """Apply the given settings (and "address", when given) to one input;
    keys left out stay as they are. "" or the error."""
    rows = _rows()
    row = rows.by_uid(uid)
    if row is None:
        return "That input no longer exists."
    fields = normalize_settings(src)
    address = str(src.get("address", row.label) or "").strip()
    error = _address_error(address)
    if error:
        return error
    merged = {**settings_of(row), **fields}
    new_type = _type_for_mode(merged["mode"], merged["enc_output"])
    if new_type != row.input_type and has_actions(row):
        return TYPE_LOCKED
    if find_duplicate(address, merged, skip_uid=uid) is not None:
        return f"{address} is already in the list."
    try:
        if address != row.label:
            rows.set_label(uid, address)
        if fields:
            rows.update(uid, **fields)
    except GremlinError as err:
        return str(err)
    return ""


# Copy for Companion (D-09-OSC-COMPANION): Companion's Generic OSC module
# (2.8.2 and 3.0.0) sends from this source port; never the program's port.
COMPANION_SOURCE_PORT = 9001


def _companion_host(bound: str) -> str:
    """The address Companion sends to: the server's own address when it
    is bound to one, else this PC's first non-loopback IPv4, else
    127.0.0.1."""
    from gremlin.osc import local_ipv4_addresses

    if bound and bound not in ("0.0.0.0", "localhost"):
        return bound
    for ip in local_ipv4_addresses():
        if ip not in ("127.0.0.1", "0.0.0.0"):
            return ip
    return "127.0.0.1"


def _fmt(value: float) -> str:
    return f"{value:g}"


def seen_addresses() -> list[str]:
    """Incoming addresses in the OSC Monitor's recent traffic, newest
    first, each once (casefolded duplicates dropped)."""
    from gremlin import osc_traffic

    out: list[str] = []
    seen: set[str] = set()
    for entry in reversed(osc_traffic.recent()):
        if entry.get("direction") != "in":
            continue
        address = str(entry.get("address") or "")
        folded = address.casefold()
        if address and folded not in seen:
            seen.add(folded)
            out.append(address)
    return out


def seen_matching(address: str, seen: list[str] | None = None) -> list[str]:
    """The seen addresses an input address answers: those a pattern
    matches, or the one equal to an exact address (any case). [] for a
    blank or bad address."""
    text = str(address or "").strip()
    if not text or osc_pattern.check(text):
        return []
    seen = seen_addresses() if seen is None else seen
    if osc_pattern.is_pattern(text):
        return [a for a in seen if osc_pattern.matches(text, a)]
    return [a for a in seen if a.casefold() == text.casefold()]


PATTERN_COMPANION_NOTE = "Companion sends exact addresses; set one per button."


def companion_actions(row: OscRow, address: str | None = None) -> list[str]:
    """Generic OSC key actions that drive this input (address: the one to
    send, for a pattern input)."""
    addr = address or row.label
    if row.cmd_mode == "data":
        data = " ".join(str(item) for item in row.data) or "<values>"
        return [
            f"Press: Send message with multiple arguments {addr} {data}",
        ]
    if row.mode == "axis":
        span = f"{_fmt(row.range_min)}..{_fmt(row.range_max)}"
        return [f"Press: Send float {addr} <value {span}>"]
    if row.mode == "encoder":
        if row.enc_format == "signed":
            right, left = "1", "-1"
        else:
            right, left = "1", "0"
        return [
            f"Rotate right: Send integer {addr} {right}",
            f"Rotate left: Send integer {addr} {left}",
        ]
    if row.trigger is True:
        return [f"Press: Send message without arguments {addr}"]
    if row.mode == "change":
        return [
            f"Press: Send integer {addr} <a value>"
            " (fires each time the value differs from the last)",
        ]
    return [
        f"Press: Send integer {addr} 1",
        f"Release: Send integer {addr} 0",
    ]


def companion_text(row: OscRow) -> str:
    """Plain text to set up Companion for one input."""
    from gremlin import osc_device_file

    server = osc_device_file.read_server()
    address = None
    note: list[str] = []
    if row.is_pattern:
        # Companion sends one exact address per button (S147).
        found = seen_matching(row.label)
        address = found[0] if found else f"<an address matching {row.label}>"
        note = ["", PATTERN_COMPANION_NOTE]
    lines = [
        f"Companion: Generic OSC connection for {row.label}",
        "Target Hostname or IP: "
        f"{_companion_host(str(server.get('host') or ''))}"
        " (127.0.0.1 if Companion runs on this PC)",
        f"Target Port: {server.get('port')}",
        "Protocol: UDP",
        "Listen for Feedback: on",
        f"Source Port: {COMPANION_SOURCE_PORT}",
        "",
        "Key actions:",
        *companion_actions(row, address),
        *note,
    ]
    return "\n".join(lines)


def copy_text(text: str) -> bool:
    """Puts text on the clipboard; False with no GUI or no text."""
    from PySide6 import QtGui

    app = QtGui.QGuiApplication.instance()
    if not isinstance(app, QtGui.QGuiApplication) or not text:
        return False
    app.clipboard().setText(str(text))
    return True


@ta.QmlElement
class OscDeviceManagementModel(QtCore.QAbstractListModel):
    listenChanged = QtCore.Signal()
    listenBound = QtCore.Signal(int)
    commandCaptured = QtCore.Signal(str, str)
    # An input was added (Add, Listen, Import): the OSC page selects it.
    inputAdded = QtCore.Signal(str)
    bulkSkippedChanged = QtCore.Signal()

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

    def _changed(self, select_uid: str = "", label: str = "") -> None:
        self.beginResetModel()
        self.endResetModel()
        note_edit(label)
        _emit_modified()
        if select_uid:
            self.listenBound.emit(self._row_of_uid(select_uid))
            self.inputAdded.emit(select_uid)

    # -- adding ---------------------------------------------------------

    @QtCore.Slot("QVariantMap", result=bool)
    def createConfiguredInput(self, settings: object) -> bool:
        """Add an input with the Add window's settings; selects it (or the
        existing one with the same address and data)."""
        row, error = add_input(normalize_raw(settings))
        if row is None:
            if error:
                signal.showError.emit("Could not add the OSC input.", error)
            return False
        if error:
            self.listenBound.emit(self._row_of_uid(row.uid))
            return False
        self._changed(row.uid, f"Add {row.label}")
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
        added, result = import_text(text)
        if added:
            count = len(added)
            label = (
                f"Import {added[0].label}" if count == 1 else f"Import {count} inputs"
            )
            self._changed(added[-1].uid, label)
        return result

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
        OscRuntime().listen_once(owner=self)

    @QtCore.Slot()
    @QtCore.Slot("QVariantMap")
    def listenForCommand(self, settings: object = None) -> None:
        if settings is not None:
            self.setCaptureSettings(settings)
        self._capture_only = True
        OscRuntime().listen_once(owner=self)

    @QtCore.Slot()
    def cancelListen(self) -> None:
        if not OscRuntime().listens_for(self):
            return  # another window's Listen
        self._capture_only = False
        OscRuntime().cancel_listen(owner=self)

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
        if not OscRuntime().listens_for(self):
            return  # another model's Listen (the OSC Monitor has its own)
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

    # Bulk capture's skipped count (S151): osc_bulk sets _bulk_skipped (0
    # at each start, +1 per address an input already answers).
    @property
    def _bulk_skipped(self) -> int:
        return int(self.__dict__.get("_bulk_skipped_n", 0))

    @_bulk_skipped.setter
    def _bulk_skipped(self, value: int) -> None:
        if int(value) != self._bulk_skipped:
            self.__dict__["_bulk_skipped_n"] = int(value)
            self.bulkSkippedChanged.emit()

    def _get_bulk_skipped(self) -> int:
        return self._bulk_skipped

    @QtCore.Slot(str, result=int)
    def matchesSeen(self, address: str) -> int:
        """How many addresses seen in the OSC Monitor this address answers
        (the Add window's hint)."""
        return len(seen_matching(address))

    # -- editing --------------------------------------------------------

    @QtCore.Slot(str, result=str)
    def companionText(self, uid: str) -> str:
        """Copy for Companion: the connection settings and key actions."""
        row = _rows().by_uid(uid)
        return companion_text(row) if row is not None else ""

    @QtCore.Slot(str, result=bool)
    def copyText(self, text: str) -> bool:
        return copy_text(text)

    @QtCore.Slot(str, result="QVariantMap")
    def inputSettings(self, uid: str) -> dict[str, Any]:
        row = _rows().by_uid(uid)
        if row is None:
            return {}
        return {
            "uid": row.uid,
            "address": row.label,
            "locked": has_actions(row),
            **settings_of(row),
        }

    @QtCore.Slot(str, "QVariantMap", result=str)
    def updateInputSettings(self, uid: str, settings: object) -> str:
        """Apply edited settings (and address) to one input; "" or the error."""
        row = _rows().by_uid(uid)
        before = row.label if row is not None else ""
        error = update_settings(uid, normalize_raw(settings))
        if error:
            return error
        self._changed(label=f"Edit Settings of {before}")
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
    bulkSkipped = QtCore.Property(
        int, fget=_get_bulk_skipped, notify=bulkSkippedChanged
    )
