# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Feedback section of OSC's Module Setup (D-09-OSC-FEEDBACK): the
feedback switches in "server" and the feedback rows, both kept in OSC's own
file. Each change is checked, then written at once."""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import osc_device_file

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

syslog = logging.getLogger("system")

WHO = "OSC Module Setup"

# Server keys this section edits.
_FLAGS = (
    "feedback_enabled",
    "resend_run",
    "resend_mode",
    "resend_profile",
    "sync_enabled",
)

KIND_LABELS = {
    "mode": "Current mode",
    "vjoy_button": "vJoy button",
    "vjoy_axis": "vJoy axis",
    "logical": "Logical Device control",
    "osc_input": "OSC input",
    "action_state": "Action state",
    "paused": "Running / Paused",
}

TYPE_LABELS = {
    "auto": "Auto",
    "int": "Int",
    "float": "Float",
    "bool": "Bool",
    "text": "Text",
}

REPLY_LABEL = "Reply to sender"


def _number(text: object) -> float | None:
    try:
        return float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _whole(text: object) -> int | None:
    number = _number(text)
    if number is None or number != int(number):
        return None
    return int(number)


ACTION_MISSING = "This action is not in the current profile"


def check_address(text: object) -> str:
    """Why text can't be an outgoing OSC address ("" when it can)."""
    address = str(text or "").strip()
    if not address.startswith("/") or " " in address:
        return "An OSC address starts with / and has no spaces, e.g. /fire."
    from gremlin import osc_pattern

    # Outgoing addresses are exact (S149).
    return osc_pattern.check(address, allow_pattern=False)


def action_inputs(profile: object) -> dict[str, str]:
    """Action id -> uid of the OSC input it sits on (any mode, nested
    actions too); the first input found wins."""
    from gremlin.osc import OSC_DEVICE_UUID, OscDevice

    out: dict[str, str] = {}
    inputs = getattr(profile, "inputs", None) or {}
    rows = OscDevice().rows
    for item in inputs.get(OSC_DEVICE_UUID, []):
        uid = rows.uid_of(item.input_type, item.input_id)
        if not uid:
            continue
        stack = [b.root_action for b in item.action_sequences if b.root_action]
        seen: set[int] = set()
        while stack:
            action = stack.pop()
            if id(action) in seen:
                continue
            seen.add(id(action))
            out.setdefault(str(action.id), str(uid))
            try:
                stack.extend(action.get_actions()[0])
            except Exception:
                pass
    return out


def placement(row: dict, actions: dict[str, str]) -> str | None:
    """The OSC input uid a row shows under (S153); None: the group
    "Feedback not tied to an input"."""
    if row.get("input"):
        return str(row["input"])
    source = row.get("source") or {}
    kind = source.get("kind")
    if kind == "osc_input" and source.get("input") not in (None, ""):
        return str(source["input"])
    if kind == "action_state" and source.get("action"):
        return actions.get(str(source["action"]))
    return None


def _current_profile() -> Any:  # noqa: ANN401
    from gremlin import shared_state

    return shared_state.current_profile


def _entry(row: dict) -> dict:
    """A row flattened for QML (numbers as text; off/on "" when not set)."""
    source = row["source"]
    return {
        "id": row["id"],
        "enabled": row["enabled"],
        "kind": source["kind"],
        "device": "" if source["device"] is None else source["device"],
        "input": "" if source["input"] is None else source["input"],
        "action": source.get("action") or "",
        "target": row["target"],
        "address": row["address"],
        "min": _show(row["min"]),
        "max": _show(row["max"]),
        "type": row["type"],
        "offValue": _show_off_on(row.get("off_value")),
        "onValue": _show_off_on(row.get("on_value")),
        "template": row.get("template") or "",
        "showUnder": row.get("input") or "",
    }


def rows_for_page(rows: list[dict] | None = None, profile: object = None) -> list[dict]:
    """Each feedback row for the OSC page with its placement (an OSC input
    uid, or None for "Feedback not tied to an input")."""
    rows = osc_device_file.read_feedback() if rows is None else rows
    profile = _current_profile() if profile is None else profile
    actions = action_inputs(profile) if profile is not None else {}
    out = []
    for row in rows:
        entry = _entry(row)
        entry["placement"] = placement(row, actions)
        out.append(entry)
    return out


