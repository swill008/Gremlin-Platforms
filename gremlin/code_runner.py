# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import os
import sys
import time
from abc import (
    ABCMeta,
    abstractmethod,
)

import dill
from gremlin import (
    audio_player,
    device_initialization,
    error,
    event_handler,
    event_helpers,
    fsm,
    input_cache,
    macro,
    mode_manager,
    profile,
    sendinput,
    signal,
    tts,
    user_script,
)
from gremlin.base_classes import Value
from gremlin.config import Configuration
from gremlin.input_refresh import RefreshPhysicalInputs
from gremlin.modules import output
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.osc import OscRuntime
from gremlin.types import (
    ActionProperty,
    AxisButtonDirection,
    HatDirection,
    InputType,
)


class VirtualButton(metaclass=ABCMeta):
    """Implements a button like interface."""

    def __init__(self) -> None:
        """Creates a new instance."""
        self._fsm = self._initialize_fsm()

    def _initialize_fsm(self) -> fsm.FiniteStateMachine:
        """Initializes the state of the button FSM."""
        states = ["up", "down"]
        actions = ["press", "release"]

        def noop() -> bool:
            return False

        def press() -> bool:
            return True

        def release() -> bool:
            return True

        transitions = {
            ("up", "press"): fsm.Transition([press], "down"),
            ("up", "release"): fsm.Transition([noop], "up"),
            ("down", "release"): fsm.Transition([release], "up"),
            ("down", "press"): fsm.Transition([noop], "down"),
        }
        return fsm.FiniteStateMachine("up", states, actions, transitions)

    @abstractmethod
    def __call__(self, event: event_handler.Event) -> list[bool]:
        """Process the input event and updates the value as needed.

        Args:
            event: The input event to process

        Returns:
            List of states to process
        """
        pass


class VirtualAxisButton(VirtualButton):
    def __init__(
        self, lower_limit: float, upper_limit: float, direction: AxisButtonDirection
    ) -> None:
        super().__init__()
        self._lower_limit = lower_limit
        self._upper_limit = upper_limit
        self._direction = direction
        self._last_value = None

    def __call__(self, event: event_handler.Event) -> list[bool]:
        value = event.value if event.value is not None else 0.0
        forced_activation = False
        newly_initialized = False
        direction = AxisButtonDirection.Anywhere

        if self._last_value is None:
            newly_initialized = True
            self._last_value = event.value
        else:
            if self._last_value < self._lower_limit and value > self._upper_limit:
                forced_activation = True
            elif self._last_value > self._upper_limit and value < self._lower_limit:
                forced_activation = True

            if self._last_value < value:
                direction = AxisButtonDirection.Below
            elif self._last_value > event.value:
                direction = AxisButtonDirection.Above

        self._last_value = event.value

        states = []
        if forced_activation:
            self._fsm.perform("press")
            self._fsm.perform("release")
            states = [True, False]
        inside_range = self._lower_limit <= value <= self._upper_limit
        valid_direction = (
            direction == self._direction
            or self._direction == AxisButtonDirection.Anywhere
        )
        if inside_range and valid_direction:
            if newly_initialized:
                self._fsm.set_state("down")
            else:
                states = [True] if self._fsm.perform("press")[0] else []
        else:
            states = [False] if self._fsm.perform("release")[0] else []

        return states


class VirtualHatButton(VirtualButton):
    """Treats directional hat events as a button."""

    def __init__(self, directions: list[HatDirection]) -> None:
        super().__init__()
        self._directions = directions

    def __call__(self, event: event_handler.Event) -> list[bool]:
        is_pressed = event.value in self._directions
        action = "press" if is_pressed else "release"
        has_changed = self._fsm.perform(action)[0]
        return [is_pressed] if has_changed else []


class VirtualButtonFunctor:
    def __init__(
        self, virtual_button: VirtualButton, event_template: event_handler.Event
    ) -> None:
        self._virtual_button = virtual_button
        self._event_template = event_template
        self._event_listener = event_handler.EventListener()

    def __call__(self, event: event_handler.Event, value: Value) -> None:
        states = self._virtual_button(event)
        for state in states:
            new_event = self._event_template.clone()
            new_event.is_pressed = state
            new_event.raw_value = state
            self._event_listener.virtual_event.emit(new_event)


