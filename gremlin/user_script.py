# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import copy
import functools
import heapq
import importlib
import importlib.util
import inspect
import logging
import numbers
import random
import string
import threading
import time
import uuid
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

import dill
import gremlin.keyboard
from gremlin import (
    error,
    event_handler,
    shared_state,
    threads,
    util,
)
from gremlin.logical_device import LogicalDevice
from gremlin.modules import inputs, output
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


def _current_script_id() -> uuid.UUID | None:
    """Returns the id of the Script currently executing, if any."""
    for frame in inspect.stack():
        identifier = frame.frame.f_locals.get("_script_id", None)
        if isinstance(identifier, uuid.UUID):
            return identifier
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
        # Each Run has its own loop: one still finishing a slow callback
        # after Stop ends by itself and never runs the new Run's callbacks.
        self._generation = 0

    def start(self) -> None:
        """Starts the event loop."""
        # Only proceed if we have functions to call
        if len(self._registry) == 0:
            return

        self._running = True
        self._generation += 1
        self._thread = threads.start(
            "user script timers",
            self._thread_loop,
            self._generation,
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

    def _thread_loop(self, generation: int) -> None:
        """Main execution loop run in a separate thread."""
        # Setup plugins to use
        self._plugins = [JoystickPlugin(), VJoyPlugin(), KeyboardPlugin()]
        callback_interval = {}

        # Populate the queue, adding an index to each callback to tie break
        # entries with identical execution times.
        self._queue = []
        with self._registry_lock:
            for index, item in enumerate(self._registry.values()):
                plugin_cb = self._install_plugins(item[1])
                callback_interval[plugin_cb] = item[0]
                heapq.heappush(
                    self._queue, (time.monotonic() + item[0], index, plugin_cb)
                )

        queue = self._queue

        def current() -> bool:
            return self._running and self._generation == generation

        while current():
            # Capture the current timestamp for reuse in the sleep down below.
            while current() and queue[0][0] < (now := time.monotonic()):
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
                    deadline + callback_interval[callback], time.monotonic()
                )
                heapq.heappush(queue, (next_at, index, callback))
            if not current():
                break

            # Sleep until either the next function needs to be run or
            # our timeout expires
            time.sleep(max(0.0, min(queue[0][0] - now, 1.0)))


callback_registry = CallbackRegistry()
periodic_registry = PeriodicRegistry()


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

    def remove_script(self, script: Script) -> None:
        """Removes the specified script's variables.

        Args:
            script: the script to remove variables for
        """
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


def describe_load_error(error_: BaseException, path: Path) -> str:
    """Why a script could not be loaded, in words for the Scripts page."""
    if isinstance(error_, FileNotFoundError) or not path.is_file():
        return "File not found"
    if isinstance(error_, SyntaxError):
        return f"Syntax error, line {error_.lineno}: {error_.msg}"
    if isinstance(error_, error.GremlinError):
        return str(error_).removeprefix("Script: ")
    return f"{type(error_).__name__}: {error_}"