def new_row() -> dict:
    """A new feedback row: current mode name, reply to sender."""
    return osc_device_file.clean_feedback(
        [
            {
                "enabled": True,
                "source": {"kind": "mode", "device": None, "input": None},
                "target": osc_device_file.REPLY,
                "address": "/gremlin/mode",
                "min": 0.0,
                "max": 1.0,
                "type": "auto",
            }
        ]
    )[0]


# Companion templates (D-09-OSC-COMPANION): defaults the Add Row dialogs show.
COMPANION_VARIABLE = "gremlin_mode"
COLOUR_OFF = "#333333"
COLOUR_ON = "#2a7a46"
VARIABLE_NOTE = "Create the custom variable in Companion first."
KEY_NOTE = "Turn on Companion's OSC Listener (Settings › OSC) first."


def _off_on(value: object) -> str | int | float | None:
    """What an Off/On box holds: blank is not set, a number is a number,
    anything else is text."""
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    number = _number(text)
    if number is not None and not text.startswith("#"):
        return int(number) if number.is_integer() else number
    return text


def template_row(kind: str, params: dict, target_id: str) -> dict | str:
    """The row a Companion template builds, or why it can't (text).

    kind: companion_variable (params name), companion_text and
    companion_colour (params page, row, column; colour also off, on).
    """
    row = new_row()
    row["target"] = target_id
    row["template"] = kind
    if kind == "companion_variable":
        name = str(params.get("name") or "").strip()
        if not name or any(c in name for c in " /$():"):
            return "A variable name has no spaces, e.g. gremlin_mode."
        row["address"] = f"/custom-variable/{name}/value"
        row["type"] = "text"
        return row
    page = _whole(params.get("page", 1))
    key_row = _whole(params.get("row", 0))
    column = _whole(params.get("column", 0))
    if page is None or page < 1:
        return "Page is a whole number, 1 or more."
    if key_row is None or key_row < 0 or column is None or column < 0:
        return "Row and column are whole numbers, 0 or more."
    where = f"/location/{page}/{key_row}/{column}/style"
    if kind == "companion_text":
        row["address"] = f"{where}/text"
        row["type"] = "text"
        return row
    if kind == "companion_colour":
        colours = []
        for key, default in (("off", COLOUR_OFF), ("on", COLOUR_ON)):
            text = str(params.get(key) or default).strip()
            if not text.startswith("#"):
                text = "#" + text
            digits = text[1:]
            hex_digits = "0123456789abcdefABCDEF"
            if len(digits) != 6 or any(c not in hex_digits for c in digits):
                return "A color is #rrggbb, e.g. #2a7a46."
            colours.append(text.lower())
        row["address"] = f"{where}/bgcolor"
        row["type"] = "auto"
        row["source"] = {"kind": "vjoy_button", "device": _vjoy_ids()[0], "input": 1}
        row["off_value"], row["on_value"] = colours
        return row
    return "Unknown template."


