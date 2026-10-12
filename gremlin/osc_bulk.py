# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, trace
from gremlin.osc import OscDevice, OscRuntime
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_DEBOUNCE_S = 0.3


def _as_dict(value: object) -> dict | None:
    if hasattr(value, "toVariant"):
        value = value.toVariant()  # type: ignore[union-attr]
    return dict(value) if isinstance(value, dict) else None


def start_bulk(model: object, settings: object) -> None:
    """Bulk capture: every new address becomes an input with the Add
    window's settings (D-09-OSC-INPUT). settings is the window's map; an
    old caller's type string ("Button"/"Axis") still works."""
    setattr(model, "_capture_only", True)
    setattr(model, "_bulk", True)
    as_map = _as_dict(settings)
    if as_map is not None:
        setter = getattr(model, "setCaptureSettings", None)
        if setter is not None:
            setter(as_map)
        setattr(model, "_bulk_settings", as_map)
        kind = "Axis" if as_map.get("mode") == "axis" else "Button"
        setattr(model, "_bulk_mode", kind)
    else:
        setattr(model, "_bulk_settings", None)
        setattr(model, "_bulk_mode", str(settings or "") or "Button")
    setattr(model, "_last_bulk_addr", "")
    setattr(model, "_last_bulk_time", 0.0)
    setattr(model, "_bulk_skipped", 0)
    OscRuntime().listen_bulk(owner=model)


def bulk_skipped(model: object) -> int:
    """Addresses this Bulk capture skipped: an input already answers them."""
    return int(getattr(model, "_bulk_skipped", 0))


def _answered(model: object, address: str, payload: tuple) -> bool:
    """An existing input (exact or pattern) already answers this address
    (S151). A data-mode capture adds one input per value, so there only an
    input answering these values counts."""
    rows = OscDevice().rows
    settings = getattr(model, "_bulk_settings", None) or {}
    if settings.get("cmd_mode") == "data":
        return bool(rows.matches(address, payload))
    return bool(rows.answered_by(address))


def _create_captured(model: object, address: str, payload: tuple) -> None:
    settings = getattr(model, "_bulk_settings", None)
    create = getattr(model, "createConfiguredInput", None)
    if settings is None or create is None:
        model.createMappedInput(  # type: ignore[attr-defined]
            getattr(model, "_bulk_mode", "Button"), address
        )
        return
    data = [str(a) for a in payload] if settings.get("cmd_mode") == "data" else []
    create(dict(settings, address=address, data=data))


def on_bulk_learned(model: object, address: str, payload: tuple) -> None:
    """A message heard while model's Bulk capture listens (the model has
    checked it owns the Listen): a repeat within the debounce or an address
    an input already answers is skipped; otherwise it becomes an input."""
    now = clock.monotonic()
    key = ((address or "").casefold(), payload)
    if key == getattr(model, "_last_bulk_addr", "") and (
        now - getattr(model, "_last_bulk_time", 0.0) < _DEBOUNCE_S
    ):
        trace.osc(
            "setup",
            f"Bulk skipped {address} (repeat within {_DEBOUNCE_S:g} s)",
            rate=True,
            key=f"bulk-repeat {address}",
        )
        return
    setattr(model, "_last_bulk_addr", key)
    setattr(model, "_last_bulk_time", now)
    if _answered(model, address, payload):
        setattr(model, "_bulk_skipped", bulk_skipped(model) + 1)
        # Trace only (E6): one line per skip filled the system log.
        trace.osc(
            "setup",
            f"Bulk skipped {address} (already answered)",
            rate=True,
            key=f"bulk-answered {address}",
        )
        return
    shown = ", ".join(str(item) for item in payload)
    getattr(model, "commandCaptured").emit(address, shown)
    _create_captured(model, address, payload)


@ta.QmlElement
class OscBulkCapture(QtCore.QObject):
    @QtCore.Slot("QVariant", "QVariant")
    def start(self, model: object, settings: object) -> None:
        if model is None:
            return
        start_bulk(model, settings)