class CallbackObject:
    """Represents the callback executed in reaction to an input."""

    c_next_virtual_identifier = 1

    def __init__(self, binding: profile.InputItemBinding) -> None:
        self._binding = binding
        self._functor = None
        self._virtual_identifier = 0

        if self._binding.virtual_button is not None:
            self._virtual_identifier = CallbackObject.c_next_virtual_identifier
            CallbackObject.c_next_virtual_identifier += 1
            self._virtual_event_setup()
        else:
            self._physical_event_setup()

    @property
    def always_execute(self) -> bool:
        actions = self._binding.root_action.get_actions()[0]
        values = [ActionProperty.AlwaysExecute in a.properties for a in actions]
        return any(values)

    def __call__(self, event: event_handler.Event) -> None:
        values = self._generate_values(event)
        for i, value in enumerate(values):
            self._functor(event, value)
            if i < len(values) - 1:
                time.sleep(0.01)

    def _physical_event_setup(self) -> None:
        self._functor = self._binding.root_action.functor(self._binding.root_action)

    def _virtual_event_setup(self) -> None:
        if self._binding.input_item.mode is None:
            logging.getLogger("system").warning(
                "Virtual button configured for input item with no mode, ignoring."
            )
            return

        virtual_event = event_handler.Event(
            event_type=InputType.VirtualButton,
            identifier=self._virtual_identifier,
            device_guid=dill.UUID_Virtual,
            mode=self._binding.input_item.mode,
            is_pressed=False,
            raw_value=False,
        )

        vb_instance = self._binding.virtual_button
        if isinstance(vb_instance, profile.VirtualAxisButton):
            self._functor = VirtualButtonFunctor(
                VirtualAxisButton(
                    vb_instance.lower_limit,
                    vb_instance.upper_limit,
                    vb_instance.direction,
                ),
                virtual_event,
            )
        elif isinstance(vb_instance, profile.VirtualHatButton):
            self._functor = VirtualButtonFunctor(
                VirtualHatButton(vb_instance.directions),
                virtual_event,
            )
        else:
            raise error.GremlinError(
                "Attempting to create virtual event setup when no virtual "
                + "button is configured."
            )

        virt_item = profile.InputItem(self._binding.input_item.library)
        virt_item.device_id = dill.UUID_Virtual
        virt_item.input_type = InputType.VirtualButton
        virt_item.input_id = self._virtual_identifier
        virt_item.mode = self._binding.input_item.mode
        virt_item.action_sequences = [self._binding]
        virt_item.is_active = self._binding.input_item.is_active

        virt_binding = profile.InputItemBinding(virt_item)
        virt_binding.root_action = self._binding.root_action
        virt_binding.behavior = InputType.JoystickButton
        virt_binding.virtual_button = None

        eh = event_handler.EventHandler()
        eh.add_callback(
            dill.UUID_Virtual,
            self._binding.input_item.mode,
            virtual_event,
            CallbackObject(virt_binding),
        )

    def _generate_values(self, event: event_handler.Event) -> list[Value]:
        if event.event_type in [InputType.JoystickAxis, InputType.JoystickHat]:
            value = Value(event.value)
        elif event.event_type in [
            InputType.JoystickButton,
            InputType.Keyboard,
            InputType.VirtualButton,
        ]:
            value = Value(event.is_pressed)
        else:
            raise error.GremlinError("Invalid event type")

        return [value]


