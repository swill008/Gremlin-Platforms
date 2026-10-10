# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import copy
import functools
import heapq
import importlib
import importlib.machinery
import importlib.util
import inspect
import logging
import numbers
import random
import string
import sys
import threading
import types
import uuid
import weakref
from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import (
    Any,
    Callable,
    override,
)
from xml.etree import ElementTree

from PySide6 import QtCore

import dill
import gremlin.keyboard
from gremlin import (
    clock,
    error,
    event_handler,
    osc_output,
    osc_pattern,
    run_scope,
    shared_state,
    threads,
    util,
)
from gremlin.edits import EditNoted, note_edit
from gremlin.log_once import log_once
from gremlin.logical_device import LogicalDevice, resolve_logical_reference
from gremlin.modules import inputs, output
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.osc_rows import OscRow
from gremlin.types import (
    HatDirection,
    InputType,
    PropertyType,
)


def _resolve_path(script_path: Path) -> Path:
    """If script_path is relative, resolve (not strictly) it to the standard
    scripts directory."""
    if script_path.is_absolute():
        return script_path
    return util.scripts_dir() / script_path


def _saved_path(script_path: Path) -> Path:
    """script_path as the profile saves it: relative to the scripts folder
    when inside it (D-04-S86-RELATIVE), else the full path."""
    try:
        return script_path.relative_to(util.scripts_dir())
    except ValueError:
        return script_path


def _current_script_id() -> uuid.UUID | None:
    """Returns the id of the Script currently executing, if any."""
    # A callback its top-level code registered, added after that code ran.
    identifier = getattr(_top_level, "script_id", None)
    if identifier is not None:
        return identifier
    # The frames themselves, not inspect.stack(): that reads every frame's
    # source and resolves the path of every loaded module, seconds in the
    # program while the main thread runs (a script now starts beside it,
    # D-04-Q13-NOWAIT).
    frame = sys._getframe(1)
    while frame is not None:
        identifier = frame.f_locals.get("_script_id", None)
        if isinstance(identifier, uuid.UUID):
            return identifier
        frame = frame.f_back
    return None


class CallbackRegistry:
    """Registry of all callbacks known to the system."""

    def __init__(self) -> None:
        """Creates a new callback registry instance."""
        self._registry = {}
        self._current_id = 0

    def add(self, callback: Callable, event: event_handler.Event, mode: str) -> None:
        """Adds a new callback to the registry.

        Args:
            callback: function to add as a callback
            event: the event on which to trigger the callback
            mode: the mode in which to trigger the callback
        """
        self._current_id += 1
        function_name = f"{callback.__name__}_{self._current_id:d}"

        if event.device_guid not in self._registry:
            self._registry[event.device_guid] = {}
        if mode not in self._registry[event.device_guid]:
            self._registry[event.device_guid][mode] = {}
        if event not in self._registry[event.device_guid][mode]:
            self._registry[event.device_guid][mode][event] = {}

        self._registry[event.device_guid][mode][event][function_name] = callback

    @property
    def registry(self) -> dict:
        """Returns the registry dictionary.

        Returns:
            The callback registry dictionary
        """
        return self._registry

    def clear(self) -> None:
        """Clears the registry entries."""
        self._registry = {}


# The shortest interval a periodic callback runs at (seconds).
_SHORTEST_INTERVAL = 0.01


class PeriodicRegistry:
    """Registry for periodically executed functions."""

    def __init__(self) -> None:
        """Creates a new instance."""
        self._registry = {}
        self._registry_lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._queue = []
        self._plugins = []
        # Each start has its own loop: one still finishing a slow callback
        # after Stop ends by itself and never runs the new Run's callbacks.
        # It ends with its Run too (run_scope's number, the one Run counter).
        self._loop: object | None = None

    def start(self) -> None:
        """Starts the event loop."""
        # Only proceed if we have functions to call
        if len(self._registry) == 0:
            return

        self._running = True
        loop = object()
        self._loop = loop
        self._thread = run_scope.loop(
            "user script timers",
            self._thread_loop,
            loop,
            stop=self._ask_to_stop,
        )

    def _ask_to_stop(self) -> None:
        self._running = False

    def stop(self) -> None:
        """Stops the event loop."""
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def add(self, callback: Callable, interval: float) -> None:
        """Adds a function to execute periodically.

        Args:
            callback: the function to execute
            interval: the time in seconds between executions
        """
        script_id = _current_script_id()
        key = (script_id, callback.__name__) if script_id is not None else callback
        if not interval or interval < _SHORTEST_INTERVAL:
            # 0 or less ran the callback without end, and Stop couldn't end it.
            logging.getLogger("system").warning(
                f"Periodic callback {callback.__name__}: interval {interval} is "
                f"too short; {_SHORTEST_INTERVAL} s is used."
            )
            interval = _SHORTEST_INTERVAL
        with self._registry_lock:
            self._registry[key] = (interval, callback)

    def clear(self) -> None:
        """Clears the registry."""
        with self._registry_lock:
            self._registry = {}

    def _install_plugins(self, callback: Callable) -> Callable:
        """Installs the current plugins into the given callback.

        Args:
            callback: the callback function to install the plugins into

        Returns:
            new callback with plugins installed
        """
        signature = inspect.signature(callback).parameters
        partial_fn = functools.partial
        if "self" in signature:
            partial_fn = functools.partialmethod
        for plugin in self._plugins:
            if plugin.keyword in signature:
                callback = plugin.install(callback, partial_fn)
        return callback

    def _thread_loop(self, run: int, loop: object = None) -> None:
        """Main execution loop run in a separate thread (run: its Run's
        number, loop: this start's own token)."""
        # Setup plugins to use
        self._plugins = [JoystickPlugin(), VJoyPlugin(), KeyboardPlugin(), OscPlugin()]
        callback_interval = {}

        # Populate the queue, adding an index to each callback to tie break
        # entries with identical execution times.
        self._queue = []
        with self._registry_lock:
            for index, item in enumerate(self._registry.values()):
                plugin_cb = self._install_plugins(item[1])
                callback_interval[plugin_cb] = item[0]
                heapq.heappush(
                    self._queue, (clock.monotonic() + item[0], index, plugin_cb)
                )

        queue = self._queue

        def current() -> bool:
            return self._running and self._loop is loop and run_scope.alive(run)

        while current():
            # Capture the current timestamp for reuse in the sleep down below.
            while current() and queue[0][0] < (now := clock.monotonic()):
                deadline, index, callback = heapq.heappop(queue)
                try:
                    callback()
                except Exception as e:
                    logging.getLogger("system").exception(
                        f"Periodic callback raised an exception: {e}"
                    )
                # One slower than its interval runs again from now, instead
                # of catching up without end.
                next_at = max(
                    deadline + callback_interval[callback], clock.monotonic()
                )
                heapq.heappush(queue, (next_at, index, callback))
            if not current():
                break

            # Sleep until either the next function needs to be run or
            # our timeout expires
            clock.sleep(max(0.0, min(queue[0][0] - now, 1.0)))


