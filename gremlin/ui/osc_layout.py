# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The OSC page's rows on the shared control page base (D-09-OSC-PAGE).

OscLayoutModel is ControlLayoutModel for OSC: one parent per OSC input
(OscDevice().rows), its actions as child rows, groups, order and your names
kept in OSC's module file (osc.json: key "layout", input keys "osc:<uid>",
names in the claim's friendly names), the settings line under each title
(S134), live value and last seen (S141), Send Test (S145), Change Address,
Edit Settings on several inputs (S146) and Copy for Companion (S122).

Batch 2: address patterns on the page (S147-S152: subtitle, Patterns
filter, seen-address hint, pattern errors) and Feedback rows (S153-S158):
child rows of kind "feedback" after an input's actions, the rest in the
fixed group "Feedback not tied to an input" at the bottom, edited in the
pane while a profile runs too, each edit a page Undo step."""

from __future__ import annotations

import contextlib
import copy
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, osc_device_file, osc_pattern
from gremlin.error import GremlinError
from gremlin.logical_device import _natural_key, _same_group
from gremlin.modules import store
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.osc_rows import OscRow, OscRows
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import osc_device_model, osc_feedback_model
from gremlin.ui.control_layout import (
    ROW_DEFAULTS,
    ControlLayoutModel,
    LayoutItem,
    group_key,
    parent_key,
    parse_parent,
)

if TYPE_CHECKING:
    from gremlin.profile import Profile

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
    "isPattern": False,
    # Feedback rows (S153): the inline check box and the stored row id.
    "enabled": False,
    "feedbackId": "",
    # The bottom group "Feedback not tied to an input": not a user group.
    "fixedGroup": False,
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


def pattern_line(count: int) -> str:
    """The start of a pattern input's subtitle (S147)."""
    word = "address" if count == 1 else "addresses"
    return f"Pattern · {count} {word} seen"


# -- Feedback rows (S153-S158) -------------------------------------------

FEEDBACK_PREFIX = "feedback:"
FEEDBACK_GROUP = "feedbackgroup"
FEEDBACK_GROUP_TITLE = "Feedback not tied to an input"
FEEDBACK_WHO = "OSC page"
SHOW_UNDER_NONE = "By its source"
# Editor field names (QML) -> stored row keys.
_STORED = {"offValue": "off_value", "onValue": "on_value", "showUnder": "input"}


def feedback_key(row_id: str) -> str:
    return FEEDBACK_PREFIX + str(row_id)


def feedback_id(key: str) -> str:
    text = str(key or "")
    return text[len(FEEDBACK_PREFIX) :] if text.startswith(FEEDBACK_PREFIX) else ""


def _target_text(target: str, targets: list[dict]) -> str:
    if target == osc_device_file.REPLY:
        return "the sender"
    for entry in targets:
        if entry["id"] == target:
            return entry["name"] or f"{entry['host']}:{entry['port']}"
    return "a target that no longer exists"


def feedback_what(
    row: dict, under: str | None, actions: dict[str, str], logical: dict[str, str]
) -> str:
    """What a feedback row sends, in words ("this input's value")."""
    source = row["source"]
    kind = source["kind"]
    device, number = source.get("device"), source.get("input")
    if kind == "mode":
        return "the mode"
    if kind == "vjoy_button":
        return f"vJoy {device} button {number}"
    if kind == "vjoy_axis":
        return f"vJoy {device} axis {number}"
    if kind == "logical":
        return logical.get(str(number), "a Logical Device control")
    if kind == "osc_input":
        if under and str(number) == under:
            return "this input's value"
        other = OscDevice().rows.by_uid(str(number)) if number else None
        return f"{other.label}'s value" if other else "an OSC input's value"
    if kind == "action_state":
        label = actions.get(str(source.get("action") or ""))
        return f"{label}'s state" if label else "an action's state"
    if kind == "paused":
        return "Running / Paused"
    return kind


def feedback_title(
    row: dict,
    under: str | None,
    actions: dict[str, str],
    logical: dict[str, str],
    targets: list[dict],
) -> str:
    """ "Sends <what> to <target> · <address>" (S153)."""
    what = feedback_what(row, under, actions, logical)
    return f"Sends {what} to {_target_text(row['target'], targets)} · {row['address']}"


def action_missing(row: dict, actions: dict[str, str]) -> bool:
    """An Action state row whose action isn't in the current profile (S158)."""
    source = row["source"]
    return source["kind"] == "action_state" and (
        str(source.get("action") or "") not in actions
    )


