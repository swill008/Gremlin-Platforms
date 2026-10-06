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
from typing import Any

import dill
from gremlin import (
    audio_player,
    base_classes,
    common,
    device_initialization,
    error,
    event_handler,
    event_helpers,
    fsm,
    logical_device,
    macro,
    mode_manager,
    profile,
    run_scope,
    sendinput,
    shared_state,
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
    """Treats a range of an axis as a button (06 S39).

    Entering the range (in the chosen direction) presses, leaving releases
    and a jump across the range in one step presses and releases. An axis
    already inside the range at Run gives no press, and leaving it then
    gives no release (D-06-S39-NORELEASE).
    """

    def __init__(
        self, lower_limit: float, upper_limit: float, direction: AxisButtonDirection
    ) -> None:
        super().__init__()
        self._lower_limit = lower_limit
        self._upper_limit = upper_limit
        self._direction = direction
        self._last_value: float | None = None
        # Inside the range at Run: no press until it leaves and re-enters.
        self._held_from_start = False

    def __call__(self, event: event_handler.Event) -> list[bool]:
        value = float(event.value) if isinstance(event.value, (int, float)) else 0.0
        inside_range = self._lower_limit <= value <= self._upper_limit

        if self._last_value is None:
            # First value of the Run: nothing is sent, inside or not.
            self._last_value = value
            self._held_from_start = inside_range
            return []

        last = self._last_value
        self._last_value = value
        direction = AxisButtonDirection.Anywhere
        if last < value:
            direction = AxisButtonDirection.Below
        elif last > value:
            direction = AxisButtonDirection.Above
        valid_direction = (
            direction == self._direction
            or self._direction == AxisButtonDirection.Anywhere
        )

        jumped = (last < self._lower_limit and value > self._upper_limit) or (
            last > self._upper_limit and value < self._lower_limit
        )
        if jumped:
            if not valid_direction:
                return []
            self._fsm.perform("press")
            self._fsm.perform("release")
            return [True, False]

        if self._held_from_start:
            if not inside_range:
                self._held_from_start = False
            return []
        if inside_range and valid_direction:
            return [True] if self._fsm.perform("press")[0] else []
        if inside_range:
            return []
        # The FSM is "up" unless a press was sent, so a release only
        # follows a press.
        return [False] if self._fsm.perform("release")[0] else []


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
        root = self._binding.root_action
        # Unfinished actions are left out of the Run (05 Q3); base_classes
        # logs one line each, naming this input.
        with base_classes.building_for(_where(self._binding.input_item)):
            self._functor = root.functor(root)

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


def run_number() -> int:
    """The current Run's number (a different one after Stop). The one Run
    number is run_scope's; this forwards to it."""
    return run_scope.number()


def __getattr__(name: str) -> object:
    # TODO(batch1): test/conftest.py reads code_runner._run_number to tell
    # whether a test ran or stopped a Run; it should read run_scope.number().
    if name == "_run_number":
        return run_scope.number()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _where(item: Any) -> str:  # noqa: ANN401
    """"<device> <control> (<mode>)" for an input, for the log."""
    device = str(item.device_id)
    try:
        for dev in device_initialization.joystick_devices():
            if dev.device_guid.uuid == item.device_id:
                device = dev.name
                break
    except Exception:
        pass
    try:
        control = common.input_to_ui_string(item.input_type, item.input_id)
    except Exception:
        control = f"{getattr(item.input_type, 'name', item.input_type)} {item.input_id}"
    return f"{device} {control} ({item.mode})"


class CodeRunner:
    """Runs the actual profile code.

    What a Run starts is registered with run_scope, and Stop is
    run_scope.stop(): the same fixed stages from the Stop button, a failed
    start and quitting (map 3).
    """

    def __init__(self) -> None:
        self.event_handler = event_handler.EventHandler()
        self.event_handler.add_plugin(user_script.JoystickPlugin())
        self.event_handler.add_plugin(user_script.VJoyPlugin())
        self.event_handler.add_plugin(user_script.KeyboardPlugin())

        self._profile = None
        self._running = False
        self._mode_listening = False
        self._connected = False
        self._config_listening = False
        self._sys_path: list[str] | None = None

    def is_running(self) -> bool:
        return self._running

    def start(self, profile: profile.Profile, start_mode: str) -> None:
        """Runs the profile in start_mode (the toolbar mode).

        A start that fails partway runs Stop itself, shows one error and
        leaves the runner stopped (06 Q5); the error is raised again for the
        caller, except a missing user plugin, which is only shown.
        """
        # A Run never stopped (a failed start, Run pressed twice) ends first:
        # its signals would otherwise be connected twice.
        self.stop()
        run_scope.begin()
        # Registered before anything starts: a start that fails partway is
        # undone by the same Stop.
        self._register_stop()
        self._profile = profile
        try:
            self._start(profile, start_mode)
        except ImportError as e:
            logging.getLogger("system").exception("Gremlin start failed")
            self.stop()
            signal.display_error(
                "Could not run the profile: a user plugin is missing.", str(e)
            )
        except Exception as e:
            logging.getLogger("system").exception("Gremlin start failed")
            self.stop()
            signal.display_error(
                "Could not run the profile.", str(e) or type(e).__name__
            )
            raise

    def _start(self, running: profile.Profile, start_mode: str) -> None:
        self._reset_state()

        settings = running.settings
        names = running.modes.mode_names()
        if str(start_mode or "") not in names:
            start_mode = mode_manager.resolve_start_mode(running)

        # The profile's own delay, or Options > Action > Macro when it has none.
        macro.MacroManager().default_delay = settings.effective_macro_delay()
        syslog = logging.getLogger("system")
        # Each run reads the output modules fresh and logs blocked outputs anew.
        output.refresh()
        output.clear_blocked_log()
        # Output modules saved while running apply at once (06 Q12).
        self._listen_to_config(True)
        # Repeating problems may be logged once again in this run.
        from gremlin import log_once

        log_once.reset()

        self._setup_user_scripts()

        for mode_name in running.modes.mode_names():
            self.event_handler.add_callback(0, mode_name, None, lambda x: x)

        callback_count = 0
        for dev_id, modes in user_script.callback_registry.registry.items():
            for mode, events in modes.items():
                for event, callback_list in events.items():
                    for callback in callback_list.values():
                        self.event_handler.add_callback(dev_id, mode, event, callback)
                        callback_count += 1

        sequence_count = self._setup_profile()
        # Status, not a problem: Info, so it is not in a Warning log.
        syslog.info(
            "Gremlin start: %s UI sequences, %s script callbacks, mode=%s",
            sequence_count,
            callback_count,
            start_mode,
        )

        self.event_handler.build_event_lookup(running.modes.mode_list())

        evt_listener = event_handler.EventListener()
        module_bus = InputModuleRuntime()
        module_bus.reload()
        # Joystick and keyboard events both come through the input
        # modules: only claimed inputs reach the profile.
        # Noted before connecting: Stop disconnects whenever this is set.
        self._connected = True
        module_bus.event.connect(self.event_handler.process_event)
        module_bus.key_event.connect(self.event_handler.process_event)
        evt_listener.virtual_event.connect(self.event_handler.process_event)
        evt_listener.gremlin_active = True

        user_script.periodic_registry.start()
        macro.MacroManager().start()
        audio_player.AudioPlayer().start()
        tts.TTSManager().start()

        # The toolbar mode, on a fresh mode stack (06 Q3, decision R3).
        mode_manager.ModeManager().start_run(start_mode)
        # Mode changes refresh the axes from here on (after the other
        # listeners, connected when they were made). The start itself is not
        # one: the axes are sent once, after the Initial Values (06 S8).
        self._listen_to_mode_changes(True)
        self.event_handler.resume()
        self._running = True
        shared_state.set_runtime_active(True)

        sendinput.MouseController().start()
        OscRuntime().start()
        self._refresh_axes()

    def stop(self) -> None:
        """Ends the Run: run_scope runs the Stop stages. Safe to call twice."""
        run_scope.stop()
        self._running = False

    def _register_stop(self) -> None:
        """What Stop does for this Run, stage by stage (map 3).

        The parts are looked up when Stop runs, not now.
        """
        on = run_scope.on_stop
        stage = run_scope.Stage
        on(stage.CUT_INPUT, "input off", self._cut_input)
        on(stage.CANCEL, "release actions", self._drop_release_actions)
        on(stage.CANCEL, "script state", self._end_scripts)
        on(stage.CANCEL, "OSC", lambda: OscRuntime().stop())
        on(stage.FIRE_PENDING, "pulse releases", self._flush_pulses)
        on(stage.END_WORK, "macros", lambda: macro.MacroManager().stop())
        on(stage.END_WORK, "mouse motion", lambda: sendinput.MouseController().stop())
        on(stage.NEUTRAL, "Logical Device", self._logical_device_neutral)
        on(stage.NEUTRAL, "modes", lambda: mode_manager.ModeManager().end_run())
        on(stage.NEUTRAL, "sound", lambda: audio_player.AudioPlayer().stop())
        on(stage.NEUTRAL, "speech", lambda: tts.TTSManager().stop())
        on(stage.DRIVERS, "drivers", lambda: output.reset_drivers())

    def _cut_input(self) -> None:
        self._listen_to_mode_changes(False)
        self._listen_to_config(False)
        if self._connected:
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
        shared_state.set_runtime_active(False)
        self.event_handler.clear()

    def _drop_release_actions(self) -> None:
        # Release actions waiting at Stop are dropped (decision R2): the held
        # outputs are released and the drivers reset anyway.
        event_helpers.ButtonReleaseActions().reset()

    def _end_scripts(self) -> None:
        # Script callbacks and timers end with the Run; sys.path is put back
        # (the script folders were added for this Run only).
        user_script.callback_registry.clear()
        user_script.periodic_registry.stop()
        user_script.periodic_registry.clear()
        if self._sys_path is not None:
            sys.path = self._sys_path
            self._sys_path = None

    def _flush_pulses(self) -> None:
        # TODO(batch1): pulse releases become run_scope timers with
        # at_stop="fire" (base_classes); until then they are flushed here.
        flush = getattr(base_classes, "flush_pulses", None)
        if callable(flush):
            flush()

    def _logical_device_neutral(self) -> None:
        # Decision R1: the next Run starts from rest (06 S85).
        device = logical_device.LogicalDevice()
        reset_values = getattr(device, "reset_values", None)
        if callable(reset_values):
            reset_values()

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

    def _listen_to_config(self, on: bool) -> None:
        if on == self._config_listening:
            return
        changed = signal.signal.configChanged
        if on:
            changed.connect(self._refresh_outputs)
        else:
            try:
                changed.disconnect(self._refresh_outputs)
            except (TypeError, RuntimeError):
                pass
        self._config_listening = on

    def _refresh_outputs(self) -> None:
        # A module file saved while running: its claims count from now on.
        output.refresh()

    def _refresh_on_mode_change(self, _mode: str) -> None:
        if Configuration().value("global", "general", "refresh-axis-on-mode-change"):
            RefreshPhysicalInputs.refresh_axes()

    def _refresh_axes(self) -> None:
        # vJoy Initial Values first, always, through the output module (06
        # S8, Q7); the physical axes sent after them then override them.
        for vid, data in self._profile.settings.vjoy_initial_values.items():
            for aid, value in data.items():
                output.write_vjoy_axis_linear(vid, aid, value)

        if Configuration().value("global", "general", "refresh-axis-on-activation"):
            RefreshPhysicalInputs.refresh_axes()

    def _setup_user_scripts(self) -> None:
        # Put back at Stop: a script folder belongs to this Run only (GL-062).
        if self._sys_path is None:
            self._sys_path = list(sys.path)
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

            script_folder = os.path.normcase(os.path.abspath(script.path.parent))
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
