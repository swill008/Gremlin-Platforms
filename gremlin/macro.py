# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import collections
import functools
import logging
import time
import uuid
from abc import (
    ABC,
    abstractmethod,
)
from threading import (
    Condition,
    Event,
    Lock,
)
from typing import override
from xml.etree import ElementTree

import dill
from gremlin import (
    error,
    event_handler,
    mode_manager,
    sendinput,
    threads,
    util,
)
from gremlin.common import SingletonMetaclass
from gremlin.config import Configuration
from gremlin.keyboard import (
    Key,
    key_from_code,
    key_from_name,
    send_key_down,
    send_key_up,
)
from gremlin.logical_device import LogicalDevice
from gremlin.modules import output
from gremlin.types import (
    AxisMode,
    InputType,
    MouseButton,
    PropertyType,
)

MacroEntry = collections.namedtuple("MacroEntry", ["macro", "state"])


class MacroManager(metaclass=SingletonMetaclass):
    """Manages the proper dispatching and scheduling of macros."""

    def __init__(self) -> None:
        """Initializes the instance."""
        self._queued_macros: list[MacroEntry] = []
        self._scheduled_macro: dict[int, Macro] = {}
        self._executing_macro: dict[int, bool] = {}
        self._executing_macro_lock = Lock()
        self._queued_macros_lock = Lock()

        # Default delay between subsequent message dispatch. This is to get
        # around some games not picking up messages if they are sent in too
        # quick a succession.
        self.default_delay = Configuration().value("action", "macro", "default-delay")

        self._is_executing_preemptive = False
        self._is_executing_exclusive = False
        self._preemptive_condition = Condition()
        self._is_running = False
        self._schedule_event = Event()

        self._run_scheduler_thread = None

    def start(self) -> None:
        """Starts the scheduler."""
        self._scheduled_macro = {}
        self._executing_macro = {}
        # Macros queued before the last Stop don't run now.
        with self._queued_macros_lock:
            self._queued_macros = []
        self._is_executing_preemptive = False
        self._is_executing_exclusive = False
        self._is_running = True
        if (
            self._run_scheduler_thread is None
            or not self._run_scheduler_thread.is_alive()
        ):
            self._run_scheduler_thread = threads.start(
                "macro scheduler", self._run_scheduler, stop=self._ask_to_stop
            )

    def _ask_to_stop(self) -> None:
        self._is_running = False
        self._schedule_event.set()

    def stop(self) -> None:
        """Stops the scheduler."""
        self._is_running = False
        with self._queued_macros_lock:
            self._queued_macros = []
        if (
            self._run_scheduler_thread is not None
            and self._run_scheduler_thread.is_alive()
        ):
            # Terminate the scheduler.
            self._schedule_event.set()
            self._run_scheduler_thread.join(timeout=2.0)
            self._run_scheduler_thread = None

            # Terminate any macro that is still active.
            with self._executing_macro_lock:
                for key in self._executing_macro:
                    self._executing_macro[key] = False

    def queue_macro(self, macro: Macro) -> None:
        """Queues a macro in the schedule taking the repeat type into account.

        Args:
            macro: the macro to add to the scheduler
        """
        if isinstance(macro.repeat, ToggleRepeat) and macro.id in self._scheduled_macro:
            self.terminate_macro(macro)
        else:
            # Preprocess macro to contain pauses as necessary.
            self._preprocess_macro(macro)
            with self._queued_macros_lock:
                self._queued_macros.append(MacroEntry(macro, True))
            self._schedule_event.set()

    def terminate_macro(self, macro: Macro) -> None:
        """Adds a termination request for a macro to the execution queue.

        Args:
            macro: the macro to terminate
        """
        with self._queued_macros_lock:
            self._queued_macros.append(MacroEntry(macro, False))
        self._schedule_event.set()

    def _run_scheduler(self) -> None:
        """Dispatches macros as required."""
        while self._is_running:
            # Wake up when the event triggers to proces the macro list.
            self._schedule_event.wait()
            self._schedule_event.clear()

            # Run scheduled macros and ensure exclusive ones run separately from all
            # other macros.
            with self._queued_macros_lock:
                entries_to_remove = []
                has_exclusive = False
                # A copy: entries are removed from the queue along the way.
                for entry in list(self._queued_macros):
                    if entry not in self._queued_macros:
                        continue  # removed by a stop request above
                    # Terminate macro if needed.
                    if entry.state is False:
                        # The running one stops (its flag is set when it is
                        # dispatched, so a release that came first finds it).
                        with self._executing_macro_lock:
                            if self._executing_macro.get(entry.macro.id):
                                self._executing_macro[entry.macro.id] = False
                        # Queued ones with the same id go, and so does this
                        # request (it used to stay, and a Hold macro released
                        # before it started kept running).
                        self._queued_macros = [
                            queue_entry for queue_entry in self._queued_macros
                            if queue_entry.macro.id != entry.macro.id
                        ]
                    # Don't run a queued macro if the same instance is already running.
                    elif entry.macro.id in self._scheduled_macro:
                        continue
                    # Handle exclusive and pre-empting macros.
                    elif entry.macro.is_exclusive:
                        has_exclusive = True

                        # Can only preempt if no other macro is currently performing a
                        # preemptive macro.
                        if entry.macro.is_preempting:
                            if not self._is_executing_preemptive:
                                self._is_executing_preemptive = True
                                self._is_executing_exclusive = True
                                self._dispatch_macro(entry.macro)
                                entries_to_remove.append(entry)
                        # Non-preemptive exclusive macros wait for currently running
                        # macros to finish before being dispatched.
                        elif len(self._scheduled_macro) == 0:
                            self._is_executing_exclusive = True
                            self._dispatch_macro(entry.macro)
                            entries_to_remove.append(entry)
                    # When no exclusive macro is running dispatch all queued up macros.
                    elif not has_exclusive and not self._is_executing_exclusive:
                        self._dispatch_macro(entry.macro)
                        entries_to_remove.append(entry)

                # Remove all entries we've processed.
                for entry in entries_to_remove:
                    if entry in self._queued_macros:
                        self._queued_macros.remove(entry)

    def _dispatch_macro(self, macro: Macro) -> None:
        """Dispatches a single macro to be run.

        Args:
            macro: the macro to dispatch
        """
        if macro.id not in self._scheduled_macro:
            self._scheduled_macro[macro.id] = macro
            if macro.repeat is not None:
                # Set here, not in the thread: a release that comes before the
                # thread starts must find it running.
                with self._executing_macro_lock:
                    self._executing_macro[macro.id] = True
            threads.start(
                "macro",
                self._execute_macro,
                macro,
                stop=functools.partial(self._ask_macro_to_stop, macro),
            )
        else:
            logging.getLogger("system").warning(
                "Attempting to dispatch an already running macro."
            )

    def _ask_macro_to_stop(self, macro: Macro) -> None:
        """Ends a repeating macro after its current step."""
        with self._executing_macro_lock:
            if macro.id in self._executing_macro:
                self._executing_macro[macro.id] = False

    def _wait_while_paused(self, macro: Macro) -> None:
        """Blocks the calling thread while a different macro is executing preemptively
        and exclusively.

        Args:
            macro: the macro whose thread is calling this method
        """
        # In short waits, so a stop (of the macros or of this macro) ends it.
        with self._preemptive_condition:
            while not self._preemptive_condition.wait_for(
                lambda: not self._is_executing_preemptive or macro.is_preempting,
                timeout=0.5,
            ):
                if not self._is_running or not self._executing_macro.get(
                    macro.id, True
                ):
                    return

    def _execute_macro(self, macro: Macro) -> None:
        """Executes a given macro in a separate thread.

        This method will run all provided actions and once they all have been executed
        will remove the macro from the set of active macros and inform the scheduler of
        the completion.

        Args:
            macro: the macro object to be executed
        """
        try:
            self._run_steps(macro)
        except Exception:
            # A failing step ends this macro only; the clean-up below lets
            # every other macro (and this one again) run.
            logging.getLogger("system").exception("A macro step failed")
        finally:
            self._finish_macro(macro)

    def _run_steps(self, macro: Macro) -> None:
        # Handle macros with a repeat mode
        if macro.repeat is not None:
            delay = macro.repeat.delay

            # Handle count repeat mode
            if isinstance(macro.repeat, CountRepeat):
                count = 0
                while count < macro.repeat.count and self._executing_macro[macro.id]:
                    for action in macro.sequence:
                        self._wait_while_paused(macro)
                        action()
                    count += 1
                    time.sleep(delay)

            # Handle continuous repeat modes
            elif type(macro.repeat) in [HoldRepeat, ToggleRepeat]:
                # The first round runs even if a release already came (a tap
                # released before the run started ran once before, too); after
                # that, as before, each round checks first.
                first = True
                while first or self._executing_macro.get(macro.id, False):
                    first = False
                    for action in macro.sequence:
                        self._wait_while_paused(macro)
                        action()
                    time.sleep(delay)

        # Handle simple one shot macros.
        else:
            for action in macro.sequence:
                self._wait_while_paused(macro)
                action()

    def _finish_macro(self, macro: Macro) -> None:
        # Remove macro from active set, notify manager, and remove any potential
        # callbacks.
        self._scheduled_macro.pop(macro.id, None)
        if macro.is_exclusive:
            self._is_executing_exclusive = False
            if macro.is_preempting:
                with self._preemptive_condition:
                    self._is_executing_preemptive = False
                    self._preemptive_condition.notify_all()
        with self._executing_macro_lock:
            if macro.id in self._executing_macro:
                self._executing_macro[macro.id] = False
        self._schedule_event.set()

    def _preprocess_macro(self, macro: Macro) -> None:
        """Inserts pauses as necessary into the macro.

        Args:
            macro: the macro instance to modify
        """
        if not macro.sequence:  # an empty macro: nothing to space out
            return
        new_sequence = [macro.sequence[0]]
        for a1, a2 in zip(macro.sequence[:-1], macro.sequence[1:]):
            if isinstance(a1, PauseAction) or isinstance(a2, PauseAction):
                new_sequence.append(a2)
            else:
                new_sequence.append(PauseAction(self.default_delay))
                new_sequence.append(a2)
        macro._sequence = new_sequence