callback_registry = CallbackRegistry()
periodic_registry = PeriodicRegistry()


def forget_other_scripts(scripts: list[Script]) -> None:
    """Script state that belongs to no script of the open profile goes
    (profile load): script settings of the profile open before, and the
    callbacks and timers of a Run (CodeRunner ends those at Stop)."""
    callback_registry.clear()
    periodic_registry.stop()
    periodic_registry.clear()
    Script.variable_registry.keep_only({script.id for script in scripts})


class JoystickDecorator:
    """Creates customized decorators for physical joystick devices."""

    def __init__(self, name: str, device_guid: str, mode: str) -> None:
        """Creates a new instance with customized decorators.

        Args:
            name: name of the device
            device_guid: the device's guid in the system
            mode: the mode in which the decorated functions should be active
        """
        self.name = name
        self.mode = mode

        # Convert string-based GUID to the actual GUID object
        try:
            self.device_guid = uuid.UUID(device_guid)
        except ValueError:
            logging.getLogger("system").error(
                f"Invalid guid value '{device_guid}' received."
            )
            self.device_guid = dill.UUID_Invalid

        # Create decorators for the different input types
        self.axis = functools.partial(
            _input_callback,
            device_guid=self.device_guid,
            input_type=InputType.JoystickAxis,
            mode=self.mode,
        )
        self.button = functools.partial(
            _input_callback,
            device_guid=self.device_guid,
            input_type=InputType.JoystickButton,
            mode=self.mode,
        )
        self.hat = functools.partial(
            _input_callback,
            device_guid=self.device_guid,
            input_type=InputType.JoystickHat,
            mode=self.mode,
        )


class VJoyPlugin:
    """Plugin giving scripts vJoy access through the output modules.

    For a function to use this plugin it requires one of its parameters
    to be named "vjoy".
    """

    vjoy = output.ScriptVJoy()

    def __init__(self) -> None:
        self.keyword = "vjoy"

    def install(self, callback: Callable, partial_fn: Callable) -> Callable:
        """Decorates the given callback function to provide access to
        the firewalled vJoy object.

        Only if the signature contains the plugin's keyword is the
        decorator applied.

        Args:
            callback: the callback to decorate
            partial_fn: function to create the partial function / method

        Returns:
            callback with the plugin parameter bound
        """
        return partial_fn(callback, vjoy=VJoyPlugin.vjoy)


class JoystickPlugin:
    """Plugin providing automatic access to the Joystick object.

    For a function to use this plugin it requires one of its parameters
    to be named "joy".
    """

    joystick = inputs.ScriptJoystick()

    def __init__(self) -> None:
        self.keyword = "joy"

    def install(self, callback: Callable, partial_fn: Callable) -> Callable:
        """Decorates the given callback function to provide access
        to the Joystick object.

        Only if the signature contains the plugin's keyword is the
        decorator applied.

        Args:
            callback: the callback to decorate
            partial_fn: function to create the partial function / method

        Returns:
            callback with the plugin parameter bound
        """
        return partial_fn(callback, joy=JoystickPlugin.joystick)


class KeyboardPlugin:
    """Plugin providing automatic access to the Keyboard object.

    For a function to use this plugin it requires one of its parameters
    to be named "keyboard".
    """

    keyboard = inputs.ScriptKeyboard()

    def __init__(self) -> None:
        self.keyword = "keyboard"

    def install(self, callback: Callable, partial_fn: Callable) -> Callable:
        """Decorates the given callback function to provide access to
        the Keyboard object.

        Args:
            callback: the callback to decorate
            partial_fn: function to create the partial function / method

        Returns:
            callback with the plugin parameter bound
        """
        return partial_fn(callback, keyboard=KeyboardPlugin.keyboard)


