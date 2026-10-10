# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The OSC page's rows on the shared control page base (D-09-OSC-PAGE).

OscLayoutModel is ControlLayoutModel for OSC: one parent per OSC input
(OscDevice().rows), its actions as child rows, groups, order and your names
kept in OSC's module file (osc.json: key "layout", input keys "osc:<uid>",
names in the claim's friendly names), the settings line under each title
(S134), live value and last seen (S141), Send Test (S145), Change Address,
Edit Settings on several inputs (S146) and Copy for Companion (S122)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, osc_device_file
from gremlin.error import GremlinError
from gremlin.logical_device import _natural_key, _same_group
from gremlin.modules import store
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.osc_rows import OscRow, OscRows
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import osc_device_model
from gremlin.ui.control_layout import (
    ROW_DEFAULTS,
    ControlLayoutModel,
    LayoutItem,
    parent_key,
    parse_parent,
)

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

KEY_PREFIX = "osc:"
TYPE_ORDER = (InputType.JoystickButton, InputType.JoystickAxis)
SETTING_KEYS = osc_device_model.SETTING_KEYS

# Roles the OSC page adds to the shared ones (parent rows; defaults elsewhere).
EXTRA_DEFAULTS: dict[str, Any] = {
    "uid": "",
    "address": "",
    "inputMode": "",
    "liveValue": "",
    "livePressed": False,
    "liveAxis": 0.0,
    "lastSeenAt": 0.0,
    "lastSeen": "",
    "liveSynthetic": False,
}
LIVE_ROLES = (
    "liveValue",
    "livePressed",
    "liveAxis",
    "lastSeenAt",
    "lastSeen",
    "liveSynthetic",
)

_FORMAT_WORDS = {
    "auto": "Auto",
    "direction": "1 = clockwise, 0 = counter-clockwise",
    "signed": "+n and −n",
}
_OUTPUT_WORDS = {
    "axis": "Axis",
    "pulse_cw": "Pulses clockwise",
    "pulse_ccw": "Pulses counter-clockwise",
}


def _num(value: float) -> str:
    return f"{value:g}"


def settings_line(row: OscRow) -> str:
    """The settings line under an input's title (S134), in the Add window's
    words: "Axis · Source value: P1 · Min: 0 · Max: 1"."""
    parts = [row.mode.capitalize()]
    source = f"Source value: P{row.source + 1}"
    if row.mode == "axis":
        parts += [source, f"Min: {_num(row.range_min)}", f"Max: {_num(row.range_max)}"]
    elif row.mode == "encoder":
        parts.append(f"Format: {_FORMAT_WORDS.get(row.enc_format, row.enc_format)}")
        parts.append(f"Output: {_OUTPUT_WORDS.get(row.enc_output, row.enc_output)}")
        if row.enc_output == "axis":
            parts.append(f"Step size: {_num(row.enc_step)}")
        elif row.delay_ms is not None:
            parts.append(f"Release after: {row.delay_ms} ms")
    else:
        if row.cmd_mode == "data":
            data = ", ".join(row.data)
            parts.append(f"Message + data: {data}" if data else "Message + data")
        else:
            parts += ["Message only", source]
        if row.trigger:
            parts.append("Trigger on message")
            if row.delay_ms is not None:
                parts.append(f"{row.delay_ms} ms")
    return " · ".join(parts)


def last_seen_text(at: float) -> str:
    """ "never", or "last seen 3 s ago" (min, h for older)."""
    if not at:
        return "never"
    gone = max(0.0, clock.now() - float(at))
    if gone < 60:
        return f"last seen {int(gone)} s ago"
    if gone < 3600:
        return f"last seen {int(gone // 60)} min ago"
    return f"last seen {int(gone // 3600)} h ago"


def live_fields(uid: str) -> dict[str, Any]:
    """The live roles of one input from OscRuntime.live (S141)."""
    live = OscRuntime().live(uid) if uid else None
    if live is None:
        return {
            "liveValue": "",
            "livePressed": False,
            "liveAxis": 0.0,
            "lastSeenAt": 0.0,
            "lastSeen": last_seen_text(0.0),
            "liveSynthetic": False,
        }
    pressed = live.get("pressed")
    axis = live.get("axis")
    if pressed is not None:
        text = "Pressed" if pressed else "Released"
    elif axis is not None:
        text = f"{float(axis):.2f}"
    else:
        value = live.get("value")
        text = "" if value is None else str(value)
    at = float(live.get("last_seen") or 0.0)
    return {
        "liveValue": text,
        "livePressed": bool(pressed),
        "liveAxis": float(axis) if axis is not None else 0.0,
        "lastSeenAt": at,
        "lastSeen": last_seen_text(at),
        "liveSynthetic": bool(live.get("synthetic")),
    }


