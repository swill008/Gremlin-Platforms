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
}

TYPE_LABELS = {
    "auto": "Auto",
    "int": "Int",
    "float": "Float",
    "bool": "True/false",
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


def check_address(text: object) -> str:
    """Why text can't be an OSC address ("" when it can)."""
    address = str(text or "").strip()
    if not address.startswith("/") or " " in address:
        return "An OSC address starts with / and has no spaces, e.g. /fire."
    return ""


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

    # -- rows ----------------------------------------------------------------

    @QtCore.Property(list, notify=changed)
    def rows(self) -> list:
        """Each row flattened for QML: id, enabled, kind, device, input,
        target, address, min, max, type (numbers as text)."""
        out = []
        for row in self._rows:
            source = row["source"]
            out.append(
                {
                    "id": row["id"],
                    "enabled": row["enabled"],
                    "kind": source["kind"],
                    "device": "" if source["device"] is None else source["device"],
                    "input": "" if source["input"] is None else source["input"],
                    "target": row["target"],
                    "address": row["address"],
                    "min": _show(row["min"]),
                    "max": _show(row["max"]),
                    "type": row["type"],
                }
            )
        return out

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