class ScriptOsc:
    """Scripts' OSC output (09 S163): to a named target only, through
    osc_output, so the OSC output switch applies and the Monitor shows the
    message as Out. No raw host and port, no reply to the sender."""

    def send(
        self,
        target_name: str,
        address: str,
        *values: object,
        types: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        """Sends address with values to the target named target_name.

        types gives each value's type (auto/int/float/bool/text). Returns
        True when the message went out: False with OSC output off, no Run,
        an unknown target or an address that isn't a plain OSC address.
        """
        reason = osc_pattern.check(address, allow_pattern=False)
        if reason:
            log_once(
                "user",
                ("script-osc-address", str(address)),
                logging.WARNING,
                f"Script OSC send to '{address}' refused: {reason}",
            )
            return False
        target_id = self._target_id(target_name)
        if target_id is None:
            log_once(
                "user",
                ("script-osc-target", str(target_name)),
                logging.WARNING,
                f"Script OSC send refused: no OSC target named '{target_name}'.",
            )
            return False
        return osc_output.send(target_id, address, values, types)

    @staticmethod
    def _target_id(target_name: str) -> str | None:
        """The id of the target with this name (any case), or None."""
        name = str(target_name or "").strip().casefold()
        if not name:
            return None
        _, targets = osc_output._settings()  # noqa: SLF001 - the one reader
        for target in targets:
            if str(target.get("name") or "").strip().casefold() == name:
                target_id = target.get("id")
                return str(target_id) if target_id else None
        return None


# The object scripts use: the "osc" callback parameter, or import it.
osc = ScriptOsc()


class OscPlugin:
    """Plugin giving scripts OSC output (09 S163).

    For a function to use this plugin it requires one of its parameters
    to be named "osc".
    """

    def __init__(self) -> None:
        self.keyword = "osc"

    def install(self, callback: Callable, partial_fn: Callable) -> Callable:
        """Binds the script OSC object to the callback's "osc" parameter.

        Args:
            callback: the callback to decorate
            partial_fn: function to create the partial function / method

        Returns:
            callback with the plugin parameter bound
        """
        return partial_fn(callback, osc=osc)


class ScriptVariableRegistry:
    def __init__(self) -> None:
        self._registry = {}

    def clear(self) -> None:
        """Clears all registry entries."""
        self._registry = {}

    def register_script(self, script: Script) -> None:
        """Registers all variables of a script.

        This will forcibly overwrite existing entries for the same script.

        Args:
            script: the Script instance to register
        """
        self._registry[script.id] = {}
        for variable in script.variables.values():
            self._registry[script.id][variable.name] = variable

    def keep_only(self, script_ids: set[uuid.UUID]) -> None:
        """Forgets the variables of every script not in script_ids (a
        script of those still starting registers none when it has)."""
        for script in list(_starting_scripts):
            if script.id not in script_ids:
                script._drop_start()
        for script_id in [k for k in self._registry if k not in script_ids]:
            del self._registry[script_id]

    def remove_script(self, script: Script) -> None:
        """Removes the specified script's variables.

        Args:
            script: the script to remove variables for
        """
        # Still starting: it registers none when it has.
        script._drop_start()
        if script.id in self._registry:
            del self._registry[script.id]

    def set(self, script_id: uuid.UUID, variable: AbstractVariable) -> None:
        """Stores a variable in the registry.

        Args:
            script_id: unique identifier of the script
            variable: the variable to register
        """
        if script_id not in self._registry:
            self._registry[script_id] = {}
        self._registry[script_id][variable.name] = variable

    def get(self, script_id: uuid.UUID, name: str) -> AbstractVariable | None:
        """Returns a variable from the registry.

        Args:
            script_id: unique identifier of the script
            name: the name of the variable to retrieve

        Returns:
            Variable instance corresponding to the script and name
        """
        if script_id not in self._registry:
            return None
        return self._registry[script_id].get(name, None)


def rename_mode_settings(script: Script, old_name: str, new_name: str) -> None:
    """A script's mode settings naming old_name follow the new name, both
    the loaded ones and those kept as saved (a script that could not be
    loaded wrote the old name back on save)."""
    for variable in script.variables.values():
        if isinstance(variable, ModeVariable) and variable.value == old_name:
            variable.value = new_name
    for saved in getattr(script, "_saved_variables", ()):
        if saved.get("type") != ModeVariable.xml_tag:
            continue
        value = saved.find("./property/name[.='value']/../value")
        if value is not None and value.text == old_name:
            value.text = new_name


def describe_load_error(error_: BaseException, path: Path) -> str:
    """Why a script could not be loaded, in words for the Scripts page."""
    if isinstance(error_, FileNotFoundError) or not path.is_file():
        return "File not found"
    if isinstance(error_, SyntaxError):
        return f"Syntax error, line {error_.lineno}: {error_.msg}"
    if isinstance(error_, error.GremlinError):
        # Its text itself: str() of a GremlinError is quoted.
        return str(error_.value).removeprefix("Script: ")
    return f"{type(error_).__name__}: {error_}"


# Seconds a script's top-level code may take when the script is loaded or
# added (D-04-Q13-TIMELIMIT), and when Run reloads it (D-04-Q13-RUNLIMIT).
# Longer, and the script is marked as failed.
TOP_LEVEL_TIME_LIMIT = 5.0

# Set on a thread running a script's top-level code: the callbacks its
# decorators register, added only once the code finished in time.
_top_level = threading.local()


def _register(add: Callable[[], None]) -> None:
    """Registers a decorated callback now, or once the top-level code
    running on this thread has finished in time (never, when it hasn't)."""
    pending = getattr(_top_level, "pending", None)
    if pending is None:
        add()
    else:
        pending.append((_current_script_id(), add))


class _TopLevel:
    """A script's top-level code running on its own thread."""

    def __init__(
        self,
        spec: importlib.machinery.ModuleSpec,
        module: types.ModuleType,
        name: str,
        on_done: Callable[[_TopLevel], None] | None = None,
    ) -> None:
        self.spec = spec
        self.module = module
        self.limit = TOP_LEVEL_TIME_LIMIT
        self.deadline = clock.monotonic() + self.limit
        self.done = threading.Event()
        self.raised: list[BaseException] = []
        self.pending: list[tuple[uuid.UUID | None, Callable[[], None]]] = []
        self._on_done = on_done
        threads.start(f"script {name}", self._run)

    def _run(self) -> None:
        _top_level.pending = self.pending
        try:
            self.spec.loader.exec_module(self.module)
        except BaseException as e:
            self.raised.append(e)
        finally:
            self.done.set()
            if self._on_done is not None:
                self._on_done(self)

    def wait(self) -> None:
        """Waits for the code until the time limit at most (from its start)."""
        self.done.wait(max(0.0, self.deadline - clock.monotonic()))

    def finish(self) -> None:
        """Raises what the code raised, or a GremlinError when it hasn't
        finished (that thread ends whenever the code does, and the callbacks
        it registers are dropped); else registers those callbacks."""
        if not self.done.is_set():
            raise error.GremlinError(
                f"Script: Its top-level code did not finish within "
                f"{self.limit:g} s (it may loop or wait)"
            )
        if self.raised:
            raise self.raised[0]
        for script_id, add in self.pending:
            _top_level.script_id = script_id
            try:
                add()
            finally:
                _top_level.script_id = None


def _run_top_level(
    spec: importlib.machinery.ModuleSpec, module: types.ModuleType, name: str
) -> None:
    """Runs a script's top-level code on its own thread and waits for it at
    most TOP_LEVEL_TIME_LIMIT seconds, so a script that loops or waits can't
    freeze the program (Run's reload, D-04-Q13-RUNLIMIT)."""
    code = _TopLevel(spec, module, name)
    code.wait()
    code.finish()


class _StartNotifier(QtCore.QObject):
    """Brings a script's start to an end on the main thread (D-04-Q13-NOWAIT)."""

    # From the worker, queued to this object's (the main) thread.
    codeDone = QtCore.Signal(object, object)
    # A start began: its time limit is timed on the main thread.
    limitStart = QtCore.Signal(object, object)
    # A script finished starting (loaded or failed): the Scripts page shows it.
    started = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        queued = QtCore.Qt.ConnectionType.QueuedConnection
        self.codeDone.connect(self._code_done, queued)
        self.limitStart.connect(self._start_limit, queued)

    def _code_done(self, script: Script, code: _TopLevel) -> None:
        script._end_start(code)

    def _start_limit(self, script: Script, code: _TopLevel) -> None:
        if not script.starting or script._starting is not code:
            return
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)

        def limit_passed() -> None:
            timer.deleteLater()
            script._end_start(code)

        timer.timeout.connect(limit_passed)
        timer.start(max(0, round((code.deadline - clock.monotonic()) * 1000)))


# Made where this module is first imported: the main thread.
start_notifier = _StartNotifier()
# Scripts whose top-level code is still starting.
_starting_scripts: weakref.WeakSet[Script] = weakref.WeakSet()


def _without_layout(node: ElementTree.Element) -> ElementTree.Element:
    """node with the line breaks and indents a saved file put between its
    tags removed: saving pretty-prints it again, which would otherwise add
    more each time. A value's own text (a tag with no tags inside) stays."""
    for element in node.iter():
        if len(element) and element.text is not None and not element.text.strip():
            element.text = None
        if element.tail is not None and not element.tail.strip():
            element.tail = None
    return node