def stateful_labels(profile: Profile | None) -> dict[str, str]:
    """Action id -> label of every Smart Toggle and Tempo in profile."""
    if profile is None:
        return {}
    from gremlin import action_state

    out: dict[str, str] = {}
    for aid, label in action_state.stateful_actions(profile):
        out.setdefault(str(aid), label)
    return out


def _logical_names() -> dict[str, str]:
    from gremlin import logical_device_file

    out = {}
    for control in logical_device_file.read_layout()["controls"]:
        uid = str(control.get("uid") or "")
        if uid:
            out[uid] = str(control.get("user-label") or control.get("label") or uid)
    return out


def set_field(row: dict, name: str, value: object) -> str:
    """Puts one editor field into a stored feedback row (in place); "" or
    why it was refused. The same checks as Module Setup's rows."""
    fb = osc_feedback_model
    source = dict(row["source"])
    if name == "enabled":
        row["enabled"] = bool(value)
    elif name == "kind":
        kind = str(value)
        if kind not in osc_device_file.SOURCE_KINDS:
            return "Pick a source."
        if kind != source["kind"]:
            source = {"kind": kind, "device": None, "input": None}
            if kind in ("vjoy_button", "vjoy_axis"):
                source["device"] = fb._vjoy_ids()[0]
                source["input"] = 1
    elif name == "device":
        number = fb._whole(value)
        if number is None or not 1 <= number <= 16:
            return "Pick a vJoy device."
        source["device"] = number
    elif name == "input":
        if source["kind"] in ("vjoy_button", "vjoy_axis"):
            number = fb._whole(value)
            if number is None or number < 1:
                return "The number is a whole number, 1 or more."
            source["input"] = number
        else:
            source["input"] = str(value or "") or None
    elif name == "action":
        text = str(value or "").strip()
        if text:
            source["action"] = text
        else:
            source.pop("action", None)
    elif name == "showUnder":
        text = str(value or "").strip()
        if text:
            row["input"] = text
        else:
            row.pop("input", None)
    elif name == "target":
        row["target"] = str(value or "") or osc_device_file.REPLY
    elif name == "address":
        # Outgoing addresses are exact (S149).
        why = fb.check_address(value)
        if why:
            return why
        row["address"] = str(value).strip()
    elif name in ("min", "max"):
        number = fb._number(value)
        if number is None:
            return "Min and Max are numbers, e.g. 0 or 1.5."
        row[name] = number
    elif name in ("offValue", "onValue"):
        stored = _STORED[name]
        given = fb._off_on(value)
        if given is None:
            row.pop(stored, None)
        else:
            row[stored] = given
    elif name == "type":
        if value not in osc_device_file.VALUE_TYPES:
            return "Pick a value type."
        row["type"] = str(value)
    else:
        return f"Unknown field {name}."
    row["source"] = source
    return ""