class Macro:
    """Represents a macro which can be executed."""

    # Unique identifier for each macro
    _next_macro_id = 0

    def __init__(self) -> None:
        """Creates a new macro instance."""
        self._sequence = []
        self._id = Macro._next_macro_id
        Macro._next_macro_id += 1
        self.repeat = None
        self.is_exclusive = False
        self.is_preempting = False

    @property
    def id(self) -> int:
        """Returns the unique id of this macro.

        Returns:
            unique id of this macro
        """
        return self._id

    @property
    def sequence(self) -> list[AbstractAction]:
        """Returns the action sequence of this macro.

        Returns:
            Sequence of actions comprising the macro
        """
        return self._sequence

    def add_action(self, action: AbstractAction) -> None:
        """Adds an action to the list of actions to perform.

        Args:
            action: the action to add
        """
        self._sequence.append(action)

    def pause(self, duration: float) -> None:
        """Adds a pause of the given duration to the macro.

        Args:
            duration: the duration of the pause in seconds
        """
        self._sequence.append(PauseAction(duration))

    def press(self, key: Key) -> None:
        """Presses the specified key down.

        Args:
            key: the key to press
        """
        self.action(key, True)

    def release(self, key: Key) -> None:
        """Releases the specified key.

        Args:
            key; the key to release
        """
        self.action(key, False)

    def tap(self, key: Key) -> None:
        """Taps the specified key.

        Args:
            key: the key to tap
        """
        self.action(key, True)
        self.action(key, False)

    def action(self, key: Key | str, is_pressed: bool) -> None:
        """Adds the specified action to the sequence.

        Args:
            key: the key involved in the action
            is_pressed: boolean indicating if the key is pressed
                (True) or released (False)
        """
        if isinstance(key, str):
            key = key_from_name(key)
        elif isinstance(key, Key):
            pass
        else:
            raise error.KeyboardError("Invalid key specified")

        self._sequence.append(KeyAction(key, is_pressed))