class Script(EditNoted):
    """Represents the prototype of a script."""

    variable_registry = ScriptVariableRegistry()

    def __init__(self, path: Path = Path(), name: str = "") -> None:
        """Creates a new Script."""
        self._id = uuid.uuid4()
        self.path = _resolve_path(path)
        self.name = name
        self._variables: dict[str, AbstractVariable] = {}
        # Why the script could not be loaded ("" when it loaded). Such a
        # script stays in the profile: its saved settings are written back
        # unchanged, it is tried again at each Run, and the Scripts page
        # shows the reason.
        self._load_error = ""
        self._saved_variables: list[ElementTree.Element] = []
        # Its top-level code while it is starting (loaded or added): the
        # program doesn't wait for it (D-04-Q13-NOWAIT). The saved settings
        # it gets once started, or None.
        self._starting: _TopLevel | None = None
        self._starting_node: ElementTree.Element | None = None
        self._start_lock = threading.Lock()

        if self.path.is_file():
            try:
                self._begin_start(None)
            except Exception as e:
                self._failed(e)

    # A script that is starting has its settings and its load error once it
    # has started: reading them waits for that (at most until its time
    # limit), as Run does. What only shows the script reads starting first.

    @property
    def variables(self) -> dict[str, AbstractVariable]:
        self._wait_started()
        return self._variables

    @variables.setter
    def variables(self, value: dict[str, AbstractVariable]) -> None:
        self._variables = value

    @property
    def load_error(self) -> str:
        self._wait_started()
        return self._load_error

    @load_error.setter
    def load_error(self, value: str) -> None:
        self._load_error = value

    @property
    def starting(self) -> bool:
        """True while its top-level code runs at load or add (it doesn't
        wait): its settings and load error aren't known yet."""
        return self._starting is not None

    @property
    def shown_load_error(self) -> str:
        """The load error, "" while starting (doesn't wait)."""
        return "" if self.starting else self._load_error

    @property
    def shown_variables(self) -> dict[str, AbstractVariable]:
        """The settings, none while starting (doesn't wait)."""
        return {} if self.starting else self._variables

    def _begin_start(self, node: ElementTree.Element | None) -> None:
        """Starts its top-level code without waiting for it; node holds the
        saved settings it gets once started. Raises when it can't start."""
        self._drop_start()
        spec, module = self._new_module()
        self._starting_node = node
        with self._start_lock:
            # Done, it ends its start on the main thread (queued).
            code = _TopLevel(
                spec,
                module,
                self.name or self.path.name,
                on_done=lambda done: start_notifier.codeDone.emit(self, done),
            )
            self._starting = code
            _starting_scripts.add(self)
        # Not done when the limit passes: marked failed then, on the main
        # thread.
        start_notifier.limitStart.emit(self, code)

    def _wait_started(self) -> None:
        code = self._starting
        if code is None:
            return
        code.wait()
        self._end_start(code)

    def _drop_start(self) -> None:
        """Forgets a start still running (it is replaced)."""
        with self._start_lock:
            self._starting = None
            _starting_scripts.discard(self)

    def _end_start(self, code: _TopLevel) -> None:
        """Its start comes to an end: loaded with its saved settings, or
        failed (an error, or the time limit passed). Once only."""
        with self._start_lock:
            if self._starting is not code:
                return
            self._starting = None
            _starting_scripts.discard(self)
        node, self._starting_node = self._starting_node, None
        try:
            code.finish()
            self._take_module(code.spec, code.module)
            if node is not None:
                self._apply_saved(node)
            Script.variable_registry.register_script(self)
            self._load_error = ""
        except BaseException as e:  # what its code raised too (SystemExit)
            self._failed(e)
        # What it writes now comes from its settings, not as saved: the
        # title's "*" checks again (04 Q19); a script that started with
        # its saved settings writes the same, so nothing shows unsaved.
        note_edit()
        start_notifier.started.emit()

    @property
    def id(self) -> uuid.UUID:
        """Returns the UUID of the script.

        Returns:
            Unique identifier of this script.
        """
        return self._id

    @property
    def is_configured(self) -> bool:
        """Returns if the instance is fully configured.

        Returns:
            True if the instance is fully configured, False otherwise
        """
        return all(
            [var.is_valid() for var in self.variables.values() if not var.is_optional]
        )

    def has_variable(self, name: str) -> bool:
        """Returns if this instance has a particular variable.

        Args:
            name: name of the variable to check the existence of

        Returns:
            True if a variable with the given name exists, False otherwise
        """
        return name in self.variables

    def set_variable(self, name: str, variable: AbstractVariable) -> None:
        """Sets the value of a named variable.

        Args:
            name: Name of the variable object to be set
            variable: Variable to store
        """
        self.variables[name] = variable
        note_edit()

    def get_variable(self, name: str) -> AbstractVariable:
        """Returns the variable stored under the specified name.

        Attempting to retrieve a non-existent variable will raise an error.

        Args:
            name: Name of the variable to return

        Returns:
            Variable corresponding to the specified name
        """
        if not self.has_variable(name):
            raise error.GremlinError(
                f"Script '{self.path}' does not contain a variable '{name}'"
            )
        return self.variables[name]

    def from_xml(self, node: ElementTree.Element, wait: bool = False) -> None:
        """Initializes the values of this instance based on the node's contents.

        Its top-level code starts without the program waiting for it (profile
        load, D-04-Q13-NOWAIT); wait=True waits for it (retry at Run).

        Args:
            node: XML node containing this instance's configuration
            wait: wait for the top-level code (up to its time limit)
        """
        self._drop_start()
        # Remove information of this script in case the ID changes
        Script.variable_registry.remove_script(self)

        self._id = util.read_uuid(node, "script", "id")
        self.path = _resolve_path(util.read_property(node, "path", PropertyType.Path))
        self.name = util.read_property(node, "name", PropertyType.String)
        # Kept as saved, so a script that can't load loses nothing on save.
        self._saved_variables = [copy.deepcopy(v) for v in node.iter("variable")]
        self._variables = {}
        self._load_error = ""
        try:
            if wait:
                self._load_from_xml(node)
            else:
                self._begin_start(node)
        except Exception as e:
            self._failed(e)

    def _load_from_xml(self, node: ElementTree.Element) -> None:
        # Retrieve variable information from the script and instantiate them
        self._retrieve_variable_definitions()
        self._apply_saved(node)
        # Store script values in the registry
        Script.variable_registry.register_script(self)

    def _apply_saved(self, node: ElementTree.Element) -> None:
        """Gives the script's settings the values saved in node."""
        lookup: dict[str | None, type[AbstractVariable]] = {
            "bool": BoolVariable,
            "float": FloatVariable,
            "int": IntegerVariable,
            "keyboard": KeyboardVariable,
            "logical-device": LogicalDeviceVariable,
            "osc-input": OscInputVariable,
            "mode": ModeVariable,
            "physical-input": PhysicalInputVariable,
            "selection": SelectionVariable,
            "string": StringVariable,
            "vjoy": VirtualInputVariable,
        }
        # Populate variables with data from the XML if they are present
        for entry in node.iter("variable"):
            name = util.read_property(entry, "name", PropertyType.String)
            # Don't parse variables that don't exist anymore, they will be
            # removed upon the next save
            if name not in self._variables:
                logging.getLogger("system").warning(
                    f"Script: Unknown variable '{name}' ignored"
                )
                continue
            type_name = entry.get("type")
            if not isinstance(self._variables[name], lookup[type_name]):
                raise error.GremlinError(
                    f"Script: Type mismatch, profile contains '{type_name}' "
                    + f"while script expects '{self._variables[name]}'"
                )
            self._variables[name].from_xml(entry)

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing this instance.

        A script that is starting is written as saved (it doesn't wait).

        Returns:
            XML node representing this instance
        """
        node = util.create_node_from_data(
            "script",
            [
                ("path", _saved_path(self.path), PropertyType.Path),
                ("name", str(self.name), PropertyType.String),
            ],
        )
        node.set("id", util.safe_format(self._id, uuid.UUID))
        if self._load_error or self.starting:
            for saved in self._saved_variables:
                node.append(_without_layout(copy.deepcopy(saved)))
            return node
        for entry in self._variables.values():
            variable_node = entry.to_xml()
            if variable_node is not None:
                node.append(variable_node)
        return node

    def retry(self) -> bool:
        """Loads a script that could not be loaded again (its file may have
        been fixed). Returns True when it is loaded now."""
        if not self.load_error:
            return True
        node = self.to_xml()
        self.from_xml(node, wait=True)
        return not self._load_error

    def _failed(self, error_: BaseException) -> None:
        self._variables = {}
        self._load_error = describe_load_error(error_, self.path)
        Script.variable_registry.remove_script(self)
        logging.getLogger("system").warning(
            f"Script '{self.name}' ({self.path}) could not be loaded: "
            f"{self._load_error}"
        )

    def reload(self) -> bool:
        """Reloads this script. Returns False (and keeps the reason) when it
        can't be run."""
        if self.load_error and not self.retry():
            return False
        Script.variable_registry.register_script(self)
        self.module._script_id = self.id
        try:
            # Under the same time limit as loading (D-04-Q13-RUNLIMIT).
            _run_top_level(self.spec, self.module, self.name or self.path.name)
        except Exception as e:
            nodes = (v.to_xml() for v in self._variables.values())
            self._saved_variables = [n for n in nodes if n is not None]
            self._failed(e)
            return False
        return True

    def _new_module(self) -> tuple[importlib.machinery.ModuleSpec, types.ModuleType]:
        """A new module for the script's file (its code not run yet)."""
        if not self.path.is_file():
            raise error.GremlinError(f"Invalid script file '{self.path}'")

        spec = importlib.util.spec_from_file_location(
            "".join(random.choices(string.ascii_lowercase, k=16)), str(self.path)
        )
        if spec is None or spec.loader is None:
            raise error.GremlinError(f"Script: Can't read '{self.path}'")
        module = importlib.util.module_from_spec(spec)
        module._script_id = self.id
        return spec, module

    def _retrieve_variable_definitions(self) -> None:
        """Runs the script's top-level code, waiting for it up to its time
        limit, and takes the variables it defines."""
        self._variables = {}
        spec, module = self._new_module()
        # Kept only once it has run: a run that is still going after the
        # time limit changes nothing here.
        _run_top_level(spec, module, self.name or self.path.name)
        self._take_module(spec, module)

    def _take_module(
        self, spec: importlib.machinery.ModuleSpec, module: types.ModuleType
    ) -> None:
        """Keeps the module whose top-level code ran, and its variables."""
        self.spec = spec
        self.module = module
        self._variables = {}
        for value in self.module.__dict__.values():
            if isinstance(value, AbstractVariable):
                if value.name in self._variables:
                    logging.getLogger("system").error(
                        f"Script: Duplicate label {value.label} present in {self.path}"
                    )
                self._variables[value.name] = copy.deepcopy(value)

    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        """Swaps occurrences of the old UUID with the new one for this action."""
        swap_done = False
        for variable in self.variables.values():
            if variable.swap_uuid(old_uuid, new_uuid):
                swap_done = True
        return swap_done


class AbstractVariable(EditNoted, ABC):
    xml_tag = "abstract"

    def __init__(
        self, name: str | None = None, description: str = "", is_optional: bool = True
    ) -> None:
        self.name = name
        self.description = description
        self.is_optional = is_optional
        self.is_set = False

    @property
    @abstractmethod
    def value(self) -> Any:  # noqa: ANN401
        pass

    @value.setter
    @abstractmethod
    def value(self, value: Any) -> None:  # noqa: ANN401
        pass

    def from_xml(self, node: ElementTree.Element) -> None:
        self.name = util.read_property(node, "name", PropertyType.String)
        self._from_xml(node)

    def to_xml(self) -> None | ElementTree.Element:
        if not self.is_valid():
            return None
        node = ElementTree.Element("variable")
        node.set("type", self.xml_tag)
        util.append_property_nodes(node, [["name", self.name, PropertyType.String]])
        self._to_xml(node)
        return node

    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @abstractmethod
    def _from_xml(self, node: ElementTree.Element) -> None:
        pass

    @abstractmethod
    def _to_xml(self, node: ElementTree.Element) -> None:
        pass

    @abstractmethod
    def _assign_value_from(self, other: AbstractVariable) -> None:
        pass

    def _initialize_from_registry(self) -> None:
        idx = _current_script_id()
        var = Script.variable_registry.get(idx, self.name)
        if isinstance(var, AbstractVariable):
            self._assign_value_from(var)

    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        """Swaps occurrences of the old UUID with the new one for this variable."""
        return False


class BoolVariable(AbstractVariable):
    xml_tag = "bool"

    def __init__(
        self, name: str, description: str, is_optional: bool, initial_value: bool
    ) -> None:
        super().__init__(name, description, is_optional)

        self._value = initial_value
        self._initialize_from_registry()

    @property
    def value(self) -> bool:
        return self._value

    @value.setter
    def value(self, value: bool) -> None:
        self._value = value

    def is_valid(self) -> bool:
        return self._value in [True, False]

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._value = util.read_property(node, "value", PropertyType.Bool)

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(util.create_property_node("value", self.value, PropertyType.Bool))

    def _assign_value_from(self, other: BoolVariable) -> None:
        self._value = other.value


class FloatVariable(AbstractVariable):
    xml_tag = "float"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        initial_value: float,
        min_value: float,
        max_value: float,
    ) -> None:
        super().__init__(name, description, is_optional)

        self._value = initial_value
        self._min_value = min_value
        self._max_value = max_value
        self._initialize_from_registry()

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = clamp_value(value, self._min_value, self._max_value)

    @property
    def min_value(self) -> float:
        return self._min_value

    @property
    def max_value(self) -> float:
        return self._max_value

    def is_valid(self) -> bool:
        return isinstance(self._value, numbers.Number)

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._value = util.read_property(
            node, "value", [PropertyType.Float, PropertyType.Int]
        )

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(
            util.create_property_node(
                "value", self._value, [PropertyType.Float, PropertyType.Int]
            )
        )

    def _assign_value_from(self, other: FloatVariable) -> None:
        self._value = other.value


