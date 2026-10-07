# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from PySide6 import QtCore

from gremlin.config import Configuration
from gremlin.types import PropertyType
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
from gremlin.ui import ui_scale_option
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

SECTION = "ui"
GROUP = "general"
NAME = "disable-windows-scaling"
DESCRIPTION = (
    "Ignore Windows display scaling and use the UI scale slider instead. "
    "Takes effect on the next start."
)


def register() -> None:
    """The one definition of this setting (Options shows it with
    WindowsScaleModel). joystick_gremlin reads the same key from the file
    before Qt starts, without this module."""
    Configuration().register(
        SECTION, GROUP, NAME, PropertyType.Bool, False, DESCRIPTION, {}, True
    )


def saved_disabled() -> bool:
    cfg = Configuration()
    if not cfg.exists(SECTION, GROUP, NAME):
        return False
    raw = cfg.value(SECTION, GROUP, NAME)
    return str(raw).strip().lower() in ("1", "true", "yes")


@ta.QmlElement
class WindowsScaleModel(QtCore.QObject, BaseMetaConfigOptionWidget):
    disabledChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)
        self._config = Configuration()

    def _get_disabled(self) -> bool:
        return saved_disabled()

    def _set_disabled(self, value: bool) -> None:
        disabled = bool(value)
        if disabled != saved_disabled() or not self._config.exists(SECTION, GROUP, NAME):
            self._config.set(SECTION, GROUP, NAME, disabled)
        self.disabledChanged.emit()

    @QtCore.Slot(bool)
    def setDisabled(self, value: bool) -> None:
        self._set_disabled(value)

    def _get_running_disabled(self) -> bool:
        return not ui_scale_option.windows_scaling_active()

    disabled = QtCore.Property(bool, fget=_get_disabled, fset=_set_disabled, notify=disabledChanged)
    runningDisabled = QtCore.Property(bool, fget=_get_running_disabled, constant=True)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionWindowsScale.qml").fileName()


MetaConfigOption().register(SECTION, GROUP, NAME, DESCRIPTION, WindowsScaleModel)
