# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gremlin import (
    clock,
    common,
    error,
    util,
)
from gremlin.types import PropertyType

_config_file_path = os.path.join(util.userprofile_path(), "configuration.json")


def _write_file(path: Path, text: str) -> None:
    """A temporary file, then a swap: a crash mid-write leaves the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


# The settings core imports no UI or module code (01 section 7): the program
# hands it these at start (use()). Until then (a test, a tool): no activity
# line, a setting's own name in History titles, and _write_file.
def _no_trace(
    _action: str, _window: str, _function: str, _path: object, _result: str
) -> None:
    return None


def _own_name(name: str, _key: str) -> str:
    return name


_trace: Callable[[str, str, str, object, str], None] = _no_trace
_title: Callable[[str, str], str] = _own_name
_write_text: Callable[[Path, str], None] = _write_file


def use(
    trace: Callable[[str, str, str, object, str], None] | None = None,
    title: Callable[[str, str], str] | None = None,
    write_text: Callable[[Path, str], None] | None = None,
) -> None:
    """Hands the settings core what it needs from the layers above: the
    activity trace (Live Log Reader), the names Options shows (History
    titles) and the safe file write the program's other files use."""
    global _trace, _title, _write_text
    if trace is not None:
        _trace = trace
    if title is not None:
        _title = title
    if write_text is not None:
        _write_text = write_text


def _parse_entry(entry: dict) -> dict:
    """One saved setting as stored in memory; raises if it can't be read."""
    data_type = PropertyType.to_enum(entry["data_type"])
    value = entry["value"]
    # Saved as "True"/"False": anything else is unreadable, not False.
    if data_type == PropertyType.Bool and str(value).lower() not in ("true", "false"):
        raise ValueError(f"not a true/false value: {value!r}")
    if data_type in util._property_to_string:
        value = util.property_from_string(data_type, value)
    properties = entry["properties"]
    if not isinstance(properties, dict):
        raise ValueError("properties")
    return {
        "value": value,
        "data_type": data_type,
        "properties": properties,
        "expose": bool(entry["expose"]),
    }


_required_properties = {
    PropertyType.Bool: {},
    PropertyType.Int: {"min": int, "max": int},
    PropertyType.Float: {"min": float, "max": float},
    PropertyType.List: {},
    PropertyType.String: {},
    PropertyType.Selection: {"valid_options": list},
    PropertyType.HatDirection: {},
    PropertyType.Path: {"is_folder": bool},
    PropertyType.Dict: {},
}


# Where a settings file that could not be read was kept aside, until the
# user has been told (announce_damaged_settings).
_damaged_copy: str = ""


def _keep_damaged_file(reason: str) -> None:
    """Moves an unreadable settings file aside so nothing overwrites it."""
    global _damaged_copy
    stamp = time.strftime("%Y%m%d-%H%M%S")
    copy = f"{_config_file_path}.bad-{stamp}"
    try:
        os.replace(_config_file_path, copy)
    except OSError:
        copy = ""
    _damaged_copy = copy or _config_file_path
    logging.getLogger("system").error(
        f"Settings file could not be read ({reason}); defaults are used."
        + (f" The file was kept as {copy}." if copy else "")
    )


def announce_damaged_settings() -> None:
    """Tells the user once (when the main window is up) that the settings
    file could not be read and where it was kept."""
    global _damaged_copy
    if not _damaged_copy:
        return
    from gremlin.signal import signal

    signal.showNotification.emit(
        "Settings Reset",
        "Your settings file could not be read, so Gremlin-Platforms started "
        "with default settings. The old file was kept as:\n" + _damaged_copy,
    )
    _damaged_copy = ""


# Told once per session when configuration.json could not be written.
_write_failure_told = False


def _tell_write_failure(reason: str) -> None:
    """A settings file that can't be written (read-only, locked) is logged
    every time and told once per session (01 Q6). It never stops a quit or
    an update install: nothing waits on the answer."""
    global _write_failure_told
    logging.getLogger("system").error(f"Settings could not be saved: {reason}")
    if _write_failure_told:
        return
    _write_failure_told = True
    from gremlin.signal import signal

    signal.showNotification.emit(
        "Settings Not Saved", f"Settings could not be saved: {reason}"
    )


