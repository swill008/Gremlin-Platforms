# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import time

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin.osc import OscRuntime
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from gremlin.ui.osc_device_model import OscDeviceManagementModel

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_DEBOUNCE_S = 0.3

_orig_learned = OscDeviceManagementModel._on_learned
_orig_cancel_model = OscDeviceManagementModel.cancelListen
_orig_listen_cmd = OscDeviceManagementModel.listenForCommand


def model_listen_for_command(
    self: OscDeviceManagementModel, settings: object = None
) -> None:
    # The Add window passes its settings (D-09-OSC-INPUT); old callers none.
    setattr(self, "_bulk", False)
    if settings is None:
        _orig_listen_cmd(self)
    else:
        _orig_listen_cmd(self, settings)  # type: ignore[call-arg]


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
    OscRuntime().listen_bulk(owner=model)


def model_cancel_listen(self: OscDeviceManagementModel) -> None:
    if not OscRuntime().listens_for(self):
        return  # another window's Listen keeps going
    setattr(self, "_bulk", False)
    _orig_cancel_model(self)


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


def model_on_learned(self: object, address: str, args: object) -> None:
    if not OscRuntime().listens_for(self):
        return  # another model's Listen (the OSC Monitor has its own)
    if getattr(self, "_bulk", False):
        payload = args if isinstance(args, tuple) else ()
        now = time.monotonic()
        key = ((address or "").casefold(), payload)
        if key == getattr(self, "_last_bulk_addr", "") and (
            now - getattr(self, "_last_bulk_time", 0.0) < _DEBOUNCE_S
        ):
            return
        setattr(self, "_last_bulk_addr", key)
        setattr(self, "_last_bulk_time", now)
        shown = ", ".join(str(item) for item in payload)
        getattr(self, "commandCaptured").emit(address, shown)
        _create_captured(self, address, payload)
        return
    _orig_learned(self, address, args)  # type: ignore[arg-type]


setattr(OscDeviceManagementModel, "listenForCommand", model_listen_for_command)
setattr(OscDeviceManagementModel, "cancelListen", model_cancel_listen)
setattr(OscDeviceManagementModel, "_on_learned", model_on_learned)


@ta.QmlElement
class OscBulkCapture(QtCore.QObject):
    @QtCore.Slot("QVariant", "QVariant")
    def start(self, model: object, settings: object) -> None:
        if model is None:
            return
        start_bulk(model, settings)