class IntegerVariable(AbstractVariable):
    xml_tag = "int"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        initial_value: int,
        min_value: int,
        max_value: int,
    ) -> None:
        super().__init__(name, description, is_optional)

        self._value = initial_value
        self._min_value = min_value
        self._max_value = max_value
        self._initialize_from_registry()

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        self._value = clamp_value(value, self._min_value, self._max_value)

    @property
    def min_value(self) -> int:
        return self._min_value

    @property
    def max_value(self) -> int:
        return self._max_value

    def is_valid(self) -> bool:
        return isinstance(self._value, int)

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._value = util.read_property(node, "value", PropertyType.Int)

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(util.create_property_node("value", self._value, PropertyType.Int))

    def _assign_value_from(self, other: IntegerVariable) -> None:
        self._value = other.value


class KeyboardVariable(AbstractVariable):
    xml_tag = "keyboard"

    def __init__(self, name: str, description: str, is_optional: bool) -> None:
        super().__init__(name, description, is_optional)

        self._value: None | gremlin.keyboard.Key = None
        self._initialize_from_registry()

    @property
    def value(self) -> gremlin.keyboard.Key | None:
        return self._value

    @value.setter
    def value(self, data: gremlin.keyboard.Key) -> None:
        self._value = data

    def is_valid(self) -> bool:
        return isinstance(self._value, gremlin.keyboard.Key)

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._value = gremlin.keyboard.key_from_code(
            util.read_property(node, "scan-code", PropertyType.Int),
            util.read_property(node, "is-extended", PropertyType.Bool),
        )

    def _to_xml(self, node: ElementTree.Element) -> None:
        assert isinstance(self._value, gremlin.keyboard.Key)
        util.append_property_nodes(
            node,
            [
                ["scan-code", self._value.scan_code, PropertyType.Int],
                ["is-extended", self._value.is_extended, PropertyType.Bool],
            ],
        )

    def _assign_value_from(self, other: KeyboardVariable) -> None:
        self._value = other.value

    def decorator(self, mode: ModeVariable) -> Callable:
        if self._value is None:
            # Return a no-op decorator.
            return lambda f: f
        else:
            assert isinstance(self._value, gremlin.keyboard.Key)
            # The Key itself: names don't round-trip (Numpad 5, extended keys).
            return keyboard(self._value, mode.value)


