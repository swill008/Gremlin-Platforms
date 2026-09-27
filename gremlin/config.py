# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Any

from gremlin import (
    common,
    error,
    util,
)
from gremlin.types import PropertyType
from gremlin.ui.live_debug import trace

_config_file_path = os.path.join(util.userprofile_path(), "configuration.json")


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


class Configuration(metaclass=common.SingletonMetaclass):
    """Responsible for loading and saving configuration data."""

    def __init__(self) -> None:
        """Creates a new instance, loading the current configuration."""
        self._data = {}
        self._last_reload = None
        self.load()

    def count(self) -> int:
        return len(self._data)

    def load(self) -> None:
        if self._should_skip_reload():
            return

        logging.getLogger("system").info(
            f"Loading configuration from {_config_file_path}."
        )

        load_successful = False
        json_data = {}
        if os.path.isfile(_config_file_path):
            with open(_config_file_path) as hdl:
                try:
                    decoder = json.JSONDecoder()
                    json_data = decoder.decode(hdl.read())
                    load_successful = True
                except ValueError:
                    pass
        if not load_successful:
            self._data = {}
        trace(
            "READ",
            "Program Settings",
            "load",
            _config_file_path,
            "ok" if load_successful else "missing",
        )

        self._data = {}
        for section, sec_data in json_data.items():
            for group, grp_data in sec_data.items():
                for name, entry in grp_data.items():
                    data_type = PropertyType.to_enum(entry["data_type"])
                    value = entry["value"]
                    if data_type in util._property_to_string:
                        value = util.property_from_string(data_type, value)
                    self._data[(section, group, name)] = {
                        "value": value,
                        "data_type": data_type,
                        "properties": entry["properties"],
                        "expose": entry["expose"],
                    }

        self._last_reload = time.time()

    def save(self) -> None:
        json_data = {}
        for key, entry in self._data.items():
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
        with open(_config_file_path, "w") as hdl:
            encoder = json.JSONEncoder(sort_keys=True, indent=4)
            hdl.write(encoder.encode(json_data))
        trace("SAVE", "Program Settings", "save", _config_file_path, "ok")

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
        if changed:
            try:
                self.save()
            except TypeError:
                logging.getLogger("system").error(
                    f"Failed to save configuration after registering parameter {key}."
                )
        self._data[key]["is_registered"] = True

    def purge_unused(self) -> None:
        keys_to_delete = []
        for key, value in self._data.items():
            if not value.get("is_registered", False):
                keys_to_delete.append(key)
        removed = False
        for key in keys_to_delete:
            if key[0] != "calibration":
                logging.getLogger("system").warning(
                    f"Parameter '{key}' has not been registered, purging."
                )
                del self._data[key]
                removed = True
        if removed:
            self.save()

    def get(self, section: str, group: str, name: str, entry: str) -> Any:
        return self._retrieve_value(section, group, name, entry)

    def set(self, section: str, group: str, name: str, value: Any) -> None:
        key = (section, group, name)
        if key not in self._data:
            raise error.GremlinError(f"No parameter with key '{key}' exists.")
        _, is_valid = util.determine_value_type(value, self._data[key]["data_type"])
        if is_valid:
            if self._data[key]["value"] != value:
                self._data[key]["value"] = value
                self.save()
        else:
            data_type = self._data[key]["data_type"]
            raise error.GremlinError(
                "Value has wrong data type, expted: "
                + f"'{data_type}' got '{type(value)}'"
            )

    def exists(self, section: str, group: str, name: str) -> bool:
        return (section, group, name) in self._data

    def sections(self, only_exposed: bool = True) -> list[str]:
        section_names = []
        for key in self._data.keys():
            if len(self.groups(key[0], only_exposed)) > 0:
                section_names.append(key[0])
        return sorted(set(section_names))

    def groups(self, section: str, only_exposed: bool = True) -> list[str]:
        group_names = []
        for key in self._data.keys():
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
                            for key in self._data.keys()
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
                        for key in self._data.keys()
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
        return self._last_reload is not None and time.time() - self._last_reload < 1.0


def get_profile(exec_path: str) -> str | None:
    for entry in Configuration().value("profile", "automation", "entries-auto-loading"):
        if entry[1] == exec_path and entry[2]:
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
        if not entry[2] or os.path.exists(entry_path):
            continue
        if re.search(entry_path, exec_path) is not None:
            logging.getLogger("system").info(
                f"Found regex match in {entry_path} for {exec_path}, "
                f"returning {profile_path}"
            )
            return profile_path
        return None
