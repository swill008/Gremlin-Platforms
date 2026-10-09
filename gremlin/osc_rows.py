# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC's address list: one row per input, saved in OSC's module file
(decision D-09-OSC-FILE) with its per-input settings (D-09-OSC-INPUT).

Pure data: no file access, no Qt. Every row has a permanent random id (uid);
its number is a display name (lowest free per type)."""

from __future__ import annotations

import collections
import dataclasses
import math
import uuid
from typing import Any

from gremlin.error import GremlinError
from gremlin.types import InputType

MODES = ("button", "axis", "change")
CMD_MODES = ("message", "data")
MAX_DELAY_MS = 10000

Identifier = collections.namedtuple("Identifier", ["type", "id"])

_DEFAULTS: dict[str, Any] = {
    "mode": "button",
    "cmd_mode": "message",
    "data": [],
    "source": 0,
    "range_min": 0.0,
    "range_max": 1.0,
    "trigger": None,
    "delay_ms": None,
}
SETTING_KEYS = tuple(_DEFAULTS)


@dataclasses.dataclass
class OscRow:
    uid: str
    input_type: InputType
    input_id: int
    label: str
    mode: str = "button"
    cmd_mode: str = "message"
    data: list[str] = dataclasses.field(default_factory=list)
    source: int = 0
    range_min: float = 0.0
    range_max: float = 1.0
    trigger: bool | None = None
    delay_ms: int | None = None

    @property
    def identifier(self) -> Identifier:
        return Identifier(self.input_type, self.input_id)

    @property
    def address(self) -> str:
        return self.label

    def match_key(self) -> tuple:
        """Two rows with the same key would answer the same messages."""
        data: tuple = ()
        if self.cmd_mode == "data":
            data = tuple(_norm_value(v) for v in self.data)
        return (self.label.casefold(), self.cmd_mode, data, self.source)


def type_of_mode(mode: str) -> InputType:
    return InputType.JoystickAxis if mode == "axis" else InputType.JoystickButton


def check_address(label: object) -> str:
    """The address, trimmed; refuses blank ones and ones without a leading "/"."""
    text = str(label if label is not None else "").strip()
    if not text:
        raise GremlinError("An OSC address can't be blank")
    if not text.startswith("/"):
        raise GremlinError(f"An OSC address must start with \"/\": {text}")
    return text


def _norm_value(value: object) -> tuple[int, Any]:
    # Numbers compare as numbers ("1" == 1.0), everything else as text.
    if not isinstance(value, bool):
        try:
            if isinstance(value, str):
                number = float(value.strip())
            else:
                number = float(value)  # type: ignore[arg-type]
            if math.isfinite(number):
                return (0, number)
        except (TypeError, ValueError):
            pass
    return (1, str(value))


def check_settings(settings: dict[str, object]) -> dict[str, Any]:
    """Validated copies of the per-input settings given; refuses unknown keys."""
    unknown = set(settings) - set(SETTING_KEYS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise GremlinError(f"Unknown OSC input setting(s): {names}")
    out: dict[str, Any] = {}
    for key, raw in settings.items():
        value: Any = raw
        if key == "mode":
            if value not in MODES:
                raise GremlinError(f"Invalid OSC input mode: {value!r}")
        elif key == "cmd_mode":
            if value not in CMD_MODES:
                raise GremlinError(f"Invalid OSC command mode: {value!r}")
        elif key == "data":
            if value is None:
                value = []
            if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
                raise GremlinError("OSC data must be a list of values")
            value = [str(v) for v in value]
        elif key == "source":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise GremlinError(f"Invalid OSC value index: {value!r}")
        elif key in ("range_min", "range_max"):
            if isinstance(value, bool):
                raise GremlinError(f"Invalid OSC {key}: {value!r}")
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise GremlinError(f"Invalid OSC {key}: {value!r}") from None
            if not math.isfinite(value):
                raise GremlinError(f"Invalid OSC {key}: {value!r}")
        elif key == "trigger":
            if value is not None and not isinstance(value, bool):
                raise GremlinError(f"Invalid OSC trigger: {value!r}")
        elif key == "delay_ms":
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_DELAY_MS
            ):
                raise GremlinError(f"Invalid OSC delay: {value!r}")
        out[key] = value
    return out


class OscRows:
    """The OSC inputs; OscDevice() shows one shared instance."""

    def __init__(self) -> None:
        self._rows: list[OscRow] = []
        self._dirty = False
        self.load_warnings: list[str] = []

    # -- state ---------------------------------------------------------------

    @property
    def dirty(self) -> bool:
        """True when the rows changed since the last save or load."""
        return self._dirty

    def mark_saved(self) -> None:
        self._dirty = False

    def _changed(self) -> None:
        self._dirty = True

    def reset(self) -> None:
        if self._rows:
            self._changed()
        self._rows = []

    # -- lookups -------------------------------------------------------------

    def rows(self) -> list[OscRow]:
        return list(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def by_uid(self, uid: str) -> OscRow | None:
        for row in self._rows:
            if row.uid == uid:
                return row
        return None

    def by_number(self, input_type: InputType, input_id: int) -> OscRow | None:
        for row in self._rows:
            if row.input_type == input_type and row.input_id == int(input_id):
                return row
        return None

    def uid_of(self, input_type: InputType, input_id: int) -> str | None:
        row = self.by_number(input_type, input_id)
        return row.uid if row is not None else None

    def identifier_of_uid(self, uid: str) -> Identifier | None:
        """The input's current type and number."""
        row = self.by_uid(uid)
        return row.identifier if row is not None else None

    def matches(self, address: str, args: tuple | list = ()) -> list[OscRow]:
        """Rows answering this message: same address (any case); a "data"
        row also needs the message's values to equal its data."""
        key = str(address or "").strip().casefold()
        values = [_norm_value(v) for v in (args or ())]
        found = []
        for row in self._rows:
            if row.label.casefold() != key:
                continue
            if row.cmd_mode == "data" and [_norm_value(v) for v in row.data] != values:
                continue
            found.append(row)
        return found

    # -- edits ---------------------------------------------------------------

    def _get(self, uid: str) -> OscRow:
        row = self.by_uid(uid)
        if row is None:
            raise GremlinError(f"No OSC input with id {uid}")
        return row

    def _lowest_free(self, input_type: InputType, skip: OscRow | None = None) -> int:
        used = {
            r.input_id
            for r in self._rows
            if r.input_type == input_type and r is not skip
        }
        number = 1
        while number in used:
            number += 1
        return number

    def _check_unique(self, candidate: OscRow, skip: OscRow | None = None) -> None:
        key = candidate.match_key()
        for row in self._rows:
            if row is not skip and row.match_key() == key:
                raise GremlinError(f"OSC address '{candidate.label}' already exists")

    def create(
        self,
        input_type: InputType,
        label: str,
        *,
        uid: str | None = None,
        input_id: int | None = None,
        **settings: object,
    ) -> OscRow:
        """Adds an input. Its mode follows input_type unless given (axis mode
        needs an axis); input_id is kept when free, else the lowest free."""
        if input_type not in (InputType.JoystickAxis, InputType.JoystickButton):
            raise GremlinError(f"OSC inputs must be axis or button, got {input_type}")
        address = check_address(label)
        values = dict(_DEFAULTS)
        values["data"] = []
        values["mode"] = "axis" if input_type == InputType.JoystickAxis else "button"
        values.update(check_settings(settings))
        if type_of_mode(values["mode"]) != input_type:
            raise GremlinError(f"OSC mode {values['mode']} doesn't fit {input_type}")
        if values["range_min"] == values["range_max"]:
            raise GremlinError("OSC range needs two different ends")
        if uid and self.by_uid(uid) is not None:
            raise GremlinError(f"OSC input id {uid} already exists")
        if input_id is None or self.by_number(input_type, input_id) is not None:
            input_id = self._lowest_free(input_type)
        row = OscRow(uid=uid or uuid.uuid4().hex, input_type=input_type,
                     input_id=int(input_id), label=address, **values)
        self._check_unique(row)
        self._rows.append(row)
        self._changed()
        return row

    def delete(self, uid: str) -> None:
        self._rows.remove(self._get(uid))
        self._changed()

    def set_label(self, uid: str, label: str) -> None:
        row = self._get(uid)
        address = check_address(label)
        if address == row.label:
            return
        self._check_unique(dataclasses.replace(row, label=address), skip=row)
        row.label = address
        self._changed()

    def update(self, uid: str, **settings: object) -> OscRow:
        """Changes per-input settings. A mode change to or from axis moves the
        input to the other type (lowest free number there; uid kept)."""
        row = self._get(uid)
        values = check_settings(settings)
        new = dataclasses.replace(row, **values)
        new.data = list(new.data)
        if new.range_min == new.range_max:
            raise GremlinError("OSC range needs two different ends")
        new_type = type_of_mode(new.mode)
        if new_type != row.input_type:
            new.input_type = new_type
            new.input_id = self._lowest_free(new_type, skip=row)
        self._check_unique(new, skip=row)
        if new == row:
            return row
        for field in dataclasses.fields(OscRow):
            setattr(row, field.name, getattr(new, field.name))
        self._changed()
        return row

    # -- file format ---------------------------------------------------------

    def to_dict(self) -> dict:
        """The rows as stored in OSC's module file ("inputs" key)."""
        return {
            "inputs": [
                {
                    "uid": row.uid,
                    "type": InputType.to_string(row.input_type),
                    "id": row.input_id,
                    "label": row.label,
                    "mode": row.mode,
                    "cmd_mode": row.cmd_mode,
                    "data": list(row.data),
                    "source": row.source,
                    "range_min": row.range_min,
                    "range_max": row.range_max,
                    "trigger": row.trigger,
                    "delay_ms": row.delay_ms,
                }
                for row in self._rows
            ]
        }

    def load_dict(self, data: dict) -> None:
        """Replaces the rows with a to_dict() layout, then counts as saved.
        Entries that can't be read are skipped and named in load_warnings."""
        self._rows = []
        self.load_warnings = []
        for entry in (data or {}).get("inputs", []) or []:
            try:
                kind = entry.get("type", "button")
                if isinstance(kind, str):
                    kind = InputType.to_enum(kind)
                settings = {k: entry[k] for k in SETTING_KEYS if k in entry}
                if "mode" in settings and type_of_mode(settings["mode"]) != kind:
                    kind = type_of_mode(settings["mode"])
                raw_id = entry.get("id")
                self.create(
                    kind,
                    entry.get("label", ""),
                    uid=entry.get("uid") or None,
                    input_id=int(raw_id) if raw_id is not None else None,
                    **settings,
                )
            except (GremlinError, AttributeError, TypeError, ValueError) as error:
                self.load_warnings.append(f"OSC input skipped ({entry!r}): {error}")
        self.mark_saved()