class CodeRunner:
    """Runs the actual profile code."""

    def __init__(self) -> None:
        self.event_handler = event_handler.EventHandler()
        self.event_handler.add_plugin(user_script.JoystickPlugin())
        self.event_handler.add_plugin(user_script.VJoyPlugin())
        self.event_handler.add_plugin(user_script.KeyboardPlugin())

        self._profile = None
        self._running = False
        self._mode_listening = False

    def is_running(self) -> bool:
        return self._running

    def start(self, profile: profile.Profile, start_mode: str) -> None:
        self._profile = profile
        self._reset_state()

        settings = self._profile.settings
        names = self._profile.modes.mode_names()
        if str(start_mode or "") not in names:
            start_mode = mode_manager.resolve_start_mode(self._profile)

        # The profile's own delay, or Options > Action > Macro when it has none.
        macro.MacroManager().default_delay = settings.effective_macro_delay()
        syslog = logging.getLogger("system")
        # Each run reads the output modules fresh and logs blocked outputs anew.
        output.refresh()
        output.clear_blocked_log()
        # Repeating problems may be logged once again in this run.
        from gremlin import log_once

        log_once.reset()

        try:
            self._setup_user_scripts()

            for mode_name in self._profile.modes.mode_names():
                self.event_handler.add_callback(0, mode_name, None, lambda x: x)

            callback_count = 0
            for dev_id, modes in user_script.callback_registry.registry.items():
                for mode, events in modes.items():
                    for event, callback_list in events.items():
                        for callback in callback_list.values():
                            self.event_handler.add_callback(
                                dev_id, mode, event, callback
                            )
                            callback_count += 1

            sequence_count = self._setup_profile()
            # Status, not a problem: Info, so it is not in a Warning log.
            syslog.info(
                "Gremlin start: %s UI sequences, %s script callbacks, mode=%s",
                sequence_count,
                callback_count,
                start_mode,
            )

            self.event_handler.build_event_lookup(self._profile.modes.mode_list())

            evt_listener = event_handler.EventListener()
            module_bus = InputModuleRuntime()
            module_bus.reload()
            # Joystick and keyboard events both come through the input
            # modules: only claimed inputs reach the profile.
            # Noted before connecting: stop() disconnects whenever this is
            # set, also after a start() that failed later on (they stayed
            # connected, and the next Run handled every event twice).
            self._connected = True
            module_bus.event.connect(self.event_handler.process_event)
            module_bus.key_event.connect(self.event_handler.process_event)
            evt_listener.virtual_event.connect(self.event_handler.process_event)
            evt_listener.gremlin_active = True

            user_script.periodic_registry.start()
            macro.MacroManager().start()
            audio_player.AudioPlayer().start()
            tts.TTSManager().start()

            # Listening before the first switch and after the other listeners
            # (connected when they were made), as when the mode manager did it.
            self._listen_to_mode_changes(True)
            mode_manager.ModeManager().switch_to(
                mode_manager.Mode(start_mode, "Default")
            )
            self.event_handler.resume()
            self._running = True

            sendinput.MouseController().start()
            OscRuntime().start()
            self._refresh_axes()
        except ImportError as e:
            signal.display_error(
                "Could not run the profile: a user plugin is missing.", str(e)
            )
        except Exception:
            syslog.exception("Gremlin start failed")
            raise

    def stop(self) -> None:
        self._listen_to_mode_changes(False)
        if getattr(self, "_connected", False):
            evt_lst = event_handler.EventListener()
            bus = InputModuleRuntime()
            for sig in (bus.event, bus.key_event, evt_lst.virtual_event):
                try:
                    sig.disconnect(self.event_handler.process_event)
                except (TypeError, RuntimeError):
                    pass
            evt_lst.gremlin_active = False
            self._connected = False
        if self._running:
            # The last mode, kept in memory during play, is saved now.
            from gremlin import mode_manager

            mode_manager.flush_last_modes()
        self._running = False

        user_script.callback_registry.clear()
        self.event_handler.clear()

        user_script.periodic_registry.stop()
        user_script.periodic_registry.clear()

        OscRuntime().stop()
        macro.MacroManager().stop()
        sendinput.MouseController().stop()
        audio_player.AudioPlayer().stop()
        tts.TTSManager().stop()

        output.reset_drivers()

    def _reset_state(self) -> None:
        self.event_handler._active_mode = self._profile.modes.first_mode
        self.event_handler._previous_mode = self._profile.modes.first_mode
        user_script.callback_registry.clear()
        event_helpers.ButtonReleaseActions().reset()

    def _listen_to_mode_changes(self, on: bool) -> None:
        if on == self._mode_listening:
            return
        mm = mode_manager.ModeManager()
        if on:
            mm.mode_changed.connect(self._refresh_on_mode_change)
        else:
            mm.mode_changed.disconnect(self._refresh_on_mode_change)
        self._mode_listening = on

    def _refresh_on_mode_change(self, _mode: str) -> None:
        if Configuration().value("global", "general", "refresh-axis-on-mode-change"):
            RefreshPhysicalInputs.refresh_axes()

    def _refresh_axes(self) -> None:
        vjoy_state = {}
        for vjoy_dev in device_initialization.vjoy_devices():
            vjoy_state[vjoy_dev.vjoy_id] = {}
            cache_dev = input_cache.Joystick()[vjoy_dev.device_guid.uuid]
            for entry in vjoy_dev.axis_map:
                if entry.axis_index == 0:
                    continue
                vjoy_state[vjoy_dev.vjoy_id][entry.axis_index] = cache_dev.axis(
                    entry.axis_index
                ).value

        if Configuration().value("global", "general", "refresh-axis-on-activation"):
            RefreshPhysicalInputs.refresh_axes()

        for vid, data in self._profile.settings.vjoy_initial_values.items():
            for aid, value in data.items():
                if value != 0.0 and vjoy_state.get(vid, {}).get(aid) == 0.0:
                    output.write_vjoy_axis_linear(vid, aid, value)

    def _setup_user_scripts(self) -> None:
        system_paths = [os.path.normcase(os.path.abspath(p)) for p in sys.path]

        syslog = logging.getLogger("system")
        user_script.periodic_registry.clear()
        for script in self._profile.scripts.scripts:
            # Tried again here: the file may have been fixed since loading.
            if script.load_error and not script.retry():
                syslog.warning(f"Script '{script.name}' not run: {script.load_error}")
                continue
            if not script.is_configured:
                continue

            script_folder = str(script.path.parent)
            if script_folder not in system_paths:
                system_paths.append(script_folder)

            if not script.reload():
                syslog.warning(f"Script '{script.name}' not run: {script.load_error}")

        sys.path = system_paths

    def _setup_profile(self) -> int:
        item_list = sum(self._profile.inputs.values(), [])
        action_sequences = sum([e.action_sequences for e in item_list], [])
        syslog = logging.getLogger("system")

        for action in action_sequences:
            event = event_handler.Event(
                event_type=action.input_item.input_type,
                device_guid=action.input_item.device_id,
                identifier=action.input_item.input_id,
                mode=action.input_item.mode,
            )
            self.event_handler.add_callback(
                event.device_guid, action.input_item.mode, event, CallbackObject(action)
            )

        if action_sequences:
            sample = action_sequences[0].input_item
            syslog.info(
                "First sequence device=%s type=%s id=%s mode=%s",
                sample.device_id,
                sample.input_type,
                sample.input_id,
                sample.mode,
            )
        return len(action_sequences)