class AbstractAction(ABC):
    """Base class for all macro action."""

    @abstractmethod
    def __call__(self) -> None:
        pass

    @classmethod
    @abstractmethod
    def create(cls) -> AbstractAction:
        """Creates an empty, likely invalid instance, of the action."""
        pass

    @abstractmethod
    def to_xml(self) -> ElementTree.Element:
        pass

    @abstractmethod
    def from_xml(self, node: ElementTree.Element) -> None:
        pass

    @abstractmethod
    def is_valid() -> bool:
        pass

    def _create_node(self, type_name: str) -> ElementTree.Element:
        """Creates an action node of the given type.

        Args:
            type_name: name of the type of this action node

        Returns:
            An action node typed as request
        """
        node = ElementTree.Element("macro-action")
        node.set("type", type_name)
        return node

    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        """Swaps occurrences of the old UUID with the new one for this action."""
        return False


class JoystickAction(AbstractAction):
    """Joystick input action for a macro."""

    tag = "joystick"

    def __init__(
        self,
        device_guid: uuid.UUID,
        input_type: InputType,
        input_id: int | uuid.UUID,
        value: bool | float | tuple[int, int],
        axis_mode: AxisMode = AxisMode.Absolute,
    ) -> None:
        """Creates a new JoystickAction instance for use in a macro.

        Args:
            device_guid: GUID of the device generating the input
            input_type: type of input being generated
            input_id: id of the input being generated
            value: the value of the generated input
            axis_mode: if an axis is used, how to interpret the value
        """
        self.device_guid = device_guid
        self.input_type = input_type
        self.input_id = input_id
        self.value = value
        self.axis_mode = axis_mode

    @classmethod
    def create(cls) -> JoystickAction:
        return JoystickAction(dill.UUID_Invalid, InputType.JoystickButton, 0, False)

    def __call__(self) -> None:
        """Emits an Event instance through the EventListener system."""
        el = event_handler.EventListener()
        if self.input_type == InputType.JoystickAxis:
            event = event_handler.Event(
                event_type=self.input_type,
                device_guid=self.device_guid,
                identifier=self.input_id,
                mode=mode_manager.ModeManager().current.name,
                value=self.value,
            )
        elif self.input_type == InputType.JoystickButton:
            event = event_handler.Event(
                event_type=self.input_type,
                device_guid=self.device_guid,
                identifier=self.input_id,
                mode=mode_manager.ModeManager().current.name,
                is_pressed=self.value,
            )
        elif self.input_type == InputType.JoystickHat:
            event = event_handler.Event(
                event_type=self.input_type,
                device_guid=self.device_guid,
                identifier=self.input_id,
                mode=mode_manager.ModeManager().current.name,
                value=self.value,
            )

        el.joystick_event.emit(event)

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["device-guid", self.device_guid, PropertyType.UUID],
                ["input-type", self.input_type, PropertyType.InputType],
                ["input-id", self.input_id, PropertyType.Int],
            ],
        )
        if self.input_type == InputType.JoystickAxis:
            util.append_property_nodes(
                node,
                [
                    ["value", self.value, PropertyType.Float],
                    ["axis-mode", self.axis_mode, PropertyType.AxisMode],
                ],
            )
        elif self.input_type == InputType.JoystickButton:
            node.append(
                util.create_property_node("value", self.value, PropertyType.Bool)
            )
        elif self.input_type == InputType.JoystickHat:
            node.append(
                util.create_property_node(
                    "value", self.value, PropertyType.HatDirection
                )
            )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.device_guid = util.read_property(node, "device-guid", PropertyType.UUID)
        self.input_type = util.read_property(node, "input-type", PropertyType.InputType)
        self.input_id = util.read_property(node, "input-id", PropertyType.Int)
        if self.input_type == InputType.JoystickAxis:
            self.value = util.read_property(node, "value", PropertyType.Float)
            self.axis_mode = util.read_property(
                node, "axis-mode", PropertyType.AxisMode
            )
        elif self.input_type == InputType.JoystickButton:
            self.value = util.read_property(node, "value", PropertyType.Bool)
        elif self.input_type == InputType.JoystickHat:
            self.value = util.read_property(node, "value", PropertyType.HatDirection)

    def is_valid(self) -> bool:
        return self.device_guid != dill.UUID_Invalid

    @override
    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        if self.device_guid == old_uuid:
            self.device_guid = new_uuid
            return True
        return False


