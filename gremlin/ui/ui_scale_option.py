# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import math
import os

from PySide6 import QtCore

from gremlin.config import Configuration
from gremlin.signal import signal
from gremlin.types import PropertyType
from gremlin.ui.option import BaseMetaConfigOptionWidget, MetaConfigOption
import gremlin.ui.type_aliases as ta

QML_IMPORT_NAME = "Gremlin.Config"
QML_IMPORT_MAJOR_VERSION = 1

SCALE_SECTION = "ui"
SCALE_GROUP = "general"
SCALE_NAME = "ui-scale"
SCALE_MIN = 70
SCALE_MAX = 200
SCALE_DEFAULT = 100
DESCRIPTION = (
    "Scale the program UI when Windows scaling is disabled. "
    "The UI resizes when the slider is released."
)


def register() -> None:
    """The one definition of the UI scale setting (Options shows it with
    UiScaleModel). Called at start with the other settings."""
    Configuration().register(
        SCALE_SECTION, SCALE_GROUP, SCALE_NAME, PropertyType.Int, SCALE_DEFAULT,
        DESCRIPTION, {"min": SCALE_MIN, "max": SCALE_MAX}, True,
    )


def clamp_scale(value: object) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = SCALE_DEFAULT
    return max(SCALE_MIN, min(SCALE_MAX, number))


def saved_scale() -> int:
    cfg = Configuration()
    if cfg.exists(SCALE_SECTION, SCALE_GROUP, SCALE_NAME):
        return clamp_scale(cfg.value(SCALE_SECTION, SCALE_GROUP, SCALE_NAME))
    return SCALE_DEFAULT


def windows_scaling_active() -> bool:
    """Qt reads this once before it starts, so it holds for the whole run."""
    return os.environ.get("QT_ENABLE_HIGHDPI_SCALING") != "0"


def active_scale() -> int:
    """UI scale in percent: the slider value when Windows scaling is off, else 100."""
    if windows_scaling_active():
        return SCALE_DEFAULT
    return saved_scale()


def dp(pixels: float) -> int:
    """Pixels at the active UI scale, rounded like QML's Style.dp()."""
    return math.floor(pixels * active_scale() / 100 + 0.5)


@ta.QmlElement
class UiScaleModel(QtCore.QObject, BaseMetaConfigOptionWidget):
    scaleChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        QtCore.QObject.__init__(self, parent)
        BaseMetaConfigOptionWidget.__init__(self)
        self._config = Configuration()

    def _get_scale(self) -> int:
        return saved_scale()

    def _set_scale(self, value: int) -> None:
        scale = clamp_scale(value)
        current = saved_scale()
        if scale != current or not self._config.exists(SCALE_SECTION, SCALE_GROUP, SCALE_NAME):
            self._config.set(SCALE_SECTION, SCALE_GROUP, SCALE_NAME, scale)
        self.scaleChanged.emit()
        signal.uiScaleChanged.emit()

    @QtCore.Slot(int)
    def setScale(self, value: int) -> None:
        self._set_scale(value)

    def _get_minimum(self) -> int:
        return SCALE_MIN

    def _get_maximum(self) -> int:
        return SCALE_MAX

    def _get_enabled(self) -> bool:
        return not windows_scaling_active()

    scale = QtCore.Property(int, fget=_get_scale, fset=_set_scale, notify=scaleChanged)
    minimum = QtCore.Property(int, fget=_get_minimum, constant=True)
    maximum = QtCore.Property(int, fget=_get_maximum, constant=True)
    enabled = QtCore.Property(bool, fget=_get_enabled, constant=True)

    def _qml_path(self) -> str:
        return "file:///" + QtCore.QFile("qml:OptionUiScale.qml").fileName()


MetaConfigOption().register(
    SCALE_SECTION, SCALE_GROUP, SCALE_NAME, DESCRIPTION, UiScaleModel
)