class LogicalDeviceVariable(AbstractVariable):
    xml_tag = "logical-device"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        valid_types: list[InputType],
    ) -> None:
        super().__init__(name, description, is_optional)

        self._ld = LogicalDevice()
        self._valid_types = valid_types
        inputs = self._ld.inputs_of_type(valid_types)
        # Create a valid entry if none exists/
        if not inputs:
            inputs = [self._ld.create(self._valid_types[0])]
        self._identifier = inputs[0].identifier
        # The stored permanent id is what the variable names (D-04-LD-FILE);
        # _identifier is the type+number last known for it.
        self._uid: str | None = inputs[0].uid
        self._initialize_from_registry()

    @property
    def uid(self) -> str | None:
        """Permanent id of the named control (None: unknown, old data)."""
        return self._uid

    @uid.setter
    def uid(self, value: str | None) -> None:
        self._uid = value or None

    def is_missing(self) -> bool:
        """The stored uid names a control the Logical Device doesn't have."""
        return self._uid is not None and self._ld.identifier_of_uid(self._uid) is None

    def _current(self) -> LogicalDevice.Input.Identifier:
        """The named control's current type and number (the last known one
        when missing)."""
        if self._uid is not None:
            ident = self._ld.identifier_of_uid(self._uid)
            if ident is not None:
                return ident
        return self._identifier

    def decorator(self, mode: ModeVariable) -> Callable:
        dec = self.create_decorator(mode.value)
        ident = self._current()
        match ident.type:
            case InputType.JoystickButton:
                return dec.button(ident.id)
            case InputType.JoystickAxis:
                return dec.axis(ident.id)
            case InputType.JoystickHat:
                return dec.hat(ident.id)
            case _:
                raise error.GremlinError(
                    f"Received invalid input type '{ident.type}'"
                )

    def create_decorator(self, mode: str) -> JoystickDecorator:
        if not self.is_valid():
            return JoystickDecorator("", str(dill.GUID_Invalid), "")
        else:
            return JoystickDecorator(
                "Logical Device", str(LogicalDevice.device_guid), mode
            )

    @property
    def value(self) -> LogicalDevice.Input:
        return self._ld[self._current()]

    @value.setter
    def value(self, value: LogicalDevice.Input.Identifier) -> None:
        self._identifier = value
        self._uid = self._ld.uid_of(value.type, value.id)

    @property
    def valid_types(self) -> list[InputType]:
        return self._valid_types

    def is_valid(self) -> bool:
        return not self.is_missing() and self._ld.exists(self._current())

    def to_xml(self) -> None | ElementTree.Element:
        # A missing control is kept on save, never dropped (decision 4).
        if not self.is_missing():
            return super().to_xml()
        node = ElementTree.Element("variable")
        node.set("type", self.xml_tag)
        util.append_property_nodes(node, [["name", self.name, PropertyType.String]])
        self._to_xml(node)
        return node

    def _from_xml(self, node: ElementTree.Element) -> None:
        input_type = util.read_property(node, "input-type", PropertyType.InputType)
        input_id = util.read_property(node, "input-id", PropertyType.Int)
        ident, uid = resolve_logical_reference(
            node.get("uid") or None, input_type, input_id
        )
        self._identifier = (
            ident
            if ident is not None
            else LogicalDevice.Input.Identifier(input_type, input_id)
        )
        # A saved uid the Logical Device doesn't have stays: missing.
        self._uid = uid

    def _to_xml(self, node: ElementTree.Element) -> None:
        ident = self._current()
        util.append_property_nodes(
            node,
            [
                ["input-type", ident.type, PropertyType.InputType],
                ["input-id", ident.id, PropertyType.Int],
            ],
        )
        if self._uid:
            node.set("uid", self._uid)

    def _assign_value_from(self, other: LogicalDeviceVariable) -> None:
        self._identifier = other._identifier
        self._uid = other._uid


