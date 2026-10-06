# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Calibration stored on an input module and applied to the bound stick."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from gremlin.config import Configuration
from gremlin.device_initialization import physical_devices
from gremlin.modules import module_file, registry
from gremlin.modules.ids import guid_key

_DEFAULT = (-32768, 0, 0, 32767, True)
_SKIP_SLUGS = {"keyboard", "osc"}


def curve_problem(values: tuple[int, int, int, int, bool]) -> str:
    """Why a curve can't be used: "range" (low not below high), "center"
    (the center outside low..high), or "" when it can.

    Either one can make an axis divide by zero, so loading drops such a
    curve and saving refuses it (it was saved, then thrown away on load).
    """
    low, center_low, center_high, high, with_center = values
    if low >= high:
        return "range"
    if with_center and not low <= center_low <= center_high <= high:
        return "center"
    return ""


def _as_tuple(raw: object) -> tuple[int, int, int, int, bool] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) < 5:
        return None
    try:
        values = (int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]), bool(raw[4]))
    except (TypeError, ValueError):
        return None
    # A file edited by hand: the default is used instead.
    if curve_problem(values):
        return None
    return values


def _load(path: Path) -> dict:
    return registry.read_doc(path) or {}


def _source_modules() -> list[dict]:
    """The input modules of connected sticks, each as Module Setup and Run
    find it (registry.for_device: by the device it is bound to, else, when
    the stick has a new id, by its name). A stick found by name is marked
    "rebind": saving its calibration records its new id."""
    physical = {guid_key(dev.device_guid): dev for dev in physical_devices()}
    modules = [m for m in registry.inputs() if m.slug not in _SKIP_SLUGS]
    found: dict[str, tuple[Any, bool]] = {}
    for key, device in physical.items():
        try:
            module = registry.for_device(device.name, str(device.device_guid))
        except Exception:
            module = None
        # No module, or an output one: Run passes none of its inputs, so
        # there is nothing to calibrate (another file bound to the stick's
        # id used to be shown and saved instead).
        if module is None or module.is_output or module.slug in _SKIP_SLUGS:
            continue
        if module.slug in found:
            continue
        found[module.slug] = (device, guid_key(module.bound_guid) != key)
    rows = []
    for module in modules:
        if module.slug not in found:
            continue
        device, rebind = found[module.slug]
        rows.append(
            {
                "name": module.name or device.name,
                "slug": module.slug,
                "guid": str(device.device_guid),
                "path": module.path,
                "rebind": rebind,
            }
        )
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def module_for_slug(slug: str) -> dict | None:
    want = str(slug or "").strip().lower()
    if not want:
        return None
    for row in _source_modules():
        if row["slug"] == want:
            return row
    return None


def _module_for_guid(device_id: uuid.UUID) -> dict | None:
    want = guid_key(device_id)
    for row in _source_modules():
        if guid_key(row["guid"]) == want:
            return row
    return None


def _from_config(device_id: uuid.UUID, axis_id: int) -> tuple[int, int, int, int, bool]:
    stored = _as_tuple(Configuration().get_calibration(device_id, int(axis_id)))
    return stored if stored is not None else _DEFAULT


Curve = tuple[int, int, int, int, bool]


def _stored_axis(row: dict | None, axis_id: int) -> Curve | None:
    if row is None:
        return None
    saved = _load(row["path"]).get("calibration") or {}
    return _as_tuple(saved.get(str(int(axis_id))))


def values_for_device(device_id: uuid.UUID, axis_id: int) -> Curve:
    """The curve for a live stick. The module file wins; older program data is
    used until then."""
    stored = _stored_axis(_module_for_guid(device_id), axis_id)
    return stored if stored is not None else _from_config(device_id, axis_id)


def values_for_module(slug: str, device_id: uuid.UUID, axis_id: int) -> Curve:
    stored = _stored_axis(module_for_slug(slug), axis_id)
    return stored if stored is not None else _from_config(device_id, axis_id)


AxisData = tuple[int, int, int, int, bool]


def write_axis(slug: str, axis_id: int, data: AxisData) -> bool:
    return write_axes(slug, {axis_id: data})


def write_axes(slug: str, axes: dict[int, AxisData]) -> bool:
    """Write several axes' calibration in one save of the module file
    (Save All writes the file once, not once per axis)."""
    curves = {
        str(int(axis_id)): (
            int(data[0]), int(data[1]), int(data[2]), int(data[3]), bool(data[4])
        )
        for axis_id, data in axes.items()
    }
    # A curve the next load would drop is not written (the file would keep
    # values that are never used).
    if any(curve_problem(curve) for curve in curves.values()):
        return False
    row = module_for_slug(slug)
    if row is None or not axes:
        return False
    try:
        doc = module_file.load_for_update(row["path"])
    except module_file.ModuleFileDamaged as damaged:
        registry.trace("READ", "Calibration", "write_axis", row["path"], "damaged")
        module_file.report_refused(damaged)
        return False
    registry.trace("READ", "Calibration", "write_axis", row["path"], "ok")
    calibration = dict(doc.get("calibration") or {})
    for axis_id, curve in curves.items():
        calibration[axis_id] = list(curve)
    doc["calibration"] = calibration
    if row.get("rebind"):
        # Found by name: the stick's id changed. Record it, as Module Setup
        # does on save, so the next session finds it directly.
        doc["boundGuidLocal"] = row["guid"]
    try:
        module_file.write_json(row["path"], doc)
    except OSError:
        registry.trace("SAVE", "Calibration", "write_axis", row["path"], "error")
        return False
    registry.trace("SAVE", "Calibration", "write_axis", row["path"], "ok")
    return True