class KeyAction(AbstractAction):
    """Key to press or release by a macro."""

    tag = "key"

    def __init__(self, key: Key | None, is_pressed: bool) -> None:
        """Creates a new KeyAction object for use in a macro.

        Args:
            key: the key to use in the action
            is_pressed: True if the key should be pressed, False otherwise
        """
        if not (isinstance(key, Key) or key is None):
            raise error.KeyboardError("Invalid Key instance provided")

        self.key = key
        self.is_pressed = is_pressed

    @classmethod
    def create(cls) -> KeyAction:
        return KeyAction(None, False)

    def __call__(self) -> None:
        if self.key is None:
            return

        if self.is_pressed:
            send_key_down(self.key)
        else:
            send_key_up(self.key)

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["scan-code", self.key.scan_code, PropertyType.Int],
                ["is-extended", self.key.is_extended, PropertyType.Bool],
                ["is-pressed", self.is_pressed, PropertyType.Bool],
            ],
        )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.key = key_from_code(
            util.read_property(node, "scan-code", PropertyType.Int),
            util.read_property(node, "is-extended", PropertyType.Bool),
        )
        self.is_pressed = util.read_property(node, "is-pressed", PropertyType.Bool)

    def is_valid(self) -> bool:
        return self.key is not None


class LogicalDeviceAction(AbstractAction):
    """Logical device input action."""

    tag = "logical-device"

    def __init__(
        self,
        input_type: InputType,
        input_id: int,
        value: bool | float | tuple[int, int],
        axis_mode: AxisMode = AxisMode.Absolute,
    ) -> None:
        """Creates a new LogicalDeviceAction instance for use in a macro.

        Args:
            input_type: type of input being generated
            input_id: id of the input being generated
            value: the value of the generated input
            axis_mode: if an axis is used, how to interpret the value
        """
        self.input_type = input_type
        self.input_id = input_id
        self.value = value
        self.axis_mode = axis_mode
        self._event_listener = event_handler.EventListener()
        self._mode_manager = mode_manager.ModeManager()

    @classmethod
    def create(cls) -> LogicalDeviceAction:
        if len(LogicalDevice().inputs_of_type()) == 0:
            LogicalDevice().create(InputType.JoystickButton)
        first_input = LogicalDevice().inputs_of_type()[0]
        return LogicalDeviceAction(first_input.type, first_input.id, first_input._value)

    def __call__(self) -> None:
        ld = LogicalDevice()[
            LogicalDevice.Input.Identifier(self.input_type, self.input_id)
        ]
        # Update the state of the logical device and then emit the corresponding
        # event to trigger further processing.
        value = None
        match self.input_type:
            case InputType.JoystickAxis:
                if self.axis_mode == AxisMode.Absolute:
                    ld.update(self.value)
                elif self.axis_mode == AxisMode.Relative:
                    ld.update(max(-1.0, min(1.0, ld.value + self.value)))
                value = ld.value
            case InputType.JoystickButton:
                ld.update(self.value)
            case InputType.JoystickHat:
                ld.update(self.value)
                value = ld.direction

        is_pressed = (
            ld.is_pressed if self.input_type == InputType.JoystickButton else None
        )

        self._event_listener.joystick_event.emit(
            event_handler.Event(
                event_type=self.input_type,
                identifier=self.input_id,
                device_guid=LogicalDevice.device_guid,
                mode=self._mode_manager.current.name,
                value=value,
                is_pressed=is_pressed,
                raw_value=value,
            )
        )

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["input-type", self.input_type, PropertyType.InputType],
                ["input-id", self.input_id, PropertyType.Int],
            ],
        )
        if self.input_type == InputType.JoystickAxis:
            util.append_property_nodes(
                node,
                [
                    ["value", self.value, PropertyType.Float],
                    ["axis-mode", self.axis_mode, PropertyType.AxisMode],
                ],
            )
        elif self.input_type == InputType.JoystickButton:
            node.append(
                util.create_property_node("value", self.value, PropertyType.Bool)
            )
        elif self.input_type == InputType.JoystickHat:
            node.append(
                util.create_property_node(
                    "value", self.value, PropertyType.HatDirection
                )
            )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.input_type = util.read_property(node, "input-type", PropertyType.InputType)
        self.input_id = util.read_property(node, "input-id", PropertyType.Int)
        if self.input_type == InputType.JoystickAxis:
            self.value = util.read_property(node, "value", PropertyType.Float)
            self.axis_mode = util.read_property(
                node, "axis-mode", PropertyType.AxisMode
            )
        elif self.input_type == InputType.JoystickButton:
            self.value = util.read_property(node, "value", PropertyType.Bool)
        elif self.input_type == InputType.JoystickHat:
            self.value = util.read_property(node, "value", PropertyType.HatDirection)

    def is_valid(self) -> bool:
        return True


