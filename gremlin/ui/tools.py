# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import uuid

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import (
    auto_mapper,
    config,
    error,
    shared_state,
    signal,
    swap_devices,
)

QML_IMPORT_NAME = "Gremlin.Tools"
QML_IMPORT_MAJOR_VERSION = 1


@ta.QmlElement
class Tools(QtCore.QObject):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

    @QtCore.Slot(str, dict, dict, bool, bool, bool, result=str)
    def createMappings(
        self,
        mode: str,
        source_modules: dict[str, bool],
        dest_modules: dict[str, bool],
        overwrite: bool,
        repeat: bool,
        claim_outputs: bool = False,
    ) -> str:
        mapper = auto_mapper.AutoMapper(shared_state.current_profile)
        feedback_string = mapper.generate_module_mappings(
            [slug for (slug, chosen) in source_modules.items() if chosen],
            [slug for (slug, chosen) in dest_modules.items() if chosen],
            auto_mapper.AutoMapperOptions(mode, repeat, overwrite, claim_outputs),
        )
        signal.signal.profileChanged.emit()
        signal.signal.reloadCurrentInputItem.emit()
        signal.signal.configChanged.emit()
        cfg = config.Configuration()
        if cfg.exists("automap", "mapper", "remember-overwrite") and cfg.value(
            "automap", "mapper", "remember-overwrite"
        ):
            cfg.set("automap", "mapper", "overwrite-used-inputs", bool(overwrite))
        return feedback_string

    @QtCore.Slot(result=bool)
    def lastOverwriteUsedInputs(self) -> bool:
        cfg = config.Configuration()
        if cfg.exists("automap", "mapper", "overwrite-used-inputs"):
            return bool(cfg.value("automap", "mapper", "overwrite-used-inputs"))
        return False

    @QtCore.Slot(str, str, result=str)
    def swapDevices(self, source_uuid_str: str, target_uuid_str: str) -> str:
        try:
            source_uuid = uuid.UUID(source_uuid_str)
            target_uuid = uuid.UUID(target_uuid_str)
            result = swap_devices.swap_devices(
                shared_state.current_profile, source_uuid, target_uuid
            )
            signal.signal.profileChanged.emit()
            signal.signal.reloadCurrentInputItem.emit()
            return result.as_string()
        except ValueError:
            logging.getLogger("system").error(
                f"Invalid UUID provided for swapping devices: "
                f"{source_uuid_str}, {target_uuid_str}"
            )
            return (
                "Could not swap: choose a profile device and a connected device."
            )
        except swap_devices.SameDevice:
            return (
                "Could not swap: the profile device and the connected device "
                "are the same device."
            )
        except error.GremlinError as e:
            # The keyboard, logical device, OSC or Xbox: not a stick.
            logging.getLogger("system").error(f"Swap devices refused: {e}")
            return (
                "Could not swap: the keyboard, the Logical Device, OSC and "
                "the Xbox pad can't be swapped."
            )