@dataclass(frozen=True)
class OscLayoutItem:
    """One OSC input as the shared base reads it (LayoutItem)."""

    uid: str
    type: InputType
    id: int
    address: str
    group: str
    second_name: str

    @property
    def identifier(self) -> str:
        return self.uid

    @property
    def system_name(self) -> str:
        return self.address

    @property
    def label(self) -> str:
        return self.address

    @property
    def row_title(self) -> str:
        word = "Axis" if self.type == InputType.JoystickAxis else "Button"
        title = f"{word} {self.id} - {self.address}"
        return f"{title}   {self.second_name}" if self.second_name else title

    @property
    def choice_label(self) -> str:
        return self.address


class OscLayoutStore:
    """Groups, order and your names for OSC's inputs, over OSC's module file
    (the duck-typed store of control_layout). Inputs are known by uid, so a
    type change (a new number) keeps the place and the name."""

    def __init__(self) -> None:
        self._groups: list[str] = []
        self._order: list[str] = []
        self._group_of: dict[str, str] = {}
        self._names: dict[str, str] = {}

    @property
    def rows(self) -> OscRows:
        return OscDevice().rows

    # -- file --------------------------------------------------------------
    # The layout and names live with OSC's rows (read by
    # osc_device_file.load, written by its save): an edit here marks OSC's
    # file changed (the title's "*"), File > Save Profile writes it with the
    # inputs in one write, Discard reads the file again (D-09-OSC-FILE).

    def load(self) -> None:
        """Takes the layout and names OSC's rows hold."""
        rows = self.rows
        layout = store.normalize_layout(rows.layout)

        def uid(key: str) -> str:
            return key[len(KEY_PREFIX) :] if key.startswith(KEY_PREFIX) else ""

        self._groups = list(layout["groups"])
        self._order = [uid(key) for key in layout["order"] if uid(key)]
        self._group_of = {
            uid(key): name for key, name in layout["group_of"].items() if uid(key)
        }
        self._names = {}
        for key, value in rows.names.items():
            text = str(value or "").strip()
            if uid(str(key)) and text:
                self._names[uid(str(key))] = text

    def _layout_doc(self) -> dict:
        return store.normalize_layout(
            {
                "groups": self._groups,
                "order": [KEY_PREFIX + uid for uid in self._order],
                "group_of": {
                    KEY_PREFIX + uid: name for uid, name in self._group_of.items()
                },
            }
        )

    def _save(self) -> None:
        """Hands the layout and names to OSC's rows, unsaved until Save."""
        self.rows.set_layout(
            self._layout_doc(),
            {KEY_PREFIX + uid: name for uid, name in self._names.items()},
        )

    # -- Undo --------------------------------------------------------------

    def memento(self) -> dict:
        return {
            "rows": self.rows.to_dict()["inputs"],
            "groups": list(self._groups),
            "order": list(self._order),
            "group_of": dict(self._group_of),
            "names": dict(self._names),
        }

    def restore(self, memo: dict) -> None:
        rows = self.rows
        if rows.to_dict()["inputs"] != memo["rows"]:
            rows.load_dict({"inputs": memo["rows"]})
            # load_dict counts as saved; this is an edit to save.
            rows.mark_dirty()
        self._groups = list(memo["groups"])
        self._order = list(memo["order"])
        self._group_of = dict(memo["group_of"])
        self._names = dict(memo["names"])
        self._save()

    # -- reading -----------------------------------------------------------

    def group_names(self) -> list[str]:
        return list(self._groups)

    def _item(self, row: OscRow) -> OscLayoutItem:
        group = self._group_of.get(row.uid, "")
        return OscLayoutItem(
            uid=row.uid,
            type=row.input_type,
            id=row.input_id,
            address=row.label,
            group=group if group in self._groups else "",
            second_name=self._names.get(row.uid, ""),
        )

    def _uids(self) -> list[str]:
        """Every input's uid in page order: the saved order, then the rest
        (buttons, then axes, by number)."""
        rows = self.rows.rows()
        known = {row.uid for row in rows}
        out = [uid for uid in dict.fromkeys(self._order) if uid in known]
        seen = set(out)
        rest = sorted(
            (row for row in rows if row.uid not in seen),
            key=lambda r: (TYPE_ORDER.index(r.input_type), r.input_id),
        )
        return out + [row.uid for row in rest]

    def ordered(self) -> list[OscLayoutItem]:
        rows = self.rows
        items = []
        for uid in self._uids():
            row = rows.by_uid(uid)
            if row is not None:
                items.append(self._item(row))
        return items

    def exists(self, identifier: object) -> bool:
        return bool(identifier) and self.rows.by_uid(str(identifier)) is not None

    def __getitem__(self, identifier: object) -> OscLayoutItem:
        row = self.rows.by_uid(str(identifier)) if identifier else None
        if row is None:
            raise KeyError(identifier)
        return self._item(row)

    # -- edits -------------------------------------------------------------

    def _ensure(self, name: str) -> str:
        text = " ".join((name or "").split())
        if not text:
            return text
        for existing in self._groups:
            if _same_group(existing, text):
                return existing
        self._groups.append(text)
        return text

    def ensure_group(self, name: str) -> str:
        """The group for a typed name, made only when new (capitals and
        spacing don't make a look-alike)."""
        text = self._ensure(name)
        self._save()
        return text

    def rename_group(self, old_name: str, new_name: str) -> None:
        old = (old_name or "").strip()
        new = " ".join((new_name or "").split())
        if not old or old not in self._groups:
            raise GremlinError(f"No group named '{old_name}' exists")
        if not new:
            raise GremlinError("A group needs a name")
        clash = next(
            (name for name in self._groups if name != old and _same_group(name, new)),
            None,
        )
        if clash is not None:
            raise GremlinError(f"A group named '{clash}' already exists")
        self._groups = [new if name == old else name for name in self._groups]
        self._group_of = {
            uid: (new if name == old else name) for uid, name in self._group_of.items()
        }
        self._save()

    def delete_group(self, name: str) -> None:
        """Removes the group; its inputs go to Ungrouped."""
        text = (name or "").strip()
        self._groups = [entry for entry in self._groups if entry != text]
        self._group_of = {
            uid: group for uid, group in self._group_of.items() if group != text
        }
        self._save()

    def place(self, identifier: object, group: str, before: object = None) -> None:
        uid = str(identifier)
        folder = self._ensure(group or "")
        if folder:
            self._group_of[uid] = folder
        else:
            self._group_of.pop(uid, None)
        order = [entry for entry in self._uids() if entry != uid]
        if before is not None and str(before) in order and str(before) != uid:
            order.insert(order.index(str(before)), uid)
        else:
            order.append(uid)
        self._order = order
        self._save()

    def move_group_before(self, name: str, before: str | None) -> None:
        text = (name or "").strip()
        if text not in self._groups:
            return
        self._groups = [entry for entry in self._groups if entry != text]
        if before and before in self._groups:
            self._groups.insert(self._groups.index(before), text)
        else:
            self._groups.append(text)
        self._save()

    def sort_within(self, key_name: str) -> None:
        """Orders the inputs inside each group: "system" by address (Order ›
        By Address, S28), "user" by your name (else the address)."""
        items = self.ordered()
        order: list[str] = []
        for folder in [""] + self._groups:
            bucket = [item for item in items if (item.group or "") == folder]
            if key_name == "user":
                bucket.sort(
                    key=lambda i: (_natural_key(i.second_name or i.address), i.id)
                )
            else:
                bucket.sort(key=lambda i: (i.address.casefold(), i.type.value, i.id))
            order.extend(item.uid for item in bucket)
        self._order = order
        self._save()

    def sort_groups(self) -> None:
        self._groups.sort(key=_natural_key)
        self._save()

    def set_user_label(self, identifier: object, text: str) -> None:
        uid = str(identifier)
        row = self.rows.by_uid(uid)
        cleaned = (text or "").strip()
        if row is not None and cleaned == row.label:
            cleaned = ""
        if cleaned:
            self._names[uid] = cleaned
        else:
            self._names.pop(uid, None)
        self._save()

    def delete(self, identifier: object) -> None:
        uid = str(identifier)
        self.rows.delete(uid)
        self._order = [entry for entry in self._order if entry != uid]
        self._group_of.pop(uid, None)
        self._names.pop(uid, None)
        self._save()


