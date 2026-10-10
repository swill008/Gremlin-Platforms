# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import functools
import inspect
import logging
import threading
import uuid
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
)

from PySide6 import QtCore

import dill
from gremlin import (
    clock,
    common,
    device_initialization,
    error,
    event_helpers,
    input_monitor,
    keyboard,
    mode_manager,
    run_scope,
    threads,
    trace,
    tree,
    util,
    windows_event_hook,
)
from gremlin.input_cache import (
    Joystick,
    Keyboard,
)
from gremlin.osc import OSC_DEVICE_UUID
from gremlin.types import (
    HatDirection,
    InputType,
    ScanCode,
)
from vigem.ids import is_vigem_xbox_summary

_TRACE_KINDS = {
    InputType.JoystickAxis: "axis",
    InputType.JoystickButton: "button",
    InputType.JoystickHat: "hat",
}


def trace_kind(event_type: object) -> str | None:
    """The Trace tab's name for a stick input type ("axis", "button",
    "hat"); None for anything else."""
    return _TRACE_KINDS.get(event_type)  # type: ignore[call-overload]


def trace_ticked(event: Event) -> tuple[str, int] | None:
    """(kind, index) of a stick input when tracing is on and it is ticked."""
    if not trace.enabled():
        return None
    kind = trace_kind(event.event_type)
    index = event.identifier
    if kind is None or not isinstance(index, int):
        return None
    if not trace.ticked(event.device_guid, kind, index):
        return None
    return kind, index

if TYPE_CHECKING:
    from gremlin.code_runner import CallbackObject


# A "repeat" press this long (s) after the key's last event cannot be
# Windows' auto-repeat (first repeat within 1 s, then several a second).
REPEAT_GAP_S = 1.2

# The mode of an event the hardware listener sends: the listener (the input
# layer) doesn't know the modes; EventHandler.process_event stamps the
# current mode on the main thread (GL-065).
NO_MODE = ""