class OscInputVariable(AbstractVariable):
    """An OSC input, named by its permanent id (09 S163). Its decorator
    puts the callback on the normal event path for that input."""

    xml_tag = "osc-input"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        valid_types: list[InputType] | None = None,
    ) -> None:
        super().__init__(name, description, is_optional)

        self._valid_types = valid_types or [
            InputType.JoystickAxis,
            InputType.JoystickButton,
        ]
        # Nothing is chosen until the user picks an address.
        self._uid: str | None = None
        self._initialize_from_registry()

    @property
    def uid(self) -> str | None:
        """Permanent id of the chosen OSC input (None: none chosen)."""
        return self._uid

    @uid.setter
    def uid(self, value: str | None) -> None:
        self._uid = value or None

    @property
    def value(self) -> OscRow | None:
        """The chosen OSC input, None when none is chosen or it is gone."""
        if self._uid is None:
            return None
        return OscDevice().rows.by_uid(self._uid)

    @value.setter
    def value(self, value: OscRow | str | None) -> None:
        self.uid = value.uid if isinstance(value, OscRow) else value

    @property
    def valid_types(self) -> list[InputType]:
        return self._valid_types

    def choices(self) -> list[OscRow]:
        """The OSC inputs this variable can name, by address."""
        return sorted(
            (r for r in OscDevice().rows.rows() if r.input_type in self._valid_types),
            key=lambda r: r.label.casefold(),
        )

    def is_missing(self) -> bool:
        """The stored uid names an OSC input that no longer exists."""
        return self._uid is not None and self.value is None

    def is_valid(self) -> bool:
        row = self.value
        return row is not None and row.input_type in self._valid_types

    def create_decorator(self, mode: str) -> JoystickDecorator:
        return JoystickDecorator("OSC", str(OSC_DEVICE_UUID), mode)

    def decorator(self, mode: ModeVariable) -> Callable:
        row = self.value
        if row is None or not self.is_valid():
            # Return a no-op decorator.
            return lambda f: f
        dec = self.create_decorator(mode.value)
        if row.input_type == InputType.JoystickAxis:
            return dec.axis(row.input_id)
        return dec.button(row.input_id)

    def to_xml(self) -> None | ElementTree.Element:
        # A missing input is kept on save, never dropped.
        if not self.is_missing():
            return super().to_xml()
        node = ElementTree.Element("variable")
        node.set("type", self.xml_tag)
        util.append_property_nodes(node, [["name", self.name, PropertyType.String]])
        self._to_xml(node)
        return node

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._uid = node.get("uid") or None

    def _to_xml(self, node: ElementTree.Element) -> None:
        if self._uid:
            node.set("uid", self._uid)

    def _assign_value_from(self, other: OscInputVariable) -> None:
        self._uid = other._uid


class ModeVariable(AbstractVariable):
    xml_tag = "mode"

    def __init__(self, name: str, description: str, is_optional: bool) -> None:
        super().__init__(name, description, is_optional)

        self._mode = shared_state.current_profile.modes.first_mode
        self._initialize_from_registry()

    @property
    def value(self) -> str:
        return self._mode

    @value.setter
    def value(self, value: str) -> None:
        self._mode = value

    def is_valid(self) -> bool:
        return self._mode in shared_state.current_profile.modes.mode_names()

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._mode = util.read_property(node, "value", PropertyType.String)

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(util.create_property_node("value", self._mode, PropertyType.String))

    def _assign_value_from(self, other: ModeVariable) -> None:
        self._mode = other.value


class SelectionVariable(AbstractVariable):
    xml_tag = "selection"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        option_list: list[str],
        default_index: int = 0,
    ) -> None:
        super().__init__(name, description, is_optional)

        if not (0 <= default_index < len(option_list)):
            raise error.PluginError(
                f"Default index {default_index} is out of range for option list "
                f"of length {len(option_list)} for selection variable '{name}'"
            )
        self._option_list = option_list
        self._set_current_index(default_index)
        self._initialize_from_registry()

    def _set_current_index(self, index: int) -> None:
        if 0 <= index < len(self._option_list):
            self._current_index = index
        else:
            logging.getLogger("user_script").warning(
                f"Ignoring invalid index {index} for selection variable '{self.name}'"
            )

    @property
    def options(self) -> list[str]:
        return self._option_list

    @property
    def value(self) -> str:
        return self._option_list[self._current_index]

    @value.setter
    def value(self, value: str) -> None:
        self._current_index = self._option_list.index(value)

    def is_valid(self) -> bool:
        return True

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._set_current_index(util.read_property(node, "index", PropertyType.Int))

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(
            util.create_property_node("index", self._current_index, PropertyType.Int)
        )

    def _assign_value_from(self, other: SelectionVariable) -> None:
        self._set_current_index(other._current_index)


class StringVariable(AbstractVariable):
    xml_tag = "string"

    def __init__(
        self, name: str, description: str, is_optional: bool, initial_value: str
    ) -> None:
        super().__init__(name, description, is_optional)

        self._value = initial_value
        self._initialize_from_registry()

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value

    def is_valid(self) -> bool:
        return isinstance(self._value, str) and len(self._value) > 0

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._value = util.read_property(node, "value", PropertyType.String)

    def _to_xml(self, node: ElementTree.Element) -> None:
        node.append(
            util.create_property_node("value", self._value, PropertyType.String)
        )

    def _assign_value_from(self, other: StringVariable) -> None:
        self._value = other.value