class Script:
    """Represents the prototype of a script."""

    variable_registry = ScriptVariableRegistry()

    def __init__(self, path: Path = Path(), name: str = "") -> None:
        """Creates a new Script."""
        self._id = uuid.uuid4()
        self.path = _resolve_path(path)
        self.name = name
        self.variables: dict[str, AbstractVariable] = {}
        # Why the script could not be loaded ("" when it loaded). Such a
        # script stays in the profile: its saved settings are written back
        # unchanged, it is tried again at each Run, and the Scripts page
        # shows the reason.
        self.load_error = ""
        self._saved_variables: list[ElementTree.Element] = []

        if self.path.is_file():
            try:
                self._retrieve_variable_definitions()
            except Exception as e:
                self._failed(e)
            else:
                self.variable_registry.register_script(self)

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

    def from_xml(self, node: ElementTree.Element) -> None:
        """Initializes the values of this instance based on the node's contents.

        Args:
            node: XML node containing this instance's configuration
        """
        # Remove information of this script in case the ID changes
        Script.variable_registry.remove_script(self)

        lookup = {
            "bool": BoolVariable,
            "float": FloatVariable,
            "int": IntegerVariable,
            "keyboard": KeyboardVariable,
            "logical-device": LogicalDeviceVariable,
            "mode": ModeVariable,
            "physical-input": PhysicalInputVariable,
            "selection": SelectionVariable,
            "string": StringVariable,
            "vjoy": VirtualInputVariable,
        }

        self._id = util.read_uuid(node, "script", "id")
        self.path = _resolve_path(util.read_property(node, "path", PropertyType.Path))
        self.name = util.read_property(node, "name", PropertyType.String)
        # Kept as saved, so a script that can't load loses nothing on save.
        self._saved_variables = [copy.deepcopy(v) for v in node.iter("variable")]
        try:
            self._load_from_xml(node, lookup)
        except Exception as e:
            self._failed(e)
            return
        self.load_error = ""

    def _load_from_xml(self, node: ElementTree.Element, lookup: dict) -> None:
        # Retrieve variable information from the script and instantiate them
        self._retrieve_variable_definitions()

        # Populate variables with data from the XML if they are present
        for entry in node.iter("variable"):
            name = util.read_property(entry, "name", PropertyType.String)
            # Don't parse variables that don't exist anymore, they will be
            # removed upon the next save
            if name not in self.variables:
                logging.getLogger("system").warning(
                    f"Script: Unknown variable '{name}' ignored"
                )
                continue
            type_name = entry.get("type")
            if not isinstance(self.variables[name], lookup[type_name]):
                raise error.GremlinError(
                    f"Script: Type mismatch, profile contains '{type_name}' "
                    + f"while script expects '{self.variables[name]}'"
                )
            self.variables[name].from_xml(entry)

        # Store script values in the registry
        Script.variable_registry.register_script(self)

    def to_xml(self) -> ElementTree.Element:
        """Returns an XML node representing this instance.

        Returns:
            XML node representing this instance
        """
        node = util.create_node_from_data(
            "script",
            [
                ("path", self.path, PropertyType.Path),
                ("name", str(self.name), PropertyType.String),
            ],
        )
        node.set("id", util.safe_format(self._id, uuid.UUID))
        if self.load_error:
            for saved in self._saved_variables:
                node.append(copy.deepcopy(saved))
            return node
        for entry in self.variables.values():
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
        self.from_xml(node)
        return not self.load_error

    def _failed(self, error_: BaseException) -> None:
        self.variables = {}
        self.load_error = describe_load_error(error_, self.path)
        Script.variable_registry.remove_script(self)
        logging.getLogger("system").warning(
            f"Script '{self.name}' ({self.path}) could not be loaded: "
            f"{self.load_error}"
        )

    def reload(self) -> bool:
        """Reloads this script. Returns False (and keeps the reason) when it
        can't be run."""
        if self.load_error and not self.retry():
            return False
        Script.variable_registry.register_script(self)
        self.module._script_id = self.id
        try:
            self.spec.loader.exec_module(self.module)
        except Exception as e:
            nodes = (v.to_xml() for v in self.variables.values())
            self._saved_variables = [n for n in nodes if n is not None]
            self._failed(e)
            return False
        return True

    def _retrieve_variable_definitions(self) -> None:
        """Returns all variable definitions used in the provided script.

        Args:
            path: Path to the script file

        Returns:
            List of variiables used in the script
        """
        self.variables = {}
        if not self.path.is_file():
            raise error.GremlinError(f"Invalid script file '{self.path}'")

        self.spec = importlib.util.spec_from_file_location(
            "".join(random.choices(string.ascii_lowercase, k=16)), str(self.path)
        )
        self.module = importlib.util.module_from_spec(self.spec)
        self.module._script_id = self.id
        self.spec.loader.exec_module(self.module)

        for key, value in self.module.__dict__.items():
            if isinstance(value, AbstractVariable):
                if value.name in self.variables:
                    logging.getLogger("system").error(
                        f"Script: Duplicate label {value.label} present in {self.path}"
                    )
                self.variables[value.name] = copy.deepcopy(value)

    def swap_uuid(self, old_uuid: uuid.UUID, new_uuid: uuid.UUID) -> bool:
        """Swaps occurrences of the old UUID with the new one for this action."""
        swap_done = False
        for variable in self.variables.values():
            if variable.swap_uuid(old_uuid, new_uuid):
                swap_done = True
        return swap_done


class AbstractVariable(ABC):
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
            return keyboard(self._value.name, mode.value)


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
        self._initialize_from_registry()

    def decorator(self, mode: ModeVariable) -> Callable:
        dec = self.create_decorator(mode.value)
        match self._identifier.type:
            case InputType.JoystickButton:
                return dec.button(self._identifier.id)
            case InputType.JoystickAxis:
                return dec.axis(self._identifier.id)
            case InputType.JoystickHat:
                return dec.hat(self._identifier.id)
            case _:
                raise error.GremlinError(
                    f"Received invalid input type '{self._identifier.type}'"
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
        return self._ld[self._identifier]

    @value.setter
    def value(self, value: LogicalDevice.Input.Identifier) -> None:
        self._identifier = value

    @property
    def valid_types(self) -> list[InputType]:
        return self._valid_types

    def is_valid(self) -> bool:
        return self._ld.exists(self._identifier)

    def _from_xml(self, node: ElementTree.Element) -> None:
        input_type = util.read_property(node, "input-type", PropertyType.InputType)
        input_id = util.read_property(node, "input-id", PropertyType.Int)
        self._identifier = LogicalDevice.Input.Identifier(input_type, input_id)

    def _to_xml(self, node: ElementTree.Element) -> None:
        util.append_property_nodes(
            node,
            [
                ["input-type", self._identifier.type, PropertyType.InputType],
                ["input-id", self._identifier.id, PropertyType.Int],
            ],
        )

    def _assign_value_from(self, other: LogicalDeviceVariable) -> None:
        self._identifier = other._identifier


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
        callback_registry.add(wrapper_fn, event, mode)

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

        periodic_registry.add(wrapper_fn, interval)

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
        callback_registry.add(wrapper_fn, event, mode)

        return wrapper_fn

    return wrap