# One layout for every OSC page (OSC's rows are shared too).
_STORE = OscLayoutStore()


def osc_layout_store() -> OscLayoutStore:
    return _STORE


@ta.QmlElement
class OscLayoutModel(ControlLayoutModel):
    """Rows for the OSC page: group headers, one parent per OSC input, and
    its actions in the current mode."""

    roles = {
        **ControlLayoutModel.roles,
        **{
            QtCore.Qt.ItemDataRole.UserRole
            + 1
            + len(ROW_DEFAULTS)
            + i: QtCore.QByteArray(name.encode())
            for i, name in enumerate(EXTRA_DEFAULTS)
        },
    }
    _ROLE_OF = {bytes(v.data()).decode(): k for k, v in roles.items()}

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._baseline: dict | None = None
        self._seen_edit = osc_device_model.last_edit()[0]
        self._store: OscLayoutStore
        modified = getattr(signal, "oscDeviceModified", None)
        if modified is not None:
            modified.connect(self._on_external)
        reloaded = getattr(signal, "oscDeviceReloaded", None)
        if reloaded is not None:
            reloaded.connect(self._on_file_read)
        OscRuntime().liveChanged.connect(self._on_live)
        self._rebuild()

    # ControlLayoutModel hooks.

    def _make_store(self) -> OscLayoutStore:
        self._store = osc_layout_store()
        self._store.load()
        return self._store

    def _device_guid(self) -> uuid.UUID:
        return OSC_DEVICE_UUID

    def _identifier(self, kind: InputType, input_id: int) -> str | None:
        return OscDevice().rows.uid_of(kind, input_id)

    def _emit_store_changed(self) -> None:
        osc_device_model._emit_modified()

    def _type_order(self) -> tuple[InputType, ...]:
        return TYPE_ORDER

    def _parent_subtitle(self, item: LayoutItem, extra: list[dict]) -> str:
        row = self._osc_row(item)
        return settings_line(row) if row is not None else ""

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        row = self._osc_row(item)
        if row is None:
            return {}
        return {
            "uid": row.uid,
            "address": row.label,
            "inputMode": row.mode,
            **live_fields(row.uid),
        }

    def _sort_system_label(self) -> str:
        return "Sort by Address"

    def _row(self, **fields: object) -> dict:
        return {**ROW_DEFAULTS, **EXTRA_DEFAULTS, **fields}

    # Undo for edits made in the Add / Import / Listen windows (S131).

    def _rebuild(self) -> None:
        super()._rebuild()
        self._baseline = self._layout.memento()

    def _on_external(self) -> None:
        if self._writing:
            return
        serial, label = osc_device_model.last_edit()
        if label and serial != self._seen_edit and self._baseline is not None:
            after = self._layout.memento()
            if after != self._baseline:
                self._undo.append(
                    {
                        "before": self._baseline,
                        "after": after,
                        "links": [],
                        "label": label,
                    }
                )
                if len(self._undo) > 50:
                    self._undo.pop(0)
                self._redo.clear()
                self._just_undid = False
        self._seen_edit = serial
        self._rebuild()

    def _on_file_read(self) -> None:
        self._store.load()
        self._on_reloaded()

    # Live value and last seen (S141): only that input's row changes.

    def _on_live(self, uid: str) -> None:
        for index, row in enumerate(self._rows):
            if row.get("rowKind") != "parent" or row.get("uid") != uid:
                continue
            row.update(live_fields(uid))
            at = self.index(index, 0)
            self.dataChanged.emit(at, at, [self._ROLE_OF[name] for name in LIVE_ROLES])
            return

    # Helpers.

    def _osc_row(self, item: LayoutItem | None) -> OscRow | None:
        if item is None:
            return None
        return OscDevice().rows.by_uid(str(item.identifier))

    def _row_of_key(self, key: str) -> OscRow | None:
        return self._osc_row(self._item_for(key))

    # Slots.

    @QtCore.Slot(float, result=str)
    def lastSeenText(self, at: float) -> str:
        return last_seen_text(at)

    @QtCore.Slot(str, result=str)
    def keyOfUid(self, uid: str) -> str:
        row = OscDevice().rows.by_uid(uid)
        return parent_key(row.input_type, row.input_id) if row is not None else ""

    @QtCore.Slot(str, result=str)
    def uidOf(self, key: str) -> str:
        row = self._row_of_key(key)
        return row.uid if row is not None else ""

    @QtCore.Slot(str, result=str)
    def addressOf(self, key: str) -> str:
        row = self._row_of_key(key)
        return row.label if row is not None else ""

    @QtCore.Slot(str, result=str)
    def kindOf(self, key: str) -> str:
        parsed = parse_parent(key)
        if parsed is None:
            return ""
        return "axis" if parsed[0] == InputType.JoystickAxis else "button"

    @QtCore.Slot(str, str, float, result=bool)
    def sendTest(self, key: str, kind: str, value: float = 0.0) -> bool:
        """Send Test Press / Send Test Value (S145): as if the input got a
        message. A press is let go after the input's delay."""
        row = self._row_of_key(key)
        if row is None:
            return False
        runtime = OscRuntime()
        if kind == "value":
            return runtime.send_test(row.uid, "value", float(value))
        if kind not in ("press", "release"):
            return False
        fired = runtime.send_test(row.uid, kind)
        if kind == "press":
            delay = row.delay_ms
            if delay is None:
                delay = osc_device_file.read_server()["autorelease_delay_ms"]
            uid = row.uid
            QtCore.QTimer.singleShot(
                max(1, int(delay)), lambda: OscRuntime().send_test(uid, "release")
            )
        return fired

    @QtCore.Slot(str, str, result=str)
    def changeAddress(self, key: str, address: str) -> str:
        """Change Address…: "" or the error to show."""
        row = self._row_of_key(key)
        if row is None:
            return "That input no longer exists."
        uid, old = row.uid, row.label
        error: list[str] = []

        def fn() -> list[dict]:
            error.append(osc_device_model.update_settings(uid, {"address": address}))
            return []

        if not self._apply(fn, f"Change Address of {old}"):
            return "The profile is running."
        return error[0] if error else ""

    def _rows_for(self, keys: list) -> list[OscRow]:
        found = []
        for key in keys:
            row = self._row_of_key(str(key))
            if row is not None and row not in found:
                found.append(row)
        return found

    @QtCore.Slot("QStringList", result="QVariantMap")
    def editSettingsFor(self, keys: list) -> dict[str, Any]:
        """Edit Settings… on one or more inputs (S146): the shared values; a
        setting that differs is "" and named in "mixed"."""
        rows = self._rows_for(keys)
        out: dict[str, Any] = {
            "count": len(rows),
            "keys": [parent_key(r.input_type, r.input_id) for r in rows],
            "address": rows[0].label if len(rows) == 1 else "",
            "locked": any(osc_device_model.has_actions(r) for r in rows),
            "mixed": [],
        }
        settings = [osc_device_model.settings_of(r) for r in rows]
        for name in SETTING_KEYS:
            values = [entry[name] for entry in settings]
            if values and all(value == values[0] for value in values):
                out[name] = values[0]
            else:
                out[name] = ""
                if values:
                    out["mixed"].append(name)
        return out

    @QtCore.Slot("QStringList", "QVariantMap", result=str)
    def applySettings(self, keys: list, changed: object) -> str:
        """Applies only the given settings to each input, as one Undo step;
        "" or a line per refused input."""
        rows = self._rows_for(keys)
        if not rows:
            return "Those inputs no longer exist."
        src = osc_device_model.normalize_raw(changed)
        if len(rows) > 1:
            src.pop("address", None)
        targets = [(row.uid, row.label) for row in rows]
        refused: list[str] = []

        def fn() -> list[dict]:
            for uid, address in targets:
                why = osc_device_model.update_settings(uid, src)
                if why:
                    refused.append(f"{address}: {why}")
            return []

        label = (
            f"Edit Settings of {targets[0][1]}"
            if len(targets) == 1
            else f"Edit Settings of {len(targets)} inputs"
        )
        if not self._apply(fn, label):
            return "The profile is running."
        return "\n".join(refused)

    @QtCore.Slot(str, result=str)
    def copyForCompanion(self, key: str) -> str:
        """Copy for Companion (S122): the text, also put on the clipboard."""
        row = self._row_of_key(key)
        if row is None:
            return ""
        text = osc_device_model.companion_text(row)
        osc_device_model.copy_text(text)
        return text

    @QtCore.Slot()
    def clearAll(self) -> None:
        """Clear… (S27): every input and its actions, one Undo step."""
        items = list(self._layout.ordered())
        if not items:
            return

        def fn() -> list[dict]:
            links: list[dict] = []
            for item in items:
                if self._layout.exists(item.identifier):
                    links.extend(self._delete_parent(item))
            return links

        self._apply(fn, "Clear all inputs")