@ta.QmlElement
class OscFeedbackModel(QtCore.QObject):
    """Feedback switches and rows for OSC's Module Setup."""

    changed = QtCore.Signal()
    messageChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._server: dict[str, Any] = {}
        self._rows: list[dict] = []
        self._targets: list[dict] = []
        self._message = ""
        self.reload()
        from gremlin.signal import signal

        for name in (
            "oscFeedbackChanged",
            "oscServerSettingsChanged",
            "oscDeviceReloaded",
        ):
            sig = getattr(signal, name, None)
            if sig is not None:
                sig.connect(self.reload)

    @QtCore.Slot()
    def reload(self) -> None:
        self._server = osc_device_file.read_server()
        self._rows = osc_device_file.read_feedback()
        self._targets = osc_device_file.read_targets()
        self.changed.emit()

    def _say(self, text: str) -> None:
        if text != self._message:
            self._message = text
            self.messageChanged.emit()

    # -- switches ------------------------------------------------------------

    @QtCore.Slot(str, "QVariant", result=bool)
    def setSetting(self, key: str, value: object) -> bool:
        """Checks and saves one feedback setting; False (with message)
        when refused."""
        if key in _FLAGS:
            value = bool(value)
        elif key == "sync_address":
            why = check_address(value)
            if why:
                self._say(why)
                return False
            value = str(value).strip()
        elif key == "feedback_rate":
            value = _whole(value)
            if value is None or value < 1:
                self._say("Messages per second is a whole number, 1 or more.")
                return False
        else:
            return False
        self._say("")
        if self._server.get(key) == value:
            return True
        settings = dict(self._server)
        settings[key] = value
        try:
            osc_device_file.write_server(settings, WHO)
        except OSError as exc:
            syslog.error("OSC: feedback settings not written: %s", exc)
            self._say("Not written. The OSC file could not be saved.")
            return False
        self.reload()
        return self._server.get(key) == value

    def _get(self, key: str) -> object:
        return self._server.get(key, osc_device_file.SERVER_DEFAULTS[key])

    @QtCore.Property(str, constant=True)
    def defaultOffColor(self) -> str:
        """The Key color template's default off color (data, not a theme color)."""
        return COLOUR_OFF

    @QtCore.Property(str, constant=True)
    def defaultOnColor(self) -> str:
        """The Key color template's default on color."""
        return COLOUR_ON

    @QtCore.Property(bool, notify=changed)
    def feedbackEnabled(self) -> bool:
        return bool(self._get("feedback_enabled"))

    @QtCore.Property(bool, notify=changed)
    def resendRun(self) -> bool:
        return bool(self._get("resend_run"))

    @QtCore.Property(bool, notify=changed)
    def resendMode(self) -> bool:
        return bool(self._get("resend_mode"))

    @QtCore.Property(bool, notify=changed)
    def resendProfile(self) -> bool:
        return bool(self._get("resend_profile"))

    @QtCore.Property(bool, notify=changed)
    def syncEnabled(self) -> bool:
        return bool(self._get("sync_enabled"))

    @QtCore.Property(str, notify=changed)
    def syncAddress(self) -> str:
        return str(self._get("sync_address"))

    @QtCore.Property(str, notify=changed)
    def feedbackRate(self) -> str:
        return str(self._get("feedback_rate"))

    @QtCore.Property(str, notify=messageChanged)
    def message(self) -> str:
        return self._message

    # -- choices -------------------------------------------------------------

    @QtCore.Property(list, constant=True)
    def kindChoices(self) -> list:
        return [{"value": k, "text": t} for k, t in KIND_LABELS.items()]

    @QtCore.Property(list, constant=True)
    def typeChoices(self) -> list:
        return [{"value": k, "text": t} for k, t in TYPE_LABELS.items()]

    @QtCore.Property(list, notify=changed)
    def targetChoices(self) -> list:
        out = [
            {"value": t["id"], "text": t["name"] or f"{t['host']}:{t['port']}"}
            for t in self._targets
        ]
        out.append({"value": osc_device_file.REPLY, "text": REPLY_LABEL})
        return out

    @QtCore.Property(list, notify=changed)
    def vjoyChoices(self) -> list:
        return [{"value": i, "text": f"vJoy {i}"} for i in _vjoy_ids()]

    @QtCore.Property(list, notify=changed)
    def logicalChoices(self) -> list:
        from gremlin import logical_device_file

        out = []
        for control in logical_device_file.read_layout()["controls"]:
            uid = str(control.get("uid") or "")
            if not uid:
                continue
            name = str(control.get("user-label") or control.get("label") or uid)
            out.append({"value": uid, "text": name})
        return out

    @QtCore.Property(list, notify=changed)
    def oscChoices(self) -> list:
        out = []
        for row in osc_device_file.read_inputs():
            uid = str(row.get("uid") or "")
            if uid:
                out.append({"value": uid, "text": str(row.get("label") or uid)})
        return out

    @QtCore.Property(list, notify=changed)
    def actionChoices(self) -> list:
        """Smart Toggles and Tempos of the current profile, for the
        action_state source picker: [{value: action id, text: label}]."""
        from gremlin import action_state

        profile = _current_profile()
        if profile is None:
            return []
        return [
            {"value": str(aid), "text": label}
            for aid, label in action_state.stateful_actions(profile)
        ]

    # -- rows ----------------------------------------------------------------

    @QtCore.Property(list, notify=changed)
    def rows(self) -> list:
        """Each row flattened for QML: id, enabled, kind, device, input,
        action, target, address, min, max, type, offValue, onValue,
        template, showUnder (numbers as text; off/on "" when not set)."""
        return [_entry(row) for row in self._rows]

    @QtCore.Property(list, notify=changed)
    def rowsForPage(self) -> list:
        """rows plus placement: the OSC input uid ("" for the group
        "Feedback not tied to an input")."""
        out = rows_for_page(self._rows)
        for entry in out:
            entry["placement"] = entry["placement"] or ""
        return out

    def _index_of(self, row_id: str) -> int:
        for index, row in enumerate(self._rows):
            if row["id"] == str(row_id):
                return index
        return -1

    @QtCore.Slot(str, result="QVariantMap")
    def rowById(self, row_id: str) -> dict:
        for entry in rows_for_page(self._rows):
            if entry["id"] == str(row_id):
                entry["placement"] = entry["placement"] or ""
                return entry
        return {}

    @QtCore.Slot(str, bool, result=bool)
    def setRowEnabled(self, row_id: str, on: bool) -> bool:
        return self.setRowValue(self._index_of(row_id), "enabled", bool(on))

    @QtCore.Slot(str, str, "QVariant", result=bool)
    def setRowValueById(self, row_id: str, key: str, value: object) -> bool:
        return self.setRowValue(self._index_of(row_id), key, value)

    @QtCore.Slot(str, result=bool)
    def removeRowById(self, row_id: str) -> bool:
        return self.removeRow(self._index_of(row_id))

    @QtCore.Slot(str, result=str)
    def duplicateRow(self, row_id: str) -> str:
        """Copies a row (new id) right after it; the new id, "" when the
        row isn't there."""
        index = self._index_of(row_id)
        if index < 0:
            return ""
        copy = dict(self._rows[index])
        copy["source"] = dict(copy["source"])
        copy["id"] = osc_device_file.new_id()
        rows = [dict(r) for r in self._rows]
        rows.insert(index + 1, copy)
        return copy["id"] if self._write(rows) else ""

    @QtCore.Slot("QVariantMap", result=str)
    def addRowFor(self, fields: dict) -> str:
        """A new row from new_row() with the given stored-row keys; the
        new id, "" (with message) when refused."""
        row = new_row()
        given = dict(fields or {})
        if "source" in given:
            given["source"] = dict(given["source"] or {})
        row.update(given)
        row["id"] = osc_device_file.new_id()
        why = check_address(row.get("address"))
        if why:
            self._say(why)
            return ""
        cleaned = osc_device_file.clean_feedback([row])[0]
        rows = [dict(r) for r in self._rows] + [cleaned]
        return cleaned["id"] if self._write(rows) else ""

    @QtCore.Slot(str, result=bool)
    def actionMissing(self, row_id: str) -> bool:
        """An action_state row whose action isn't in the current profile
        (S158)."""
        index = self._index_of(row_id)
        if index < 0:
            return False
        source = self._rows[index]["source"]
        if source["kind"] != "action_state":
            return False
        action = source.get("action")
        profile = _current_profile()
        if not action or profile is None:
            return True
        return str(action) not in action_inputs(profile) and not _in_library(
            profile, str(action)
        )

    def _write(self, rows: list[dict]) -> bool:
        try:
            osc_device_file.write_feedback(rows, WHO)
        except OSError as exc:
            syslog.error("OSC: feedback rows not written: %s", exc)
            self._say("Not written. The OSC file could not be saved.")
            return False
        self._say("")
        self.reload()
        return True

    @QtCore.Slot(result=bool)
    def addRow(self) -> bool:
        return self._write([dict(r) for r in self._rows] + [new_row()])

    def _companion_target(self) -> str:
        """The Companion target's id; added (127.0.0.1:12321) when missing."""
        found = osc_device_file.find_companion_target(self._targets)
        if found is None:
            # Same target as Module Setup's Add Companion (Output tab).
            found = osc_device_file.ensure_companion_target(WHO)
        return found["id"]

    @QtCore.Slot(str, "QVariantMap", result=str)
    def addTemplateRow(self, kind: str, params: dict) -> str:
        """Adds a row from a template ("blank" or companion_variable /
        companion_text / companion_colour); the text to show (a note, or
        why nothing was added)."""
        if kind == "blank":
            return "" if self.addRow() else self._message
        params = dict(params or {})
        if kind not in osc_device_file.TEMPLATES:
            return "Unknown template."
        # Check the fields before a target is added.
        why = template_row(kind, params, osc_device_file.REPLY)
        if isinstance(why, str):
            self._say(why)
            return why
        try:
            target = self._companion_target()
        except OSError as exc:
            syslog.error("OSC: Companion target not written: %s", exc)
            self._say("Not written. The OSC file could not be saved.")
            return self._message
        row = template_row(kind, params, target)
        assert isinstance(row, dict)
        if not self._write([dict(r) for r in self._rows] + [row]):
            return self._message
        return VARIABLE_NOTE if kind == "companion_variable" else KEY_NOTE

    @QtCore.Slot(int, result=bool)
    def removeRow(self, index: int) -> bool:
        if not 0 <= index < len(self._rows):
            return False
        rows = [dict(r) for i, r in enumerate(self._rows) if i != index]
        return self._write(rows)

    @QtCore.Slot(int, str, "QVariant", result=bool)
    def setRowValue(self, index: int, key: str, value: object) -> bool:
        """Checks and saves one part of a row; False (with message) when
        refused."""
        if not 0 <= index < len(self._rows):
            return False
        row = dict(self._rows[index])
        source = dict(row["source"])
        if key == "enabled":
            row["enabled"] = bool(value)
        elif key == "kind":
            kind = str(value)
            if kind not in osc_device_file.SOURCE_KINDS:
                return False
            if kind != source["kind"]:
                source = {"kind": kind, "device": None, "input": None}
                if kind in ("vjoy_button", "vjoy_axis"):
                    source["device"] = _vjoy_ids()[0]
                    source["input"] = 1
        elif key == "device":
            number = _whole(value)
            if number is None or not 1 <= number <= 16:
                self._say("Pick a vJoy device.")
                return False
            source["device"] = number
        elif key == "input":
            if source["kind"] in ("vjoy_button", "vjoy_axis"):
                number = _whole(value)
                if number is None or number < 1:
                    self._say("The number is a whole number, 1 or more.")
                    return False
                source["input"] = number
            else:
                source["input"] = str(value or "") or None
        elif key == "action":
            text = str(value or "").strip()
            if text:
                source["action"] = text
            else:
                source.pop("action", None)
        elif key in ("showUnder", "show_under"):
            text = str(value or "").strip()
            if text:
                row["input"] = text
            else:
                row.pop("input", None)
        elif key == "target":
            row["target"] = str(value or "") or osc_device_file.REPLY
        elif key == "address":
            why = check_address(value)
            if why:
                self._say(why)
                return False
            row["address"] = str(value).strip()
        elif key in ("min", "max"):
            number = _number(value)
            if number is None:
                self._say("Min and Max are numbers, e.g. 0 or 1.5.")
                return False
            row[key] = number
        elif key in ("off_value", "on_value"):
            row[key] = _off_on(value)
        elif key == "type":
            if value not in osc_device_file.VALUE_TYPES:
                return False
            row["type"] = str(value)
        else:
            return False
        row["source"] = source
        if row == self._rows[index]:
            self._say("")
            return True
        rows = [dict(r) for r in self._rows]
        rows[index] = row
        return self._write(rows)


def _in_library(profile: object, action_id: str) -> bool:
    """action_id is used by an input of profile (any device)."""
    try:
        used = profile.library.in_use()  # type: ignore[attr-defined]
    except Exception:
        return False
    return action_id in {str(a) for a in used}


def _vjoy_ids() -> list[int]:
    """vJoy devices set up in the driver (1-16 when it can't be read)."""
    try:
        from gremlin.modules.output import vjoy_ids

        ids = vjoy_ids()
    except Exception:
        ids = []
    return ids or list(range(1, 17))


def _show(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else str(number)


def _show_off_on(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _show(float(value))
    return str(value)