class MouseButtonAction(AbstractAction):
    """Mouse button action."""

    tag = "mouse-button"

    def __init__(self, button: MouseButton, is_pressed: bool) -> None:
        """Creates a new MouseButtonAction object for use in a macro.

        Args:
            button: the button to use in the action
            is_pressed: True if the button should be pressed, False otherwise
        """
        if not isinstance(button, MouseButton):
            raise error.MouseError("Invalid mouse button provided")

        self.button = button
        self.is_pressed = is_pressed

    @classmethod
    def create(cls) -> MouseButtonAction:
        return MouseButtonAction(MouseButton.Left, False)

    def __call__(self) -> None:
        if self.button == MouseButton.WheelDown:
            sendinput.mouse_wheel(1)
        elif self.button == MouseButton.WheelUp:
            sendinput.mouse_wheel(-1)
        else:
            if self.is_pressed:
                sendinput.mouse_press(self.button)
            else:
                sendinput.mouse_release(self.button)

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["button", MouseButton.to_string(self.button), PropertyType.String],
                ["is-pressed", self.is_pressed, PropertyType.Bool],
            ],
        )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.button = MouseButton.to_enum(
            util.read_property(node, "button", PropertyType.String)
        )
        self.is_pressed = util.read_property(node, "is-pressed", PropertyType.Bool)

    def is_valid(self) -> bool:
        return self.button is not None