def settings_history_title(keys: list[str]) -> str:
    """A settings entry's title in Tools > History, by the names Options
    shows ("plugin-directory" -> "Plugins folder", a repeated name with its
    group: "Tempo duration"). Old entries are shown with it too."""
    names = dict.fromkeys(
        _title(str(key).rsplit("/", 1)[-1], str(key)) for key in keys
    )
    return "Changed " + ", ".join(names)


class Configuration(metaclass=common.SingletonMetaclass):
    """Responsible for loading and saving configuration data."""

    def __init__(self) -> None:
        """Creates a new instance, loading the current configuration."""
        # Settings may be changed from another thread (device hot-plug,
        # History), so every change and every walk over _data holds it.
        self._lock = threading.RLock()
        self._data = {}
        self._last_reload = None
        self.load()

    def count(self) -> int:
        return len(self._data)

    def load(self) -> None:
        if self._should_skip_reload():
            return
        # A save still waiting goes to disk first, so the file read is current.
        from gremlin import deferred_write

        deferred_write.flush("configuration")

        logging.getLogger("system").info(
            f"Loading configuration from {_config_file_path}."
        )

        result = "missing"
        json_data: dict = {}
        if os.path.isfile(_config_file_path):
            try:
                with open(_config_file_path, encoding="utf-8") as hdl:
                    text = hdl.read()
                # An empty file holds no settings (nothing to keep aside): the
                # same as no file. The program never writes one (save_now
                # writes a temporary file and swaps it in).
                json_data = json.loads(text) if text.strip() else {}
                if not isinstance(json_data, dict):
                    raise ValueError("not a settings file")
                result = "ok"
            except (OSError, ValueError) as e:
                # Unreadable as a whole: kept aside, defaults are used.
                json_data = {}
                result = "damaged"
                _keep_damaged_file(str(e))
        _trace("READ", "Program Settings", "load", _config_file_path, result)

        data: dict = {}
        skipped = []
        for section, sec_data in json_data.items():
            if not isinstance(sec_data, dict):
                skipped.append(str(section))
                continue
            for group, grp_data in sec_data.items():
                if not isinstance(grp_data, dict):
                    skipped.append(f"{section}/{group}")
                    continue
                for name, entry in grp_data.items():
                    try:
                        data[(section, group, name)] = _parse_entry(entry)
                    except Exception:
                        # A bad setting falls back to its default (register).
                        skipped.append(f"{section}/{group}/{name}")
        if skipped:
            logging.getLogger("system").warning(
                "Settings with a value that could not be read use their "
                "default: " + ", ".join(skipped)
            )

        with self._lock:
            self._data = data
            self._last_reload = clock.monotonic()
            self._history_view = self._settings_view()

    # Settings the user chooses (Options, HidHide, OSC, folders) go in the
    # history; window places, sizes and other things the program remembers
    # for itself don't.
    # (module-links: which module's picture each hidden device shows, worked
    # out by the HidHide window itself.)
    _HIDHIDE_PLACES = {"window-width", "window-height", "split-ratio", "module-links"}

    def _view_entry(self, key: tuple[str, str, str], entry: dict) -> str | None:
        """A setting's value as History compares it, or None for one History
        leaves out (window places and other things the program remembers)."""
        section, group, name = key
        if group == "internal":
            return None
        hidhide = (section, group) == ("display", "hidhide")
        if not entry.get("expose") and not hidhide:
            return None
        if hidhide and name in self._HIDHIDE_PLACES:
            return None
        value = entry["value"]
        if entry["data_type"] in util._property_to_string:
            value = util.property_to_string(entry["data_type"], value)
        return json.dumps(value, sort_keys=True)

    def _settings_view(self) -> dict[str, str]:
        view = {}
        with self._lock:
            items = list(self._data.items())
        for key, entry in items:
            shown = self._view_entry(key, entry)
            if shown is not None:
                view["/".join(key)] = shown
        return view

    def _note_first_appearance(self, key: tuple[str, str, str]) -> None:
        """A setting that appears (registered for the first time, or shown
        in Options from now on) is noted with the value it starts with, so
        a change made before the next save is still a change (08 S16; it
        was lost when it fell into the same write)."""
        view = getattr(self, "_history_view", None)
        name = "/".join(key)
        if view is None or name in view:
            return
        shown = self._view_entry(key, self._data[key])
        if shown is not None:
            view[name] = shown

    def _record_history(self) -> None:
        """Tools > History: the settings this save changed (only ones that
        were there before: a setting appearing for the first time isn't a
        change)."""
        before = getattr(self, "_history_view", None)
        after = self._settings_view()
        self._history_view = after
        if before is None:
            return
        changed = sorted(
            key for key in after if key in before and before[key] != after[key]
        )
        if not changed:
            return
        from gremlin import history

        history.record(
            "settings",
            settings_history_title(changed),
            {"keys": changed},
            {key: json.loads(before[key]) for key in changed},
            {key: json.loads(after[key]) for key in changed},
        )

    def save(self) -> None:
        """Save soon: one write about a second after the last change (and
        always on quit), not one per change (gremlin.deferred_write)."""
        from gremlin import deferred_write

        # The file as it is named now: a later path change cannot redirect it.
        path = _config_file_path
        deferred_write.schedule("configuration", lambda: self.save_now(path))

    def save_now(self, path: str | None = None) -> None:
        """Write configuration.json now. It is written to a temporary file
        first and then swapped in, so a crash mid-write cannot leave a
        broken file."""
        path = path or _config_file_path
        json_data: dict = {}
        with self._lock:
            items = [(key, dict(entry)) for key, entry in self._data.items()]
        for key, entry in items:
            section = key[0]
            group = key[1]
            name = key[2]
            if section not in json_data:
                json_data[section] = {}
            if group not in json_data[section]:
                json_data[section][group] = {}
            value = entry["value"]
            if entry["data_type"] in util._property_to_string:
                value = util.property_to_string(entry["data_type"], value)
            json_data[section][group][name] = {
                "value": value,
                "data_type": PropertyType.to_string(entry["data_type"]),
                "properties": entry["properties"],
                "expose": entry["expose"],
            }
        text = json.JSONEncoder(sort_keys=True, indent=4).encode(json_data)
        # The same safe write as module files and profiles (use()): a
        # temporary file, then a swap. It also makes the folder on the first
        # run.
        try:
            _write_text(Path(path), text)
        except OSError as e:
            _trace("SAVE", "Program Settings", "save", path, "failed")
            _tell_write_failure(e.strerror or str(e))
            return
        _trace("SAVE", "Program Settings", "save", path, "ok")
        self._record_history()

    def register(
        self,
        section: str,
        group: str,
        name: str,
        data_type: PropertyType,
        initial_value: Any,
        description: str,
        properties: dict[str, Any],
        expose: bool = False,
    ) -> None:
        with self._lock:
            self._validate(section, group, name)
            key = (section, group, name)
            if data_type not in _required_properties:
                raise error.GremlinError(
                    "Attempting to register an entry with unsupported data type: "
                    + f"{str(data_type)} in {key}"
                )
            if data_type in _required_properties:
                for req_prop, req_type in _required_properties[data_type].items():
                    if req_prop not in properties:
                        raise error.GremlinError(
                            f"Missing property '{req_prop}' of type "
                            f"{str(req_type)} in entry '{key}'"
                        )
                    elif not isinstance(properties[req_prop], req_type):
                        raise error.GremlinError(
                            f"Incorrect type for property '{req_prop}', expected "
                            + f"'{req_type}' but got '{type(properties[req_prop])}' "
                            + f"in entry {key}"
                        )
            changed = False
            if key in self._data:
                if self._data[key]["properties"] != properties:
                    logging.getLogger("system").warning(
                        f"Properties for parameter '{key}' changed, updating"
                    )
                    self._data[key]["properties"] = properties
                    changed = True
                if data_type != self._data[key]["data_type"]:
                    logging.getLogger("system").warning(
                        f"Data type for parameter '{key}' changed, updating from "
                        + f"'{self._data[key]['data_type']}' to '{data_type}'"
                    )
                    self._data[key]["data_type"] = data_type
                    changed = True
                if bool(self._data[key].get("expose")) != bool(expose):
                    self._data[key]["expose"] = bool(expose)
                    changed = True
                self._data[key]["description"] = description
            else:
                self._data[key] = {
                    "value": initial_value,
                    "data_type": data_type,
                    "description": description,
                    "properties": properties,
                    "expose": expose,
                }
                changed = True
            self._data[key]["is_registered"] = True
            self._note_first_appearance(key)
        # Saved outside the lock: a save made at once (no Qt) writes the
        # file and History.
        if changed:
            try:
                self.save()
            except TypeError:
                logging.getLogger("system").error(
                    f"Failed to save configuration after registering parameter {key}."
                )

    # The newest program version that has used this settings file.
    _VERSION_KEY = ("global", "internal", "settings-version")

    def purge_unused(self) -> None:
        """Remove settings no option uses any more (run at start, once every
        option is registered). Settings saved by a newer version are kept: an
        older copy of the program does not know that version's settings and
        must not delete them."""
        from gremlin.updater import is_newer

        current = util.get_code_version()
        with self._lock:
            stored = self._data.get(self._VERSION_KEY, {}).get("value")
        newer = bool(stored) and is_newer(str(stored), current)
        self.register(
            *self._VERSION_KEY, PropertyType.String, current,
            "The newest program version that has used these settings.", {}, False,
        )
        if newer:
            logging.getLogger("system").info(
                f"Settings were last used by version {stored}; settings this "
                f"version ({current}) does not know are kept."
            )
            return
        if stored != current:
            self.set(*self._VERSION_KEY, current)
        removed = False
        with self._lock:
            keys_to_delete = [
                key for key, value in self._data.items()
                if not value.get("is_registered", False)
            ]
            for key in keys_to_delete:
                if key[0] != "calibration":
                    # A retired setting: cleanup, not a problem.
                    logging.getLogger("system").info(
                        f"Removed setting {'/'.join(key)}: no longer used."
                    )
                    del self._data[key]
                    removed = True
        if removed:
            self.save()

    def get(self, section: str, group: str, name: str, entry: str) -> Any:
        return self._retrieve_value(section, group, name, entry)

    def set(self, section: str, group: str, name: str, value: Any) -> None:
        with self._lock:
            key = (section, group, name)
            if key not in self._data:
                raise error.GremlinError(f"No parameter with key '{key}' exists.")
            _, is_valid = util.determine_value_type(value, self._data[key]["data_type"])
            if is_valid:
                stored = self._data[key]["value"]
                # value() hands out the stored object; a list edited in place compares
                # equal to itself, so saving the same object always writes.
                changed = stored is value or stored != value
                if changed:
                    self._data[key]["value"] = value
            else:
                data_type = self._data[key]["data_type"]
                raise error.GremlinError(
                    "Value has wrong data type, expted: "
                    + f"'{data_type}' got '{type(value)}'"
                )
        if changed:
            self.save()

    def _keys(self) -> list[tuple[str, str, str]]:
        """Every setting's key, read under the lock (another thread may add
        one while this walks them)."""
        with self._lock:
            return list(self._data)

    def exists(self, section: str, group: str, name: str) -> bool:
        return (section, group, name) in self._data

    def sections(self, only_exposed: bool = True) -> list[str]:
        section_names = []
        for key in self._keys():
            if len(self.groups(key[0], only_exposed)) > 0:
                section_names.append(key[0])
        return sorted(set(section_names))

    def groups(self, section: str, only_exposed: bool = True) -> list[str]:
        group_names = []
        for key in self._keys():
            if (
                key[0] == section
                and len(self.entries(key[0], key[1], only_exposed)) > 0
            ):
                group_names.append(key[1])
        return sorted(set(group_names))

    def entries(self, section: str, group: str, only_exposed: bool = True) -> list[str]:
        if only_exposed:
            return sorted(
                list(
                    set(
                        [
                            key[2]
                            for key in self._keys()
                            if key[0] == section
                            and key[1] == group
                            and self.expose(section, group, key[2])
                        ]
                    )
                )
            )
        return sorted(
            list(
                set(
                    [
                        key[2]
                        for key in self._keys()
                        if key[0] == section and key[1] == group
                    ]
                )
            )
        )

    def value(self, section: str, group: str, name: str) -> Any:
        return self._retrieve_value(section, group, name, "value")

    def data_type(self, section: str, group: str, name: str) -> PropertyType:
        return self._retrieve_value(section, group, name, "data_type")

    def description(self, section: str, group: str, name: str) -> str:
        return self._retrieve_value(section, group, name, "description")

    def properties(self, section: str, group: str, name: str) -> dict[str, Any]:
        return self._retrieve_value(section, group, name, "properties")

    def expose(self, section: str, group: str, name: str) -> bool:
        return self._retrieve_value(section, group, name, "expose")

    def init_calibration(self, uuid: uuid.UUID, axis_id: int) -> None:
        uuid_str = str(uuid).upper()
        if not self.exists("calibration", uuid_str, str(axis_id)):
            self.register(
                "calibration",
                uuid_str,
                str(axis_id),
                PropertyType.List,
                [-32768, 0, 0, 32767, True],
                "",
                {},
                False,
            )

    def get_calibration(
        self, uuid: uuid.UUID, axis_id: int
    ) -> tuple[int, int, int, int, bool]:
        if self.exists("calibration", str(uuid).upper(), str(axis_id)):
            return self.value("calibration", str(uuid).upper(), str(axis_id))
        return (-32768, 0, 0, 32767, True)

    def set_calibration(
        self, uuid: uuid.UUID, axis_id: int, data: tuple[int, int, int, int, bool]
    ) -> None:
        self.set("calibration", str(uuid).upper(), str(axis_id), list(data))

    def _retrieve_value(self, section: str, group: str, name: str, entry: str) -> Any:
        key = (section, group, name)
        if key not in self._data:
            raise error.GremlinError(f"No parameter with key {key} exists.")
        return self._data[key][entry]

    def _validate(self, section: str, group: str, name: str) -> None:
        if section == "calibration":
            return
        if not re.match(r"^[a-z0-9-]+$", section):
            raise error.GremlinError(f"Invalid section name '{section}'.")
        if not re.match(r"^[a-z0-9-]+$", group):
            raise error.GremlinError(f"Invalid group name '{group}'.")
        if not re.match(r"^[a-z0-9-]+$", name):
            raise error.GremlinError(f"Invalid name '{name}'.")

    def _should_skip_reload(self) -> bool:
        return (
            self._last_reload is not None
            and clock.monotonic() - self._last_reload < 1.0
        )