class Event:
    """Represents a single event captured by the system.

    An event can originate from the keyboard or joystick which is
    indicated by the EventType value. The value of the event has to
    be interpreted based on the type of the event.

    Keyboard and JoystickButton events have a simple True / False
    value stored in is_pressed indicating whether or not the key has
    been pressed. For JoystickAxis the value indicates the axis value
    in the range [-1, 1] stored in the value field. JoystickHat events
    represent the hat position as a unit tuple (x, y) representing
    deflection in cartesian coordinates in the value field.

    The extended field is used for Keyboard events only to indicate
    whether or not the key's scan code is extended one.
    """

    def __init__(
        self,
        event_type: InputType,
        identifier: int | ScanCode,
        device_guid: uuid.UUID,
        mode: str,
        value: float | HatDirection | None = None,
        is_pressed: bool | None = None,
        raw_value: float | bool | HatDirection | None = None,
        synthetic: bool = False,
        osc_address: str | None = None,
    ) -> None:
        """Creates a new Event object.

        Args:
            event_type: the type of input causing the event
            identifier: the identifier of the event source
            device_guid: uuid identifying the device causing this event
            mode: name of the mode the system was in when the even was received
            value: the value of the input
            is_pressed: boolean flag indicating if a button or key is pressed
            raw_value: the raw value of the axis being moved
            synthetic: made by the program (macro step, refresh axes, Hat
                as Buttons), not by the hardware; screens that show what the
                hardware does (Listen, highlighting, Module Setup) ignore it
            osc_address: the address an OSC input received (for a pattern
                input, which of its addresses sent it); None otherwise
        """
        self.event_type = event_type
        self.identifier = identifier
        self.device_guid = device_guid
        self.mode = mode
        self.is_pressed = is_pressed
        self.value = value
        self.raw_value = raw_value
        self.synthetic = synthetic
        self.osc_address = osc_address

    def display_name(self) -> str:
        """Returns the display representation of this event.

        Returns:
            Textual representation of the event's input
        """
        if self.device_guid == OSC_DEVICE_UUID:
            return (
                "OSC - "
                + common.input_to_ui_string(self.event_type, self.identifier)
            )

        # The name the program shows for the device (twin name included),
        # one lookup instead of walking the list a hot-plug may be rebuilding.
        label = device_initialization.device_name(self.device_guid)
        if not label:
            logging.warning(
                f"Unable to find a device with GUID {str(self.device_guid)}"
            )
            label = "Unknown"

        # Retrive input name
        label += " - "
        label += common.input_to_ui_string(self.event_type, self.identifier)

        return label

    def clone(self) -> Event:
        """Returns a clone of the event.

        Returns:
            Cloned copy of this event.
        """
        return Event(
            self.event_type,
            self.identifier,
            self.device_guid,
            self.mode,
            self.value,
            self.is_pressed,
            self.raw_value,
            self.synthetic,
            self.osc_address,
        )

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Event)
        return self.__hash__() == other.__hash__()

    def __ne__(self, other: object) -> bool:
        assert isinstance(other, Event)
        return not (self == other)

    def __str__(self) -> str:
        return f"{self.device_guid}: {self.event_type} {self.identifier}"

    def __repr__(self) -> str:
        value = (
            self.is_pressed
            if self.event_type in [InputType.JoystickButton, InputType.Keyboard]
            else self.value
        )
        return (
            f"Event({self.event_type}, {self.identifier}, "
            + f"{self.device_guid}, {self.mode}, {value})"
        )

    def __hash__(self) -> int:
        """Computes the hash value of this event.

        The hash is comprised of the events type, identifier of the
        event source and the id of the event device. Events from the same
        input, e.g. axis, button, hat, key, with different values / states
        shall have the same hash.

        Returns:
            Integer hash value of this event
        """
        if self.event_type == InputType.Keyboard:
            return hash(
                (
                    self.device_guid,
                    self.event_type.value,
                    self.identifier[0],
                    int(self.identifier[1]),
                )
            )
        else:
            return hash((self.device_guid, self.event_type.value, self.identifier, 0))

    @staticmethod
    def from_key(key: keyboard.Key) -> Event:
        """Creates an event object corresponding to the provided key.

        Args:
            key: the Key object from which to create the Event

        Returns:
            Event object corresponding to the provided key
        """
        assert isinstance(key, keyboard.Key)
        return Event(
            event_type=InputType.Keyboard,
            identifier=(key.scan_code, key.is_extended),
            device_guid=dill.UUID_Keyboard,
            mode=NO_MODE,
        )