class MouseMotionAction(AbstractAction):
    """Mouse motion action."""

    tag = "mouse-motion"

    def __init__(self, dx: float | int, dy: float | int) -> None:
        """Creates a new MouseMotionAction object for use in a macro.

        Args:
            dx: change along the X axis
            dy: change along the Y axis
        """
        self.dx = int(dx)
        self.dy = int(dy)

    @classmethod
    def create(cls) -> MouseMotionAction:
        return MouseMotionAction(0, 0)

    def __call__(self) -> None:
        sendinput.mouse_relative_motion(self.dx, self.dy)

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["dx", self.dx, PropertyType.Int],
                ["dy", self.dy, PropertyType.Int],
            ],
        )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.dx = util.read_property(node, "dx", PropertyType.Int)
        self.dy = util.read_property(node, "dy", PropertyType.Int)

    def is_valid(self) -> bool:
        return True


class PauseAction(AbstractAction):
    """Represents the pause in a macro between pressed."""

    tag = "pause"

    def __init__(self, duration: float) -> None:
        """Creates a new Pause object for use in a macro.

        Args:
            duration: the duration in seconds of the pause
        """
        self.duration = duration

    @classmethod
    def create(cls) -> PauseAction:
        return PauseAction(0.0)

    def __call__(self) -> None:
        time.sleep(self.duration)

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        node.append(
            util.create_property_node("duration", self.duration, PropertyType.Float)
        )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.duration = util.read_property(node, "duration", PropertyType.Float)

    def is_valid(self) -> bool:
        return True


