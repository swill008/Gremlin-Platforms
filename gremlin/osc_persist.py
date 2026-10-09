# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""OSC references and labels.

OSC's inputs live in OSC's module file (D-09-OSC-FILE); every reference
stores the input's permanent id (uid). resolve_osc_reference finds what a
saved reference points at now. osc_label is the one "OSC - <address>"
label (InputIdentifier and the OSC page use it); this module puts it on
InputIdentifier for the OSC GUID.
"""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore

from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.types import InputType
from gremlin.ui.device import InputIdentifier

_orig_label = getattr(InputIdentifier.label, "fget", None)
_orig_linear_index = getattr(InputIdentifier.linear_index, "fget", None)


def osc_rows() -> Any:  # noqa: ANN401 - gremlin.osc_rows.OscRows
    """The shared OSC rows (OscDevice().rows)."""
    return OscDevice().rows


def resolve_osc_reference(
    uid: str | None, input_type: InputType | None, input_id: int | None
) -> tuple[Any, str | None]:
    """Current (type, number) and uid of a saved OSC reference.

    A uid wins; one OSC's file doesn't have is missing (None), never
    re-targeted by number (D-09-OSC-FILE 2). No uid (old data): the old
    profile's load map (osc_device_file.current_uid_map, keyed by the XML
    type name or the enum name), then type+number. (None, None): nothing
    matches.
    """
    rows = osc_rows()
    if uid:
        return rows.identifier_of_uid(uid), uid
    if input_type is None or input_id is None:
        return None, None
    try:
        from gremlin import osc_device_file

        remap = getattr(osc_device_file, "current_uid_map", None) or {}
    except ImportError:
        remap = {}
    for key in (
        (InputType.to_string(input_type), int(input_id)),
        (input_type.name, int(input_id)),
    ):
        mapped = remap.get(key)
        if mapped:
            return rows.identifier_of_uid(mapped), mapped
    row = rows.by_number(input_type, int(input_id))
    if row is None:
        return None, None
    return row.identifier, row.uid


def osc_label(input_type: InputType, input_id: int) -> str:
    """"OSC - <address>" for an OSC input by its number; one that isn't in
    OSC's file: "OSC - Button 3"."""
    row = osc_rows().by_number(input_type, int(input_id))
    if row is not None:
        return f"OSC - {row.label}"
    return f"OSC - {InputType.to_string(input_type).capitalize()} {input_id}"


def osc_linear_index(input_id: int) -> int:
    return max(int(input_id) - 1, 0)


def _label(self) -> str:
    if getattr(self, "isValid", False) and self.device_guid == OSC_DEVICE_UUID:
        return osc_label(self.input_type, int(self.input_id))
    if _orig_label is not None:
        return _orig_label(self)
    return "No input"


def _linear_index(self) -> int:
    if getattr(self, "isValid", False) and self.device_guid == OSC_DEVICE_UUID:
        return osc_linear_index(self.input_id)
    if _orig_linear_index is not None:
        return _orig_linear_index(self)
    return max(int(getattr(self, "input_id", 1) or 1) - 1, 0)


if _orig_label is not None:
    InputIdentifier.label = QtCore.Property(
        str, _label, notify=InputIdentifier.changed
    )
if _orig_linear_index is not None:
    InputIdentifier.linear_index = property(_linear_index)