@common.SingletonDecorator
class EventListener(QtCore.QObject):
    """Listens for keyboard and joystick events and publishes them
    via QT's signal/slot interface.
    """

    # Signal emitted when joystick events are received
    joystick_event = QtCore.Signal(Event)
    # Signal emitted when keyboard events are received
    keyboard_event = QtCore.Signal(Event)
    # Signal emitted when mouse events are received
    mouse_event = QtCore.Signal(Event)
    # Signal emitted when virtual button events are received
    virtual_event = QtCore.Signal(Event)
    # Signal emitted when a joystick is attached or removed
    device_change_event = QtCore.Signal()

    def __init__(self) -> None:
        """Creates a new instance."""
        QtCore.QObject.__init__(self)
        self.keyboard_hook = windows_event_hook.KeyboardHook()
        self.keyboard_hook.register(self._keyboard_handler)
        self.mouse_hook = windows_event_hook.MouseHook()
        self.mouse_hook.register(self._mouse_handler)

        # Calibration function for each axis of all devices
        self._calibrations = {}

        # Joystick device change update timeout timer
        self._device_update_timer = None
        self._joystick = Joystick()
        self._keyboard = Keyboard()
        # When each key last had an event (lost-release check).
        self._key_times: dict[keyboard.Key, float] = {}

        self._running = True
        self._stop_event = threading.Event()
        self.gremlin_active = False

        self._init_joysticks()
        self.keyboard_hook.start()

        self._start_thread()

    def _start_thread(self) -> None:
        threads.start("event listener", self._run, stop=self._ask_to_stop)

    def _ask_to_stop(self) -> None:
        self._running = False
        self._stop_event.set()

    def terminate(self) -> None:
        """Stops the loop from running."""
        self._running = False
        self._stop_event.set()
        timer = getattr(self, "_device_update_timer", None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
            self._device_update_timer = None
        self.keyboard_hook.stop()
        mouse_hook = getattr(self, "mouse_hook", None)
        if mouse_hook is not None:
            try:
                mouse_hook.stop()
            except Exception:
                pass
        dill.DILL.set_device_change_callback(lambda *_: None)
        dill.DILL.set_input_event_callback(lambda *_: None)

    def restart(self) -> None:
        """Restarts the event listener."""
        if not self._running:
            self._running = True
            self.keyboard_hook.start()
            self._stop_event.clear()
            self._start_thread()

    def reload_calibration(self, device_guid: dill.GUID, axis_index: int) -> None:
        """Reloads the calibration data of the specified axis."""
        from gremlin.modules.calibration import values_for_device

        key = (device_guid, axis_index)
        self._calibrations[key] = util.create_calibration_function(
            *values_for_device(device_guid.uuid, axis_index)
        )

    def _run(self) -> None:
        """Starts the event loop."""
        dill.DILL.set_device_change_callback(self._joystick_device_handler)
        dill.DILL.set_input_event_callback(self._joystick_event_handler)
        while self._running:
            # Keep this thread alive until we are done
            self._stop_event.wait()

    def _joystick_event_handler(self, data: dill.InputEvent) -> None:
        """Callback for joystick events.

        The handler converts the event data into a signal which is then
        emitted.

        Args:
            data: the joystick event information
        """
        event = dill.InputEvent(data)
        try:
            self._joystick_event(event)
        except Exception as e:
            # Raised here it would be lost inside the driver's thread.
            from gremlin.log_once import log_once

            log_once(
                "system",
                ("unknown input", event.device_guid.uuid, event.input_type,
                 event.input_index),
                logging.WARNING,
                f"Input {event.input_type} {event.input_index} of device "
                f"{event.device_guid.uuid} was dropped: {e}",
            )

    def _joystick_event(self, event: dill.InputEvent) -> None:
        # Trace tab (D-01-TRACE): the value as the driver sent it, before
        # the claim gate. Off costs one check.
        if trace.enabled():
            self._trace_raw(event)
        if event.input_type == dill.InputType.Axis:
            calibrated_value = self._apply_calibration(event)
            self._joystick[event.device_guid.uuid].axis(event.input_index).update(
                calibrated_value
            )

            self.joystick_event.emit(
                Event(
                    event_type=InputType.JoystickAxis,
                    device_guid=event.device_guid.uuid,
                    identifier=event.input_index,
                    mode=NO_MODE,
                    value=calibrated_value,
                    raw_value=event.value,
                )
            )
        elif event.input_type == dill.InputType.Button:
            self._joystick[event.device_guid.uuid].button(event.input_index).update(
                event.value == 1
            )

            self.joystick_event.emit(
                Event(
                    event_type=InputType.JoystickButton,
                    device_guid=event.device_guid.uuid,
                    identifier=event.input_index,
                    mode=NO_MODE,
                    is_pressed=event.value == 1,
                )
            )
        elif event.input_type == dill.InputType.Hat:
            direction = util.dill_hat_lookup(event.value)
            self._joystick[event.device_guid.uuid].hat(event.input_index).update(
                direction
            )

            self.joystick_event.emit(
                Event(
                    event_type=InputType.JoystickHat,
                    device_guid=event.device_guid.uuid,
                    identifier=event.input_index,
                    mode=NO_MODE,
                    value=direction,
                )
            )

    def _trace_raw(self, event: dill.InputEvent) -> None:
        guid = event.device_guid.uuid
        index = event.input_index
        if event.input_type == dill.InputType.Axis:
            if trace.ticked(guid, "axis", index):
                calibrated = self._apply_calibration(event)  # type: ignore[arg-type]
                trace.raw(guid, "axis", index, calibrated,
                          raw_value=event.value)
        elif event.input_type == dill.InputType.Button:
            if trace.ticked(guid, "button", index):
                trace.raw(guid, "button", index, event.value == 1)
        elif event.input_type == dill.InputType.Hat:
            if trace.ticked(guid, "hat", index):
                direction = util.dill_hat_lookup(event.value)
                trace.raw(guid, "hat", index,
                          getattr(direction, "name", str(direction)))

    def _joystick_device_handler(
        self, data: dill.DeviceSummary, action: dill.DeviceActionType
    ) -> None:
        """Callback for device change events.

        This is called when a device is added or removed from the system. This
        uses a timer to call the actual device update function to prevent
        the addition or removal of a multiple devices at the same time to
        cause repeat updates.

        Args:
            data: information about the device changing state
            action: whether the device was added or removed
        """
        # ViGEm 360 pads are created by Gremlin itself. Reloading on that
        # arrival unplugs the pad (XboxProxy.reset) and Steam flaps connect.
        try:
            if is_vigem_xbox_summary(data):
                return
        except Exception:
            pass
        if trace.enabled():
            try:
                info = (data if isinstance(data, dill.DeviceSummary)
                        else dill.DeviceSummary(data))
                if isinstance(action, int):
                    action = dill.DeviceActionType.from_ctype(action)
                name = info.name
                plugged = action == dill.DeviceActionType.Connected
                trace.event(f"{name} {'plugged in' if plugged else 'unplugged'}")
            except Exception:
                pass
        if self._device_update_timer is not None:
            self._device_update_timer.cancel()
        self._device_update_timer = threads.timer(
            "device list update", 0.2, self._run_device_list_update
        )

    def _run_device_list_update(self) -> None:
        """Performs the update of the devices connected."""
        before = {
            dev.device_guid.uuid
            for dev in device_initialization.joystick_devices()
        }
        try:
            device_initialization.joystick_devices_initialization()
        except error.GremlinError as e:
            # Runs on a timer thread: say so instead of losing it.
            logging.getLogger("system").error(f"Device update failed: {e}")
            from gremlin import signal as gremlin_signal

            gremlin_signal.display_error(
                "The device list could not be updated.", str(e)
            )
            return
        self._init_joysticks()
        after = {
            dev.device_guid.uuid
            for dev in device_initialization.joystick_devices()
        }
        # A device that changed layout under the same id (an Xbox pad
        # switched XInput <-> DirectInput) is an unplug + plug-in (02 S143).
        relaid = device_initialization.layout_changed()
        # A stick unplugged with a button held (or a hat pushed) would keep
        # it held on the outputs until it came back: it is let go now.
        for device_guid in (before - after) | relaid:
            self._let_go(device_guid)
        # A stick that comes back may have another layout under the same
        # id: its cached inputs follow the new one (an unplugged stick keeps
        # its last values for scripts and conditions).
        for device_guid in (after - before) | (relaid & after):
            self._joystick.reconnected(device_guid)
        # HID already ignores ViGEm pads; do not fire Reload if the
        # filtered list did not change.
        if trace.enabled():
            trace.event(
                f"Devices re-read: {len(after)} connected, "
                f"{len(after - before)} new, {len(before - after)} gone"
                + (f", {len(relaid)} changed layout" if relaid else "")
            )
        if before != after or relaid:
            self.device_change_event.emit()

    def _let_go(self, device_guid: uuid.UUID) -> None:
        """Releases what an unplugged stick was holding, as its own input
        events would (buttons up, hats centred; axes stay where they were:
        a throttle has no rest position)."""
        wrapper = self._joystick.devices.get(device_guid)
        if wrapper is None or not hasattr(wrapper, "let_go"):
            return
        buttons, hats = wrapper.let_go()
        mode = NO_MODE
        for index in buttons:
            self.joystick_event.emit(
                Event(
                    event_type=InputType.JoystickButton,
                    device_guid=device_guid,
                    identifier=index,
                    mode=mode,
                    is_pressed=False,
                )
            )
        for index in hats:
            self.joystick_event.emit(
                Event(
                    event_type=InputType.JoystickHat,
                    device_guid=device_guid,
                    identifier=index,
                    mode=mode,
                    value=HatDirection.Center,
                )
            )
        if buttons or hats:
            logging.getLogger("system").info(
                f"Unplugged {device_guid}: let go of buttons {buttons}, hats {hats}"
            )

    def _keyboard_handler(self, event: Event) -> bool:
        """Callback for keyboard events.

        The handler converts the event data into a signal which is then
        emitted.

        Args:
            event: the keyboard event

        Returns:
            True to enable the event to propagate up further
        """
        # Keys the program sends itself (Map to Keyboard, macros) are not
        # input while a Run is on: one binding's key must not fire another,
        # nor be recorded or listened for (decision D-02-Q4).
        if getattr(event, "is_own", False) and run_scope.running():
            return True

        key_id = keyboard.key_from_code(event.scan_code, event.is_extended)
        is_pressed = event.is_pressed
        is_repeat = self._keyboard.is_pressed(key_id) and is_pressed
        now = clock.monotonic()
        if is_repeat and self._release_was_lost(key_id, now):
            is_repeat = False
        self._key_times[key_id] = now
        # Only emit an event if they key is pressed for the first
        # time or released but not when it's being held down
        if not is_repeat:
            self._keyboard.update(key_id, is_pressed)
            self.keyboard_event.emit(
                Event(
                    event_type=InputType.Keyboard,
                    device_guid=dill.UUID_Keyboard,
                    identifier=(key_id.scan_code, key_id.is_extended),
                    mode=NO_MODE,
                    is_pressed=is_pressed,
                )
            )

        # Allow the windows event to propagate further
        return True

    def _release_was_lost(self, key: keyboard.Key, now: float) -> bool:
        """A press of a key the cache has down: True when its release was
        lost (Windows had it, we did not: Ctrl+Alt+Del, a hook timeout), so
        this is a new press, not Windows repeating a held key."""
        last = self._key_times.get(key)
        if last is not None and now - last <= REPEAT_GAP_S:
            return False
        try:
            return not keyboard.is_down_in_windows(key)
        except Exception:
            return False

    def _mouse_handler(self, event: Event) -> bool:
        """Callback for mouse events.

        The handler converts the event data into a signal which is then
        emitted.

        Args:
            event: the mouse event

        Returns:
            True to enable the event to propagate up further
        """
        # Same device id as keyboard events (a UUID, not a GUID).
        self.mouse_event.emit(
            Event(
                event_type=InputType.Mouse,
                device_guid=dill.UUID_Keyboard,
                identifier=event.button_id,
                mode=NO_MODE,
                is_pressed=event.is_pressed,
            )
        )

        # Allow the windows event to propagate further
        return True

    def _apply_calibration(self, event: Event) -> float:
        """Applies a calibration to raw input values.

        The resulting value will be in the range [-1, 1].

        Args:
            event: the event containing the data to be calibrated

        Returns:
            Value with applied calibration and scaling
        """
        key = (event.device_guid, event.input_index)
        calibration = self._calibrations.get(key)
        if calibration is not None:
            return calibration(event.value)
        else:
            # Once per axis: this runs on every move of that axis.
            from gremlin.log_once import log_once

            log_once(
                "system", ("calibration", key), logging.INFO,
                f"No calibration data for {key[0]} - Axis {key[1]}",
            )
            return util.with_default_center_calibration(event.value)

    def _init_joysticks(self) -> None:
        """Initializes joystick devices.

        Loads calibration data for the joystick. The new table is built
        aside and swapped in at once: the driver's thread reads it meanwhile.
        """
        from gremlin.modules.calibration import values_for_device

        calibrations = {}
        for dev_info in device_initialization.joystick_devices():
            for entry in dev_info.axis_map:
                key = (dev_info.device_guid, entry.axis_index)
                calibrations[key] = util.create_calibration_function(
                    *values_for_device(dev_info.device_guid.uuid, entry.axis_index)
                )
        self._calibrations = calibrations

    def axis_value(self, device_guid: uuid.UUID, axis_index: int) -> float:
        """The calibrated value of a stick's axis. An axis that has not
        moved since the program started is read from the driver once and
        cached (a throttle resting at 80% is not centre; decision D-02-Q7)."""
        axis = self._joystick[device_guid].axis(axis_index)
        if not axis.seen:
            guid = dill.GUID.from_uuid(device_guid)
            raw = int(dill.DILL.get_axis(guid, axis_index))
            calibration = self._calibrations.get((guid, axis_index))
            if calibration is not None:
                value = calibration(raw)
            else:
                value = util.with_default_center_calibration(raw)
            axis.update(value)
        return axis.value


@common.SingletonDecorator
class EventHandler(QtCore.QObject):
    """Listens to the inputs from multiple different input devices."""

    # Signal emitted when the mode is changed
    mode_changed = QtCore.Signal(str)
    # Signal emitted when the application is pause / resumed
    is_active = QtCore.Signal(bool)

    def __init__(self) -> None:
        """Initializes the EventHandler instance."""
        QtCore.QObject.__init__(self)
        self.process_callbacks = True
        self.plugins = {}
        self.callbacks = {}
        self._event_lookup = {}
        self.known_modes: set[str] = set()

    def add_plugin(self, plugin: Any) -> None:  # noqa: ANN401
        """Adds a new plugin to be attached to event callbacks.

        Params:
            plugin: Instance of the plugin to add
        """
        # Do not add the same type of plugin multiple times
        if plugin.keyword not in self.plugins:
            self.plugins[plugin.keyword] = plugin

    def add_callback(
        self,
        device_guid: uuid.UUID,
        mode: str,
        event: Event,
        callback: CallbackObject | Callable[[Event], None],
    ) -> None:
        """Installs the provided callback for the given event.

        Args:
            device_guid: the GUID of the device the callback is associated with
            mode: the mode the callback belongs to
            event: the event for which to install the callback
            callback: the callback function to link to the provided event
        """
        if device_guid not in self.callbacks:
            self.callbacks[device_guid] = {}
        if mode not in self.callbacks[device_guid]:
            self.callbacks[device_guid][mode] = {}
        if event not in self.callbacks[device_guid][mode]:
            self.callbacks[device_guid][mode][event] = []
        self.callbacks[device_guid][mode][event].append(self._install_plugins(callback))

    def rename_mode(self, old_name: str, new_name: str) -> None:
        """Move callbacks registered for a mode onto its new name."""
        if old_name == new_name:
            return
        if old_name in self.known_modes:
            self.known_modes.discard(old_name)
            self.known_modes.add(new_name)
        for device_cb in self.callbacks.values():
            if old_name not in device_cb:
                continue
            moved = device_cb.pop(old_name)
            current = device_cb.get(new_name)
            if current is None:
                device_cb[new_name] = moved
                continue
            for event, callbacks in moved.items():
                current.setdefault(event, []).extend(callbacks)

    def drop_mode(self, name: str) -> None:
        """Remove callbacks registered for a deleted mode."""
        self.known_modes.discard(name)
        for device_cb in self.callbacks.values():
            device_cb.pop(name, None)

    def build_event_lookup(self, mode_list: list[tree.TreeNode]) -> None:
        """Builds the lookup table linking events to callbacks.

        This takes mode inheritance into account to create items in children
        if they do not override a parent's action.

        Args:
            modes: information about the mode hierarchy
        """
        # The running profile's modes (a mode change to any other is ignored).
        self.known_modes = {mode.value for mode in mode_list}
        for mode in mode_list:
            # Each device is treated separately
            for device_guid in self.callbacks:
                # Only attempt to copy handlers into child modes if the current
                # mode has any available
                if mode.value in self.callbacks[device_guid]:
                    device_cb = self.callbacks[device_guid]
                    mode_cb = device_cb[mode.value]
                    # Copy the handlers into each child mode, unless they
                    # have their own handlers already defined
                    for child in [e.value for e in mode.children]:
                        if child not in device_cb:
                            device_cb[child] = {}
                        for event, callbacks in mode_cb.items():
                            if event not in device_cb[child]:
                                device_cb[child][event] = callbacks

    def is_same_binding(self, event: Event, old_mode: str, new_mode: str) -> bool:
        """Whether both modes route event to the same binding (06 S88).

        build_event_lookup gives an inheriting child mode the parent's very
        list, so list identity is the test. No binding in either mode is not
        the same binding.
        """
        device_cb = self.callbacks.get(event.device_guid, {})
        old = device_cb.get(old_mode, {}).get(event)
        new = device_cb.get(new_mode, {}).get(event)
        return old is not None and old is new

    def resume(self) -> None:
        """Resumes the processing of callbacks."""
        self.process_callbacks = True
        self.is_active.emit(self.process_callbacks)

    def pause(self) -> None:
        """Stops the processing of callbacks."""
        self.process_callbacks = False
        self.is_active.emit(self.process_callbacks)

    def toggle_active(self) -> None:
        """Toggles the processing of callbacks on or off."""
        self.process_callbacks = not self.process_callbacks
        self.is_active.emit(self.process_callbacks)

    def clear(self) -> None:
        """Removes all attached callbacks."""
        self.callbacks = {}
        self.known_modes = set()

    @QtCore.Slot(Event)
    def process_event(self, event: Event) -> None:
        """Processes a single event by passing it to all callbacks
        registered for this event.

        Args:
            event: the event to process
        """
        # The listener leaves the mode to the layer above it: the mode is the
        # one current when the event is handled, read on the main thread.
        if not event.mode:
            event.mode = mode_manager.ModeManager().current.name
        # Process callbacks defined via actions or scripts.
        callbacks = self._matching_callbacks(event)
        # Input Monitor (Live Log Reader): read-only, one check when off.
        if input_monitor.enabled():
            input_monitor.record(event, callbacks, not self.process_callbacks)
        # Trace tab (D-01-TRACE): outputs written from here on belong to
        # this input. Off costs one check.
        traced = trace_ticked(event)
        if traced is not None:
            self._trace_wiring(event, *traced, callbacks)
        try:
            self._run_callbacks(event, callbacks)
        finally:
            if traced is not None:
                trace.end_input()

    def _trace_wiring(
        self,
        event: Event,
        kind: str,
        index: int,
        callbacks: list[Callable[[Event], None]],
    ) -> None:
        try:
            trace.begin_input(event.device_guid, kind, index)
            names = (input_monitor.callback_text(cb) for cb in callbacks)
            ran = [text for text in names if text]
            if ran:
                done = "ran " + "; ".join(ran)
            elif callbacks:
                done = "ran script"
            else:
                done = "paused" if not self.process_callbacks else "no actions"
            trace.wiring(
                event.device_guid, kind, index,
                f"claimed · mode {event.mode} · {done}",
            )
        except Exception:  # tracing never affects the profile
            pass

    def _run_callbacks(
        self, event: Event, callbacks: list[Callable[[Event], None]]
    ) -> None:
        for cb in callbacks:
            # A vJoy error is logged like any other failure; it no longer
            # pauses the profile (decision 06 Q10).
            try:
                cb(event)
            except Exception:
                # One failing action doesn't stop the others, or the release
                # handling below.
                logging.getLogger("system").exception(
                    f"An action for {event} failed"
                )

        # Call button release callbacks after basic event processing completes.
        try:
            event_helpers.ButtonReleaseActions().process_release(event)
        except Exception:
            logging.getLogger("system").exception(
                f"A release action for {event} failed"
            )

    def _matching_callbacks(self, event: Event) -> list[Callable[[Event], None]]:
        """Returns the list of callbacks to execute in response to
        the provided event.

        Args:
            event: the event for which to search the matching callbacks

        Returns:
            A list of all callbacks registered and valid for the given event.
        """
        # Obtain callbacks matching the event
        callback_list = []
        if event.device_guid in self.callbacks:
            callback_list = (
                self.callbacks[event.device_guid].get(event.mode, {}).get(event, [])
            )

        # Filter events when the system is paused
        if not self.process_callbacks:
            # A user-script callback is a plain function, without always_execute:
            # reading it raised, so nothing ran while paused, not even Resume.
            return [c for c in callback_list if getattr(c, "always_execute", False)]
        else:
            return callback_list

    def _install_plugins(
        self, callback: CallbackObject | Callable[[Event], None]
    ) -> Callable[[Event], None]:
        """Installs the current plugins into the given callback.

        Args:
            callback: the callback function to install the plugins into

        Returns:
            New callback with plugins installed
        """
        signature = inspect.signature(callback).parameters
        for keyword, plugin in self.plugins.items():
            if keyword in signature:
                callback = plugin.install(callback, functools.partial)
        return callback