class VJoyAction(AbstractAction):
    """VJoy input action for a macro."""

    tag = "vjoy"

    def __init__(
        self,
        vjoy_id: int,
        input_type: InputType,
        input_id: int,
        value: bool | float | tuple[int, int],
        axis_mode: AxisMode = AxisMode.Absolute,
    ) -> None:
        """Creates a new VJoyAction instance for use in a macro.

        Args:
            vjoy_id: id of the vjoy device which is to be modified
            input_type: type of input being generated
            input_id: id of the input being generated
            value: the value of the generated input
            axis_type: if an axis is used, how to interpret the value
        """
        self.vjoy_id = vjoy_id
        self.input_type = input_type
        self.input_id = input_id
        self.value = value
        self.axis_mode = axis_mode

    @classmethod
    def create(cls) -> VJoyAction:
        # FIXME: Implement a function returning a valid vJoy input
        return VJoyAction(1, InputType.JoystickButton, 1, False)

    def __call__(self) -> None:
        try:
            vid, iid = self.vjoy_id, self.input_id
            if self.input_type == InputType.JoystickAxis:
                if self.axis_mode == AxisMode.Absolute:
                    output.write_vjoy(vid, "axis", iid, self.value)
                elif self.axis_mode == AxisMode.Relative:
                    current = output.vjoy_value(vid, "axis", iid)
                    value = max(-1.0, min(1.0, current + self.value))
                    output.write_vjoy(vid, "axis", iid, value)
            elif self.input_type == InputType.JoystickButton:
                output.write_vjoy(vid, "button", iid, self.value)
            elif self.input_type == InputType.JoystickHat:
                output.write_vjoy(vid, "hat", iid, self.value)
        except Exception as e:
            # Once per error: a macro can repeat this many times a second.
            from gremlin.log_once import log_once

            log_once(
                "event", ("macro-vjoy", str(e)), logging.ERROR,
                f"Failed to execute vJoy macro entry due to: {e}",
            )

    def to_xml(self) -> ElementTree.Element:
        node = self._create_node(self.tag)
        util.append_property_nodes(
            node,
            [
                ["vjoy-id", self.vjoy_id, PropertyType.Int],
                ["input-type", self.input_type, PropertyType.InputType],
                ["input-id", self.input_id, PropertyType.Int],
            ],
        )
        if self.input_type == InputType.JoystickAxis:
            util.append_property_nodes(
                node,
                [
                    ["value", self.value, PropertyType.Float],
                    ["axis-mode", self.axis_mode, PropertyType.AxisMode],
                ],
            )
        elif self.input_type == InputType.JoystickButton:
            node.append(
                util.create_property_node("value", self.value, PropertyType.Bool)
            )
        elif self.input_type == InputType.JoystickHat:
            node.append(
                util.create_property_node(
                    "value", self.value, PropertyType.HatDirection
                )
            )
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        self.vjoy_id = util.read_property(node, "vjoy-id", PropertyType.Int)
        self.input_type = util.read_property(node, "input-type", PropertyType.InputType)
        self.input_id = util.read_property(node, "input-id", PropertyType.Int)
        if self.input_type == InputType.JoystickAxis:
            self.value = util.read_property(node, "value", PropertyType.Float)
            self.axis_mode = util.read_property(
                node, "axis-mode", PropertyType.AxisMode
            )
        elif self.input_type == InputType.JoystickButton:
            self.value = util.read_property(node, "value", PropertyType.Bool)
        elif self.input_type == InputType.JoystickHat:
            self.value = util.read_property(node, "value", PropertyType.HatDirection)

    def is_valid(self) -> bool:
        return True


