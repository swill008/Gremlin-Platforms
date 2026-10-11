# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import (
    auto_mapping_tool,
    config,
    shared_state,
    signal,
)

QML_IMPORT_NAME = "Gremlin.Tools"
QML_IMPORT_MAJOR_VERSION = 1

# The Auto Mapping Tool's own settings (gremlin.ui.shell_option registers them).
_KEY = ("auto-mapping-tool", "mapper")


@ta.QmlElement
class Tools(QtCore.QObject):
    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)

    @QtCore.Slot(str, dict, dict, bool, bool, bool, str, result=str)
    def createMappings(
        self,
        mode: str,
        source_modules: dict[str, bool],
        dest_modules: dict[str, bool],
        overwrite: bool,
        repeat: bool,
        claim_outputs: bool = False,
        toolbar_mode: str = "",
    ) -> str:
        profile = shared_state.current_profile
        if profile is None:
            return "No profile is open."
        mapper = auto_mapping_tool.AutoMappingTool(profile)
        feedback_string = mapper.generate_module_mappings(
            [slug for (slug, chosen) in source_modules.items() if chosen],
            [slug for (slug, chosen) in dest_modules.items() if chosen],
            auto_mapping_tool.AutoMappingToolOptions(
                mode, repeat, overwrite, claim_outputs, toolbar_mode
            ),
        )
        signal.signal.profileChanged.emit()
        signal.signal.reloadCurrentInputItem.emit()
        signal.signal.configChanged.emit()
        cfg = config.Configuration()
        if cfg.exists(*_KEY, "remember-overwrite") and cfg.value(
            *_KEY, "remember-overwrite"
        ):
            cfg.set(*_KEY, "overwrite-used-inputs", bool(overwrite))
        return feedback_string

    @QtCore.Slot(result=bool)
    def lastOverwriteUsedInputs(self) -> bool:
        cfg = config.Configuration()
        if cfg.exists(*_KEY, "overwrite-used-inputs"):
            return bool(cfg.value(*_KEY, "overwrite-used-inputs"))
        return False