class PhysicalInputVariable(AbstractVariable):
    xml_tag = "physical-input"

    type Identifier = tuple[uuid.UUID, InputType, int]

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        valid_types: list[InputType],
    ) -> None:
        super().__init__(name, description, is_optional)

        self._valid_types = valid_types
        self._device_guid = None
        self._input_type = valid_types[0]
        self._input_id = 1
        self._initialize_from_registry()

    @property
    def device_guid(self) -> uuid.UUID:
        return self._device_guid

    @property
    def input_type(self) -> InputType:
        return self._input_type

    @property
    def input_id(self) -> int:
        return self._input_id

    @property
    def value(self) -> Identifier:
        return (self._device_guid, self._input_type, self._input_id)

    @property
    def valid_types(self) -> list[InputType]:
        return self._valid_types

    @value.setter
    def value(self, value: Identifier) -> None:
        self._device_guid = value[0]
        self._input_type = value[1]
        self._input_id = value[2]

    def decorator(self, mode: ModeVariable) -> Callable:
        dec = self.create_decorator(mode.value)
        match self._input_type:
            case InputType.JoystickButton:
                return dec.button(self._input_id)
            case InputType.JoystickAxis:
                return dec.axis(self._input_id)
            case InputType.JoystickHat:
                return dec.hat(self._input_id)
            case _:
                raise error.GremlinError(
                    f"Received invalid input type '{self._input_type}'"
                )

    def create_decorator(self, mode: str) -> JoystickDecorator:
        if not self.is_valid():
            return JoystickDecorator("", str(dill.GUID_Invalid), "")
        else:
            return JoystickDecorator("device name", str(self._device_guid), mode)

    def is_valid(self) -> bool:
        return (
            self._device_guid is not None
            and self._input_type in self._valid_types
            and isinstance(self._input_id, int)
        )

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._device_guid = util.read_property(node, "device-guid", PropertyType.UUID)
        self._input_type = util.read_property(
            node, "input-type", PropertyType.InputType
        )
        self._input_id = util.read_property(node, "input-id", PropertyType.Int)

    def _to_xml(self, node: ElementTree.Element) -> None:
        util.append_property_nodes(
            node,
            [
                ["device-guid", self._device_guid, PropertyType.UUID],
                ["input-type", self._input_type, PropertyType.InputType],
                ["input-id", self._input_id, PropertyType.Int],
            ],
        )

    def _assign_value_from(self, other: PhysicalInputVariable) -> None:
        self._valid_types = other._valid_types
        self._device_guid = other.device_guid
        self._input_type = other.input_type
        self._input_id = other.input_id

    @override
    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        if self._device_guid == old_uuid:
            self._device_guid = new_uuid
            return True
        return False


class VirtualInputVariable(AbstractVariable):
    xml_tag = "vjoy"

    def __init__(
        self,
        name: str,
        description: str,
        is_optional: bool,
        valid_types: list[InputType],
    ) -> None:
        super().__init__(name, description, is_optional)

        self._valid_types = valid_types
        self._vjoy_id = 1
        self._input_type = valid_types[0]
        self._input_id = 1
        self._initialize_from_registry()

    @property
    def value(self) -> None:
        pass

    @value.setter
    def value(self, value: bool) -> None:
        pass

    @property
    def vjoy_id(self) -> int:
        return self._vjoy_id

    @property
    def input_id(self) -> int:
        return self._input_id

    @property
    def input_type(self) -> InputType:
        return self._input_type

    @property
    def valid_types(self) -> list[InputType]:
        return self._valid_types

    def remap(self, value: float | bool | HatDirection) -> None:
        match self._input_type:
            case InputType.JoystickButton:
                output.write_vjoy(self._vjoy_id, "button", self._input_id, value)
            case InputType.JoystickAxis:
                output.write_vjoy(self._vjoy_id, "axis", self._input_id, value)
            case InputType.JoystickHat:
                output.write_vjoy(self._vjoy_id, "hat", self._input_id, value)
            case _:
                raise error.GremlinError(
                    f"Received invalid input type '{self._input_type}'"
                )

    def is_valid(self) -> bool:
        return (
            self._vjoy_id is not None
            and self._input_type in self._valid_types
            and isinstance(self._input_id, int)
        )

    def _from_xml(self, node: ElementTree.Element) -> None:
        self._vjoy_id = util.read_property(node, "vjoy-id", PropertyType.Int)
        self._input_type = util.read_property(
            node, "input-type", PropertyType.InputType
        )
        self._input_id = util.read_property(node, "input-id", PropertyType.Int)

    def _to_xml(self, node: ElementTree.Element) -> None:
        util.append_property_nodes(
            node,
            [
                ["vjoy-id", self._vjoy_id, PropertyType.Int],
                ["input-type", self._input_type, PropertyType.InputType],
                ["input-id", self._input_id, PropertyType.Int],
            ],
        )

    def _assign_value_from(self, other: VirtualInputVariable) -> None:
        self._valid_types = other._valid_types
        self._vjoy_id = other.vjoy_id
        self._input_type = other.input_type
        self._input_id = other.input_id


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Returns the value clamped to the provided range.

    Args:
        value: numerical value to clamp
        min_val: lower bound of the range
        max_val: upper bound of the range

    Returns:
        The input value clamped to the provided range
    """
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    return min(max_val, max(min_val, value))


def keyboard(key: str | gremlin.keyboard.Key, mode: str) -> Callable:
    """Decorator for keyboard key callbacks.

    Args:
        key: key name, or a Key instance for keys that have no name lookup
        mode: mode in which this callback is active
    """

    def wrap(callback: Callable) -> Callable:

        @functools.wraps(callback)
        def wrapper_fn(*args: Any, **kwargs: dict) -> None:  # noqa: ANN401
            callback(*args, **kwargs)

        resolved_key = (
            key
            if isinstance(key, gremlin.keyboard.Key)
            else gremlin.keyboard.key_from_name(key)
        )
        event = event_handler.Event.from_key(resolved_key)
        _register(lambda: callback_registry.add(wrapper_fn, event, mode))

        return wrapper_fn

    return wrap


def periodic(interval: float) -> Callable:
    """Decorator for periodic function callbacks.

    Args:
        interval: the duration between executions of the function
    """

    def wrap(callback: Callable) -> Callable:

        @functools.wraps(callback)
        def wrapper_fn(*args: Any, **kwargs: dict) -> None:  # noqa: ANN401
            callback(*args, **kwargs)

        _register(lambda: periodic_registry.add(wrapper_fn, interval))

        return wrapper_fn

    return wrap


def _input_callback(
    input_id: int, device_guid: uuid.UUID, input_type: InputType, mode: str
) -> Callable:
    """Decorator for a specific input on a physical device.

    Args:
        device_guid: GUID of the physical device
        input_type: type of the input being wrapped in the decorator
        input_id: identifier of the axis, button, or hat being decorated
        mode: name of the mode the callback is active in
    """

    # The order of the input arguments has to be this specific one as otherwise
    # the positional argument part of the decorator breaks.

    def wrap(callback: Callable) -> Callable:

        @functools.wraps(callback)
        def wrapper_fn(*args: Any, **kwargs: dict) -> None:  # noqa: ANN401
            callback(*args, **kwargs)

        event = event_handler.Event(
            event_type=input_type,
            identifier=input_id,
            device_guid=device_guid,
            mode=mode,
        )
        _register(lambda: callback_registry.add(wrapper_fn, event, mode))

        return wrapper_fn

    return wrap
