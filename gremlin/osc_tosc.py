# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Reads a TouchOSC (Mk2) layout file (.tosc) into OSC input rows (09 S162).

The file structure comes from tosclib (AlbertoV5/tosclib on GitHub) and
editor-made sample files: XML with a <lexml> root holding <node type="...">
elements with <properties>, <values>, <messages> and <children>. The
control types, the path/argument partials (CONSTANT, INDEX, VALUE,
PROPERTY), the control values and the scaleMin/scaleMax scaling are
confirmed in Hexler's TouchOSC manual. That the whole file is
zlib-compressed comes from third-party sources only (Hexler does not
document it). INDEX is taken as the control's 1-based position in its
parent (the manual's script index; NOT VERIFIED for partials).

Pure: reads the one file, no Qt, no network. Each row is the settings dict
osc_device_model.add_input takes, plus a display-only "label"."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
import zlib
from typing import Any

from gremlin.error import GremlinError

MAX_BYTES = 10 * 1024 * 1024

# Control kind -> (input mode, display name); kinds left out are skipped.
# An encoder sends its absolute 0..1 position, so it is an axis (TC4).
_KINDS: dict[str, tuple[str, str]] = {
    "FADER": ("axis", "Fader"),
    "RADIAL": ("axis", "Radial"),
    "ENCODER": ("axis", "Encoder"),
    "XY": ("axis", "XY"),
    "RADAR": ("axis", "Radar"),
    "BUTTON": ("button", "Button"),
    "RADIO": ("change", "Radio"),
    "PAGER": ("change", "Pager"),
}
# Two axes, one per value: x is P1, y is P2.
_TWO_AXES = ("XY", "RADAR")
# Containers: their own message is a template for the children (TC1).
_CONTAINERS = ("GROUP", "GRID")
# Display-only kinds: skipped with a note.
_NOT_INPUTS = ("LABEL", "TEXT", "BOX")

_UNSAFE = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


def _read(path: str | os.PathLike[str]) -> bytes:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError as err:
        raise GremlinError(f"Can't read the TouchOSC file: {err}") from None
    if len(raw) > MAX_BYTES:
        raise GremlinError("The TouchOSC file is too big (over 10 MB).")
    inflate = zlib.decompressobj()
    try:
        data = inflate.decompress(raw, MAX_BYTES + 1)
    except zlib.error:
        raise GremlinError("Not a TouchOSC layout (.tosc) file.") from None
    if len(data) > MAX_BYTES or inflate.unconsumed_tail:
        raise GremlinError("The TouchOSC layout is too big (over 10 MB unpacked).")
    return data


def _parse_xml(data: bytes) -> ET.Element:
    # No DTD means no entity expansion (billion laughs, external entities).
    if _UNSAFE.search(data):
        raise GremlinError("The TouchOSC layout holds a DOCTYPE or ENTITY; refused.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as err:
        raise GremlinError(f"The TouchOSC layout is not valid XML: {err}") from None
    if root.tag != "lexml":
        raise GremlinError("Not a TouchOSC layout (.tosc) file.")
    return root


def _text(elem: ET.Element | None, tag: str) -> str:
    child = elem.find(tag) if elem is not None else None
    return (child.text or "").strip() if child is not None else ""


def _float(elem: ET.Element, tag: str, default: float) -> float:
    try:
        return float(_text(elem, tag))
    except ValueError:
        return default


def _properties(node: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for prop in node.findall("./properties/property"):
        key = _text(prop, "key")
        if key:
            out[key] = _text(prop, "value")
    return out


class _Node:
    def __init__(self, elem: ET.Element, parent: _Node | None, index: int) -> None:
        self.elem = elem
        self.parent = parent
        # 1-based position in the parent's children, 0 for the top node.
        self.index = index
        self.kind = (elem.get("type") or "").upper()
        self.props = _properties(elem)
        self.name = self.props.get("name", "")

    def lookup(self, ref: str) -> str | None:
        """A PROPERTY partial's value: "name", "parent.name", ..."""
        node: _Node | None = self
        parts = ref.split(".")
        while len(parts) > 1 and parts[0] == "parent":
            node = node.parent if node is not None else None
            parts = parts[1:]
        if node is None or len(parts) != 1:
            return None
        return node.props.get(parts[0])


def _resolve_path(node: _Node, osc: ET.Element) -> str | None:
    """The message's address, None when it is built at run time."""
    partials = osc.findall("./path/partial")
    if not partials:
        # The editor writes even the default path as partials; an empty
        # one has no documented meaning.
        return None
    out = []
    for partial in partials:
        kind = _text(partial, "type").upper()
        value = _text(partial, "value")
        if kind == "CONSTANT":
            out.append(value)
        elif kind == "PROPERTY":
            resolved = node.lookup(value)
            if resolved is None:
                return None
            out.append(resolved)
        elif kind == "INDEX":
            out.append(str(node.index))
        else:
            return None
    path = "".join(out)
    return path if path.startswith("/") and len(path) > 1 else None


def _value_args(osc: ET.Element) -> list[tuple[int, str, float, float]]:
    """(argument index, value name, scaleMin, scaleMax) per VALUE argument."""
    out = []
    for index, partial in enumerate(osc.findall("./arguments/partial")):
        if _text(partial, "type").upper() == "VALUE":
            out.append(
                (
                    index,
                    _text(partial, "value"),
                    _float(partial, "scaleMin", 0.0),
                    _float(partial, "scaleMax", 1.0),
                )
            )
    return out


def _rows_for(
    node: _Node, osc: ET.Element, address: str, title: str
) -> tuple[list[dict[str, Any]], str | None]:
    mode, display = _KINDS[node.kind]
    args = _value_args(osc)
    label = f"{title} ({display})"
    if node.kind in _TWO_AXES:
        rows = []
        for index, value, low, high in args:
            point = {"x": "P1", "y": "P2"}.get(value)
            if point is None:
                continue
            rows.append(
                {
                    "address": address,
                    "mode": "axis",
                    "source": index,
                    "range_min": low,
                    "range_max": high,
                    "label": f"{title} ({display} {point})",
                }
            )
        if not rows:
            return [], f"{title} ({display}): no x or y value in its message, skipped"
        return rows, None
    wanted = "page" if node.kind == "PAGER" else "x"
    arg = next((a for a in args if a[1] == wanted), args[0] if args else None)
    row: dict[str, Any] = {
        "address": address,
        "mode": mode,
        "source": arg[0] if arg else 0,
        "label": label,
    }
    if mode == "axis":
        if arg is None:
            return [], f"{label}: no value in its message, skipped"
        row["range_min"], row["range_max"] = arg[2], arg[3]
    return [row], None


def _walk(node: _Node, rows: list[dict[str, Any]], skipped: list[str]) -> None:
    title = node.name or node.kind.lower()
    if node.kind in _KINDS:
        sends = [
            osc
            for osc in node.elem.findall("./messages/osc")
            if _text(osc, "enabled") == "1" and _text(osc, "send") == "1"
        ]
        if not sends:
            skipped.append(f"{title} ({node.kind}): sends no OSC, skipped")
        for osc in sends:
            address = _resolve_path(node, osc)
            if address is None:
                skipped.append(
                    f"{title} ({node.kind}): OSC path is built at run time "
                    "or can't be read, skipped"
                )
                continue
            new_rows, note = _rows_for(node, osc, address, title)
            rows.extend(new_rows)
            if note:
                skipped.append(note)
    elif node.kind in _NOT_INPUTS:
        skipped.append(f"{title} ({node.kind}): not an input, skipped")
    elif node.kind not in _CONTAINERS:
        skipped.append(f"{title} ({node.kind or '?'}): unknown control, skipped")
    # Pager pages are GROUP children, walked like any container's.
    for index, child in enumerate(node.elem.findall("./children/node"), start=1):
        _walk(_Node(child, node, index), rows, skipped)


def parse(path: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Rows (add_input settings plus "label") and skipped notes for one
    .tosc file; GremlinError when the file is refused."""
    root = _parse_xml(_read(path))
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for elem in root.findall("./node"):
        _walk(_Node(elem, None, 0), rows, skipped)
    return rows, skipped