def _stored_feedback() -> list:
    """The feedback rows as stored (uncleaned, so two reads compare equal)."""
    raw = store.read_path(osc_device_file.path()).get(osc_device_file.FEEDBACK_KEY)
    return copy.deepcopy(raw) if isinstance(raw, list) else []


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
        # Feedback rows ride along (written at once, not at Save): a
        # feedback edit is a page Undo step too (S156).
        return {
            "feedback": _stored_feedback(),
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
        if _stored_feedback() != memo["feedback"]:
            osc_device_file.write_feedback(memo["feedback"], FEEDBACK_WHO)
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

    feedbackMessageChanged = QtCore.Signal()
    feedbackEditorChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._baseline: dict | None = None
        self._seen_edit = osc_device_model.last_edit()[0]
        self._store: OscLayoutStore
        self._patterns_only = False
        self._seen: list[str] = []
        # Feedback rows of this rebuild: input uid -> page entries; the
        # entries tied to no input go to the bottom group.
        self._fb_under: dict[str, list[dict]] = {}
        self._fb_loose: list[dict] = []
        self._fb_actions: dict[str, str] = {}
        self._fb_unlocked = False
        self._fb_writing = False
        self._fb_message = ""
        # The pane's feedback editor: the stored row and its draft.
        self._fb_id = ""
        self._fb_saved: dict | None = None
        self._fb_draft: dict | None = None
        self._fb_error = ""
        self._fb_choices: osc_feedback_model.OscFeedbackModel | None = None
        changed = getattr(signal, "oscFeedbackChanged", None)
        if changed is not None:
            changed.connect(self._on_feedback_changed)
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
        return self._subtitle_of(row) if row is not None else ""

    def _subtitle_of(self, row: OscRow) -> str:
        line = settings_line(row)
        if not row.is_pattern:
            return line
        seen = osc_device_model.seen_matching(row.label, self._seen)
        return f"{pattern_line(len(seen))} · {line}"

    def _parent_fields(self, item: LayoutItem, extra: list[dict]) -> dict:
        row = self._osc_row(item)
        if row is None:
            return {}
        return {
            "uid": row.uid,
            "address": row.label,
            "inputMode": row.mode,
            "isPattern": row.is_pattern,
            **live_fields(row.uid),
        }

    def _sort_system_label(self) -> str:
        return "Sort by Address"

    def _row(self, **fields: object) -> dict:
        row = {**ROW_DEFAULTS, **EXTRA_DEFAULTS, **fields}
        if row["rowKind"] == "parent" and row["uid"]:
            # Feedback rows count as children: an input with only feedback
            # rows still gets a caret.
            row["childCount"] += len(self._fb_under.get(row["uid"], ()))
        return row

    def _rows_after_actions(self, item: LayoutItem, extra: list[dict]) -> list[dict]:
        # Actions first, then feedback rows (S156).
        key = parent_key(item.type, item.id)
        return [
            self._feedback_row(entry, key, group_key(item.group), item.group or "")
            for entry in self._fb_under.get(str(item.identifier), [])
        ]

    def _filtering(self) -> bool:
        return self._patterns_only or super()._filtering()

    def _visible_parent(
        self, item: LayoutItem, extra: list[dict], action_count: int
    ) -> bool:
        if self._patterns_only:
            row = self._osc_row(item)
            if row is None or not row.is_pattern:
                return False
        return super()._visible_parent(item, extra, action_count)

    def _refused(self) -> bool:
        # Feedback edits go on while a profile runs (S155).
        return False if self._fb_unlocked else super()._refused()

    # Undo for edits made in the Add / Import / Listen windows (S131).

    def _rebuild(self) -> None:
        self._seen = osc_device_model.seen_addresses()
        self._place_feedback()
        super()._rebuild()
        self._baseline = self._layout.memento()
        self._refresh_editor()

    def _rows_at_end(self) -> list[dict]:
        # The bottom group goes last, after every group.
        return self._loose_rows()

    # Feedback rows (S153-S158).

    def _place_feedback(self) -> None:
        profile = self._profile()
        rows = osc_device_file.read_feedback()
        self._fb_actions = stateful_labels(profile)
        logical = (
            _logical_names()
            if any(row["source"]["kind"] == "logical" for row in rows)
            else {}
        )
        targets = osc_device_file.read_targets()
        known = {row.uid for row in OscDevice().rows.rows()}
        self._fb_under = {}
        self._fb_loose = []
        entries = osc_feedback_model.rows_for_page(rows, profile)
        for row, entry in zip(rows, entries, strict=True):
            under = entry["placement"] if entry["placement"] in known else None
            entry["title"] = feedback_title(
                row, under, self._fb_actions, logical, targets
            )
            entry["note"] = (
                osc_feedback_model.ACTION_MISSING
                if action_missing(row, self._fb_actions)
                else ""
            )
            if under:
                self._fb_under.setdefault(under, []).append(entry)
            else:
                self._fb_loose.append(entry)

    def _feedback_row(
        self, entry: dict, parent: str, group: str, group_name: str
    ) -> dict:
        return self._row(
            rowKind="feedback",
            key=feedback_key(entry["id"]),
            title=entry["title"],
            subtitle=entry["note"],
            parentKey=parent,
            groupKey=group,
            groupName=group_name,
            indent=1,
            enabled=bool(entry["enabled"]),
            feedbackId=entry["id"],
        )

    def _loose_rows(self) -> list[dict]:
        """The bottom group "Feedback not tied to an input" and its rows."""
        entries = self._fb_loose
        if self._filtering():
            if (
                self._patterns_only
                or self._type_filter not in ("", "all")
                or self._ungrouped_only
                or self._no_writer
                or self._no_actions
            ):
                return []
            text = self._search.lower()
            entries = [e for e in entries if text in e["title"].lower()]
        if not entries:
            return []
        count = len(entries)
        out = [
            self._row(
                rowKind="group",
                key=FEEDBACK_GROUP,
                title=FEEDBACK_GROUP_TITLE,
                subtitle=f"{count} feedback row" + ("" if count == 1 else "s"),
                groupKey=FEEDBACK_GROUP,
                childCount=count,
                fixedGroup=True,
            )
        ]
        out += [
            self._feedback_row(entry, FEEDBACK_GROUP, FEEDBACK_GROUP, "")
            for entry in entries
        ]
        return out

    def _on_feedback_changed(self) -> None:
        if self._writing or self._fb_writing:
            return
        self._rebuild()

    @contextlib.contextmanager
    def _feedback_step(self) -> Iterator[None]:
        """Lets one feedback edit (or its Undo) through while running."""
        self._fb_unlocked = True
        self._fb_writing = True
        try:
            yield
        finally:
            self._fb_unlocked = False
            self._fb_writing = False

    def _apply_feedback(self, change: Callable[[list[dict]], str], label: str) -> str:
        """change(rows) edits the stored rows in place and returns what to
        hand back ("": nothing to write). One page Undo step, also while a
        profile runs."""
        result: list[str] = []
        top = self._undo[-1] if self._undo else None

        def fn() -> list[dict]:
            rows = osc_device_file.read_feedback()
            out = change(rows)
            if out:
                osc_device_file.write_feedback(rows, FEEDBACK_WHO)
            result.append(out)
            return []

        try:
            with self._feedback_step():
                self._apply(fn, label)
        except OSError as exc:
            self._say(f"Not written. The OSC file could not be saved. ({exc})")
            self._rebuild()
            return ""
        if self._undo and self._undo[-1] is not top:
            self._undo[-1]["feedbackOnly"] = True
        return result[0] if result else ""

    def _say(self, text: str) -> None:
        if text != self._fb_message:
            self._fb_message = text
            self.feedbackMessageChanged.emit()

    @staticmethod
    def _index_of(rows: list[dict], row_id: str) -> int:
        for index, row in enumerate(rows):
            if row["id"] == row_id:
                return index
        return -1

    def _stored_row(self, row_id: str) -> dict | None:
        rows = osc_device_file.read_feedback()
        index = self._index_of(rows, row_id)
        return rows[index] if index >= 0 else None

    # Undo / Redo of a feedback step work while running too (S155, S156).

    @QtCore.Slot()
    def undo(self) -> None:
        top = self._undo[-1] if self._undo else None
        if top is not None and top.get("feedbackOnly"):
            with self._feedback_step():
                super().undo()
            return
        super().undo()

    @QtCore.Slot()
    def redo(self) -> None:
        top = self._redo[-1] if self._redo else None
        if top is not None and top.get("feedbackOnly"):
            with self._feedback_step():
                super().redo()
            return
        super().redo()

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
            names: list[str] = list(LIVE_ROLES)
            osc_row = OscDevice().rows.by_uid(uid)
            if osc_row is not None and osc_row.is_pattern:
                # A new address may have been seen: "Pattern · N addresses seen".
                self._seen = osc_device_model.seen_addresses()
                row["subtitle"] = self._subtitle_of(osc_row)
                names.append("subtitle")
            at = self.index(index, 0)
            self.dataChanged.emit(at, at, [self._ROLE_OF[name] for name in names])
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

    # Address patterns on the page (S147-S152).

    @QtCore.Slot(bool)
    def setPatternsOnly(self, on: bool) -> None:
        """Find's "Patterns" tick: only pattern inputs."""
        self._patterns_only = bool(on)
        self._rebuild()

    @QtCore.Slot(str, result=int)
    def matchesSeen(self, address: str) -> int:
        """How many addresses seen in the OSC Monitor this address answers
        ("Matches N of the addresses seen")."""
        return len(osc_device_model.seen_matching(address))

    @QtCore.Slot(str, result=str)
    def addressError(self, address: str) -> str:
        """Why an input address is refused ("" when it's fine), for the
        Change Address… error line (S152)."""
        return osc_pattern.check(str(address or "").strip())

    # Feedback rows (S153-S156): each edit is a page Undo step and works
    # while a profile runs.

    @QtCore.Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._fb_message

    @QtCore.Slot(str, result=bool)
    def isFeedbackKey(self, key: str) -> bool:
        return bool(feedback_id(key))

    def _add_row(self, row: dict, label: str) -> str:
        cleaned = osc_device_file.clean_feedback([row])[0]
        cleaned["id"] = osc_device_file.new_id()

        def change(rows: list[dict]) -> str:
            rows.append(cleaned)
            return cleaned["id"]

        new_id = self._apply_feedback(change, label)
        return feedback_key(new_id) if new_id else ""

    @QtCore.Slot(str, result=str)
    def addFeedback(self, parent: str) -> str:
        """Add Feedback on an input: its value back to the sender, at its
        own address (a pattern input: /gremlin/feedback, S149). The new
        row's key, "" when refused."""
        osc_row = self._row_of_key(parent)
        if osc_row is None:
            return ""
        row = osc_feedback_model.new_row()
        row["source"] = {"kind": "osc_input", "device": None, "input": osc_row.uid}
        row["target"] = osc_device_file.REPLY
        row["address"] = "/gremlin/feedback" if osc_row.is_pattern else osc_row.label
        self._say("")
        return self._add_row(row, f"Add Feedback to {osc_row.label}")

    @QtCore.Slot(str, str, result=str)
    def addCompanionFeedback(self, parent: str, kind: str) -> str:
        """Companion Key text ("text") or Key color ("colour") for an
        input: its value drives the key. The new row's key or ""."""
        osc_row = self._row_of_key(parent)
        template = {"text": "companion_text", "colour": "companion_colour"}.get(kind)
        if osc_row is None or template is None:
            return ""
        try:
            found = osc_device_file.find_companion_target()
            if found is None:
                found = osc_device_file.ensure_companion_target(FEEDBACK_WHO)
        except OSError as exc:
            self._say(f"Not written. The OSC file could not be saved. ({exc})")
            return ""
        row = osc_feedback_model.template_row(template, {}, found["id"])
        if isinstance(row, str):
            self._say(row)
            return ""
        row["source"] = {"kind": "osc_input", "device": None, "input": osc_row.uid}
        word = "Key text" if kind == "text" else "Key color"
        key = self._add_row(row, f"Add Companion {word} to {osc_row.label}")
        if key:
            self._say(osc_feedback_model.KEY_NOTE)
        return key

    def _edit_row(
        self, key: str, edit: Callable[[list[dict], int], str], label: str
    ) -> str:
        row_id = feedback_id(key)
        stored = self._stored_row(row_id) if row_id else None
        if stored is None:
            return ""

        def change(rows: list[dict]) -> str:
            index = self._index_of(rows, row_id)
            return edit(rows, index) if index >= 0 else ""

        return self._apply_feedback(change, f"{label} · {stored['address']}")

    @QtCore.Slot(str, bool, result=bool)
    def setFeedbackEnabled(self, key: str, on: bool) -> bool:
        def edit(rows: list[dict], index: int) -> str:
            if rows[index]["enabled"] == bool(on):
                return ""
            rows[index]["enabled"] = bool(on)
            return "done"

        word = "On" if on else "Off"
        self._edit_row(key, edit, f"Turn Feedback {word}")
        stored = self._stored_row(feedback_id(key))
        return stored is not None and stored["enabled"] == bool(on)

    @QtCore.Slot(str, result=str)
    def duplicateFeedback(self, key: str) -> str:
        """A copy (new id) right after the row; its key or ""."""

        def edit(rows: list[dict], index: int) -> str:
            twin = copy.deepcopy(rows[index])
            twin["id"] = osc_device_file.new_id()
            rows.insert(index + 1, twin)
            return twin["id"]

        new_id = self._edit_row(key, edit, "Duplicate Feedback")
        return feedback_key(new_id) if new_id else ""

    @QtCore.Slot(str, result=bool)
    def deleteFeedback(self, key: str) -> bool:
        def edit(rows: list[dict], index: int) -> str:
            del rows[index]
            return "done"

        if feedback_id(key) and feedback_id(key) == self._fb_id:
            self.endFeedback()
        return bool(self._edit_row(key, edit, "Delete Feedback"))

    # The pane's Feedback editor.

    def _choices(self) -> dict:
        if self._fb_choices is None:
            self._fb_choices = osc_feedback_model.OscFeedbackModel(self)
        fb = self._fb_choices

        def get(name: str) -> list:
            return list(cast("list", getattr(fb, name)))

        osc = get("oscChoices")
        return {
            "kinds": get("kindChoices"),
            "targets": get("targetChoices"),
            "types": get("typeChoices"),
            "vjoy": get("vjoyChoices"),
            "logical": get("logicalChoices"),
            "osc": osc,
            "actions": get("actionChoices"),
            "showUnder": [{"value": "", "text": SHOW_UNDER_NONE}, *osc],
        }

    def _editor(self) -> dict:
        draft = self._fb_draft
        if draft is None:
            return {}
        entry = osc_feedback_model._entry(draft)
        return {
            "key": feedback_key(self._fb_id),
            "id": self._fb_id,
            **{
                name: entry[name]
                for name in (
                    "kind",
                    "device",
                    "input",
                    "action",
                    "target",
                    "address",
                    "min",
                    "max",
                    "type",
                    "offValue",
                    "onValue",
                    "showUnder",
                    "enabled",
                )
            },
            "dirty": draft != self._fb_saved,
            "error": self._fb_error,
            "note": (
                osc_feedback_model.ACTION_MISSING
                if action_missing(draft, self._fb_actions)
                else ""
            ),
            "choices": self._choices(),
        }

    @QtCore.Property(dict, notify=feedbackEditorChanged)
    def feedbackEditor(self) -> dict:
        return self._editor()

    def _refresh_editor(self) -> None:
        """After a write (Undo, another window): an unchanged draft follows
        the stored row; a deleted row closes the editor."""
        if not self._fb_id:
            return
        stored = self._stored_row(self._fb_id)
        if stored is None:
            self.endFeedback()
            return
        if stored != self._fb_saved:
            if self._fb_draft == self._fb_saved:
                self._fb_draft = copy.deepcopy(stored)
            self._fb_saved = stored
        self.feedbackEditorChanged.emit()

    @QtCore.Slot(str, result="QVariantMap")
    def beginFeedback(self, key: str) -> dict:
        """Opens the editor on a feedback row; {} when it is gone."""
        row_id = feedback_id(key)
        stored = self._stored_row(row_id) if row_id else None
        if stored is None:
            self.endFeedback()
            return {}
        self._fb_id = row_id
        self._fb_saved = stored
        self._fb_draft = copy.deepcopy(stored)
        self._fb_error = ""
        self._fb_actions = stateful_labels(self._profile())
        self.feedbackEditorChanged.emit()
        return self._editor()

    @QtCore.Slot(str, "QVariant", result=str)
    def setFeedbackField(self, name: str, value: object) -> str:
        """Changes one field of the draft; "" or why it was refused."""
        if self._fb_draft is None:
            return "No feedback row is open."
        draft = copy.deepcopy(self._fb_draft)
        why = set_field(draft, str(name), value)
        if not why:
            self._fb_draft = draft
        self._fb_error = why
        self.feedbackEditorChanged.emit()
        return why

    @QtCore.Slot(result=bool)
    def feedbackDirty(self) -> bool:
        return self._fb_draft is not None and self._fb_draft != self._fb_saved

    @QtCore.Slot(result=bool)
    def commitFeedback(self) -> bool:
        """Writes the draft as one Undo step; True when written or when
        nothing changed."""
        draft = self._fb_draft
        if draft is None:
            return False
        if draft == self._fb_saved:
            return True
        why = osc_feedback_model.check_address(draft["address"])
        if why:
            self._fb_error = why
            self.feedbackEditorChanged.emit()
            return False
        new = copy.deepcopy(draft)

        def edit(rows: list[dict], index: int) -> str:
            rows[index] = new
            return "done"

        if not self._edit_row(feedback_key(self._fb_id), edit, "Edit Feedback"):
            if self._stored_row(self._fb_id) is None:
                self._say("That feedback row no longer exists.")
                self.endFeedback()
            return False
        stored = self._stored_row(self._fb_id)
        self._fb_saved = stored
        self._fb_draft = copy.deepcopy(stored)
        self._fb_error = ""
        self.feedbackEditorChanged.emit()
        return True

    @QtCore.Slot()
    def discardFeedback(self) -> None:
        if self._fb_saved is None:
            return
        self._fb_draft = copy.deepcopy(self._fb_saved)
        self._fb_error = ""
        self.feedbackEditorChanged.emit()

    @QtCore.Slot()
    def endFeedback(self) -> None:
        if not self._fb_id and self._fb_draft is None:
            return
        self._fb_id = ""
        self._fb_saved = None
        self._fb_draft = None
        self._fb_error = ""
        self.feedbackEditorChanged.emit()
