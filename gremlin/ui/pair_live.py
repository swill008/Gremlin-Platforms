# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin import device_initialization, event_handler
from gremlin.modules import output
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.types import InputType
import gremlin.ui.type_aliases as ta
from gremlin.ui import input_pairing as pairing
from gremlin.modules.ids import guid_key

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


def _vjoy_ids_by_guid() -> dict[str, int]:
    """vJoy number for each vJoy device, keyed by its comparison GUID."""
    try:
        devices = list(device_initialization.vjoy_devices() or [])
    except Exception:
        return {}
    return {
        guid_key(dev.device_guid): int(dev.vjoy_id)
        for dev in devices
        if getattr(dev, "vjoy_id", 0)
    }


def _gremlin_running() -> bool:
    try:
        return bool(event_handler.EventListener().gremlin_active)
    except Exception:
        return False


@ta.QmlElement
class PairLiveThrottle(QtCore.QObject):
    stampChanged = QtCore.Signal()
    axisStampChanged = QtCore.Signal()
    buttonStampChanged = QtCore.Signal()
    hatStampChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._guid = ""
        self._uid = None
        self._hw_axis: dict[int, float] = {}
        self._hw_button: dict[int, float] = {}
        self._hw_hat: dict[int, float] = {}
        self._vj_axis: dict[tuple[str, int], float] = {}
        self._vj_button: dict[tuple[str, int], float] = {}
        self._stamp = 0
        self._axis_stamp = 0
        self._button_stamp = 0
        self._hat_stamp = 0
        self._watch = set()
        self._axis_dirty = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush)
        # vJoy values come from the vJoy output modules (claimed outputs only),
        # not from reading the vJoy device back through DirectInput.
        self._vjoy_ids: dict[str, int] = {}
        self._vjoy_poll = QtCore.QTimer(self)
        self._vjoy_poll.setInterval(50)
        self._vjoy_poll.timeout.connect(self._poll_vjoy)
        # Claimed inputs only: the input module feed, not raw hardware.
        InputModuleRuntime().event.connect(self._on_event)

    def _bump(self) -> None:
        self._stamp += 1
        self.stampChanged.emit()

    def _bump_axis(self) -> None:
        self._axis_stamp += 1
        self.axisStampChanged.emit()

    def _bump_button(self) -> None:
        self._button_stamp += 1
        self.buttonStampChanged.emit()

    def _flush(self) -> None:
        if self._axis_dirty:
            self._axis_dirty = False
            self._bump_axis()

    def _get_guid(self) -> str:
        return self._guid

    def _set_guid(self, guid: str) -> None:
        self._guid = str(guid or "")
        self._uid = pairing._guid(self._guid)
        self._hw_axis.clear()
        self._hw_button.clear()
        self._hw_hat.clear()
        self._vj_axis.clear()
        self._vj_button.clear()
        self._watch = {guid_key(self._guid)} if self._guid else set()
        watched: set[str] = set()
        for kind in (InputType.JoystickAxis, InputType.JoystickButton, InputType.JoystickHat):
            for row in pairing._mapped_rows(self._guid, kind):
                vg = guid_key(row.get("vjoyGuid", ""))
                if vg:
                    watched.add(vg)
        self._vjoy_ids = {
            key: vid for key, vid in _vjoy_ids_by_guid().items() if key in watched
        }
        if self._vjoy_ids:
            self._vjoy_poll.start()
        else:
            self._vjoy_poll.stop()
        self._bump()

    def _poll_vjoy(self) -> None:
        axes: dict[tuple[str, int], float] = {}
        buttons: dict[tuple[str, int], float] = {}
        if _gremlin_running():
            for key, vid in self._vjoy_ids.items():
                for (kind, ident), value in output.vjoy_state(vid).items():
                    target = axes if kind == "axis" else buttons
                    target[(key, ident)] = float(value)
        if axes != self._vj_axis:
            self._vj_axis = axes
            self._bump_axis()
        if buttons != self._vj_button:
            self._vj_button = buttons
            self._bump_button()

    def _on_event(self, event: event_handler.Event) -> None:
        ev = guid_key(event.device_guid)
        if ev not in self._watch:
            return
        is_hw = self._uid is not None and ev == guid_key(self._uid)
        if not is_hw:
            return
        if event.event_type == InputType.JoystickAxis:
            try:
                value = float(event.value)
                ident = int(event.identifier)
            except Exception:
                return
            self._hw_axis[ident] = value
            self._axis_dirty = True
            if not self._timer.isActive():
                self._timer.start()
            return
        if event.event_type == InputType.JoystickButton:
            try:
                ident = int(event.identifier)
                pressed = 1.0 if event.is_pressed else 0.0
            except Exception:
                return
            self._hw_button[ident] = pressed
            self._bump_button()
            return
        if event.event_type == InputType.JoystickHat:
            try:
                ident = int(event.identifier)
            except Exception:
                return
            val = getattr(event, "value", None)
            on = 0.0
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                try:
                    on = 1.0 if float(val[0]) or float(val[1]) else 0.0
                except Exception:
                    on = 1.0
            elif val not in (None, 0, 0.0, "center", "Center", "neutral"):
                on = 1.0
            self._hw_hat[ident] = on
            self._hat_stamp += 1
            self.hatStampChanged.emit()

    @QtCore.Slot(int, result=float)
    def axisValue(self, identifier: int) -> float:
        return float(self._hw_axis.get(int(identifier), 0.0))

    @QtCore.Slot(int, result=float)
    def buttonValue(self, identifier: int) -> float:
        return float(self._hw_button.get(int(identifier), 0.0))

    @QtCore.Slot(str, int, result=float)
    def vjoyAxisValue(self, vjoy_guid: str, identifier: int) -> float:
        return float(self._vj_axis.get((guid_key(vjoy_guid), int(identifier)), 0.0))

    @QtCore.Slot(str, int, result=float)
    def vjoyButtonValue(self, vjoy_guid: str, identifier: int) -> float:
        return float(self._vj_button.get((guid_key(vjoy_guid), int(identifier)), 0.0))

    @QtCore.Slot(int, result=float)
    def hatValue(self, identifier: int) -> float:
        return float(self._hw_hat.get(int(identifier), 0.0))

    def _get_stamp(self) -> int:
        return self._stamp

    def _get_axis_stamp(self) -> int:
        return self._axis_stamp

    def _get_button_stamp(self) -> int:
        return self._button_stamp

    def _get_hat_stamp(self) -> int:
        return self._hat_stamp

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid)
    stamp = QtCore.Property(int, fget=_get_stamp, notify=stampChanged)
    axisStamp = QtCore.Property(int, fget=_get_axis_stamp, notify=axisStampChanged)
    buttonStamp = QtCore.Property(int, fget=_get_button_stamp, notify=buttonStampChanged)
    hatStamp = QtCore.Property(int, fget=_get_hat_stamp, notify=hatStampChanged)