class AbstractRepeat(ABC):
    """Base class for all macro repeat modes."""

    def __init__(self, delay: float) -> None:
        """Creates a new instance.

        Args:
            delay the delay between repetitions
        """
        self.delay = delay

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node encoding the repeat information.

        Returns:
            XML node containing the instance's information
        """
        node = ElementTree.Element("repeat")
        node.append(util.create_property_node("delay", self.delay, PropertyType.Float))
        self._to_xml_additional(node)
        return node

    def from_xml(self, node: ElementTree.Element) -> None:
        """Populates the instance's data from the provided XML node.

        Args:
            node: XML node containing data with which to populate the instance
        """
        self.delay = util.read_property(node, "delay", PropertyType.Float)
        self._from_xml_additional(node)

    @abstractmethod
    def _to_xml_additional(self, node: ElementTree.Element) -> None:
        pass

    @abstractmethod
    def _from_xml_additional(self, node: ElementTree.Element) -> None:
        pass


class CountRepeat(AbstractRepeat):
    """Repeat mode which repeats the macro a fixed number of times."""

    def __init__(self, count: int = 1, delay: float = 0.1) -> None:
        """Creates a new instance.

        Args:
            count: the number of times to repeat the macro
            delay: the delay between repetitions
        """
        super().__init__(delay)
        self.count = count

    def _to_xml_additional(self, node: ElementTree.Element) -> None:
        """Returns an XML node encoding the repeat information.

        Args:
            node: XML node containing the instance's information
        """
        node.set("type", "count")
        node.append(util.create_property_node("count", self.count, PropertyType.Int))

    def _from_xml_additional(self, node: ElementTree.Element) -> None:
        """Populates the instance's data from the provided XML node.

        Args:
            node: XML node containing data with which to populate the instance
        """
        self.count = util.read_property(node, "count", PropertyType.Int)


class ToggleRepeat(AbstractRepeat):
    """Repeat mode which repeats the macro as long as it hasn't been toggled
    off again after being toggled on."""

    def __init__(self, delay: float = 0.1) -> None:
        """Creates a new instance.

        Args:
            delay the delay between repetitions
        """
        super().__init__(delay)

    def _to_xml_additional(self, node: ElementTree.Element) -> None:
        """Returns an XML node encoding the repeat information.

        Args:
            node: XML node containing the instance's information
        """
        node.set("type", "toggle")

    def _from_xml_additional(self, node: ElementTree.Element) -> None:
        """Populates the instance's data from the provided XML node.

        Args:
            node: XML node containing data with which to populate the instance
        """
        pass


class HoldRepeat(AbstractRepeat):
    """Repeat mode which repeats the macro as long as the activation condition
    is being fulfilled or held down."""

    def __init__(self, delay: float = 0.1) -> None:
        """Creates a new instance.

        Args:
            delay the delay between repetitions
        """
        super().__init__(delay)

    def _to_xml_additional(self, node: ElementTree.Element) -> None:
        """Returns an XML node encoding the repeat information.

        Args:
            node: XML node containing the instance's information
        """
        node.set("type", "hold")

    def _from_xml_additional(self, node: ElementTree.Element) -> None:
        """Populates the instance's data from the provided XML node.

        Args:
            node XML node containing data with which to populate the instance
        """
        pass


Configuration().register(
    "action",
    "macro",
    "default-delay",
    PropertyType.Float,
    0.05,
    "The time (in seconds) macros wait between actions when no pauses are "
    + "present. Used by every profile that does not set its own delay "
    + "(Profile settings).",
    {"min": 0.0, "max": 10.0},
    True,
)