def _same_program(a: str, b: str) -> bool:
    """Paths name the same program whichever slashes or case were typed."""

    def clean(path: str) -> str:
        return os.path.normcase(os.path.normpath(path.strip())).replace("\\", "/")

    return bool(a.strip()) and clean(a) == clean(b)


def get_profile(exec_path: str) -> str | None:
    for entry in Configuration().value("profile", "automation", "entries-auto-loading"):
        if entry[2] and _same_program(entry[1], exec_path):
            return entry[0]
    return None


def get_profile_with_regex(exec_path: str) -> str | None:
    profile_path = get_profile(exec_path)
    if profile_path:
        logging.getLogger("system").info(
            f"Found exact match for {exec_path}, returning {profile_path}"
        )
        return profile_path
    for entry in sorted(
        Configuration().value("profile", "automation", "entries-auto-loading"),
        key=lambda x: x[1].lower(),
    ):
        profile_path = entry[0]
        entry_path = entry[1]
        # Off, blank (would match every program) or a real file (exact only).
        if not entry[2] or not entry_path.strip() or os.path.exists(entry_path):
            continue
        try:
            found = re.search(entry_path, exec_path, re.IGNORECASE) is not None
        except re.error:
            logging.getLogger("system").warning(
                f"Auto-load pattern {entry_path!r} is not a valid pattern"
            )
            continue
        if found:
            logging.getLogger("system").info(
                f"Found regex match in {entry_path} for {exec_path}, "
                f"returning {profile_path}"
            )
            return profile_path
    return None
