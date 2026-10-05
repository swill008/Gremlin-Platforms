# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin.config import Configuration
from gremlin.types import PropertyType
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

SECTION_DISPLAY = "display"
SECTION_AUTOMAP = "automap"


def ensure_shell_options() -> None:
    cfg = Configuration()
    specs = [
        (
            SECTION_DISPLAY,
            "status",
            "show-stubs",
            PropertyType.Bool,
            True,
            "Show stub cards for detected hardware that has no saved module.",
        ),
        (
            SECTION_DISPLAY,
            "status",
            "last-keep-after-release",
            PropertyType.Bool,
            True,
            "Keep the last: value after the control is released.",
        ),
        (
            SECTION_AUTOMAP,
            "mapper",
            "remember-overwrite",
            PropertyType.Bool,
            True,
            "Remember the Auto Mapper overwrite-used-inputs checkbox.",
        ),
        (
            SECTION_AUTOMAP,
            "mapper",
            "overwrite-used-inputs",
            PropertyType.Bool,
            False,
            "Last Auto Mapper overwrite-used-inputs value.",
        ),
    ]
    for section, group, name, dtype, initial, desc in specs:
        # The Auto Mapper remembers its own checkbox; it is not an Options entry.
        shown = section != SECTION_AUTOMAP
        if not cfg.exists(section, group, name):
            cfg.register(section, group, name, dtype, initial, desc, {}, shown)
        else:
            cfg.register(
                section,
                group,
                name,
                dtype,
                cfg.value(section, group, name),
                desc,
                {},
                shown,
            )


ensure_shell_options()


@ta.QmlElement
class StatusResetModel(QtCore.QObject, BaseMetaConfigOptionWidget):
    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionStatusCards.qml").fileName()


MetaConfigOption().register(
    SECTION_DISPLAY,
    "status",
    "reset-card-sizes",
    "Restore every Home card to its default size. Stacks, order, and hidden cards stay as they are. Right-click a card for Reset Size, or Reset Card Layout (size and stacking).",
    StatusResetModel,
)
