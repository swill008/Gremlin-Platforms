# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid

from PySide6 import QtCore

import dill
import gremlin.ui.type_aliases as ta
from gremlin import event_handler, shared_state
from gremlin.modules import hardware, output
from gremlin.modules.ids import guid_key
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.types import InputType

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


import re

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)


def _extract_uuid(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, uuid.UUID):
        return str(value).lower()
    nested = getattr(value, "uuid", None)
    if isinstance(nested, uuid.UUID):
        return str(nested).lower()
    text = str(value or "")
    hit = _UUID_RE.search(text)
    if hit:
        return hit.group(0).lower()
    return text.strip().strip("{}").lower()


def _hat_xy(direction: object) -> tuple[int, int]:
    if direction is None:
        return (0, 0)
    raw = getattr(direction, "value", direction)
    if isinstance(raw, (tuple, list)) and len(raw) >= 2:
        try:
            return (int(raw[0]), int(raw[1]))
        except (TypeError, ValueError):
            return (0, 0)
    return (0, 0)


@ta.QmlElement
class DeviceLiveState(QtCore.QObject):
    """Live axis/button/hat values for the current physical device tab."""

    guidChanged = QtCore.Signal()
    stampChanged = QtCore.Signal()
    lockedChanged = QtCore.Signal()
    drivenChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._device = None
        self._device_uuid = None
        self._guid = ""
        self._locked = False
        self._live_while_active = False
        self._vjoy_id = 0
        self._device_name = ""
        self._driven = False
        self._kinds: list[str] = []
        self._values: list[float] = []
        self._hat_x: list[int] = []
        self._hat_y: list[int] = []
        self._axis_rows: dict[int, int] = {}
        self._stamp = 0
        self._axis_dirty = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush_axes)
        self._poll = QtCore.QTimer(self)
        self._poll.setInterval(33)
        self._poll.timeout.connect(self._poll_output)
        # Claimed inputs only: the input module feed, not raw hardware.
        InputModuleRuntime().event.connect(self._on_event)

    def _get_guid(self) -> str:
        return self._guid

    def _get_locked(self) -> bool:
        if self._live_while_active:
            return False
        return self._locked or shared_state.runtime_active()

    def _get_live_while_active(self) -> bool:
        return self._live_while_active

    def _get_driven(self) -> bool:
        if not self._live_while_active:
            return True
        return bool(self._driven)

    def _set_driven(self, value: bool) -> None:
        flag = bool(value)
        if flag == self._driven:
            return
        self._driven = flag
        self.drivenChanged.emit()
        self._bump()

    def _set_live_while_active(self, value: bool) -> None:
        flag = bool(value)
        if flag == self._live_while_active:
            return
        self._live_while_active = flag
        self.lockedChanged.emit()
        self._sync_poll()

    def _get_device_name(self) -> str:
        return self._device_name

    def _set_device_name(self, name: str) -> None:
        text = str(name or "")
        if text == self._device_name:
            return
        self._device_name = text
        self._resolve_vjoy()
        self._sync_poll()

    def _set_locked(self, value: bool) -> None:
        flag = bool(value)
        if flag == self._locked:
            return
        self._locked = flag
        self.lockedChanged.emit()

    def _clear(self) -> None:
        self._device = None
        self._device_uuid = None
        self._guid = ""
        self._vjoy_id = 0
        self._kinds = []
        self._values = []
        self._hat_x = []
        self._hat_y = []
        self._axis_rows = {}
        self._sync_poll()
        self.guidChanged.emit()
        self._bump()

    def _set_guid(self, guid: str) -> None:
        incoming = _extract_uuid(guid)
        if not incoming or incoming in ("unknown", str(dill.UUID_Invalid).lower()):
            self._clear()
            return
        if self._guid == incoming and self._device is not None:
            return
        try:
            self._device = hardware.device_info(guid)
            self._device_uuid = uuid.UUID(incoming)
            self._guid = incoming
        except Exception:
            self._clear()
            return
        self._kinds = []
        self._values = []
        self._hat_x = []
        self._hat_y = []
        self._axis_rows = {}
        for i in range(self._device.axis_count):
            self._kinds.append("axis")
            self._values.append(0.0)
            self._hat_x.append(0)
            self._hat_y.append(0)
            try:
                axis_id = int(self._device.axis_map[i].axis_index)
            except Exception:
                axis_id = i + 1
            self._axis_rows[axis_id] = i
        lookup = getattr(self._device, "axis_lookup", None) or {}
        for axis_id, position in lookup.items():
            try:
                row = int(position) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= row < self._device.axis_count:
                self._axis_rows[int(axis_id)] = row
        for _ in range(self._device.button_count):
            self._kinds.append("button")
            self._values.append(0.0)
            self._hat_x.append(0)
            self._hat_y.append(0)
        for _ in range(self._device.hat_count):
            self._kinds.append("hat")
            self._values.append(0.0)
            self._hat_x.append(0)
            self._hat_y.append(0)
        self._resolve_vjoy()
        self.guidChanged.emit()
        self._bump()
        self._sync_poll()

    def _resolve_vjoy(self) -> None:
        # Fresh DILL DeviceSummary.vjoy_id is not the feeder id. Resolve like
        # output_modules: name "vJoy N" and bound GUID.
        self._vjoy_id = 0
        try:
            from gremlin.modules.registry import resolve_vjoy_id
            self._vjoy_id = int(resolve_vjoy_id(self._device_name, self._guid) or 0)
        except Exception:
            self._vjoy_id = 0
        if self._vjoy_id:
            return
        from gremlin.modules import registry

        if "vjoy" in (self._device_name or "").lower():
            self._vjoy_id = registry.vjoy_id_from_name(self._device_name)
            return
        target = guid_key(self._guid)
        if not target:
            return
        try:
            from gremlin import device_initialization
            for vdev in device_initialization.vjoy_devices():
                if guid_key(vdev.device_guid) == target:
                    self._vjoy_id = int(vdev.vjoy_id)
                    return
        except Exception:
            self._vjoy_id = 0

    def _sync_poll(self) -> None:
        if self._live_while_active:
            if not self._poll.isActive():
                self._poll.start()
            self._poll_output()
        else:
            self._poll.stop()
            self._set_driven(False)

    def _gremlin_running(self) -> bool:
        try:
            return bool(event_handler.EventListener().gremlin_active)
        except Exception:
            return False

    def _poll_output(self) -> None:
        """vJoy dest Configuration live: this output module's feeder only."""
        if not self._live_while_active:
            return
        if not self._vjoy_id:
            self._resolve_vjoy()
        running = self._gremlin_running()
        if not running:
            self._set_driven(False)
            return
        # Read through the vJoy output module: claimed outputs only, and only
        # while Gremlin holds the device.
        if not output.vjoy_held(self._vjoy_id):
            self._set_driven(False)
            return
        self._set_driven(True)
        if not self._values:
            return
        state = output.vjoy_state(self._vjoy_id, hats=True)
        changed = False
        axis_count = int(self._device.axis_count) if self._device is not None else 0
        button_count = int(self._device.button_count) if self._device is not None else 0
        for i, kind in enumerate(self._kinds):
            if kind == "axis":
                try:
                    axis_id = int(self._device.axis_map[i].axis_index)
                except Exception:
                    axis_id = i + 1
                value = float(state.get(("axis", axis_id), 0.0))
            elif kind == "button":
                value = float(state.get(("button", i - axis_count + 1), 0.0))
            elif kind == "hat":
                hat_id = i - axis_count - button_count + 1
                hx, hy = _hat_xy(state.get(("hat", hat_id)))
                if i < len(self._hat_x) and (self._hat_x[i], self._hat_y[i]) != (hx, hy):
                    self._hat_x[i] = hx
                    self._hat_y[i] = hy
                    changed = True
                value = 0.0 if (hx, hy) == (0, 0) else 1.0
            else:
                continue
            if abs(self._values[i] - value) > 0.002:
                self._values[i] = value
                changed = True
        if changed:
            self._bump()

    def _get_stamp(self) -> int:
        return self._stamp

    def _bump(self) -> None:
        self._stamp += 1
        self.stampChanged.emit()

    def _flush_axes(self) -> None:
        if self._get_locked():
            self._axis_dirty = False
            return
        if self._axis_dirty:
            self._axis_dirty = False
            self._bump()

    def _axis_row(self, identifier: object) -> int | None:
        try:
            key = int(identifier)
        except (TypeError, ValueError):
            return None
        return self._axis_rows.get(key)

    def _axis_value(self, event: event_handler.Event) -> float | None:
        raw = event.value
        if raw is None:
            raw = getattr(event, "raw_value", None)
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if value > 1.5 or value < -1.5:
            value = max(-1.0, min(1.0, value / 32767.0))
        else:
            value = max(-1.0, min(1.0, value))
        return value

    def _event_is_this_device(self, event: event_handler.Event) -> bool:
        if self._device_uuid is not None:
            raw = event.device_guid
            if isinstance(raw, uuid.UUID) and raw == self._device_uuid:
                return True
            nested = getattr(raw, "uuid", None)
            if isinstance(nested, uuid.UUID) and nested == self._device_uuid:
                return True
        return guid_key(event.device_guid) == guid_key(self._guid)

    def _on_event(self, event: event_handler.Event) -> None:
        if self._live_while_active:
            return
        if self._get_locked():
            return
        if self._device is None or self._device_uuid is None:
            return
        if not self._event_is_this_device(event):
            return
        if event.event_type == InputType.JoystickAxis:
            row = self._axis_row(event.identifier)
            if row is None:
                return
            value = self._axis_value(event)
            if value is None:
                return
            self._values[row] = value
            self._axis_dirty = True
            if not self._timer.isActive():
                self._timer.start()
            return
        if event.event_type == InputType.JoystickButton:
            row = self._device.axis_count + event.identifier - 1
            if 0 <= row < len(self._values):
                self._values[row] = 1.0 if event.is_pressed else 0.0
                self._bump()
            return
        if event.event_type == InputType.JoystickHat:
            row = (
                self._device.axis_count
                + self._device.button_count
                + event.identifier
                - 1
            )
            if 0 <= row < len(self._values):
                hx, hy = _hat_xy(event.value)
                self._hat_x[row] = hx
                self._hat_y[row] = hy
                self._values[row] = 0.0 if (hx, hy) == (0, 0) else 1.0
                self._bump()

    @QtCore.Slot(int, result=str)
    def kindAt(self, index: int) -> str:
        if 0 <= index < len(self._kinds):
            return self._kinds[index]
        return ""

    @QtCore.Slot(int, result=float)
    def valueAt(self, index: int) -> float:
        if 0 <= index < len(self._values):
            return self._values[index]
        return 0.0

    @QtCore.Slot(int, result=int)
    def hatXAt(self, index: int) -> int:
        if 0 <= index < len(self._hat_x):
            return int(self._hat_x[index])
        return 0

    @QtCore.Slot(int, result=int)
    def hatYAt(self, index: int) -> int:
        if 0 <= index < len(self._hat_y):
            return int(self._hat_y[index])
        return 0

    guid = QtCore.Property(str, fget=_get_guid, fset=_set_guid, notify=guidChanged)
    locked = QtCore.Property(bool, fget=_get_locked, fset=_set_locked, notify=lockedChanged)
    liveWhileActive = QtCore.Property(
        bool,
        fget=_get_live_while_active,
        fset=_set_live_while_active,
        notify=lockedChanged,
    )
    deviceName = QtCore.Property(
        str,
        fget=_get_device_name,
        fset=_set_device_name,
        notify=guidChanged,
    )
    driven = QtCore.Property(bool, fget=_get_driven, notify=drivenChanged)
    stamp = QtCore.Property(int, fget=_get_stamp, notify=stampChanged)


import gremlin.ui.input_pairing  # noqa: F401
import gremlin.ui.pair_live  # noqa: F401
import gremlin.ui.viewer_devices  # noqa: F401
import gremlin.ui.xbox_viewer  # noqa: F401
